# Cinema-Edit-Studio — no-install workflow

User sends a video batch directly in ChatGPT. The assistant runs the renderer in an authorized compute session; the user installs nothing. The repository stores **source code and tests only**, never customer clips.

## Chat-first command

    python cinema_integrated.py shot1.mp4 shot2.mov shot3.mp4 -o output/reel.mp4 --seconds 12 --width 720 --height 1280 --style sport

Optional soundtrack:

    python cinema_integrated.py shot1.mp4 shot2.mp4 --music licensed_music.wav -o output/reel.mp4 --seconds 15 --width 1080 --height 1920 --style cinematic

Supported styles: sport, cinematic, clean. By default the renderer synthesizes an original percussive instrumental. No titles, captions, logos or text overlays are added.

Included pipeline:
1. Select frames by brightness/detail score (heuristic, not semantic AI understanding).
2. Detect onsets in audio; create a cut plan.
3. Apply 3-part speed ramps with motion-compensated optical flow for slow portions.
4. Color correction, subtle motion and xfade transitions.
5. Mix original or supplied licensed instrumental and limit peaks.
6. Export H.264/AAC MP4 and verify full decode, stream dimensions and audio.

**Hardware-agnostic baseline:** FFmpeg plus Python standard library. The user does not install these; they are needed wherever the assistant actually runs the job.

### Limitations — not implemented
- RIFE / Real-ESRGAN neural GPU processing (optional adapters only; no compatible GPU or model weights verified).
- Blender 3D compositing (template only; no verified Blender runtime).
- Automatic selection of semantically interesting moments; scene scoring currently favors visual detail.
- Upscaling a 720p input to 1080p changes frame size but cannot guarantee new true detail.
- No permanent server or asynchronous bot. Each assistant execution is session-bound.
- Source audio is intentionally replaced by instrumental music unless future configuration adds original ambience.

## Test
    python -m unittest discover -s tests -v

## Evidence
2026-10-30: four integrated Python/FFmpeg tests passed locally. Rendered 5 current-chat real clips into 720×1280 H.264/AAC (8.27 seconds, 10 shots), and verified full decode and audio. Repository-side GitHub Actions not independently verified. Do not call product commercial-ready until target-environment, security and regression acceptance pass.

## Optional heavy processing
Only use external RIFE, Real-ESRGAN and Blender on a confirmed supported compute runtime; do not auto-download binaries, model weights or start paid GPU resources without appropriate authorization.
