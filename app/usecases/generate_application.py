"""Core orchestration. Composes the ports; contains the business rules.

Flow:
  1. Resolve JD (paste or URL).
  2. Run the LLM skill -> audit + resume + cover letter + interview prep.
     The LLM is also what canonicalizes company/role from arbitrary JD text;
     we can't dedupe before this step without a separate extraction call.
  3. Normalize the (company, role) pair (whitespace) so model drift like
     "Acme  Corp" vs "Acme Corp" doesn't silently fragment the audit log.
  4. Duplicate check on the normalized pair. If it exists and overwrite is
     not confirmed -> raise; stop before any Drive write.
  5. Render PDFs + Match_Report.md, write the 5 files, append the audit row.
     Overwrite semantics: files are re-saved in place; a fresh audit row is
     appended so the Sheet keeps full generation history.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.models import (
    COVER_LETTER_PDF,
    INTERVIEW_PREP_MD,
    JOB_DESCRIPTION_MD,
    MATCH_REPORT_MD,
    RESUME_PDF,
    ApplicationRecord,
    GeneratedContent,
    JobDescription,
)
from app.domain.ports import (
    AuditLog,
    ExperienceDocStore,
    JDSource,
    LLMClient,
    OutputStore,
    PdfRenderer,
)
from app.usecases.errors import DuplicateApplicationError


@dataclass(frozen=True)
class GenerationRequest:
    raw_text: str | None
    url: str | None
    confirm_overwrite: bool = False


@dataclass(frozen=True)
class GenerateApplication:
    jd_source: JDSource
    docs: ExperienceDocStore
    llm: LLMClient
    pdf: PdfRenderer
    store: OutputStore
    audit_log: AuditLog

    def __call__(self, req: GenerationRequest) -> ApplicationRecord:
        jd: JobDescription = self.jd_source.resolve(raw_text=req.raw_text, url=req.url)

        jd_hash = hashlib.sha256(jd.text.encode()).hexdigest()[:16]

        content: GeneratedContent = self.llm.generate(
            experience_docs=self.docs.load_concatenated(), jd=jd
        )
        company = _norm(content.audit.company)
        role = _norm(content.audit.role)

        existing = self.audit_log.find(company=company, role=role, jd_hash=jd_hash)
        if existing is not None and not req.confirm_overwrite:
            raise DuplicateApplicationError(existing)

        folder = self.store.ensure_folder(company=company, role=role)

        self.store.save_bytes(
            folder_id=folder.id, filename=RESUME_PDF,
            data=self.pdf.render_resume(content.resume), mime="application/pdf",
        )
        self.store.save_bytes(
            folder_id=folder.id, filename=COVER_LETTER_PDF,
            data=self.pdf.render_cover_letter(content.cover_letter), mime="application/pdf",
        )
        self.store.save_text(
            folder_id=folder.id, filename=JOB_DESCRIPTION_MD, text=jd.text,
        )
        self.store.save_text(
            folder_id=folder.id, filename=INTERVIEW_PREP_MD, text=content.interview_prep_md,
        )
        self.store.save_text(
            folder_id=folder.id, filename=MATCH_REPORT_MD,
            text=self.pdf.render_match_report(content.audit),
        )

        record = ApplicationRecord(
            date=datetime.now(UTC).isoformat(timespec="seconds"),
            company=company,
            role=role,
            status="Generated",
            work_mode=content.audit.work_mode.value,
            location=content.audit.location,
            pay=content.audit.pay,
            benefits=content.audit.benefits,
            jd_source_url=jd.source_url,
            folder_url=folder.url,
            folder_id=folder.id,
            seniority=content.audit.seniority,
            fit_score=content.audit.fit_score,
            key_requirements=content.audit.key_requirements,
            tech_stack=content.audit.tech_stack,
            matched=content.audit.matched,
            missing=content.audit.missing,
            concerns=content.audit.concerns,
            jd_hash=jd_hash,
        )
        self.audit_log.append(record)
        return record


_WHITESPACE = re.compile(r"\s+")


def _norm(value: str) -> str:
    """Strip + collapse internal whitespace. Keeps capitalization for display."""
    return _WHITESPACE.sub(" ", value).strip()
