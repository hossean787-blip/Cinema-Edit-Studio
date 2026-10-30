"""Independent video edit backends. Optional tools fail explicitly, never silently."""
import json
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

def exec_ok(args, timeout=180):
    p=subprocess.run([str(a) for a in args],capture_output=True,text=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-1200:])
    return p.stdout

def scene_intervals(source, threshold=27):
    from scenedetect import detect, ContentDetector
    if not Path(source).is_file(): raise FileNotFoundError(source)
    scenes=detect(str(source),ContentDetector(threshold=float(threshold)),show_progress=False)
    result=[{'start':round(a.get_seconds(),4),'end':round(b.get_seconds(),4)}
            for a,b in scenes if b.get_seconds()>a.get_seconds()]
    if not result:
        info=json.loads(exec_ok(['ffprobe','-v','error','-show_format','-of','json',source]))
        return [{'start':0.0,'end':round(float(info['format']['duration']),4)}]
    return result

def export_otio(shots, output, fps=30):
    import opentimelineio as otio
    output=Path(output)
    if not shots:raise ValueError('No source shots')
    timeline=otio.schema.Timeline(name='Cinema Edit Studio')
    track=otio.schema.Track(name='Footage',kind=otio.schema.TrackKind.Video)
    for shot in shots:
        source=Path(shot['file']).resolve()
        clip=otio.schema.Clip(name=source.stem,
            media_reference=otio.schema.ExternalReference(target_url=source.as_uri()))
        start=float(shot.get('start',0));duration=float(shot['duration'])
        if start<0 or duration<=0:raise ValueError('Invalid shot range')
        clip.source_range=otio.opentime.TimeRange(
            otio.opentime.RationalTime.from_seconds(start,fps),
            otio.opentime.RationalTime.from_seconds(duration,fps))
        track.append(clip)
    timeline.tracks.append(track)
    output.parent.mkdir(parents=True,exist_ok=True)
    otio.adapters.write_to_file(timeline,str(output))
    if not output.is_file() or output.stat().st_size<100:raise RuntimeError('Invalid OTIO export')
    return output

def export_mlt(shots, output, fps=30):
    """Generate editable single-track MLT XML; external executable melt renders it."""
    if not shots:raise ValueError('No clips for MLT')
    root=ET.Element('mlt',{'LC_NUMERIC':'C','version':'7.0.0'})
    ET.SubElement(root,'profile',{'description':'Cinema Studio','width':'360','height':'640',
        'progressive':'1','sample_aspect_num':'1','sample_aspect_den':'1',
        'display_aspect_num':'9','display_aspect_den':'16','frame_rate_num':str(fps),'frame_rate_den':'1'})
    playlist=ET.SubElement(root,'playlist',{'id':'main'})
    for i,shot in enumerate(shots):
        src=Path(shot['file']).resolve()
        if not src.is_file():raise FileNotFoundError(src)
        prod=ET.SubElement(root,'producer',{'id':f'p{i}'})
        ET.SubElement(prod,'property',{'name':'mlt_service'}).text='avformat'
        ET.SubElement(prod,'property',{'name':'resource'}).text=str(src)
        start=round(float(shot.get('start',0))*fps)
        end=start+round(float(shot['duration'])*fps)-1
        if start<0 or end<start:raise ValueError('Invalid MLT timing')
        ET.SubElement(playlist,'entry',{'producer':f'p{i}','in':str(start),'out':str(end)})
    tractor=ET.SubElement(root,'tractor',{'id':'mainTractor'})
    ET.SubElement(tractor,'track',{'producer':'main'})
    tree=ET.ElementTree(root)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    tree.write(output,encoding='utf-8',xml_declaration=True)
    return output

