"""RIFE / Real-ESRGAN frame pipeline. Real inference requires actual ncnn model binaries."""
import argparse, json, re, shutil, subprocess, tempfile
from fractions import Fraction
from pathlib import Path

NAMES={'rife':'rife-ncnn-vulkan','realesrgan':'realesrgan-ncnn-vulkan'}
MODELS={'realesrgan-x4plus','realesrnet-x4plus','realesrgan-x4plus-anime','realesr-animevideov3'}

def call(args,timeout=900):
    p=subprocess.run([str(a) for a in args],capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError((p.stderr or p.stdout)[-1400:])
    return p.stdout

def probe(path):
    info=json.loads(call(['ffprobe','-v','error','-show_streams','-show_format','-of','json',path]))
    video=next((s for s in info['streams'] if s['codec_type']=='video'),None)
    if video is None:raise ValueError('Missing video track')
    rate=Fraction(video['avg_frame_rate'])
    if rate<=0:raise ValueError('Invalid source framerate')
    return video,float(rate),float(info['format']['duration'])

def pngs(folder):
    files=list(Path(folder).glob('*.png'))
    if not files or any(re.fullmatch(r'\d+',f.stem) is None for f in files):
        raise ValueError('Expected numbered PNG sequence')
    return sorted(files,key=lambda f:int(f.stem))

def process(source,destination,backend,executable=None,*,slow_motion=False,scale=2,
            model='realesrgan-x4plus',max_frames=600,timeout=900,gpu_id=None):
    if backend not in NAMES:raise ValueError('Unknown model backend')
    if slow_motion and backend!='rife':raise ValueError('Slow-motion only with RIFE')
    if scale not in (2,3,4) or model not in MODELS or max_frames<1 or timeout<=0:
        raise ValueError('Invalid AI settings')
    binary=executable or shutil.which(NAMES[backend])
    if not binary or not Path(binary).is_file():raise RuntimeError(NAMES[backend]+' not installed on render host')
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):raise RuntimeError('FFmpeg missing')
    src=Path(source).resolve();dest=Path(destination).resolve()
    if not src.is_file():raise FileNotFoundError(src)
    if src==dest or dest.exists():raise FileExistsError('Output exists or equals input')
    src_video,src_fps,src_duration=probe(src)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ncnn-cinema-') as temp:
        tmp=Path(temp);a=tmp/'input';b=tmp/'output';c=tmp/'normalized'
        for folder in (a,b,c):folder.mkdir()
        call(['ffmpeg','-v','error','-y','-i',src,'-map','0:v:0',
              '-fps_mode','passthrough',a/'%08d.png'],timeout)
        originals=pngs(a)
        if len(originals)>max_frames:raise ValueError('Frame budget exceeded')
        args=[binary,'-i',a,'-o',b]
        if backend=='rife':args+=['-n',str(len(originals)*2)]
        else:args+=['-s',str(scale),'-n',model]
        if gpu_id is not None:args+=['-g',str(gpu_id)]
        call(args,timeout)
        out_frames=pngs(b)
        if backend=='rife' and len(out_frames)<=len(originals):
            raise RuntimeError('RIFE emitted no extra frames')
        if backend=='realesrgan' and len(out_frames)!=len(originals):
            raise RuntimeError('Real-ESRGAN emitted wrong frame count')
        for index,file in enumerate(out_frames,1):shutil.copyfile(file,c/('%08d.png'%index))
        output_fps=src_fps if slow_motion or backend!='rife' else src_fps*len(out_frames)/len(originals)
        silent=tmp/'silent.mp4'
        call(['ffmpeg','-v','error','-y','-framerate',str(output_fps),'-start_number','1',
              '-i',c/'%08d.png','-c:v','libx264','-crf','19','-pix_fmt','yuv420p',silent],timeout)
        if slow_motion:shutil.move(silent,dest)
        else:
            call(['ffmpeg','-v','error','-y','-i',silent,'-i',src,'-map','0:v:0','-map','1:a:0?',
                  '-c:v','copy','-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',dest],timeout)
        info,_,actual_duration=probe(dest)
        if abs(actual_duration-(src_duration*(len(out_frames)/len(originals) if slow_motion else 1)))>.35:
            raise RuntimeError('Wrong resulting duration')
        if backend=='realesrgan' and info['width']<src_video['width']*scale:
            raise RuntimeError('Upscale did not produce requested frame size')
        call(['ffmpeg','-v','error','-xerror','-i',dest,'-f','null','-'],timeout)
    return {'backend':backend,'executable':str(binary),'input_frames':len(originals),
            'output_frames':len(out_frames),'width':info['width'],'height':info['height'],
            'duration':round(actual_duration,3),'full_decode_pass':True}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('backend',choices=sorted(NAMES))
    p.add_argument('source');p.add_argument('destination');p.add_argument('--executable')
    p.add_argument('--slow-motion',action='store_true');p.add_argument('--scale',type=int,default=2)
    p.add_argument('--model',default='realesrgan-x4plus');p.add_argument('--gpu-id')
    a=p.parse_args();print(json.dumps(process(a.source,a.destination,a.backend,a.executable,
       slow_motion=a.slow_motion,scale=a.scale,model=a.model,gpu_id=a.gpu_id),indent=2))
