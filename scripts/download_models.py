#!/usr/bin/env python3
"""Install pinned assets; checksum large files; retry and resume downloads."""
import hashlib
import json
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def valid(path, asset):
    return path.exists() and path.stat().st_size == asset["size"] and (not asset.get("sha256") or checksum(path) == asset["sha256"])


def download(asset, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if valid(path, asset):
        print(f"Verified {path.relative_to(ROOT)}", flush=True)
        return
    part = path.with_suffix(path.suffix + ".part")
    for attempt in range(4):
        try:
            offset = part.stat().st_size if part.exists() else 0
            if offset >= asset["size"]:
                part.unlink()
                offset = 0
            headers = {"User-Agent": "offline-jarvis-installer/1.0"}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            request = urllib.request.Request(asset["url"], headers=headers)
            with urllib.request.urlopen(request, timeout=60) as response:
                append = offset > 0 and response.status == 206
                if append and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                    raise ValueError("Download server returned an unexpected resume range")
                print(f"Downloading {path.name} ({asset['size']/1e6:.1f} MB)", flush=True)
                with part.open("ab" if append else "wb") as f:
                    while chunk := response.read(1024 * 1024):
                        f.write(chunk)
            if not valid(part, asset):
                part.unlink(missing_ok=True)
                raise ValueError(f"Size or checksum mismatch: {path.name}")
            part.replace(path)
            return
        except (OSError, urllib.error.URLError, ValueError) as exc:
            print(f"Attempt {attempt + 1}: {exc}", file=sys.stderr)
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def write_keywords(directory):
    # This model uses ARPAbet phones, not English characters or BPE tokens.
    phrases = {
        "WAKE": ["HH EY1 JH AA1 R V AH0 S", "HH EY1 JH AA1 R V IH0 S", "HH EY1 JH AA1 R V IH1 S"],
        "STOP": ["OW2 K EY1 S T AA1 P", "OW0 K EY1 S T AA1 P", "OW1 K EY1 S T AA1 P", "S T AA1 P T AO1 K IH0 NG"],
        "EXIT": ["EH1 G Z IH0 T", "EH1 K S IH0 T", "EH1 G Z IH1 T", "EH1 K S IH1 T"]
    }
    tokens = {line.rsplit(" ", 1)[0] for line in (directory / "tokens.txt").read_text(encoding="utf-8").splitlines()}
    lines = []
    for label, variants in phrases.items():
        for phones in variants:
            missing = set(phones.split()) - tokens
            if missing:
                raise ValueError(f"Wake model is missing phonemes: {missing}")
            lines.append(f"{phones} @{label}")
    (directory / "keywords.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    lock = json.loads((ROOT / "models.lock.json").read_text(encoding="utf-8"))
    model_root = ROOT / "models"
    for asset in lock["files"]:
        download(asset, model_root / asset["target"])
    archive = model_root / "kws.tar.bz2"
    download(lock["kws_archive"], archive)
    kws = model_root / "kws"
    kws.mkdir(exist_ok=True)
    wanted = {"tokens.txt", "en.phone", "encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx",
              "decoder-epoch-13-avg-2-chunk-8-left-64.onnx", "joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx"}
    found = set()
    with tarfile.open(archive, "r:bz2") as tar:
        for member in tar:
            name = Path(member.name).name
            if name not in wanted or not member.isfile():
                continue
            if member.size > 8000000:
                raise ValueError("Unexpectedly large wake model asset")
            source = tar.extractfile(member)
            with (kws / name).open("wb") as dest:
                while chunk := source.read(1024 * 1024):
                    dest.write(chunk)
            found.add(name)
    if found != wanted:
        raise ValueError(f"Incomplete wake archive: missing {wanted - found}")
    write_keywords(kws)
    manifest = {"kws": {"encoder": "models/kws/encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx",
                        "decoder": "models/kws/decoder-epoch-13-avg-2-chunk-8-left-64.onnx",
                        "joiner": "models/kws/joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx",
                        "tokens": "models/kws/tokens.txt", "keywords_file": "models/kws/keywords.txt"},
                "stt": {"encoder": "models/stt/encoder.int8.onnx",
                        "decoder": "models/stt/decoder.onnx",
                        "joiner": "models/stt/joiner.int8.onnx",
                        "tokens": "models/stt/tokens.txt"}}
    (model_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # Record checksums for small pinned metadata too, for offline doctor checks.
    paths = [model_root / asset["target"] for asset in lock["files"]]
    paths += [kws / name for name in wanted] + [kws / "keywords.txt"]
    hashes = {str(p.relative_to(ROOT)).replace("\\", "/"): checksum(p) for p in paths}
    (model_root / "installed.sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print("All model files verified. Runtime needs no internet.")


if __name__ == "__main__":
    main()
