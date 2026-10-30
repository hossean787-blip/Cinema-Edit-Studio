#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
command -v python3 >/dev/null || { echo 'Python 3 is required on render host' >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo 'FFmpeg missing on render host' >&2; exit 1; }
command -v ffprobe >/dev/null || { echo 'FFprobe missing on render host' >&2; exit 1; }
: "${CINEMA_PORT:=8765}"
: "${CINEMA_WORKSPACE:=$HOME/.cinema-edit-studio}"
cd "$SCRIPT_DIR"
exec python3 studio_web.py --port "$CINEMA_PORT" --workspace "$CINEMA_WORKSPACE"
