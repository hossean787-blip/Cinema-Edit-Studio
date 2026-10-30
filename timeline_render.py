#!/usr/bin/env python3
"""Editable manual timeline renderer. No user video is modified."""
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from cinema_integrated import generate_music, verify
from studio_backends import export_otio, export_mlt

STYLES={"sport":"eq=contrast=1.17:saturation=1.15,unsharp=3:3:0.45",
        "cinematic":"eq=contrast=1.13:saturation=0.92,vignette=PI/7",
        "clean":"eq=contrast=1.05:saturation=1.04"}
def exec_checked(args, timeout=3600):
    p=subprocess.run([str(x) for x in args],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=timeout)
    if p.returncode: raise RuntimeError((p.stderr or b"render failed").decode("utf-8","replace")[-1800:])

def render_timeline(shots, output, *, resolution=(720,1280), fps=30,
                    style="sport", transition=0.12, music=None,
                    optical_flow=True, stabilize=False, on_progress=None):
    w,h=map(int,resolution)
    fps=int(fps); output=Path(output).resolve()
    if not shots or len(shots)>80:raise ValueError("Number of shots must be 1–80")
    if w<64 or h<64 or w>4096 or h>4096 or w%2 or h%2 or fps not in (24,25,30,60):
        raise ValueError("Invalid resolution or frame rate")
    if style not in STYLES or not 0<=transition<=0.5:raise ValueError("Invalid style/transition")
    if output.exists(): raise FileExistsError("Output already exists")
    clean=[]
    for i,shot in enumerate(shots):
        src=Path(shot['file']).resolve()
        start=float(shot.get('start',0)); length=float(shot['duration']);speed=float(shot.get('speed',1))
        if not src.is_file() or output==src:raise ValueError("Missing video or unsafe output")
        if not all(math.isfinite(v) for v in (start,length,speed)):raise ValueError("Invalid timeline values")
        if start<0 or length<=0 or length>300 or speed<0.2 or speed>4:
            raise ValueError("Invalid clip trim or speed")
        if type(shot.get("ramp",False)) is not bool:raise ValueError("Invalid speed ramp")
        clean.append({"file":str(src),"start":start,"duration":length,"speed":speed,
                      "ramp":shot.get("ramp",False)})
    music=Path(music).resolve() if music else None
    if music and not music.is_file():raise FileNotFoundError(music)
    total=sum(s['duration']/s['speed'] for s in clean)
    if total>300:raise ValueError("Project longer than 5-minute limit")
    output.parent.mkdir(parents=True,exist_ok=True)
    if on_progress:on_progress(2,"شروع پردازش تایم‌لاین")
    with tempfile.TemporaryDirectory(prefix="cinema-timeline-") as td:
        tmp=Path(td);segments=[]
        for idx,shot in enumerate(clean):
            source=Path(shot["file"])
            if stabilize:
                from studio_backends import stabilize as stabilize_video
                stable=tmp/f"stable_{idx}.mp4"
                stabilize_video(source,stable)
                source=stable
            common=(f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,"
                    f"crop={w}:{h},setsar=1,{STYLES[style]},format=yuv420p")
            segment=tmp/f"clip_{idx:03}.mp4"
            base=["ffmpeg","-hide_banner","-loglevel","error","-y","-ss",shot["start"],
                  "-t",shot["duration"],"-i",source,"-an"]
            if shot.get("ramp") and shot["duration"]>=.6:
                fast=min(4,shot["speed"]*2)
                slow=.5/(1/shot["speed"]-.5/fast)
                starts=[0,shot["duration"]*.25,shot["duration"]*.75]
                ends=[starts[1],starts[2],shot["duration"]]
                speeds=[fast,slow,fast];parts=[]
                for n,sp in enumerate(speeds):
                    interp=(f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc,"
                            if optical_flow and sp<1 else "")
                    parts.append(f"[0:v]trim=start={starts[n]:.5f}:end={ends[n]:.5f},"
                                 f"setpts=(PTS-STARTPTS)/{sp:.5f},{interp}fps={fps},"
                                 f"{common}[s{n}]")
                graph=";".join(parts)+";[s0][s1][s2]concat=n=3:v=1:a=0[out]"
                commands=base+["-filter_complex",graph,"-map","[out]"]
            else:
                interp=(f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc,"
                        if optical_flow and shot["speed"]<1 else "")
                vf=(f"setpts=(PTS-STARTPTS)/{shot['speed']},"
                    f"{interp}fps={fps},{common}")
                commands=base+["-vf",vf]
            exec_checked(commands+["-c:v","libx264","-preset","veryfast","-crf","20",
                                  "-video_track_timescale","30000",segment])
            segments.append(segment)
            if on_progress:on_progress(8+int(64*(idx+1)/len(clean)),f"پردازش نمای {idx+1} از {len(clean)}")
        joined=tmp/"joined.mp4"
        if len(segments)==1:shutil.copyfile(segments[0],joined)
        elif transition>0:
            durations=[]
            for seg in segments:
                meta=json.loads(subprocess.check_output(
                    ["ffprobe","-v","error","-show_entries","format=duration","-of","json",seg]))
                durations.append(float(meta["format"]["duration"]))
            cross=min(transition,*[max(0,d-.08) for d in durations])
            if cross<=0:raise ValueError("Clips too short for transition")
            args=[]
            for seg in segments:args+=["-i",seg]
            offsets=durations[0];last="0:v";graphs=[]
            for idx in range(1,len(segments)):
                tag=f"c{idx}"
                graphs.append(f"[{last}][{idx}:v]xfade=transition=fade:duration={cross:.4f}:offset={offsets-cross:.4f}[{tag}]")
                last=tag;offsets+=durations[idx]-cross
            graphs.append(f"[{last}]format=yuv420p[out]")
            exec_checked(["ffmpeg","-loglevel","error","-y",*args,"-filter_complex",
                         ";".join(graphs),"-map","[out]","-c:v","libx264",
                         "-preset","veryfast","-crf","20",joined])
        else:
            manifest=tmp/"list.txt"
            manifest.write_text("".join("file '"+p.as_posix()+"'\n" for p in segments))
            exec_checked(["ffmpeg","-loglevel","error","-y","-f","concat","-safe","0",
                         "-i",manifest,"-c","copy",joined])
        if on_progress:on_progress(80,"تدوین تصویر آماده شد")
        if music is None:
            music=generate_music(tmp/"original_music.wav",total)
        stage=tmp/"checked.mp4"
        exec_checked(["ffmpeg","-loglevel","error","-y","-i",joined,
                      "-stream_loop","-1","-i",music,"-map","0:v:0","-map","1:a:0",
                      "-c:v","copy","-c:a","aac","-b:a","192k","-shortest",
                      "-movflags","+faststart",stage])
        if on_progress:on_progress(90,"کنترل کامل تصویر و صدا")
        info=verify(stage,w,h,audio=True)
        # Emit editable sidecars referring to durable inputs, not transient fragments.
        # Speed is recorded in metadata because native basic MLT/OTIO export does not retime.
        export_otio(clean,output.with_suffix(".otio"),fps=fps,music=music if music and music.parent!=tmp else None)
        export_mlt(clean,output.with_suffix(".mlt"),fps=fps,music=music if music and music.parent!=tmp else None)
        timing=output.with_suffix(".timeline.json")
        timing.write_text(json.dumps({"shots":clean,"speed_aware":True,"fps":fps,
            "note":"OTIO/MLT tracks represent raw trim spans; speed ramps are authoritative in timeline JSON."},indent=2))
        os.replace(stage,output)
        if on_progress:on_progress(100,"رندر تأیید شد")
    return {"file":str(output),"qa":info,"shot_count":len(clean),"resolution":[w,h],"fps":fps}
