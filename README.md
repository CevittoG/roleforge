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
   resources; accept the `drive.file` + `spreadsheets` scopes. The script
   prints the refresh token — paste it into `.env` as
   `GOOGLE_REFRESH_TOKEN`.
5. **Create the Drive resources via the same account.** In Drive, create:
   - an `Experience Docs` folder (drop your career markdown files inside),
   - a `Job Applications` root folder.

   The `drive.file` scope is per-file — the token can only see files it
   creates or *opens* through itself. Folders created before this bootstrap
   are invisible to the token; either recreate them or open them once via
   the app (`scripts/smoke_drive.py` does the latter for the output root).
   Copy each folder ID (the last URL segment) into `.env` as
   `DRIVE_EXPERIENCE_FOLDER_ID` and `DRIVE_OUTPUT_ROOT_FOLDER_ID`.
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

## Run locally

`pip install .` then `uvicorn app.main:app --reload` with a populated `.env`.
