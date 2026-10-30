"""Simple offline onset-based beat markers; accepts any audio FFmpeg can decode."""
import argparse
import json
import math
import shutil
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

def detect_beats(audio, min_interval=0.28, sensitivity=1.4):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg required")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "mono.wav"
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(audio),"-ac","1",
                        "-ar","8000","-c:a","pcm_s16le",str(wav)],check=True)
        with wave.open(str(wav),"rb") as f:
            raw=f.readframes(f.getnframes())
            rate=f.getframerate()
        samples=struct.unpack("<%dh" % (len(raw)//2),raw)
        hop=400
        rms=[math.sqrt(sum(v*v for v in samples[i:i+hop])/max(1,len(samples[i:i+hop])))
             for i in range(0,len(samples),hop)]
        if len(rms)<5: return []
        novelty=[max(0,rms[i]-rms[i-1]) for i in range(1,len(rms))]
        sorted_n=sorted(novelty)
        threshold=sorted_n[int(.75*(len(sorted_n)-1))]*sensitivity
        beats=[]
        last=-min_interval
        for i in range(1,len(novelty)-1):
            timestamp=(i+1)*hop/rate
            if novelty[i]>threshold and novelty[i]>=novelty[i-1] and novelty[i]>=novelty[i+1] and timestamp-last>=min_interval:
                beats.append(round(timestamp,3)); last=timestamp
        return beats

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("-o","--output",default="beats.json")
    a=p.parse_args()
    Path(a.output).write_text(json.dumps({"beats":detect_beats(a.audio)},indent=2))
    print(a.output)
