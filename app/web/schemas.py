"""HTTP request/response models with input caps (validation at the edge)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.config import get_settings
from app.domain.models import ApplicationRecord, ApplicationStatus

JobStatus = Literal["queued", "running", "done", "duplicate", "error"]
LlmProvider = Literal["anthropic", "gemini"]


class GenerateRequest(BaseModel):
    jd_text: str = Field(min_length=1)
    confirm_overwrite: bool = False
    provider: LlmProvider | None = None  # None ⇒ server default
    application_questions: str = ""      # optional; answered in the same call

    @model_validator(mode="after")
    def _within_cap(self) -> GenerateRequest:
        settings = get_settings()
        if len(self.jd_text) > settings.max_jd_chars:
            raise ValueError("jd_text too long")
        if len(self.application_questions) > settings.max_application_questions_chars:
            raise ValueError("application_questions too long")
        return self


class InterviewPrepRequest(BaseModel):
    """Optional body for the on-demand interview-prep endpoint."""

    provider: LlmProvider | None = None  # None ⇒ server default


class ApplicationQuestionsRequest(BaseModel):
    """Body for the on-demand application-questions endpoint."""

    questions: str = Field(min_length=1)
    provider: LlmProvider | None = None  # None ⇒ server default

    @model_validator(mode="after")
    def _within_cap(self) -> ApplicationQuestionsRequest:
        if len(self.questions) > get_settings().max_application_questions_chars:
            raise ValueError("questions too long")
        return self


class RegenerateRequest(BaseModel):
    """Optional body for the re-generate endpoint. application_questions: omit /
    null ⇒ reuse the saved questions input; "" ⇒ no questions; else override."""

    provider: LlmProvider | None = None  # None ⇒ server default
    application_questions: str | None = None

    @model_validator(mode="after")
    def _within_cap(self) -> RegenerateRequest:
        q = self.application_questions
        if q is not None and len(q) > get_settings().max_application_questions_chars:
            raise ValueError("application_questions too long")
        return self


class ApplicationSummary(BaseModel):
    date: str
    company: str
    role: str
    status: str
    seniority: str
    fit_score: int | None
    work_mode: str
    location: str | None
    pay: str | None
    benefits: str | None
    key_requirements: list[str]
    tech_stack: list[str]
    matched_experience: list[str]
    missing_experience: list[str]
    concerns: str | None
    jd_source_url: str | None
    folder_url: str
    folder_id: str

    @classmethod
    def of(cls, r: ApplicationRecord) -> ApplicationSummary:
        return cls(
            date=r.date, company=r.company, role=r.role, status=r.status,
            seniority=r.seniority, fit_score=r.fit_score, work_mode=r.work_mode,
            location=r.location, pay=r.pay, benefits=r.benefits,
            key_requirements=list(r.key_requirements), tech_stack=list(r.tech_stack),
            matched_experience=[s.name for s in r.matched],
            missing_experience=[s.name for s in r.missing],
            concerns=r.concerns, jd_source_url=r.jd_source_url,
            folder_url=r.folder_url, folder_id=r.folder_id,
        )


class GenerateResponse(BaseModel):
    """Returned by POST /api/generate — the job is now queued; client polls GET /api/jobs/{id}."""

    job_id: str
    status: JobStatus


class JobResponse(BaseModel):
    """Polled state of a generate job."""

    job_id: str
    status: JobStatus
    application: ApplicationSummary | None = None
    existing: ApplicationSummary | None = None
    error: str | None = None
    # The recoverable "Error" record persisted when a run fails, so the client
    # can deep-link to it in History for re-generation.
    error_record: ApplicationSummary | None = None
    started_at: float | None = None
    finished_at: float | None = None


class DuplicateResponse(BaseModel):
    """Legacy sync-mode response shape. Kept for symmetry; the async path
    surfaces duplicates via JobResponse.status == 'duplicate'."""

    detail: str = "application already exists"
    existing: ApplicationSummary


class StatusUpdateRequest(BaseModel):
    status: ApplicationStatus


class ConfigResponse(BaseModel):
    """Runtime-injected, non-secret config the frontend needs."""

    insights_url: str | None
    llm_providers: list[str]          # which LLM providers are configured
    default_llm_provider: str         # which one the UI pre-selects
