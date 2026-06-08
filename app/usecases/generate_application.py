"""Core orchestration. Composes the ports; contains the business rules.

Flow:
  1. Resolve JD (paste or URL).
  2. Run the LLM skill -> audit + resume + cover letter + interview prep.
  3. Duplicate check on (company, role). If it exists and overwrite not
     confirmed -> raise (no Drive writes, no extra token spend already paid,
     but we stop before persisting). NOTE: the cheap pre-check below avoids
     even the LLM call when we can determine the company/role up front.
  4. Render PDFs, write the 4 files, append the audit row.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.models import (
    COVER_LETTER_PDF,
    INTERVIEW_PREP_MD,
    JOB_DESCRIPTION_MD,
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

        content: GeneratedContent = self.llm.generate(
            experience_docs=self.docs.load_concatenated(), jd=jd
        )
        company, role = content.audit.company, content.audit.role

        existing = self.audit_log.find(company=company, role=role)
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
        )
        # Overwrite semantics: files were re-saved above; we append a fresh audit
        # row so the Sheet keeps the full generation history (date trail).
        self.audit_log.append(record)
        return record
