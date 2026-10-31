"""Windows WAV preview playback, including selected caption ranges."""
import sys
import wave
from pathlib import Path

class Player:
    def __init__(self):
        self.clip=None
    def stop(self):
        if sys.platform=="win32":
            import winsound
            winsound.PlaySound(None,0)
        if self.clip:
            try: self.clip.unlink(missing_ok=True)
            except OSError: pass
            self.clip=None
    def play(self,preview,start=None,end=None):
        import winsound
        self.stop()
        path=Path(preview)
        if not path.is_file():
            raise ValueError("Audio preview is unavailable. Choose the original audio and click Prepare preview.")
        if start is not None:
            if end-start > 120:
                raise ValueError("Selected preview is over two minutes. Adjust the caption or use Play all.")
            with wave.open(str(path),"rb") as src:
                rate=src.getframerate()
                first=round(start*rate);last=min(round(end*rate),src.getnframes())
                if first>=last: raise ValueError("Caption is outside the available audio.")
                src.setpos(first)
                frames=src.readframes(last-first)
                clip=path.parent/"selected-caption-preview.wav"
                with wave.open(str(clip),"wb") as dest:
                    dest.setparams(src.getparams());dest.writeframes(frames)
            self.clip=clip;path=clip
        winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
