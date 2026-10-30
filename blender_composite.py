"""Optional real Blender Cycles CPU scene appended to an already verified MP4."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

def run(args,timeout=900):
    r=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=timeout)
    if r.returncode:raise RuntimeError((r.stderr or r.stdout)[-1300:])

def append_blender_scene(source,destination,blender_binary,width,height,fps=30):
    source=Path(source).resolve();destination=Path(destination).resolve()
    blender=Path(blender_binary).resolve()
    if not source.is_file() or not blender.is_file() or source==destination or destination.exists():
        raise ValueError("Invalid Blender input/output")
    if width<64 or height<64 or width%2 or height%2 or fps not in (24,25,30,60):
        raise ValueError("Invalid Blender output geometry")
    template=Path(__file__).parent/"blender_scene.py"
    if not template.is_file():raise FileNotFoundError(template)
    with tempfile.TemporaryDirectory(prefix="cinema-blender-") as td:
        folder=Path(td)
        script=folder/"render_scene.py"
        src=template.read_text(encoding="utf-8")
        src=src.replace('scene.render.engine="BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"',
                        'scene.render.engine="CYCLES"\nscene.cycles.device="CPU"\nscene.cycles.samples=8')
        src=src.replace('scene.render.resolution_x=720',f'scene.render.resolution_x={width}')
        src=src.replace('scene.render.resolution_y=1280',f'scene.render.resolution_y={height}')
        src=src.replace('scene.render.fps=30',f'scene.render.fps={fps}')
        src=src.replace('scene.frame_end=90','scene.frame_end=12')
        script.write_text(src,encoding="utf-8")
        scene=folder/"scene.mp4"
        run([blender,'-b','-noaudio','--python',script,'--',scene])
        if not scene.is_file():raise RuntimeError("Blender did not create a scene")
        graph=f'[0:v]fps={fps},format=yuv420p[v0];[1:v]fps={fps},format=yuv420p[v1];[v0][v1]concat=n=2:v=1:a=0[out]'
        run(['ffmpeg','-v','error','-y','-i',source,'-i',scene,'-filter_complex',graph,
             '-map','[out]','-map','0:a:0?','-c:v','libx264','-crf','20',
             '-preset','veryfast','-af','apad','-shortest','-c:a','aac',
             '-movflags','+faststart',destination])
        run(['ffmpeg','-v','error','-xerror','-i',destination,'-f','null','-'])
        return destination
