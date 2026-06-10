"""Use-case level errors, mapped to HTTP in the web layer."""
from __future__ import annotations

from app.domain.models import ApplicationRecord


class DuplicateApplicationError(Exception):
    """Raised when a Company+Role record already exists and overwrite wasn't confirmed."""

    def __init__(self, existing: ApplicationRecord) -> None:
        self.existing = existing
        super().__init__(f"Application already exists for {existing.company} / {existing.role}")


class RecordNotFoundError(Exception):
    """Raised when a status update targets a folder_id with no matching audit row."""

    def __init__(self, folder_id: str) -> None:
        self.folder_id = folder_id
        super().__init__(f"No application row found for folder_id={folder_id!r}")