def stabilize(source, output, shakiness=5):
    if not shutil.which('ffmpeg'):raise RuntimeError('FFmpeg missing')
    source=Path(source).resolve();output=Path(output).resolve()
    if not source.is_file():raise FileNotFoundError(source)
    if source==output or output.exists():raise ValueError('Refuse overwrite')
    if not 1<=shakiness<=10:raise ValueError('Invalid shakiness')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vidstab-') as tmp:
        tr=Path(tmp)/'transforms.trf'
        exec_ok(['ffmpeg','-v','error','-y','-i',source,
                 '-vf',f'vidstabdetect=shakiness={shakiness}:result={tr}',
                 '-an','-f','null','-'])
        if not tr.is_file():raise RuntimeError('Vid.Stab detection failed')
        exec_ok(['ffmpeg','-v','error','-y','-i',source,
                 '-vf',f'vidstabtransform=input={tr}:smoothing=10:optzoom=1',
                 '-c:v','libx264','-crf','20','-c:a','aac','-movflags','+faststart',output])
    return output

def frei0r_filter(source, output, name='contrast0r', params=None):
    if name not in ('contrast0r','coloradj_RGB','saturat0r','brightness'):
        raise ValueError('Unapproved frei0r plugin')
    if not Path(source).is_file():raise FileNotFoundError(source)
    if Path(output).resolve()==Path(source).resolve() or Path(output).exists():
        raise ValueError('Refuse overwrite')
    vf=f'frei0r=filter_name={name}' + (f':filter_params={params}' if params else '')
    exec_ok(['ffmpeg','-v','error','-y','-i',source,
             '-vf',vf,'-map','0:v:0','-map','0:a:0?','-c:v','libx264','-crf','20','-c:a','aac',output])
    return Path(output)

def bake_ocio(config_path, src_space, dst_space, output, cube_size=17):
    import PyOpenColorIO as ocio
    if not 8<=cube_size<=64:raise ValueError('Invalid cube size')
    cfg=ocio.Config.CreateFromFile(str(config_path)) if config_path else ocio.Config.CreateRaw()
    if not src_space or not dst_space:raise ValueError('Color spaces required')
    baker=ocio.Baker()
    baker.setConfig(cfg);baker.setFormat('iridas_cube')
    baker.setInputSpace(src_space);baker.setTargetSpace(dst_space)
    baker.setCubeSize(cube_size)
    data=baker.bake()
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(data,encoding='utf-8')
    return output

def color_transform(source, output, cube):
    if not Path(cube).is_file():raise FileNotFoundError(cube)
    if Path(source).resolve()==Path(output).resolve() or Path(output).exists():raise ValueError('Unsafe output')
    exec_ok(['ffmpeg','-v','error','-y','-i',source,'-vf',
             f'lut3d=file={Path(cube).resolve()}', '-c:v','libx264','-crf','20',
             '-c:a','aac',output])
    return Path(output)

def auto_cut(source, output, binary='auto-editor'):
    """Audio-motion auto-cut using official Auto-Editor binary. Explicit opt-in."""
    executable=shutil.which(binary) if binary=='auto-editor' else binary
    if not executable or not Path(executable).is_file():raise RuntimeError('Auto-Editor executable missing')
    if Path(source).resolve()==Path(output).resolve() or Path(output).exists():
        raise ValueError('Unsafe output')
    exec_ok([executable,str(Path(source).resolve()),'--output',str(Path(output).resolve())],timeout=900)
    if not Path(output).is_file():raise RuntimeError('Auto-Editor produced no file')
    return Path(output)

def transcribe(source, output_stem, whisper_bin, ggml_model):
    """Sidecar SRT ONLY; never burns subtitles into the video."""
    if not Path(whisper_bin).is_file() or not Path(ggml_model).is_file():
        raise RuntimeError('Whisper.cpp executable and GGML model required')
    out=Path(output_stem).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='whisper-cpp-') as tmp:
        wav=Path(tmp)/'audio.wav'
        exec_ok(['ffmpeg','-v','error','-y','-i',source,'-ar',16000,
                 '-ac',1,'-c:a','pcm_s16le',wav])
        exec_ok([whisper_bin,'-m',ggml_model,'-f',wav,
                 '-osrt','-of',out],timeout=900)
    srt=Path(str(out)+'.srt')
    if not srt.is_file():raise RuntimeError('No SRT generated')
    return srt
