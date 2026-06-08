"""Single responsibility: does a record for this Company+Role already exist?"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import ApplicationRecord
from app.domain.ports import AuditLog


@dataclass(frozen=True)
class CheckDuplicate:
    audit_log: AuditLog

    def __call__(self, *, company: str, role: str) -> ApplicationRecord | None:
        return self.audit_log.find(company=company, role=role)
