"""Google Gemini transport for the shared LLM adapter.

The shared prompt + parsing live in `llm_base.BaseLLMAdapter`; this module
supplies only the Gemini API call. Gemini has a free tier, which is why it's
offered alongside Anthropic.

Caching note: Anthropic's adapter cache-flags the system + experience-docs
blocks explicitly. Gemini flash models apply *implicit* prefix caching
automatically for repeated leading content, so there's no explicit
`cache_control` equivalent to set here — the absence of cache flags is not a
regression relative to the Anthropic path.
"""
from __future__ import annotations

import logging

from google import genai
from google.genai import types

from app.adapters.llm_base import BaseLLMAdapter
from app.domain.models import JobDescription

_log = logging.getLogger(__name__)


class GoogleAdapter(BaseLLMAdapter):
    def __init__(self, *, api_key: str, model: str, max_tokens: int) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def _call(
        self,
        system_prompt: str,
        experience_docs: str,
        jd: JobDescription,
        *,
        jd_suffix: str = "",
        expect_json: bool = True,
    ) -> str:
        contents = (
            "EXPERIENCE_DOCS:\n"
            + experience_docs
            + "\n\nJOB_DESCRIPTION:\n"
            + jd.text
            + jd_suffix
        )
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=self._max_tokens,
            response_mime_type="application/json" if expect_json else "text/plain",
        )
        resp = self._client.models.generate_content(
            model=self._model, contents=contents, config=config
        )
        u = resp.usage_metadata
        _log.info(
            "gemini.usage input=%s cached=%s output=%s total=%s",
            getattr(u, "prompt_token_count", None),
            getattr(u, "cached_content_token_count", None),
            getattr(u, "candidates_token_count", None),
            getattr(u, "total_token_count", None),
        )
        return resp.text or ""
