#!/usr/bin/env python3
"""Local-only professional browser editor with durable queue and FFmpeg exports.

No external hosting, cloud service, subprocess command interpolation or third-party Python dependency.
"""
import argparse
import hashlib
import json
import math
import os
import queue
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from timeline_render import render_timeline
from cinema_integrated import verify as verify_video

ROOT_UI=Path(__file__).parent/"web"/"index.html"
VIDEO_SUFFIXES={".mp4",".mov",".mkv",".webm",".avi"}
AUDIO_SUFFIXES={".mp3",".m4a",".wav",".ogg",".flac"}
MAX_UPLOAD=1024*1024*1024
MAX_JSON=256*1024

def media_metadata(path):
    p=subprocess.run(["ffprobe","-v","error","-show_entries",
                      "format=duration:stream=width,height,codec_type","-of","json",str(path)],
                     capture_output=True,text=True,timeout=30)
    if p.returncode:raise ValueError("فایل چندرسانه‌ای قابل خواندن نیست")
    data=json.loads(p.stdout)
    duration=float(data.get("format",{}).get("duration",0))
    if duration<=0:raise ValueError("مدت ویدئو/صدا نامعتبر است")
    video=next((v for v in data.get("streams",[]) if v.get("codec_type")=="video"),None)
    return {"duration":round(duration,3),
            "width":video.get("width") if video else None,
            "height":video.get("height") if video else None,
            "type":"video" if video else "audio"}

