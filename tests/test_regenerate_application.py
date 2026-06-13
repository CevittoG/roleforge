"""RegenerateApplication use case and job-store dispatch.

Covers:
- Happy path: reads back JD, calls LLM, saves artifacts, moves folder, updates record.
- Questions: reuse from saved input file vs. explicit override vs. empty override.
- Missing JD -> FileNotFoundError propagates.
- update_record on an unknown folder_id -> RecordNotFoundError.
- Job-store dispatch: RegenerationRequest routes to _regenerate, not _generate.
"""
from __future__ import annotations

import pytest

from app.domain.models import (
    APPLICATION_QUESTIONS_INPUT,
    JOB_DESCRIPTION_MD,
    ApplicationRecord,
    ApplicationStatus,
    WorkMode,
)
from app.runtime.jobs import Job, JobStore
from app.usecases.errors import RecordNotFoundError
from app.usecases.generate_application import GenerateApplication, GenerationRequest
from app.usecases.regenerate_application import RegenerateApplication, RegenerationRequest
from tests.conftest import (
    FakeAuditLog,
    FakeExperienceDocs,
    FakeLLM,
    FakeOutputStore,
    FakeRenderer,
    make_header,
)

_FOLDER = "Unknown - 2026-06-01__abc123"
_JD_TEXT = "Senior Data Engineer JD"
_QUESTIONS_TEXT = "Why us?\nWhy you?"


def _error_record(folder_id: str = _FOLDER) -> ApplicationRecord:
    return ApplicationRecord(
        date="2026-06-01T00:00:00+00:00",
        company="Unknown",
        role="",
        status=ApplicationStatus.ERROR.value,
        work_mode=WorkMode.UNKNOWN.value,
        location=None,
        pay=None,
        benefits=None,
        jd_source_url=None,
        folder_url=f"https://drive.example/{folder_id}",
        folder_id=folder_id,
    )


