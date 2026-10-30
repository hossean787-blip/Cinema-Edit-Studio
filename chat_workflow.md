# Chat-first editing workflow

Users upload clips directly in their ChatGPT conversation. The assistant performs editing inside an available execution environment; the user does not install software. The engine is stored in `chat_editor.py` and expects FFmpeg/FFprobe in the assistant runtime. No server or persistent remote render service is provisioned. Each session must verify tool and file availability.

Usage (assistant environment): `python chat_editor.py clip1.mp4 clip2.mp4 --output reel.mp4 --seconds 15 --profile punch --music licensed_music.wav`.

Validated with a synthetic video rendered to 720x1280 MP4 and fully decoded. This does not prove creative quality or GPU-based AI interpolated slow-motion. Future integration: actual beat-map cutting, curated shot scoring, GPU models when available.
