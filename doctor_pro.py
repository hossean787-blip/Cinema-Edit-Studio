"""Read-only inventory of the 12 professional editing backends."""
import importlib.util
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

BINARIES={
 'FFmpeg':'ffmpeg','FFprobe':'ffprobe','RIFE':'rife-ncnn-vulkan',
 'Real-ESRGAN':'realesrgan-ncnn-vulkan','Blender':'blender',
 'MLT':'melt','Auto-Editor':'auto-editor','Whisper.cpp':'whisper-cli'
}
MODULES={'PySceneDetect':'scenedetect','OpenColorIO':'PyOpenColorIO',
         'OpenTimelineIO':'opentimelineio'}

def scan():
    report={'platform':platform.platform(),'backend_status':{}}
    for name,binary in BINARIES.items():
        alias={'RIFE':'RIFE_BIN','Real-ESRGAN':'REALESRGAN_BIN','Blender':'BLENDER_BIN','MLT':'MELT_BIN','Auto-Editor':'AUTO_EDITOR_BIN','Whisper.cpp':'WHISPER_CPP_BIN'}.get(name)
        override=os.getenv(alias,'') if alias else ''
        path=override if override and Path(override).is_file() else shutil.which(binary)
        report['backend_status'][name]={'available':bool(path),'path':path}
    for name,module in MODULES.items():
        try:available=importlib.util.find_spec(module) is not None
        except (ImportError,ValueError):available=False
        report['backend_status'][name]={'available':available}
    ffmpeg=report['backend_status']['FFmpeg']['path']
    filters=''
    if ffmpeg:
        p=subprocess.run([ffmpeg,'-hide_banner','-filters'],capture_output=True,text=True,timeout=15)
        filters=p.stdout
    report['backend_status']['Vid.Stab']={'available':'vidstabdetect' in filters and 'vidstabtransform' in filters}
    report['backend_status']['frei0r']={'ffmpeg_filter':bool('frei0r ' in filters),
                                         'plugin_folder':any(Path(p).is_dir() for p in
                                             ('/usr/lib/frei0r-1','/usr/lib/x86_64-linux-gnu/frei0r-1'))}
    return report

if __name__=='__main__':
    print(json.dumps(scan(),indent=2))