class Studio:
    def __init__(self,root,worker=True):
        self.root=Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.projects=self.root/"projects"
        self.projects.mkdir(exist_ok=True)
        self.db=sqlite3.connect(self.root/"queue.sqlite3",check_same_thread=False)
        self.lock=threading.RLock()
        with self.lock:
            self.db.execute("""CREATE TABLE IF NOT EXISTS jobs(
                 id TEXT PRIMARY KEY,project TEXT NOT NULL,status TEXT NOT NULL,
                 progress INTEGER NOT NULL, detail TEXT NOT NULL,
                 params TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,
                 error TEXT NOT NULL DEFAULT '',created REAL NOT NULL,updated REAL NOT NULL)""")
            self.db.execute("UPDATE jobs SET status='queued',detail='بازیابی بعد از قطع اجرا' WHERE status='running'")
            self.db.commit()
        self.pending=queue.Queue()
        for (id,) in self.db.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created"):
            self.pending.put(id)
        self.worker_enabled=worker
        self.worker_thread=None
        self.closed=False
        if worker:
            self.worker_thread=threading.Thread(target=self._work,daemon=True,name="cinema-render-worker")
            self.worker_thread.start()

    def close(self):
        if self.closed:return
        self.closed=True
        if self.worker_thread is not None:
            self.pending.put(None)
            self.worker_thread.join(timeout=5)
            # Never close the shared connection while an in-flight render needs it.
            if self.worker_thread.is_alive():return
        with self.lock:self.db.close()


    def _project_dir(self,id):
        if not isinstance(id,str) or len(id)!=32 or any(c not in '0123456789abcdef' for c in id):
            raise ValueError("شناسه پروژه نامعتبر است")
        p=(self.projects/id).resolve()
        if p.parent!=self.projects.resolve():raise ValueError("مسیر نامعتبر")
        return p

    def create(self,title="پروژه جدید"):
        id=uuid.uuid4().hex
        p=self._project_dir(id)
        p.mkdir()
        (p/"media").mkdir()
        (p/"exports").mkdir()
        obj={"id":id,"title":str(title)[:80] or "پروژه جدید",
             "created":time.time(),"updated":time.time(),"media":[],"shots":[],
             "music":None,"overlay":None,"settings":{"width":720,"height":1280,"fps":30,
             "style":"sport","transition":0.12,"optical_flow":True,
             "stabilize":False,"rife":False,"realesrgan":False,"blender":False,"auto":False}}
        self._atomic_write(p/"project.json",obj)
        return obj

    def _atomic_write(self,path,obj):
        tmp=path.with_suffix(path.suffix+".tmp")
        tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(tmp,path)

    def read(self,id):
        path=self._project_dir(id)/"project.json"
        if not path.is_file():raise FileNotFoundError("پروژه پیدا نشد")
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self):
        out=[]
        for p in self.projects.iterdir():
            f=p/"project.json"
            if f.is_file():
                try:
                    x=json.loads(f.read_text())
                    out.append({"id":x["id"],"title":x["title"],"updated":x["updated"],
                                "clips":len(x["shots"])})
                except (ValueError,KeyError,OSError):pass
        return sorted(out,key=lambda x:x["updated"],reverse=True)

    def upload(self,id,stream,length,name):
        p=self._project_dir(id)
        obj=self.read(id)
        if length<=0 or length>MAX_UPLOAD:raise ValueError("حجم فایل خارج از محدوده است")
        title=Path(str(name).replace("\\","/")).name[:120]
        suffix=Path(title).suffix.lower()
        if suffix not in VIDEO_SUFFIXES|AUDIO_SUFFIXES:raise ValueError("پسوند فایل مجاز نیست")
        id_media=uuid.uuid4().hex
        out=p/"media"/(id_media+suffix)
        written=0
        try:
            with out.open("xb") as f:
                while written<length:
                    block=stream.read(min(1024*1024,length-written))
                    if not block:raise ValueError("آپلود ناقص")
                    f.write(block);written+=len(block)
            metadata=media_metadata(out)
            if metadata["type"]=="audio" and suffix in VIDEO_SUFFIXES:
                raise ValueError("ویدئو بدون جریان تصویر است")
            item={"id":id_media,"name":title,"file":out.name,**metadata}
            with self.lock:
                obj=self.read(id)
                obj["media"].append(item)
                if metadata["type"]=="video":
                    obj["shots"].append({"media":id_media,"ramp":False,"start":0,
                        "duration":round(min(metadata["duration"],2.5),2),"speed":1.0})
                elif not obj["music"]:obj["music"]=id_media
                obj["updated"]=time.time()
                self._atomic_write(p/"project.json",obj)
            return item
        except Exception:
            out.unlink(missing_ok=True)
            raise

    def save(self,id,data):
        with self.lock:
            obj=self.read(id)
            allowed={m["id"]:m for m in obj["media"]}
            shots=data.get("shots",obj["shots"])
            if not isinstance(shots,list) or len(shots)>80:raise ValueError("تعداد نماها نامعتبر است")
            cleaned=[]
            for shot in shots:
                m=allowed.get(shot.get("media"))
                if not m or m["type"]!="video":raise ValueError("شناسه ویدئو معتبر نیست")
                start=float(shot.get("start",0));dur=float(shot.get("duration",2));speed=float(shot.get("speed",1))
                if not all(map(math.isfinite,(start,dur,speed))):
                    raise ValueError("عدد نامعتبر")
                if start<0 or dur<=0 or speed<.2 or speed>4 or start+dur>m["duration"]+.08:
                    raise ValueError("محدوده یا سرعت نما نامعتبر است")
                if type(shot.get("ramp",False)) is not bool:raise ValueError("Speed Ramp نامعتبر")
            cleaned.append({"media":m["id"],"start":start,"duration":dur,
                            "speed":speed,"ramp":shot.get("ramp",False)})
            settings=obj["settings"].copy()
            settings.setdefault("auto",False)
            new=data.get("settings",{})
            for key in settings:
                if key in new:settings[key]=new[key]
            if settings["style"] not in ("sport","cinematic","clean"):raise ValueError("سبک نامعتبر")
            if (settings["width"],settings["height"]) not in ((720,1280),(1080,1920),(1920,1080),(3840,2160),(160,288)):
                raise ValueError("ابعاد خروجی نامعتبر")
            if settings["fps"] not in (24,25,30,60):raise ValueError("نرخ فریم نامعتبر")
            if not 0<=float(settings["transition"])<=.5:raise ValueError("ترنزیشن نامعتبر")
            for k in ("rife","realesrgan","blender","stabilize","optical_flow","auto"):
                if type(settings[k]) is not bool:raise ValueError("گزینه نامعتبر")
            music=data.get("music",obj["music"])
            if music is not None and (music not in allowed or allowed[music]["type"]!="audio"):
                raise ValueError("شناسه موسیقی نامعتبر")
            overlay=data.get("overlay",obj.get("overlay"))
            if overlay is not None:
                if not isinstance(overlay,dict):raise ValueError("لایه تصویر نامعتبر است")
                mid=overlay.get("media")
                if mid not in allowed or allowed[mid]["type"]!="video":raise ValueError("شناسه لایه دوم نامعتبر است")
                at=float(overlay.get("at",0));length=float(overlay.get("duration",2))
                scale=float(overlay.get("scale",.3));position=overlay.get("position","top-left")
                if not all(map(math.isfinite,(at,length,scale))) or at<0 or length<=0 or length>120 or not .15<=scale<=.60 or position not in ("top-left","top-right","bottom-left","bottom-right"):
                    raise ValueError("موقعیت یا ابعاد لایه دوم نامعتبر است")
                overlay={"media":mid,"at":at,"duration":length,"scale":scale,"position":position}
            obj.update(shots=cleaned,settings=settings,music=music,overlay=overlay,
                       title=str(data.get("title",obj["title"]))[:80],updated=time.time())
            self._atomic_write(self._project_dir(id)/"project.json",obj)
        return obj

    def capabilities(self):
        def executable(name,env):
            value=os.environ.get(env)
            return bool(shutil.which(name) or (value and Path(value).is_file()))
        return {"ffmpeg":bool(shutil.which("ffmpeg")),
          "rife":executable("rife-ncnn-vulkan","RIFE_BIN"),
          "realesrgan":executable("realesrgan-ncnn-vulkan","REALESRGAN_BIN"),
          "blender":executable("blender","BLENDER_BIN"),
          "note":"پشتیبانی AI به وجود باینری، وزن مدل و آزمون سخت‌افزار وابسته است."}

    def enqueue(self,id):
        obj=self.read(id)
        if not obj["shots"]:raise ValueError("تایم‌لاین خالی است")
        with self.lock:
            active=self.db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running') AND project=?",(id,)).fetchone()[0]
            if active:raise ValueError("برای این پروژه رندر در صف است")
            if self.db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]>=12:
                raise ValueError("صف پر است")
            jid=uuid.uuid4().hex;now=time.time()
            self.db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?)",
                (jid,id,"queued",0,"در صف",json.dumps(obj),0,"",now,now))
            self.db.commit()
            self.pending.put(jid)
        return self.job(jid)

    def job(self,id):
        if not isinstance(id,str) or len(id)!=32:raise ValueError("شناسه رندر نامعتبر")
        with self.lock:
            r=self.db.execute("SELECT id,project,status,progress,detail,attempts,error,created,updated FROM jobs WHERE id=?",(id,)).fetchone()
        if not r:raise FileNotFoundError("رندر پیدا نشد")
        x=dict(zip(("id","project","status","progress","detail","attempts","error","created","updated"),r))
        if x["status"]=="done":x["video_url"]=f"/api/projects/{x['project']}/exports/{id}.mp4"
        return x

    def project_jobs(self,id):
        self.read(id)
        with self.lock:
            ids=self.db.execute(
                "SELECT id FROM jobs WHERE project=? ORDER BY created DESC LIMIT 12",(id,)).fetchall()
        return [self.job(x[0]) for x in ids]

    def retry(self,id):
        with self.lock:
            j=self.job(id)
            if j["status"] not in ("failed",):raise ValueError("فقط رندر ناموفق قابل تکرار است")
            if j["attempts"]>=2:raise ValueError("سقف تلاش مجدد پر شده")
            self.db.execute("UPDATE jobs SET status='queued',progress=0,detail='تلاش مجدد',error='' WHERE id=?",(id,))
            self.db.commit();self.pending.put(id)
        return self.job(id)

    def _update(self,jid,**fields):
        with self.lock:
            cols=list(fields)
            self.db.execute("UPDATE jobs SET "+",".join(k+"=?" for k in cols)+",updated=? WHERE id=?",
                            [fields[k] for k in cols]+[time.time(),jid])
            self.db.commit()

    def _work(self):
        while True:
            jid=self.pending.get()
            if jid is None:
                self.pending.task_done()
                break
            with self.lock:
                row=self.db.execute("SELECT project,params,attempts,status FROM jobs WHERE id=?",(jid,)).fetchone()
                if not row or row[3]!="queued":continue
                pid,obj_json,attempt,_=row
                self._update(jid,status="running",attempts=attempt+1,progress=1,detail="شروع رندر")
            try:
                obj=json.loads(obj_json)
                directory=self._project_dir(pid)
                files={m["id"]:directory/"media"/m["file"] for m in obj["media"]}
                shots=[{"file":str(files[s["media"]]),"start":s["start"],"duration":s["duration"],"speed":s["speed"],
                        "ramp":s.get("ramp",False)} for s in obj["shots"]]
                media_dir=(directory/"media").resolve()
                for file in files.values():
                    if file.resolve().parent != media_dir:raise ValueError("Unsafe media path in project")
                settings=obj["settings"];music=files[obj["music"]] if obj["music"] else None
                layer=obj.get("overlay")
                if layer:
                    layer=dict(layer,file=str(files[layer["media"]]))
                if settings["rife"] or settings["realesrgan"]:
                    caps=self.capabilities()
                    if (settings["rife"] and not caps["rife"]) or (settings["realesrgan"] and not caps["realesrgan"]):
                        raise RuntimeError("موتور AI انتخاب‌شده در محیط رندر نصب و تأیید نشده است")
                output=directory/"exports"/(jid+".mp4")
                def progress(n,msg):self._update(jid,progress=n,detail=msg)
                if output.is_file():
                    # A complete export may predate a power loss while job status was pending.
                    verify_video(output,
                        settings["width"]*(2 if settings["realesrgan"] else 1),
                        settings["height"]*(2 if settings["realesrgan"] else 1))
                    self._update(jid,status="done",progress=100,detail="بازیابی خروجی قبلی تأیید شد")
                    continue
                if settings.get("auto"):
                    from studio_pro import options_render
                    inputs=list(dict.fromkeys(s["file"] for s in shots))
                    result=options_render(inputs,output,music=music,
                        seconds=max(2,min(60,round(sum(s["duration"]/s["speed"] for s in shots)))),
                        width=settings["width"],height=settings["height"],fps=settings["fps"],
                        style=settings["style"],stabilize_input=settings["stabilize"],
                        detect_scenes=True,interpolate=settings["optical_flow"])
                else:
                    result=render_timeline(shots,output,resolution=(settings["width"],settings["height"]),
                        fps=settings["fps"],style=settings["style"],transition=settings["transition"],
                        music=music,optical_flow=settings["optical_flow"],
                        stabilize=settings["stabilize"],overlay=layer,on_progress=progress)
                if settings.get("auto") and layer:
                    from timeline_render import apply_overlay_video
                    layered=directory/"exports"/(jid+"-layered.mp4")
                    apply_overlay_video(output,layer["file"],layered,settings["width"],settings["height"],
                                        at=layer["at"],duration=layer["duration"],
                                        scale=layer["scale"],position=layer["position"])
                    os.replace(layered,output)
                ai_warnings=[]
                if settings.get("blender"):
                    try:
                        from blender_composite import append_blender_scene
                        binary=os.environ.get("BLENDER_BIN") or shutil.which("blender")
                        if not binary:raise RuntimeError("Blender executable missing")
                        enhanced=directory/"exports"/(jid+"-blender.mp4")
                        self._update(jid,progress=92,detail="رندر صحنه واقعی Blender")
                        append_blender_scene(output,enhanced,binary,settings["width"],
                                             settings["height"],settings["fps"])
                        os.replace(enhanced,output)
                    except Exception as blender_error:
                        (directory/"exports"/(jid+"-blender.mp4")).unlink(missing_ok=True)
                        ai_warnings.append("Blender: "+str(blender_error)[:200])
                if settings["rife"] or settings["realesrgan"]:
                    from neural_video import process
                    for backend in ("rife","realesrgan"):
                        if not settings[backend]:continue
                        binary=os.environ.get("RIFE_BIN" if backend=="rife" else "REALESRGAN_BIN") or shutil.which(
                            "rife-ncnn-vulkan" if backend=="rife" else "realesrgan-ncnn-vulkan")
                        tmp=directory/"exports"/(jid+"-"+backend+".mp4")
                        self._update(jid,detail="اجرای مدل واقعی "+backend,progress=94)
                        try:
                            process(output,tmp,backend,executable=binary,max_frames=900,timeout=3600)
                            os.replace(tmp,output)
                        except Exception as model_error:
                            tmp.unlink(missing_ok=True)
                            ai_warnings.append(backend+": "+str(model_error)[:200])
                self._update(jid,status="done",progress=100,
                    detail="رندر آماده شد" + ("؛ بعضی پردازش‌های اختیاری انجام نشدند" if ai_warnings else " و تأیید شد"),
                    error="؛ ".join(ai_warnings))
            except Exception as e:
                self._update(jid,status="failed",detail="خطای رندر",error=str(e)[:800])
            finally:self.pending.task_done()

