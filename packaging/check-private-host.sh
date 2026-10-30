#!/usr/bin/env sh
# Cinema Edit Studio: non-destructive host prerequisites and private listener smoke test.
set -eu
PORT="${CINEMA_PORT:-8765}"
for bin in python3 ffmpeg ffprobe curl; do
  if ! command -v "$bin" >/dev/null 2>&1; then echo "MISSING: $bin" >&2; exit 1; fi
done
python3 -c 'import sqlite3, http.server; print("Python/SQLite: OK")'
ffmpeg -hide_banner -encoders 2>/dev/null | grep -q 'libx264' || { echo 'MISSING: FFmpeg libx264 encoder' >&2; exit 1; }
ffmpeg -hide_banner -encoders 2>/dev/null | grep -q 'aac' || { echo 'MISSING: FFmpeg AAC encoder' >&2; exit 1; }
echo "FFmpeg H.264/AAC: OK"
if curl -fsS --max-time 5 "http://127.0.0.1:${PORT}/api/projects" >/dev/null; then
  echo "Private loopback HTTP project API: OK"
else
  echo "NOT RUNNING: start sh packaging/launch-host.sh on this same host" >&2
  exit 2
fi
echo "WARNING: This verifies only local prerequisites and HTTP health, not login/TLS or remote reachability."
