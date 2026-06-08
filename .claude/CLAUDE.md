# Roleforge — Project Context for Claude

Private, single-user **Job Application Generator**: paste a JD (or URL), call
Claude once, produce a tailored Resume.pdf + Cover_Letter.pdf + Job_Description.md
+ Interview_Prep.md, save them to Google Drive under
`Job Applications/<Company>/<Role>/`, log a row to a Google Sheet for cross-role
gap analysis, and serve a mobile-first history view. Cost target ≈ $0 infra,
pennies of Claude tokens per run.

`plan.md` at the repo root (gitignored) is the source of truth for phase status
and the next-phase to-do list. **Read it first** every session — it tells you
what's done and what to pick up next. The original build prompt is the spec;
its hard invariants are reproduced below.

---

## Hard invariants — do NOT change without asking

- **Ports & adapters / SOLID.** `app/domain/` (ports + models) and
  `app/usecases/` must never import a vendor SDK or FastAPI. They depend only on
  the `Protocol`s in `app/domain/ports.py`. Adapters are the only place vendor
  SDKs appear, and they're constructed in exactly one place: `app/container.py`.
- **Single process.** FastAPI serves `/api/*` and the Next.js *static export* at
  `/`. One Docker image, one Render service, no CORS, no Node at runtime, no
  reverse proxy.
- **Security on every `/api` route** via `verify_access` (Cloudflare Access JWT
  *and* `X-Origin-Secret`). Keep the SSRF guard on the URL fetcher. Keep
  least-privilege Google scopes (`drive.file` + `spreadsheets`) — never request
  full `drive`.
- **PDF layout lives in our templates/CSS**, never in model output. The model
  returns structured JSON; Jinja + WeasyPrint render it.
- **Skills are short canonical tags** (`Kubernetes`, `Apache Spark`,
  `team leadership`); gap analysis is **honest** — `missing` means
  required/preferred but not evidenced in the user's docs.
- **No secrets in the frontend or the Docker image.** Secrets come from Render
  env / secret files at runtime. The client only ever calls same-origin
  `/api/...`.
- **Mobile-first frontend.** Primary device is Android phone. Design for
  ~360–412px first, single column. Touch targets ≥ 44px. Generation can take
  30–90s — show a clear progress state and account for Render free-tier cold
  starts (~1 min first request).

## Non-goals

Multi-user auth, login UI (Cloudflare Access handles auth at the edge),
switching hosting/LLM providers, SSR / server actions.

## Tech stack (pinned)

- **Backend:** Python 3.12 (Docker) / 3.14 (local dev), FastAPI 0.115,
  pydantic 2, pydantic-settings 2, WeasyPrint 63, google-api-python-client 2,
  anthropic 0.40, PyJWT 2 (with crypto), httpx 0.27, Jinja2 3.
- **Frontend (not yet scaffolded):** Next.js with `output: 'export'`,
  TypeScript, Tailwind CSS, shadcn/ui. Keep deps minimal for mobile perf.
- **LLM:** Claude (`claude-sonnet-4-6` default). Keep prompt caching on the
  experience-docs block (`cache_control: ephemeral`).
- **Tooling:** `ruff` (lint) + `mypy` (strict) wired via `Makefile`.

## Local-dev quirks

- **WeasyPrint on macOS** needs Homebrew dylibs (pango/cairo/gdk-pixbuf/libffi).
  The `Makefile` injects `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` for
  `make run` and `make type`. Always use the Make targets; don't call
  `uvicorn`/`mypy` directly.
- **`AUTH_REQUIRED=false`** in local `.env` short-circuits `verify_access` with
  a stub claims dict. The dependency stays wired on every `/api` route — only
  the body no-ops. Default is `true`. Never ship `false` to production.
- **Python 3.14 locally** (only version installed). Production runtime is the
  `python:3.12-slim` image from the Dockerfile. Watch for behavior divergence
  if anything looks weird locally.
- `.env` is gitignored. `.env.example` documents every required setting.

## Conventions

