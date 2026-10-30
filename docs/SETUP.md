# Setup and limitations

## Free local processing
Python 3.8+ and a compatible FFmpeg build are required. On Windows 7 some recent FFmpeg installers may not run; use a legally obtained compatible build. Run: `python -m unittest discover -s tests -v` and `python studio.py examples/reel.json -o output/reel.mp4` after placing input clips.

## Interface
Open `project_builder.html` locally. It produces a JSON manifest; it does not upload media, render video, or execute shell commands.

## Rhythm
`python beat_sync.py owned-audio.wav -o beats.json` identifies approximate percussive transients. This is NOT yet integrated as automatic timeline cuts and will misdetect some musical genres.

## Optical flow
`python enhance.py input.mp4 output.mp4 --speed 0.5 --interpolate` uses FFmpeg's minterpolate, not neural RIFE. It may produce artifacts.

## Optional GPU tools
RIFE and Real-ESRGAN adapters in `ai_tools.py` require separately installed, compatible executables. Their ncnn-vulkan CLI typically operates on images or numbered frame directories, not arbitrary MP4 videos; extract frames, run model, then encode output with FFmpeg. Do not supply MP4 inputs directly to these adapters. Model formats, flags and licenses must be validated for the exact release before enabling. No binaries or model weights are bundled. Blender has not been integrated.

## CI and costs
GitHub Actions test-render.yml runs tests and render-demo.yml manually builds an artifact. Availability, quotas, and billing restrictions depend on your account and must be verified from actual runs. No cloud GPU or paid account is provisioned.

## Production gate
Before calling this product complete: verify tests, actual CI runs, multi-format input, licensed music, export fidelity, GPU performance, security review, and manual usability on target devices.
