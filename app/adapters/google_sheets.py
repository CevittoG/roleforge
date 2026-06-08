"""Google Sheets adapter implementing AuditLog.

Two tabs:
  - Applications: one row per generation (wide, with delimited summary columns).
  - Skills: one row per (application, skill) in LONG format, for pattern mining.
    Rank your recurring gaps with:
      =QUERY(Skills!A:F,"select D, count(D) where F='missing'
                          group by D order by count(D) desc")
"""
from __future__ import annotations

from googleapiclient.discovery import build

from app.adapters.google_auth import build_credentials
from app.config import Settings
from app.domain.models import ApplicationRecord, SkillItem

DELIM = "; "

HEADER = [
    "date", "company", "role", "status", "seniority", "fit_score",
    "work_mode", "location", "pay", "benefits",
    "key_requirements", "tech_stack", "matched_experience", "missing_experience", "concerns",
    "jd_source_url", "folder_url", "folder_id",
]  # 18 cols -> A:R

SKILLS_HEADER = ["date", "company", "role", "skill", "category", "status"]  # A:F


class GoogleSheetsAudit:
    def __init__(self, settings: Settings) -> None:
        self._svc = build("sheets", "v4", credentials=build_credentials(settings),
                          cache_discovery=False)
        self._sheet_id = settings.sheet_id
        self._tab = settings.sheet_tab
        self._skills_tab = settings.sheet_skills_tab

    def find(self, *, company: str, role: str) -> ApplicationRecord | None:
        match = None
        for rec in self.list_all():
            if rec.company.casefold() == company.casefold() and \
               rec.role.casefold() == role.casefold():
                match = rec  # latest wins
        return match

    def append(self, record: ApplicationRecord) -> None:
        self._svc.spreadsheets().values().append(
            spreadsheetId=self._sheet_id, range=f"{self._tab}!A:R",
            valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": [self._to_row(record)]},
        ).execute()

        skill_rows = self._skill_rows(record)
        if skill_rows:
            self._svc.spreadsheets().values().append(
                spreadsheetId=self._sheet_id, range=f"{self._skills_tab}!A:F",
                valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                body={"values": skill_rows},
            ).execute()

    def list_all(self) -> list[ApplicationRecord]:
        res = self._svc.spreadsheets().values().get(
            spreadsheetId=self._sheet_id, range=f"{self._tab}!A2:R",
        ).execute()
        return [self._from_row(r) for r in res.get("values", []) if r]

    # --- mapping ---
    @staticmethod
    def _to_row(r: ApplicationRecord) -> list[str]:
        return [
            r.date, r.company, r.role, r.status, r.seniority,
            "" if r.fit_score is None else str(r.fit_score),
            r.work_mode, r.location or "", r.pay or "", r.benefits or "",
            DELIM.join(r.key_requirements), DELIM.join(r.tech_stack),
            DELIM.join(s.name for s in r.matched),
            DELIM.join(s.name for s in r.missing),
            r.concerns or "", r.jd_source_url or "", r.folder_url, r.folder_id,
        ]

    @staticmethod
    def _skill_rows(r: ApplicationRecord) -> list[list[str]]:
        rows: list[list[str]] = []
        for s in r.matched:
            rows.append([r.date, r.company, r.role, s.name, s.category, "matched"])
        for s in r.missing:
            rows.append([r.date, r.company, r.role, s.name, s.category, "missing"])
        return rows

    @staticmethod
    def _split(cell: str) -> tuple[str, ...]:
        return tuple(p.strip() for p in cell.split(";") if p.strip()) if cell else ()

    @classmethod
    def _from_row(cls, row: list[str]) -> ApplicationRecord:
        cells = (row + [""] * len(HEADER))[: len(HEADER)]
        d = dict(zip(HEADER, cells, strict=False))
        fit = d["fit_score"].strip()
        return ApplicationRecord(
            date=d["date"], company=d["company"], role=d["role"], status=d["status"],
            work_mode=d["work_mode"], location=d["location"] or None, pay=d["pay"] or None,
            benefits=d["benefits"] or None, jd_source_url=d["jd_source_url"] or None,
            folder_url=d["folder_url"], folder_id=d["folder_id"],
            seniority=d["seniority"], fit_score=int(fit) if fit.isdigit() else None,
            key_requirements=cls._split(d["key_requirements"]),
            tech_stack=cls._split(d["tech_stack"]),
            matched=tuple(SkillItem(n) for n in cls._split(d["matched_experience"])),
            missing=tuple(SkillItem(n) for n in cls._split(d["missing_experience"])),
            concerns=d["concerns"] or None,
        )
