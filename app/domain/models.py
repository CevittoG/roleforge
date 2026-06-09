"""Domain models. Pure data structures with no FastAPI / vendor dependencies."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkMode(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


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
class ResumeSection:
    title: str
    items: list[str]


@dataclass(frozen=True)
class ResumeContent:
    headline: str
    summary: str
    sections: list[ResumeSection]


@dataclass(frozen=True)
class CoverLetterContent:
    greeting: str
    body_paragraphs: list[str]
    closing: str


@dataclass(frozen=True)
class GeneratedContent:
    audit: AuditFields
    resume: ResumeContent
    cover_letter: CoverLetterContent
    interview_prep_md: str


RESUME_PDF = "Resume.pdf"
COVER_LETTER_PDF = "Cover_Letter.pdf"
JOB_DESCRIPTION_MD = "Job_Description.md"
INTERVIEW_PREP_MD = "Interview_Prep.md"
MATCH_REPORT_MD = "Match_Report.md"

DOWNLOADABLE = {
    "resume": RESUME_PDF,
    "cover_letter": COVER_LETTER_PDF,
    "job_description": JOB_DESCRIPTION_MD,
    "interview_prep": INTERVIEW_PREP_MD,
    "match_report": MATCH_REPORT_MD,
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
