from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import DOWNLOADABLE
from app.domain.ports import OutputStore


@dataclass(frozen=True)
class DownloadFile:
    store: OutputStore

    def __call__(self, *, folder_id: str, file_key: str) -> tuple[bytes, str, str]:
        """Return (data, mime, download_filename). `file_key` is a DOWNLOADABLE
        key. The resume Doc is exported to PDF by the store; its download name
        differs from its Drive name (see DOWNLOADABLE)."""
        if file_key not in DOWNLOADABLE:
            raise KeyError(file_key)
        drive_filename, download_filename = DOWNLOADABLE[file_key]
        data, mime = self.store.read_file(folder_id=folder_id, filename=drive_filename)
        return data, mime, download_filename
