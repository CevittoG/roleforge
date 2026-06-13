"""On-demand application-question answers for an already-generated application.

The primary path answers questions inline during the main `generate` call (max
context reuse, fully coherent with the resume + cover letter). This use case
covers the secondary case: questions that surface *after* generating. It reads
the JD back from the role folder, re-runs the experience docs (hitting the
prompt cache) through a focused prompt, and writes Application_Questions.docx
(enumerated Q&A) into the same folder.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.domain.models import (
    APPLICATION_QUESTIONS_DOCX,
    DOCX_MIME,
    JOB_DESCRIPTION_MD,
    JobDescription,
)
from app.domain.ports import DocumentRenderer, ExperienceDocStore, LLMClient, OutputStore


@dataclass(frozen=True)
class GenerateApplicationAnswers:
    docs: ExperienceDocStore
    llms: Mapping[str, LLMClient]
    renderer: DocumentRenderer
    store: OutputStore
    default_provider: str = "anthropic"

    def __call__(
        self, *, folder_id: str, questions: str, provider: str | None = None
    ) -> None:
        jd_bytes, _ = self.store.read_file(folder_id=folder_id, filename=JOB_DESCRIPTION_MD)
        jd = JobDescription(text=jd_bytes.decode("utf-8", errors="replace"))
        chosen = provider or self.default_provider
        if chosen not in self.llms:
            chosen = self.default_provider
        answers = self.llms[chosen].generate_application_answers(
            experience_docs=self.docs.load_concatenated(), jd=jd, questions=questions
        )
        docx_bytes = self.renderer.render_application_questions_docx(answers)
        self.store.save_bytes(
            folder_id=folder_id, filename=APPLICATION_QUESTIONS_DOCX,
            data=docx_bytes, mime=DOCX_MIME,
        )
