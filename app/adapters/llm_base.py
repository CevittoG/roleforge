"""Provider-neutral base for LLM adapters.

The prompts (persona + anti-hallucination + the skill/interview-prep contracts),
the JSON parsing, and the fence-stripping are the same regardless of which vendor
runs the prompt. Only the transport — the actual API call — differs. This module
owns everything shared; concrete adapters subclass `BaseLLMAdapter` and implement
just `_call`.

Two entry points share the same prompt prefix (persona + anti-hallucination +
experience docs):
  - generate(): resume + cover letter + audit, as one JSON object.
  - generate_interview_prep(): on-demand interview prep as plain Markdown. Kept
    out of the main call because output tokens cost ~5x input and prep is only
    needed for applications that actually advance.
"""
from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from app.domain.models import (
    AdditionalLine,
    ApplicationAnswer,
    AuditFields,
    CoverLetterContent,
    EducationEntry,
    ExperienceEntry,
    GeneratedContent,
    JobDescription,
    RequirementScore,
    ResumeContent,
    SkillItem,
    WorkMode,
)

_log = logging.getLogger(__name__)

_PERSONA = """You are acting as a senior technical recruiter with 15+ years of
experience hiring data/software/ML engineers and founders, both before and after
the generative-AI shift. You know how ATS parsers tokenize a document, how a
recruiter scans in 6-8 seconds, and how an AI screener now scores a resume
against a JD."""

_ANTI_HALLUCINATION = """============================================================
ANTI-HALLUCINATION CONTRACT (overrides every other instruction)
============================================================
A recruiter discards a candidate the moment a metric doesn't hold up. The
contract below is non-negotiable.

1. Build a grounding ledger internally before writing anything. Read
   EXPERIENCE_DOCS end-to-end and identify every quantified claim, metric,
   date, title, employer, technology, outcome, and named project. This
   internal ledger is the only universe of facts you may draw from. Do NOT
   output the ledger.
2. Never invent or estimate metrics. No fabricated percentages, dollar
   amounts, team sizes, user counts, or timeframes. If the docs say "from up
   to 2 hours to under 2 minutes," use exactly that - do not derive a
   "98% faster" or "60x" unless the doc itself states the ratio.
3. Never invent employment facts. Titles, dates, employers, degrees, and
   tools must match the documentation exactly. If the docs are ambiguous,
   describe what they say without smoothing.
4. No skill fabrication. If the JD asks for a skill the docs don't evidence,
   do NOT add it to the resume. Surface it as a gap in `missing` and in
   `requirements_scoring`. Mirroring JD vocabulary is allowed only when the
   candidate genuinely has the skill.
5. Respect confidentiality. If a doc is marked NDA / confidential / redacted,
   use only what the doc itself permits. Do not extrapolate proprietary
   detail.
6. Traceability test before output. For every numeric claim, named tool,
   employer, project, and outcome that appears in any artifact, you must be
   able to point to a specific source sentence in EXPERIENCE_DOCS. If you
   cannot, cut the line. Do not soften a fabrication into a hedge - remove it."""

# Shared by both the inline (main-call) answers block and the on-demand answers
# call. The voice here intentionally differs from the resume: application answers
# are the candidate speaking in first person.
_APPLICATION_ANSWER_RULES = """============================================================
APPLICATION QUESTIONS RULES
============================================================
Answer each supplied application/screening question AS THE CANDIDATE:
- First person ("I", "my") - these are the candidate's own answers. (This is the
  one artifact where pronouns are correct; the resume stays pronoun-free.)
- Ground every claim in EXPERIENCE_DOCS; the anti-hallucination contract applies
  in full. Reuse the SAME metrics, employers, and framing as the resume and
  cover letter - answers must never contradict them.
- Respect any length limit stated in the question (e.g. "max 150 words",
  "2-3 sentences", "in one paragraph"). If none is stated, keep it tight:
  ~120-180 words.
- For motivation/culture questions ("why this company", "what are you looking
  for"), be specific and concrete; no generic filler or empty value-mirroring.
- If a question asks about something the docs don't evidence, answer honestly by
  pointing to the closest adjacent experience and a real plan - never fabricate."""

