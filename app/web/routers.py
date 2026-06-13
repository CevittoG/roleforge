"""Thin HTTP layer: translate HTTP <-> use cases. No business logic here."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import Settings, get_settings
from app.container import Container
from app.runtime.jobs import JobStore
from app.security.cf_access import verify_access
from app.usecases.errors import RecordNotFoundError
from app.usecases.generate_application import GenerationRequest
from app.web.deps import get_container, get_job_store
from app.web.schemas import (
    ApplicationQuestionsRequest,
    ApplicationSummary,
    ConfigResponse,
    GenerateRequest,
    GenerateResponse,
    InterviewPrepRequest,
    JobResponse,
    StatusUpdateRequest,
)

# Every API route requires a valid Cloudflare Access token + origin secret.
api = APIRouter(prefix="/api", dependencies=[Depends(verify_access)])


@api.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@api.get("/config", response_model=ConfigResponse)
def get_config(
    settings: Settings = Depends(get_settings),
    c: Container = Depends(get_container),
) -> ConfigResponse:
    return ConfigResponse(
        insights_url=settings.sheet_insights_url,
        llm_providers=list(c.llm_providers),
        default_llm_provider=c.default_provider,
    )


@api.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate(
    req: GenerateRequest,
    jobs: JobStore = Depends(get_job_store),
) -> GenerateResponse:
    """Enqueue a generation job. Returns immediately; client polls /api/jobs/{id}."""
    job = await jobs.enqueue(
        GenerationRequest(
            raw_text=req.jd_text,
            confirm_overwrite=req.confirm_overwrite,
            provider=req.provider,
            application_questions=req.application_questions,
        )
    )
    return GenerateResponse(job_id=job.id, status=job.status)


@api.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    jobs: JobStore = Depends(get_job_store),
) -> JSONResponse:
    job = await jobs.get(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    payload = JobResponse(
        job_id=job.id,
        status=job.status,
        application=ApplicationSummary.of(job.application) if job.application else None,
        existing=ApplicationSummary.of(job.existing) if job.existing else None,
        error=job.error,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )
    return JSONResponse(content=payload.model_dump())


@api.get("/applications", response_model=list[ApplicationSummary])
def list_applications(c: Container = Depends(get_container)) -> list[ApplicationSummary]:
    return [ApplicationSummary.of(r) for r in c.list_applications()]


@api.patch(
    "/applications/{folder_id}/status",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=JSONResponse,
)
def update_application_status(
    folder_id: str,
    req: StatusUpdateRequest,
    c: Container = Depends(get_container),
) -> JSONResponse:
    try:
        c.update_status(folder_id=folder_id, status=req.status.value)
    except RecordNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "application not found") from exc
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@api.post(
    "/applications/{folder_id}/interview-prep",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=JSONResponse,
)
def generate_interview_prep(
    folder_id: str,
    req: InterviewPrepRequest | None = None,
    c: Container = Depends(get_container),
) -> JSONResponse:
    """Generate Interview_Prep.md on demand (the one artifact kept out of the
    main generate call to save output tokens). Synchronous: it's a single short
    LLM call and relies on a warm instance (the frontend warm-pings /healthz).
    The optional body carries the provider override; an empty POST uses the
    server default."""
    provider = req.provider if req else None
    try:
        c.generate_interview_prep(folder_id=folder_id, provider=provider)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "application not found") from exc
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@api.post(
    "/applications/{folder_id}/application-questions",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=JSONResponse,
)
def generate_application_answers(
    folder_id: str,
    req: ApplicationQuestionsRequest,
    c: Container = Depends(get_container),
) -> JSONResponse:
    """Answer application questions on demand for an already-generated
    application (the case where questions surface after the main run). The
    inline path on /api/generate is preferred; this reuses the cached experience
    docs and the saved JD. Synchronous — a single short LLM call."""
    try:
        c.generate_application_answers(
            folder_id=folder_id, questions=req.questions, provider=req.provider
        )
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "application not found") from exc
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@api.get("/download")
def download(
    folder_id: str = Query(..., max_length=128),
    file: str = Query(
        ...,
        pattern="^(resume|cover_letter|job_description|interview_prep|match_report"
        "|application_questions)$",
    ),
    role: str | None = Query(None, max_length=200),
    date: str | None = Query(None, max_length=40),
    c: Container = Depends(get_container),
) -> StreamingResponse:
    try:
        data, mime, filename = c.download(
            folder_id=folder_id, file_key=file, role=role, date=date
        )
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found") from exc
    except KeyError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown file") from exc

    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
