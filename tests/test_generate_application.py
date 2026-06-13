"""GenerateApplication orchestration: writes the right artifacts, injects the
config contact header, and no longer produces interview prep."""
from __future__ import annotations

from dataclasses import replace

from app.domain.models import (
    APPLICATION_QUESTIONS_DOCX,
    COVER_LETTER_TXT,
    DOCX_MIME,
    INTERVIEW_PREP_MD,
    JOB_DESCRIPTION_MD,
    MATCH_REPORT_MD,
    RESUME_DOC,
    ApplicationAnswer,
)
from app.usecases.generate_application import GenerateApplication, GenerationRequest
from tests.conftest import (
    FakeAuditLog,
    FakeExperienceDocs,
    FakeLLM,
    FakeOutputStore,
    FakeRenderer,
    make_generated,
    make_header,
)


def _build() -> tuple[GenerateApplication, FakeOutputStore, FakeLLM, FakeRenderer]:
    store = FakeOutputStore()
    llm = FakeLLM()
    renderer = FakeRenderer()
    uc = GenerateApplication(
        docs=FakeExperienceDocs(),
        llms={"anthropic": llm},
        renderer=renderer,
        store=store,
        audit_log=FakeAuditLog(),
        default_provider="anthropic",
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


def test_no_questions_skips_application_questions_file() -> None:
    uc, store, llm, _renderer = _build()
    record = uc(GenerationRequest(raw_text="A job description."))

    # The (empty) questions string is threaded to the LLM...
    assert llm.generate_calls[0][3] == ""
    # ...and with no answers returned, no Application_Questions.docx is written.
    assert (record.folder_id, APPLICATION_QUESTIONS_DOCX) not in store.bytes_files


def test_questions_are_answered_and_saved() -> None:
    content = replace(
        make_generated(),
        application_answers=(ApplicationAnswer(question="Why us?", answer="Because."),),
    )
    store = FakeOutputStore()
    llm = FakeLLM(content=content)
    uc = GenerateApplication(
        docs=FakeExperienceDocs(),
        llms={"anthropic": llm},
        renderer=FakeRenderer(),
        store=store,
        audit_log=FakeAuditLog(),
        default_provider="anthropic",
        resume_header=make_header(),
    )
    record = uc(GenerationRequest(raw_text="JD", application_questions="Why us?"))

    # Questions reach the same generate call (reusing context).
    assert llm.generate_calls[0][3] == "Why us?"
    # Application_Questions.docx is written from the rendered answers.
    data, mime = store.bytes_files[(record.folder_id, APPLICATION_QUESTIONS_DOCX)]
    assert data == b"APPLICATION-QUESTIONS-DOCX"
    assert mime == DOCX_MIME


def _build_multi() -> tuple[GenerateApplication, FakeLLM, FakeLLM]:
    """A use case wired with two providers, so routing can be asserted."""
    anthropic_llm, gemini_llm = FakeLLM(), FakeLLM()
    uc = GenerateApplication(
        docs=FakeExperienceDocs(),
        llms={"anthropic": anthropic_llm, "gemini": gemini_llm},
        renderer=FakeRenderer(),
        store=FakeOutputStore(),
        audit_log=FakeAuditLog(),
        default_provider="anthropic",
        resume_header=make_header(),
    )
    return uc, anthropic_llm, gemini_llm


def test_explicit_provider_routes_to_that_llm() -> None:
    uc, anthropic_llm, gemini_llm = _build_multi()
    uc(GenerationRequest(raw_text="A job description.", provider="gemini"))
    assert gemini_llm.generate_calls and not anthropic_llm.generate_calls


def test_none_provider_uses_default() -> None:
    uc, anthropic_llm, gemini_llm = _build_multi()
    uc(GenerationRequest(raw_text="A job description."))
    assert anthropic_llm.generate_calls and not gemini_llm.generate_calls


def test_unknown_provider_falls_back_to_default() -> None:
    uc, anthropic_llm, gemini_llm = _build_multi()
    uc(GenerationRequest(raw_text="A job description.", provider="bogus"))
    assert anthropic_llm.generate_calls and not gemini_llm.generate_calls


def test_contact_header_comes_from_config_not_model() -> None:
    uc, _store, llm, renderer = _build()
    uc(GenerationRequest(raw_text="A job description."))

    # The candidate name is threaded to the LLM (for the cover-letter signature).
    assert llm.generate_calls[0][2] == "Alfredo Gutierrez"
    # The rendered resume carries the config header, regardless of model output.
    assert renderer.resume is not None
    assert renderer.resume.header.name == "Alfredo Gutierrez"
    assert renderer.resume.header.email == "a@example.com"
