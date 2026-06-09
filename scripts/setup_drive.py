"""Create the two Drive folders the app needs, via the OAuth token.

Because the app uses drive.file scope, the token can only access files it
created through itself. Folders made in the Drive UI are invisible to it.
This script creates both folders via the API so the token owns them.

Run:
    python -m scripts.setup_drive

Prints the IDs of both folders. Paste them into .env, then upload your
experience .md files via:

    python -m scripts.upload_experience_docs <local-dir>

Drag-and-drop in the Drive UI will NOT work: the drive.file scope hides any
file the token didn't create or open, so the API has to do the upload.

You can freely move or rename the folders in Drive later; the ID never changes.
"""
from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build

from app.adapters.google_auth import build_credentials
from app.config import get_settings

FOLDER_MIME = "application/vnd.google-apps.folder"


def _create_folder(svc: Any, name: str) -> tuple[str, str]:
    """Create a top-level Drive folder; return (id, webViewLink)."""
    f = svc.files().create(
        body={"name": name, "mimeType": FOLDER_MIME},
        fields="id,webViewLink",
    ).execute()
    fid = f["id"]
    url = f.get("webViewLink", f"https://drive.google.com/drive/folders/{fid}")
    return fid, url


def main() -> None:
    svc = build("drive", "v3", credentials=build_credentials(get_settings()),
                cache_discovery=False)

    exp_id, exp_url = _create_folder(svc, "Experience Docs")
    out_id, out_url = _create_folder(svc, "Job Applications")

    print("Created both folders. Add these to .env:\n")
    print(f"  DRIVE_EXPERIENCE_FOLDER_ID={exp_id}")
    print(f"  DRIVE_OUTPUT_ROOT_FOLDER_ID={out_id}")
    print(f"\nExperience Docs : {exp_url}")
    print(f"Job Applications: {out_url}")
    print(
        "\nNext: open the Experience Docs URL above and upload your career "
        ".md files (drag-and-drop works in the Drive UI).\n"
        "Then re-run: python -m scripts.smoke_experience_docs"
    )


if __name__ == "__main__":
    main()
