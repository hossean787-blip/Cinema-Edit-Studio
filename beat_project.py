"""Produce a beat-synchronized edit manifest from local video files."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from beat_sync import detect_beats

def duration(filename):
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(filename)],text=True).strip())

def plan(music, clips, output, width=1080, height=1920, fps=30, min_shot=0.55):
    if not shutil.which("ffprobe"): raise RuntimeError("FFprobe required")
    music=Path(music).resolve()
    if not music.is_file(): raise FileNotFoundError(music)
    output=Path(output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    clips=[Path(x).resolve() for x in clips]
    if not clips or any(not x.is_file() for x in clips): raise ValueError("Missing clips")
    music_dur=duration(music)
    if music_dur<=0: raise ValueError("Invalid music")
    beats=[0.0]+[b for b in detect_beats(music) if b>0 and b<music_dur]+[music_dur]
    cuts=[0.]
    for t in beats[1:]:
        if t-cuts[-1]>=min_shot: cuts.append(t)
    if cuts[-1]<music_dur: cuts.append(music_dur)
    durations=[duration(c) for c in clips]
    shots=[]
    for i,(a,b) in enumerate(zip(cuts,cuts[1:])):
        clip=clips[i%len(clips)]
        if durations[i%len(clips)]<b-a: continue
        shots.append({"file":str(clip),"start":0,"duration":round(b-a,3),"speed":1.0})
    if not shots: raise ValueError("No usable shots")
    cfg={"resolution":[width,height],"fps":fps,"shots":shots,"music":str(music)}
    output.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding="utf-8")
    return output

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("music");p.add_argument("clips",nargs="+")
    p.add_argument("-o","--output",default="beat_project.json")
    a=p.parse_args()
    print(plan(a.music,a.clips,a.output))
