"""Shared fixtures and fakes for the test suite.

The fakes satisfy the structural ports in ``app/domain/ports.py`` so the core
stays network-free and credential-free in tests.
"""
from __future__ import annotations

from app.domain.models import ApplicationRecord
from app.usecases.errors import RecordNotFoundError


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
