"""Failure path of GenerateApplication: a failed run still leaves a recoverable
trace — an "Error" audit row plus an Unknown-<date>/<uuid> Drive folder holding
the JD and any pasted questions — and raises GenerationFailedError carrying it."""
from __future__ import annotations

import pytest

from app.domain.models import (
    APPLICATION_QUESTIONS_DOCX,
    APPLICATION_QUESTIONS_INPUT,
    JOB_DESCRIPTION_MD,
    ApplicationStatus,
    FolderRef,
    GeneratedContent,
    JobDescription,
)
from app.usecases.errors import GenerationFailedError
from app.usecases.generate_application import GenerateApplication, GenerationRequest
from tests.conftest import (
    FakeAuditLog,
    FakeExperienceDocs,
    FakeLLM,
    FakeOutputStore,
    FakeRenderer,
    make_header,
)


class _RaisingLLM(FakeLLM):
    """Fails the main generate call — the most common real-world failure."""

    def generate(
        self,
        *,
        experience_docs: str,
        jd: JobDescription,
        candidate_name: str = "",
        application_questions: str = "",
    ) -> GeneratedContent:
        raise RuntimeError("llm exploded")


class _FlakyStore(FakeOutputStore):
    """FakeOutputStore that raises on a chosen operation."""

    def __init__(self, *, fail_on: str) -> None:
        super().__init__()
        self._fail_on = fail_on

    def ensure_folder(self, *, company: str, role: str) -> FolderRef:
        if self._fail_on == "ensure_folder":
            raise RuntimeError("drive down")
        return super().ensure_folder(company=company, role=role)

    def ensure_error_folder(self, *, group_name: str, run_id: str) -> FolderRef:
        if self._fail_on == "ensure_error_folder":
            raise RuntimeError("drive down")
        return super().ensure_error_folder(group_name=group_name, run_id=run_id)


def _build(*, llm: FakeLLM, store: FakeOutputStore, audit: FakeAuditLog) -> GenerateApplication:
    return GenerateApplication(
        docs=FakeExperienceDocs(),
        llms={"anthropic": llm},
        renderer=FakeRenderer(),
        store=store,
        audit_log=audit,
        default_provider="anthropic",
        resume_header=make_header(),
    )


def test_llm_failure_persists_unknown_error_record() -> None:
    store, audit = FakeOutputStore(), FakeAuditLog()
    uc = _build(llm=_RaisingLLM(), store=store, audit=audit)

    with pytest.raises(GenerationFailedError) as exc_info:
        uc(GenerationRequest(raw_text="A job description."))

    # Exactly one Unknown-<date>/<uuid> error folder was created.
    assert len(store.error_folders) == 1
    group_name, _run_id, folder_id = store.error_folders[0]
    assert group_name.startswith("Unknown - ")

    # JD saved there for traceability.
    assert store.texts[(folder_id, JOB_DESCRIPTION_MD)][0] == "A job description."

    # An "Error" row was appended, company falls back to "Unknown".
    assert len(audit.records) == 1
    rec = audit.records[0]
    assert rec.status == ApplicationStatus.ERROR.value
    assert rec.company == "Unknown"
    assert rec.role == ""
    assert rec.folder_id == folder_id

    # The exception carries the persisted record for the UI.
    assert exc_info.value.record is rec
    assert isinstance(exc_info.value.original, RuntimeError)


def test_failure_after_llm_keeps_company_role_but_stays_in_unknown_folder() -> None:
    store = _FlakyStore(fail_on="ensure_folder")
    audit = FakeAuditLog()
    uc = _build(llm=FakeLLM(), store=store, audit=audit)

    with pytest.raises(GenerationFailedError):
        uc(GenerationRequest(raw_text="JD"))

    rec = audit.records[0]
    # LLM succeeded, so company/role come from its audit output...
    assert rec.company == "Acme Corp"
    assert rec.role == "Data Engineer"
    assert rec.status == ApplicationStatus.ERROR.value
    # ...but the folder is still the Unknown error bucket.
    assert rec.folder_id == store.error_folders[0][2]


def test_failure_with_questions_saves_input_and_blank_docx() -> None:
    store, audit = FakeOutputStore(), FakeAuditLog()
    uc = _build(llm=_RaisingLLM(), store=store, audit=audit)

    with pytest.raises(GenerationFailedError):
        uc(GenerationRequest(raw_text="JD", application_questions="Why us?\nWhy you?"))

    folder_id = store.error_folders[0][2]
    # Raw questions saved verbatim for one-click regen.
    assert store.texts[(folder_id, APPLICATION_QUESTIONS_INPUT)][0] == "Why us?\nWhy you?"
    # A placeholder (no-answer) Application_Questions.docx is written too.
    assert (folder_id, APPLICATION_QUESTIONS_DOCX) in store.bytes_files


def test_best_effort_persistence_failure_still_surfaces_original_error() -> None:
    store = _FlakyStore(fail_on="ensure_error_folder")
    audit = FakeAuditLog()
    uc = _build(llm=_RaisingLLM(), store=store, audit=audit)

    with pytest.raises(GenerationFailedError) as exc_info:
        uc(GenerationRequest(raw_text="JD"))

    # Persistence itself failed -> no record, but the run doesn't crash and the
    # original cause is preserved.
    assert exc_info.value.record is None
    assert isinstance(exc_info.value.original, RuntimeError)
    assert audit.records == []
