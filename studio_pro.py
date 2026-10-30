#!/usr/bin/env python3
"""Cinema Edit Studio 12-backend orchestrator; optional stages are explicit."""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from cinema_integrated import render as render_cinematic, verify
from studio_backends import (scene_intervals,export_otio,export_mlt,stabilize,
                             frei0r_filter,bake_ocio,color_transform,auto_cut,transcribe)

def call(args,timeout=1200):
    r=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=timeout)
    if r.returncode:raise RuntimeError((r.stderr or r.stdout)[-1500:])
    return r.stdout

def options_render(source_files,destination,*,music=None,seconds=12,width=720,height=1280,
                   style='sport',stabilize_input=False,detect_scenes=False,
                   auto_editor=None,frei0r=None,ocio_config=None,ocio_input=None,
                   ocio_output=None,with_otio=True,with_mlt=True,
                   rife_binary=None,realesrgan_binary=None,blender_binary=None,
                   whisper_binary=None,whisper_model=None,interpolate=True):
    """Return a truthful per-stage manifest alongside MP4. Originals never overwritten."""
    inputs=[Path(x).resolve() for x in source_files]
    output=Path(destination).resolve()
    if not inputs or any(not x.is_file() for x in inputs):raise FileNotFoundError('One or more source clips missing')
    if output in inputs or output.exists():raise ValueError('Output exists or equals source')
    if width%2 or height%2 or min(width,height)<64:raise ValueError('Invalid output resolution')
    output.parent.mkdir(parents=True,exist_ok=True)
    stages={}
    with tempfile.TemporaryDirectory(prefix='cinema-pro-') as temp:
        tmp=Path(temp)
        prepared=inputs
        if auto_editor:
            processed=[]
            for i,src in enumerate(prepared):
                result=tmp/f'autocut_{i:02d}.mp4'
                auto_cut(src,result,auto_editor)
                processed.append(result)
            prepared=processed
            stages['auto_editor']='executed'
        if stabilize_input:
            processed=[]
            for i,src in enumerate(prepared):
                target=tmp/f'stable_{i:02d}.mp4'
                stabilize(src,target)
                processed.append(target)
            prepared=processed
            stages['vidstab']='executed'
        if detect_scenes:
            processed=[]
            for i,src in enumerate(prepared):
                detected=scene_intervals(src)
                for j,scene in enumerate(detected[:3]):
                    length=scene['end']-scene['start']
                    if length<1.2:continue
                    dst=tmp/f'scene_{i:02d}_{j:02d}.mp4'
                    call(['ffmpeg','-v','error','-y','-ss',scene['start'],'-i',src,
                          '-t',length,'-c:v','libx264','-crf','20','-an',dst])
                    processed.append(dst)
            if processed:prepared=processed
            stages['pyscenedetect']='executed'
        shot_manifest=[]
        for src in inputs:
            probe=json.loads(call(['ffprobe','-v','error','-show_format','-of','json',src]))
            duration=float(probe['format']['duration'])
            shot_manifest.append({'file':str(src),'start':0.0,'duration':min(2.0,duration)})
        if with_otio:
            saved=output.with_suffix('.otio')
            export_otio(shot_manifest,saved,music=music)
            stages['opentimelineio']=str(saved)
        if with_mlt:
            saved=output.with_suffix('.mlt')
            export_mlt(shot_manifest,saved,music=music)
            stages['mlt_xml']=str(saved)
        rendered=tmp/'edited.mp4'
        result=render_cinematic(prepared,rendered,music=music,seconds=seconds,
                                width=width,height=height,style=style,interpolate=interpolate)
        stages['ffmpeg']=result
        current=rendered
        if frei0r:
            next_file=tmp/'frei0r.mp4'
            frei0r_filter(current,next_file,name=frei0r)
            current=next_file
            stages['frei0r']='executed'
        if ocio_config or (ocio_input and ocio_output):
            if not ocio_input or not ocio_output:raise ValueError('OCIO color spaces required')
            lut=bake_ocio(ocio_config,ocio_input,ocio_output,tmp/'transform.cube')
            next_file=tmp/'ocio.mp4'
            color_transform(current,next_file,lut)
            current=next_file
            stages['opencolorio']='executed'
        if rife_binary:
            from neural_video import process
            next_file=tmp/'rife.mp4'
            stages['rife']=process(current,next_file,'rife',executable=rife_binary,
                                   slow_motion=False,max_frames=1000)
            current=next_file
        if realesrgan_binary:
            from neural_video import process
            next_file=tmp/'sr.mp4'
            stages['real_esrgan']=process(current,next_file,'realesrgan',
                                         executable=realesrgan_binary,
                                         scale=2,max_frames=1000)
            current=next_file
        if blender_binary:
            # Script renders a separate optional 3D trailer; do not alter source audio.
            script=Path(__file__).resolve().parent/'blender_scene.py'
            cpu_script=tmp/'blender_cpu.py'
            text=script.read_text()
            text=text.replace('scene.render.engine="BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"',
                              'scene.render.engine="CYCLES"\nscene.cycles.device="CPU"\nscene.cycles.samples=8')
            text=text.replace('scene.render.resolution_x=720',f'scene.render.resolution_x={width}')
            text=text.replace('scene.render.resolution_y=1280',f'scene.render.resolution_y={height}')
            text=text.replace('scene.frame_end=90','scene.frame_end=12')
            cpu_script.write_text(text)
            trailer=tmp/'blender_raw.mp4'
            call([blender_binary,'-b','-noaudio','--python',cpu_script,'--',trailer],timeout=900)
            concat=tmp/'appended.mp4'
            # Compose using concat filter; audio is passed through for the real montage.
            call(['ffmpeg','-v','error','-y','-i',current,'-i',trailer,
                  '-filter_complex','[0:v]fps=30,format=yuv420p[v0];[1:v]fps=30,format=yuv420p[v1];[v0][v1]concat=n=2:v=1:a=0[v]',
                  '-map','[v]','-map','0:a:0?','-c:v','libx264','-crf','20',
                  '-c:a','aac','-movflags','+faststart',concat])
            current=concat
            stages['blender']='executed'
        shutil.copyfile(current,output)
        if whisper_binary or whisper_model:
            if not whisper_binary or not whisper_model:raise ValueError('Whisper binary and model both required')
            stages['whisper_cpp_srt']=str(transcribe(inputs[0],output.with_suffix(''),whisper_binary,whisper_model))
    final=verify(output,width if not realesrgan_binary else width*2,
                 height if not realesrgan_binary else height*2)
    manifest={'output':str(output),'original_files_untouched':True,
              'no_burned_captions':True,'modules':stages,'qa':final}
    Path(str(output)+'.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    return manifest

def main():
    p=argparse.ArgumentParser(description='Assistant-only cinematic processing. No text by default.')
    p.add_argument('clips',nargs='+');p.add_argument('-o','--output',required=True)
    p.add_argument('--music');p.add_argument('--seconds',type=float,default=12)
    p.add_argument('--width',type=int,default=720);p.add_argument('--height',type=int,default=1280)
    p.add_argument('--style',choices=('sport','cinematic','clean'),default='sport')
    p.add_argument('--stabilize',action='store_true');p.add_argument('--scene-detect',action='store_true')
    p.add_argument('--auto-editor-bin');p.add_argument('--frei0r')
    p.add_argument('--ocio-config');p.add_argument('--ocio-input');p.add_argument('--ocio-output')
    p.add_argument('--no-optical-flow',action='store_true')
    p.add_argument('--rife-bin');p.add_argument('--realesrgan-bin');p.add_argument('--blender-bin')
    p.add_argument('--whisper-bin');p.add_argument('--whisper-model')
    a=p.parse_args()
    print(json.dumps(options_render(a.clips,a.output,music=a.music,seconds=a.seconds,
      width=a.width,height=a.height,style=a.style,stabilize_input=a.stabilize,
      detect_scenes=a.scene_detect,auto_editor=a.auto_editor_bin,frei0r=a.frei0r,
      ocio_config=a.ocio_config,ocio_input=a.ocio_input,ocio_output=a.ocio_output,
      interpolate=not a.no_optical_flow,rife_binary=a.rife_bin,
      realesrgan_binary=a.realesrgan_bin,blender_binary=a.blender_bin,
      whisper_binary=a.whisper_bin,whisper_model=a.whisper_model),indent=2))
if __name__=='__main__':
    main()
