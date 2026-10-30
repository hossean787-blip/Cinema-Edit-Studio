"""Validate an exported MP4 with FFprobe and a full decode pass."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

def inspect(file, min_width=0, min_height=0, require_audio=False):
    f=Path(file)
    if not f.is_file() or f.stat().st_size<1000:
        raise ValueError("Missing or empty output video")
    if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg and FFprobe are required")
    data=json.loads(subprocess.check_output([
        "ffprobe","-v","error","-show_format","-show_streams","-of","json",str(f)
    ],text=True))
    videos=[s for s in data["streams"] if s["codec_type"]=="video"]
    audios=[s for s in data["streams"] if s["codec_type"]=="audio"]
    if len(videos)!=1: raise ValueError("Expected one video stream")
    v=videos[0]
    if v["width"]<min_width or v["height"]<min_height:
        raise ValueError("Output resolution too small")
    if require_audio and not audios: raise ValueError("Audio stream missing")
    if float(data["format"].get("duration",0))<=0:
        raise ValueError("Invalid duration")
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(f),
                    "-f","null","-"],check=True)
    return {"width":v["width"],"height":v["height"],
            "duration":float(data["format"]["duration"]),
            "has_audio":bool(audios),"bytes":f.stat().st_size}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("--width",type=int,default=0)
    p.add_argument("--height",type=int,default=0)
    p.add_argument("--audio",action="store_true")
    a=p.parse_args()
    print(json.dumps(inspect(a.file,a.width,a.height,a.audio),indent=2))
