#!/usr/bin/env python3
"""Full frame-folder pipeline for RIFE / Real-ESRGAN ncnn Vulkan executables.

Requires user-installed, compatible binaries and model data. Original stays intact.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path

def exec_cmd(args):
    subprocess.run([str(v) for v in args], check=True)

def probe(source):
    obj=json.loads(subprocess.check_output([
        "ffprobe","-v","error","-show_streams","-of","json",str(source)],text=True))
    video=next((s for s in obj.get("streams",[]) if s.get("codec_type")=="video"),None)
    if video is None:raise ValueError("Video stream not found")
    fps=Fraction(video.get("avg_frame_rate","0/1"))
    if fps<=0:raise ValueError("Source frame rate is invalid")
    return fps

def process(source, destination, model, slow_motion=False, upscale=2):
    bins={"rife":"rife-ncnn-vulkan","realesrgan":"realesrgan-ncnn-vulkan"}
    if model not in bins:raise ValueError("Unsupported AI model")
    binary=shutil.which(bins[model])
    if not binary:raise RuntimeError(bins[model]+" missing; install separately and verify Vulkan")
    for cmd in ("ffmpeg","ffprobe"):
        if not shutil.which(cmd):raise RuntimeError(cmd+" missing")
    src=Path(source).resolve();dst=Path(destination).resolve()
    if not src.is_file() or src==dst:raise ValueError("Source missing or destination unsafe")
    if dst.exists():raise FileExistsError(dst)
    if upscale not in (2,3,4):raise ValueError("Upscale must be 2, 3 or 4")
    fps=probe(src)
    dst.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cinema-ai-") as td:
        work=Path(td)
        raw=work/"frames";result=work/"processed"
        raw.mkdir();result.mkdir()
        exec_cmd(["ffmpeg","-v","error","-y","-i",src,
                  "-vsync","0",raw/"%08d.png"])
        if not any(raw.iterdir()):raise RuntimeError("No frames extracted")
        args=[binary,"-i",raw,"-o",result]
        if model=="realesrgan": args+=["-s",str(upscale),"-n","realesrgan-x4plus"]
        exec_cmd(args)
        if not any(result.iterdir()):raise RuntimeError("AI output frames missing")
        # RIFE defaults to N*2 frames. Preserve original runtime unless slow_motion requested.
        out_fps=fps*(2 if model=="rife" and not slow_motion else 1)
        video=work/"video.mp4"
        exec_cmd(["ffmpeg","-v","error","-y","-framerate",str(out_fps),
                  "-i",result/"%08d.png","-c:v","libx264","-crf","18",
                  "-preset","medium","-pix_fmt","yuv420p",video])
        if model=="rife" and slow_motion:
            shutil.copyfile(video,dst)
        else:
            # Use source audio if present, without inventing new audio.
            exec_cmd(["ffmpeg","-v","error","-y","-i",video,"-i",src,
                      "-map","0:v:0","-map","1:a:0?","-c:v","copy",
                      "-c:a","aac","-b:a","192k","-shortest",
                      "-movflags","+faststart",dst])
    return dst

if __name__=="__main__":
    p=argparse.ArgumentParser(description="Optional AI video frame processing")
    p.add_argument("model",choices=["rife","realesrgan"])
    p.add_argument("source");p.add_argument("destination")
    p.add_argument("--slow-motion",action="store_true")
    p.add_argument("--scale",type=int,choices=(2,3,4),default=2)
    a=p.parse_args()
    print(process(a.source,a.destination,a.model,a.slow_motion,a.scale))
