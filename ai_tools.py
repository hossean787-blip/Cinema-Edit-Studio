"""Safe optional adapters for externally installed AI tools. Never installs software."""
import argparse
import shutil
import subprocess
from pathlib import Path

def run_adapter(command, source, destination, model=None):
    tools={
        "rife": "rife-ncnn-vulkan",
        "realesrgan": "realesrgan-ncnn-vulkan",
    }
    if command not in tools: raise ValueError("Unknown adapter")
    binary=shutil.which(tools[command])
    if not binary: raise RuntimeError(f"{tools[command]} is not installed. Check GPU and license compatibility.")
    source=Path(source).resolve(); destination=Path(destination).resolve()
    if not source.is_file() or source==destination: raise ValueError("Invalid input or output")
    if model and not Path(model).exists(): raise FileNotFoundError(model)
    if destination.exists(): raise FileExistsError(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    args=[binary,"-i",str(source),"-o",str(destination)]
    if model: args+=["-m",str(Path(model).resolve())]
    subprocess.run(args,check=True)
    return destination

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("adapter",choices=["rife","realesrgan"])
    p.add_argument("source");p.add_argument("destination")
    p.add_argument("--model")
    a=p.parse_args()
    print(run_adapter(a.adapter,a.source,a.destination,a.model))
