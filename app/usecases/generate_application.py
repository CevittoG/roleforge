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

Failure path: anything from the LLM call onward is wrapped. On failure we
best-effort persist a recoverable record — an "Error" Sheet row plus an
``Unknown - <date>/<uuid>`` Drive folder holding the JD and any pasted questions
— then raise ``GenerationFailedError`` so the run can be re-generated later from
History (see ``regenerate_application.py``). The shared rendering / saving /
record-building helpers below are reused by that regen use case.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.models import (
    APPLICATION_QUESTIONS_DOCX,
    APPLICATION_QUESTIONS_INPUT,
    COVER_LETTER_TXT,
    DOCX_MIME,
    JOB_DESCRIPTION_MD,
    MATCH_REPORT_MD,
    RESUME_DOC,
    ApplicationAnswer,
    ApplicationRecord,
    ApplicationStatus,
    ContactHeader,
    FolderRef,
    GeneratedContent,
    JobDescription,
    WorkMode,
)
from app.domain.ports import (
    AuditLog,
    DocumentRenderer,
    ExperienceDocStore,
    LLMClient,
    OutputStore,
)
from app.usecases.errors import DuplicateApplicationError, GenerationFailedError

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
    provider: str | None = None  # which LLM; None ⇒ use the default
    application_questions: str = ""  # optional; answered in the same call when present


@dataclass(frozen=True)
class GenerateApplication:
    docs: ExperienceDocStore
    llms: Mapping[str, LLMClient]
    renderer: DocumentRenderer
    store: OutputStore
    audit_log: AuditLog
    default_provider: str = "anthropic"
    resume_header: ContactHeader = field(default_factory=ContactHeader)  # from config

    def __call__(self, req: GenerationRequest) -> ApplicationRecord:
        t_start = time.monotonic()

        jd = JobDescription(text=req.raw_text.strip())
        jd_hash = hashlib.sha256(jd.text.encode()).hexdigest()[:16]

        provider = req.provider or self.default_provider
        if provider not in self.llms:
            provider = self.default_provider
        _log.info("generate provider=%s", provider)

        # Anything from the LLM call onward can fail (API errors, quota, Drive,
        # Sheets). content stays None until the LLM returns, so _persist_failure
        # can fall back to "Unknown" when the LLM itself is what broke.
        content: GeneratedContent | None = None
        try:
            with _phase("llm"):
                content = self.llms[provider].generate(
                    experience_docs=self.docs.load_concatenated(),
                    jd=jd,
                    candidate_name=self.resume_header.name,
                    application_questions=req.application_questions,
                )
            company = _norm(content.audit.company)
            role = _norm(content.audit.role)

            existing = self.audit_log.find(company=company, role=role, jd_hash=jd_hash)
            if existing is not None and not req.confirm_overwrite:
                raise DuplicateApplicationError(existing)

            with _phase("render"):
                bundle = _render_all(self.renderer, content, self.resume_header)

            with _phase("drive_save"):
                folder = self.store.ensure_folder(company=company, role=role)
                _save_artifacts(self.store, folder_id=folder.id, jd_text=jd.text, bundle=bundle)

            record = _build_record(
                company=company, role=role, status=ApplicationStatus.GENERATED.value,
                content=content, jd=jd, jd_hash=jd_hash, folder=folder,
            )
            with _phase("sheet_append"):
                self.audit_log.append(record)

            _log.info("phase=total duration_s=%.2f", time.monotonic() - t_start)
            return record
        except DuplicateApplicationError:
            raise  # not a failure — caller decides whether to overwrite
        except Exception as exc:
            _log.exception("generate failed; persisting recoverable error record")
            error_record = self._persist_failure(
                jd=jd, jd_hash=jd_hash, content=content,
                questions_text=req.application_questions, original=exc,
            )
            raise GenerationFailedError(error_record, exc) from exc

    def _persist_failure(
        self,
        *,
        jd: JobDescription,
        jd_hash: str,
        content: GeneratedContent | None,
        questions_text: str,
        original: BaseException,
    ) -> ApplicationRecord | None:
        """Best-effort: leave a recoverable trace of a failed run. All failures
        land under Job Applications/Unknown - <date>/<uuid>/ (a successful regen
        later moves the uuid folder to its real <Company>/<Role> home). Swallows
        its own errors so the original failure always surfaces to the caller."""
        try:
            company = _norm(content.audit.company) if content else "Unknown"
            role = _norm(content.audit.role) if content else ""
            today = datetime.now(UTC).date().isoformat()
            folder = self.store.ensure_error_folder(
                group_name=f"Unknown - {today}", run_id=uuid4().hex,
            )
            # JD first — the whole point of the error folder is traceability.
            self.store.save_text(folder_id=folder.id, filename=JOB_DESCRIPTION_MD, text=jd.text)
            if questions_text.strip():
                self.store.save_text(
                    folder_id=folder.id, filename=APPLICATION_QUESTIONS_INPUT,
                    text=questions_text, mime="text/plain",
                )
                blanks = tuple(
                    ApplicationAnswer(question=q, answer="")
                    for q in _split_questions(questions_text)
                )
                if blanks:
                    self.store.save_bytes(
                        folder_id=folder.id, filename=APPLICATION_QUESTIONS_DOCX,
                        data=self.renderer.render_application_questions_docx(blanks),
                        mime=DOCX_MIME,
                    )
            record = _build_record(
                company=company, role=role, status=ApplicationStatus.ERROR.value,
                content=content, jd=jd, jd_hash=jd_hash, folder=folder,
            )
            self.audit_log.append(record)
            return record
        except Exception:
            _log.exception("failed to persist error record for a failed generate")
            return None


