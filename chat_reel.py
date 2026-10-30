#!/usr/bin/env python3
"""Chat-first reel builder; user only uploads footage, assistant renders with FFmpeg."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from studio import assemble

def get_duration(path):
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True).strip())

def create_reel(clips, output, music=None, length=18, shot=2.0, resolution=(720,1280)):
    clips=[Path(p).resolve() for p in clips]
    if not clips or any(not p.is_file() for p in clips):
        raise ValueError("Videos not found")
    if length <= 0 or shot <= 0:
        raise ValueError("Positive duration required")
    durations=[get_duration(p) for p in clips]
    shots=[]
    remaining=float(length)
    index=0
    while remaining > 0.02:
        i=index%len(clips)
        source_length=durations[i]
        if source_length < 0.25:
            raise ValueError("Source clip too short")
        duration=min(float(shot),remaining,source_length)
        start=max(0,(source_length-duration)*(.22 if index%2==0 else .55))
        shots.append({"file":str(clips[i]),"start":round(start,3),"duration":round(duration,3),"speed":1.0})
        remaining-=duration
        index+=1
        if index>1000:
            raise ValueError("Too many shots")
    with tempfile.TemporaryDirectory(prefix="chat-reel-") as tmp:
        manifest=Path(tmp)/"project.json"
        manifest.write_text(json.dumps({"resolution":list(resolution),"fps":30,"shots":shots,
                                         "music":str(Path(music).resolve()) if music else None}),encoding="utf-8")
        return assemble(manifest,output)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("clips",nargs="+")
    p.add_argument("-o","--output",required=True)
    p.add_argument("--music")
    p.add_argument("--length",type=float,default=18)
    p.add_argument("--shot",type=float,default=2)
    a=p.parse_args()
    print(create_reel(a.clips,a.output,a.music,a.length,a.shot))
