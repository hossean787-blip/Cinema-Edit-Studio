# Cinema Edit Studio — Interactive Professional Editor

**New runnable host interface:** `python3 studio_web.py --workspace ./studio_workspace`, then open `http://127.0.0.1:8765` on the authorized rendering host. A host-side installer is not required for the user: rendering can be delegated by uploading videos to ChatGPT, while persistent web UI access requires an approved private host connection.

The implemented Persian RTL dark workspace includes true media uploads, source preview, editable video/audio timeline, optional picture-in-picture visual track, per-clip speed and 3-part ramps, dynamic color/transition controls, 720p/1080p/4K export presets, automatic cut mode, persistent SQLite queue and project save/recovery, AI/Blender settings with capability checks, actual H.264/AAC render and downloadable final preview. **Defaults to no text on footage.**

**Evidence and boundaries:** [host runbook](docs/WEB_STUDIO.md) · [previous professional engine](docs/PRO_RUNBOOK.md) · [benchmarks](performance/benchmark-2026-10-30.json) · [recovery and blockers](STATUS.md) · [GitHub CI](.github/workflows/web-studio.yml).

This is a tested render-host backend, not a publicly deployed commercial SaaS. Public access requires authentication, HTTPS, security/privacy review and authorized hosting. The full model stack is not installed or required on the user's device.

---

# Cinema Edit Studio — 12-engine professional chat workflow

**Primary executable:** studio_pro.py — receive clips in ChatGPT, render with assistant-hosted tools, return H.264/AAC MP4 without installing an application on the user's device.

**Quick command (execution-host only):**

    python studio_pro.py shot1.mp4 shot2.mp4 -o export/reel.mp4 --seconds 12 --width 1080 --height 1920 --style sport --scene-detect --stabilize

**Installed/tested dependencies:** FFmpeg, RIFE, Real-ESRGAN, Blender, MLT, PySceneDetect, Auto-Editor, whisper.cpp, Vid.Stab, OpenColorIO, OpenTimelineIO and frei0r. Optional AI and 3D features are enabled only when the corresponding executable/model exists; default workflow remains usable without GPU.

**Key files:** [usage & limitations](docs/PRO_RUNBOOK.md), [upstream versions and licensing](docs/TOOLS_AND_LICENSES.md), [live progress and recovery](STATUS.md), [GitHub CI](.github/workflows/pro-backends.yml).

**Release gate:** An operational tested backend is not by itself a commercial-ready released product. Long-footage performance, model output quality, target device compatibility and third-party redistribution rights must still be accepted.

---

# Cinema Edit Studio — Chat-first edition

**Main entry point:** `cinema_integrated.py`. The user only uploads videos to the conversation; the assistant can process them in its available execution environment and return MP4. No software needs installing on the user's device.

**One-command example:**
```bash
python cinema_integrated.py input1.mp4 input2.mov -o output/reel.mp4 --seconds 12 --width 720 --height 1280 --style sport
```

Current integrated workflow: shot scoring, music onset detection, beat edits, speed ramps, FFmpeg optical-flow slow motion, cinematic color, dynamic-camera effect, xfade transitions, original instrumental synthesis or supplied licensed soundtrack, H.264/AAC export and full-decode QA. No on-screen text is added.

**Verified locally 2026-10-30:** four tests passed; a 5-clip 720×1280 reel rendered and decoded successfully. See [chat workflow and limitations](docs/CHAT_ONLY.md) and [integrated tests](tests/test_cinema_integrated.py).

**Not verified or activated:** actual neural RIFE / Real-ESRGAN GPU models, Blender rendering, Windows 7 installation, and GitHub Actions success. This is a usable chat-render backend, not a commercial release.

---

# Cinema Edit Studio

Independent cinematic reel editing project.

## Implemented scaffold
- Cut and arrange videos using start time and duration.
- Adjust speed per shot (e.g. 0.5 = slow motion).
- Export 1080x1920 portrait H.264 MP4 by default.
- Add an optionally supplied music track (ensure usage rights).
- Default output contains no text overlays.
- Original clips are not modified.

## Requirements
Python 3.8+; FFmpeg and FFprobe in PATH, with libx264 and AAC support.

## Run
Copy `examples/reel.json` to a folder containing your footage. Adjust the paths and timings, then:

```bash
python studio.py project/reel.json -o output/reel.mp4
```

Speed 1 = normal, 0.5 = half speed, 2 = double speed. This is frame retiming, not AI interpolation.

## Later integrations (not installed or tested)
- RIFE — interpolated slow motion
- Real-ESRGAN — AI video enhancement
- PySceneDetect — automated cut detection
- Blender — 3D composition

External tools will be connected by versioned dependencies after license and compatibility checks; their source code is not copied into this repository.

## Status
Initial functional scaffold. CI/integration tests and production readiness are not yet verified. No cloud render or paid API is configured.


## Enhanced slow motion (implemented and locally smoke-tested)
Run `python enhance.py input.mp4 output.mp4 --speed 0.5 --interpolate --width 1080 --height 1920 --fps 30`.
The optional `--interpolate` invokes FFmpeg's motion-compensated minterpolate filter, NOT RIFE; clips with cuts or fast occlusions can show artifacts. This tool removes source audio; add appropriately licensed music in a separate editing step. Resizing to Full HD is not the same as recovering lost source detail.

## Verification
Run `python -m unittest discover -s tests -v`. Basic assembler tests (5) and a separate optical-flow smoke render were run successfully in a temporary execution environment on 2026-10-30. GitHub Actions results remain unconfirmed; external AI integrations, GPU pipelines, and product readiness remain pending.


## Desktop application (initial working source)
Run `python desktop_gui.py` on a computer with Python, Tkinter and FFmpeg. Choose videos, adjust shot timing and speed, order clips, optionally add music, then export MP4. This is a local lightweight desktop renderer, not a live-preview nonlinear editor. It creates no on-screen captions. Local desktop GUI has not been usability-tested on the user's Windows 7 laptop.

## Automatic rhythm starter
Run `python beat_project.py music.mp3 clip1.mp4 clip2.mp4 -o beat_edit.json`, then `python studio.py beat_edit.json -o output/beat_reel.mp4`. Beat markers are approximate and source shot length requirements apply.

## Quality control
`python quality_check.py output/reel.mp4 --width 1080 --height 1920 --audio` checks size, streams, and decodes the full export (no guarantee of creative quality).

## Demo
GitHub Actions `Render synthetic demo` can generate a downloadable artifact when manually dispatched. A successful run has not been verified.

## GPU work blocked by environment
RIFE / Real-ESRGAN and Blender are optional external tools, NOT activated by committing adapters. Their models, hardware, release-specific CLI behavior, license and actual service costs require validation. Nothing will auto-purchase or provision a paid GPU.


## Cinematic effects
Five optional FFmpeg color and light presets: `moody`, `punch`, `film`, `cold`, `warm`.
Example: `python effects.py input.mp4 output.mp4 --preset punch`.
No added titles. This processor is a color / grain / vignette effect system, not Blender 3D simulation. Renders have not yet been validated in GitHub CI.

## Implementation status
- Source code stored on main for six requested workstreams.
- CI confirmation is unavailable from the currently exposed GitHub status result (empty status list).
- Cloud GPU provisioning, model download, release packaging, Windows 7 install and end-to-end commercial QA remain incomplete.
