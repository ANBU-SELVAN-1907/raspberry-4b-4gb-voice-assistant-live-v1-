import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
hashes = {}
for directory in ("runtime/python", "runtime/flasher", "vendor/windows"):
    for path in (ROOT / directory).rglob("*"):
        if path.is_file() and path.suffix.lower() in {".exe", ".dll", ".pyd", ".zip"}:
            with path.open("rb") as file:
                hashes[path.relative_to(ROOT).as_posix()] = hashlib.file_digest(file, "sha256").hexdigest()
(ROOT / "runtime/runtime-checksums.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
print(f"Recorded {len(hashes)} portable runtime binary checksums")
