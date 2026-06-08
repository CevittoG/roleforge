"""Shared Google credentials built from an own-account OAuth refresh token."""
from __future__ import annotations

from google.oauth2.credentials import Credentials

from app.config import GOOGLE_SCOPES, Settings


def build_credentials(settings: Settings) -> Credentials:
    # google-auth ships no type stubs, so strict mypy flags the constructor as
    # untyped. The call shape is stable; no value in chasing third-party stubs.
    return Credentials(  # type: ignore[no-untyped-call]
        token=None,
        refresh_token=settings.google_refresh_token,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_uri=settings.google_token_uri,
        scopes=GOOGLE_SCOPES,
    )
