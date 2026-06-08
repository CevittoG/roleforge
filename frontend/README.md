# Frontend (Next.js static export)

Two views, both backed by the audit Sheet via the backend API:

- **Generate** — paste JD text or a URL → `POST /api/generate`.
  On `409` (duplicate Company+Role), show a confirm dialog and re-POST with
  `confirm_overwrite: true`.
- **History** — `GET /api/applications` → sortable list. Each row links to the
  Drive folder (`folder_url`) and offers in-app downloads via
  `GET /api/download?folder_id=<id>&file=<resume|cover_letter|job_description|interview_prep>`.

## Build (must be a static export)

`next.config.js`:
```js
/** @type {import('next').NextConfig} */
module.exports = { output: 'export', trailingSlash: true };
```

`npm run build` emits `./out`, which the Dockerfile copies into the backend's
`app/static/`. The frontend and API share an origin, so no CORS config and no
secrets in the client — only call same-origin `/api/...`.

Auth is handled entirely at the edge by Cloudflare Access; the app never sees
unauthenticated traffic, so there is no login UI to build here.