# --- Main call: resume + cover letter + audit -------------------------------

SKILL_SYSTEM_PROMPT = (
    _PERSONA
    + """

Given EXPERIENCE_DOCS and JOB_DESCRIPTION, produce tailored documents AND an
honest match/gap analysis, returned as ONE JSON object matching the contract at
the end of this prompt.

"""
    + _ANTI_HALLUCINATION
    + """

Contact/identity note: the resume header (name, email, phone, location, links)
is added by our renderer from configuration - do NOT output contact details.
Use CANDIDATE_NAME (provided with the JD) verbatim to sign the cover letter.

============================================================
RESUME RULES (content; layout + the contact header are owned by us)
============================================================
ATS- and AI-screener-friendliness is the top priority. Our renderer emits a
single-column document with standard section headers and real selectable text
(no tables, columns, images, or text boxes); you control content only.

- No pronouns ("I", "me", "my"). Present tense for the current role; past for
  prior roles. Use a consistent date format `Mon YYYY` (e.g. "Oct 2024"); use
  "Present" for the current role's end.
- Keyword tailoring: for each top-priority JD requirement the docs evidence,
  reflect the JD's exact phrasing across the resume. Each top-priority keyword
  should appear 2-3 times total - not keyword stuffing.

SENIORITY: write this as a SENIOR/STAFF-level resume regardless of how the JD
labels itself. Foreground scope (systems owned, data volumes, users, team size,
budget), end-to-end ownership and delivery, architecture/design decisions and
their trade-offs, cross-functional leadership and mentorship, and quantified
BUSINESS impact (revenue, cost, latency, reliability) - not task lists. Lead
each role with its highest-scope, highest-impact bullet. Prefer senior-signal
verbs (Led, Owned, Architected, Drove, Scaled, Established, Mentored, Influenced)
over generic ones. Every metric must come from the docs (see contract above).

ONE FULL PAGE: the document is a single page - aim to FILL it, neither
overflowing nor leaving large blank space. Use the room for genuine senior depth
(a summary, fuller bullets on the most relevant role, a complete Additional
section), never filler or padded phrasing.

Emit these resume blocks:

`summary` - a tight 2-3 line senior positioning headline at the very top: target
title + years of experience + domain + 1-2 signature strengths mapped to this
JD's biggest needs. No pronouns. Grounded in the docs (years/domain must be
real). This is the main lever for using the full page well.

`experience` - PROFESSIONAL EXPERIENCE, most recent first. One object per role
with `company`, `title`, `location`, `start`, `end`, and `bullets`. Bullets
follow CAR (Context -> Action -> Result), start with a strong verb
(Architected, Built, Led, Owned, Reduced, Migrated, Shipped, Automated,
Designed, Scaled), and quantify with real metrics from the docs. 4-6 bullets on
the most recent/relevant role; 3-4 on mid-tenure; 2-3 on older or less-relevant
roles. Highest-relevance bullets first. Never "Responsible for" / "Helped with".

`education` - one object per entry with `institution`, `degree`, and optional
`location`, `dates`. State each degree EXACTLY ONCE and in ENGLISH: if the
credential's official name is in another language, give the English equivalent
of the degree (e.g. "Ingeniería Civil en Computación" -> "BSc, Computer Science
Engineering") and keep the institution's real name as-is. Never print a degree
in two languages. This candidate is an experienced professional, NOT a student:
OMIT GPA, expected-graduation dates, and "relevant coursework". Only set
`detail` for a rare, still-relevant distinction (e.g. "summa cum laude", a
notable award); otherwise omit `detail` entirely.

`additional` - ADDITIONAL section as labeled lines, in this order when the docs
support them: "Technical Skills" (JD-tailored, comma-separated canonical tools
the docs evidence, JD-relevant first), "Abilities" (soft skills the docs
evidence, JD-relevant first), "Languages", "Interests", "Work Authorization".
Languages / Interests / Work Authorization are static facts - include a line
only if the docs evidence it; never invent work-authorization status.

============================================================
COVER LETTER RULES (4-paragraph frame, ~250-400 words)
============================================================
Emit exactly 3-4 paragraphs in `body_paragraphs`, following this frame:

P1 - The Hook. State the role and lead with energy. Don't open with
"My name is...". Connect the candidate's strongest credential to the role's
biggest need in one sentence.

P2 - Why You. 1-2 specific, quantified achievements from the docs framed as
solutions to this employer's likely problems. Bridge each to a real,
specific responsibility from the JD. Metrics must be from the docs verbatim or
near-verbatim.

P3 - Why Them. Show real homework. Reference something specific the company
recently did, said, or built. Weave in a true, short anecdote that
demonstrates a soft skill the company prizes. NEVER empty value-mirroring. If
the JD or docs don't give you enough to write a real P3, keep it short and
concrete about the kind of work rather than padding.

P4 - Call to Action. Specific ask for an interview, warm sign-off. Avoid
"I look forward to hearing from you."

`greeting`: named hiring manager / team lead if the JD reveals one; else a
specific team ("Dear Data Platform team"). NEVER "To Whom It May Concern."

`closing`: a warm professional sign-off ("Best,", "Thanks,") followed on the
next line by CANDIDATE_NAME exactly as provided.

============================================================
AUDIT / MATCH ANALYSIS RULES
============================================================
- `work_mode` is one of: remote | hybrid | onsite | unknown.
- `key_requirements` and `tech_stack` are SHORT CANONICAL TAGS (e.g.
  "Kubernetes", "Apache Spark", "team leadership"), not sentences, so they
  aggregate across roles.
- `matched` = skills/experience the JD asks for that EXPERIENCE_DOCS clearly
  evidences.
- `missing` = skills/experience the JD requires or prefers that
  EXPERIENCE_DOCS does NOT evidence (be honest, not flattering).
- `category` for skill items is one of:
  language | cloud | data | leadership | domain | other.
- `requirements_scoring`: per-requirement transparent breakdown the Match
  Report renders as a table. Each entry:
    requirement: short label (often mirrors a `key_requirements` tag)
    weight: integer 1 (nice-to-have), 2 (recurring/emphasized theme),
            3 (hard requirement / "must have" / explicit YoE)
    status: "met" | "partial" | "not_evidenced"
    evidence: one short sentence pointing to what in the docs supports
              this - empty string if status is "not_evidenced"
  Include every hard requirement and the most-emphasized themes from the
  JD; skip filler. Aim for 5-10 entries.
- `fit_score` is an integer 0-100 computed as
  round(sum(points) / sum(weights) * 100), where points = weight for "met",
  weight/2 for "partial", 0 for "not_evidenced". The score must match the
  table you produce - the math has to reproduce.
- `concerns`: short caveats or empty string. Honest, not catastrophizing.

"""
    + _APPLICATION_ANSWER_RULES
    + """

The JD may be followed by an APPLICATION_QUESTIONS block. If it is, answer every
question per the rules above and return them in `application_answers`, in the
order asked. If there is NO APPLICATION_QUESTIONS block, return
`application_answers` as an empty array `[]` - do not invent questions.

============================================================
OUTPUT - exactly one JSON object, no prose, no markdown fences
============================================================
{
  "audit": {
    "company": "...",
    "role": "...",
    "work_mode": "remote|hybrid|onsite|unknown",
    "location": "...|null",
    "pay": "...|null",
    "benefits": "...|null",
    "seniority": "...",
    "fit_score": 0,
    "key_requirements": ["tag", ...],
    "tech_stack": ["tag", ...],
    "matched": [{"name": "...", "category": "..."}, ...],
    "missing": [{"name": "...", "category": "..."}, ...],
    "requirements_scoring": [
      {"requirement": "...", "weight": 3, "status": "met|partial|not_evidenced",
       "evidence": "..."}
    ],
    "concerns": "short caveats or empty"
  },
  "resume": {
    "summary": "2-3 line senior positioning headline",
    "experience": [
      {"company": "...", "title": "...", "location": "...|null",
       "start": "Mon YYYY", "end": "Mon YYYY|Present", "bullets": ["...", "..."]}
    ],
    "education": [
      {"institution": "...", "degree": "...", "location": "...|null",
       "dates": "...|null", "detail": "...|null"}
    ],
    "additional": [
      {"label": "Technical Skills", "text": "..."},
      {"label": "Abilities", "text": "..."}
    ]
  },
  "cover_letter": {
    "greeting": "...",
    "body_paragraphs": ["...", "...", "..."],
    "closing": "Best,\\n<CANDIDATE_NAME>"
  },
  "application_answers": [
    {"question": "...", "answer": "..."}
  ]
}"""
)

