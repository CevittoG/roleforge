"""Upload local experience docs into the Drive Experience Docs folder.

Why this exists: the app uses the `drive.file` OAuth scope, which restricts
the token to files it created or opened. Files dragged into the folder via
the Drive UI are invisible to the token. This script uploads `.md` / `.txt`
files via the API so the token owns them — after which
`smoke_experience_docs` and the full generation pipeline can read them.

Run:
    python -m scripts.upload_experience_docs <local-dir>

For each file in <local-dir>, if a file with the same name already exists in
the folder (visible to the token), its content is overwritten in place.
Otherwise a new file is created. Idempotent — safe to re-run.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from app.adapters.google_auth import build_credentials
from app.config import get_settings

_MIME_BY_SUFFIX = {".md": "text/markdown", ".txt": "text/plain"}


def _find(svc: Any, folder_id: str, name: str) -> str | None:
    safe = name.replace("\\", "\\\\").replace("'", "\\'")
    res = svc.files().list(
        q=f"name='{safe}' and '{folder_id}' in parents and trashed=false",
        spaces="drive", fields="files(id)", pageSize=1,
    ).execute()
    files = res.get("files", [])
    return str(files[0]["id"]) if files else None


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit("Usage: python -m scripts.upload_experience_docs <local-dir>")
    src = Path(argv[0]).expanduser().resolve()
    if not src.is_dir():
        raise SystemExit(f"{src} is not a directory.")

    settings = get_settings()
    svc = build("drive", "v3", credentials=build_credentials(settings),
                cache_discovery=False)
    folder = settings.drive_experience_folder_id

    candidates = sorted(
        p for p in src.iterdir()
        if p.is_file() and p.suffix.lower() in _MIME_BY_SUFFIX
    )
    if not candidates:
        raise SystemExit(f"No .md / .txt files found in {src}.")

    print(f"Uploading {len(candidates)} file(s) to folder {folder}…")
    for p in candidates:
        mime = _MIME_BY_SUFFIX[p.suffix.lower()]
        data = p.read_bytes()
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime)
        existing = _find(svc, folder, p.name)
        if existing:
            svc.files().update(fileId=existing, media_body=media).execute()
            print(f"  updated {p.name}")
        else:
            svc.files().create(
                body={"name": p.name, "parents": [folder], "mimeType": mime},
                media_body=media, fields="id",
            ).execute()
            print(f"  created {p.name}")
    print("\nDone. Re-run: python -m scripts.smoke_experience_docs")


if __name__ == "__main__":
    main(sys.argv[1:])
