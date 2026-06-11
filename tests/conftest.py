"""Shared fixtures and fakes for the test suite.

The fakes satisfy the structural ports in ``app/domain/ports.py`` so the core
stays network-free and credential-free in tests.
"""
from __future__ import annotations

from app.domain.models import (
    AdditionalLine,
    ApplicationRecord,
    AuditFields,
    ContactHeader,
    CoverLetterContent,
    EducationEntry,
    ExperienceEntry,
    FolderRef,
    GeneratedContent,
    JobDescription,
    ResumeContent,
)
from app.usecases.errors import RecordNotFoundError


def make_generated() -> GeneratedContent:
    """A minimal, valid GeneratedContent for orchestration tests."""
    return GeneratedContent(
        audit=AuditFields(company="Acme Corp", role="Data Engineer"),
        resume=ResumeContent(
            experience=[
                ExperienceEntry(
                    company="uPlanner", title="Data Engineer", location="Remote",
                    start="Jul 2021", end="Present", bullets=["Built X that reduced Y."],
                )
            ],
            education=[EducationEntry(institution="UAI", degree="BS CS")],
            additional=[AdditionalLine(label="Technical Skills", text="Python, SQL")],
        ),
        cover_letter=CoverLetterContent(
            greeting="Dear Data team,",
            body_paragraphs=["Hook.", "Why you.", "Why them."],
            closing="Best,\nAlfredo Gutierrez",
        ),
    )


class FakeExperienceDocs:
    """In-memory ExperienceDocStore."""

    def __init__(self, text: str = "EXPERIENCE") -> None:
        self.text = text

    def load_concatenated(self) -> str:
        return self.text


class FakeLLM:
    """Records calls; returns canned content. Satisfies LLMClient."""

    def __init__(
        self, content: GeneratedContent | None = None, prep_md: str = "## Interview prep"
    ) -> None:
        self._content = content or make_generated()
        self.prep_md = prep_md
        self.generate_calls: list[tuple[str, JobDescription, str]] = []
        self.prep_calls: list[tuple[str, JobDescription]] = []

    def generate(
        self, *, experience_docs: str, jd: JobDescription, candidate_name: str = ""
    ) -> GeneratedContent:
        self.generate_calls.append((experience_docs, jd, candidate_name))
        return self._content

    def generate_interview_prep(self, *, experience_docs: str, jd: JobDescription) -> str:
        self.prep_calls.append((experience_docs, jd))
        return self.prep_md


class FakeRenderer:
    """Records inputs; returns sentinels. Satisfies DocumentRenderer."""

    def __init__(self) -> None:
        self.resume: ResumeContent | None = None
        self.cover: CoverLetterContent | None = None

    def render_resume_docx(self, content: ResumeContent) -> bytes:
        self.resume = content
        return b"DOCX-BYTES"

    def render_cover_letter_txt(self, content: CoverLetterContent) -> str:
        self.cover = content
        return "COVER-TEXT\n"

    def render_match_report(self, audit: AuditFields) -> str:
        return "MATCH-REPORT-MD"


class FakeOutputStore:
    """In-memory OutputStore. Records every write; supports JD read-back."""

    def __init__(self, preload: dict[tuple[str, str], tuple[bytes, str]] | None = None) -> None:
        self.google_docs: dict[tuple[str, str], bytes] = {}
        self.texts: dict[tuple[str, str], tuple[str, str]] = {}
        self.bytes_files: dict[tuple[str, str], tuple[bytes, str]] = {}
        self._preload = preload or {}

    def ensure_folder(self, *, company: str, role: str) -> FolderRef:
        fid = f"{company}__{role}"
        return FolderRef(id=fid, url=f"https://drive.example/{fid}")

    def save_bytes(self, *, folder_id: str, filename: str, data: bytes, mime: str) -> None:
        self.bytes_files[(folder_id, filename)] = (data, mime)

    def save_text(
        self, *, folder_id: str, filename: str, text: str, mime: str = "text/markdown"
    ) -> None:
        self.texts[(folder_id, filename)] = (text, mime)

    def save_google_doc(self, *, folder_id: str, name: str, docx_bytes: bytes) -> None:
        self.google_docs[(folder_id, name)] = docx_bytes

    def read_file(self, *, folder_id: str, filename: str) -> tuple[bytes, str]:
        key = (folder_id, filename)
        if key in self._preload:
            return self._preload[key]
        if key in self.texts:
            return self.texts[key][0].encode("utf-8"), "text/markdown"
        raise FileNotFoundError(filename)


def make_header() -> ContactHeader:
    return ContactHeader(
        name="Alfredo Gutierrez",
        location="Austin, TX",
        email="a@example.com",
        phone="+1 555 0100",
        links=("linkedin.com/in/x",),
    )


class FakeAuditLog:
    """In-memory AuditLog. Implements only what tests need."""

    def __init__(self, records: list[ApplicationRecord] | None = None) -> None:
        self.records: list[ApplicationRecord] = list(records or [])
        self.status_updates: list[tuple[str, str]] = []

    def find(
        self, *, company: str, role: str, jd_hash: str = ""
    ) -> ApplicationRecord | None:
        for rec in self.records:
            if jd_hash and rec.jd_hash == jd_hash:
                return rec
            if (
                rec.company.casefold() == company.casefold()
                and rec.role.casefold() == role.casefold()
            ):
                return rec
        return None

    def append(self, record: ApplicationRecord) -> None:
        self.records.append(record)

    def list_all(self) -> list[ApplicationRecord]:
        return list(self.records)

    def update_status(self, *, folder_id: str, status: str) -> None:
        for i, rec in enumerate(self.records):
            if rec.folder_id == folder_id:
                # Frozen dataclass — replace in place via dataclasses.replace
                # would import dataclasses; the test only inspects status_updates,
                # so we record the call and mutate a fresh copy.
                from dataclasses import replace

                self.records[i] = replace(rec, status=status)
                self.status_updates.append((folder_id, status))
                return
        raise RecordNotFoundError(folder_id)
