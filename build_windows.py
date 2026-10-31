"""Build a portable folder; run using standard Python 3.11.9 x64 with Tcl/Tk."""
import importlib.metadata as md
import json
import shutil
import subprocess
import sys
from pathlib import Path

def main():
    root=Path(__file__).resolve().parent
    dest=root/"dist"/"SongEngine"
    if dest.exists():
        raise SystemExit("dist/SongEngine already exists. Rename the previous build before rebuilding.")
    cmd=[sys.executable,"-m","PyInstaller","--noconfirm","--onedir","--windowed",
         "--name","SongEngine","--distpath",str(root/"dist"),"--workpath",str(root/"build"),
         "--specpath",str(root/"build"),"--noupx",
         "--collect-all","faster_whisper","--collect-all","ctranslate2",
         "--collect-all","av","--collect-all","tokenizers",
         "--collect-data","huggingface_hub",
         "--copy-metadata","faster-whisper","--copy-metadata","huggingface-hub",
         "--hidden-import","numpy","--hidden-import","numpy.core._multiarray_umath",
         str(root/"app.py")]
    subprocess.run(cmd,cwd=root,check=True)
    add_notices(root,dest)


def add_notices(root,dest):
    for name in ("README.md","LICENSE","THIRD_PARTY_NOTICES.md","TEST_REPORT.md"):
        if (root/name).exists():shutil.copy2(root/name,dest/name)
    licenses=dest/"THIRD_PARTY_LICENSES";licenses.mkdir(exist_ok=True)
    if (root/"third_party_licenses").is_dir():
        shutil.copytree(root/"third_party_licenses",licenses,dirs_exist_ok=True)
    inventory={}
    for package in ("faster-whisper","ctranslate2","av","numpy","tokenizers","huggingface-hub",
                    "tqdm","requests","PyYAML","onnxruntime","certifi","filelock","fsspec",
                    "typing_extensions","protobuf","flatbuffers","charset-normalizer","urllib3","idna","packaging","colorama"):
        dist=md.distribution(package);inventory[package]=dist.version
        for entry in dist.files or []:
            if any(token in str(entry).lower() for token in ("license","copying","notice")):
                src=Path(dist.locate_file(entry))
                if src.is_file():
                    target=licenses/package/Path(str(entry))
                    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
    # CPython embeds its upstream and bundled component notices here.
    for path in (Path(sys.base_prefix)/"LICENSE.txt",Path(sys.base_prefix)/"LICENSE"):
        if path.exists():shutil.copy2(path,licenses/"Python-LICENSE.txt");break
    tkroot=Path(sys.base_prefix)/"tcl"
    if tkroot.is_dir():
        for path in tkroot.rglob("license*"):
            if path.is_file():
                target=licenses/"Tcl-Tk"/path.relative_to(tkroot)
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    (dest/"BUNDLED_VERSIONS.json").write_text(json.dumps(inventory,indent=2),encoding="utf-8")
    print("Built:",dest)

if __name__=="__main__":main()
