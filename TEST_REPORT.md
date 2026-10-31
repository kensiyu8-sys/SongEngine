# SongEngine Desktop v0.3 preview — validation

Date: 24 October 2026, Singapore.

## Passed

- 34 automated tests on Windows x64, CPython 3.11.9:
  - Existing engine regression suite: 22 tests.
  - Project persistence, Unicode/combining marks, timestamp parsing, overlap rejection,
    atomic writes, invalid-save preservation, project import, UTF-8 SRT/review export,
    file-event tailing and preview audio slicing: 12 tests.
- Native Tk UI smoke test: opening/building controls, multilingual rows, editing and
  marking checked, add/delete/undo, save/reopen data, SRT export and busy controls.
- The standalone Windows EXE passed that same UI smoke test.
- Real audio integration through the packaged EXE's worker:
  upstream OpenAI Whisper jfk.flac, about 11 seconds of English speech,
  tiny multilingual model, CPU int8, 2 threads, beam 1.
  - Whole-file auto: en, 1 caption, saved project and 352044-byte mono WAV preview.
  - Mixed-window auto (10 seconds): en/en, 2 captions with offset times and saved preview.
  - Packaged model-name/cache/download-status path: tiny checked 4 cached model files,
    loaded the native model, recognised speech and completed project/preview export.
- Full source UI workflow with a real background worker:
  recognition -> review population -> multilingual text edit -> mark reviewed ->
  project save -> SRT export -> preview preparation -> cancellation preserving the
  current project. The UI event loop stayed active while the subprocess ran.
- Original v0.1 and v0.2 archives remain unchanged.
- Final source and Windows ZIP integrity checks and file-hash manifests.

## Limits / manual acceptance still required

- Real speech tests do not establish accuracy for multilingual singing.
- Mandarin/Cantonese/Japanese/Korean/Malay singing and fast within-line language
  switches need listening tests. No dedicated large-v3 yue inference benchmark.
- No user song was available in the original ZIP; Test 001 regression remains manual.
- No audible speaker verification; playback file slicing was tested with a mocked
  sound call, and real WAV preview generation was tested.
- No actual CapCut, DaVinci Resolve or 剪映 GUI import was performed.
- Native UI behaviour was exercised programmatically; layout has not been visually
  reviewed on your laptop, at high display scaling or with a screen reader.
- The packaged EXE was tested in this Windows environment, not on a second clean PC.
- The standard installer/venv BAT setup is included but not executed end to end here.
  The build/test runtime was an isolated Python 3.11.9 Windows embeddable runtime
  supplemented with unmodified Tcl/Tk files extracted from the official MSI.
  No existing user Python install was changed.
- Model-name lookup used an existing cached tiny model; a fresh first download in a
  clean offline/online user profile still needs acceptance testing.
- Unsigned preview; no installer, updater, public GitHub publication or payment setup.
- Third-party binary public-release compliance review remains before public release.

## Reproduce

Use standard Python 3.11.9 x64 with Tcl/Tk, Install.bat, then:
  .venv\Scripts\python.exe -m unittest discover -s tests -v
  .venv\Scripts\python.exe app.py --self-test-ui

Run the short audio/editor acceptance checklist in README.md.
