"""Create a portable friend-transfer ZIP without personal facts or recordings."""
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    if not (ROOT / "runtime/setup-complete.json").exists():
        raise SystemExit("Complete setup.bat before packaging the transferable runtime")
    includes = ["jarvis", "scripts", "web", "tests", "docs", "esp32", "knowledge_examples",
                "runtime/python", "runtime/flasher", "vendor/windows"]
    top_files = [*ROOT.glob("*.bat"), ROOT / "README.md", ROOT / "requirements.txt", ROOT / "LICENSE",
                 ROOT / "THIRD_PARTY.md", ROOT / "config.example.json", ROOT / "config.laptop.example.json",
                 ROOT / "models.lock.json", ROOT / "runtime/setup-complete.json"]
    for name in ("runtime/llama-version.json", "runtime/runtime-checksums.json"):
        if (ROOT / name).exists():
            top_files.append(ROOT / name)
    hashes = json.loads((ROOT / "models/installed.sha256.json").read_text(encoding="utf-8"))
    top_files += [ROOT / path for path in hashes]
    top_files += [ROOT / "models/manifest.json", ROOT / "models/installed.sha256.json"]
    files = set(top_files)
    for folder in includes:
        if (ROOT / folder).exists():
            files.update(p for p in (ROOT / folder).rglob("*") if p.is_file()
                         and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".log"})
    output = ROOT / "dist/Jarvis-Windows-Portable.zip"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=2, allowZip64=True) as archive:
        for path in sorted(files):
            relative = path.relative_to(ROOT).as_posix()
            if relative.startswith("esp32/build/") and not path.name.endswith((".bin", ".json")):
                continue
            archive.write(path, "Jarvis/" + relative)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Transfer ZIP failed integrity verification")
    print(f"Ready: {output} ({output.stat().st_size/1e6:.1f} MB)")
    print("Extract the complete Jarvis folder on the friend's Windows x64 laptop, then double-click start.bat.")


if __name__ == "__main__":
    main()
