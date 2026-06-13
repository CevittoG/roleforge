"""On-demand interview prep: reads the JD back, runs the focused prompt, writes
Interview_Prep.md into the same folder."""
from __future__ import annotations

import pytest

from app.domain.models import INTERVIEW_PREP_MD, JOB_DESCRIPTION_MD
from app.usecases.generate_interview_prep import GenerateInterviewPrep
from tests.conftest import FakeExperienceDocs, FakeLLM, FakeOutputStore

_FOLDER = "Acme__Data Engineer"


def test_generates_prep_from_saved_jd() -> None:
    store = FakeOutputStore(
        preload={(_FOLDER, JOB_DESCRIPTION_MD): (b"Senior Data Engineer JD", "text/markdown")}
    )
    llm = FakeLLM(prep_md="## Likely questions\n- ...")
    uc = GenerateInterviewPrep(
        docs=FakeExperienceDocs(), llms={"anthropic": llm}, store=store,
        default_provider="anthropic",
    )

    uc(folder_id=_FOLDER)

    # Read the JD back and fed it to the focused prompt.
    assert llm.prep_calls and llm.prep_calls[0][1].text == "Senior Data Engineer JD"
    # Wrote the prep markdown into the same folder.
    assert store.texts[(_FOLDER, INTERVIEW_PREP_MD)][0] == "## Likely questions\n- ..."


def test_provider_selects_the_right_llm() -> None:
    store = FakeOutputStore(
        preload={(_FOLDER, JOB_DESCRIPTION_MD): (b"Senior Data Engineer JD", "text/markdown")}
    )
    anthropic_llm, gemini_llm = FakeLLM(), FakeLLM()
    uc = GenerateInterviewPrep(
        docs=FakeExperienceDocs(),
        llms={"anthropic": anthropic_llm, "gemini": gemini_llm},
        store=store,
        default_provider="anthropic",
    )

    uc(folder_id=_FOLDER, provider="gemini")
    assert gemini_llm.prep_calls and not anthropic_llm.prep_calls

    uc(folder_id=_FOLDER)  # None -> default
    assert anthropic_llm.prep_calls


def test_missing_jd_raises() -> None:
    uc = GenerateInterviewPrep(
        docs=FakeExperienceDocs(), llms={"anthropic": FakeLLM()}, store=FakeOutputStore(),
        default_provider="anthropic",
    )
    with pytest.raises(FileNotFoundError):
        uc(folder_id="nonexistent")
