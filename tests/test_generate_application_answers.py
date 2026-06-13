"""On-demand application answers: reads the JD back, runs the focused prompt,
renders the enumerated .docx, and writes Application_Questions.docx into the
same folder."""
from __future__ import annotations

import pytest

from app.domain.models import (
    APPLICATION_QUESTIONS_DOCX,
    DOCX_MIME,
    JOB_DESCRIPTION_MD,
    ApplicationAnswer,
)
from app.usecases.generate_application_answers import GenerateApplicationAnswers
from tests.conftest import FakeExperienceDocs, FakeLLM, FakeOutputStore, FakeRenderer

_FOLDER = "Acme__Data Engineer"


def test_answers_from_saved_jd() -> None:
    store = FakeOutputStore(
        preload={(_FOLDER, JOB_DESCRIPTION_MD): (b"Senior Data Engineer JD", "text/markdown")}
    )
    llm = FakeLLM(answers=(ApplicationAnswer("Why us?", "Because."),))
    renderer = FakeRenderer()
    uc = GenerateApplicationAnswers(
        docs=FakeExperienceDocs(), llms={"anthropic": llm}, renderer=renderer, store=store,
        default_provider="anthropic",
    )

    uc(folder_id=_FOLDER, questions="Why us?")

    # Read the JD back and fed it + the questions to the focused prompt.
    assert llm.answer_calls
    assert llm.answer_calls[0][1].text == "Senior Data Engineer JD"
    assert llm.answer_calls[0][2] == "Why us?"
    # The structured answers were rendered, then saved as a .docx.
    assert renderer.answers == (ApplicationAnswer("Why us?", "Because."),)
    data, mime = store.bytes_files[(_FOLDER, APPLICATION_QUESTIONS_DOCX)]
    assert data == b"APPLICATION-QUESTIONS-DOCX"
    assert mime == DOCX_MIME


def test_provider_selects_the_right_llm() -> None:
    store = FakeOutputStore(
        preload={(_FOLDER, JOB_DESCRIPTION_MD): (b"JD", "text/markdown")}
    )
    anthropic_llm, gemini_llm = FakeLLM(), FakeLLM()
    uc = GenerateApplicationAnswers(
        docs=FakeExperienceDocs(),
        llms={"anthropic": anthropic_llm, "gemini": gemini_llm},
        renderer=FakeRenderer(),
        store=store,
        default_provider="anthropic",
    )

    uc(folder_id=_FOLDER, questions="Q", provider="gemini")
    assert gemini_llm.answer_calls and not anthropic_llm.answer_calls


def test_missing_jd_raises() -> None:
    uc = GenerateApplicationAnswers(
        docs=FakeExperienceDocs(), llms={"anthropic": FakeLLM()}, renderer=FakeRenderer(),
        store=FakeOutputStore(), default_provider="anthropic",
    )
    with pytest.raises(FileNotFoundError):
        uc(folder_id="nonexistent", questions="Q")
