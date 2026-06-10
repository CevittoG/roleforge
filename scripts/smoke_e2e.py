"""Phase-3 end-to-end smoke test: full GenerateApplication pipeline.

Run:
    python -m scripts.smoke_e2e            # uses scripts/jds/*.txt
    python -m scripts.smoke_e2e path/to/jd1.txt path/to/jd2.txt ...

For each JD file the script:
  1. Calls container.generate(GenerationRequest(raw_text=<jd>)) →
     creates Drive folder, writes the 5 files, appends the audit row.
  2. On the FIRST JD only: re-runs without confirm_overwrite → expects
     DuplicateApplicationError; then re-runs WITH confirm_overwrite → expects
     success and a second audit row appended (overwrite semantics: files
     re-saved in place, audit log keeps history).

Prints `usage` per call so you can eyeball cache hits across the run (the
adapter logs it at INFO; we set basicConfig below). No cleanup — leftover
Drive folders / Sheet rows ARE the evidence trail for the manual spot-check.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.config import get_settings
from app.container import build_container
from app.usecases.errors import DuplicateApplicationError
from app.usecases.generate_application import GenerationRequest

_JD_DIR = Path(__file__).resolve().parent / "jds"


def _load_jds(argv: list[str]) -> list[tuple[str, str]]:
    """Return [(label, text)] from CLI args or scripts/jds/*.txt."""
    paths: list[Path] = [Path(a) for a in argv] if argv else sorted(_JD_DIR.glob("*.txt"))
    if not paths:
        raise SystemExit(
            f"No JDs found. Pass paths on the CLI or drop *.txt files into {_JD_DIR}."
        )
    out: list[tuple[str, str]] = []
    for p in paths:
        text = p.read_text(encoding="utf-8").strip()
        if not text:
            raise SystemExit(f"{p} is empty.")
        out.append((p.name, text))
    return out


def main(argv: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    jds = _load_jds(argv)
    print(f"Loaded {len(jds)} JD(s): {', '.join(label for label, _ in jds)}")

    container = build_container(get_settings())

    for i, (label, text) in enumerate(jds, start=1):
        print(f"\n=== JD #{i}: {label} ===")
        record = container.generate(GenerationRequest(raw_text=text))
        print(
            f"OK · company={record.company!r} role={record.role!r} "
            f"fit_score={record.fit_score} folder={record.folder_url}"
        )
        print(
            f"matched={[s.name for s in record.matched]} "
            f"missing={[s.name for s in record.missing]}"
        )

        if i == 1:
            print("\n--- duplicate flow on JD #1 ---")
            try:
                container.generate(GenerationRequest(raw_text=text))
            except DuplicateApplicationError as exc:
                ex = exc.existing
                assert ex.company == record.company and ex.role == record.role
                print(f"409 OK · existing={ex.company} / {ex.role} at {ex.folder_url}")
            else:
                raise AssertionError("Expected DuplicateApplicationError on re-run")

            print("\n--- overwrite flow on JD #1 ---")
            again = container.generate(
                GenerationRequest(raw_text=text, confirm_overwrite=True)
            )
            assert again.folder_id == record.folder_id, "overwrite created a new folder"
            print(f"overwrite OK · same folder_id={again.folder_id}")

    print("\nDone. Open the Drive folders + Sheet tabs to spot-check the artifacts.")


if __name__ == "__main__":
    main(sys.argv[1:])
