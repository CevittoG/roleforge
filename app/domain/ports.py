"""Ports: the abstractions the use cases depend on.

Each is a typing.Protocol so adapters need only match the shape (structural
typing). The core never imports anthropic / googleapiclient / weasyprint —
swapping a vendor means writing a new adapter, with zero changes here
(Open/Closed + Dependency Inversion).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.models import (
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
    def generate(self, *, experience_docs: str, jd: JobDescription) -> GeneratedContent:
        """Run the skill: produce audit fields, resume, cover letter, interview prep."""
        ...


@runtime_checkable
class PdfRenderer(Protocol):
    def render_resume(self, content: ResumeContent) -> bytes: ...
    def render_cover_letter(self, content: CoverLetterContent) -> bytes: ...
    def render_match_report(self, audit: AuditFields) -> str:
        """Render the per-application match report as Markdown (no PDF)."""
        ...


@runtime_checkable
class OutputStore(Protocol):
    def ensure_folder(self, *, company: str, role: str) -> FolderRef:
        """Create/locate Job Applications/<Company>/<Role>/ and return its ref."""
        ...

    def save_bytes(self, *, folder_id: str, filename: str, data: bytes, mime: str) -> None: ...
    def save_text(self, *, folder_id: str, filename: str, text: str) -> None: ...
    def read_file(self, *, folder_id: str, filename: str) -> tuple[bytes, str]:
        """Return (data, mime_type) for an existing file in the folder."""
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
