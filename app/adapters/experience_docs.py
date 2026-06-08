"""ExperienceDocStore adapter: reads the experience .md files from the Drive
folder so docs can be edited anywhere without redeploying."""
from __future__ import annotations

import io

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.adapters.google_auth import build_credentials
from app.config import Settings


class DriveExperienceDocs:
    def __init__(self, settings: Settings) -> None:
        self._svc = build("drive", "v3", credentials=build_credentials(settings),
                          cache_discovery=False)
        self._folder = settings.drive_experience_folder_id

    def load_concatenated(self) -> str:
        res = self._svc.files().list(
            q=f"'{self._folder}' in parents and trashed=false and "
              f"(mimeType='text/markdown' or mimeType='text/plain')",
            fields="files(id,name)", orderBy="name",
        ).execute()
        parts: list[str] = []
        for f in res.get("files", []):
            parts.append(f"# === {f['name']} ===\n{self._download(f['id'])}")
        return "\n\n".join(parts)

    def _download(self, file_id: str) -> str:
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, self._svc.files().get_media(fileId=file_id))
        done = False
        while not done:
            _, done = dl.next_chunk()
        return buf.getvalue().decode("utf-8", errors="replace")
