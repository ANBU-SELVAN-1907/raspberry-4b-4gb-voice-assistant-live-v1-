"""Install only the classic ESP32 SDK from the official pinned core archive."""
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def install_tools(package, platform):
    from scripts.download_models import download
    for dependency in platform["toolsDependencies"]:
        if dependency["name"] not in {"xtensa-esp32-elf-gcc", "esptool_py", "mkspiffs", "mklittlefs"}:
            continue
        tool = next(t for t in package["tools"] if t["name"] == dependency["name"] and t["version"] == dependency["version"])
        systems = [s for s in tool["systems"] if s["host"] in {"x86_64-mingw32", "i686-mingw32"}]
        systems.sort(key=lambda s: s["host"] != "x86_64-mingw32")
        asset = systems[0]
        destination = ROOT / "runtime/arduino-data/packages/esp32/tools" / tool["name"] / tool["version"]
        if destination.exists() and any(destination.rglob("*.exe")):
            continue
        archive = ROOT / "runtime/arduino-downloads/packages" / asset["archiveFileName"]
        download({"url": asset["url"], "size": int(asset["size"]), "sha256": asset["checksum"].split(":", 1)[1]}, archive)
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as source:
            files = [m for m in source.infolist() if not m.is_dir()]
            first = Path(files[0].filename).parts[0]
            strip = all(len(Path(m.filename).parts) > 1 and Path(m.filename).parts[0] == first for m in files)
            for member in files:
                parts = Path(member.filename).parts[int(strip):]
                relative = Path(*parts)
                if relative.is_absolute() or ".." in relative.parts or any(":" in p for p in relative.parts):
                    raise ValueError("Unsafe tool archive path")
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(member) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
        print(f"Installed official tool {tool['name']} {tool['version']}")


def main():
    index = json.loads((ROOT / "runtime/arduino-data/package_esp32_index.json").read_text(encoding="utf-8-sig"))
    package = next(p for p in index["packages"] if p["name"] == "esp32")
    platform = next(p for p in package["platforms"] if p["version"] == "2.0.17")
    install_tools(package, platform)
    archive = ROOT / "runtime/arduino-downloads/packages" / platform["archiveFileName"]
    if not archive.exists():
        from scripts.download_models import download
        download({"url": platform["url"], "size": int(platform["size"]),
                  "sha256": platform["checksum"].split(":", 1)[1]}, archive)
    expected = platform["checksum"].split(":", 1)[1]
    with archive.open("rb") as file:
        actual = hashlib.file_digest(file, "sha256").hexdigest()
    if actual != expected:
        raise ValueError("Official core archive checksum mismatch")
    destination = ROOT / "runtime/arduino-data/packages/esp32/hardware/esp32/2.0.17"
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            parts = Path(member.filename).parts[1:]
            if not parts or member.is_dir():
                continue
            relative = Path(*parts)
            if relative.is_absolute() or ".." in relative.parts or any(":" in p for p in relative.parts):
                raise ValueError("Unsafe archive path")
            if relative.parts[:2] == ("tools", "sdk") and len(relative.parts) > 2 and relative.parts[2] != "esp32":
                continue
            if relative.parts[0] in {"docs", "examples", ".github"}:
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
    print("Verified classic ESP32 Arduino core installed; other chip-family SDKs excluded.")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
