"""Re-generate a previously failed application from History.

A failed `generate` leaves an "Error" audit row plus an Unknown-<date>/<uuid>
Drive folder holding the JD and any pasted questions (see
``generate_application.py``). This use case re-runs the full pipeline against that
saved context, saves the artifacts back into the *same* folder (its Drive id is
preserved), then graduates the folder to its real <Company>/<Role> home and
rewrites the existing audit row in place (status -> Generated, all columns +
skill rows filled).

It deliberately does NOT dedupe (it's an intentional overwrite) and does NOT
persist its own error record on failure — a failure leaves the Error row + the
Unknown folder untouched, so the run can simply be re-tried.
"""
from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

from app.domain.models import (
    APPLICATION_QUESTIONS_INPUT,
    JOB_DESCRIPTION_MD,
    ApplicationRecord,
    ApplicationStatus,
    ContactHeader,
    JobDescription,
)
from app.domain.ports import (
    AuditLog,
    DocumentRenderer,
    ExperienceDocStore,
    LLMClient,
    OutputStore,
)
from app.usecases.generate_application import (
    _build_record,
    _norm,
    _render_all,
    _save_artifacts,
)

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegenerationRequest:
    folder_id: str
    provider: str | None = None
    # None ⇒ reuse the saved questions input; "" ⇒ no questions; else an override.
    application_questions: str | None = None


@dataclass(frozen=True)
class RegenerateApplication:
    docs: ExperienceDocStore
    llms: Mapping[str, LLMClient]
    renderer: DocumentRenderer
    store: OutputStore
    audit_log: AuditLog
    default_provider: str = "anthropic"
    resume_header: ContactHeader = field(default_factory=ContactHeader)

    def __call__(self, req: RegenerationRequest) -> ApplicationRecord:
        jd_bytes, _ = self.store.read_file(
            folder_id=req.folder_id, filename=JOB_DESCRIPTION_MD
        )
        jd = JobDescription(text=jd_bytes.decode("utf-8", errors="replace"))
        jd_hash = hashlib.sha256(jd.text.encode()).hexdigest()[:16]
        questions = self._resolve_questions(req.folder_id, req.application_questions)

        provider = req.provider or self.default_provider
        if provider not in self.llms:
            provider = self.default_provider
        _log.info("regenerate folder=%s provider=%s", req.folder_id, provider)

        content = self.llms[provider].generate(
            experience_docs=self.docs.load_concatenated(),
            jd=jd,
            candidate_name=self.resume_header.name,
            application_questions=questions,
        )
        company = _norm(content.audit.company)
        role = _norm(content.audit.role)

        bundle = _render_all(self.renderer, content, self.resume_header)
        _save_artifacts(self.store, folder_id=req.folder_id, jd_text=jd.text, bundle=bundle)
        # If the caller overrode the questions, persist them so a later regen is
        # still one-click.
        if req.application_questions is not None and req.application_questions.strip():
            self.store.save_text(
                folder_id=req.folder_id, filename=APPLICATION_QUESTIONS_INPUT,
                text=req.application_questions, mime="text/plain",
            )

        new_ref = self.store.move_folder(folder_id=req.folder_id, company=company, role=role)
        record = _build_record(
            company=company, role=role, status=ApplicationStatus.GENERATED.value,
            content=content, jd=jd, jd_hash=jd_hash, folder=new_ref,
        )
        self.audit_log.update_record(record)
        return record

    def _resolve_questions(self, folder_id: str, override: str | None) -> str:
        if override is not None:
            return override
        try:
            data, _ = self.store.read_file(
                folder_id=folder_id, filename=APPLICATION_QUESTIONS_INPUT
            )
        except FileNotFoundError:
            return ""
        return data.decode("utf-8", errors="replace")
