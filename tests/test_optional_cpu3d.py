"""Optional CPU-3D geometry integration smoke test, skipped without dependencies."""
import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HAS_CPU_3D=bool(importlib.util.find_spec('numpy') and importlib.util.find_spec('cv2')
                and shutil.which('ffmpeg') and shutil.which('ffprobe'))

@unittest.skipUnless(HAS_CPU_3D, 'Optional numpy and OpenCV CPU renderer not present')
class Geometry3DTest(unittest.TestCase):
    def test_rotating_wheel_renders_and_decodes(self):
        from tire_3d_cpu import create
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'wheel.mp4'
            create(path,seconds=0.3,width=80,height=144,fps=12)
            self.assertGreater(path.stat().st_size,1000)
            subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(path),
                            '-f','null','-'],check=True)

if __name__=='__main__':
    unittest.main()
