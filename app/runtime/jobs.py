"""Background job store for async generate.

The generate use case is sync (Anthropic + Google SDKs are sync) and takes
30-90s. Fronted by Cloudflare's 100s edge timeout plus Render Free's ~60s cold
start, a blocking POST routinely 524s. So POST /api/generate enqueues a job
and returns 202; the client polls GET /api/jobs/{id} every 2s.

Single-user, single-process. State lives in memory, guarded by an asyncio
lock. A single-worker thread pool serializes the actual generation calls.
Completed jobs survive for 1h then get swept.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Literal

from app.domain.models import ApplicationRecord
from app.usecases.errors import DuplicateApplicationError, GenerationFailedError
from app.usecases.generate_application import GenerateApplication, GenerationRequest
from app.usecases.regenerate_application import RegenerateApplication, RegenerationRequest

_log = logging.getLogger(__name__)

JobStatus = Literal["queued", "running", "done", "duplicate", "error"]

# A queued unit of work: a fresh generate, or a regenerate of a failed run.
RunRequest = GenerationRequest | RegenerationRequest

_JOB_TTL_S = 3600.0
_SWEEP_INTERVAL_S = 300.0


@dataclass
class Job:
    id: str
    status: JobStatus
    created_at: float
    started_at: float | None = None
    finished_at: float | None = None
    application: ApplicationRecord | None = None
    existing: ApplicationRecord | None = None
    error: str | None = None
    error_record: ApplicationRecord | None = None  # the persisted "Error" row, if any


@dataclass
class JobStore:
    """In-memory job store with a 1-worker thread pool for the actual runs.

    Both generate and regenerate are sync, expensive LLM pipelines, so they
    share the same executor / TTL / polling machinery; ``_run`` dispatches on
    the request type."""

    _generate: GenerateApplication
    _regenerate: RegenerateApplication
    _jobs: dict[str, Job] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _executor: ThreadPoolExecutor = field(
        default_factory=lambda: ThreadPoolExecutor(max_workers=1, thread_name_prefix="generate")
    )

    async def enqueue(self, req: RunRequest) -> Job:
        job = Job(id=uuid.uuid4().hex, status="queued", created_at=time.time())
        async with self._lock:
            self._jobs[job.id] = job
        loop = asyncio.get_running_loop()
        loop.run_in_executor(self._executor, self._run, job.id, req)
        return job

    async def get(self, job_id: str) -> Job | None:
        async with self._lock:
            return self._jobs.get(job_id)

    def _run(self, job_id: str, req: RunRequest) -> None:
        # Runs on the executor thread; no event loop here. Mutate the job
        # under a coarse module-level GIL-protected update — the asyncio.Lock
        # is for the async accessors, not for thread/event-loop interleave.
        job = self._jobs.get(job_id)
        if job is None:
            return
        job.status = "running"
        job.started_at = time.time()
        try:
            record = (
                self._regenerate(req)
                if isinstance(req, RegenerationRequest)
                else self._generate(req)
            )
        except DuplicateApplicationError as exc:
            job.status = "duplicate"
            job.existing = exc.existing
            job.finished_at = time.time()
            _log.info("job %s duplicate (%s / %s)", job_id, exc.existing.company, exc.existing.role)
            return
        except GenerationFailedError as exc:
            # The use case already persisted a recoverable "Error" record; attach
            # it so the UI can point the user at it in History.
            job.status = "error"
            job.error = str(exc) or exc.__class__.__name__
            job.error_record = exc.record
            job.finished_at = time.time()
            _log.warning("job %s failed (record persisted=%s)", job_id, exc.record is not None)
            return
        except Exception as exc:
            job.status = "error"
            job.error = str(exc) or exc.__class__.__name__
            job.finished_at = time.time()
            _log.exception("job %s failed", job_id)
            return
        job.status = "done"
        job.application = record
        job.finished_at = time.time()
        _log.info("job %s done (%s / %s)", job_id, record.company, record.role)

    async def sweep(self) -> int:
        """Evict completed jobs older than _JOB_TTL_S. Returns the count evicted."""
        cutoff = time.time() - _JOB_TTL_S
        async with self._lock:
            stale = [
                jid
                for jid, j in self._jobs.items()
                if j.finished_at is not None and j.finished_at < cutoff
            ]
            for jid in stale:
                del self._jobs[jid]
        return len(stale)

    async def run_sweeper(self) -> None:
        """Background task: sweep on a loop. Cancelled by lifespan shutdown."""
        while True:
            try:
                await asyncio.sleep(_SWEEP_INTERVAL_S)
                evicted = await self.sweep()
                if evicted:
                    _log.info("swept %d expired job(s)", evicted)
            except asyncio.CancelledError:
                raise
            except Exception:
                _log.exception("sweeper iteration failed; continuing")

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