_WHITESPACE = re.compile(r"\s+")


def _norm(value: str) -> str:
    """Strip + collapse internal whitespace. Keeps capitalization for display."""
    return _WHITESPACE.sub(" ", value).strip()


def _split_questions(raw: str) -> tuple[str, ...]:
    """Split a pasted questions blob into individual non-empty lines. Used to
    render a placeholder (no-answer) Application_Questions.docx on the error
    path; the LLM does the real splitting when it answers them."""
    return tuple(line.strip() for line in raw.splitlines() if line.strip())


@dataclass(frozen=True)
class _RenderBundle:
    resume_docx: bytes
    cover_letter_txt: str
    match_report_md: str
    application_questions_docx: bytes | None


def _render_all(
    renderer: DocumentRenderer, content: GeneratedContent, header: ContactHeader
) -> _RenderBundle:
    """Render every artifact for a generated application. Contact header is
    authoritative config data, never model output."""
    resume = replace(content.resume, header=header)
    return _RenderBundle(
        resume_docx=renderer.render_resume_docx(resume),
        cover_letter_txt=renderer.render_cover_letter_txt(content.cover_letter),
        match_report_md=renderer.render_match_report(content.audit),
        application_questions_docx=(
            renderer.render_application_questions_docx(content.application_answers)
            if content.application_answers
            else None
        ),
    )


def _save_artifacts(
    store: OutputStore, *, folder_id: str, jd_text: str, bundle: _RenderBundle
) -> None:
    """Write all artifacts into the folder. JD goes first so a mid-save crash
    still leaves the JD for traceability."""
    store.save_text(folder_id=folder_id, filename=JOB_DESCRIPTION_MD, text=jd_text)
    store.save_google_doc(folder_id=folder_id, name=RESUME_DOC, docx_bytes=bundle.resume_docx)
    store.save_text(
        folder_id=folder_id, filename=COVER_LETTER_TXT,
        text=bundle.cover_letter_txt, mime="text/plain",
    )
    store.save_text(folder_id=folder_id, filename=MATCH_REPORT_MD, text=bundle.match_report_md)
    if bundle.application_questions_docx is not None:
        store.save_bytes(
            folder_id=folder_id, filename=APPLICATION_QUESTIONS_DOCX,
            data=bundle.application_questions_docx, mime=DOCX_MIME,
        )


def _build_record(
    *,
    company: str,
    role: str,
    status: str,
    content: GeneratedContent | None,
    jd: JobDescription,
    jd_hash: str,
    folder: FolderRef | None,
) -> ApplicationRecord:
    """Build an audit row. ``content`` is None on the failure path when the LLM
    never returned — the decision-support columns then default to empty."""
    audit = content.audit if content else None
    return ApplicationRecord(
        date=datetime.now(UTC).isoformat(timespec="seconds"),
        company=company,
        role=role,
        status=status,
        work_mode=audit.work_mode.value if audit else WorkMode.UNKNOWN.value,
        location=audit.location if audit else None,
        pay=audit.pay if audit else None,
        benefits=audit.benefits if audit else None,
        jd_source_url=jd.source_url,
        folder_url=folder.url if folder else "",
        folder_id=folder.id if folder else "",
        seniority=audit.seniority if audit else "",
        fit_score=audit.fit_score if audit else None,
        key_requirements=audit.key_requirements if audit else (),
        tech_stack=audit.tech_stack if audit else (),
        matched=audit.matched if audit else (),
        missing=audit.missing if audit else (),
        concerns=audit.concerns if audit else None,
        jd_hash=jd_hash,
    )
