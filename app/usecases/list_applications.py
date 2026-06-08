from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import ApplicationRecord
from app.domain.ports import AuditLog


@dataclass(frozen=True)
class ListApplications:
    audit_log: AuditLog

    def __call__(self) -> list[ApplicationRecord]:
        return self.audit_log.list_all()
