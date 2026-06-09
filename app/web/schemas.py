"""HTTP request/response models with input caps (validation at the edge)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.config import get_settings
from app.domain.models import ApplicationRecord

JobStatus = Literal["queued", "running", "done", "duplicate", "error"]


class GenerateRequest(BaseModel):
    jd_text: str | None = Field(default=None)
    jd_url: str | None = Field(default=None, max_length=2048)
    confirm_overwrite: bool = False

    @model_validator(mode="after")
    def _exactly_one_source(self) -> GenerateRequest:
        if bool(self.jd_text) == bool(self.jd_url):
            raise ValueError("provide exactly one of jd_text or jd_url")
        if self.jd_text and len(self.jd_text) > get_settings().max_jd_chars:
            raise ValueError("jd_text too long")
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
    started_at: float | None = None
    finished_at: float | None = None


class DuplicateResponse(BaseModel):
    """Legacy sync-mode response shape. Kept for symmetry; the async path
    surfaces duplicates via JobResponse.status == 'duplicate'."""

    detail: str = "application already exists"
    existing: ApplicationSummary
