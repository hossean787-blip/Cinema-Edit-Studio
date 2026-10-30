"""Real synthetic media smoke coverage for cinematic phase 2."""
import json,shutil,subprocess,tempfile,unittest
from pathlib import Path
from phase2 import render

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg unavailable")
class Phase2Tests(unittest.TestCase):
    def test_ramp_transition_and_full_decode(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);clips=[]
            for i in range(2):
                p=root/("clip%d.mp4"%i)
                subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi",
                    "-i","testsrc2=size=160x288:rate=30","-t","2.2",
                    "-c:v","libx264",str(p)],check=True)
                clips.append(p)
            out=root/"output.mp4"
            result=render(clips,out,width=160,height=288)
            self.assertGreater(result["seconds"],2)
            self.assertEqual(result["clips"],2)
            subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(out),"-f","null","-"],check=True)
    def test_invalid_geometry(self):
        with self.assertRaises(ValueError):render(["fake.mp4"],"out.mp4",width=161)
if __name__=="__main__":unittest.main()
