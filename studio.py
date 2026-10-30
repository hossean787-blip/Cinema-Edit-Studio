#!/usr/bin/env python3
"""Standalone cinematic reel assembler using an installed FFmpeg/FFprobe.
No downloaded code, external API keys, or third-party Python dependencies.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

def run(args):
    subprocess.run(args, check=True)

def assemble(project, output):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and FFprobe must be installed and on PATH")
    cfg = json.loads(Path(project).read_text(encoding="utf-8"))
    shots = cfg.get("shots", [])
    if not shots:
        raise ValueError("At least one shot is required")
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    width, height = (int(x) for x in cfg.get("resolution", [1080, 1920]))
    fps = int(cfg.get("fps", 30))
    if min(width, height, fps) <= 0 or width % 2 or height % 2:
        raise ValueError("Invalid resolution or FPS")
    base = Path(project).resolve().parent
    with tempfile.TemporaryDirectory(prefix="cinema-edit-") as tmp:
        entries = []
        for i, shot in enumerate(shots):
            source = (base / shot["file"]).resolve()
            if not source.is_file():
                raise FileNotFoundError(source)
            start = float(shot.get("start", 0))
            length = float(shot["duration"])
            speed = float(shot.get("speed", 1))
            if start < 0 or length <= 0 or speed <= 0 or speed > 8:
                raise ValueError(f"Invalid shot timing or speed: {i}")
            segment = Path(tmp) / f"shot_{i:03d}.mp4"
            vf = (f"setpts=(PTS-STARTPTS)/{speed},fps={fps},"
                  f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                  f"crop={width}:{height},setsar=1,format=yuv420p")
            run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                 "-ss",str(start),"-t",str(length),"-i",str(source),
                 "-an","-vf",vf,"-c:v","libx264","-preset","medium",
                 "-crf","19","-r",str(fps),str(segment)])
            entries.append(segment)
        manifest = Path(tmp) / "list.txt"
        manifest.write_text("".join(f"file '{p.as_posix()}'\n" for p in entries), encoding="utf-8")
        video = Path(tmp) / "picture.mp4"
        run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat",
             "-safe","0","-i",str(manifest),"-c","copy",str(video)])
        if cfg.get("music"):
            music = (base / cfg["music"]).resolve()
            if not music.is_file():
                raise FileNotFoundError(music)
            run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                 "-i",str(video),"-stream_loop","-1","-i",str(music),
                 "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac",
                 "-b:a","192k","-shortest","-movflags","+faststart",str(output)])
        else:
            run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                 "-i",str(video),"-c","copy","-movflags","+faststart",str(output)])
    return output

def main():
    p = argparse.ArgumentParser(description="Build an Instagram-ready video reel")
    p.add_argument("project", help="JSON project manifest")
    p.add_argument("-o","--output",default="output/reel.mp4")
    args = p.parse_args()
    print(assemble(args.project,args.output))

if __name__ == "__main__":
    main()
