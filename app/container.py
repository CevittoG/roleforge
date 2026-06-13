"""Composition root. The ONLY place adapters are instantiated and wired into
use cases. Everything else depends on ports, not concretions."""
from __future__ import annotations

from dataclasses import dataclass

from app.adapters.anthropic_llm import AnthropicAdapter
from app.adapters.docx_resume import DocxRenderer
from app.adapters.experience_docs import DriveExperienceDocs
from app.adapters.google_drive import GoogleDriveStore
from app.adapters.google_llm import GoogleAdapter
from app.adapters.google_sheets import GoogleSheetsAudit
from app.config import Settings
from app.domain.models import ContactHeader
from app.domain.ports import LLMClient
from app.usecases.download_file import DownloadFile
from app.usecases.generate_application import GenerateApplication
from app.usecases.generate_application_answers import GenerateApplicationAnswers
from app.usecases.generate_interview_prep import GenerateInterviewPrep
from app.usecases.list_applications import ListApplications
from app.usecases.update_application_status import UpdateApplicationStatus


@dataclass(frozen=True)
class Container:
    generate: GenerateApplication
    generate_interview_prep: GenerateInterviewPrep
    generate_application_answers: GenerateApplicationAnswers
    list_applications: ListApplications
    download: DownloadFile
    update_status: UpdateApplicationStatus
    llm_providers: tuple[str, ...]      # available providers, for /api/config
    default_provider: str               # effective default (always available)


def _resume_header(settings: Settings) -> ContactHeader:
    links = tuple(s.strip() for s in settings.resume_links.split(",") if s.strip())
    return ContactHeader(
        name=settings.resume_full_name.strip(),
        location=settings.resume_location.strip() or None,
        email=settings.resume_email.strip() or None,
        phone=settings.resume_phone.strip() or None,
        links=links,
    )


def _build_llms(settings: Settings) -> dict[str, LLMClient]:
    """Provider registry. Anthropic is always present (its key is required);
    Gemini joins only when a key is configured."""
    llms: dict[str, LLMClient] = {
        "anthropic": AnthropicAdapter(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
        )
    }
    if settings.gemini_api_key:
        llms["gemini"] = GoogleAdapter(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            max_tokens=settings.gemini_max_tokens,
        )
    return llms


def effective_default_provider(settings: Settings, available: list[str]) -> str:
    """The configured default if it's available, else the first available
    provider — so the UI never pre-selects an unconfigured provider."""
    if settings.default_llm_provider in available:
        return settings.default_llm_provider
    return available[0]


def build_container(settings: Settings) -> Container:
    llms = _build_llms(settings)
    default_provider = effective_default_provider(settings, list(llms))
    drive = GoogleDriveStore(settings)
    sheets = GoogleSheetsAudit(settings)
    docs = DriveExperienceDocs(settings)
    renderer = DocxRenderer()

    return Container(
        generate=GenerateApplication(
            docs=docs, llms=llms, renderer=renderer, store=drive, audit_log=sheets,
            default_provider=default_provider, resume_header=_resume_header(settings),
        ),
        generate_interview_prep=GenerateInterviewPrep(
            docs=docs, llms=llms, store=drive, default_provider=default_provider,
        ),
        generate_application_answers=GenerateApplicationAnswers(
            docs=docs, llms=llms, renderer=renderer, store=drive,
            default_provider=default_provider,
        ),
        list_applications=ListApplications(audit_log=sheets),
        download=DownloadFile(store=drive, candidate_name=settings.resume_full_name.strip()),
        update_status=UpdateApplicationStatus(audit_log=sheets),
        llm_providers=tuple(llms),
        default_provider=default_provider,
    )
