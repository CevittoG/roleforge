"""On-demand interview prep for an already-generated application.

Kept out of the main `generate` call because output tokens cost ~5x input and
prep is only needed for applications that actually advance. Reads the JD back
from the role folder, re-runs the experience docs through a focused prompt, and
writes Interview_Prep.md into the same folder.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import INTERVIEW_PREP_MD, JOB_DESCRIPTION_MD, JobDescription
from app.domain.ports import ExperienceDocStore, LLMClient, OutputStore


@dataclass(frozen=True)
class GenerateInterviewPrep:
    docs: ExperienceDocStore
    llm: LLMClient
    store: OutputStore

    def __call__(self, *, folder_id: str) -> None:
        jd_bytes, _ = self.store.read_file(folder_id=folder_id, filename=JOB_DESCRIPTION_MD)
        jd = JobDescription(text=jd_bytes.decode("utf-8", errors="replace"))
        prep_md = self.llm.generate_interview_prep(
            experience_docs=self.docs.load_concatenated(), jd=jd
        )
        self.store.save_text(folder_id=folder_id, filename=INTERVIEW_PREP_MD, text=prep_md)
