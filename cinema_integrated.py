#!/usr/bin/env python3
"""Cinema Edit Studio — integrated assistant-run, no-text cinematic reels.
Local Python + FFmpeg only. Optional neural AI / Blender are NOT bundled.
"""
import argparse
import array
import json
import math
import random
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

def run(args, capture=False):
    cmd=[str(a) for a in args]
    p=subprocess.run(cmd, check=False,
                     stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                     stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError('Command failed: '+ ' '.join(cmd[:6])+' | '+p.stderr.decode('utf-8','replace')[-2200:])
    return p.stdout if capture else None

def probe(path):
    data=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',path],capture=True))
    v=next((s for s in data['streams'] if s['codec_type']=='video'),None)
    if not v: raise ValueError('No video stream: '+str(path))
    return float(data['format']['duration']),v['width'],v['height']

def generate_music(path, seconds, bpm=140):
    """Original synth rhythm; no copyrighted recordings."""
    sr=22050
    N=round((seconds+0.4)*sr)
    samples=array.array('f',[0.0])*N
    beat=60/bpm
    rng=random.Random(119)
    for n in range(int(seconds/beat)+3):
        start=int(n*beat*sr)
        if start>=N:break
        for j in range(min(int(.28*sr),N-start)):
            t=j/sr
            samples[start+j]+=.58*math.sin(2*math.pi*(57*t+90*(1-math.exp(-35*t))/35))*math.exp(-23*t)
        if n%2:
            for j in range(min(int(.16*sr),N-start)):
                t=j/sr
                samples[start+j]+=.19*(rng.random()*2-1)*math.exp(-25*t)
        for sub in range(2):
            at=start+int(sub*beat*.5*sr)
            for j in range(min(int(.055*sr),max(0,N-at))):
                t=j/sr
                samples[at+j]+=.09*(rng.random()*2-1)*math.exp(-65*t)
    notes=[55,55,65.41,49,55,73.42,65.41,49]
    for k in range(int(seconds/(beat/2))+3):
        start=int(k*beat*.5*sr)
        if start>=N:break
        hz=notes[k%len(notes)]
        for j in range(min(int(.18*sr),N-start)):
            t=j/sr
            samples[start+j]+=.18*math.sin(2*math.pi*hz*t)*(1-math.exp(-55*t))*math.exp(-7*t)
    frames=array.array('h',(int(29000*math.tanh(1.3*v)*min(1,(N-i)/(sr*.5)))
                            for i,v in enumerate(samples)))
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr)
        w.writeframes(frames.tobytes())
    return path

def beats_from_track(path, seconds, minimum=.52):
    """Approximate music onsets, falling back to 140-BPM cuts."""
    with tempfile.TemporaryDirectory(prefix='cinema-beats-') as td:
        wav=Path(td)/'track.wav'
        run(['ffmpeg','-v','error','-y','-i',path,'-t',seconds,'-ac',1,
             '-ar',8000,'-acodec','pcm_s16le',wav])
        with wave.open(str(wav),'rb') as w:
            b=array.array('h');b.frombytes(w.readframes(w.getnframes()))
    hop=400
    energy=[math.sqrt(sum(x*x for x in b[i:i+hop])/len(b[i:i+hop]))
            for i in range(0,len(b)-hop,hop)]
    novelty=[max(0,energy[i]-energy[i-1]) for i in range(1,len(energy))]
    positive=sorted(v for v in novelty if v>0)
    threshold=positive[int(.70*(len(positive)-1))] if positive else float('inf')
    selected=[]
    for i in range(1,len(novelty)-1):
        t=(i+1)*hop/8000
        if .62<t<seconds-.45 and novelty[i]>threshold and novelty[i]>=novelty[i-1] and novelty[i]>=novelty[i+1] and (not selected or t-selected[-1]>=minimum):
            selected.append(t)
    if len(selected)<2:
        selected=[n*60/140 for n in range(2,int(seconds*140/60))]
    cuts=[0.]
    for b in selected:
        if b-cuts[-1]>=minimum and seconds-b>=.48:cuts.append(round(b,3))
    if seconds-cuts[-1]<.55 and len(cuts)>1:cuts.pop()
    cuts.append(float(seconds))
    return cuts

