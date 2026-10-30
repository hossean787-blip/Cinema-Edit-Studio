# Cinema Edit Studio — Render Free single-user TEST deployment

This is an **ephemeral trial only**. Render Free provides 0.1 CPU, 512 MB RAM, and no persistent disk. Video uploads, project JSON and SQLite renders in /data are lost on instance restart, redeploy or spin-down. Render may sleep after inactivity. Complex rendering, large files, GPU AI and sustained videos are not supported at this tier. Do not use private customer footage, or trust it for archival production.

## Render create screen
- Source GitHub `hossean787-blip/Cinema-Edit-Studio`, branch `main`.
- **Language = Docker** (do not use Python 3; image installs FFmpeg with apt). Dockerfile is at repository root.
- Root Directory blank, Dockerfile path default.
- Compute = Free $0. Region may remain Oregon.
- **Do not fill Build Command or Start Command**; Dockerfile builds and runs everything.
- Environment Variables:
  - `CINEMA_AUTH_USER` = your chosen login name (not an email address, preferably)
  - `CINEMA_AUTH_PASSWORD` = cryptographically random unique password of 20+ characters, entered **in Render only**, never in GitHub, chat or screenshots.
  - `CINEMA_WORKSPACE` = `/data` (optional, Docker default).
- Click Deploy Web Service only when these credentials are set; without credentials the server refuses public binding. Render's HTTPS endpoint terminates TLS and forwards traffic to the container. Do not publish the resulting URL or password.

## Authentication notes
HTTP Basic authentication guards **all** GET and POST routes, media and MP4 downloads. Browsers show their native sign-in dialog. This protects casual remote access but is **not** enterprise auth: no MFA, per-user access control, password-reset flow or rate limiting. Single trusted user only, always via Render's https:// address. Avoid public sharing of URLs and credentials.

## Verification after deployment
- Render logs should contain `Cinema Edit Studio: http://0.0.0.0:${PORT}`.
- Open the Render **https** address. Enter username/password in the browser's login prompt.
- Verify wrong credentials receive HTTP 401 and valid credentials can open UI.
- Use only 2–3 short synthetic MP4 files + short music to test upload, timeline save, render progress, download and playback.
- Do not upload important videos: renders and project data will be ephemeral on Free.
- Chrome 109 and Android actual device checks remain required; successful newer Chromium CI is not evidence for them.
- End-to-end success is not established until a Render-hosted render finishes. OOM can occur on the 512 MB tier.

## Security limits
No account management, MFA, antivirus or permanent storage; never call this a private production service. Basic Auth uses a user-chosen secret stored in Render environment. Password persists across deploys but files do not. To support large footage and persistent storage, move to a suitable host with private authenticated access and encrypted backups.
