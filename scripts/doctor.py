#!/usr/bin/env python3
import argparse
import hashlib
import importlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jarvis.config import load_config, resolve
from jarvis.metrics import memory_pressure, system_memory


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", action="store_true")
    parser.add_argument("--audio", action="store_true")
    parser.add_argument("--verify-hashes", action="store_true")
    args = parser.parse_args()
    failures = []

    def check(name, fn):
        try:
            detail = fn()
            print(f"PASS {name}: {detail or 'OK'}", flush=True)
        except Exception as exc:
            failures.append(name)
            print(f"FAIL {name}: {exc}", flush=True)

    check("Python", lambda: f"{sys.version.split()[0]} on {platform.machine()}")
    cfg = load_config()
    check("Configuration", lambda: "validated")
    for name in ("aiohttp", "numpy", "sounddevice", "sherpa_onnx", "piper"):
        check(name, lambda name=name: importlib.import_module(name).__name__)
    memory = system_memory()
    if memory:
        check("System memory headroom", lambda: memory_check(memory, cfg))
    if args.models:
        check("Model manifest", lambda: check_manifest())
        check("llama.cpp binary", lambda: binary_check(cfg))
        check("Speech model smoke test", lambda: speech_smoke(cfg))
    if args.verify_hashes:
        check("Model checksums", verify_hashes)
        if (ROOT / "runtime/runtime-checksums.json").exists():
            check("Portable runtime checksums", verify_runtime)
    if args.audio:
        check("Headset capture and playback", lambda: audio_check(cfg))
    if failures:
        print("Fix failures before starting the service: " + ", ".join(failures))
        raise SystemExit(1)
    print("Checks passed. Test real microphone/playback and run benchmark.py on the target computer to validate latency.")


def memory_check(memory, cfg):
    reason = memory_pressure(memory, cfg)
    if reason:
        raise ValueError(reason)
    return f"{memory['used_bytes']/1e9:.2f} GB used; {memory['available_bytes']/1e9:.2f} GB available"


def check_manifest():
    manifest = json.loads((ROOT / "models/manifest.json").read_text(encoding="utf-8"))
    for group in manifest.values():
        for path in group.values():
            if not resolve(path).is_file() or resolve(path).stat().st_size == 0:
                raise ValueError(f"Missing or empty model file: {path}")
    return "KWS/STT files present"


def binary_check(cfg):
    result = subprocess.run([str(resolve(cfg["llama_binary"])), "--help"], capture_output=True, text=True, timeout=20, check=True)
    for flag in ("--jinja", "--no-warmup", "--parallel"):
        if flag not in result.stdout + result.stderr:
            raise ValueError(f"Upstream binary is missing {flag}; try LLAMA_REF=v0.6.0 bash scripts/install.sh")
    if not resolve(cfg["llm_model"]).is_file():
        raise ValueError("GGUF model missing")
    with resolve(cfg["llm_model"]).open("rb") as file:
        if file.read(4) != b"GGUF":
            raise ValueError("The LLM file is not a GGUF")
    return "Server flags and GGUF header checked"


def speech_smoke(cfg):
    import numpy as np
    import sherpa_onnx
    from jarvis.voice import load_voice
    manifest = json.loads((ROOT / "models/manifest.json").read_text(encoding="utf-8"))
    kws = sherpa_onnx.KeywordSpotter(**{k: str(resolve(v)) for k, v in manifest["kws"].items()}, num_threads=1)
    stream = kws.create_stream()
    stream.accept_waveform(16000, np.zeros(8000, dtype=np.float32))
    while kws.is_ready(stream):
        kws.decode_stream(stream)
    del kws, stream
    stt = sherpa_onnx.OnlineRecognizer.from_transducer(
        **{k: str(resolve(v)) for k, v in manifest["stt"].items()}, num_threads=1,
        enable_endpoint_detection=True, rule2_min_trailing_silence=cfg["endpoint_silence_seconds"])
    stream = stt.create_stream()
    stream.accept_waveform(16000, np.zeros(8000, dtype=np.float32))
    while stt.is_ready(stream):
        stt.decode_stream(stream)
    del stt, stream
    voice = load_voice(resolve(cfg["voice_model"]))
    chunks = list(voice.synthesize("Hello."))
    if not chunks or not chunks[0].audio_int16_bytes:
        raise ValueError("Piper produced no audio")
    return "KWS/STT silent frames and Piper speech generated offline"


def audio_check(cfg):
    import sounddevice as sd
    if sys.platform == "win32":
        from scripts.windows_audio import resolve_devices
        cfg = resolve_devices(cfg)
    sd.check_input_settings(device=cfg["input_device"], channels=1, dtype="float32", samplerate=cfg["input_rate"])
    rate = sd.query_devices(cfg["output_device"], "output")["default_samplerate"]
    sd.check_output_settings(device=cfg["output_device"], channels=1, dtype="int16", samplerate=rate)
    with sd.InputStream(device=cfg["input_device"], samplerate=cfg["input_rate"], channels=1) as microphone:
        microphone.read(int(cfg["input_rate"] * 0.1))
    return "Input opened; Piper-rate output format supported"


def verify_hashes():
    hashes = json.loads((ROOT / "models/installed.sha256.json").read_text(encoding="utf-8"))
    for path, expected in hashes.items():
        if digest(resolve(path)) != expected:
            raise ValueError(f"Checksum mismatch: {path}; rerun download_models.py")
    return f"{len(hashes)} assets verified"


def verify_runtime():
    hashes = json.loads((ROOT / "runtime/runtime-checksums.json").read_text(encoding="utf-8"))
    for path, expected in hashes.items():
        if digest(resolve(path)) != expected:
            raise ValueError(f"Runtime binary checksum mismatch: {path}")
    return f"{len(hashes)} runtime binaries verified"


if __name__ == "__main__":
    main()
