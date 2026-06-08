"""Smoke test: load the experience .md files from the Drive folder.

Run:
    python -m scripts.smoke_experience_docs

Prints the first 500 chars of the concatenated experience corpus and its
total length. Empty output usually means the experience folder wasn't
created or opened through the OAuth token — `drive.file` scope only sees
files the token has touched. See README § Google auth.
"""
from __future__ import annotations

from app.adapters.experience_docs import DriveExperienceDocs
from app.config import get_settings

PREVIEW_CHARS = 500


def main() -> None:
    docs = DriveExperienceDocs(get_settings())
    body = docs.load_concatenated()
    if not body:
        print(
            "WARNING: concatenated experience corpus is EMPTY.\n"
            "Likely cause: the Drive folder referenced by "
            "DRIVE_EXPERIENCE_FOLDER_ID was not created or opened with this "
            "OAuth token. Re-create it via the app account, then put the new "
            "folder ID into .env. See README step 5."
        )
        return
    print(f"Loaded {len(body):,} chars total. First {PREVIEW_CHARS}:")
    print("-" * 60)
    print(body[:PREVIEW_CHARS])
    print("-" * 60)


if __name__ == "__main__":
    main()
