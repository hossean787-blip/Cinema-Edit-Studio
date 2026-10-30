#!/usr/bin/env python3
"""Opt-in video enhancement: no overlays, no synthetic detail claims."""
import argparse
import shutil
import subprocess
from pathlib import Path

def enhance(source, destination, slow=1.0, width=1080, height=1920, fps=30,
            interpolate=False, saturation=1.08, contrast=1.07, sharpen=0.45):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and FFprobe are required")
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source == destination:
        raise ValueError("Input and output must differ")
    if slow <= 0 or slow > 8 or not (0 < saturation <= 3) or not (0 < contrast <= 3) or not (0 <= sharpen <= 2):
        raise ValueError("Invalid enhancement values")
    if width < 2 or height < 2 or width % 2 or height % 2 or fps < 1 or fps > 120:
        raise ValueError("Invalid dimensions or FPS")
    vf = ["setpts=(PTS-STARTPTS)/%s" % slow]
    if interpolate:
        vf.append("minterpolate=fps=%d:mi_mode=mci:mc_mode=aobmc:me_mode=bidir" % fps)
    else:
        vf.append("fps=%d" % fps)
    vf += ["scale=%d:%d:force_original_aspect_ratio=increase:flags=lanczos" % (width,height),
           "crop=%d:%d" % (width,height),
           "eq=contrast=%g:saturation=%g" % (contrast,saturation),
           "unsharp=3:3:%g" % sharpen, "format=yuv420p"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(source),
                    "-an","-vf",",".join(vf),"-c:v","libx264","-crf","18",
                    "-preset","medium","-movflags","+faststart",str(destination)],check=True)
    return destination

def main():
    p = argparse.ArgumentParser(description="Enhance a video with no text overlays")
    p.add_argument("source")
    p.add_argument("destination")
    p.add_argument("--speed",type=float,default=1.0)
    p.add_argument("--width",type=int,default=1080)
    p.add_argument("--height",type=int,default=1920)
    p.add_argument("--fps",type=int,default=30)
    p.add_argument("--interpolate",action="store_true")
    a=p.parse_args()
    print(enhance(a.source,a.destination,slow=a.speed,width=a.width,height=a.height,fps=a.fps,interpolate=a.interpolate))

if __name__ == "__main__":
    main()
