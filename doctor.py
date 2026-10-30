#!/usr/bin/env python3
"""Read-only diagnostic for rendering dependencies; never installs or spends credits."""
import importlib.util
import json
import platform
import shutil
import subprocess

def describe(binary):
    path=shutil.which(binary)
    if not path:return {"available":False}
    try:
        r=subprocess.run([path,"-version"] if binary in ("ffmpeg","ffprobe") else [path,"--version"],
                         stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
        return {"available":True,"path":path,"version":r.stdout.splitlines()[0][:200] if r.stdout else "unknown"}
    except (OSError,subprocess.TimeoutExpired) as exc:
        return {"available":True,"path":path,"warning":str(exc)}

def report():
    return {"platform":platform.platform(),"python":platform.python_version(),
      "tools":{name:describe(name) for name in
        ("ffmpeg","ffprobe","blender","rife-ncnn-vulkan","realesrgan-ncnn-vulkan")},
      "tkinter":importlib.util.find_spec("tkinter") is not None,
      "gpu_notes":"Vulkan compatibility and model weights require direct system verification."}

if __name__=="__main__":
    print(json.dumps(report(),ensure_ascii=False,indent=2))