def frame_score(video, at):
    raw=run(['ffmpeg','-v','error','-ss',str(at),'-i',video,
             '-vf','scale=80:44,format=gray','-frames:v','1','-f','rawvideo','-'],capture=True)
    if len(raw)<80*44:return 0.
    mu=sum(raw)/len(raw)
    variance=sum((v-mu)**2 for v in raw)/len(raw)
    sharp=sum(abs(raw[i]-raw[i-1]) for i in range(1,len(raw)))/len(raw)
    return (variance**.5+2*sharp)*min(1,mu/43)

def choose_windows(clips, cuts):
    durations=[probe(c)[0] for c in clips]
    score=[]
    for i,c in enumerate(clips):
        d=durations[i]
        score.append((max(frame_score(c,max(.1,d*.25)),
                          frame_score(c,max(.1,d*.60))),i))
    order=[idx for _,idx in sorted(score,reverse=True)]
    result=[]
    for j,(a,b) in enumerate(zip(cuts,cuts[1:])):
        target=b-a
        required=target*1.2+.12
        available=[idx for idx in order if durations[idx]>required]
        if not available:raise ValueError('Every source clip is too short for requested cut duration')
        idx=available[j%len(available)]
        d=durations[idx]
        start=max(0,min(d-required-.04,(d-required)*(.18 if j%2==0 else .55)))
        result.append({'path':str(clips[idx]),'start':round(start,3),
                       'seconds':round(target,3),'score':round(score[idx][0],3)})
    return result

def segment(source, start, seconds, out, w, h, fps, mode, interpolate):
    ramp=seconds>=.85
    fractions=[.23,.53,.24] if ramp else [1.]
    speeds=[1.55,.64,1.55] if ramp else [1.12]
    parts=[];pos=0
    for j,(f,speed) in enumerate(zip(fractions,speeds)):
        time=seconds*f;length=time*speed
        vf=f'trim=start={pos:.5f}:end={pos+length:.5f},setpts=(PTS-STARTPTS)/{speed:.5f},'
        if interpolate and speed<1:
            vf+=f'minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir,'
        vf+=f'fps={fps},scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},'
        if mode=='cinematic':vf+='eq=contrast=1.14:saturation=1.06:gamma=1.01,vignette=PI/7,'
        elif mode=='sport':vf+='eq=contrast=1.17:saturation=1.18,unsharp=3:3:.45,'
        else:vf+='eq=contrast=1.09:saturation=1.05,'
        if speed>1.3 and w>=40 and h>=40:
            vf+=f'crop={w-8}:{h-8}:x=4+3*sin(t*11):y=4+3*cos(t*9),scale={w}:{h},'
        vf+='setsar=1,format=yuv420p'
        parts.append(vf+f'[p{j}]')
        pos+=length
    graph=';'.join(f'[0:v]{f}' for f in parts)
    graph+=';' + ''.join(f'[p{i}]' for i in range(len(parts)))+f'concat=n={len(parts)}:v=1:a=0[v]'
    run(['ffmpeg','-v','error','-y','-ss',start,'-t',pos+.02,'-i',source,
         '-filter_complex',graph,'-map','[v]','-an','-c:v','libx264',
         '-preset','veryfast','-crf',21,'-r',fps,'-video_track_timescale',30000,out])

def merge(parts, output, crossfade, w, h, fps):
    if len(parts)==1:
        shutil.copyfile(parts[0],output)
        return
    lengths=[probe(p)[0] for p in parts]
    if any(x<=crossfade for x in lengths):raise ValueError('Too-short shot for transition')
    inputs=sum((['-i',p] for p in parts),[])
    graph=[];accum=lengths[0];last='0:v'
    effects=['fade','smoothleft','fadeblack','wipeleft']
    for i in range(1,len(parts)):
        tag=f'x{i}'
        graph.append(f'[{last}][{i}:v]xfade=transition={effects[(i-1)%len(effects)]}:duration={crossfade:.4f}:offset={accum-crossfade:.4f}[{tag}]')
        last=tag;accum+=lengths[i]-crossfade
    graph.append(f'[{last}]format=yuv420p[v]')
    run(['ffmpeg','-v','error','-y',*inputs,'-filter_complex',';'.join(graph),
         '-map','[v]','-an','-c:v','libx264','-preset','veryfast','-crf',20,
         '-pix_fmt','yuv420p',output])

