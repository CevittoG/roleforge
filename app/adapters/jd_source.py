"""JDSource adapter: paste-first, URL as best-effort (LinkedIn/Workday block bots)."""
from __future__ import annotations

import re

from app.config import Settings
from app.domain.models import JobDescription
from app.security.ssrf import safe_fetch

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\n\s*\n\s*\n+")


class JDSourceAdapter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def resolve(self, *, raw_text: str | None, url: str | None) -> JobDescription:
        if raw_text:
            return JobDescription(text=raw_text.strip(), source_url=url)
        if not url:
            raise ValueError("provide JD text or a URL")
        html = safe_fetch(
            url,
            timeout_s=self._settings.url_fetch_timeout_s,
            max_bytes=self._settings.url_fetch_max_bytes,
        )
        # Minimal extraction. Swap for trafilatory/readability if you want
        # better main-content isolation — interface stays the same.
        text = _WS_RE.sub("\n\n", _TAG_RE.sub(" ", html)).strip()
        return JobDescription(text=text, source_url=url)
