"""Ports: the abstractions the use cases depend on.

Each is a typing.Protocol so adapters need only match the shape (structural
typing). The core never imports anthropic / googleapiclient / python-docx —
swapping a vendor means writing a new adapter, with zero changes here
(Open/Closed + Dependency Inversion).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.models import (
    ApplicationAnswer,
    ApplicationRecord,
    AuditFields,
    CoverLetterContent,
    FolderRef,
    GeneratedContent,
    JobDescription,
    ResumeContent,
)


@runtime_checkable
class ExperienceDocStore(Protocol):
    def load_concatenated(self) -> str:
        """Return all experience markdown docs concatenated, ready for the prompt."""
        ...


@runtime_checkable
class LLMClient(Protocol):
    def generate(
        self,
        *,
        experience_docs: str,
        jd: JobDescription,
        candidate_name: str = "",
        application_questions: str = "",
    ) -> GeneratedContent:
        """Run the skill: produce audit fields, resume, and cover letter.
        `candidate_name` (authoritative, from config) signs the cover letter.
        When `application_questions` is non-empty, the same call also answers
        them (reusing the grounded context) and returns them in
        `GeneratedContent.application_answers`."""
        ...

    def generate_interview_prep(self, *, experience_docs: str, jd: JobDescription) -> str:
        """On-demand interview-prep Markdown for an already-generated application."""
        ...

    def generate_application_answers(
        self, *, experience_docs: str, jd: JobDescription, questions: str
    ) -> tuple[ApplicationAnswer, ...]:
        """On-demand structured answers to application questions for an
        already-generated application, when the questions surface after the
        main run (the renderer turns them into the .docx)."""
        ...


@runtime_checkable
class DocumentRenderer(Protocol):
    def render_resume_docx(self, content: ResumeContent) -> bytes:
        """Render the resume as a .docx (uploaded to Drive as a Google Doc)."""
        ...

    def render_cover_letter_txt(self, content: CoverLetterContent) -> str:
        """Render the cover letter as plain text."""
        ...

    def render_match_report(self, audit: AuditFields) -> str:
        """Render the per-application match report as Markdown."""
        ...

    def render_application_questions_docx(
        self, answers: tuple[ApplicationAnswer, ...]
    ) -> bytes:
        """Render answered application questions as an enumerated .docx."""
        ...


@runtime_checkable
class OutputStore(Protocol):
    def ensure_folder(self, *, company: str, role: str) -> FolderRef:
        """Create/locate Job Applications/<Company>/<Role>/ and return its ref."""
        ...

    def ensure_error_folder(self, *, group_name: str, run_id: str) -> FolderRef:
        """Create/locate Job Applications/<group_name>/<run_id>/ for a failed run
        (e.g. group_name='Unknown - 2026-06-13', run_id=a uuid). The run_id child
        can later be reparented + renamed to its real <Company>/<Role> home by a
        successful regen (see move_folder)."""
        ...

    def move_folder(self, *, folder_id: str, company: str, role: str) -> FolderRef:
        """Reparent folder_id under Job Applications/<company>/ (creating the
        company folder if needed) and rename it to <role>. The folder id is
        unchanged, so the audit row's folder_id stays valid. Used by regen to
        graduate an Unknown-<date>/<uuid> folder to its real home."""
        ...

    def save_bytes(self, *, folder_id: str, filename: str, data: bytes, mime: str) -> None: ...
    def save_text(
        self, *, folder_id: str, filename: str, text: str, mime: str = "text/markdown"
    ) -> None: ...
    def save_google_doc(self, *, folder_id: str, name: str, docx_bytes: bytes) -> None:
        """Upload a .docx, converting it to a native Google Doc on import."""
        ...

    def read_file(self, *, folder_id: str, filename: str) -> tuple[bytes, str]:
        """Return (data, mime_type) for an existing file in the folder. A Google
        Doc is exported to PDF; other files are returned byte-for-byte."""
        ...


@runtime_checkable
class AuditLog(Protocol):
    def find(self, *, company: str, role: str, jd_hash: str = "") -> ApplicationRecord | None: ...
    def append(self, record: ApplicationRecord) -> None: ...
    def list_all(self) -> list[ApplicationRecord]: ...
    def update_status(self, *, folder_id: str, status: str) -> None:
        """Update the status cell for the row matching folder_id.
        Raises RecordNotFoundError if no row matches."""
        ...

    def update_record(self, record: ApplicationRecord) -> None:
        """Rewrite the entire row matching record.folder_id (all columns) and
        append fresh skill rows. Used by regen to promote an 'Error' row to a
        full 'Generated' row in place. Raises RecordNotFoundError if no row
        matches."""
        ...
