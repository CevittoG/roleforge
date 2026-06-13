from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.models import DOWNLOADABLE
from app.domain.ports import OutputStore

_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")
_ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


def _slug(value: str) -> str:
    """Collapse runs of non-alphanumerics to a single underscore. Doubles as a
    header-injection guard: the result is safe to drop into a Content-Disposition
    filename (no quotes, newlines, or path separators survive)."""
    return _NON_ALNUM.sub("_", value).strip("_")


@dataclass(frozen=True)
class DownloadFile:
    store: OutputStore
    candidate_name: str = ""

    def __call__(
        self,
        *,
        folder_id: str,
        file_key: str,
        role: str | None = None,
        date: str | None = None,
    ) -> tuple[bytes, str, str]:
        """Return (data, mime, download_filename). `file_key` is a DOWNLOADABLE
        key. When `role` and `date` are supplied (and a candidate name is
        configured), the suggested filename becomes
        ``<Name>-<Role>-<YYYY-MM-DD>-<Artifact>.<ext>``; otherwise it falls back
        to the static name in DOWNLOADABLE. The resume Doc is exported to PDF by
        the store, so its artifact/extension come from the static download name."""
        if file_key not in DOWNLOADABLE:
            raise KeyError(file_key)
        drive_filename, download_filename = DOWNLOADABLE[file_key]
        data, mime = self.store.read_file(folder_id=folder_id, filename=drive_filename)
        return data, mime, self._filename(download_filename, role, date)

    def _filename(self, static_name: str, role: str | None, date: str | None) -> str:
        name = _slug(self.candidate_name)
        role_slug = _slug(role or "")
        day = (date or "")[:10]  # YYYY-MM-DD prefix of an ISO timestamp
        if not (name and role_slug and _ISO_DAY.fullmatch(day)):
            return static_name
        artifact, _, ext = static_name.rpartition(".")
        artifact = artifact or static_name
        stem = f"{name}-{role_slug}-{day}-{artifact}"
        return f"{stem}.{ext}" if ext else stem
