"""Provider registry + effective-default behavior that /api/config relies on."""
from __future__ import annotations

from app.config import Settings
from app.container import _build_llms, effective_default_provider


def _settings(*, gemini_api_key: str = "", default_llm_provider: str = "anthropic") -> Settings:
    """A fully-populated Settings with dummy creds, varying only the two fields
    these tests care about. Explicit kwargs override any local .env."""
    return Settings(
        anthropic_api_key="sk-ant-test",
        google_client_id="cid",
        google_client_secret="csecret",
        google_refresh_token="rtok",
        drive_experience_folder_id="exp",
        drive_output_root_folder_id="out",
        sheet_id="sheet",
        cf_access_team_domain="team.cloudflareaccess.com",
        cf_access_aud="aud",
        origin_shared_secret="secret",
        gemini_api_key=gemini_api_key,
        default_llm_provider=default_llm_provider,
    )


def test_registry_has_only_anthropic_without_gemini_key() -> None:
    assert list(_build_llms(_settings())) == ["anthropic"]


def test_registry_adds_gemini_when_key_present() -> None:
    assert set(_build_llms(_settings(gemini_api_key="g-key"))) == {"anthropic", "gemini"}


def test_default_falls_back_when_chosen_provider_unavailable() -> None:
    s = _settings(gemini_api_key="", default_llm_provider="gemini")
    assert effective_default_provider(s, ["anthropic"]) == "anthropic"


def test_default_honored_when_available() -> None:
    s = _settings(gemini_api_key="g-key", default_llm_provider="gemini")
    assert effective_default_provider(s, ["anthropic", "gemini"]) == "gemini"
