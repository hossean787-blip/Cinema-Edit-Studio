# Cinema Edit Studio — Assistant-run 12-engine workflow

This product is a chat-first processing backend, not a persistent hosted website or an app to install on the customer's phone. The assistant receives authorized clips, performs work in its available execution environment and returns MP4. The main branch contains source code, setup and CI.

## Main entry point

    python studio_pro.py clip1.mp4 clip2.mov -o output/final.mp4 --seconds 15 --width 1080 --height 1920 --style sport

Default behavior: auto rhythm detection, speed ramps, FFmpeg optical-flow interpolation, music generated locally, cinematic color, transitions, H.264/AAC export and full decode validation. No on-video text/subtitles.

Optional stages:

    --scene-detect           PySceneDetect scene boundaries and split preparation
    --stabilize              FFmpeg Vid.Stab two-pass input stabilization
    --auto-editor-bin PATH   Official binary auto-detects and cuts silence/motion
    --frei0r contrast0r      Apply separate frei0r filter
    --ocio-config FILE       Load color-management configuration
    --ocio-input SPACE --ocio-output SPACE
    --rife-bin PATH          Real RIFE ncnn Vulkan frame interpolation
    --realesrgan-bin PATH    Real-ESRGAN ncnn Vulkan 2x enhancement
    --blender-bin PATH       Render actual Cycles CPU 3D additional segment
    --whisper-bin PATH --whisper-model PATH    Optional sidecar .srt, never burned onto video

Default export includes:
- final.mp4: rendered video, published atomically after checks
- final.mp4.json: stage evidence, output dimensions/codec, A/V sync
- final.otio: editable source timeline; independent video/audio tracks if music is supplied
- final.mlt: MLT timeline; independent video/audio tracks if music is supplied
- final.srt only when whisper.cpp is requested and a model provided

## Installation is for the execution host ONLY

For Python modules: python -m pip install -r requirements-professional.txt.
For native tools: use compatible FFmpeg/MLT/frei0r/Vid.Stab, Blender, official Auto-Editor and whisper.cpp; install and version-pin on the execution host, not the user's device. RIFE and Real-ESRGAN require genuine Vulkan runtime and model directories.
There is no guaranteed permanent cloud GPU, global Python installation or continuous background service. Consult .github/workflows/*.yml for tested provisioning recipes.

## Tests
- python -m unittest discover -s tests -v
- python doctor_pro.py (read-only tool capability scan)
- GitHub Actions Pro toolchain integration smoke: independent jobs for MLT/frei0r/Python, Auto-Editor, Whisper.cpp.
- GitHub Actions Real AI and Blender CPU smoke tests true RIFE/Real-ESRGAN and Blender outputs.
- MP4 output must pass full FFmpeg decode, H.264/AAC streams, expected dimensions, no subtitle streams, input SHA256 preservation and audio/video timestamp checks.

## Safety and distribution
- User files are not committed to the repository or third-party model vendors by default.
- Upload and background processing require connected infrastructure and do not persist automatically after this conversation.
- A model binary being present is not proof of high-quality real-video output. Neural processing was actually tested with small synthetic videos; large-input throughput and visual fidelity remain environment-specific.
- See docs/TOOLS_AND_LICENSES.md for upstream links and compliance risks. Do not call this a commercial production release without legal and real-world compatibility/performance sign-off.
