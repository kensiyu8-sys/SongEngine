"""Lightweight native desktop interface; all model work happens outside the UI process."""
import copy
import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import project as projects
from audio import Player
from controller import Job
import songengine

LANGUAGES={"Auto detect":"auto","Mandarin / Chinese":"zh","Cantonese (compatible model required)":"yue",
           "English":"en","Japanese":"ja","Korean":"ko","Malay":"ms","Other code":"other"}
MODELS={"Fast test — base":"base","Balanced — small":"small","Lightest — tiny":"tiny",
        "Cantonese / higher accuracy — large-v3":"large-v3","Large v3 turbo":"large-v3-turbo"}
BG="#101923";PANEL="#182532";TEXT="#e6edf3";MUTED="#a8b7c6";TEAL="#4ed5b5"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SongEngine • Desktop v0.3")
        self.geometry("1160x820");self.minsize(980,700);self.configure(bg=BG)
        self.data=None;self.project_path=None;self.selected=None;self.dirty=False
        self.undo=[];self.job=None;self.job_started=0;self.final_event=False
        self.player=Player();self.actions=[];self.inputs=[];self.editable_texts=[]
        self.audio=tk.StringVar();self.language=tk.StringVar(value="Auto detect")
        self.other=tk.StringVar(value="fr");self.model=tk.StringVar(value="Fast test — base")
        self.model_hint=tk.StringVar(value="Base model weights: about 145 MB download. Cached locally after first use.")
        self.mixed=tk.BooleanVar();self.threads=tk.StringVar(value="2")
        self.chunk=tk.StringVar(value="30");self.bom=tk.BooleanVar(value=True)
        self.start=tk.StringVar();self.end=tk.StringVar();self.reviewed=tk.BooleanVar()
        self.status=tk.StringVar(value="Ready • choose audio or open an existing project")
        self.meta=tk.StringVar(value="Your audio stays on this computer. First model use needs a download.")
        self.heard=tk.StringVar();self.flags=tk.StringVar(value="Select a caption to review.")
        self._style();self._build()
        self.protocol("WM_DELETE_WINDOW",self.close)
        self.bind("<Control-s>",lambda e:self.safe(self.save))
        self.bind("<Control-o>",lambda e:self.safe(self.open_project))
        self.after(200,self.tick)

    def _style(self):
        s=ttk.Style(self);s.theme_use("clam")
        s.configure(".",background=BG,foreground=TEXT,font=("Segoe UI",10))
        s.configure("TFrame",background=BG)
        s.configure("Card.TFrame",background=PANEL)
        s.configure("TLabel",background=BG,foreground=TEXT)
        s.configure("Muted.TLabel",foreground=MUTED)
        s.configure("Title.TLabel",font=("Segoe UI",23,"bold"),foreground=TEAL)
        s.configure("TButton",background="#26394b",foreground=TEXT,padding=(12,7),borderwidth=0)
        s.map("TButton",background=[("active","#335069"),("disabled","#1c2935")],
              foreground=[("disabled","#68798a")])
        s.configure("Accent.TButton",background="#218871",foreground="white")
        s.map("Accent.TButton",background=[("active","#2ca88c"),("disabled","#1c433b")])
        s.configure("TEntry",fieldbackground="#223242",foreground=TEXT,insertcolor=TEXT,padding=5)
        s.configure("TCombobox",fieldbackground="#223242",background="#26394b",foreground=TEXT,padding=5)
        s.map("TCombobox",fieldbackground=[("readonly","#223242")],foreground=[("readonly",TEXT)])
        s.configure("TCheckbutton",background=BG,foreground=TEXT,padding=3)
        s.configure("TNotebook",background=BG,borderwidth=0)
        s.configure("TNotebook.Tab",padding=(20,9),background="#1b2a38",foreground=MUTED)
        s.map("TNotebook.Tab",background=[("selected","#2a4355")],foreground=[("selected",TEXT)])
        s.configure("Treeview",background=PANEL,fieldbackground=PANEL,foreground=TEXT,rowheight=29,borderwidth=0)
        s.configure("Treeview.Heading",background="#26394b",foreground=TEXT,padding=7)
        s.map("Treeview",background=[("selected","#286554")])
        s.configure("Horizontal.TProgressbar",background=TEAL,troughcolor=PANEL)

    def button(self,parent,text,fn,accent=False,**pack):
        b=ttk.Button(parent,text=text,command=lambda:self.safe(fn),
                     style="Accent.TButton" if accent else "TButton")
        b.pack(side="left",padx=(0,7),**pack);self.actions.append(b);return b

    def entry(self,parent,var,width=None):
        e=ttk.Entry(parent,textvariable=var,width=width);self.inputs.append(e);return e

    def text_box(self,parent,height):
        t=tk.Text(parent,height=height,bg=PANEL,fg=TEXT,insertbackground=TEXT,
                  relief="flat",font=("Segoe UI",11),wrap="word",padx=10,pady=9,undo=True)
        self.editable_texts.append(t);return t

    def _build(self):
        header=ttk.Frame(self,padding=(24,18,24,10));header.pack(fill="x")
        ttk.Label(header,text="SONGENGINE",style="Title.TLabel").pack(side="left")
        ttk.Label(header,text="DESKTOP 0.3  /  LOCAL • MULTILINGUAL",style="Muted.TLabel").pack(side="left",padx=20)
        bar=ttk.Frame(self,padding=(24,0,24,14));bar.pack(fill="x")
        self.button(bar,"New",self.new);self.button(bar,"Open project / timing JSON",self.open_project)
        self.button(bar,"Save project",self.save);self.button(bar,"Export SRT",self.export,True)
        self.button(bar,"Open project folder",self.open_folder)
        self.tabs=ttk.Notebook(self);self.tabs.pack(fill="both",expand=True,padx=24)
        self.prepare=ttk.Frame(self.tabs,padding=16);self.review=ttk.Frame(self.tabs,padding=12)
        self.activity=ttk.Frame(self.tabs,padding=12)
        self.tabs.add(self.prepare,text="1   Audio & lyrics")
        self.tabs.add(self.review,text="2   Review & edit")
        self.tabs.add(self.activity,text="Activity")
        self._prepare();self._review()
        self.log=tk.Text(self.activity,bg=PANEL,fg=MUTED,font=("Consolas",10),relief="flat",wrap="word",state="disabled")
        self.log.pack(fill="both",expand=True)
        footer=ttk.Frame(self,padding=(24,12,24,16));footer.pack(fill="x")
        ttk.Label(footer,textvariable=self.status).pack(anchor="w")
        self.progress=ttk.Progressbar(footer,mode="indeterminate");self.progress.pack(fill="x",pady=(8,0))

    def _prepare(self):
        p=self.prepare
        ttk.Label(p,text="Turn a song into an editable subtitle draft",font=("Segoe UI",17,"bold")).pack(anchor="w")
        ttk.Label(p,textvariable=self.meta,style="Muted.TLabel",wraplength=1000).pack(anchor="w",pady=(4,16))
        row=ttk.Frame(p);row.pack(fill="x",pady=(0,14))
        ttk.Label(row,text="Audio").pack(side="left",padx=(0,12))
        self.entry(row,self.audio).pack(side="left",fill="x",expand=True,padx=(0,10))
        self.button(row,"Browse…",self.choose_audio)
        options=ttk.Frame(p);options.pack(fill="x")
        for col,label in enumerate(("Language","Recognition model","CPU threads","Window (sec)")):
            ttk.Label(options,text=label,style="Muted.TLabel").grid(row=0,column=col,sticky="w",padx=(0,14))
        self.lang_combo=ttk.Combobox(options,textvariable=self.language,values=list(LANGUAGES),state="readonly",width=31)
        self.lang_combo.grid(row=1,column=0,sticky="ew",padx=(0,14),pady=7);self.inputs.append(self.lang_combo)
        self.model_combo=ttk.Combobox(options,textvariable=self.model,values=list(MODELS),state="readonly",width=34)
        self.model_combo.grid(row=1,column=1,sticky="ew",padx=(0,14));self.inputs.append(self.model_combo)
        self.model_combo.bind("<<ComboboxSelected>>",lambda e:self.model_hint.set({"tiny":"Tiny weights: about 76 MB.","base":"Base weights: about 145 MB.","small":"Small weights: about 484 MB.","large-v3":"Large-v3 weights: about 3.1 GB; much heavier CPU/RAM use.","large-v3-turbo":"Large-v3-turbo is a large download and needs more memory."}[MODELS[self.model.get()]]+" Downloaded files are cached locally."))
        self.entry(options,self.threads,5).grid(row=1,column=2,sticky="w",padx=(0,14))
        self.entry(options,self.chunk,6).grid(row=1,column=3,sticky="w")
        ttk.Label(p,textvariable=self.model_hint,style="Muted.TLabel",wraplength=1000).pack(anchor="w",pady=(3,7))
        extra=ttk.Frame(p);extra.pack(fill="x",pady=(2,9))
        ttk.Label(extra,text="Other language code:",style="Muted.TLabel").pack(side="left")
        self.entry(extra,self.other,6).pack(side="left",padx=(7,18))
        mixed=ttk.Checkbutton(extra,text="Mixed languages • re-detect in each window",variable=self.mixed)
        mixed.pack(side="left");self.inputs.append(mixed)
        ttk.Label(p,text="Cantonese yue requires large-v3 or another compatible model; it can be heavy on an older laptop.",
                  style="Muted.TLabel",wraplength=1000).pack(anchor="w",pady=(0,12))
        lyr=ttk.Frame(p);lyr.pack(fill="x")
        ttk.Label(lyr,text="Original lyrics",font=("Segoe UI",11,"bold")).pack(side="left")
        self.button(lyr,"Load UTF-8 TXT…",self.load_lyrics)
        ttk.Label(p,text="Paste exact sung lines in performance order. Mixed scripts are welcome. Lyrics are optional.",
                  style="Muted.TLabel").pack(anchor="w",pady=6)
        self.lyrics=self.text_box(p,7);self.lyrics.pack(fill="both",expand=True)
        go=ttk.Frame(p);go.pack(fill="x",pady=(14,0))
        self.button(go,"Generate subtitle draft",self.generate,True)
        self.cancel=ttk.Button(go,text="Cancel processing",command=lambda:self.safe(self.cancel_job),state="disabled")
        self.cancel.pack(side="left")
        ttk.Label(go,text="CPU only • one song at a time",style="Muted.TLabel").pack(side="right")

    def _review(self):
        p=self.review
        self.summary=tk.StringVar(value="Open a project or generate a draft to begin.")
        ttk.Label(p,textvariable=self.summary,style="Muted.TLabel").pack(anchor="w",pady=(0,9))
        table=ttk.Frame(p);table.pack(fill="both",expand=True)
        self.tree=ttk.Treeview(table,columns=("start","end","text","state"),show="headings",selectmode="browse",height=7)
        for key,label,width in (("start","Start",115),("end","End",115),("text","Caption",530),("state","Review",130)):
            self.tree.heading(key,text=label);self.tree.column(key,width=width,minwidth=80,stretch=key=="text")
        scroll=ttk.Scrollbar(table,orient="vertical",command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left",fill="both",expand=True);scroll.pack(side="right",fill="y")
        self.tree.tag_configure("needs",foreground="#efc078");self.tree.tag_configure("reviewed",foreground="#78d6b5")
        self.tree.bind("<<TreeviewSelect>>",self.select_row)
        edit=ttk.Frame(p);edit.pack(fill="x",pady=(12,5))
        ttk.Label(edit,text="Start").pack(side="left")
        self.entry(edit,self.start,16).pack(side="left",padx=(8,14))
        ttk.Label(edit,text="End").pack(side="left")
        self.entry(edit,self.end,16).pack(side="left",padx=(8,14))
        check=ttk.Checkbutton(edit,text="I checked this caption",variable=self.reviewed)
        check.pack(side="left");self.inputs.append(check)
        self.caption=self.text_box(p,2);self.caption.pack(fill="x")
        ttk.Label(p,textvariable=self.heard,style="Muted.TLabel",wraplength=1000).pack(anchor="w",pady=(6,2))
        ttk.Label(p,textvariable=self.flags,style="Muted.TLabel",wraplength=1000).pack(anchor="w")
        actions=ttk.Frame(p);actions.pack(fill="x",pady=10)
        self.button(actions,"Apply edit",self.apply)
        self.button(actions,"Add caption",self.add_caption);self.button(actions,"Delete",self.delete_caption)
        self.button(actions,"Undo",self.undo_edit);self.button(actions,"Missing lyric lines",self.show_missing)
        audio=ttk.Frame(p);audio.pack(fill="x")
        self.button(audio,"▶ Play selected",self.play_selected)
        self.button(audio,"▶ Play all",self.play_all);self.button(audio,"■ Stop",self.player.stop)
        self.button(audio,"Prepare preview…",self.prepare_preview)
        bom=ttk.Checkbutton(audio,text="UTF-8 BOM",variable=self.bom)
        bom.pack(side="right");self.inputs.append(bom)

    def safe(self,fn):
        try:return fn()
        except Exception as exc:messagebox.showerror("SongEngine",str(exc),parent=self)

    def set_busy(self,busy):
        for button in self.actions:button.configure(state="disabled" if busy else "normal")
        for widget in self.inputs:
            widget.configure(state="disabled" if busy else ("readonly" if isinstance(widget,ttk.Combobox) else "normal"))
        for text in self.editable_texts:text.configure(state="disabled" if busy else "normal")
        self.cancel.configure(state="normal" if busy else "disabled")
        if busy:self.progress.configure(mode="indeterminate");self.progress.start(12)
        else:self.progress.stop();self.progress.configure(mode="determinate",value=0)

    def add_log(self,message):
        self.log.configure(state="normal");self.log.insert("end",message+"\n");self.log.see("end");self.log.configure(state="disabled")

    def choose_audio(self):
        path=filedialog.askopenfilename(parent=self,title="Choose song audio",
            filetypes=[("Audio / video","*.mp3 *.wav *.flac *.m4a *.ogg *.aac *.wma *.mp4"),("All files","*.*")])
        if path:
            self.audio.set(path)
            matching=Path(path).with_suffix(".txt")
            if matching.is_file() and not self.lyrics.get("1.0","end-1c").strip():self.set_lyrics(songengine.read_lyrics(matching))

    def set_lyrics(self,lines):
        self.lyrics.delete("1.0","end");self.lyrics.insert("1.0","\n".join(lines))

    def load_lyrics(self):
        path=filedialog.askopenfilename(parent=self,filetypes=[("UTF-8 lyrics","*.txt")])
        if path:self.set_lyrics(songengine.read_lyrics(path))

    def options(self):
        code=LANGUAGES[self.language.get()]
        return songengine.validate(dict(model=MODELS[self.model.get()],language=self.other.get() if code=="other" else code,
            mixed_language=self.mixed.get(),threads=int(self.threads.get()),chunk_seconds=int(self.chunk.get()),
            beam_size=1 if MODELS[self.model.get()] in ("base","tiny") else 3,srt_bom=self.bom.get()))

    def ask_save(self):
        if self.selected is not None:self.commit()
        if not self.dirty:return True
        answer=messagebox.askyesnocancel("Save changes?","Save your current caption edits before continuing?",parent=self)
        if answer is None:return False
        return self.save() if answer else True

    def new(self):
        if self.job or not self.ask_save():return
        self.player.stop();self.data=None;self.project_path=None;self.selected=None;self.dirty=False;self.undo=[]
        self.audio.set("");self.set_lyrics([]);self.refresh();self.tabs.select(self.prepare)

    def open_project(self):
        if self.job or not self.ask_save():return
        path=filedialog.askopenfilename(parent=self,title="Open SongEngine project or v0.2 timing JSON",
                                       filetypes=[("SongEngine / timing JSON","*.json")])
        if path:
            data=projects.load_project(path)
            raw=json.loads(Path(path).read_text(encoding="utf-8-sig"))
            self.load_data(data,Path(path) if raw.get("format")==projects.FORMAT else None)

    def load_data(self,data,path=None):
        self.player.stop();self.data=data;self.project_path=path;self.selected=None;self.dirty=False;self.undo=[]
        self.audio.set(data.get("audio",""))
        self.bom.set(data.get("options",{}).get("srt_bom",True))
        self.refresh();self.tabs.select(self.review)
        self.status.set("Draft ready • listen, edit, save, then export")
        if data["rows"]:self.tree.selection_set("0");self.select_row()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        rows=self.data["rows"] if self.data else []
        for i,row in enumerate(rows):
            state="Checked" if row.get("reviewed") else ("Flagged" if row.get("reasons") else "Listen")
            self.tree.insert("","end",iid=str(i),values=(songengine.stamp(row["start"]),songengine.stamp(row["end"]),
                row["text"].replace("\n"," / "),state),tags=("reviewed" if row.get("reviewed") else "needs",))
        missing=len(self.data.get("unmatched_lyrics",[])) if self.data else 0
        checked=sum(bool(r.get("reviewed")) for r in rows)
        self.summary.set(f"{len(rows)} captions • {checked} checked • {missing} unmatched lyric lines • timings need listening review")
        if self.selected is None:self.clear_editor()

    def clear_editor(self):
        self.start.set("");self.end.set("");self.reviewed.set(False)
        self.caption.delete("1.0","end");self.heard.set("");self.flags.set("Select a caption to review.")

    def select_row(self,event=None):
        if self.job:return
        selected=self.tree.selection()
        if not selected:return
        target=int(selected[0])
        if target==self.selected:return
        try:self.commit()
        except Exception as exc:
            if self.selected is not None:self.tree.selection_set(str(self.selected))
            messagebox.showerror("Check caption",str(exc),parent=self);return
        self.selected=target;self.fill_editor()

    def fill_editor(self):
        if self.selected is None or not self.data:return
        r=self.data["rows"][self.selected]
        self.start.set(songengine.stamp(r["start"]));self.end.set(songengine.stamp(r["end"]))
        self.caption.delete("1.0","end");self.caption.insert("1.0",r["text"]);self.reviewed.set(bool(r.get("reviewed")))
        self.heard.set("Recognised: "+r.get("heard",""))
        self.flags.set("Check: "+(", ".join(r.get("reasons",[])) or "listen to the timing"))

    def snapshot(self):
        self.undo.append(copy.deepcopy(self.data["rows"]))
        self.undo=self.undo[-30:]

    def commit(self):
        if self.selected is None or not self.data:return
        old=self.data["rows"][self.selected];row=dict(old)
        row.update(start=projects.parse_time(self.start.get()),end=projects.parse_time(self.end.get()),
                   text=self.caption.get("1.0","end-1c").strip(),reviewed=self.reviewed.get())
        if row==old:return
        rows=copy.deepcopy(self.data["rows"]);rows[self.selected]=row;projects.validate_rows(rows)
        self.snapshot();self.data["rows"]=rows;self.dirty=True

    def apply(self):
        self.commit();index=self.selected;self.refresh()
        if index is not None:self.tree.selection_set(str(index));self.fill_editor()
        self.status.set("Edit applied • save project to keep your changes")

    def add_caption(self):
        if not self.data:raise ValueError("Open a project or generate a draft first.")
        self.commit();self.snapshot()
        start=self.data["rows"][-1]["end"] if self.data["rows"] else 0
        self.data["rows"].append(dict(start=start,end=start+2,text="New caption",heard="",reasons=["manually_added"],reviewed=False))
        self.selected=None;self.dirty=True;self.refresh();self.tree.selection_set(str(len(self.data["rows"])-1));self.select_row()
        self.caption.focus_set();self.caption.tag_add("sel","1.0","end-1c")

    def delete_caption(self):
        if self.selected is None:return
        self.snapshot();del self.data["rows"][self.selected];self.selected=None;self.dirty=True;self.refresh()

    def undo_edit(self):
        if not self.undo:return
        self.data["rows"]=self.undo.pop();self.selected=None;self.dirty=True;self.refresh()

    def save(self):
        if self.job:return False
        if not self.data:raise ValueError("No project to save yet.")
        self.commit()
        path=self.project_path
        if path is None:
            chosen=filedialog.asksaveasfilename(parent=self,defaultextension=".songengine.json",
                initialfile="Song.songengine.json",filetypes=[("SongEngine project","*.json")])
            if not chosen:return False
            path=Path(chosen)
        projects.save_project(path,self.data);self.project_path=path;self.dirty=False
        self.status.set("Project saved");return True

    def export(self):
        if self.job:return
        if not self.data:raise ValueError("No captions to export.")
        self.commit()
        base=Path(self.data.get("audio") or "Song").stem
        path=filedialog.asksaveasfilename(parent=self,defaultextension=".srt",initialfile=base+".srt",
                                         filetypes=[("SubRip subtitles","*.srt")])
        if path:
            projects.export_srt(path,self.data,self.bom.get())
            report=Path(path).with_name(Path(path).stem+"_REVIEW.txt")
            if report.exists():report=report.with_stem(report.stem+datetime.now().strftime("_%Y%m%d_%H%M%S_%f"))
            projects.export_review(report,self.data)
            self.status.set("SRT + review report exported • import into your video editor")

    def open_folder(self):
        if self.project_path:os.startfile(str(self.project_path.parent))
        elif self.job:os.startfile(str(self.job.path.parent))
        else:raise ValueError("Save or generate a project first.")

    def show_missing(self):
        if not self.data:return
        win=tk.Toplevel(self);win.title("Unmatched original lyric lines");win.geometry("650x430")
        text=tk.Text(win,wrap="word",font=("Segoe UI",11));text.pack(fill="both",expand=True)
        lines=self.data.get("unmatched_lyrics",[])
        text.insert("1.0","No automatic timestamps were fabricated for these lines.\n\n"+
            ("\n".join(f"{r['line']}: {r['text']}" for r in lines) or "No unmatched reference lines."))
        text.configure(state="disabled")

    def start_job(self,action):
        audio=Path(self.audio.get())
        if not audio.is_file():raise ValueError("Choose an existing audio file.")
        options=self.options()
        configured=os.environ.get("SONGENGINE_DATA_DIR")
        root=Path(configured) if configured else Path(os.environ.get("LOCALAPPDATA") or str(Path.home()))/"SongEngine"
        folder=root/"Projects"/datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        folder.mkdir(parents=True,exist_ok=False)
        job=dict(audio=str(audio.resolve()),lyrics=self.lyrics.get("1.0","end-1c"),options=options,
                 model_cache=str(root/"Models"),action=action)
        path=folder/"job.json";projects.atomic_text(path,json.dumps(job,ensure_ascii=False,indent=2))
        self.pending_result=None;self.pending_preview=None;self.pending_error=None
        self.player.stop();self.job=Job(path);self.final_event=False
        self.job_started=time.monotonic();self.job_action=action
        try:self.job.start()
        except Exception:self.job=None;raise
        self.set_busy(True);self.status.set("Starting background worker…")
        self.add_log("Started "+action+" • "+audio.name)

    def generate(self):
        if self.job or not self.ask_save():return
        self.start_job("recognise")

    def prepare_preview(self):
        if not self.data:raise ValueError("Open a project first.")
        self.commit()
        if not Path(self.audio.get()).is_file():self.choose_audio()
        self.start_job("preview")

    def cancel_job(self):
        if not self.job:return
        self.job.cancel();self.job=None;self.pending_result=None;self.pending_preview=None;self.pending_error=None;self.set_busy(False)
        self.status.set("Cancelled • existing projects and exports were kept")
        self.add_log("Processing cancelled.")

    def tick(self):
        if self.job:
            job=self.job
            try:
                for event in job.poll():
                    kind=event["kind"]
                    if kind in ("stage","progress","warning"):
                        msg=event.get("message","")
                        elapsed=int(time.monotonic()-self.job_started)
                        self.status.set(f"{msg} • elapsed {elapsed//60:02}:{elapsed%60:02}")
                        self.add_log(msg)
                        if kind=="progress" and event.get("total"):
                            self.progress.stop();self.progress.configure(mode="determinate",
                                value=min(100,event["current"]/event["total"]*100))
                    elif kind=="done":
                        self.final_event=True
                        self.pending_result=event["path"]
                    elif kind=="preview":
                        self.final_event=True
                        self.pending_preview=event["path"]
                    elif kind=="error":
                        self.final_event=True;self.add_log("ERROR: "+event["message"])
                        self.pending_error=event["message"]
                code=job.exitcode
                if code is not None:
                    # Process exits only after flushing the terminal event.
                    for event in job.poll():
                        if event["kind"]=="done":self.final_event=True;self.pending_result=event["path"]
                        elif event["kind"]=="preview":self.final_event=True;self.pending_preview=event["path"]
                        elif event["kind"]=="error":self.final_event=True;self.pending_error=event["message"]
                    self.job=None;self.set_busy(False)
                    if getattr(self,"pending_error",None):
                        msg=self.pending_error;self.pending_error=None
                        self.status.set("Processing failed • open Activity for details")
                        messagebox.showerror("Processing failed",msg+"\n\nWorker log: "+str(job.path.parent/"worker.log"),parent=self)
                    elif getattr(self,"pending_result",None):
                        path=Path(self.pending_result);self.pending_result=None
                        self.load_data(projects.load_project(path),path)
                    elif getattr(self,"pending_preview",None):
                        self.data["preview"]=self.pending_preview;self.data["audio"]=self.audio.get()
                        self.pending_preview=None;self.dirty=True
                        self.status.set("Audio preview ready • save project to retain its path")
                    else:
                        self.status.set(f"Worker stopped (exit {code}). Check "+str(job.path.parent/"worker.log"))
            except Exception as exc:
                job.cancel();self.job=None;self.set_busy(False);self.add_log("ERROR: "+str(exc));self.status.set("Processing stopped • check Activity")
        if self.job:
            elapsed=int(time.monotonic()-self.job_started)
            base=self.status.get().split(" • elapsed ")[0]
            self.status.set(f"{base} • elapsed {elapsed//60:02}:{elapsed%60:02}")
        self.after(250,self.tick)

    def preview_path(self):
        if not self.data:raise ValueError("Open a project first.")
        return self.data.get("preview","")

    def play_selected(self):
        self.commit()
        if self.selected is None:raise ValueError("Select a caption first.")
        row=self.data["rows"][self.selected]
        self.player.play(self.preview_path(),row["start"],row["end"])

    def play_all(self):
        self.player.play(self.preview_path())

    def close(self):
        if self.job:
            if not messagebox.askyesno("Processing is running","Cancel processing and close SongEngine?",parent=self):return
            self.cancel_job()
        try:
            if not self.ask_save():return
        except Exception as exc:messagebox.showerror("Check caption",str(exc),parent=self);return
        self.player.stop();self.destroy()

    def self_test(self):
        rows=[dict(start=0,end=2,text="明明没喝 bubble tea",heard="明明没喝 bubble tea",reasons=["uncertain_language"],reviewed=False),
              dict(start=2,end=4,text="君と歩こう / 너와 함께",heard="君と歩こう",reasons=[],reviewed=False)]
        self.load_data(projects.from_timing(dict(segments=rows)))
        self.update_idletasks()
        assert len(self.tree.get_children())==2
        self.caption.delete("1.0","end");self.caption.insert("1.0","Aku di sini • edited")
        self.reviewed.set(True);self.apply()
        assert self.data["rows"][0]["text"]=="Aku di sini • edited"
        assert self.data["rows"][0]["reviewed"]
        self.add_caption();assert len(self.data["rows"])==3
        self.delete_caption();assert len(self.data["rows"])==2
        self.undo_edit();assert len(self.data["rows"])==3
        self.set_busy(True);assert str(self.cancel["state"])=="normal"
        self.set_busy(False);assert str(self.cancel["state"])=="disabled"
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"demo.songengine.json"
            self.project_path=path;self.save()
            assert projects.load_project(path)["rows"][0]["reviewed"]
            projects.export_srt(Path(folder)/"demo.srt",self.data)
