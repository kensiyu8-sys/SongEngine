# SongEngine Desktop v0.3 Preview

A free, local Windows app for turning songs into multilingual subtitle drafts, reviewing uncertain lines, and exporting UTF-8 SRT for editors such as DaVinci Resolve, CapCut and 剪映专业版.

**This is a local preview, not yet a published GitHub release.** It uses Whisper recognition and lexical matching, not verified sung-lyric forced alignment. Listen before publishing subtitles.

## Use the portable Windows app

1. Extract the entire Windows ZIP. Keep SongEngine.exe and its _internal folder together.
2. Open SongEngine.exe. No separate Python installation is required for this build.
3. Choose a song with Browse. Paste lyrics or load a UTF-8 TXT; a same-name TXT is picked up automatically if the lyric box is empty.
4. Choose a language or Auto detect. For a first test use Fast test — base, or Lightest — tiny. Start with 20–40 seconds of audio.
5. Tick Mixed languages for windowed re-detection. A manual language override forces that language in every window.
6. Click Generate subtitle draft. The first use of each model checks/downloads model files; later runs reuse the cache. The window stays responsive. Activity shows model/file status and recognition stages; elapsed time continues to update. The bar does not claim an accurate overall percentage during loading/downloading.
7. Review & edit: select a caption, listen with Play selected, correct text/start/end, mark checked, and Apply edit. Switching captions also applies a valid edit. Overlaps and invalid times are rejected.
8. Save project to keep edits. Export SRT writes UTF-8 captions and a review report. Save the project separately after editing, even if you exported SRT.
9. Import the SRT into the editor with the identical audio at timeline zero. Choose a font supporting the script. Styling, animated text and karaoke highlighting belong in the editor.

This package has no updater, telemetry, automatic publishing, donation collection, cloud audio upload, or editor automation. Models are downloaded from Hugging Face; audio processing is local.

## Features

- Mandarin/Chinese zh, English en, Japanese ja, Korean ko, Malay ms, Cantonese yue with a compatible model, and other model-supported language codes.
- Exact original mixed-script lyric text retained when lexically matched; otherwise recognised text remains for review.
- Normal whole-file auto mode and optional windowed language re-detection.
- One CPU recognition worker, int8 computation, two default threads; no GPU requirement.
- Separate background process, cancellation, stage/file status, elapsed time and Activity log.
- Native Windows audio preview: full song or selected caption range; Stop button.
- Editable text and millisecond timestamps; add/delete captions, undo last applied edits.
- Original heard text, uncertainty reasons, missing-lyric list and user review flags.
- Save/reopen projects; import v0.2 timing JSON without rerunning recognition.
- UTF-8 SRT with optional BOM and a review report preserving uncertainty notes.

## Languages and models

Auto detects one dominant language per file/window; it does not identify every word's language. Short switches and mixed-language sung lines may still be wrong. Try normal and mixed modes on the same short excerpt and compare.

Choose Other code and enter an appropriate Whisper language code such as fr or th. Unsupported codes produce an error. No translation is requested.

Cantonese yue requires a model with that token, such as large-v3. Base/small/tiny reject explicit yue rather than pretending to support it. On an older laptop, small + auto/zh can be tried as a **best-effort Chinese-model route**, but zh detection does not establish Mandarin versus Cantonese. Large-v3 uses much more RAM/CPU.

Approximate weight downloads, checked against upstream model metadata on 24 October 2026: tiny 76 MB, base 145 MB, small 484 MB, large-v3 3.1 GB. Other files add a little overhead. Download size is not RAM usage. Model loading and recognition can be slow on an L340.

Unicode normalization preserves vowel/combining marks. Matching does not translate, romanize, or equate Simplified/Traditional Chinese. Supply lyrics in the actual sung script and order. Repeated choruses need their repeated lines in the TXT. Known section headers are ignored. Grouped lines can share one ASR segment; no individual timings are invented.

## Projects, files and cancellation

Default data location: %LOCALAPPDATA%\SongEngine
- Models\ holds downloaded models.
- Projects\<dated run>\ holds job.json, worker.log, events.jsonl, project.songengine.json, draft exports and audio-preview.wav.
- Set SONGENGINE_DATA_DIR before launching if you need a different writable data directory.

