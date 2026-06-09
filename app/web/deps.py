"""FastAPI dependencies: access to the wired container + the job store."""
from __future__ import annotations

from typing import cast

from fastapi import Request

from app.container import Container
from app.runtime.jobs import JobStore


def get_container(request: Request) -> Container:
    return cast(Container, request.app.state.container)


def get_job_store(request: Request) -> JobStore:
    return cast(JobStore, request.app.state.job_store)
