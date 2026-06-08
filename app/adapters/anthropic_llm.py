"""Anthropic adapter implementing LLMClient.

Experience docs go in a cache-flagged block (~90% off on repeat runs in-window).
The model returns ONE JSON object we parse; layout is never taken from the model
(the PDF template owns layout). The audit block now also carries the match/gap
analysis used for cross-opportunity comparison and "what to learn next".
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any, cast

import anthropic

from app.domain.models import (
    AuditFields,
    CoverLetterContent,
    GeneratedContent,
    JobDescription,
    ResumeContent,
    ResumeSection,
    SkillItem,
    WorkMode,
)

# TODO: paste your "skill" here. Keep the JSON contract below intact.
SKILL_SYSTEM_PROMPT = """You are a careful career-documents generator and JD analyst.
Given EXPERIENCE_DOCS and a JOB_DESCRIPTION, produce tailored documents AND an
honest match/gap analysis.

Hard rules:
- Ground every resume/cover-letter claim in EXPERIENCE_DOCS; never invent experience.
- "matched" = skills/experience the JD asks for that EXPERIENCE_DOCS clearly evidences.
- "missing" = skills/experience the JD requires or prefers that EXPERIENCE_DOCS does
  NOT evidence (these are your growth areas — be honest, not flattering).
- All skill/requirement entries are SHORT CANONICAL TAGS (e.g. "Kubernetes",
  "Apache Spark", "team leadership"), not sentences, so they aggregate across roles.
- "category" is one of: language | cloud | data | leadership | domain | other.
- "fit_score" is an integer 0-100.

Return ONLY one JSON object, no prose, no markdown fences:
{
  "audit": {
    "company","role","work_mode"(remote|hybrid|onsite|unknown),"location","pay","benefits",
    "seniority","fit_score",
    "key_requirements":[tag,...],
    "tech_stack":[tag,...],
    "matched":[{"name","category"},...],
    "missing":[{"name","category"},...],
    "concerns": "short caveats or empty"
  },
  "resume": {"headline","summary","sections":[{"title","items":[...]}]},
  "cover_letter": {"greeting","body_paragraphs":[...],"closing"},
  "interview_prep_md": "<markdown>"
}"""


class AnthropicAdapter:
    def __init__(self, *, api_key: str, model: str, max_tokens: int) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def generate(self, *, experience_docs: str, jd: JobDescription) -> GeneratedContent:
        # SDK 0.40 typed-dicts don't model `cache_control` on text blocks; the
        # field is still accepted at runtime. Cast keeps the call site honest.
        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "EXPERIENCE_DOCS:\n" + experience_docs,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {"type": "text", "text": "JOB_DESCRIPTION:\n" + jd.text},
                ],
            }
        ]
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=SKILL_SYSTEM_PROMPT,
            messages=cast(Any, messages),
        )
        raw = "".join(b.text for b in resp.content if b.type == "text")
        return self._parse(raw)

    @staticmethod
    def _skills(items: Iterable[dict[str, Any]] | None) -> tuple[SkillItem, ...]:
        return tuple(
            SkillItem(
                name=str(i["name"]).strip(),
                category=str(i.get("category", "")).strip(),
            )
            for i in (items or [])
        )

    @classmethod
    def _parse(cls, raw: str) -> GeneratedContent:
        data = json.loads(raw)
        a, r, c = data["audit"], data["resume"], data["cover_letter"]
        fit = a.get("fit_score")
        return GeneratedContent(
            audit=AuditFields(
                company=a["company"].strip(),
                role=a["role"].strip(),
                work_mode=WorkMode(a.get("work_mode", "unknown")),
                location=a.get("location"),
                pay=a.get("pay"),
                benefits=a.get("benefits"),
                seniority=a.get("seniority", "").strip(),
                fit_score=int(fit) if fit not in (None, "") else None,
                key_requirements=tuple(a.get("key_requirements", [])),
                tech_stack=tuple(a.get("tech_stack", [])),
                matched=cls._skills(a.get("matched")),
                missing=cls._skills(a.get("missing")),
                concerns=a.get("concerns") or None,
            ),
            resume=ResumeContent(
                headline=r["headline"], summary=r["summary"],
                sections=[ResumeSection(title=s["title"], items=list(s["items"]))
                          for s in r["sections"]],
            ),
            cover_letter=CoverLetterContent(
                greeting=c["greeting"],
                body_paragraphs=list(c["body_paragraphs"]),
                closing=c["closing"],
            ),
            interview_prep_md=data["interview_prep_md"],
        )