def verify(path, w, h, audio=True):
    data=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams',
                         '-of','json',path],capture=True))
    vs=[s for s in data['streams'] if s['codec_type']=='video']
    aus=[s for s in data['streams'] if s['codec_type']=='audio']
    if len(vs)!=1 or vs[0]['width']!=w or vs[0]['height']!=h:
        raise ValueError('Incorrect video stream or dimensions')
    if audio and not aus:raise ValueError('Missing audio')
    if any(s['codec_type']=='subtitle' for s in data['streams']):raise ValueError('Unexpected subtitles')
    if float(data['format']['duration'])<=0:raise ValueError('Empty video')
    run(['ffmpeg','-v','error','-xerror','-i',path,'-f','null','-'])
    return {'duration':round(float(data['format']['duration']),2),
            'size_bytes':Path(path).stat().st_size,
            'video_codec':vs[0]['codec_name'],
            'audio_codec':aus[0]['codec_name'] if aus else None,
            'width':w,'height':h,'decoded':True,'no_text':True}

def render(clips, output, music=None, seconds=12, width=720, height=1280,
           fps=30, style='sport', interpolate=True, fade=.08, verify_output=True):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('FFmpeg / FFprobe are required in render environment')
    clips=[Path(c).resolve() for c in clips]
    output=Path(output).resolve()
    if not clips or any(not c.is_file() for c in clips):raise ValueError('No usable input clips')
    if output in clips:raise ValueError('Never overwrite original footage')
    if music and Path(music).resolve()==output:raise ValueError('Music and output paths must differ')
    if width<64 or height<64 or width%2 or height%2 or fps<12 or fps>60 or seconds<2 or seconds>120 or fade<0 or fade>.25:
        raise ValueError('Invalid output settings')
    if style not in ('sport','cinematic','clean'):raise ValueError('Unsupported style')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cinema-integration-') as t:
        folder=Path(t)
        source_music=Path(music).resolve() if music else generate_music(folder/'original_soundtrack.wav',seconds)
        if not source_music.is_file():raise FileNotFoundError(source_music)
        cuts=beats_from_track(source_music,seconds)
        plan=choose_windows(clips,cuts)
        shots=[]
        for i,item in enumerate(plan):
            part=folder/f'shot_{i:03d}.mp4'
            segment(item['path'],item['start'],item['seconds'],part,width,height,fps,style,interpolate)
            shots.append(part)
        joined=folder/'joined.mp4'
        merge(shots,joined,fade,width,height,fps)
        joined_duration=probe(joined)[0]
        run(['ffmpeg','-v','error','-y','-i',joined,'-stream_loop','-1','-i',source_music,
             '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k',
             '-af',f'afade=t=in:st=0:d=0.15,afade=t=out:st={max(0,joined_duration-0.60):.3f}:d=0.55,alimiter=limit=0.90',
             '-shortest','-movflags','+faststart',output])
    stats=verify(output,width,height) if verify_output else {'duration':probe(output)[0]}
    return {'file':str(output),'shots':len(plan),'style':style,'source_videos':len(clips),
            'music_source':'provided' if music else 'original generated',
            'interpolation':'ffmpeg optical flow' if interpolate else 'simple fps',
            'note':'No neural AI or Blender 3D was run; upscaling cannot restore all source detail.',
            'quality':stats}

def main():
    p=argparse.ArgumentParser(description='Assistant-run cinematic reel maker. No text overlays.')
    p.add_argument('clips',nargs='+')
    p.add_argument('-o','--output',required=True)
    p.add_argument('--music')
    p.add_argument('--seconds',type=float,default=12)
    p.add_argument('--width',type=int,default=720)
    p.add_argument('--height',type=int,default=1280)
    p.add_argument('--fps',type=int,default=30)
    p.add_argument('--style',choices=['sport','cinematic','clean'],default='sport')
    p.add_argument('--no-optical-flow',action='store_true')
    args=p.parse_args()
    print(json.dumps(render(args.clips,args.output,args.music,args.seconds,args.width,args.height,
                            args.fps,args.style,not args.no_optical_flow),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
