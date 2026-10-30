"""Unit and integration smoke tests. Run: python -m unittest discover -s tests -v"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from studio import assemble


class ReelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project.json"
        self.output = self.root / "result.mp4"

    def save(self, shots, **extra):
        config = {"resolution": [320, 576], "fps": 24, "shots": shots, **extra}
        self.project.write_text(json.dumps(config), encoding="utf-8")

    def test_empty_shots_rejected(self):
        self.save([])
        with self.assertRaisesRegex(ValueError, "At least one"):
            assemble(self.project, self.output)

    def test_invalid_resolution_rejected(self):
        self.save([{"file": "a.mp4", "duration": 1}], resolution=[321, 577])
        with self.assertRaisesRegex(ValueError, "resolution"):
            assemble(self.project, self.output)

    def test_missing_clip_rejected(self):
        self.save([{"file": "missing.mp4", "duration": 1}])
        with self.assertRaises(FileNotFoundError):
            assemble(self.project, self.output)

    def test_speed_zero_rejected(self):
        clip = self.root / "dummy.mp4"
        clip.touch()
        self.save([{"file": "dummy.mp4", "duration": 1, "speed": 0}])
        with self.assertRaisesRegex(ValueError, "timing"):
            assemble(self.project, self.output)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools unavailable")
    def test_real_render_without_text(self):
        source = self.root / "synthetic.mp4"
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-f", "lavfi",
            "-i", "testsrc2=size=320x576:rate=24", "-t", "2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source)
        ], check=True)
        self.save([
            {"file": "synthetic.mp4", "start": 0, "duration": 1, "speed": 1},
            {"file": "synthetic.mp4", "start": 1, "duration": 1, "speed": 0.5},
        ])
        assemble(self.project, self.output)
        probe = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=width,height", "-of", "json", str(self.output)
        ], text=True)
        info = json.loads(probe)
        self.assertTrue(self.output.stat().st_size > 1000)
        self.assertEqual(info["streams"][0]["width"], 320)
        self.assertEqual(info["streams"][0]["height"], 576)
        self.assertAlmostEqual(float(info["format"]["duration"]), 3, delta=0.3)


if __name__ == "__main__":
    unittest.main()
