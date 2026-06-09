"""PdfRenderer adapter. HTML+CSS templates -> PDF so layout is OURS, stable
across runs regardless of model output."""
from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.domain.models import AuditFields, CoverLetterContent, ResumeContent

_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


class WeasyPrintRenderer:
    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(_TEMPLATES),
            autoescape=select_autoescape(["html"]),  # escapes model content -> no HTML injection
        )

    def render_resume(self, content: ResumeContent) -> bytes:
        return self._render("resume.html", resume=content)

    def render_cover_letter(self, content: CoverLetterContent) -> bytes:
        return self._render("cover_letter.html", letter=content)

    def render_match_report(self, audit: AuditFields) -> str:
        # Markdown output — no autoescape needed; the template controls the
        # structure and the values are plain text from the model.
        tmpl = self._env.get_template("match_report.md.j2")
        return tmpl.render(audit=audit)

    def _render(self, template: str, **ctx: Any) -> bytes:
        html = self._env.get_template(template).render(**ctx)
        return cast(bytes, HTML(string=html, base_url=str(_TEMPLATES)).write_pdf())
