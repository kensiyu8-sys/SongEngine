"""Review project persistence and subtitle export; no GUI or model dependencies."""
import copy
import json
import math
import os
import re
import tempfile
from pathlib import Path
from songengine import stamp

FORMAT = "songengine-project"
VERSION = 1

def parse_time(value):
    text = str(value).strip()
    if ":" in text:
        match = re.fullmatch(r"(\d+):([0-5]\d):([0-5]\d)[,.](\d{3})", text)
        if not match:
            raise ValueError("Use seconds (1.25) or HH:MM:SS,mmm.")
        h,m,s,ms = map(int, match.groups())
        result = h*3600+m*60+s+ms/1000
    else:
        result = float(text)
    if not math.isfinite(result) or result < 0:
        raise ValueError("Time must be a finite, nonnegative number.")
    return round(result, 3)

def validate_rows(rows):
    if not isinstance(rows, list):
        raise ValueError("Project captions must be a list.")
    previous = 0
    for index,row in enumerate(rows, 1):
        if not isinstance(row,dict) or not isinstance(row.get("text"),str):
            raise ValueError(f"Caption {index}: invalid text.")
        start,end = parse_time(row["start"]),parse_time(row["end"])
        if end <= start:
            raise ValueError(f"Caption {index}: end must be after start.")
        if start < previous:
            raise ValueError(f"Caption {index}: overlaps the previous caption. Adjust the times first.")
        if not row["text"].strip() or re.search(r"\n\s*\n",row["text"].strip()):
            raise ValueError(f"Caption {index}: use nonempty text with no blank lines inside a cue.")
        previous = end
    return rows

def from_timing(data, audio="", preview=""):
    rows = copy.deepcopy(data.get("segments",[]))
    for row in rows:
        row.setdefault("reviewed",False)
        row.setdefault("heard",row.get("text",""))
        row.setdefault("reasons",[])
    project = dict(format=FORMAT,version=VERSION,audio=str(audio),preview=str(preview),
                   options=data.get("options",{}),language_chunks=data.get("language_chunks",[]),
                   unmatched_lyrics=data.get("unmatched_lyrics",[]),rows=rows)
    validate_rows(rows)
    return project

def atomic_text(path,text,encoding="utf-8"):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding=encoding,newline="\n") as f:
            f.write(text);f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def save_project(path,data):
    validate_rows(data["rows"])
    atomic_text(path,json.dumps(data,ensure_ascii=False,indent=2)+"\n")

def load_project(path):
    data=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if data.get("format")==FORMAT and data.get("version")==VERSION:
        validate_rows(data["rows"])
        return data
    if "segments" in data: # v0.2 timing JSON can be reviewed without rerunning recognition.
        return from_timing(data)
    raise ValueError("Not a supported SongEngine project/timing JSON.")

def export_srt(path,data,bom=True):
    validate_rows(data["rows"])
    if not data["rows"]:
        raise ValueError("No captions to export.")
    content="".join(f"{i}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['text'].strip()}\n\n"
                    for i,r in enumerate(data["rows"],1))
    atomic_text(path,content,"utf-8-sig" if bom else "utf-8")

def export_review(path,data):
    lines=["SongEngine Desktop v0.3 | review report",
           "Draft timings; user-reviewed means marked by the user, not independently verified.",
           f"Audio: {data.get('audio','')}",
           f"Requested language: {data.get('options',{}).get('language','unknown')}",
           "\nLANGUAGE WINDOWS"]
    lines += [json.dumps(c,ensure_ascii=False) for c in data.get("language_chunks",[])]
    for i,r in enumerate(data["rows"],1):
        lines += [f"\n{i:03d} {stamp(r['start'])} --> {stamp(r['end'])} | "+("USER REVIEWED" if r.get("reviewed") else "NEEDS LISTENING"),
                  "TEXT: "+r["text"],"HEARD: "+r.get("heard",""),
                  "FLAGS: "+(", ".join(r.get("reasons",[])) or "check timing")]
    lines.append("\nUNMATCHED ORIGINAL LYRIC LINES")
    lines += [f"{r['line']}: {r['text']}" for r in data.get("unmatched_lyrics",[])]
    atomic_text(path,"\n".join(lines)+"\n","utf-8-sig")
