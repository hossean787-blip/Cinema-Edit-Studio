import json
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from ai_tools import run_adapter
from beat_sync import detect_beats

class FeatureTests(unittest.TestCase):
    def test_adapter_rejects_unknown(self):
        with self.assertRaises(ValueError):
            run_adapter("unknown","a","b")

    def test_detect_beats_from_click_track(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"click.wav"
            n=8000*3
            samples=[0]*n
            for t in (0.5,1.0,1.5,2.0,2.5):
                for j in range(100):
                    samples[int(t*8000)+j]=int(15000*(1-j/100))
            with wave.open(str(p),"wb") as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000)
                w.writeframes(struct.pack("<%dh"%n,*samples))
            beats=detect_beats(p,sensitivity=1.0)
            self.assertGreaterEqual(len(beats),3)

if __name__=="__main__": unittest.main()
