"""Audio/KWS worker isolated from web and LLM scheduling."""
import gc
import json
import queue
import sys
import threading
import time

from .config import ROOT, load_config


def emit(event):
    print(json.dumps(event), flush=True)


def main():
    print("Loading audio libraries", file=sys.stderr, flush=True)
    # Load NumPy before sherpa creates inference threads. On Windows, lazy
    # native DLL loading inside InputStream can otherwise deadlock the loader.
    import numpy
    import sounddevice as sd
    import sherpa_onnx
    cfg = load_config()
    import os
    if os.name == "nt":
        from scripts.windows_audio import resolve_devices
        cfg = resolve_devices(cfg)
    print("Loading keyword detector", file=sys.stderr, flush=True)
    manifest = json.loads((ROOT / "models/manifest.json").read_text(encoding="utf-8"))
    kws_paths = {k: str(ROOT / v) for k, v in manifest["kws"].items()}
    detector = sherpa_onnx.KeywordSpotter(**kws_paths, num_threads=1, provider="cpu",
                                        keywords_score=cfg["kws_score"], keywords_threshold=cfg["kws_threshold"],
                                        num_trailing_blanks=1)
    kws_stream = detector.create_stream()
    commands = queue.Queue(maxsize=16)
    audio = queue.Queue(maxsize=24)  # 1.2 seconds at 50ms; never grows without limit.
    closed = threading.Event()

    def read_commands():
        for line in sys.stdin:
            try:
                commands.put_nowait(json.loads(line))
            except (ValueError, queue.Full):
                continue
        closed.set()

    def callback(samples, frames, timing, status):
        try:
            audio.put_nowait((samples.copy().reshape(-1), bool(status)))
        except queue.Full:
            # Drop the oldest frame, favouring current audio over growing latency.
            try:
                audio.get_nowait()
            except queue.Empty:
                pass
            try:
                audio.put_nowait((samples.copy().reshape(-1), True))
            except queue.Full:
                pass

    threading.Thread(target=read_commands, daemon=True).start()
    recognizer = stream = None
    session = 0
    started = 0
    previous = ""
    overflow_at = 0
    print("Opening microphone stream", file=sys.stderr, flush=True)
    with sd.InputStream(samplerate=cfg["input_rate"], channels=1, dtype="float32",
                        device=cfg["input_device"], blocksize=int(cfg["input_rate"] * 0.05),
                        callback=callback, latency="low"):
        emit({"type": "ready"})
        print("Microphone ready", file=sys.stderr, flush=True)
        while not closed.is_set():
            while not commands.empty():
                command = commands.get_nowait()
                if command["action"] == "listen":
                    session = command["session"]
                    if recognizer is None:
                        paths = {k: str(ROOT / v) for k, v in manifest["stt"].items()}
                        recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                            **paths, num_threads=1, sample_rate=16000, feature_dim=80,
                            decoding_method="greedy_search", provider="cpu", enable_endpoint_detection=True,
                            rule1_min_trailing_silence=cfg["listen_timeout_seconds"],
                            rule2_min_trailing_silence=cfg["endpoint_silence_seconds"],
                            rule3_min_utterance_length=cfg["utterance_limit_seconds"])
                    stream = recognizer.create_stream()
                    previous, started = "", time.monotonic()
                elif command["action"] == "idle":
                    stream = recognizer = None
                    gc.collect()
                elif command["action"] == "close":
                    return
            try:
                samples, overflow = audio.get(timeout=0.2)
            except queue.Empty:
                continue
            if overflow and time.monotonic() - overflow_at > 5:
                emit({"type": "warning", "text": "Audio overflow; reduce LLM threads or check USB audio."})
                overflow_at = time.monotonic()
            kws_stream.accept_waveform(cfg["input_rate"], samples)
            while detector.is_ready(kws_stream):
                detector.decode_stream(kws_stream)
                keyword = detector.get_result(kws_stream)
                if keyword:
                    emit({"type": "keyword", "keyword": keyword})
                    detector.reset_stream(kws_stream)
            if stream is None:
                continue
            stream.accept_waveform(cfg["input_rate"], samples)
            while recognizer.is_ready(stream):
                recognizer.decode_stream(stream)
            text = recognizer.get_result(stream).strip()
            if text != previous:
                emit({"type": "partial", "text": text, "session": session})
                previous = text
            elapsed = time.monotonic() - started
            if recognizer.is_endpoint(stream) or elapsed > cfg["utterance_limit_seconds"] or (not text and elapsed > cfg["listen_timeout_seconds"]):
                emit({"type": "final", "text": text, "session": session})
                stream = recognizer = None
                gc.collect()


if __name__ == "__main__":
    main()
