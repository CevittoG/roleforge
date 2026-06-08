# Job Application Generator

Private, single-user app: paste a job description (or URL), generate a tailored
**Resume.pdf**, **Cover_Letter.pdf**, **Job_Description.md**, and
**Interview_Prep.md**, save them to Google Drive, and log a queryable row to a
Google Sheet. Browse and re-download past applications from history.

## Architecture (ports & adapters)

- `app/domain/` — models + `ports.py` (Protocols). No vendor/framework imports.
- `app/usecases/` — one responsibility each: `GenerateApplication`,
  `CheckDuplicate`, `ListApplications`, `DownloadFile`.
- `app/adapters/` — Anthropic, Google Drive/Sheets, JD source, WeasyPrint.
  Swap a vendor = new adapter, zero core changes (Open/Closed + DIP).
- `app/web/` — thin FastAPI routers, schemas, deps.
- `app/security/` — Cloudflare Access JWT verification + SSRF guard.
- `app/container.py` — the only place adapters are constructed and injected.

Single process: FastAPI serves the API at `/api` and the Next static export
at `/`. One Docker image, one Render service, no CORS.

## Endpoints

- `POST /api/generate` → `200` (created/overwritten) or `409` (duplicate; body
  carries the existing record so the UI can confirm overwrite).
- `GET  /api/applications` → history rows from the Sheet.
- `GET  /api/download?folder_id&file` → streams a file as an attachment.

## Security checklist

**Cloudflare:** Access (Zero Trust) gating the hostname to your email; proxied
DNS; SSL Full (Strict) + HSTS; WAF + rate limiting. Inject `X-Origin-Secret`
via a Transform Rule.
**Render:** lock origin to Cloudflare (Authenticated Origin Pulls) so the
`*.onrender.com` URL can't be hit directly; secrets as env/secret files;
container runs non-root.
**Backend:** verifies the Access JWT *and* the origin secret on every `/api`
route; SSRF guard on URL fetch (blocks private/loopback/metadata IPs, no
redirects, size + time caps); Pydantic input caps; least-privilege Google
scopes (`drive.file` + `spreadsheets`); locked CSP/HSTS headers; set an
Anthropic spend cap + alert.

## Google auth (own account)

Create an OAuth client (Desktop), consent once with scopes
`drive.file` + `spreadsheets`, store the **refresh token**. Set the OAuth app
to **In production** (you can stay unverified for your own single use) so the
token doesn't expire after 7 days. Then create the Drive `Experience Docs`
folder and `Job Applications` root *with the app* (or open them through it) so
`drive.file` can reach them, and put their IDs + the Sheet ID in env.

## Sheets (two tabs)

**Applications** (row 1 header, order matters):
`date, company, role, status, seniority, fit_score, work_mode, location, pay,
benefits, key_requirements, tech_stack, matched_experience, missing_experience,
concerns, jd_source_url, folder_url, folder_id`

**Skills** (long format, one row per skill — header):
`date, company, role, skill, category, status`  (status = matched | missing)

The app fans each generation's matched/missing skills into the Skills tab.
Rank recurring gaps across all applications (what to learn next):
```
=QUERY(Skills!A:F,"select D, count(D) where F='missing' group by D order by count(D) desc")
```
Swap `'missing'` for `'matched'` to see your most-leveraged strengths, or add
`category` to the select to see whether gaps cluster by area.

## Run locally

`pip install .` then `uvicorn app.main:app --reload` with a populated `.env`.
