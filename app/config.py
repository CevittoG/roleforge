"""Application settings. All values come from the environment (Render secret files).

Nothing here has a sensitive default — secrets MUST be injected at runtime.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Google scopes — least-privilege within the "edit experience docs from the
# Drive UI" workflow the user wants.
#   drive.readonly — read-only on every file the user owns or has access to.
#                    This is what lets the token see experience docs the user
#                    drag-and-drops into the Experience Docs folder; without
#                    it, drive.file only sees files the app itself created.
#   drive.file     — write access, but ONLY to files the app creates or opens.
#                    Outputs (resumes, cover letters, etc.) go through this.
#   spreadsheets   — append/read the audit log.
# Never request the bare `drive` scope: that grants write to every file in
# the user's Drive, which we have no use for.
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Anthropic ---
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_max_tokens: int = 12_000

    # --- Google OAuth (own-account refresh token; see README) ---
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    google_token_uri: str = "https://oauth2.googleapis.com/token"

    # --- Google resources ---
    drive_experience_folder_id: str          # folder holding the experience .md docs
    drive_output_root_folder_id: str          # "Job Applications" root folder
    sheet_id: str                             # audit / history spreadsheet
    sheet_tab: str = "Applications"
    sheet_skills_tab: str = "Skills"

    # --- Cloudflare Access (edge auth) ---
    cf_access_team_domain: str                # e.g. "yourteam.cloudflareaccess.com"
    cf_access_aud: str                        # Access application AUD tag

    # --- Origin lock (defense-in-depth; see README) ---
    origin_shared_secret: str                 # header value Cloudflare injects

    # --- Guardrails ---
    max_jd_chars: int = 30_000                # caps token cost + abuse
    url_fetch_timeout_s: float = 8.0
    url_fetch_max_bytes: int = 2_000_000

    environment: str = Field(default="production")
    # Default ON. Only flip to false in a local .env to skip the Cloudflare
    # Access JWT + origin-secret checks while developing.
    auth_required: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
