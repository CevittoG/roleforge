# Roleforge — Project Context for Claude

Private, single-user **Job Application Generator**: paste a JD, call the chosen
LLM (Claude or Gemini) once, produce a tailored Resume (saved as an editable
Google Doc) + Cover_Letter.txt + Job_Description.md + Match_Report.md, save them
to Google Drive under `Job Applications/<Company>/<Role>/`, log a row to a Google
Sheet for cross-role gap analysis, and serve a mobile-first history view.
Optional **application questions** pasted on the generate form are answered in
the **same** call (Application_Questions.docx — a standalone enumerated Q&A Word
file, never folded into the resume), reusing the resume's grounded context. Interview_Prep.md — and application answers when the questions surface
*after* generating — are produced **on demand** in a second, cheaper call (not
part of the main generate) to save output tokens. Cost target ≈ $0 infra
(Gemini's free tier or pennies of Claude tokens per run).

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
- **Resume layout lives in our docx renderer**, never in model output. The model
  returns structured JSON; `app/adapters/docx_resume.py` (python-docx) renders the
  resume to a `.docx` (uploaded as a Google Doc), the cover letter is plain text,
  and the match report is Jinja-rendered Markdown. ATS-safety is load-bearing:
  single column, real selectable text, no tables/columns/images.
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
switching hosting, SSR / server actions. **LLM provider is selectable** —
Anthropic Claude and (optionally) Google Gemini are both wired behind one
`LLMClient` port; a UI toggle picks which one runs a given generate. Adding a
*third* vendor or swapping the whole stack to a different provider remains a
non-goal.

## Tech stack (pinned)

- **Backend:** Python 3.12 (Docker) / 3.14 (local dev), FastAPI 0.115,
  pydantic 2, pydantic-settings 2, python-docx 1, google-api-python-client 2,
  anthropic 0.40, google-genai 2 (Gemini), PyJWT 2 (with crypto), httpx 0.28,
  Jinja2 3.
- **Frontend:** Next.js 14 (`output: 'export'`, `trailingSlash: true`),
  **pages router** — chosen because the backend CSP forbids inline scripts
  and app router emits them during hydration. TypeScript, Tailwind, Radix
  Dialog/Tabs, lucide-react. UI primitives are hand-authored under
  `frontend/src/components/ui/` (no shadcn CLI dependency).
- **LLM:** Claude (`claude-sonnet-4-6`) or Gemini (`gemini-3.5-flash`), chosen
  per-request via a UI toggle; `DEFAULT_LLM_PROVIDER` (default `gemini`) sets the
  pre-selection. Keep prompt caching on the experience-docs block for Anthropic
  (`cache_control: ephemeral`); Gemini flash relies on implicit prefix caching.
  Gemini is optional — without `GEMINI_API_KEY` the toggle hides and every run
  uses Claude.
- **Tooling:** `ruff` (lint) + `mypy` (strict) wired via `Makefile`.

## Local-dev quirks

- **No system libraries.** The resume is built with python-docx (pure Python +
  lxml wheels) and converted to a Google Doc by Drive on upload — no Pango/Cairo
  and no `DYLD_FALLBACK_LIBRARY_PATH` shim (both removed with WeasyPrint). The
  Make targets call `uvicorn`/`mypy` directly.
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
  without stubs (`googleapiclient.*`, `google.oauth2.*`, `google.genai.*`,
  `docx.*`, `anthropic.*`, `jwt.*`) are whitelisted with `ignore_missing_imports`.
  When
  SDK stubs are wrong (e.g. `cache_control` on Anthropic TextBlockParam), use a
  narrow `cast(Any, ...)` with a one-line comment naming the SDK gap — don't
  blanket-ignore.
- **Imports/from __future__ import annotations** at the top of every Python file.
- **Tests:** pytest under `tests/`. `tests/conftest.py` has in-memory fakes for
  every port (`FakeAuditLog`, `FakeExperienceDocs`, `FakeLLM`, `FakeRenderer`,
  `FakeOutputStore`) plus builders (`make_generated`, `make_header`); future
  use-case tests should reuse them (a structural fake satisfies the Protocol).

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
- `app/domain/models.py` — domain dataclasses (incl. the structured resume:
  `ContactHeader` / `ExperienceEntry` / `EducationEntry` / `AdditionalLine`,
  plus `ApplicationAnswer` and `GeneratedContent.application_answers`) + the
  output filenames + the `DOWNLOADABLE` map (key → (Drive name, static fallback
  download name); the download use case rewrites the name to
  `<Name>-<Role>-<Date>-<Artifact>.<ext>` when role+date are supplied).
- `app/container.py` — the *only* place adapters are instantiated.
- `app/main.py` — FastAPI app factory; security headers middleware; static
  mount at `/` is added LAST so it doesn't shadow `/api`. Also owns the
  public `GET /healthz` (no auth) used by Render health checks + uptime pingers.
- `app/runtime/jobs.py` — in-process async job store (asyncio.Lock dict +
  1-worker ThreadPoolExecutor). Dispatches `RunRequest = GenerationRequest |
  RegenerationRequest` via isinstance; both share the same executor, TTL, and
  poll machinery. Lifecycle: queued→running→done/duplicate/error. 1h TTL with
  background sweeper. Wired via `app.state.job_store` in lifespan.
- `app/web/routers.py` — endpoints on the auth-gated `/api` prefix:
  `POST /api/generate` (202, enqueues; body carries optional
  `application_questions`), `GET /api/jobs/{id}` (poll),
  `GET /api/applications`, `PATCH /api/applications/{folder_id}/status`,
  `POST /api/applications/{folder_id}/interview-prep` (on-demand prep, 204, sync),
  `POST /api/applications/{folder_id}/application-questions` (on-demand answers,
  204, sync), `POST /api/applications/{folder_id}/regenerate` (202, enqueues a
  `RegenerationRequest`; poll via `GET /api/jobs/{id}` same as generate),
  `GET /api/download` (`file` ∈ resume | cover_letter |
  job_description | match_report | interview_prep | application_questions; optional
  `role`+`date` shape the filename), `GET /api/config` (frontend-visible
  non-secrets), `GET /api/healthz` (ops).
- `app/security/cf_access.py` — JWT verification + origin-secret check +
  the `auth_required` escape hatch.
- `app/adapters/llm_base.py` — `BaseLLMAdapter`: the provider-neutral half both
  LLM adapters inherit. Owns the persona + anti-hallucination + experience-docs
  prompts, the three entry points (`generate()` → one JSON object of audit +
  structured resume + cover letter [+ `application_answers` only when the request
  carries questions] via `SKILL_SYSTEM_PROMPT`; `generate_interview_prep()` →
  Markdown via `INTERVIEW_PREP_SYSTEM_PROMPT`; `generate_application_answers()` →
  Markdown via `APPLICATION_ANSWERS_SYSTEM_PROMPT`), and all JSON parsing /
  fence-stripping. Subclasses implement only the abstract `_call` transport (the
  optional questions/candidate-name ride the JD `jd_suffix`, so neither concrete
  adapter changes). The rubric covers the anti-hallucination contract, CAR resume
  rules (senior-level framing, a top `summary`, English-only degree with no GPA),
  the Harvard-style section set, the 4-paragraph cover letter, the per-requirement
  scoring table, and the first-person application-answer rules. `candidate_name`
  signs the cover letter.
- `app/adapters/anthropic_llm.py` / `app/adapters/google_llm.py` — the two
  transports. Anthropic cache-flags the system + experience-docs blocks
  (`cache_control: ephemeral`); Gemini sends `system_instruction` + `contents`
  and sets `response_mime_type` (relies on implicit caching). `app/container.py`
  builds a `{provider: LLMClient}` registry (Gemini only when keyed) and injects
  it plus the effective default into the use cases; `GenerationRequest.provider`
  / the interview-prep body select which one runs.
- `app/adapters/google_sheets.py` — two-tab audit log: `Applications` (A:S)
  wide row + `Skills` (A:F) long-format fan-out.
- `app/adapters/google_drive.py` — folder-per-(Company, Role) with upsert;
  `save_google_doc` converts an uploaded `.docx` to a native Google Doc;
  `read_file` exports a Google Doc to PDF on download. `ensure_error_folder`
  creates `Unknown - <date>/<uuid>` for failed runs; `move_folder` reparents +
  renames a folder via `files().update` (preserves folder id) when regen succeeds.
- `app/adapters/docx_resume.py` — `DocumentRenderer`: resume `.docx` via
  python-docx (ATS-safe, no tables; right tab stop for dates/location), cover
  letter as plain text, match report as Jinja Markdown
  (`app/templates/match_report.md.j2`).
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
