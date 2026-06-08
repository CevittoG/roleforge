"""Google Drive adapter implementing OutputStore.

Folder layout: <output_root>/<Company>/<Role>/  with the four files inside.
Uses the `drive.file` scope (per-file), so it only ever touches files it
creates or opens.
"""
from __future__ import annotations

import io
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from app.adapters.google_auth import build_credentials
from app.config import Settings
from app.domain.models import FolderRef

_FOLDER_MIME = "application/vnd.google-apps.folder"


class GoogleDriveStore:
    def __init__(self, settings: Settings) -> None:
        self._svc = build("drive", "v3", credentials=build_credentials(settings),
                          cache_discovery=False)
        self._root = settings.drive_output_root_folder_id

    # --- OutputStore ---
    def ensure_folder(self, *, company: str, role: str) -> FolderRef:
        company_id = self._child_folder(self._root, company)
        role_id = self._child_folder(company_id, role)
        return FolderRef(id=role_id, url=f"https://drive.google.com/drive/folders/{role_id}")

    def save_bytes(self, *, folder_id: str, filename: str, data: bytes, mime: str) -> None:
        self._upsert(folder_id, filename, MediaIoBaseUpload(io.BytesIO(data), mimetype=mime))

    def save_text(self, *, folder_id: str, filename: str, text: str) -> None:
        media = MediaIoBaseUpload(io.BytesIO(text.encode("utf-8")), mimetype="text/markdown")
        self._upsert(folder_id, filename, media)

    def read_file(self, *, folder_id: str, filename: str) -> tuple[bytes, str]:
        file_id, mime = self._find_file(folder_id, filename)
        if file_id is None:
            raise FileNotFoundError(filename)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, self._svc.files().get_media(fileId=file_id))
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf.getvalue(), mime or "application/octet-stream"

    # --- helpers ---
    def _child_folder(self, parent_id: str, name: str) -> str:
        existing = self._query_one(
            f"mimeType='{_FOLDER_MIME}' and name={_q(name)} "
            f"and '{parent_id}' in parents and trashed=false"
        )
        if existing:
            return str(existing["id"])
        created = self._svc.files().create(
            body={"name": name, "mimeType": _FOLDER_MIME, "parents": [parent_id]},
            fields="id",
        ).execute()
        return str(created["id"])

    def _find_file(self, folder_id: str, name: str) -> tuple[str | None, str | None]:
        f = self._query_one(
            f"name={_q(name)} and '{folder_id}' in parents and trashed=false",
            fields="files(id,mimeType)",
        )
        return (f["id"], f.get("mimeType")) if f else (None, None)

    def _upsert(self, folder_id: str, filename: str, media: MediaIoBaseUpload) -> None:
        file_id, _ = self._find_file(folder_id, filename)
        if file_id:  # overwrite content of the existing file
            self._svc.files().update(fileId=file_id, media_body=media).execute()
        else:
            self._svc.files().create(
                body={"name": filename, "parents": [folder_id]}, media_body=media, fields="id"
            ).execute()

    def _query_one(self, q: str, fields: str = "files(id)") -> dict[str, Any] | None:
        res = self._svc.files().list(
            q=q, spaces="drive", fields=fields, pageSize=1
        ).execute()
        files = res.get("files", [])
        return files[0] if files else None


def _q(value: str) -> str:
    """Quote a value for a Drive query, escaping single quotes."""
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