- **Commands:** `make check` (ruff + mypy), `make run` (uvicorn --reload),
  `make lint`, `make type`, `make install`.
- **Style:** ruff with `E, F, I, B, UP, SIM, PL, RUF` selected. `B008` ignored
  (FastAPI's `Depends`/`Query` in defaults is the framework pattern).
- **Types:** mypy strict, `pydantic.mypy` plugin enabled. Vendor modules
  without stubs (`googleapiclient.*`, `google.oauth2.*`, `weasyprint.*`,
  `anthropic.*`, `jwt.*`) are whitelisted with `ignore_missing_imports`. When
  SDK stubs are wrong (e.g. `cache_control` on Anthropic TextBlockParam), use a
  narrow `cast(Any, ...)` with a one-line comment naming the SDK gap — don't
  blanket-ignore.
- **Imports/from __future__ import annotations** at the top of every Python file.
- **Tests:** when added, use **fake adapters** that satisfy the ports so the
  core stays testable without network or credentials.

## Commit policy (important)

- **Never commit without explicit, in-the-moment review confirmation from the
  user.** A plan saying "commit per phase" is *not* standing authorization.
  When a chunk of work finishes, surface what changed and ask whether to
  commit; default to waiting.
- Conventional commits (`feat`, `fix`, `chore`, `docs`, `refactor`, `test`,
  `style`, `ci`, `perf`, `build`). Imperative title ≤ 72 chars. 2–4 bullets
  explaining *what and why*, not which files.
- One concern per commit; commits should be independently revertable.
- Never `--no-verify`, never bypass hooks.

## Key files & where to look

- `app/domain/ports.py` — the Protocols the core depends on.
- `app/domain/models.py` — domain dataclasses + the four output filenames +
  `DOWNLOADABLE` alias map.
- `app/container.py` — the *only* place adapters are instantiated.
- `app/main.py` — FastAPI app factory; security headers middleware; static
  mount at `/` is added LAST so it doesn't shadow `/api`.
- `app/web/routers.py` — three endpoints: `POST /api/generate`,
  `GET /api/applications`, `GET /api/download`. `/api/healthz` for ops.
- `app/security/cf_access.py` — JWT verification + origin-secret check +
  the `auth_required` escape hatch.
- `app/security/ssrf.py` — blocks non-HTTP schemes, private/loopback IPs, and
  redirects on the JD URL fetcher.
- `app/adapters/anthropic_llm.py` — single cache-flagged call producing one
  JSON object. `SKILL_SYSTEM_PROMPT` is the user's tailoring rubric (the user
  will provide / refine the experience-specific text in Phase 3).
- `app/adapters/google_sheets.py` — two-tab audit log: `Applications` (A:R)
  wide row + `Skills` (A:F) long-format fan-out.
- `app/adapters/google_drive.py` — folder-per-(Company, Role) with upsert.
- `app/adapters/weasyprint_pdf.py` — Jinja + WeasyPrint; templates in
  `app/templates/`.
- `Dockerfile` — multi-stage: Node builds the Next static export, Python image
  copies it into `app/static/`, single uvicorn process serves both.

## Sheet schema (do not change column order)

**Applications** (A:R, row 1 = header):
`date, company, role, status, seniority, fit_score, work_mode, location, pay,
benefits, key_requirements, tech_stack, matched_experience, missing_experience,
concerns, jd_source_url, folder_url, folder_id`

**Skills** (A:F, long format):
`date, company, role, skill, category, status` — `status` is `matched` or
`missing`. Recurring-gap query:

```
=QUERY(Skills!A:F,"select D, count(D) where F='missing' group by D order by count(D) desc")
```

## When you're unsure

- Check `plan.md` first — it has the phase status and next-phase task list.
- The original build prompt is the spec; the README mirrors the architecture
  and security checklist. The Sheet schema and the OAuth setup are documented
  in `README.md`.
- If a task seems to require breaking a hard invariant, **stop and ask** — don't
  silently reshape the architecture.
- If you need a real secret, an ID, or the skill-prompt text, ask — never
  fabricate.
