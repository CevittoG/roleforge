from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import DOWNLOADABLE
from app.domain.ports import OutputStore


@dataclass(frozen=True)
class DownloadFile:
    store: OutputStore

    def __call__(self, *, folder_id: str, file_key: str) -> tuple[bytes, str, str]:
        """Return (data, mime, filename). `file_key` is one of DOWNLOADABLE keys."""
        if file_key not in DOWNLOADABLE:
            raise KeyError(file_key)
        filename = DOWNLOADABLE[file_key]
        data, mime = self.store.read_file(folder_id=folder_id, filename=filename)
        return data, mime, filename
