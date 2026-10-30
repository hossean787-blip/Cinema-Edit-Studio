"""Phase 2 cinematic video engine: speed ramps, optical-flow, shake and crossfades."""
import argparse,json,subprocess,tempfile
from pathlib import Path

def run(a): subprocess.run([str(x) for x in a],check=True)
def duration(p):
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration","-of","default=nw=1:nk=1",str(p)],text=True))

def select(clips):
    scores=[]
    for p in clips:
        d=duration(p);t=min(d*.45,max(0,d-.3))
        raw=subprocess.check_output(["ffmpeg","-v","error","-ss",str(t),"-i",str(p),
            "-frames:v","1","-vf","scale=64:36,format=gray","-f","rawvideo","-"])
        if not raw: raise ValueError("Unreadable frame")
        mean=sum(raw)/len(raw)
        variance=sum((x-mean)**2 for x in raw)/len(raw)
        scores.append((variance*min(1,mean/40),str(p)))
    return [p for _,p in sorted(scores,reverse=True)]

def render(clips,out,width=360,height=640,fps=30,transition=.16,music=None,interpolate=True):
    if not clips or width%2 or height%2 or fps<=0 or not 0<=transition<.4:raise ValueError("Invalid settings")
    clips=[Path(x).resolve() for x in clips]
    if any(not x.is_file() for x in clips):raise FileNotFoundError("Source missing")
    out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cinema-phase2-") as temp:
        folder=Path(temp);parts=[]
        for n,source in enumerate(select(clips)):
            full=duration(source)
            if full<1.82:raise ValueError("Clip shorter than 1.82 s")
            start=min(full-1.72,max(.1,full*.18))
            specs=[(.65,1),(.42,.5),(.65,1.7)]
            filters=[];pos=0
            for j,(length,speed) in enumerate(specs):
                v=f"[0:v]trim=start={pos}:end={pos+length},setpts=(PTS-STARTPTS)/{speed},"
                pos+=length
                if interpolate and speed<1:v+=f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc,"
                v+=f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,"
                v+=f"crop={width}:{height},eq=contrast=1.15:saturation=1.18,unsharp=3:3:.45,"
                if speed>1:
                    v+=f"crop={width-8}:{height-8}:x=4+3*sin(t*10):y=4+3*cos(t*9),scale={width}:{height},"
                v+=f"setsar=1,format=yuv420p[p{j}]"
                filters.append(v)
            graph=";".join(filters)+";[p0][p1][p2]concat=n=3:v=1:a=0[v]"
            part=folder/("%02d.mp4"%n)
            run(["ffmpeg","-v","error","-y","-ss",start,"-t",1.72,"-i",source,
                 "-filter_complex",graph,"-map","[v]","-an","-c:v","libx264",
                 "-preset","veryfast","-crf","21",part])
            parts.append(part)
        if len(parts)==1:video=parts[0]
        else:
            args=[]
            for part in parts:args+=["-i",part]
            lens=[duration(p) for p in parts]
            previous="0:v";elapsed=lens[0];graphs=[]
            for i in range(1,len(parts)):
                nxt="x"+str(i)
                graphs.append(f"[{previous}][{i}:v]xfade=transition=fade:duration={transition}:offset={elapsed-transition:.4f}[{nxt}]")
                elapsed+=lens[i]-transition;previous=nxt
            graphs.append(f"[{previous}]eq=brightness=0.018*sin(2*PI*t*2):eval=frame,format=yuv420p[v]")
            video=folder/"joined.mp4"
            run(["ffmpeg","-v","error","-y",*args,"-filter_complex",";".join(graphs),
                "-map","[v]","-an","-c:v","libx264","-preset","veryfast","-crf","21",video])
        if music:
            if not Path(music).is_file():raise FileNotFoundError(music)
            run(["ffmpeg","-v","error","-y","-i",video,"-stream_loop","-1","-i",music,
                "-map","0:v","-map","1:a:0","-c:v","copy","-c:a","aac",
                "-b:a","160k","-shortest","-movflags","+faststart",out])
        else:run(["ffmpeg","-v","error","-y","-i",video,"-c","copy","-movflags","+faststart",out])
    return {"output":str(out),"seconds":duration(out),"clips":len(parts)}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("clips",nargs="+");p.add_argument("-o","--output",required=True)
    p.add_argument("--width",type=int,default=360);p.add_argument("--height",type=int,default=640)
    p.add_argument("--music");p.add_argument("--no-interpolation",action="store_true")
    a=p.parse_args()
    print(json.dumps(render(a.clips,a.output,a.width,a.height,music=a.music,
        interpolate=not a.no_interpolation),indent=2))
