"""Thin HTTP layer: translate HTTP <-> use cases. No business logic here."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.container import Container
from app.security.cf_access import verify_access
from app.usecases.errors import DuplicateApplicationError
from app.usecases.generate_application import GenerationRequest
from app.web.deps import get_container
from app.web.schemas import (
    ApplicationSummary,
    DuplicateResponse,
    GenerateRequest,
    GenerateResponse,
)

# Every API route requires a valid Cloudflare Access token + origin secret.
api = APIRouter(prefix="/api", dependencies=[Depends(verify_access)])


@api.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@api.post(
    "/generate",
    response_model=GenerateResponse,
    responses={status.HTTP_409_CONFLICT: {"model": DuplicateResponse}},
)
def generate(req: GenerateRequest, c: Container = Depends(get_container)) -> Response:
    try:
        record = c.generate(
            GenerationRequest(
                raw_text=req.jd_text, url=req.jd_url, confirm_overwrite=req.confirm_overwrite
            )
        )
    except DuplicateApplicationError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=DuplicateResponse(existing=ApplicationSummary.of(exc.existing)).model_dump(),
        )
    return JSONResponse(
        content=GenerateResponse(application=ApplicationSummary.of(record)).model_dump()
    )


@api.get("/applications", response_model=list[ApplicationSummary])
def list_applications(c: Container = Depends(get_container)) -> list[ApplicationSummary]:
    return [ApplicationSummary.of(r) for r in c.list_applications()]


@api.get("/download")
def download(
    folder_id: str = Query(..., max_length=128),
    file: str = Query(..., pattern="^(resume|cover_letter|job_description|interview_prep)$"),
    c: Container = Depends(get_container),
) -> StreamingResponse:
    try:
        data, mime, filename = c.download(folder_id=folder_id, file_key=file)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found") from exc
    except KeyError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown file") from exc

    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
