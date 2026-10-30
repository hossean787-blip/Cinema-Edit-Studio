# Cinema Edit Studio — real-world integration and release acceptance

The project is an **operational local-hosted browser-based beta** and a candidate for supervised use, **not a public multi-user commercial release**. It requires a private compatible Linux rendering host and a browser connection to that host. No installation of heavy editing engines on the user's own Windows 7 computer is needed for chat-provided clip processing.

## Verified source and five CI workflows

- Baseline revision checked on 2026-10-30: `c9e9a928adfaf06127e15a20cfaa78d6279af9ac` on the **only** authorized branch `main`.
- All five workflows for that baseline were `success`: **Verify cinematic studio**, **Real AI and Blender CPU smoke**, **Pro toolchain integration smoke**, **Integrated cinema quality gate**, **Cinema Studio web editor and distributable**.
- Since that revision, defects were fixed in `main`: multi-shot save unintentionally retaining only the last clip; MP4 publish failing with EXDEV across filesystems; recovery of un-upscaled outputs when optional AI models were unavailable; optional warning visibility and favicon request handling.
- A Playwright/Chromium browser test is now part of `.github/workflows/web-studio.yml` (plus headless HTTP/unit tests). Do not substitute previous successes for the latest head. Recheck <https://github.com/hossean787-blip/Cinema-Edit-Studio/actions> and the exact latest head before publication.

## Real browser test and rendering

- Browser actually launched: **Chrome for Testing 143.0.7499.4**, Linux headless, desktop 1440×900 and mobile 390×844.
- UI actually exercised: new project, two media uploads, preview, trim/speed change, actual 3-stage speed ramp, clip reordering, save, reload and persisted state, rendering queue, final output link and MP4 download.
- Browser automation succeeded with no JavaScript errors and no mobile horizontal overflow. Automatic QA source: `tests/browser_qa_playwright.js`; screenshots: `cinema-browser-visual-qa` GitHub Actions Artifact when that job finishes successfully. Screenshots use only synthetic media.
- Independently rendered and decoded 3 clips through a **clean ZIP extraction** of the host program, using the documented shell launcher, with no optional AI models: duration **7.99s**, output **342,633 bytes**, source SHA256 preserved.
- Previous review used **five authorized real user videos** with the older `cinema_integrated.py` engine to render a 7.8s Full HD MP4 (81.49 seconds wall time as logged). **Do not conflate this with an end-to-end five-real-video run through the new browser UI.** Files were not committed.

## Performance measurement

Inspect `performance/benchmark-2026-10-30-professional.json`. Actual latest modular timeline engine on five **synthetic moving clips** at 1080×1920 H.264/AAC (24fps):

- Output duration **5.39s** and file size **1,719,960 bytes**.
- Wall-clock **7.70s**; summed CPU time (parent and children) **9.83s**.
- Maximum child process resident memory **775,528 KiB** (~757 MiB).
- GPU not used; all five input SHA256 hashes unchanged; complete decode passed.
- This is one short cloud-hosted CPU measurement, not a throughput/memory guarantee for Full HD user videos, 4K timelines, extended Blender scenes or neural video models.

## Security and retention

- Local server binds **127.0.0.1 only**, randomizes uploaded filenames and stores work per project in workspace-local directories. Uploaded media stays outside Git.
- Tested path traversal rejection, origin rejection for mutation requests, per-file size restrictions, range-based video streaming, no-overwrite of original files, atomic same-volume MP4 publication, SQLite job recovery and controlled retry.
- Optional RIFE/Real-ESRGAN/Blender failures do not discard a valid base render; warnings are surfaced. Features with missing models remain unavailable, not silently simulated.
- Workspace data retention, backup scheduling, legal distribution and cloud availability remain a deployment responsibility; there is no configured public auth/HTTPS, billing, public publishing or shared multi-user hosting.

## Remaining blockers before commercial availability

**متوقف به‌دلیل مانع** — No authorized persistent private rendering host, TLS and authentication deployment; no Windows 7/Chrome 109 acceptance test; no multi-user security audit or private-media retention policy. Heavy 4K, long real-video RIFE+Real-ESRGAN and actual GPU performance remain unverified. Redistribution rights for combined GPL/LGPL/native/model assets require expert licensing review.

**در حال اجرا** — Cross-browser/a11y review, sustained render benchmark and operational release acceptance on chosen host.

**تکمیل و آزموده‌شده** — Short-video end-to-end browser-to-server rendering, saved-project editing, optional engine fallbacks, independent two-layer video/audio timeline plus PIP, smoke CI engine tests, Full HD synthetic and previously authorized-real-media sample, ZIP CRC verification and clean-host startup/render test.

## Reproducible commands

```bash
python3 -m unittest discover -s tests -v
sh packaging/launch-host.sh
# On a supported host with browser QA dependencies:
CINEMA_URL=http://127.0.0.1:8765 CINEMA_TEST_VIDEO=/path/to/safe-test-clip.mp4 node tests/browser_qa_playwright.js
```

For Windows 7 and Chrome 109, the preferred architecture is **a remotely accessible private Linux rendering host**, with the user's device acting only as a browser client. No public network connection is enabled by default.
