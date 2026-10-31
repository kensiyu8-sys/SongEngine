import copy,json,math,sys,tempfile,types,wave
from pathlib import Path
from unittest.mock import patch
import unittest
import project as p
from controller import Job
from audio import Player

def data():
    return p.from_timing(dict(segments=[dict(start=0,end=1,text="你好 bubble tea",heard="你好 bubble tea",reasons=[]),
                                        dict(start=1,end=3,text="君と歩こう",heard="君と歩こう",reasons=["check"])]))
class ProjectTests(unittest.TestCase):
    def test_time_formats(self):
        self.assertEqual(p.parse_time("01:02:03,450"),3723.45)
        self.assertEqual(p.parse_time("1.125"),1.125)
        for t in ("NaN","inf","-1","00:99:01,000"):
            with self.subTest(t=t),self.assertRaises(ValueError):p.parse_time(t)
    def test_overlap_rejected_not_silently_moved(self):
        d=data();d["rows"][1]["start"]=.5
        with self.assertRaises(ValueError):p.validate_rows(d["rows"])
    def test_blank_cue_separator_rejected(self):
        d=data();d["rows"][0]["text"]="a\n\nb"
        with self.assertRaises(ValueError):p.validate_rows(d["rows"])
    def test_save_reload_unicode_and_review_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"歌.songengine.json";d=data();d["rows"][0]["reviewed"]=True
            p.save_project(path,d);r=p.load_project(path)
            self.assertEqual(r,d)
            r["rows"][0]["text"]="我鍾意你";p.save_project(path,r)
            self.assertEqual(p.load_project(path)["rows"][0]["text"],"我鍾意你")
            self.assertFalse(list(Path(folder).glob("*.tmp")))
    def test_invalid_save_preserves_existing_project(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"p.json";d=data();p.save_project(path,d);original=path.read_bytes()
            d["rows"][0]["end"]=0
            with self.assertRaises(ValueError):p.save_project(path,d)
            self.assertEqual(path.read_bytes(),original)
    def test_v02_timing_import_does_not_mutate(self):
        original=dict(segments=[dict(start=0,end=1,text="你好")]);saved=copy.deepcopy(original)
        imported=p.from_timing(original)
        self.assertEqual(original,saved);self.assertFalse(imported["rows"][0]["reviewed"])
    def test_unknown_project_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"x.json";path.write_text('{"format":"other"}')
            with self.assertRaises(ValueError):p.load_project(path)
    def test_srt_and_review_export(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);d=data();d["rows"][0]["reviewed"]=True
            p.export_srt(path/"x.srt",d)
            self.assertTrue((path/"x.srt").read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertIn("00:00:01,000 --> 00:00:03,000",(path/"x.srt").read_text(encoding="utf-8-sig"))
            p.export_review(path/"r.txt",d)
            report=(path/"r.txt").read_text(encoding="utf-8-sig")
            self.assertIn("USER REVIEWED",report);self.assertIn("君と歩こう",report)
    def test_atomic_failure_preserves_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"x.txt";path.write_text("original")
            with patch("project.os.replace",side_effect=OSError("test failure")):
                with self.assertRaises(OSError):p.atomic_text(path,"new")
            self.assertEqual(path.read_text(),"original")
            self.assertEqual(len(list(Path(folder).iterdir())),1)
    def test_event_tail_handles_partial_and_unicode(self):
        with tempfile.TemporaryDirectory() as folder:
            job=Job(Path(folder)/"job.json");events=Path(folder)/"events.jsonl"
            events.write_text('{"kind":"stage","message":"中文"}\n{"kind":"do',encoding="utf-8")
            self.assertEqual(job.poll()[0]["message"],"中文")
            with events.open("a",encoding="utf-8") as f:f.write('ne","path":"test"}\n')
            self.assertEqual(job.poll(),[dict(kind="done",path="test")])
            self.assertEqual(job.poll(),[])
    def test_audio_selection_uses_correct_wave_range(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"preview.wav"
            with wave.open(str(path),"wb") as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b"\0\0"*32000)
            fake=types.SimpleNamespace(PlaySound=lambda *a:None,SND_FILENAME=1,SND_ASYNC=2,SND_NODEFAULT=4)
            with patch.dict(sys.modules,{"winsound":fake}):
                player=Player();player.play(path,.5,1.5)
                with wave.open(str(player.clip),"rb") as f:self.assertEqual(f.getnframes(),16000)
                player.stop();self.assertFalse((Path(folder)/"selected-caption-preview.wav").exists())
    def test_audio_rejects_outside_range(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"preview.wav"
            with wave.open(str(path),"wb") as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b"\0\0"*16000)
            fake=types.SimpleNamespace(PlaySound=lambda *a:None)
            with patch.dict(sys.modules,{"winsound":fake}):
                with self.assertRaises(ValueError):Player().play(path,2,3)
if __name__=="__main__":unittest.main()
