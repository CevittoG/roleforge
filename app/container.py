"""Composition root. The ONLY place adapters are instantiated and wired into
use cases. Everything else depends on ports, not concretions."""
from __future__ import annotations

from dataclasses import dataclass

from app.adapters.anthropic_llm import AnthropicAdapter
from app.adapters.experience_docs import DriveExperienceDocs
from app.adapters.google_drive import GoogleDriveStore
from app.adapters.google_sheets import GoogleSheetsAudit
from app.adapters.weasyprint_pdf import WeasyPrintRenderer
from app.config import Settings
from app.usecases.download_file import DownloadFile
from app.usecases.generate_application import GenerateApplication
from app.usecases.list_applications import ListApplications
from app.usecases.update_application_status import UpdateApplicationStatus


@dataclass(frozen=True)
class Container:
    generate: GenerateApplication
    list_applications: ListApplications
    download: DownloadFile
    update_status: UpdateApplicationStatus


def build_container(settings: Settings) -> Container:
    llm = AnthropicAdapter(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        max_tokens=settings.anthropic_max_tokens,
    )
    drive = GoogleDriveStore(settings)
    sheets = GoogleSheetsAudit(settings)
    docs = DriveExperienceDocs(settings)
    pdf = WeasyPrintRenderer()

    return Container(
        generate=GenerateApplication(
            docs=docs, llm=llm, pdf=pdf, store=drive, audit_log=sheets
        ),
        list_applications=ListApplications(audit_log=sheets),
        download=DownloadFile(store=drive),
        update_status=UpdateApplicationStatus(audit_log=sheets),
    )
