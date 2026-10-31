"""Small file-event subprocess controller, independent of Tk."""
import json
import os
import subprocess
import sys
from pathlib import Path

class Job:
    def __init__(self,job_path):
        self.path=Path(job_path);self.offset=0;self.partial="";self.process=None
    def start(self):
        args=([sys.executable,"--worker",str(self.path)] if getattr(sys,"frozen",False)
              else [sys.executable,str(Path(__file__).with_name("app.py")),"--worker",str(self.path)])
        self.process=subprocess.Popen(args,creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0,
                                      stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    def poll(self):
        path=self.path.parent/"events.jsonl"
        if not path.exists(): return []
        with path.open("r",encoding="utf-8") as f:
            f.seek(self.offset);text=f.read();self.offset=f.tell()
        lines=(self.partial+text).split("\n");self.partial=lines.pop()
        return [json.loads(line) for line in lines if line.strip()]
    def cancel(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=3)
    @property
    def exitcode(self):
        return self.process.poll() if self.process else None
