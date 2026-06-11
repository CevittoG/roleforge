"""Core orchestration. Composes the ports; contains the business rules.

Flow:
  1. Run the LLM skill on the pasted JD text -> audit + resume + cover letter.
     (Interview prep is generated on demand in a separate call.) The LLM also
     canonicalizes company/role from arbitrary JD text; we can't dedupe before
     this step without a separate extraction.
  2. Normalize the (company, role) pair (whitespace) so model drift like
     "Acme  Corp" vs "Acme Corp" doesn't silently fragment the audit log.
  3. Duplicate check on the normalized pair. If it exists and overwrite is
     not confirmed -> raise; stop before any Drive write.
  4. Render the resume docx (saved as a Google Doc), the cover-letter txt, and
     Match_Report.md; write Job_Description.md too; append the audit row.
     Overwrite semantics: files are re-saved in place; a fresh audit row is
     appended so the Sheet keeps full generation history.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

from app.domain.models import (
    COVER_LETTER_TXT,
    JOB_DESCRIPTION_MD,
    MATCH_REPORT_MD,
    RESUME_DOC,
    ApplicationRecord,
    ContactHeader,
    GeneratedContent,
    JobDescription,
)
from app.domain.ports import (
    AuditLog,
    DocumentRenderer,
    ExperienceDocStore,
    LLMClient,
    OutputStore,
)
from app.usecases.errors import DuplicateApplicationError

_log = logging.getLogger(__name__)


@contextmanager
def _phase(name: str) -> Iterator[None]:
    """Time a generate phase and emit one structured log line. Operational
    visibility for the Cloudflare 100s edge timeout decision."""
    t0 = time.monotonic()
    try:
        yield
    finally:
        _log.info("phase=%s duration_s=%.2f", name, time.monotonic() - t0)


@dataclass(frozen=True)
class GenerationRequest:
    raw_text: str
    confirm_overwrite: bool = False


@dataclass(frozen=True)
class GenerateApplication:
    docs: ExperienceDocStore
    llm: LLMClient
    renderer: DocumentRenderer
    store: OutputStore
    audit_log: AuditLog
    resume_header: ContactHeader = field(default_factory=ContactHeader)  # from config

    def __call__(self, req: GenerationRequest) -> ApplicationRecord:
        t_start = time.monotonic()

        jd = JobDescription(text=req.raw_text.strip())
        jd_hash = hashlib.sha256(jd.text.encode()).hexdigest()[:16]

        with _phase("claude"):
            content: GeneratedContent = self.llm.generate(
                experience_docs=self.docs.load_concatenated(),
                jd=jd,
                candidate_name=self.resume_header.name,
            )
        company = _norm(content.audit.company)
        role = _norm(content.audit.role)

        existing = self.audit_log.find(company=company, role=role, jd_hash=jd_hash)
        if existing is not None and not req.confirm_overwrite:
            raise DuplicateApplicationError(existing)

        # Contact header is authoritative config data, never model output.
        resume = replace(content.resume, header=self.resume_header)
        with _phase("render"):
            resume_docx = self.renderer.render_resume_docx(resume)
            cover_letter_txt = self.renderer.render_cover_letter_txt(content.cover_letter)
            match_report_md = self.renderer.render_match_report(content.audit)

        with _phase("drive_save"):
            folder = self.store.ensure_folder(company=company, role=role)
            self.store.save_google_doc(
                folder_id=folder.id, name=RESUME_DOC, docx_bytes=resume_docx,
            )
            self.store.save_text(
                folder_id=folder.id, filename=COVER_LETTER_TXT,
                text=cover_letter_txt, mime="text/plain",
            )
            self.store.save_text(
                folder_id=folder.id, filename=JOB_DESCRIPTION_MD, text=jd.text,
            )
            self.store.save_text(
                folder_id=folder.id, filename=MATCH_REPORT_MD, text=match_report_md,
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
        with _phase("sheet_append"):
            self.audit_log.append(record)

        _log.info("phase=total duration_s=%.2f", time.monotonic() - t_start)
        return record


_WHITESPACE = re.compile(r"\s+")


def _norm(value: str) -> str:
    """Strip + collapse internal whitespace. Keeps capitalization for display."""
    return _WHITESPACE.sub(" ", value).strip()
