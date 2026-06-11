# Job Application Generator

Private, single-user app: paste a job description, generate a tailored
**Resume** (saved as an editable Google Doc; download as PDF on demand),
**Cover_Letter.txt**, **Job_Description.md**, and **Match_Report.md**, save them
to Google Drive, and log a queryable row to a Google Sheet. **Interview_Prep.md**
is generated on demand (a second, cheaper call). Browse, re-download, and track
status on past applications from history.

## Architecture (ports & adapters)

- `app/domain/` — models + `ports.py` (Protocols). No vendor/framework imports.
- `app/usecases/` — one responsibility each: `GenerateApplication`,
  `CheckDuplicate`, `ListApplications`, `UpdateApplicationStatus`, `DownloadFile`.
- `app/adapters/` — Anthropic, Google Drive/Sheets, docx renderer (python-docx).
  Swap a vendor = new adapter, zero core changes (Open/Closed + DIP).
- `app/web/` — thin FastAPI routers, schemas, deps.
- `app/security/` — Cloudflare Access JWT verification.
- `app/container.py` — the only place adapters are constructed and injected.

Single process: FastAPI serves the API at `/api` and the Next static export
at `/`. One Docker image, one Render service, no CORS.

## Endpoints

- `POST  /api/generate` → `202` (job enqueued).
- `GET   /api/jobs/{job_id}` → poll for status; `done | duplicate | error`.
- `GET   /api/applications` → history rows from the Sheet.
- `PATCH /api/applications/{folder_id}/status` → update one application's
  status. Body: `{"status": "Applied"}` (one of Generated, Applied, Interview,
  Offer, Rejected, Withdrawn, Ghosted, On hold).
- `POST  /api/applications/{folder_id}/interview-prep` → generate Interview_Prep.md
  on demand (`204`). Synchronous; one short LLM call.
- `GET   /api/download?folder_id&file` → streams a file as an attachment
  (`file=resume` exports the resume Google Doc to PDF).
- `GET   /api/config` → frontend-visible non-secrets (e.g. `insights_url`).

## Security checklist

**Cloudflare:** Access (Zero Trust) gating the hostname to your email; proxied
DNS; SSL Full (Strict) + HSTS; WAF + rate limiting. Inject `X-Origin-Secret`
via a Transform Rule.
**Render:** lock origin to Cloudflare (Authenticated Origin Pulls) so the
`*.onrender.com` URL can't be hit directly; secrets as env/secret files;
container runs non-root.
**Backend:** verifies the Access JWT *and* the origin secret on every `/api`
route; JD ingestion is paste-only so no outbound HTTP fetches sit on the
request path; Pydantic input caps; least-privilege Google scopes
(`drive.readonly` + `drive.file` + `spreadsheets`); locked CSP/HSTS headers;
set an Anthropic spend cap + alert.

## Google auth (own account)

One-time bootstrap. Steps 1–4 mint the refresh token; steps 5–6 wire up the
Drive folders and Sheet the app will read/write.

1. **Create an OAuth client.** Google Cloud Console → APIs & Services →
   Credentials → *Create Credentials* → *OAuth client ID* → type
   **Desktop**. Enable the **Google Drive API** and **Google Sheets API**
   on the project while you're there.
2. **Set the consent screen to "In production".** Console → OAuth consent
   screen → *Publish app*. ⚠️ **If you skip this**, the refresh token
   silently expires after 7 days and you'll find out the hard way. Staying
   unverified is fine for a single-user app — verification is only required
   if you grant access to other users.
3. **Put the client creds in `.env`.** Set `GOOGLE_CLIENT_ID` and
   `GOOGLE_CLIENT_SECRET` from the credential you just created.
4. **Mint the refresh token.** Run:
   ```
   python -m scripts.get_refresh_token
   ```
   A browser opens; sign in with the account that owns the Drive/Sheet
   resources; accept the `drive.readonly` + `drive.file` + `spreadsheets`
   scopes (Google flags `drive.readonly` as "sensitive" — that's expected
   for a single-user self-hosted app). The script prints the refresh token
   — paste it into `.env` as `GOOGLE_REFRESH_TOKEN`.
5. **Create the Drive folders.** Either via the API:
   ```
   python -m scripts.setup_drive
   ```
   or by creating two folders in the Drive UI yourself — both work because
   the token now has `drive.readonly` and can see anything the account owns.
   Paste each folder ID (the last segment of the Drive URL) into `.env` as
   `DRIVE_EXPERIENCE_FOLDER_ID` and `DRIVE_OUTPUT_ROOT_FOLDER_ID`.

   Drop your experience `.md` files into the Experience Docs folder however
   you like — UI drag-and-drop, Drive desktop sync, or
   `python -m scripts.upload_experience_docs <local-dir>` for bulk work.
   The token reads them all the same way.
6. **Create the Sheet.** New spreadsheet with two tabs named exactly
   `Applications` and `Skills`, headers per [§ Sheets](#sheets-two-tabs)
   below. Share it with the OAuth account (it does that automatically if
   you're signed in as that account). Copy the spreadsheet ID into `.env`
   as `SHEET_ID`.

After this, the smoke scripts confirm each adapter end-to-end:
`python -m scripts.smoke_experience_docs`, `…smoke_drive`, `…smoke_sheets`,
`…smoke_anthropic`.

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

### Insights tab (optional, surfaced in the app)

Add a third tab named `Insights` with that `=QUERY` pinned to `A1`:

```
=QUERY(Skills!A:F, "select D, count(D) where F='missing' group by D order by count(D) desc label count(D) 'count'", 1)
```

Then set `SHEET_INSIGHTS_URL` in `.env` to a deep-link to that tab (the URL
in Sheets has a `#gid=<n>` suffix per tab). The History view in the app
renders an **Open Insights in Sheets →** link when this env var is present.

## Run locally

`pip install .` then `uvicorn app.main:app --reload` with a populated `.env`
(or `make run`). No system libraries are needed — the resume is built with
python-docx and converted to a Google Doc by Drive on upload.

**Resume header:** set `RESUME_FULL_NAME`, `RESUME_EMAIL`, `RESUME_PHONE`,
`RESUME_LOCATION`, and `RESUME_LINKS` (comma-separated) in `.env`. These are
injected verbatim into the resume header and the cover-letter signature — the
model never sees or invents contact data — so a blank value just omits that
field. See `.env.example`.