Saved projects refer to the original audio and WAV preview by path; they do not embed/copy your original song. To move a project to another PC, retain the audio, open the project, choose the audio on the first tab, then use Prepare preview on the review tab and save.

v0.2 timing JSON can be opened, but it did not contain a full source path. Choose the original audio and Prepare preview for playback. Importing timing JSON does not overwrite that input JSON when you choose Save.

Cancel terminates only the app's recognition subprocess. Existing projects and exports stay intact. A cancelled new run may leave a dated job folder and partially downloaded cache files; retrying can reuse cached content. If recognition finishes but preview preparation fails, the initial project remains in that run folder.

SRT export validates chronological, non-overlapping, nonempty cues. It will not silently shift your manually entered timestamps. Add caption appends at the end; edit times as needed. Undo tracks applied row edits/adds/deletions during this session. It does not undo file exports. Missing lyric lines refer to the original automatic alignment; adding a manual cue does not automatically remove a line from that list.

WAV previews use mono 16kHz audio. Preparing a preview holds decoded audio in memory. Review playback requires a functioning Windows audio device. Selected-caption playback is limited to two minutes per cue. Playback has Play/Stop, not waveform scrubbing or a live playhead in this version.

## Source / developer setup

Source package: SongEngine_v0.3_Desktop_Source.zip. Use standard Python 3.11.9 x64 with Tcl/Tk enabled.

1. Extract into a new folder; keep working v0.1/v0.2 folders unchanged.
2. Run Install.bat, then Run_Desktop.bat.
3. If py is unavailable, set SONGENGINE_PYTHON to the full python.exe path before running Install.bat.
4. To verify:
   .venv\Scripts\python.exe -m unittest discover -s tests -v
   .venv\Scripts\python.exe app.py --self-test-ui
5. Build_Windows.bat creates dist\SongEngine\. Rename previous build folders before rebuilding; the build script refuses to overwrite dist\SongEngine.
6. Keep the entire output folder together. Test on a second Windows 10/11 x64 machine before making a public release.

The included GitHub Actions workflow runs Windows tests and builds a downloadable CI artifact. It does not publish a release automatically. The app source is MIT; dependencies and model weights retain their own licences. See THIRD_PARTY_NOTICES.md.

## First acceptance test

1. Copy your approved SongEngine Test 001 audio/TXT and compare the new draft with your known-good v0.1 SRT.
2. Check a short clip in each needed language, plus Mandarin + English in one line.
3. Test an instrumental gap, humming, repeated chorus, and one deliberately incorrect reference lyric.
4. Verify flagged/missing lines, edit/save/reopen, play selected, cancel a run, and export.
5. Import that SRT separately into DaVinci, CapCut and 剪映. Confirm scripts, font glyphs and timing.

34 automated tests, native UI tests and real-English-audio integration checks are documented in TEST_REPORT.md. Multilingual singing accuracy, your Test 001 regression, audible playback on your laptop and actual editor imports still need the acceptance test.

## GitHub and optional support

The source tree is prepared for a repository, but no repository or public release has been created. Before publishing: choose your GitHub owner/repository, test the portable build on another PC, check third-party notices and add screenshots. Optional support can be a verified GitHub Sponsors or buy-me-a-kopi link after you choose an account. No payment URL or donation request is embedded in this preview.

## Troubleshooting

- App won't open: extract the full ZIP; do not move SongEngine.exe away from _internal. Check that Windows is x64.
- Unsigned-app prompt: this preview has no code-signing certificate. Inspect the source/build locally if preferred; do not disable antivirus.
- Model download fails: check Hugging Face connectivity, disk space and the Activity log. Retry when online.
- Heavy/slow: choose tiny/base, two threads, one short clip. Large-v3 can be impractical on an older laptop.
- Lyrics appear wrong: compare Heard and original lyrics; mark/edit uncertain lines. A lexical match is not a timing guarantee.
- No sound: check Windows audio output. If the preview is missing, choose the original audio and Prepare preview.
- All original lyric lines absent from output: inspect Missing lyric lines; no artificial timings were assigned.
- Models/projects consume space: close the app before manually archiving/deleting dated run folders you no longer need; retain saved projects and their referenced previews.

Upstream: https://github.com/SYSTRAN/faster-whisper | https://github.com/openai/whisper
