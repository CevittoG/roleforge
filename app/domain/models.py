"""Domain models. Pure data structures with no FastAPI / vendor dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class WorkMode(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class ApplicationStatus(str, Enum):
    """User-editable application lifecycle. Stored as plain string in the Sheet
    (column D); enum is only enforced at the API boundary so old rows with
    unrecognized values keep round-tripping."""

    GENERATED = "Generated"
    APPLIED = "Applied"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"
    GHOSTED = "Ghosted"
    ON_HOLD = "On hold"


@dataclass(frozen=True)
class SkillItem:
    """A single skill/experience tag, coarsely categorized for pattern mining."""
    name: str                 # canonical short tag, e.g. "Kubernetes", "team leadership"
    category: str = ""        # language | cloud | data | leadership | domain | other


@dataclass(frozen=True)
class RequirementScore:
    """One row of the Match Report's transparent scoring table."""
    requirement: str          # short label, often mirrors a key_requirements tag
    weight: int = 1           # 1 (nice-to-have) | 2 (theme) | 3 (hard requirement)
    status: str = "not_evidenced"  # met | partial | not_evidenced
    evidence: str = ""        # one-line pointer to what in the docs supports it


@dataclass(frozen=True)
class JobDescription:
    text: str
    source_url: str | None = None


@dataclass(frozen=True)
class AuditFields:
    """Structured facts + match/gap analysis extracted from the JD."""
    company: str
    role: str
    work_mode: WorkMode = WorkMode.UNKNOWN
    location: str | None = None
    pay: str | None = None
    benefits: str | None = None
    seniority: str = ""
    fit_score: int | None = None              # 0-100, quick comparator
    key_requirements: tuple[str, ...] = ()
    tech_stack: tuple[str, ...] = ()
    matched: tuple[SkillItem, ...] = ()       # things the JD wants that your docs evidence
    missing: tuple[SkillItem, ...] = ()       # required/preferred but NOT in your docs
    requirements_scoring: tuple[RequirementScore, ...] = ()  # per-requirement breakdown
    concerns: str | None = None               # short free-text caveats


@dataclass(frozen=True)
class ContactHeader:
    """Resume header identity. Sourced deterministically from config (Settings),
    never from the model — contact data must never be hallucinated or go stale."""
    name: str = ""
    location: str | None = None
    email: str | None = None
    phone: str | None = None
    links: tuple[str, ...] = ()        # LinkedIn / portfolio / GitHub, etc.


@dataclass(frozen=True)
class ExperienceEntry:
    """One role in PROFESSIONAL EXPERIENCE. Layout (company/title left,
    location/dates right via tab stops) is owned by the renderer."""
    company: str
    title: str
    location: str | None
    start: str                        # "Oct 2024"
    end: str                          # "Present"
    bullets: list[str]                # CAR bullets, action verbs, no pronouns


@dataclass(frozen=True)
class EducationEntry:
    institution: str
    degree: str
    location: str | None = None
    dates: str | None = None
    detail: str | None = None         # coursework / honors line


@dataclass(frozen=True)
class AdditionalLine:
    """One labeled line in the ADDITIONAL section, e.g.
    label="Technical Skills", text="Python, SQL, ...". """
    label: str
    text: str


@dataclass(frozen=True)
class ResumeContent:
    experience: list[ExperienceEntry]
    education: list[EducationEntry]
    additional: list[AdditionalLine]
    header: ContactHeader = field(default_factory=ContactHeader)  # filled from config
    summary: str | None = None                # optional; omitted by default


@dataclass(frozen=True)
class CoverLetterContent:
    greeting: str
    body_paragraphs: list[str]
    closing: str


@dataclass(frozen=True)
class ApplicationAnswer:
    """One answered application/screening question. Produced only when the user
    supplies questions — answers reuse the same grounded context as the resume
    and cover letter, in first-person voice."""
    question: str
    answer: str


@dataclass(frozen=True)
class GeneratedContent:
    """Main `generate` call output. Interview prep is generated on demand in a
    separate call (it's the heaviest output and only needed for apps that
    advance), so it is NOT part of this object.

    `application_answers` is populated only when the request carried application
    questions; otherwise it stays empty and no Application_Questions.docx is written."""
    audit: AuditFields
    resume: ResumeContent
    cover_letter: CoverLetterContent
    application_answers: tuple[ApplicationAnswer, ...] = ()


# The resume is stored as a native Google Doc (editable in-browser, export PDF
# yourself), so it has no file extension. The cover letter is plain text.
RESUME_DOC = "Resume"
COVER_LETTER_TXT = "Cover_Letter.txt"
JOB_DESCRIPTION_MD = "Job_Description.md"
INTERVIEW_PREP_MD = "Interview_Prep.md"
MATCH_REPORT_MD = "Match_Report.md"
# Answered application questions are a standalone, editable Word file (enumerated
# Q&A) — never folded into the resume.
APPLICATION_QUESTIONS_DOCX = "Application_Questions.docx"

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# Maps a download key -> (Drive filename, suggested download filename). The
# resume Doc downloads as a freshly exported PDF; everything else (incl. the
# application-questions .docx) downloads byte-for-byte. The suggested name here
# is the static fallback — the download use case rewrites it to
# "<Name>-<Role>-<Date>-<Artifact>.<ext>" when the request carries role + date.
DOWNLOADABLE = {
    "resume": (RESUME_DOC, "Resume.pdf"),
    "cover_letter": (COVER_LETTER_TXT, COVER_LETTER_TXT),
    "job_description": (JOB_DESCRIPTION_MD, JOB_DESCRIPTION_MD),
    "interview_prep": (INTERVIEW_PREP_MD, INTERVIEW_PREP_MD),
    "match_report": (MATCH_REPORT_MD, MATCH_REPORT_MD),
    "application_questions": (APPLICATION_QUESTIONS_DOCX, APPLICATION_QUESTIONS_DOCX),
}


@dataclass(frozen=True)
class FolderRef:
    id: str
    url: str


@dataclass(frozen=True)
class ApplicationRecord:
    """One row in the audit Sheet = one generation = one Drive folder."""
    date: str
    company: str
    role: str
    status: str
    work_mode: str
    location: str | None
    pay: str | None
    benefits: str | None
    jd_source_url: str | None
    folder_url: str
    folder_id: str
    # decision-support / gap-analysis
    seniority: str = ""
    fit_score: int | None = None
    key_requirements: tuple[str, ...] = ()
    tech_stack: tuple[str, ...] = ()
    matched: tuple[SkillItem, ...] = ()
    missing: tuple[SkillItem, ...] = ()
    concerns: str | None = None
    jd_hash: str = ""   # SHA-256[:16] of jd.text; primary dedup key (model-drift-safe)
