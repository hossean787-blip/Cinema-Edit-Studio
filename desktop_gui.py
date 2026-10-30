#!/usr/bin/env python3
"""Lightweight desktop editor for local FFmpeg rendering; Python stdlib only."""
import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from studio import assemble

class Editor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cinema Edit Studio")
        self.geometry("820x600")
        self.configure(bg="#17212f")
        self.shots=[]
        self.music=tk.StringVar()
        self.output=tk.StringVar(value=str(Path.home()/"cinema-reel.mp4"))
        self.status=tk.StringVar(value="Ready")
        self.messages=queue.Queue()
        self._build()
        self.after(150,self.poll)

    def _build(self):
        header=ttk.Frame(self);header.pack(fill="x",padx=16,pady=12)
        ttk.Label(header,text="Cinema Edit Studio — local cinematic editor",font=("Arial",17,"bold")).pack(side="left")
        frame=ttk.LabelFrame(self,text="Clips — choose each shot and its speed")
        frame.pack(fill="both",expand=True,padx=16,pady=8)
        cols=("file","start","duration","speed")
        self.tree=ttk.Treeview(frame,columns=cols,show="headings",selectmode="browse")
        for col,label,width in zip(cols,("Video","Start (s)","Length (s)","Speed"),(400,90,100,90)):
            self.tree.heading(col,text=label);self.tree.column(col,width=width)
        self.tree.pack(fill="both",expand=True,padx=8,pady=8)
        commands=ttk.Frame(self);commands.pack(fill="x",padx=16,pady=5)
        ttk.Button(commands,text="Add clip",command=self.add_clip).pack(side="left",padx=4)
        ttk.Button(commands,text="Edit timing",command=self.edit).pack(side="left",padx=4)
        ttk.Button(commands,text="Remove clip",command=self.remove).pack(side="left",padx=4)
        ttk.Button(commands,text="Move up",command=lambda:self.move(-1)).pack(side="left",padx=4)
        ttk.Button(commands,text="Move down",command=lambda:self.move(1)).pack(side="left",padx=4)
        musicrow=ttk.Frame(self);musicrow.pack(fill="x",padx=16,pady=5)
        ttk.Label(musicrow,text="Music").pack(side="left")
        ttk.Entry(musicrow,textvariable=self.music).pack(side="left",fill="x",expand=True,padx=6)
        ttk.Button(musicrow,text="Browse",command=self.choose_music).pack(side="left")
        outrow=ttk.Frame(self);outrow.pack(fill="x",padx=16,pady=5)
        ttk.Label(outrow,text="Export").pack(side="left")
        ttk.Entry(outrow,textvariable=self.output).pack(side="left",fill="x",expand=True,padx=6)
        ttk.Button(outrow,text="Save as",command=self.choose_output).pack(side="left")
        footer=ttk.Frame(self);footer.pack(fill="x",padx=16,pady=15)
        self.render_btn=ttk.Button(footer,text="Render MP4 1080×1920",command=self.render)
        self.render_btn.pack(side="left")
        ttk.Label(footer,textvariable=self.status).pack(side="left",padx=14)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i,shot in enumerate(self.shots):
            self.tree.insert("","end",iid=str(i),values=(Path(shot["file"]).name,shot["start"],shot["duration"],shot["speed"]))

    def add_clip(self):
        files=filedialog.askopenfilenames(filetypes=[("Video","*.mp4 *.mov *.mkv *.avi"),("All files","*.*")])
        for f in files:self.shots.append(dict(file=str(Path(f).resolve()),start=0.0,duration=2.0,speed=1.0))
        self.refresh()

    def selected(self):
        sel=self.tree.selection()
        return int(sel[0]) if sel else None

    def edit(self):
        i=self.selected()
        if i is None:return
        dialog=tk.Toplevel(self);dialog.title("Shot timing");dialog.transient(self);dialog.grab_set()
        vars=[tk.StringVar(value=str(self.shots[i][key])) for key in ("start","duration","speed")]
        for label,var in zip(("Start (seconds)","Duration (seconds)","Speed (0.5 = slow)"),vars):
            row=ttk.Frame(dialog);row.pack(padx=12,pady=8)
            ttk.Label(row,text=label,width=22).pack(side="left")
            ttk.Entry(row,textvariable=var).pack(side="left")
        def save():
            try:
                start,duration,speed=(float(x.get()) for x in vars)
                if start<0 or duration<=0 or not 0<speed<=8:raise ValueError()
            except ValueError:
                messagebox.showerror("Invalid","Use start >= 0, duration > 0, and 0 < speed <= 8",parent=dialog)
                return
            self.shots[i].update(start=start,duration=duration,speed=speed)
            self.refresh();dialog.destroy()
        ttk.Button(dialog,text="Save",command=save).pack(pady=12)

    def remove(self):
        i=self.selected()
        if i is not None:self.shots.pop(i);self.refresh()

    def move(self,delta):
        i=self.selected()
        if i is None or not 0<=i+delta<len(self.shots):return
        self.shots[i],self.shots[i+delta]=self.shots[i+delta],self.shots[i]
        self.refresh();self.tree.selection_set(str(i+delta))

    def choose_music(self):
        f=filedialog.askopenfilename(filetypes=[("Audio","*.mp3 *.wav *.m4a *.flac"),("All files","*.*")])
        if f:self.music.set(f)

    def choose_output(self):
        f=filedialog.asksaveasfilename(defaultextension=".mp4",filetypes=[("MP4 video","*.mp4")])
        if f:self.output.set(f)

    def render(self):
        if not self.shots:
            messagebox.showerror("No clips","Add at least one video")
            return
        if not self.output.get().strip():
            messagebox.showerror("Missing export","Choose an output file")
            return
        shots=[dict(s) for s in self.shots]
        music=self.music.get().strip()
        out=self.output.get().strip()
        self.render_btn.configure(state="disabled")
        self.status.set("Rendering…")
        def work():
            try:
                import tempfile
                with tempfile.TemporaryDirectory(prefix="cinema-ui-") as tmp:
                    cfg=Path(tmp)/"project.json"
                    cfg.write_text(json.dumps({"resolution":[1080,1920],"fps":30,"shots":shots,"music":music or None}),encoding="utf-8")
                    assemble(cfg,out)
                self.messages.put(("ok",out))
            except Exception as e:self.messages.put(("error",str(e)))
        threading.Thread(target=work,daemon=True).start()

    def poll(self):
        try:
            while True:
                kind,data=self.messages.get_nowait()
                self.render_btn.configure(state="normal")
                self.status.set("Export ready" if kind=="ok" else "Export failed")
                if kind=="ok":messagebox.showinfo("Complete","MP4 saved to:\n"+data)
                else:messagebox.showerror("Render error",data)
        except queue.Empty:pass
        self.after(150,self.poll)

if __name__=="__main__":
    Editor().mainloop()