def _build(
    *,
    store: FakeOutputStore,
    audit: FakeAuditLog,
    llm: FakeLLM | None = None,
) -> RegenerateApplication:
    return RegenerateApplication(
        docs=FakeExperienceDocs(),
        llms={"anthropic": llm or FakeLLM()},
        renderer=FakeRenderer(),
        store=store,
        audit_log=audit,
        default_provider="anthropic",
        resume_header=make_header(),
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_regen_reads_jd_and_saves_artifacts() -> None:
    store = FakeOutputStore(
        preload={(_FOLDER, JOB_DESCRIPTION_MD): (b"Senior Data Engineer JD", "text/markdown")}
    )
    llm = FakeLLM()
    audit = FakeAuditLog(records=[_error_record()])
    uc = _build(store=store, audit=audit, llm=llm)

    record = uc(RegenerationRequest(folder_id=_FOLDER))

    # LLM was called with the read-back JD text.
    assert len(llm.generate_calls) == 1
    _, called_jd, _, called_questions = llm.generate_calls[0]
    assert called_jd.text == "Senior Data Engineer JD"
    assert called_questions == ""  # no questions preloaded

    # Core artifacts saved into the same folder_id.
    assert (_FOLDER, "Job_Description.md") in store.texts
    assert (_FOLDER, "Resume") in store.google_docs
    assert (_FOLDER, "Cover_Letter.txt") in store.texts
    assert (_FOLDER, "Match_Report.md") in store.texts

    # Folder moved to the real <Company>/<Role> path.
    assert store.moves == [(_FOLDER, "Acme Corp", "Data Engineer")]

    # Audit row updated in place: status Generated, company/role from LLM.
    assert len(audit.record_updates) == 1
    updated = audit.record_updates[0]
    assert updated.status == ApplicationStatus.GENERATED.value
    assert updated.company == "Acme Corp"
    assert updated.role == "Data Engineer"
    assert updated.folder_id == _FOLDER  # folder id preserved

    # Return value mirrors the updated record.
    assert record.status == ApplicationStatus.GENERATED.value


# ---------------------------------------------------------------------------
# Questions: reuse vs. override vs. empty
# ---------------------------------------------------------------------------


def test_regen_reuses_saved_questions_when_override_is_none() -> None:
    store = FakeOutputStore(
        preload={
            (_FOLDER, JOB_DESCRIPTION_MD): (b"JD", "text/markdown"),
            (_FOLDER, APPLICATION_QUESTIONS_INPUT): (b"Why us?\nWhy you?", "text/plain"),
        }
    )
    llm = FakeLLM()
    audit = FakeAuditLog(records=[_error_record()])
    uc = _build(store=store, audit=audit, llm=llm)

    uc(RegenerationRequest(folder_id=_FOLDER, application_questions=None))

    _, _, _, called_questions = llm.generate_calls[0]
    assert called_questions == "Why us?\nWhy you?"


def test_regen_uses_override_questions_and_persists_them() -> None:
    store = FakeOutputStore(
        preload={(_FOLDER, JOB_DESCRIPTION_MD): (b"JD", "text/markdown")}
    )
    llm = FakeLLM()
    audit = FakeAuditLog(records=[_error_record()])
    uc = _build(store=store, audit=audit, llm=llm)

    uc(RegenerationRequest(folder_id=_FOLDER, application_questions="Override Q"))

    _, _, _, called_questions = llm.generate_calls[0]
    assert called_questions == "Override Q"

    # Override persisted so a future re-regen is still one-click.
    saved_text, saved_mime = store.texts[(_FOLDER, APPLICATION_QUESTIONS_INPUT)]
    assert saved_text == "Override Q"
    assert saved_mime == "text/plain"


def test_regen_empty_override_calls_llm_without_questions_and_skips_save() -> None:
    store = FakeOutputStore(
        preload={
            (_FOLDER, JOB_DESCRIPTION_MD): (b"JD", "text/markdown"),
            (_FOLDER, APPLICATION_QUESTIONS_INPUT): (b"Old questions", "text/plain"),
        }
    )
    llm = FakeLLM()
    audit = FakeAuditLog(records=[_error_record()])
    uc = _build(store=store, audit=audit, llm=llm)

    uc(RegenerationRequest(folder_id=_FOLDER, application_questions=""))

    _, _, _, called_questions = llm.generate_calls[0]
    assert called_questions == ""

    # Empty override is not persisted (the old file stays but no new write happens).
    assert (_FOLDER, APPLICATION_QUESTIONS_INPUT) not in store.texts


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_regen_missing_jd_raises_file_not_found() -> None:
    store = FakeOutputStore()  # no preload
    audit = FakeAuditLog(records=[_error_record()])
    uc = _build(store=store, audit=audit)

    with pytest.raises(FileNotFoundError):
        uc(RegenerationRequest(folder_id=_FOLDER))


def test_regen_update_record_not_found_raises() -> None:
    store = FakeOutputStore(
        preload={(_FOLDER, JOB_DESCRIPTION_MD): (b"JD", "text/markdown")}
    )
    audit = FakeAuditLog(records=[])  # no Error row seeded
    uc = _build(store=store, audit=audit)

    with pytest.raises(RecordNotFoundError):
        uc(RegenerationRequest(folder_id=_FOLDER))


# ---------------------------------------------------------------------------
# Job-store dispatch
# ---------------------------------------------------------------------------


def test_job_store_routes_regeneration_request_to_regen_use_case() -> None:
    """_run dispatches RegenerationRequest -> _regenerate, not _generate."""
    store = FakeOutputStore(
        preload={(_FOLDER, JOB_DESCRIPTION_MD): (b"JD", "text/markdown")}
    )
    regen_llm = FakeLLM()
    audit = FakeAuditLog(records=[_error_record()])

    regen_uc = RegenerateApplication(
        docs=FakeExperienceDocs(),
        llms={"anthropic": regen_llm},
        renderer=FakeRenderer(),
        store=store,
        audit_log=audit,
        default_provider="anthropic",
    )

    class _NeverGenerate:
        """Sentinel: should never be called for a RegenerationRequest."""
        def __call__(self, req: GenerationRequest) -> ApplicationRecord:  # type: ignore[return]
            raise AssertionError("generate() was called on a RegenerationRequest")

    job_store = JobStore(_generate=_NeverGenerate(), _regenerate=regen_uc)  # type: ignore[arg-type]
    job = Job(id="j1", status="queued", created_at=0.0)
    job_store._jobs["j1"] = job

    job_store._run("j1", RegenerationRequest(folder_id=_FOLDER))

    assert job.status == "done"
    assert job.application is not None
    assert job.application.status == ApplicationStatus.GENERATED.value
    assert regen_llm.generate_calls  # regen LLM was called


def test_job_store_routes_generation_request_to_generate_use_case() -> None:
    """_run dispatches GenerationRequest -> _generate, not _regenerate."""
    gen_llm = FakeLLM()
    gen_store = FakeOutputStore()
    gen_audit = FakeAuditLog()

    gen_uc = GenerateApplication(
        docs=FakeExperienceDocs(),
        llms={"anthropic": gen_llm},
        renderer=FakeRenderer(),
        store=gen_store,
        audit_log=gen_audit,
        default_provider="anthropic",
        resume_header=make_header(),
    )

    class _NeverRegen:
        def __call__(self, req: RegenerationRequest) -> ApplicationRecord:  # type: ignore[return]
            raise AssertionError("regenerate() was called on a GenerationRequest")

    job_store = JobStore(_generate=gen_uc, _regenerate=_NeverRegen())  # type: ignore[arg-type]
    job = Job(id="j2", status="queued", created_at=0.0)
    job_store._jobs["j2"] = job

    job_store._run("j2", GenerationRequest(raw_text="Some JD text"))

    assert job.status == "done"
    assert gen_llm.generate_calls
