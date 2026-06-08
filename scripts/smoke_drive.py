"""Smoke test: round-trip a small file through the GoogleDriveStore.

Run:
    python -m scripts.smoke_drive

Creates `<output_root>/Acme/Smoke Test/`, uploads a small text file, reads
it back, and asserts the content matches. Prints the folder URL so the
user can delete it manually afterward.
"""
from __future__ import annotations

from app.adapters.google_drive import GoogleDriveStore
from app.config import get_settings

FILENAME = "roleforge_smoke.txt"
PAYLOAD = "Roleforge smoke test — safe to delete.\n"


def main() -> None:
    store = GoogleDriveStore(get_settings())
    folder = store.ensure_folder(company="Acme", role="Smoke Test")
    print(f"Folder ready: {folder.url}")

    store.save_text(folder_id=folder.id, filename=FILENAME, text=PAYLOAD)
    data, mime = store.read_file(folder_id=folder.id, filename=FILENAME)
    decoded = data.decode("utf-8")
    assert decoded == PAYLOAD, f"round-trip mismatch: {decoded!r} vs {PAYLOAD!r}"
    print(f"Round-trip OK ({len(data)} bytes, mime={mime}).")
    print(
        f"\nDelete this when done: open {folder.url} and remove the "
        "'Acme/Smoke Test/' subtree from Drive."
    )


if __name__ == "__main__":
    main()
