"""Recognition subprocess. Events go to disk so a windowed EXE needs no console."""
import json
import os
import sys
import threading
import time
import traceback
import wave
from pathlib import Path
from project import from_timing,save_project

def run(job_path):
    job_path=Path(job_path)
    job=json.loads(job_path.read_text(encoding="utf-8"))
    folder=job_path.parent
    events=(folder/"events.jsonl").open("a",encoding="utf-8",buffering=1)
    log=(folder/"worker.log").open("a",encoding="utf-8",buffering=1)
    sys.stdout=log;sys.stderr=log
    lock=threading.Lock()
    def emit(kind,**payload):
        with lock:
            events.write(json.dumps(dict(kind=kind,**payload),ensure_ascii=False)+"\n")
    try:
        import songengine as engine
        audio=Path(job["audio"])
        if not audio.is_file(): raise ValueError("Original audio file is missing.")
        options=engine.validate(job["options"])
        cache=Path(job["model_cache"]);cache.mkdir(parents=True,exist_ok=True)
        os.environ["HF_HOME"]=str(cache/"hub")
        os.environ["HF_HUB_DISABLE_XET"]="1"
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"]="1"
        if job.get("action")!="preview":
            emit("stage",message="Checking model / downloading missing files. First use needs internet.")
            from faster_whisper import WhisperModel
            from faster_whisper.utils import _MODELS
            from huggingface_hub import snapshot_download
            from tqdm.auto import tqdm
            model_name=options["model"]
            if not Path(model_name).is_dir():
                if model_name not in _MODELS:raise ValueError("Unknown model selection.")
                class DownloadProgress(tqdm):
                    last=0
                    def update(self,n=1):
                        result=super().update(n)
                        now=time.monotonic()
                        if now-self.last>.3:
                            self.last=now
                            emit("stage",message=f"Model files: {self.n:g} / {self.total or '?'} checked/downloaded")
                        return result
                model_name=snapshot_download(_MODELS[model_name],cache_dir=str(cache),
                    allow_patterns=["config.json","preprocessor_config.json","model.bin","tokenizer.json","vocabulary.*"],
                    tqdm_class=DownloadProgress)
            emit("stage",message="Loading model on CPU (int8, one worker).")
            model=WhisperModel(model_name,device="cpu",compute_type="int8",
                               cpu_threads=options["threads"],num_workers=1)
            def progress(start,end,total,language):
                emit("progress",current=end,total=total,language=language,
                     message=f"Recognised through {end:.1f}s | language {language}")
            emit("stage",message="Recognising audio. Singing may take longer than the song duration.")
            rows,chunks=engine.transcribe(audio,model,options,progress=progress)
            emit("stage",message="Matching lyrics and writing draft files.")
            lyrics=[s for line in job.get("lyrics","").splitlines()
                    if (s:=line.strip()) and not engine.SECTIONS.fullmatch(s)]
            out=engine.export(audio,folder/"draft",rows,lyrics,options,chunks)
            timing=json.loads((out/(audio.stem+"_timing.json")).read_text(encoding="utf-8"))
            data=from_timing(timing,audio)
            save_project(folder/"project.songengine.json",data)
            del model
            if not rows:emit("warning",message="No captions recognised. Check the audio and model.")
        emit("stage",message="Preparing local WAV preview for listening.")
        from faster_whisper.audio import decode_audio
        import numpy as np
        pcm=decode_audio(str(audio),sampling_rate=16000)
        preview=folder/"audio-preview.wav"
        with wave.open(str(preview),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
            f.writeframes((np.clip(pcm,-1,1)*32767).astype("<i2").tobytes())
        if job.get("action")=="preview":
            emit("preview",path=str(preview))
        else:
            data["preview"]=str(preview);save_project(folder/"project.songengine.json",data)
            emit("done",path=str(folder/"project.songengine.json"))
        return 0
    except Exception as exc:
        traceback.print_exc(file=log)
        emit("error",message=str(exc))
        return 1
    finally:
        events.close();log.flush()
