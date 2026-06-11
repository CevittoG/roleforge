"""GenerateApplication orchestration: writes the right artifacts, injects the
config contact header, and no longer produces interview prep."""
from __future__ import annotations

from app.domain.models import (
    COVER_LETTER_TXT,
    INTERVIEW_PREP_MD,
    JOB_DESCRIPTION_MD,
    MATCH_REPORT_MD,
    RESUME_DOC,
)
from app.usecases.generate_application import GenerateApplication, GenerationRequest
from tests.conftest import (
    FakeAuditLog,
    FakeExperienceDocs,
    FakeLLM,
    FakeOutputStore,
    FakeRenderer,
    make_header,
)


def _build() -> tuple[GenerateApplication, FakeOutputStore, FakeLLM, FakeRenderer]:
    store = FakeOutputStore()
    llm = FakeLLM()
    renderer = FakeRenderer()
    uc = GenerateApplication(
        docs=FakeExperienceDocs(),
        llm=llm,
        renderer=renderer,
        store=store,
        audit_log=FakeAuditLog(),
        resume_header=make_header(),
    )
    return uc, store, llm, renderer


def test_generate_writes_doc_txt_and_no_interview_prep() -> None:
    uc, store, llm, renderer = _build()
    record = uc(GenerationRequest(raw_text="A job description."))

    folder_id = record.folder_id

    # Resume saved as a Google Doc (converted from docx bytes), not a PDF.
    assert (folder_id, RESUME_DOC) in store.google_docs
    assert store.google_docs[(folder_id, RESUME_DOC)] == b"DOCX-BYTES"

    # Cover letter is plain text.
    assert store.texts[(folder_id, COVER_LETTER_TXT)] == ("COVER-TEXT\n", "text/plain")

    # JD + match report still written; interview prep is NOT.
    assert (folder_id, JOB_DESCRIPTION_MD) in store.texts
    assert (folder_id, MATCH_REPORT_MD) in store.texts
    assert (folder_id, INTERVIEW_PREP_MD) not in store.texts


def test_contact_header_comes_from_config_not_model() -> None:
    uc, _store, llm, renderer = _build()
    uc(GenerationRequest(raw_text="A job description."))

    # The candidate name is threaded to the LLM (for the cover-letter signature).
    assert llm.generate_calls[0][2] == "Alfredo Gutierrez"
    # The rendered resume carries the config header, regardless of model output.
    assert renderer.resume is not None
    assert renderer.resume.header.name == "Alfredo Gutierrez"
    assert renderer.resume.header.email == "a@example.com"
