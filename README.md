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
