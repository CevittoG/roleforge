"""Smoke test: load the experience .md files from the Drive folder.

Run:
    python -m scripts.smoke_experience_docs

Prints the first 500 chars of the concatenated experience corpus and its
total length. Gives distinct messages for the two failure modes:
  - Folder inaccessible (drive.file scope, wrong ID, or stale .env)
  - Folder accessible but no .md / .txt files uploaded yet
"""
from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.adapters.experience_docs import DriveExperienceDocs
from app.adapters.google_auth import build_credentials
from app.config import get_settings

PREVIEW_CHARS = 500


def _folder_accessible(svc: Any, folder_id: str) -> bool:
    """Return True if the token can read this folder's metadata."""
    try:
        svc.files().get(fileId=folder_id, fields="id").execute()
        return True
    except HttpError:
        return False


def main() -> None:
    settings = get_settings()
    svc = build("drive", "v3", credentials=build_credentials(settings),
                cache_discovery=False)
    folder_id = settings.drive_experience_folder_id

    if not _folder_accessible(svc, folder_id):
        print(
            "ERROR: the token cannot access folder "
            f"DRIVE_EXPERIENCE_FOLDER_ID={folder_id!r}.\n"
            "\nLikely causes:\n"
            "  a) .env still has the old placeholder or a folder created in "
            "the Drive UI.\n"
            "  b) You ran setup_drive.py but didn't paste the new ID into .env.\n"
            "\nFix: run  python -m scripts.setup_drive  and update .env with "
            "the printed DRIVE_EXPERIENCE_FOLDER_ID."
        )
        return

    docs = DriveExperienceDocs(settings)
    body = docs.load_concatenated()

    if not body:
        print(
            "Folder is accessible but contains no .md or .txt files.\n"
            f"Open https://drive.google.com/drive/folders/{folder_id} "
            "and upload your experience .md files, then re-run this script."
        )
        return

    print(f"Loaded {len(body):,} chars total. First {PREVIEW_CHARS}:")
    print("-" * 60)
    print(body[:PREVIEW_CHARS])
    print("-" * 60)


if __name__ == "__main__":
    main()
