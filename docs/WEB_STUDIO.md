# Cinema Edit Studio — Persian web editing workspace

## Goal and scope

This is an actual **local browser editor backed by a Python HTTP render server**. It is not a permanently hosted SaaS, native mobile app or a public cloud deployment. Users can send their clips to the assistant in ChatGPT without installing anything; when the assistant runs a render on a supported compute host, FFmpeg and optional AI models run **on that host**. The web editor itself requires that host's server to be reachable through an approved private channel. **Do not expose port 8765 to the public Internet** without an authenticated reverse proxy and a security review.

## Host launch (Linux, Python 3.8+ basic workflow)

Dependencies on execution host: Python 3.8+, FFmpeg and FFprobe with H.264/AAC support. Optional PySceneDetect/OpenTimelineIO/OpenColorIO and other 12 engines: see `requirements-professional.txt` and `docs/PRO_RUNBOOK.md`.

    sh packaging/launch-host.sh

Or:

    python3 studio_web.py --port 8765 --workspace /safe/private/workspace

Open **http://127.0.0.1:8765** on the render host. Listens only on loopback. User device install requirement: **none**, but the web UI is not reachable remotely unless the authorized environment provides private browser access. No publishing action is included.

## Functional capabilities

- RTL Persian responsive dark editor.
- Multiple uploaded videos/audio tracks in a project library; timeline selectable trim/start/duration, speed, true 3-stage speed ramps and clip reordering/removal.
- Source video preview (the preview does NOT show post-render effect output), and final MP4 preview after render.
- Horizontal/vertical preset selection (720×1280, 1080×1920, 1920×1080 and 3840×2160); 24/25/30/60 FPS.
- Separate audio track: uploaded music or original locally synthesized instrumental. No captions by default.
- Opt-in automatic beat/scene cut mode through existing `studio_pro.py`, or the manual editable timeline `timeline_render.py`.
- FFmpeg optical-flow slow motion, xfade transitions, color styles; optional Vid.Stab stabilization.
- Optional RIFE / Real-ESRGAN toggles enabled only if configured binaries exist; model/hardware operation is checked during render. Failures of optional models preserve a base output and report warnings.
- Persistent JSON project manifests and SQLite render queue; queued/running jobs are safely requeued after restart and existing verified files can be recovered.
- Single-worker scheduling to avoid simultaneous memory-heavy transcodes, up to 12 pending jobs.
- Original media files are never overwritten; outputs have `.mp4`, `.otio`, `.mlt` and `.timeline.json` sidecars. The OTIO/MLT files preserve clip sources/trim ranges and separate music but **manual speed ramps are authoritative in timeline JSON** rather than fully portable native NLE effects.
- Failed job messages and explicit retry (maximum two attempts). No opaque endless retries.

## Security and limitations

- Run only on trusted loopback. Uploaded media is kept inside a project-specific directory, filenames are replaced by random IDs, user-supplied paths cannot escape the workspace via API.
- Binary uploads capped at 1 GiB each; project clips capped at 80, timeline duration capped at 5 minutes. Intended to bound resource consumption, not guarantee fixed peak RAM.
- No public-facing authentication, user accounts, HTTPS termination, upload virus scanning, distributed queue, multi-tenant access controls, or cloud persistence. These are **release blockers for public/commercial hosting**.
- On Windows 7, the modern Blender/GPU Python stack is not generally supported; no real Win7 compatibility test has been run. Recommended architecture: browser UI on the user device *if a private server is available*, render on a supported Linux host. User doesn't need to install render dependencies.
- Headless HTTP/FFmpeg tests cover functionality; visual screenshot, accessibility and cross-browser manual UX audit remain pending.
- 4K preset is present; large-production 4K throughput and model fidelity need real production performance tests.
- Source footage, soundtrack and model license compliance must be reviewed before commercial release.

## Verification

    python3 -m unittest discover -s tests -p 'test_web_workspace.py' -v
    python3 -m unittest discover -s tests -v

CI: `.github/workflows/web-studio.yml` builds an auditable ZIP artifact. No source video or proprietary models are included in the ZIP.
