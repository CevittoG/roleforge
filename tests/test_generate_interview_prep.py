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
    uc = GenerateInterviewPrep(docs=FakeExperienceDocs(), llm=llm, store=store)

    uc(folder_id=_FOLDER)

    # Read the JD back and fed it to the focused prompt.
    assert llm.prep_calls and llm.prep_calls[0][1].text == "Senior Data Engineer JD"
    # Wrote the prep markdown into the same folder.
    assert store.texts[(_FOLDER, INTERVIEW_PREP_MD)][0] == "## Likely questions\n- ..."


def test_missing_jd_raises() -> None:
    uc = GenerateInterviewPrep(
        docs=FakeExperienceDocs(), llm=FakeLLM(), store=FakeOutputStore()
    )
    with pytest.raises(FileNotFoundError):
        uc(folder_id="nonexistent")
