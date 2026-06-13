"""The shared prompt/parsing layer both real adapters inherit. Exercised through
a stub subclass whose `_call` returns canned text, so no SDK or API key is needed.
"""
from __future__ import annotations

import json

from app.adapters.llm_base import BaseLLMAdapter
from app.domain.models import JobDescription

_CANNED = json.dumps(
    {
        "audit": {
            "company": "  Acme  ",
            "role": "Data Engineer",
            "work_mode": "remote",
            "seniority": "Senior",
            "fit_score": 80,
            "key_requirements": ["Python"],
            "tech_stack": ["Spark"],
            "matched": [{"name": "Python", "category": "language"}],
            "missing": [],
            "requirements_scoring": [
                {"requirement": "Python", "weight": 3, "status": "met", "evidence": "docs"}
            ],
            "concerns": "",
        },
        "resume": {
            "experience": [
                {
                    "company": "X",
                    "title": "Y",
                    "start": "Jan 2020",
                    "end": "Present",
                    "bullets": ["Built X."],
                }
            ],
            "education": [{"institution": "U", "degree": "BS"}],
            "additional": [{"label": "Technical Skills", "text": "Python"}],
        },
        "cover_letter": {
            "greeting": "Dear team,",
            "body_paragraphs": ["P1", "P2"],
            "closing": "Best,\nJane",
        },
    }
)


class _StubAdapter(BaseLLMAdapter):
    """Returns whatever it's given; records the JSON-vs-text hint."""

    def __init__(self, canned: str) -> None:
        self._canned = canned
        self.last_expect_json: bool | None = None

    def _call(
        self,
        system_prompt: str,
        experience_docs: str,
        jd: JobDescription,
        *,
        jd_suffix: str = "",
        expect_json: bool = True,
    ) -> str:
        self.last_expect_json = expect_json
        return self._canned


def test_generate_parses_canned_json() -> None:
    adapter = _StubAdapter(_CANNED)
    content = adapter.generate(
        experience_docs="EXP", jd=JobDescription(text="JD"), candidate_name="Jane"
    )
    assert content.audit.company == "Acme"  # stripped
    assert content.audit.fit_score == 80
    assert content.resume.experience[0].company == "X"
    assert content.cover_letter.closing == "Best,\nJane"
    assert adapter.last_expect_json is True


def test_interview_prep_strips_fences_and_requests_text() -> None:
    adapter = _StubAdapter("```markdown\n## Questions\n- one\n```")
    out = adapter.generate_interview_prep(experience_docs="EXP", jd=JobDescription(text="JD"))
    assert out == "## Questions\n- one"
    assert adapter.last_expect_json is False
