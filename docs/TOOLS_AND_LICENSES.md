# External tool matrix — 2026-10-30

Code in this repository is independent. User uploads remain private to the current rendering session. Native binaries and model weights are not vendored.

| Tool | Source / version tested or targeted | License on official repository | Integration and evidence |
|---|---|---|---|
| FFmpeg/FFprobe | Debian 5.1.9, CI distro package | Mixed LGPL/GPL depending on flags/dependencies | H.264/AAC rendering, probing, full decode locally passed |
| RIFE ncnn Vulkan | 20221029 official Ubuntu binary | MIT | Genuine Vulkan llvmpipe image inference and GitHub CI success; optional full-video adapter |
| Real-ESRGAN ncnn Vulkan | 20220424 official Ubuntu binary | BSD-3-Clause | Genuine 2x image inference and GitHub CI success; optional full-video adapter |
| Blender | 4.5.15, verified official SHA256 | GPL family/mixed (do not treat as permissive) | Cycles CPU video render and GitHub CI success; optional intro |
| MLT Framework | latest official 7.42.0 / runner distro package | LGPL-2.1, check linked modules | Real editable .mlt XML export; melt integration CI |
| PySceneDetect | 0.7.2 | BSD-3-Clause | Installed; detects shots with fallback single-scene |
| Auto-Editor | 31.8.0 binary | Unlicense | CI-only binary (local Debian 12 glibc too old); optional CLI action |
| whisper.cpp | v1.9.5 | MIT | Optional SRT sidecar via real ggml model; no default on-screen text |
| Vid.Stab | ffmpeg libvidstab filters, distro build | GPL/mixed; inspect package's licensing | Two-pass stabilization rendered and decoded |
| OpenColorIO | 2.6.0 python | BSD-3-Clause | Bakes .cube LUT via PyOpenColorIO then applies via FFmpeg |
| OpenTimelineIO | 0.18.1 | Apache-2.0 | Saves and round-trip reads editable .otio |
| frei0r | distro plugin targeting | GPL-2.0 | Separate opt-in filter, requires actual plugin binary |

Official project references:
https://ffmpeg.org/legal.html
https://github.com/nihui/rife-ncnn-vulkan
https://github.com/xinntao/Real-ESRGAN
https://www.blender.org/about/license/
https://mltframework.org/
https://github.com/Breakthrough/PySceneDetect
https://github.com/WyattBlue/auto-editor
https://github.com/ggml-org/whisper.cpp
https://github.com/georgmartius/vid.stab
https://github.com/AcademySoftwareFoundation/OpenColorIO
https://github.com/AcademySoftwareFoundation/OpenTimelineIO
https://github.com/dyne/frei0r

Commercial gate: code access is not the same as permission to redistribute third-party packages. Keep copyright/license notices, attribute models and fonts, review FFmpeg compiled configuration, binary codecs, other vendors' footage/music, model weights, GPL/LGPL linking and deployment strategy. No commercial release approval until legal and operational verification.
