"""Integration coverage for chat-first rendering using synthesized frames."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from chat_reel import create_reel

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/FFprobe required")
class ChatReelTests(unittest.TestCase):
    def test_two_clips_produce_valid_video(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            clips=[]
            for i in range(2):
                clip=d/("source%d.mp4"%i)
                subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",
                    "testsrc2=size=160x288:rate=24","-t","2","-c:v","libx264",
                    "-pix_fmt","yuv420p",str(clip)],check=True)
                clips.append(clip)
            output=d/"render.mp4"
            create_reel(clips,output,length=3,shot=1.0,resolution=(160,288))
            probe=json.loads(subprocess.check_output(["ffprobe","-v","error",
                "-show_entries","format=duration:stream=width,height",
                "-of","json",str(output)],text=True))
            self.assertGreater(output.stat().st_size,1000)
            self.assertEqual(probe["streams"][0]["width"],160)
            self.assertAlmostEqual(float(probe["format"]["duration"]),3,delta=.2)
if __name__=="__main__": unittest.main()
