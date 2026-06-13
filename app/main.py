"""App entrypoint. Single process: FastAPI serves the API under /api and the
Next.js static export at /. The static mount is added LAST so it only catches
paths the API didn't claim."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings
from app.container import build_container
from app.runtime.jobs import JobStore
from app.web.routers import api

# Surface our INFO-level logs (phase durations, anthropic usage, job lifecycle)
# to stdout. Uvicorn leaves the root logger at WARNING by default, which would
# silently drop the observability work in app.usecases.* and app.runtime.*.
# Loggers are instantiated at import time but don't emit until runtime, so
# configuring after the imports is fine.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

_STATIC_DIR = Path(__file__).resolve().parent / "static"  # Next `out/` copied here at build

# Locked-down headers. CSP allows only same-origin; tighten 'connect-src' if you
# call the API from a different origin (you don't, in single-process mode).
_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        resp = await call_next(request)
        for k, v in _SECURITY_HEADERS.items():
            resp.headers.setdefault(k, v)
        return resp


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = build_container(get_settings())
    job_store = JobStore(_generate=container.generate, _regenerate=container.regenerate)
    app.state.container = container
    app.state.job_store = job_store
    sweeper = asyncio.create_task(job_store.run_sweeper(), name="job-sweeper")
    try:
        yield
    finally:
        sweeper.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await sweeper
        job_store.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Job Application Generator",
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(SecurityHeadersMiddleware)

    # Public health check. Lives OUTSIDE the /api router so Render's platform
    # health check and external uptime pingers can hit it without a Cloudflare
    # Access JWT or origin secret.
    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api)
    if _STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
    return app


app = create_app()
