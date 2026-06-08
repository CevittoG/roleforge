"""Smoke test: append + read + auto-clean a synthetic row in the audit Sheet.

Run:
    python -m scripts.smoke_sheets

Captures the current row counts in `Applications` and `Skills`, appends a
synthetic ApplicationRecord (1 row in Applications, 4 rows in Skills),
verifies it shows up via `list_all`, then clears the exact ranges it
wrote so the smoke leaves no residue. Prints the cleared ranges for the
user to spot-check in the Sheet UI.
"""
from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build

from app.adapters.google_auth import build_credentials
from app.adapters.google_sheets import GoogleSheetsAudit
from app.config import get_settings
from app.domain.models import ApplicationRecord, SkillItem

SYNTHETIC = ApplicationRecord(
    date="2099-01-01",
    company="__roleforge_smoke__",
    role="__smoke_role__",
    status="generated",
    work_mode="remote",
    location="Nowhere",
    pay="$0",
    benefits=None,
    jd_source_url=None,
    folder_url="https://drive.google.com/drive/folders/SMOKE",
    folder_id="SMOKE",
    seniority="ic",
    fit_score=0,
    key_requirements=("smoke",),
    tech_stack=("smoke-stack",),
    matched=(SkillItem("Python", "language"), SkillItem("Smoke", "other")),
    missing=(SkillItem("Rust", "language"), SkillItem("Telepathy", "other")),
    concerns="synthetic — safe to delete",
)


def _row_count(svc: Any, sheet_id: str, tab: str, col: str) -> int:
    res = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"{tab}!{col}:{col}",
    ).execute()
    return len(res.get("values", []))


def main() -> None:
    settings = get_settings()
    audit = GoogleSheetsAudit(settings)
    svc = build("sheets", "v4", credentials=build_credentials(settings),
                cache_discovery=False)

    apps_tab = settings.sheet_tab
    skills_tab = settings.sheet_skills_tab

    apps_before = _row_count(svc, settings.sheet_id, apps_tab, "A")
    skills_before = _row_count(svc, settings.sheet_id, skills_tab, "A")
    print(f"Pre-append row counts: {apps_tab}={apps_before}, {skills_tab}={skills_before}")

    audit.append(SYNTHETIC)

    found = audit.find(company=SYNTHETIC.company, role=SYNTHETIC.role)
    assert found is not None, "appended row not visible via list_all"
    assert found.fit_score == 0
    assert {s.name for s in found.matched} == {"Python", "Smoke"}
    assert {s.name for s in found.missing} == {"Rust", "Telepathy"}
    print("list_all round-trip OK.")

    apps_row = apps_before + 1
    skills_start = skills_before + 1
    skills_end = skills_before + len(SYNTHETIC.matched) + len(SYNTHETIC.missing)
    apps_range = f"{apps_tab}!A{apps_row}:R{apps_row}"
    skills_range = f"{skills_tab}!A{skills_start}:F{skills_end}"

    svc.spreadsheets().values().clear(
        spreadsheetId=settings.sheet_id, range=apps_range, body={},
    ).execute()
    svc.spreadsheets().values().clear(
        spreadsheetId=settings.sheet_id, range=skills_range, body={},
    ).execute()
    print(f"Cleared {apps_range} and {skills_range}.")
    print("Spot-check the Sheet UI to confirm no residue.")


if __name__ == "__main__":
    main()
