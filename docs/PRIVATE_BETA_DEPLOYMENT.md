# Private operational beta: host deployment and acceptance (2026-10-31)

## Current deployment status
Repository source and GitHub Actions packaging exist; a persistent render host, a private browser address and a successful Chrome 109 real-device test **have not been provisioned/verified**. Never interpret a green CI or ZIP as an accessible service.

## Recommended stack
1. Obtain an authorized, persistent Ubuntu 24.04 server or VM with sufficient disk for user footage. For cost-free evaluation, Oracle Cloud Always Free Ampere A1 may offer up to 4 OCPUs/24 GB RAM (subject to actual account and region capacity; identity verification typically requires a payment card). No provider or payment is enabled by this repository.
2. Install Python 3, ffmpeg/ffprobe and curl on the **server**, not on the Win7/Android client. Clone the authorized `main` branch. Put `CINEMA_WORKSPACE` on a persistent private disk and restrict its OS permissions to the dedicated render service account.
3. Set `CINEMA_PORT=8765` and `CINEMA_WORKSPACE=/srv/cinema-private` then run `sh packaging/launch-host.sh` as a non-root dedicated account. Do not change the application's loopback binding; confirm with `sh packaging/check-private-host.sh`. Never run on `0.0.0.0` without an authenticated ingress.
4. Configure a **named** Cloudflare Tunnel to `http://127.0.0.1:8765` on this host (outbound connection only). Before making its hostname usable, configure Cloudflare Access, an explicit allowlist of the owner's identity, deny-by-default, short session duration and MFA. Validate that unauthorized/incognito requests cannot access `/api/projects`, uploads, media or exports, and authorized HTTPS access does work. Do not use a quick tunnel as a private login solution. DNS/hostnames and account configuration require authorization.
5. Do not make this a multi-user service: the current workspace has no per-user isolation or in-app authentication. An Access gate is essential and suitable only for a single trusted user/workspace in this beta. Do not share credentials or the Access-protected URL publicly.
6. Enable systemd with a dedicated service account, auto-restart, least-privilege writable workspace, service logs, disk monitoring and scheduled encrypted backups. Test restore of the private workspace and its `queue.sqlite3`, `projects/*/project.json` and media. Do not commit workspace files, secrets, JWTs, or footage.
7. Limit cumulative disk use and monitor memory, ffmpeg processes, log files and queue growth. The application limits a single file to 1 GiB but it does **not** enforce a whole-workspace quota, malware scanning, or retention policy. Operational beta must remain trusted-user only. Suggested policy for **future approval**: retain until the owner deletes or archives the project; no automatic deletion is configured.

## Important upload limit
Cloudflare proxied-hostname Free/Pro plans typically cap a **single HTTP request** at 100 MB (the application's own maximum is 1 GiB). Current upload endpoint sends a whole file in one request: files above 100 MB will fail through this route. Do not describe large-file upload as supported over this specific free tunnel. Implement tested resumable chunked upload as a separate engineering task before accepting larger files; never bypass authentication or expose the origin.

## Browser acceptance, to run on the target devices
Use Chrome **109 on Windows 7 SP1** and a real Android browser; Chromium 143 Playwright CI is *not* equivalent.
1. Confirm HTTPS and Access login (and no access while logged out).
2. New project; upload three different small MP4 files and one music file (<100 MB each through Free Cloudflare), check previews.
3. Reorder, trim, speed and visual effect; save, reload and inspect the recovered timeline/music.
4. Start render; inspect queued/running/done state, progress and errors. Download MP4 and play it with audio.
5. Inspect duration, H.264/AAC codec and full decode on render host with `ffprobe` and `ffmpeg -v error -i exported.mp4 -f null -`.
6. Compare SHA256 of all original source files before and after render. Verify failed optional GPU models do not prevent base render.
7. Record screenshots and exact Chrome/Android versions. Confirm no horizontal overflow or JS errors. Repeat after a server restart and test restoring a workspace backup.
8. Test upload limits, out-of-disk failures and disconnected-client behavior with non-sensitive synthetic clips.

## Security and access stop conditions
No shared workspace or public hostname without an active Access deny-by-default policy; no confidential footage until backups and access checks pass; no promise of 1 GiB remote upload through Free Cloudflare; no commercial release until retention policy, malicious-file review, access isolation, load testing and browser acceptance pass.

## Current practical delivery
Source is on `main`. GitHub Actions workflow `.github/workflows/web-studio.yml` produces `cinema-studio-host-bundle` as an artifact after its tests. Download from the actual successful run; artifact availability and permanent-host deployment must be verified separately. The package contains source and needs a Linux render host with FFmpeg. This guide itself does not create a server, DNS name, account or paid resources.
