"""End-to-end multi-media acceptance on the existing editor, with real FFmpeg output."""
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from studio_web import Studio


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/FFprobe required")
class ThreeVideosAndMusic(unittest.TestCase):
    def test_three_videos_soundtrack_recovery_and_render(self):
        with tempfile.TemporaryDirectory(prefix="cinema-accept-") as temp:
            root=Path(temp)
            sources=[]
            for i, color in enumerate(("red","green","blue")):
                src=root/("video_%d.mp4"%i)
                subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",
                    "color=c="+color+":s=160x288:r=24","-t","0.85",
                    "-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",str(src)],
                    check=True,timeout=30)
                sources.append(src)
            music=root/"music.wav"
            subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",
                "sine=frequency=440:sample_rate=16000","-t","3",
                "-c:a","pcm_s16le",str(music)],check=True,timeout=30)
            sha={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[music]}
            studio=Studio(root/"workspace")
            try:
                project=studio.create("multi-asset acceptance")
                for p in sources+[music]:
                    with p.open("rb") as reader:
                        studio.upload(project["id"],reader,p.stat().st_size,p.name)
                project=studio.read(project["id"])
                self.assertEqual(len(project["media"]),4)
                self.assertEqual(len(project["shots"]),3)
                self.assertIsNotNone(project["music"])
                shots=list(reversed(project["shots"]))
                for shot in shots:
                    shot["duration"]=0.65
                    shot["speed"]=1.0
                settings=dict(project["settings"],width=160,height=288,fps=24,
                              optical_flow=False,transition=0,style="clean")
                saved=studio.save(project["id"],{"shots":shots,"settings":settings,
                                                  "music":project["music"]})
                self.assertEqual(len(saved["shots"]),3)
                self.assertEqual(saved["shots"][0]["media"],shots[0]["media"])
                job=studio.enqueue(project["id"])
                for _ in range(300):
                    latest=studio.job(job["id"])
                    if latest["status"] in ("done","failed"):break
                    time.sleep(0.2)
                self.assertEqual(latest["status"],"done",latest["error"])
                self.assertEqual(latest["progress"],100)
                output=studio._project_dir(project["id"])/"exports"/(job["id"]+".mp4")
                self.assertGreater(output.stat().st_size,1000)
                details=json.loads(subprocess.check_output(["ffprobe","-v","error",
                    "-show_entries","stream=codec_type,codec_name","-of","json",str(output)]))
                types={s["codec_type"] for s in details["streams"]}
                self.assertEqual(types,{"video","audio"})
                subprocess.run(["ffmpeg","-v","error","-i",str(output),"-f","null","-"],
                               check=True,timeout=30)
                self.assertEqual(sha,{str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in sources+[music]})
            finally:
                studio.close()
            again=Studio(root/"workspace",worker=False)
            try:
                recovered=again.read(project["id"])
                self.assertEqual(len(recovered["shots"]),3)
                self.assertEqual(recovered["music"],project["music"])
                self.assertEqual(again.job(job["id"])["status"],"done")
            finally:
                again.close()


if __name__=="__main__":
    unittest.main()
