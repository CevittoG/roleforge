"""DownloadFile: traceable filenames (Name-Role-Date-Artifact.ext) with a safe
fallback to the static DOWNLOADABLE name."""
from __future__ import annotations

import pytest

from app.usecases.download_file import DownloadFile
from tests.conftest import FakeOutputStore


def _store_with_resume() -> FakeOutputStore:
    return FakeOutputStore(preload={("f", "Resume"): (b"PDFBYTES", "application/pdf")})


def test_filename_uses_name_role_date_when_provided() -> None:
    dl = DownloadFile(store=_store_with_resume(), candidate_name="Alfredo Gutierrez")
    _data, mime, name = dl(
        folder_id="f", file_key="resume",
        role="Senior Data Engineer", date="2026-06-13T12:00:00+00:00",
    )
    assert mime == "application/pdf"
    assert name == "Alfredo_Gutierrez-Senior_Data_Engineer-2026-06-13-Resume.pdf"


def test_filename_for_markdown_artifact() -> None:
    store = FakeOutputStore()
    store.save_text(folder_id="f", filename="Match_Report.md", text="x")
    dl = DownloadFile(store=store, candidate_name="Alfredo Gutierrez")
    _d, _m, name = dl(folder_id="f", file_key="match_report", role="Data Eng", date="2026-06-13")
    assert name == "Alfredo_Gutierrez-Data_Eng-2026-06-13-Match_Report.md"


def test_falls_back_to_static_name_without_role_or_date() -> None:
    dl = DownloadFile(store=_store_with_resume(), candidate_name="Alfredo Gutierrez")
    _d, _m, name = dl(folder_id="f", file_key="resume")
    assert name == "Resume.pdf"


def test_falls_back_when_candidate_name_blank() -> None:
    dl = DownloadFile(store=_store_with_resume(), candidate_name="")
    _d, _m, name = dl(folder_id="f", file_key="resume", role="Eng", date="2026-06-13")
    assert name == "Resume.pdf"


def test_bad_date_falls_back() -> None:
    dl = DownloadFile(store=_store_with_resume(), candidate_name="Alfredo Gutierrez")
    _d, _m, name = dl(folder_id="f", file_key="resume", role="Eng", date="not-a-date")
    assert name == "Resume.pdf"


def test_unknown_key_raises() -> None:
    dl = DownloadFile(store=FakeOutputStore(), candidate_name="X")
    with pytest.raises(KeyError):
        dl(folder_id="f", file_key="bogus")
