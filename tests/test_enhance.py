import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from enhance import enhance

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg missing")
class EnhancementTests(unittest.TestCase):
    def test_interpolated_slow_motion(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/"src.mp4"
            dst=Path(d)/"dst.mp4"
            subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",
                            "testsrc2=size=180x320:rate=24","-t","1",
                            "-c:v","libx264",str(src)],check=True)
            enhance(src,dst,slow=.5,width=180,height=320,fps=24,interpolate=True)
            self.assertGreater(dst.stat().st_size,1000)

    def test_refuse_overwrite_source(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/"src.mp4"
            src.touch()
            with self.assertRaises(ValueError):
                enhance(src,src,width=180,height=320)

if __name__=="__main__":
    unittest.main()
