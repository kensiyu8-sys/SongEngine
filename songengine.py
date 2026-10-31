"""SongEngine v0.3: local multilingual ASR drafts; never verified forced alignment."""
import argparse
import difflib
import json
import math
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

VERSION = "0.3"
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma", ".mp4"}
ALIASES = {"mandarin": "zh", "chinese": "zh", "cantonese": "yue",
           "english": "en", "japanese": "ja", "korean": "ko", "malay": "ms"}
SECTIONS = re.compile(r"^\[(?:(?:verse|chorus|bridge|intro|outro|pre-chorus|instrumental|interlude|hook|end)\b.*|主歌.*|副歌.*|桥段.*|前奏.*|间奏.*|尾奏.*)\]$", re.I)
DEFAULTS = dict(model="small", language="auto", mixed_language=False, chunk_seconds=30,
                threads=2, beam_size=3, match_threshold=0.72, srt_bom=True)

def normalize(s):
    return "".join(c for c in unicodedata.normalize("NFKC", s).casefold() if c.isalnum() or unicodedata.category(c).startswith("M"))

def stamp(t):
    ms = max(0, round(float(t) * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    sec, milli = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{sec:02},{milli:03}"

def read_lyrics(p):
    # Strict decoding avoids silently corrupting Japanese/Chinese legacy encodings.
    return [s for line in Path(p).read_text(encoding="utf-8-sig").splitlines()
            if (s := line.strip()) and not SECTIONS.fullmatch(s)]

def find_lyrics(audio):
    p = Path(audio).with_suffix(".txt")
    return p if p.is_file() else None

def language_code(value):
    code = ALIASES.get(value.strip().lower(), value.strip().lower())
    if code != "auto" and not re.fullmatch(r"[a-z]{2,3}", code):
        raise ValueError("Language must be auto, a language code (zh/en/ja/ko/ms/yue), or a supported name.")
    return code

def validate(options):
    o = dict(DEFAULTS, **options)
    o["language"] = language_code(o["language"])
    for key in ("mixed_language", "srt_bom"):
        if not isinstance(o[key], bool):
            raise ValueError(f"{key} must be true or false")
    for key, lo, hi in (("threads", 1, 32), ("beam_size", 1, 10), ("chunk_seconds", 5, 120)):
        if type(o[key]) is not int or not lo <= o[key] <= hi:
            raise ValueError(f"{key} must be an integer from {lo} to {hi}")
    if type(o["match_threshold"]) not in (int, float) or not .5 <= o["match_threshold"] <= 1:
        raise ValueError("match_threshold must be between 0.5 and 1")
    if not isinstance(o["model"], str) or not o["model"].strip():
        raise ValueError("model must be a name or local model directory")
    if o["model"].endswith(".en"):
        raise ValueError("English-only .en models are disabled in Multilingual Edition.")
    return o

def clean_segments(segments):
    result = []
    previous_end = 0.0
    for seg in segments:
        start, end = float(seg["start"]), float(seg["end"])
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            raise ValueError("Invalid segment timestamps; start/end must be finite, nonnegative, end > start.")
        text = str(seg["text"]).strip()
        if not text:
            continue
        row = dict(seg, start=start, end=end, text=text)
        reasons = list(row.get("reasons", []))
        # Round to milliseconds before clamping, so SRT cannot acquire overlaps.
        start_ms = max(round(start * 1000), round(previous_end * 1000))
        end_ms = round(end * 1000)
        if start_ms != round(start * 1000):
            reasons.append("overlap_clamped")
        if end_ms <= start_ms:
            reasons.append("timing_extended")
            end_ms = start_ms + 150
        row.update(start=start_ms / 1000, end=end_ms / 1000, reasons=reasons)
        previous_end = row["end"]
        result.append(row)
    return result

def align(segments, lyrics, threshold=.72):
    """Conservative sequential lexical match; unmatched lyrics never get invented timing."""
    output, used, cursor = [], set(), 0
    for seg in clean_segments(segments):
        heard = seg["text"]
        if not normalize(heard):
            continue
        choices = []
        for j in range(cursor, min(len(lyrics), cursor + 5)):
            for count in range(1, min(3, len(lyrics) - j) + 1):
                target = "\n".join(lyrics[j:j + count])
                score = difflib.SequenceMatcher(None, normalize(heard), normalize(target), autojunk=False).ratio()
                choices.append((score, -j, -count, target))
        choices.sort(reverse=True)
        score, nj, nc, candidate = choices[0] if choices else (0., 0, 0, "")
        j, count = -nj, -nc
        reasons = list(seg.get("reasons", []))
        indices = []
        shown = heard
        if lyrics and choices and score >= threshold:
            # Equal repeated lyrics are resolved by earliest position, but still reviewed.
            if len(choices) > 1 and choices[1][0] >= score - .03:
                reasons.append("ambiguous_lyric_match")
            if j > cursor:
                reasons.append("skipped_lyric_lines")
            indices = list(range(j, j + count))
            shown = candidate
            used.update(indices)
            cursor = j + count
            if count > 1:
                reasons.append("multiple_lines_share_segment_timing")
        else:
            reasons.append("lyric_mismatch" if lyrics else "no_reference_lyrics")
        if seg.get("avg_logprob", 0) < -1:
            reasons.append("low_recognition_confidence")
        if seg.get("no_speech_prob", 0) > .6:
            reasons.append("possible_instrumental_or_hallucination")
        if seg.get("language_probability", 1) < .65:
            reasons.append("uncertain_language")
        output.append(dict(seg, text=shown, heard=heard, match_score=round(score, 4),
                           lyric_lines=[i + 1 for i in indices], reasons=reasons,
                           status="review" if reasons else "matched"))
    return output, [{"line": i + 1, "text": line} for i, line in enumerate(lyrics) if i not in used]

def transcribe(audio, model, options, progress=None):
    from faster_whisper.audio import decode_audio
    lang = None if options["language"] == "auto" else options["language"]
    supported = model.supported_languages
    if lang and (lang not in supported or model.hf_tokenizer.token_to_id(f"<|{lang}|>") is None):
        raise ValueError(f"Model does not support '{lang}'. Cantonese yue needs a compatible model such as large-v3; it is much heavier on CPU.")
    common = dict(language=lang, task="transcribe", beam_size=options["beam_size"],
                  vad_filter=False, condition_on_previous_text=False, word_timestamps=False)
    chunks, rows = [], []
    if options["mixed_language"]:
        audio_data = decode_audio(str(audio), sampling_rate=16000)
        total = len(audio_data) / 16000
        windows = ((offset / 16000, audio_data[offset:offset + options["chunk_seconds"] * 16000])
                   for offset in range(0, len(audio_data), options["chunk_seconds"] * 16000))
    else:
        total = None
        windows = [(0., str(audio))]
    for offset, source in windows:
        iterator, info = model.transcribe(source, **common)
        duration = len(source) / 16000 if not isinstance(source, str) else info.duration
        chunks.append(dict(start=offset, end=offset + duration, language=info.language,
                           probability=info.language_probability, forced=lang is not None))
        print(f"Recognizing {offset:.1f}s - {offset + duration:.1f}s | language {info.language}", flush=True)
        for s in iterator:
            if not s.text.strip():
                continue
            end = min(s.end, duration)
            if s.start >= end:
                continue
            reasons = []
            if options["mixed_language"] and (s.start < .25 or end > duration - .25):
                reasons.append("chunk_boundary_check")
            rows.append(dict(start=offset + s.start, end=offset + end, text=s.text.strip(),
                             avg_logprob=s.avg_logprob, no_speech_prob=s.no_speech_prob,
                             language=info.language, language_probability=info.language_probability,
                             reasons=reasons))
        if progress:
            progress(offset, offset + duration, total or info.duration, info.language)
    return rows, chunks

def export(audio, root, segments, lyrics, options, chunks, source="recognition"):
    rows, missing = align(segments, lyrics, options["match_threshold"])
    run = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out = Path(root) / f"{Path(audio).stem}_{Path(audio).suffix.lstrip('.')}" / run
    out.mkdir(parents=True, exist_ok=False)
    stem = Path(audio).stem
    metadata = dict(version=VERSION, audio=Path(audio).name, options=options, source=source,
                    timing_method="unverified ASR segment timing; lexical lyric matching",
                    language_chunks=chunks, segments=rows, unmatched_lyrics=missing)
    (out / f"{stem}_timing.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    encoding = "utf-8-sig" if options["srt_bom"] else "utf-8"
    with (out / f"{stem}.srt").open("w", encoding=encoding, newline="\n") as f:
        for i, r in enumerate(rows, 1):
            f.write(f"{i}\n{stamp(r['start'])} --> {stamp(r['end'])}\n{r['text']}\n\n")
    report = ["SongEngine v0.3 Multilingual Edition",
              "DRAFT: all timings need listening review; MATCHED is lexical similarity, not timing verification.",
              f"Source: {source} | requested language: {options['language']} | mixed windows: {options['mixed_language']}",
              f"Captions: {len(rows)} | flagged: {sum(r['status'] == 'review' for r in rows)} | unmatched lyric lines: {len(missing)}",
              "No captions recognized." if not rows else "",
              "Language detection is acoustic, not lyric-script guessing. zh does not prove Mandarin; Cantonese may be labelled zh.",
              "Automatic mode detects one language per file/window; within-line switching can still be wrong.",
              "Normalization does not transliterate, translate, or equate Simplified/Traditional Chinese.",
              "\nLANGUAGE WINDOWS"]
    report += [json.dumps(c, ensure_ascii=False) for c in chunks]
    report.append("\nCAPTIONS")
    for i, r in enumerate(rows, 1):
        report += [f"{i:03} {stamp(r['start'])} --> {stamp(r['end'])} {r['status'].upper()} score={r['match_score']}",
                   f"SHOW: {r['text']}", f"HEARD: {r['heard']}",
                   "CHECK: " + (", ".join(r["reasons"]) or "listen to timing")]
    report.append("\nUNMATCHED ORIGINAL LYRICS (no timing fabricated)")
    report += [f"{r['line']}: {r['text']}" for r in missing]
    (out / f"{stem}_REVIEW.txt").write_text("\n".join(report) + "\n", encoding="utf-8-sig")
    print(f"Created {out} | {len(rows)} captions; {len(missing)} unmatched lyric lines", flush=True)
    return out

def main(argv=None):
    ap = argparse.ArgumentParser(description="SongEngine v0.3 multilingual CPU subtitle drafts")
    ap.add_argument("--config", default="settings.json")
    ap.add_argument("--input", default="Input")
    ap.add_argument("--output", default="Output")
    ap.add_argument("--model")
    ap.add_argument("--language")
    ap.add_argument("--threads", type=int)
    ap.add_argument("--beam-size", type=int)
    ap.add_argument("--chunk-seconds", type=int)
    ap.add_argument("--mixed-language", action=argparse.BooleanOptionalAction, default=None)
    ap.add_argument("--list-languages", action="store_true")
    args = ap.parse_args(argv)
    try:
        config = Path(args.config)
        options = json.loads(config.read_text(encoding="utf-8-sig")) if config.is_file() else {}
        if not isinstance(options, dict):
            raise ValueError("settings.json must contain a JSON object")
        unknown = set(options) - set(DEFAULTS)
        if unknown:
            raise ValueError("Unknown settings: " + ", ".join(sorted(unknown)))
        for key in ("model", "language", "threads", "beam_size", "chunk_seconds", "mixed_language"):
            if getattr(args, key) is not None:
                options[key] = getattr(args, key)
        options = validate(options)
        from faster_whisper import WhisperModel
        if args.list_languages:
            from faster_whisper.tokenizer import _LANGUAGE_CODES
            print("Recognition library language codes (model-specific subset checked at runtime):")
            print(", ".join(_LANGUAGE_CODES))
            return 0
        input_dir = Path(args.input)
        if not input_dir.is_dir():
            print("Input folder missing. Create it and add audio plus matching UTF-8 TXT.")
            return 2
        audios = sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXT)
        if not audios:
            print("No audio found. Add MP3/WAV/etc. plus matching UTF-8 TXT in Input.")
            return 2
        print(f"Loading {options['model']} | CPU int8 | {options['threads']} threads. First use downloads model.", flush=True)
        model = WhisperModel(options["model"], device="cpu", compute_type="int8",
                             cpu_threads=options["threads"], num_workers=1)
        errors = 0
        for audio in audios:
            try:
                lyric_path = find_lyrics(audio)
                lyrics = read_lyrics(lyric_path) if lyric_path else []
                print(f"Processing: {audio.name}", flush=True)
                rows, chunks = transcribe(audio, model, options)
                export(audio, args.output, rows, lyrics, options, chunks)
                if not rows:
                    errors += 1
                    print("WARNING: no captions. Review silence, decoding, or model choice.", file=sys.stderr)
            except Exception as exc:
                errors += 1
                print(f"ERROR {audio.name}: {exc}", file=sys.stderr)
        return 1 if errors else 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
