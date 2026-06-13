"""Anthropic transport for the shared LLM adapter.

Experience docs go in a cache-flagged block (~90% off on repeat runs in-window);
the system prompt is also cache-flagged. The shared prompt + parsing live in
`llm_base.BaseLLMAdapter`; this module supplies only the Anthropic API call.
"""
from __future__ import annotations

import logging
from typing import Any, cast

import anthropic

from app.adapters.llm_base import BaseLLMAdapter
from app.domain.models import JobDescription

_log = logging.getLogger(__name__)


class AnthropicAdapter(BaseLLMAdapter):
    def __init__(self, *, api_key: str, model: str, max_tokens: int) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
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
        # SDK 0.40 typed-dicts don't model `cache_control` on text blocks; the
        # field is still accepted at runtime. Cast keeps the call site honest.
        system_blocks: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "EXPERIENCE_DOCS:\n" + experience_docs,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {"type": "text", "text": "JOB_DESCRIPTION:\n" + jd.text + jd_suffix},
                ],
            }
        ]
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=cast(Any, system_blocks),
            messages=cast(Any, messages),
        )
        u = resp.usage
        _log.info(
            "anthropic.usage input=%s cache_read=%s cache_write=%s output=%s",
            getattr(u, "input_tokens", None),
            getattr(u, "cache_read_input_tokens", None),
            getattr(u, "cache_creation_input_tokens", None),
            getattr(u, "output_tokens", None),
        )
        return "".join(b.text for b in resp.content if b.type == "text")