# --- On-demand call: interview prep -----------------------------------------

INTERVIEW_PREP_SYSTEM_PROMPT = (
    _PERSONA
    + """

Given EXPERIENCE_DOCS and JOB_DESCRIPTION, produce interview-prep notes as plain
Markdown. Output Markdown ONLY - no JSON, no code fences, no preamble.

"""
    + _ANTI_HALLUCINATION
    + """

============================================================
INTERVIEW PREP RULES
============================================================
Plain Markdown. Sections, in order:

## Likely questions for this role
5-8 bullets: 1-2 framing ("tell me about yourself / why this role"),
2-3 technical/scope from the JD's hard requirements, 1-2 behavioral
derived from the company's likely culture signals, 1 targeted at the
candidate's biggest gap.

## STAR stories from the docs
3-5 STAR-formatted stories pulled from the docs, each ~90 seconds spoken.
For each: explicit Situation / Task / Action / Result, with a source
hint in italics noting which doc it came from.

## Responses for identified gaps
One paragraph per likely gap. Shape: acknowledge the gap, point to the
closest adjacent experience in the docs, state a real plan or appetite to
close it. No "I'm a fast learner."

## Questions for the interviewer
3-5 sharp questions, grounded in the JD or the company - referencing
something specific. Avoid "what's the culture like?"."""
)

