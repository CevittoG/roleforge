"""Use-case level errors, mapped to HTTP in the web layer."""
from __future__ import annotations

from app.domain.models import ApplicationRecord


class DuplicateApplicationError(Exception):
    """Raised when a Company+Role record already exists and overwrite wasn't confirmed."""

    def __init__(self, existing: ApplicationRecord) -> None:
        self.existing = existing
        super().__init__(f"Application already exists for {existing.company} / {existing.role}")
