"""Row-lookup logic for GoogleSheetsAudit.update_status. The Google client
is mocked — we only assert the call shape and the column-D target row."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.adapters.google_sheets import GoogleSheetsAudit
from app.usecases.errors import RecordNotFoundError


def _make_adapter(folder_rows: list[list[str]]) -> tuple[GoogleSheetsAudit, MagicMock]:
    svc = MagicMock()
    svc.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
        "values": folder_rows
    }
    adapter = GoogleSheetsAudit.__new__(GoogleSheetsAudit)
    adapter._svc = svc
    adapter._sheet_id = "sheet-1"
    adapter._tab = "Applications"
    adapter._skills_tab = "Skills"
    return adapter, svc


def test_update_status_writes_to_matching_row() -> None:
    # Row offset 0 = sheet row 2; row offset 2 = sheet row 4.
    adapter, svc = _make_adapter([["folder-a"], ["folder-b"], ["folder-c"]])

    adapter.update_status(folder_id="folder-c", status="Applied")

    update_call = svc.spreadsheets.return_value.values.return_value.update
    update_call.assert_called_once()
    kwargs = update_call.call_args.kwargs
    assert kwargs["range"] == "Applications!D4"
    assert kwargs["valueInputOption"] == "RAW"
    assert kwargs["body"] == {"values": [["Applied"]]}


def test_update_status_unknown_folder_id_raises() -> None:
    adapter, svc = _make_adapter([["folder-a"], ["folder-b"]])

    with pytest.raises(RecordNotFoundError):
        adapter.update_status(folder_id="missing", status="Applied")

    svc.spreadsheets.return_value.values.return_value.update.assert_not_called()