class Handler(BaseHTTPRequestHandler):
    server_version="CinemaEdit/0.4"
    def log_message(self,format,*args):pass

    def send(self,obj,code=200):
        payload=json.dumps(obj,ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(payload)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Cross-Origin-Resource-Policy","same-origin")
        self.end_headers();self.wfile.write(payload)
    def json_body(self):
        n=int(self.headers.get("Content-Length","0"))
        if n<=0 or n>MAX_JSON:raise ValueError("اندازه درخواست نامعتبر است")
        return json.loads(self.rfile.read(n))
    def do_GET(self):
        try:self._get()
        except (ValueError,FileNotFoundError) as e:self.send({"error":str(e)},400)
        except Exception:self.send({"error":"خطای سرور"},500)

    def _get(self):
        if self.headers.get("Sec-Fetch-Site","")=="cross-site":
            raise ValueError("دسترسی بین‌سایتی مجاز نیست")
        path=urlsplit(self.path).path;parts=path.strip("/").split("/")
        studio=self.server.studio
        if path in ("/","/index.html"):
            data=ROOT_UI.read_bytes();self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(data)))
            self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; media-src 'self'; connect-src 'self'")
            self.end_headers();self.wfile.write(data);return
        if path=="/api/projects":return self.send({"projects":studio.list()})
        if path=="/api/capabilities":return self.send(studio.capabilities())
        if len(parts)==3 and parts[:2]==["api","projects"]:
            return self.send(studio.read(parts[2]))
        if len(parts)==4 and parts[:2]==["api","projects"] and parts[3]=="jobs":
            return self.send({"jobs":studio.project_jobs(parts[2])})
        if len(parts)==3 and parts[:2]==["api","jobs"]:return self.send(studio.job(parts[2]))
        if len(parts)==5 and parts[:2]==["api","projects"] and parts[3]=="media":
            obj=studio.read(parts[2])
            match=next((x for x in obj["media"] if x["id"]==parts[4]),None)
            if not match:raise FileNotFoundError("فایل موجود نیست")
            return self.stream(studio._project_dir(parts[2])/"media"/match["file"],
                       "video/mp4" if match["type"]=="video" else "audio/mpeg")
        if len(parts)==5 and parts[:2]==["api","projects"] and parts[3]=="exports":
            name=parts[4]
            if len(name)!=36 or not name.endswith(".mp4"):raise ValueError("فایل خروجی نامعتبر است")
            j=studio.job(name[:-4])
            if j["project"]!=parts[2] or j["status"]!="done":raise ValueError("خروجی آماده نیست")
            return self.stream(studio._project_dir(parts[2])/"exports"/name,"video/mp4")
        raise FileNotFoundError("مسیر نامعتبر")

    def stream(self,p,content_type):
        if not p.is_file():raise FileNotFoundError("فایل موجود نیست")
        size=p.stat().st_size
        range_header=self.headers.get("Range","")
        start=0;end=size-1
        if range_header.startswith("bytes="):
            try:
                vals=range_header[6:].split("-")
                if vals[0]:start=int(vals[0])
                if len(vals)>1 and vals[1]:end=min(end,int(vals[1]))
                if start<0 or start>=size or end<start:raise ValueError("range")
            except ValueError:raise ValueError("محدوده فایل نامعتبر")
        remaining=end-start+1
        self.send_response(206 if range_header else 200)
        self.send_header("Content-Type",content_type)
        self.send_header("Accept-Ranges","bytes")
        self.send_header("Content-Length",str(remaining))
        if range_header:self.send_header("Content-Range",f"bytes {start}-{end}/{size}")
        self.end_headers()
        with p.open("rb") as f:
            f.seek(start)
            while remaining>0:
                data=f.read(min(262144,remaining))
                if not data:break
                try:self.wfile.write(data)
                except (BrokenPipeError,ConnectionResetError):break
                remaining-=len(data)

    def do_POST(self):
        try:
            origin=self.headers.get("Origin","")
            host=self.headers.get("Host","")
            if self.headers.get("Sec-Fetch-Site","")=="cross-site":
                raise ValueError("درخواست بین‌سایتی مجاز نیست")
            if origin and origin not in ("http://"+host,"https://"+host):
                raise ValueError("درخواست از مبدأ دیگری مجاز نیست")
            path=urlsplit(self.path);parts=path.path.strip("/").split("/")
            studio=self.server.studio
            if parts==["api","projects"]:
                return self.send(studio.create(self.json_body().get("title","پروژه جدید")),201)
            if len(parts)==4 and parts[:2]==["api","projects"] and parts[3]=="upload":
                q=parse_qs(path.query)
                name=q.get("name",["video.mp4"])[0]
                n=int(self.headers.get("Content-Length","0"))
                return self.send(studio.upload(parts[2],self.rfile,n,name),201)
            if len(parts)==4 and parts[:2]==["api","projects"] and parts[3]=="save":
                return self.send(studio.save(parts[2],self.json_body()))
            if len(parts)==4 and parts[:2]==["api","projects"] and parts[3]=="render":
                # Drain JSON request body before closing HTTP/1.0 connection:
                # unread bytes can cause TCP RST and truncate otherwise valid responses.
                if int(self.headers.get("Content-Length","0")): self.json_body()
                return self.send(studio.enqueue(parts[2]),202)
            if len(parts)==4 and parts[:2]==["api","jobs"] and parts[3]=="retry":
                if int(self.headers.get("Content-Length","0")): self.json_body()
                return self.send(studio.retry(parts[2]),202)
            raise FileNotFoundError("درخواست نامعتبر")
        except (ValueError,FileNotFoundError,KeyError,TypeError,OverflowError) as e:
            self.send({"error":str(e)},400)
        except Exception:self.send({"error":"خطای سرور"},500)

def serve(host="127.0.0.1",port=8765,workspace=None):
    root=Path(workspace or (Path.home()/".cinema-edit-studio"))
    server=ThreadingHTTPServer((host,port),Handler)
    server.studio=Studio(root)
    print(f"Cinema Edit Studio: http://{host}:{server.server_port}",flush=True)
    try:server.serve_forever()
    finally:
        server.shutdown()
        server.server_close()
        server.studio.close()

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--port",type=int,default=8765)
    a.add_argument("--workspace")
    args=a.parse_args()
    serve(port=args.port,workspace=args.workspace)
