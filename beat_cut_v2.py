#!/usr/bin/env python3
"""Audio-onset-synchronized, source-preserving short reel builder."""
import argparse, json, math, subprocess, tempfile, wave
from pathlib import Path

def call(*args):
    subprocess.run(list(map(str,args)),check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(path)],text=True))

def onsets(audio, minimum=0.38):
    with tempfile.TemporaryDirectory() as t:
        wav=Path(t)/'track.wav'
        call('ffmpeg','-y','-v','error','-i',audio,'-ac',1,'-ar',8000,'-acodec','pcm_s16le',wav)
        import array
        with wave.open(str(wav)) as f:
            samples=array.array('h');samples.frombytes(f.readframes(f.getnframes()))
        hop=200; energies=[]
        for i in range(0,len(samples)-hop,hop):
            v=samples[i:i+hop]
            energies.append(math.sqrt(sum(x*x for x in v)/hop))
        if len(energies)<5:return []
        novelty=[max(0,energies[i]-energies[i-1]) for i in range(1,len(energies))]
        positive=sorted(x for x in novelty if x>0)
        if not positive:return []
        threshold=positive[int(.72*(len(positive)-1))]
        marks=[]
        for i in range(1,len(novelty)-1):
            sec=(i+1)*hop/8000
            if novelty[i]>=threshold and novelty[i]>=novelty[i-1] and novelty[i]>novelty[i+1] and (not marks or sec-marks[-1]>=minimum):marks.append(sec)
        return marks

def render(clips,music,out,seconds=12,width=360,height=640,fps=30):
    if not clips or seconds<=0 or width%2 or height%2:raise ValueError('invalid configuration')
    clips=[Path(p).resolve() for p in clips];music=Path(music).resolve();out=Path(out).resolve()
    if any(not p.is_file() for p in clips+[music]):raise FileNotFoundError('input missing')
    lengths=[float(probe(p)['format']['duration']) for p in clips]
    beats=[x for x in onsets(music) if .4<x<seconds-.4]
    cuts=[0.0]
    for x in beats:
        if x-cuts[-1]>=.48:cuts.append(x)
    if seconds-cuts[-1]<.4:cuts.pop()
    cuts.append(float(seconds))
    with tempfile.TemporaryDirectory(prefix='beatcut-') as tmp:
        segments=[]
        for k,(a,b) in enumerate(zip(cuts,cuts[1:])):
            idx=k%len(clips);span=b-a
            if lengths[idx]<span+.1: raise ValueError(f'clip {idx+1} too short for {span:.2f} sec')
            start=min(max(0,lengths[idx]-span-.08), (k%4)*.9)
            path=Path(tmp)/f'seg{k:03}.mp4'
            vf=f'scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height},fps={fps},eq=contrast=1.08:saturation=1.09,format=yuv420p'
            call('ffmpeg','-y','-v','error','-ss',f'{start:.4f}','-t',f'{span:.4f}','-i',clips[idx],'-an','-vf',vf,'-c:v','libx264','-crf',23,'-preset','ultrafast','-video_track_timescale',30000,path)
            segments.append(path)
        manifest=Path(tmp)/'list.txt';manifest.write_text(''.join(f"file '{p.as_posix()}'\n" for p in segments))
        out.parent.mkdir(parents=True,exist_ok=True)
        call('ffmpeg','-y','-v','error','-f','concat','-safe',0,'-i',manifest,'-stream_loop',-1,'-i',music,'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','ultrafast','-crf',23,'-c:a','aac','-b:a','160k','-t',seconds,'-movflags','+faststart',out)
    return {'output':str(out),'cuts':len(cuts)-1,'onsets':len(beats),'duration':float(probe(out)['format']['duration'])}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('music');p.add_argument('clips',nargs='+');p.add_argument('-o','--output',required=True);p.add_argument('--seconds',type=float,default=12);p.add_argument('--width',type=int,default=360);p.add_argument('--height',type=int,default=640)
    a=p.parse_args();print(json.dumps(render(a.clips,a.music,a.output,a.seconds,a.width,a.height),indent=2))
