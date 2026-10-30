"""Actual HTTP workspace, safety, persistence and MP4 render integration."""
import io
import json
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from studio_web import Studio,Handler
from timeline_render import render_timeline

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg unavailable")
class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.studio=Studio(self.root/"workspace")
        self.addCleanup(self.studio.close)
        self.http=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        self.http.studio=self.studio
        self.addCleanup(self.http.server_close)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.thread.join,2)
        self.addCleanup(self.http.shutdown)
        self.base="http://127.0.0.1:%s"%self.http.server_address[1]
        self.input=self.root/"a.mp4"
        subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",
            "testsrc2=size=160x288:rate=24","-t","3",
            "-c:v","libx264","-pix_fmt","yuv420p",str(self.input)],check=True)

    def request(self,path,method="GET",payload=None,upload=False):
        if payload is not None and not upload:payload=json.dumps(payload).encode()
        headers={"Content-Type":"application/octet-stream" if upload else "application/json"}
        r=urllib.request.Request(self.base+path,data=payload,method=method,headers=headers)
        with urllib.request.urlopen(r,timeout=20) as f:
            data=f.read()
            return json.loads(data) if f.headers.get_content_type()=="application/json" else data

    def test_upload_edit_save_restart_and_render_http(self):
        p=self.request("/api/projects","POST",{"title":"تست تدوین"})
        u=self.request("/api/projects/"+p["id"]+"/upload?name=example.mp4","POST",
            self.input.read_bytes(),upload=True)
        self.assertEqual(u["type"],"video")
        current=self.request("/api/projects/"+p["id"])
        self.assertEqual(len(current["shots"]),1)
        s=current["shots"][0];s.update(start=.3,duration=1.3,speed=.75)
        current["settings"].update(width=160,height=288,fps=24,transition=0.0)
        saved=self.request("/api/projects/"+p["id"]+"/save","POST",{
            "shots":[s],"settings":current["settings"],"music":None,"title":"بازنویسی"})
        self.assertEqual(saved["shots"][0]["speed"],.75)
        self.assertEqual(Studio(self.root/"workspace",worker=False).read(p["id"])["title"],"بازنویسی")
        job=self.request("/api/projects/"+p["id"]+"/render","POST",{})
        for _ in range(120):
            state=self.request("/api/jobs/"+job["id"])
            if state["status"] in ("done","failed"):break
            time.sleep(.15)
        self.assertEqual(state["status"],"done",str(state))
        self.assertEqual(self.request("/api/projects/"+p["id"]+"/jobs")["jobs"][0]["id"],job["id"])
        video=self.request(state["video_url"])
        self.assertGreater(len(video),1000)
        export=self.root/"workspace"/"projects"/p["id"]/"exports"/(job["id"]+".mp4")
        meta=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_format",
            "-show_streams","-of","json",export]))
        self.assertEqual(next(s for s in meta["streams"] if s["codec_type"]=="video")["width"],160)
        self.assertTrue(any(s["codec_type"]=="audio" for s in meta["streams"]))
        self.assertTrue(export.with_suffix(".otio").exists())
        self.assertTrue(export.with_suffix(".mlt").exists())
        self.assertEqual(self.input.stat().st_size,len(self.input.read_bytes()))

    def test_cross_filesystem_safe_publication(self):
        import os
        output=self.root/"safe_publication.mp4"
        real_replace=os.replace
        calls=[]
        def check_replace(src,dst):
            if Path(dst)==output:
                calls.append((Path(src),Path(dst)))
                self.assertEqual(Path(src).parent,output.parent)
            return real_replace(src,dst)
        with patch('timeline_render.os.replace',side_effect=check_replace):
            result=render_timeline([{'file':str(self.input),'start':0,
                           'duration':1.1,'speed':1.0}],output,
                           resolution=(160,288),fps=24)
        self.assertTrue(result['qa']['decoded'])
        self.assertEqual(len(calls),1)
        self.assertFalse(list(self.root.glob('*.partial')))

    def test_multi_clip_save_order_and_empty_timeline(self):
        project=self.studio.create('Multiple videos')
        for i in range(3):
            self.studio.upload(project['id'],io.BytesIO(self.input.read_bytes()),
                self.input.stat().st_size,f'clip-{i}.mp4')
        doc=self.studio.read(project['id'])
        self.assertEqual(len(doc['shots']),3)
        shots=list(reversed(doc['shots']))
        saved=self.studio.save(project['id'],{'shots':shots})
        self.assertEqual([x['media'] for x in saved['shots']],
                         [x['media'] for x in shots])
        self.assertEqual(len(self.studio.read(project['id'])['shots']),3)
        empty=self.studio.save(project['id'],{'shots':[]})
        self.assertEqual(empty['shots'],[])

    def test_security_and_validation(self):
        p=self.studio.create()
        with self.assertRaises(ValueError):self.studio._project_dir("../traverse")
        with self.assertRaises(ValueError):self.studio.upload(p["id"],io.BytesIO(b"abc"),3,"../../bad.exe")
        item=self.studio.upload(p["id"],io.BytesIO(self.input.read_bytes()),self.input.stat().st_size,"../../safe.mp4")
        self.assertTrue(item["file"].endswith(".mp4"))
        project=self.studio.read(p["id"]);s=project["shots"][0];s["duration"]=300
        with self.assertRaises(ValueError):self.studio.save(p["id"],{"shots":[s]})
        with self.assertRaises(FileNotFoundError):self.studio.retry("a"*32)


    def test_overlay_second_video_track_is_rendered(self):
        project=self.studio.create("لایه تصویر")
        item=self.studio.upload(project["id"],io.BytesIO(self.input.read_bytes()),
                self.input.stat().st_size,"source.mp4")
        p=self.studio.read(project["id"])
        overlay={"media":item["id"],"at":.3,"duration":1.0,
                 "scale":.3,"position":"bottom-right"}
        p["settings"].update(width=160,height=288,fps=24)
        obj=self.studio.save(project["id"],{"settings":p["settings"],
                    "overlay":overlay})
        self.assertEqual(obj["overlay"]["position"],"bottom-right")
        with self.assertRaises(ValueError):
            self.studio.save(project["id"],{"overlay":dict(overlay,position="offscreen")})
        out=self.root/"with_overlay.mp4"
        render_timeline([{"file":str(self.input),"start":0,"duration":1.8,"speed":1}],
            out,resolution=(160,288),fps=24,
            overlay=dict(overlay,file=str(self.input)))
        self.assertGreater(out.stat().st_size,1000)
        subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(out),
                        "-f","null","-"],check=True)

    def test_speed_ramp_render_and_no_overwrite(self):
        out=self.root/"ramp.mp4"
        meta=render_timeline([{"file":str(self.input),"start":0,"duration":2.4,
             "speed":1.0,"ramp":True}],out,resolution=(160,288),fps=24)
        self.assertGreater(out.stat().st_size,1000)
        self.assertAlmostEqual(meta["qa"]["duration"],2.4,delta=.25)
        with self.assertRaises(FileExistsError):
            render_timeline([{"file":str(self.input),"duration":1,"speed":1}],out,
                            resolution=(160,288),fps=24)

    def test_multiple_http_render_requests_consume_request_body(self):
        project=self.studio.create()
        for _ in range(6):
            try:
                self.request("/api/projects/"+project["id"]+"/render","POST",{})
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code,400)
                self.assertIn("error",json.loads(e.read()))
            else:
                self.fail("Empty timeline must be rejected")

    def test_ui_range_and_cross_origin_rejected(self):
        result=self.request("/")
        self.assertIn(b"CINEMA EDIT STUDIO",result)
        self.assertIn(b"favicon.svg",result)
        self.assertIn(b"<svg",self.request("/favicon.svg"))
        self.assertIn(b"timeline",result.lower())
        origin=urllib.request.Request(self.base+"/api/projects",
                    data=b'{"title":"X"}',method="POST",
                    headers={"Content-Type":"application/json","Origin":"https://malicious.example"})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(origin)
        self.assertEqual(cm.exception.code,400)


    def test_missing_optional_video_backends_do_not_break_base(self):
        output=self.root/"fallback.mp4"
        with patch("timeline_render.export_otio",side_effect=ImportError("not installed")), \
             patch("studio_backends.stabilize",side_effect=RuntimeError("filter unavailable")):
            result=render_timeline([{"file":str(self.input),"start":0,"duration":1.0,"speed":1.0}],
                        output,resolution=(160,288),fps=24,stabilize=True)
        self.assertTrue(result["qa"]["decoded"])
        self.assertEqual(len(result["warnings"]),2)
        self.assertTrue(output.is_file())

    def test_ai_missing_models_fallback_and_recover(self):
        project=self.studio.create('Model fallback')
        self.studio.upload(project['id'],io.BytesIO(self.input.read_bytes()),
            self.input.stat().st_size,'source.mp4')
        p=self.studio.read(project['id'])
        p['settings'].update(width=160,height=288,fps=24,rife=True,realesrgan=True)
        self.studio.save(project['id'],{'settings':p['settings']})
        unavailable={'rife':False,'realesrgan':False,'blender':False,'ffmpeg':True}
        with patch.object(self.studio,'capabilities',return_value=unavailable):
            job=self.studio.enqueue(project['id'])
            for _ in range(130):
                state=self.studio.job(job['id'])
                if state['status'] in ('done','failed'):break
                time.sleep(.12)
        self.assertEqual(state['status'],'done',str(state))
        self.assertIn('rife',state['error'])
        self.assertIn('realesrgan',state['error'])
        output=self.studio._project_dir(project['id'])/'exports'/(job['id']+'.mp4')
        self.assertTrue(output.is_file())
        self.assertGreater(output.stat().st_size,1000)
        # Recovery on a host with missing AI still accepts valid base dimensions.
        self.studio._update(job['id'],status='running')
        with patch.object(self.studio,'capabilities',return_value=unavailable):
            self.studio._update(job['id'],status='queued')
            self.studio.pending.put(job['id'])
            for _ in range(60):
                recovered=self.studio.job(job['id'])
                if recovered['status']=='done':break
                time.sleep(.12)
        self.assertEqual(recovered['status'],'done',str(recovered))

    def test_optional_blender_failure_keeps_base_video(self):
        p=self.studio.create()
        self.studio.upload(p["id"],io.BytesIO(self.input.read_bytes()),
                           self.input.stat().st_size,"source.mp4")
        current=self.studio.read(p["id"])
        current["settings"].update(width=160,height=288,fps=24,blender=True)
        self.studio.save(p["id"],{"settings":current["settings"]})
        job=self.studio.enqueue(p["id"])
        for _ in range(120):
            state=self.studio.job(job["id"])
            if state["status"] in ("done","failed"):break
            time.sleep(.12)
        self.assertEqual(state["status"],"done",str(state))
        # In CI no Blender is installed; if a compatible binary is present,
        # full 3D rendering may run instead and no warning is expected.
        video=self.studio._project_dir(p["id"])/"exports"/(job["id"]+".mp4")
        self.assertGreater(video.stat().st_size,1000)
        if not self.studio.capabilities()["blender"]:
            self.assertIn("Blender",state["error"])

    def test_auto_mode_existing_scene_engine(self):
        p=self.studio.create()
        self.studio.upload(p["id"],io.BytesIO(self.input.read_bytes()),
                           self.input.stat().st_size,"scene.mp4")
        current=self.studio.read(p["id"])
        current["settings"].update(width=160,height=288,fps=24,auto=True)
        self.studio.save(p["id"],{"settings":current["settings"]})
        job=self.studio.enqueue(p["id"])
        for _ in range(150):
            state=self.studio.job(job["id"])
            if state["status"] in ("done","failed"):break
            time.sleep(.15)
        self.assertEqual(state["status"],"done",str(state))
        self.assertTrue((self.studio._project_dir(p["id"])/"exports"/(job["id"]+".mp4")).is_file())

    def test_recover_job_after_written_export(self):
        p=self.studio.create()
        self.studio.upload(p["id"],io.BytesIO(self.input.read_bytes()),
                           self.input.stat().st_size,"scene.mp4")
        frozen=Studio(self.root/"workspace",worker=False)
        self.addCleanup(frozen.close)
        job=frozen.enqueue(p["id"])
        with self.studio.lock:
            self.studio.db.execute("UPDATE jobs SET status='running' WHERE id=?",(job["id"],))
            self.studio.db.commit()
        directory=self.studio._project_dir(p["id"])/"exports"
        output=directory/(job["id"]+".mp4")
        render_timeline([{"file":str(next((self.studio._project_dir(p["id"])/"media").iterdir())),
                          "start":0,"duration":1,"speed":1}],output,
                         resolution=(720,1280),fps=30)
        restarted=Studio(self.root/"workspace",worker=True)
        self.addCleanup(restarted.close)
        for _ in range(60):
            state=restarted.job(job["id"])
            if state["status"] in ("done","failed"):break
            time.sleep(.1)
        self.assertEqual(state["status"],"done",str(state))

    def test_requeue_interrupted_job(self):
        p=self.studio.create()
        self.studio.upload(p["id"],io.BytesIO(self.input.read_bytes()),self.input.stat().st_size,"clip.mp4")
        frozen=Studio(self.root/"workspace",worker=False)
        self.addCleanup(frozen.close)
        j=frozen.enqueue(p["id"])
        frozen._update(j["id"],status="running")
        restarted=Studio(self.root/"workspace",worker=False)
        self.addCleanup(restarted.close)
        self.assertEqual(restarted.job(j["id"])["status"],"queued")

if __name__=="__main__":unittest.main()
