import json
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import songengine as e

TEXT = ["明明没喝 bubble tea", "我鍾意你呀", "Stay beside me", "君と歩こう", "너와 함께", "Aku di sini", "مرحبا بالعالم", "café"]
def seg(text, start=0, end=2, **extra):
    return dict(start=start, end=end, text=text, **extra)

class CoreTests(unittest.TestCase):
    def test_unicode_normalization(self):
        self.assertEqual(e.normalize("ＢＵＢＢＬＥ　ＴＥＡ！"), "bubbletea")
        self.assertEqual(e.normalize("cafe\u0301"), e.normalize("café"))
    def test_indic_vowel_marks_retained(self):
        self.assertNotEqual(e.normalize("कि"), e.normalize("की"))
    def test_language_aliases(self):
        for name, code in e.ALIASES.items():
            self.assertEqual(e.language_code(name.upper()), code)
        self.assertEqual(e.language_code("fr"), "fr")
    def test_bad_language(self):
        with self.assertRaises(ValueError): e.language_code('zh & echo bad')
    def test_settings_validation(self):
        for options in ({"threads":0}, {"beam_size":0}, {"chunk_seconds":1},
                        {"match_threshold":float("nan")}, {"mixed_language":"false"},
                        {"model":"small.en"}):
            with self.subTest(options=options), self.assertRaises(ValueError): e.validate(options)
    def test_lyrics_utf8_bom_sections(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"歌词.txt"
            p.write_text("[Chorus]\n[副歌]\n\n"+"\n".join(TEXT),encoding="utf-8-sig")
            self.assertEqual(e.read_lyrics(p),TEXT)
    def test_invalid_encoding_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.txt";p.write_bytes(b"\xff\xfe")
            with self.assertRaises(UnicodeError): e.read_lyrics(p)
    def test_all_scripts_and_code_switch_match(self):
        rows, missing=e.align([seg(t,i*3,i*3+2) for i,t in enumerate(TEXT)],TEXT)
        self.assertEqual([r["text"] for r in rows],TEXT)
        self.assertFalse(missing)
    def test_weak_match_retains_heard_and_reports_missing(self):
        rows, missing=e.align([seg("completely different")],["我很想你"])
        self.assertEqual(rows[0]["text"],"completely different")
        self.assertIn("lyric_mismatch", rows[0]["reasons"])
        self.assertEqual(missing,[{"line":1,"text":"我很想你"}])
    def test_combined_lines_no_fake_split_timing(self):
        rows, missing=e.align([seg("hello there stay here")],["hello there","stay here"])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["lyric_lines"],[1,2])
        self.assertIn("multiple_lines_share_segment_timing",rows[0]["reasons"])
        self.assertFalse(missing)
    def test_repeated_chorus_earliest_monotonic(self):
        rows, missing=e.align([seg("stay here",0,1),seg("stay here",2,3)],["stay here","stay here"])
        self.assertEqual([r["lyric_lines"] for r in rows],[[1],[2]])
        self.assertIn("ambiguous_lyric_match",rows[0]["reasons"])
    def test_skipped_lyrics_report(self):
        rows, missing=e.align([seg("stay beside me")],["gone far away","stay beside me"])
        self.assertEqual(missing[0]["line"],1)
        self.assertIn("skipped_lyric_lines", rows[0]["reasons"])
    def test_no_lyrics(self):
        rows,_=e.align([seg("こんにちは")],[])
        self.assertIn("no_reference_lyrics",rows[0]["reasons"])
    def test_invalid_times(self):
        for a,b in ((-1,1),(1,1),(0,math.inf),(math.nan,2)):
            with self.subTest(a=a,b=b), self.assertRaises(ValueError):e.align([seg("a",a,b)],[])
    def test_overlap_rounding(self):
        rows,_=e.align([seg("a",0,2.0004),seg("b",1.9,3)],[])
        self.assertGreaterEqual(rows[1]["start"],rows[0]["end"])
        self.assertIn("overlap_clamped", rows[1]["reasons"])
    def test_acoustic_review_even_when_lyrics_match(self):
        rows,_=e.align([seg("hello",avg_logprob=-2,no_speech_prob=.9,language_probability=.2)],["hello"])
        self.assertEqual(rows[0]["status"],"review")
        self.assertIn("uncertain_language",rows[0]["reasons"])
    def test_stamp_rounding_and_hours(self):
        self.assertEqual(e.stamp(59.9996),"00:01:00,000")
        self.assertEqual(e.stamp(3600),"01:00:00,000")
    def test_export_utf8_and_unique_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            rows=[seg(t,i*3,i*3+2) for i,t in enumerate(TEXT)]
            opts=e.validate({})
            out=e.export("歌.wav",d,rows,TEXT,opts,[],source="synthetic test")
            out2=e.export("歌.wav",d,rows,TEXT,opts,[])
            self.assertNotEqual(out,out2)
            raw=(out/"歌.srt").read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            s=raw.decode("utf-8-sig")
            for t in TEXT:self.assertIn(t,s)
            data=json.loads((out/"歌_timing.json").read_text(encoding="utf-8"))
            self.assertEqual(data["segments"][0]["heard"],TEXT[0])
            opts["srt_bom"]=False
            other=e.export("歌.wav",d,rows,TEXT,opts,[])
            self.assertFalse((other/"歌.srt").read_bytes().startswith(b"\xef\xbb\xbf"))
    def test_empty_export_review(self):
        with tempfile.TemporaryDirectory() as d:
            out=e.export("empty.wav",d,[],["未唱"],e.validate({}),[])
            self.assertIn("No captions recognized",(out/"empty_REVIEW.txt").read_text(encoding="utf-8-sig"))
    def test_model_manual_override_contract(self):
        model=types.SimpleNamespace(supported_languages=["zh","en","ms","yue"], hf_tokenizer=types.SimpleNamespace(token_to_id=lambda t: None if t == "<|yue|>" else 1))
        calls=[]
        def transcribe(source,**kw):
            calls.append(kw)
            return iter([types.SimpleNamespace(start=0,end=1,text="Aku di sini",avg_logprob=-.2,no_speech_prob=0)]),types.SimpleNamespace(language="ms",language_probability=1,duration=2)
        model.transcribe=transcribe
        with patch.dict(sys.modules,{"faster_whisper.audio":types.SimpleNamespace(decode_audio=lambda *a,**k:None)}):
            rows,chunks=e.transcribe(Path("x.wav"),model,e.validate({"language":"malay"}))
            self.assertEqual(calls[0]["language"],"ms")
            self.assertEqual(calls[0]["task"],"transcribe")
            self.assertTrue(chunks[0]["forced"])
            with self.assertRaises(ValueError):e.transcribe(Path("x.wav"),model,e.validate({"language":"yue"}))
    def test_mixed_redetection_offsets_and_override(self):
        # Sliceable sample buffer: no numpy/model required for this contract test.
        model=types.SimpleNamespace(supported_languages=["en","zh"])
        calls=[]
        def transcribe(source,**kw):
            calls.append(kw)
            lang="en" if len(calls)==1 else "zh"
            return iter([types.SimpleNamespace(start=.5,end=2,text=lang,avg_logprob=-.1,no_speech_prob=0)]),types.SimpleNamespace(language=lang,language_probability=.8)
        model.transcribe=transcribe
        fake=types.SimpleNamespace(decode_audio=lambda *a,**kw:bytearray(16000*12))
        with patch.dict(sys.modules,{"faster_whisper.audio":fake}):
            rows,chunks=e.transcribe(Path("mixed.wav"),model,e.validate({"mixed_language":True,"chunk_seconds":5}))
        self.assertEqual(len(calls),3)
        self.assertTrue(all(c["language"] is None for c in calls))
        self.assertEqual([r["start"] for r in rows],[.5,5.5,10.5])
        self.assertEqual([c["language"] for c in chunks],["en","zh","zh"])
    def test_cli_unknown_config(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.json";p.write_text('{"oops":1}')
            self.assertEqual(e.main(["--config",str(p)]),1)

if __name__=="__main__":unittest.main()
