import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from effects import apply
from quality_check import inspect

class ExportTests(unittest.TestCase):
    def test_reject_bad_preset(self):
        with self.assertRaises(ValueError):
            apply("missing.mp4","out.mp4",preset="random")
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg unavailable")
    def test_effects_and_quality(self):
        with tempfile.TemporaryDirectory() as temp:
            src=Path(temp)/"sample.mp4"
            dst=Path(temp)/"cinematic.mp4"
            subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",
                            "testsrc2=size=180x320:rate=20","-t","0.5",
                            "-c:v","libx264",str(src)],check=True)
            apply(src,dst,preset="punch",width=180,height=320)
            info=inspect(dst,min_width=180,min_height=320)
            self.assertEqual((info["width"],info["height"]),(180,320))
            self.assertFalse(info["has_audio"])
if __name__=="__main__": unittest.main()
