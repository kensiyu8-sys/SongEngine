# Third-party notices

SongEngine application code is MIT licensed; the full MIT text is in LICENSE.
This does not change third-party, model-weight, or audio rights.

The portable build includes dynamically linked upstream components and their available installed licence/notice files in THIRD_PARTY_LICENSES/. BUNDLED_VERSIONS.json records the actual versions. Keep these files with redistributed binaries.

Primary components:
- CPython: Python Software Foundation licence and bundled notices — https://www.python.org/downloads/release/python-3119/
- Tcl/Tk: upstream permissive licence — https://www.tcl.tk/software/tcltk/license.html
- faster-whisper: MIT — https://github.com/SYSTRAN/faster-whisper
- CTranslate2: MIT — https://github.com/OpenNMT/CTranslate2
- Whisper model implementation/weights: upstream MIT notices; downloaded converted models retain their upstream terms — https://github.com/openai/whisper and the selected Hugging Face model repository.
- PyAV: BSD-3-Clause — https://github.com/PyAV-Org/PyAV
- FFmpeg libraries distributed with the PyAV Windows wheel retain their own licence terms, source and build provenance. Consult PyAV wheel notices and https://github.com/PyAV-Org/pyav-wheels and https://ffmpeg.org/legal.html before any public binary redistribution.
- NumPy: BSD-3-Clause and bundled native-library notices — https://numpy.org/
- tokenizers: Apache-2.0 — https://github.com/huggingface/tokenizers
- huggingface-hub: Apache-2.0 — https://github.com/huggingface/huggingface_hub
- ONNX Runtime: MIT and bundled notices — https://github.com/microsoft/onnxruntime
- Requests/certifi/urllib3/idna/tqdm/PyYAML and remaining packages: individual notices copied from installed distributions.

PyInstaller is the build tool; its bootloader distribution exception applies to built apps. See https://pyinstaller.org/en/stable/license.html.

No model weights, test speech recording, or user music are bundled in these ZIPs. Model files are downloaded on demand.
No dependencies were modified. The application source package plus build script identifies how the binary was assembled. Before a public release, review the binary wheel provenance and any corresponding-source/relinking obligations for your chosen builds; this local preview has not been cleared as a public binary release.
