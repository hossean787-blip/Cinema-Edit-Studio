#!/usr/bin/env python3
"""Offline pulse-cut reel generator; user uploads clips, assistant renders."""
import argparse
import subprocess
import tempfile
from pathlib import Path

def execute(args):
    subprocess.run([str(x) for x in args], check=True)

def render(clips, output, music=None, width=480, height=854, fps=30, max_duration=12):
    if not clips or width % 2 or height % 2 or max_duration <= 0:
        raise ValueError("Invalid clips, dimensions, or duration")
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    pattern = [(0.85,1),(0.40,.36),(.45,1.55),(.85,1),(.50,.42),(.55,1.6)]
    with tempfile.TemporaryDirectory(prefix="pulse-edit-") as tmp:
        parts=[]
        total=0.0
        for i in range(60):
            if total >= max_duration-.03: break
            source=Path(clips[i%len(clips)]).resolve()
            if not source.is_file(): raise FileNotFoundError(source)
            raw, speed=pattern[i%len(pattern)]
            length=min(raw/speed, max_duration-total)
            raw=length*speed
            clip_duration=float(subprocess.check_output(["ffprobe","-v","error",
                "-show_entries","format=duration","-of","default=nw=1:nk=1",str(source)], text=True).strip())
            if clip_duration < raw: raise ValueError("Source clip too short")
            start=min(max(0,clip_duration-raw-.05), (i%4)*.83)
            dest=Path(tmp)/("part_%03d.mp4"%i)
            vf=(f"setpts=(PTS-STARTPTS)/{speed},fps={fps},"
                f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop={width}:{height},eq=contrast=1.13:saturation=1.15,"
                "unsharp=3:3:0.4,format=yuv420p")
            execute(["ffmpeg","-v","error","-y","-ss",start,"-t",raw,
                "-i",source,"-an","-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","21",dest])
            parts.append(dest);total+=length
        manifest=Path(tmp)/"list.txt"
        manifest.write_text("".join("file '%s'\n"%p.as_posix() for p in parts),encoding="utf-8")
        video=Path(tmp)/"video.mp4"
        execute(["ffmpeg","-v","error","-y","-f","concat","-safe","0",
                 "-i",manifest,"-c","copy",video])
        if music:
            execute(["ffmpeg","-v","error","-y","-i",video,"-stream_loop","-1","-i",music,
                     "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac",
                     "-b:a","160k","-t",max_duration,"-movflags","+faststart",output])
        else:
            execute(["ffmpeg","-v","error","-y","-i",video,"-c","copy",
                     "-movflags","+faststart",output])
    return output

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("clips",nargs="+")
    p.add_argument("-o","--output",required=True)
    p.add_argument("--music")
    p.add_argument("--duration",type=float,default=12)
    p.add_argument("--width",type=int,default=480)
    p.add_argument("--height",type=int,default=854)
    a=p.parse_args()
    print(render(a.clips,a.output,a.music,a.width,a.height,max_duration=a.duration))
