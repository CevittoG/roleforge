from __future__ import annotations

import pytest

from app.domain.models import ApplicationRecord
from app.usecases.errors import RecordNotFoundError
from app.usecases.update_application_status import (
    InvalidStatusError,
    UpdateApplicationStatus,
)
from tests.conftest import FakeAuditLog


def _make_record(folder_id: str, status: str = "Generated") -> ApplicationRecord:
    return ApplicationRecord(
        date="2026-06-09T10:00:00+00:00",
        company="Acme",
        role="Engineer",
        status=status,
        work_mode="remote",
        location=None,
        pay=None,
        benefits=None,
        jd_source_url=None,
        folder_url=f"https://drive.google.com/drive/folders/{folder_id}",
        folder_id=folder_id,
    )


def test_update_happy_path_writes_through_to_audit_log() -> None:
    log = FakeAuditLog([_make_record("folder-1")])
    update = UpdateApplicationStatus(audit_log=log)

    update(folder_id="folder-1", status="Applied")

    assert log.records[0].status == "Applied"
    assert log.status_updates == [("folder-1", "Applied")]


def test_update_invalid_status_raises_before_hitting_log() -> None:
    log = FakeAuditLog([_make_record("folder-1")])
    update = UpdateApplicationStatus(audit_log=log)

    with pytest.raises(InvalidStatusError):
        update(folder_id="folder-1", status="Pending")

    assert log.status_updates == []
    assert log.records[0].status == "Generated"


def test_update_unknown_folder_id_raises_record_not_found() -> None:
    log = FakeAuditLog([_make_record("folder-1")])
    update = UpdateApplicationStatus(audit_log=log)

    with pytest.raises(RecordNotFoundError):
        update(folder_id="missing", status="Applied")
