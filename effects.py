"""Apply optional cinematic effects to a shot with FFmpeg, without any captions."""
import argparse
import shutil
import subprocess
from pathlib import Path

PRESETS={
 "moody": "eq=contrast=1.18:brightness=-0.02:saturation=0.82,vignette=PI/5",
 "punch": "eq=contrast=1.16:saturation=1.23,unsharp=5:5:0.65",
 "film": "eq=contrast=1.12:saturation=0.9,noise=alls=8:allf=t+u,vignette=PI/6",
 "cold": "colorbalance=rs=-0.08:gs=0.0:bs=0.12,eq=contrast=1.12",
 "warm": "colorbalance=rs=0.12:gs=0.04:bs=-0.08,eq=contrast=1.09",
}
def apply(source, destination, preset="punch", width=1080, height=1920):
    src=Path(source).resolve(); dst=Path(destination).resolve()
    if preset not in PRESETS: raise ValueError("Unsupported preset")
    if not src.is_file() or src==dst: raise ValueError("Invalid source/destination")
    if width<2 or height<2 or width%2 or height%2: raise ValueError("Invalid dimensions")
    if dst.exists(): raise FileExistsError(dst)
    if not shutil.which("ffmpeg"): raise RuntimeError("FFmpeg missing")
    dst.parent.mkdir(parents=True,exist_ok=True)
    vf=f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height},{PRESETS[preset]},format=yuv420p"
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(src),
                    "-map","0:v:0","-map","0:a?","-vf",vf,"-c:v","libx264",
                    "-crf","19","-preset","medium","-c:a","aac","-b:a","192k",
                    "-movflags","+faststart",str(dst)],check=True)
    return dst
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("source");p.add_argument("destination")
    p.add_argument("--preset",choices=sorted(PRESETS),default="punch")
    p.add_argument("--width",type=int,default=1080);p.add_argument("--height",type=int,default=1920)
    a=p.parse_args()
    print(apply(a.source,a.destination,a.preset,a.width,a.height))