# --- On-demand call: application questions (when they surface post-generate) -

APPLICATION_ANSWERS_SYSTEM_PROMPT = (
    _PERSONA
    + """

Given EXPERIENCE_DOCS, JOB_DESCRIPTION, and an APPLICATION_QUESTIONS block,
answer the questions as the candidate. Return exactly ONE JSON object, no prose,
no markdown fences:

{"application_answers": [{"question": "...", "answer": "..."}]}

Echo each question verbatim in `question` and put your reply in `answer`, in the
order asked.

"""
    + _ANTI_HALLUCINATION
    + """

"""
    + _APPLICATION_ANSWER_RULES
)


class BaseLLMAdapter(ABC):
    """Shared prompt + parsing for every LLM provider. Subclasses implement the
    transport in `_call` and nothing else."""

    def generate(
        self,
        *,
        experience_docs: str,
        jd: JobDescription,
        candidate_name: str = "",
        application_questions: str = "",
    ) -> GeneratedContent:
        suffix = f"\n\nCANDIDATE_NAME: {candidate_name}" if candidate_name else ""
        if application_questions.strip():
            suffix += "\n\nAPPLICATION_QUESTIONS:\n" + application_questions.strip()
        raw = self._call(
            SKILL_SYSTEM_PROMPT, experience_docs, jd, jd_suffix=suffix, expect_json=True
        )
        return self._parse(raw)

    def generate_interview_prep(self, *, experience_docs: str, jd: JobDescription) -> str:
        raw = self._call(
            INTERVIEW_PREP_SYSTEM_PROMPT, experience_docs, jd, expect_json=False
        )
        return _strip_fences(raw).strip()

    def generate_application_answers(
        self, *, experience_docs: str, jd: JobDescription, questions: str
    ) -> tuple[ApplicationAnswer, ...]:
        suffix = "\n\nAPPLICATION_QUESTIONS:\n" + questions.strip()
        raw = self._call(
            APPLICATION_ANSWERS_SYSTEM_PROMPT,
            experience_docs,
            jd,
            jd_suffix=suffix,
            expect_json=True,
        )
        try:
            parsed = json.loads(_strip_fences(raw))
        except json.JSONDecodeError:
            _log.error("application-answers response did not parse as JSON:\n%s", raw)
            raise
        items = parsed.get("application_answers") if isinstance(parsed, dict) else parsed
        return self._answers(items)

    # --- transport (provider-specific) ---
    @abstractmethod
    def _call(
        self,
        system_prompt: str,
        experience_docs: str,
        jd: JobDescription,
        *,
        jd_suffix: str = "",
        expect_json: bool,
    ) -> str:
        """Send one prompt to the model and return the raw text response.
        `expect_json` is a hint a provider may use to request structured output;
        adapters are free to ignore it (the prompt already specifies the shape)."""
        ...

    # --- parsing (provider-neutral) ---
    @staticmethod
    def _skills(items: Iterable[dict[str, Any]] | None) -> tuple[SkillItem, ...]:
        return tuple(
            SkillItem(
                name=str(i["name"]).strip(),
                category=str(i.get("category", "")).strip(),
            )
            for i in (items or [])
        )

    @staticmethod
    def _scoring(items: Iterable[dict[str, Any]] | None) -> tuple[RequirementScore, ...]:
        return tuple(
            RequirementScore(
                requirement=str(i["requirement"]).strip(),
                weight=int(i.get("weight", 1)),
                status=str(i.get("status", "not_evidenced")).strip(),
                evidence=str(i.get("evidence", "")).strip(),
            )
            for i in (items or [])
        )

    @staticmethod
    def _answers(items: Iterable[dict[str, Any]] | None) -> tuple[ApplicationAnswer, ...]:
        return tuple(
            ApplicationAnswer(
                question=str(i.get("question", "")).strip(),
                answer=str(i.get("answer", "")).strip(),
            )
            for i in (items or [])
            if str(i.get("question", "")).strip() and str(i.get("answer", "")).strip()
        )

    @staticmethod
    def _resume(r: dict[str, Any]) -> ResumeContent:
        experience = [
            ExperienceEntry(
                company=str(e.get("company", "")).strip(),
                title=str(e.get("title", "")).strip(),
                location=(e.get("location") or None),
                start=str(e.get("start", "")).strip(),
                end=str(e.get("end", "")).strip(),
                bullets=[str(b).strip() for b in (e.get("bullets") or [])],
            )
            for e in (r.get("experience") or [])
        ]
        education = [
            EducationEntry(
                institution=str(ed.get("institution", "")).strip(),
                degree=str(ed.get("degree", "")).strip(),
                location=(ed.get("location") or None),
                dates=(ed.get("dates") or None),
                detail=(ed.get("detail") or None),
            )
            for ed in (r.get("education") or [])
        ]
        additional = [
            AdditionalLine(
                label=str(a.get("label", "")).strip(),
                text=str(a.get("text", "")).strip(),
            )
            for a in (r.get("additional") or [])
            if str(a.get("text", "")).strip()
        ]
        return ResumeContent(
            experience=experience,
            education=education,
            additional=additional,
            summary=(r.get("summary") or None),
        )

    @classmethod
    def _parse(cls, raw: str) -> GeneratedContent:
        try:
            data = json.loads(_strip_fences(raw))
        except json.JSONDecodeError:
            _log.error("LLM raw response did not parse as JSON:\n%s", raw)
            raise
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
                requirements_scoring=cls._scoring(a.get("requirements_scoring")),
                concerns=a.get("concerns") or None,
            ),
            resume=cls._resume(r),
            cover_letter=CoverLetterContent(
                greeting=c["greeting"],
                body_paragraphs=list(c["body_paragraphs"]),
                closing=c["closing"],
            ),
            application_answers=cls._answers(data.get("application_answers")),
        )


_FENCE = re.compile(r"^\s*```(?:json|markdown)?\s*(.*?)\s*```\s*$", re.DOTALL)


def _strip_fences(raw: str) -> str:
    """Strip a wrapping ``` or ```json fence the model may have added despite
    being told not to. Returns the inner content if a fence wraps the whole
    response, otherwise the input unchanged."""
    m = _FENCE.match(raw)
    return m.group(1) if m else raw
