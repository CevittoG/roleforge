from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import ApplicationStatus
from app.domain.ports import AuditLog


class InvalidStatusError(ValueError):
    """Raised when the requested status is not in ApplicationStatus."""

    def __init__(self, value: str) -> None:
        self.value = value
        allowed = ", ".join(s.value for s in ApplicationStatus)
        super().__init__(f"invalid status {value!r}; expected one of: {allowed}")


@dataclass(frozen=True)
class UpdateApplicationStatus:
    audit_log: AuditLog

    def __call__(self, *, folder_id: str, status: str) -> None:
        try:
            normalized = ApplicationStatus(status).value
        except ValueError as exc:
            raise InvalidStatusError(status) from exc
        self.audit_log.update_status(folder_id=folder_id, status=normalized)
