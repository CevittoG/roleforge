"""Composition root. The ONLY place adapters are instantiated and wired into
use cases. Everything else depends on ports, not concretions."""
from __future__ import annotations

from dataclasses import dataclass

from app.adapters.anthropic_llm import AnthropicAdapter
from app.adapters.docx_resume import DocxRenderer
from app.adapters.experience_docs import DriveExperienceDocs
from app.adapters.google_drive import GoogleDriveStore
from app.adapters.google_sheets import GoogleSheetsAudit
from app.config import Settings
from app.domain.models import ContactHeader
from app.usecases.download_file import DownloadFile
from app.usecases.generate_application import GenerateApplication
from app.usecases.generate_interview_prep import GenerateInterviewPrep
from app.usecases.list_applications import ListApplications
from app.usecases.update_application_status import UpdateApplicationStatus


@dataclass(frozen=True)
class Container:
    generate: GenerateApplication
    generate_interview_prep: GenerateInterviewPrep
    list_applications: ListApplications
    download: DownloadFile
    update_status: UpdateApplicationStatus


def _resume_header(settings: Settings) -> ContactHeader:
    links = tuple(s.strip() for s in settings.resume_links.split(",") if s.strip())
    return ContactHeader(
        name=settings.resume_full_name.strip(),
        location=settings.resume_location.strip() or None,
        email=settings.resume_email.strip() or None,
        phone=settings.resume_phone.strip() or None,
        links=links,
    )


def build_container(settings: Settings) -> Container:
    llm = AnthropicAdapter(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        max_tokens=settings.anthropic_max_tokens,
    )
    drive = GoogleDriveStore(settings)
    sheets = GoogleSheetsAudit(settings)
    docs = DriveExperienceDocs(settings)
    renderer = DocxRenderer()

    return Container(
        generate=GenerateApplication(
            docs=docs, llm=llm, renderer=renderer, store=drive, audit_log=sheets,
            resume_header=_resume_header(settings),
        ),
        generate_interview_prep=GenerateInterviewPrep(docs=docs, llm=llm, store=drive),
        list_applications=ListApplications(audit_log=sheets),
        download=DownloadFile(store=drive),
        update_status=UpdateApplicationStatus(audit_log=sheets),
    )
