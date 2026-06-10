# Roleforge — Project Context for Claude

Private, single-user **Job Application Generator**: paste a JD, call
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
  *and* `X-Origin-Secret`). JD ingestion is **paste-only** — URL fetching and the
  SSRF guard were removed in Phase 6, so there is no outbound HTTP fetch on the
  request path. Keep least-privilege Google scopes
  (`drive.readonly` + `drive.file` + `spreadsheets`) —
  `drive.readonly` lets the token see user-managed experience docs in the Drive UI;
  `drive.file` writes outputs only to files the app created. Never request the bare
  `drive` scope (grants write to everything).
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
- **Frontend:** Next.js 14 (`output: 'export'`, `trailingSlash: true`),
  **pages router** — chosen because the backend CSP forbids inline scripts
  and app router emits them during hydration. TypeScript, Tailwind, Radix
  Dialog/Tabs, lucide-react. UI primitives are hand-authored under
  `frontend/src/components/ui/` (no shadcn CLI dependency).
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

- **Commands:** `make check` (ruff + mypy + pytest), `make run` (uvicorn --reload),
  `make lint`, `make type`, `make test`, `make install`, `make smoke-e2e`
  (end-to-end pipeline test against real JDs in `scripts/jds/*.txt`).
- **Style:** ruff with `E, F, I, B, UP, SIM, PL, RUF` selected. `B008` ignored
  (FastAPI's `Depends`/`Query` in defaults is the framework pattern).
- **Types:** mypy strict, `pydantic.mypy` plugin enabled. Vendor modules
  without stubs (`googleapiclient.*`, `google.oauth2.*`, `weasyprint.*`,
  `anthropic.*`, `jwt.*`) are whitelisted with `ignore_missing_imports`. When
  SDK stubs are wrong (e.g. `cache_control` on Anthropic TextBlockParam), use a
  narrow `cast(Any, ...)` with a one-line comment naming the SDK gap — don't
  blanket-ignore.
- **Imports/from __future__ import annotations** at the top of every Python file.
- **Tests:** pytest under `tests/`. `tests/conftest.py` has `FakeAuditLog`
  satisfying the `AuditLog` port; any future use-case tests should follow the
  same pattern (in-memory fake satisfies the structural port).

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
- `app/domain/models.py` — domain dataclasses + the five output filenames +
  `DOWNLOADABLE` alias map.
- `app/container.py` — the *only* place adapters are instantiated.
- `app/main.py` — FastAPI app factory; security headers middleware; static
  mount at `/` is added LAST so it doesn't shadow `/api`. Also owns the
  public `GET /healthz` (no auth) used by Render health checks + uptime pingers.
- `app/runtime/jobs.py` — in-process async job store (asyncio.Lock dict +
  1-worker ThreadPoolExecutor). Lifecycle: queued→running→done/duplicate/error.
  1h TTL with background sweeper. Wired via `app.state.job_store` in lifespan.
- `app/web/routers.py` — endpoints on the auth-gated `/api` prefix:
  `POST /api/generate` (202, enqueues), `GET /api/jobs/{id}` (poll),
  `GET /api/applications`, `PATCH /api/applications/{folder_id}/status`,
  `GET /api/download`, `GET /api/config` (frontend-visible non-secrets),
  `GET /api/healthz` (ops).
- `app/security/cf_access.py` — JWT verification + origin-secret check +
  the `auth_required` escape hatch.
- `app/adapters/anthropic_llm.py` — single cache-flagged call (system prompt
  + experience docs both cached) producing one JSON object. `SKILL_SYSTEM_PROMPT`
  is the throughline rubric: anti-hallucination contract, CAR resume rules,
  4-paragraph cover letter, and per-requirement scoring table.
- `app/adapters/google_sheets.py` — two-tab audit log: `Applications` (A:S)
  wide row + `Skills` (A:F) long-format fan-out.
- `app/adapters/google_drive.py` — folder-per-(Company, Role) with upsert.
- `app/adapters/weasyprint_pdf.py` — Jinja + WeasyPrint; templates in
  `app/templates/`.
- `Dockerfile` — multi-stage: Node builds the Next static export, Python image
  copies it into `app/static/`, single uvicorn process serves both.
- `frontend/src/pages/_app.tsx` — app shell, bottom nav, and the warm-ping to
  `/healthz` on mount + `visibilitychange` (masks Render cold start).
- `frontend/src/lib/types.ts` — TypeScript types hand-mirrored from
  `app/web/schemas.py`. Keep them in sync when changing a schema field.

## Sheet schema (do not change column order)

**Applications** (A:S, row 1 = header):
`date, company, role, status, seniority, fit_score, work_mode, location, pay,
benefits, key_requirements, tech_stack, matched_experience, missing_experience,
concerns, jd_source_url, folder_url, folder_id, jd_hash`

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
