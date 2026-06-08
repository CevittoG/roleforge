"""Bootstrap a Google OAuth refresh token for the own-account flow.

Reads GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET from `.env` (Desktop OAuth
client), runs the InstalledAppFlow against a loopback redirect, prints the
refresh token to stdout. Paste it into `.env` as GOOGLE_REFRESH_TOKEN.

Run:
    python -m scripts.get_refresh_token

Requires the OAuth consent screen to be set to "In production" — otherwise
the issued refresh token expires after 7 days. See README.
"""
from __future__ import annotations

import sys

from google_auth_oauthlib.flow import InstalledAppFlow
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config import GOOGLE_SCOPES


class _BootstrapSettings(BaseSettings):
    """Minimal settings for the bootstrap: only the two fields we need.

    Uses its own loader so the script works on a fresh clone where the rest
    of `.env` is still empty placeholders.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    google_client_id: str
    google_client_secret: str


def main() -> None:
    s = _BootstrapSettings()
    client_config = {
        "installed": {
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=GOOGLE_SCOPES)
    # access_type=offline + prompt=consent guarantees a refresh_token even if
    # the user has consented to this client before.
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
        open_browser=True,
    )
    if not creds.refresh_token:
        print("ERROR: no refresh_token returned. Did Google skip the consent "
              "screen? Revoke this client at "
              "https://myaccount.google.com/permissions and retry.",
              file=sys.stderr)
        sys.exit(1)
    print(creds.refresh_token)


if __name__ == "__main__":
    main()
