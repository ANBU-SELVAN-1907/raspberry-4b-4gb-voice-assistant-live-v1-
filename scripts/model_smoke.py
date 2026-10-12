#!/usr/bin/env python3
"""Real synthetic-audio checks, with no microphone or network calls."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def speech():
    import numpy as np
    import sherpa_onnx
    from piper import SynthesisConfig
    from jarvis.config import load_config, resolve
    from jarvis.voice import load_voice
    cfg = load_config()
    voice = load_voice(resolve(cfg["voice_model"]))
    manifest = json.loads((ROOT / "models/manifest.json").read_text(encoding="utf-8"))
    detector = sherpa_onnx.KeywordSpotter(
        **{k: str(resolve(v)) for k, v in manifest["kws"].items()}, num_threads=1,
        keywords_score=cfg["kws_score"], keywords_threshold=cfg["kws_threshold"], num_trailing_blanks=1)
    results = {}
    failures = []
    for phrase, expected in (("Hey Jarvis", "WAKE"), ("Okay stop", "STOP"), ("Exit", "EXIT")):
        stream = detector.create_stream()
        heard = []
        chunks = list(voice.synthesize(phrase, syn_config=SynthesisConfig(noise_scale=0, noise_w_scale=0)))
        rate = chunks[0].sample_rate
        pcm = np.concatenate([c.audio_float_array for c in chunks] + [np.zeros(rate, dtype=np.float32)])
        for start in range(0, len(pcm), int(rate * 0.05)):
            stream.accept_waveform(rate, pcm[start:start+int(rate * 0.05)])
            while detector.is_ready(stream):
                detector.decode_stream(stream)
                result = detector.get_result(stream)
                if result:
                    heard.append(result)
                    detector.reset_stream(stream)
        if expected not in heard:
            failures.append(f"{phrase} -> {heard}; expected {expected}")
        results[phrase] = heard
    recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
        **{k: str(resolve(v)) for k, v in manifest["stt"].items()}, num_threads=1,
        enable_endpoint_detection=True, rule2_min_trailing_silence=0.55)
    stream = recognizer.create_stream()
    chunks = list(voice.synthesize("What is the capital of France?", syn_config=SynthesisConfig(noise_scale=0, noise_w_scale=0)))
    rate = chunks[0].sample_rate
    pcm = np.concatenate([c.audio_float_array for c in chunks] + [np.zeros(rate, dtype=np.float32)])
    for start in range(0, len(pcm), int(rate * 0.05)):
        stream.accept_waveform(rate, pcm[start:start+int(rate * 0.05)])
        while recognizer.is_ready(stream):
            recognizer.decode_stream(stream)
    stream.input_finished()
    while recognizer.is_ready(stream):
        recognizer.decode_stream(stream)
    transcript = recognizer.get_result(stream)
    if "france" not in transcript.lower() or "capital" not in transcript.lower():
        raise AssertionError(f"STT synthetic test failed: {transcript}")
    results["stt"] = transcript
    print(json.dumps(results, indent=2))
    if failures:
        raise AssertionError("Synthetic wake tests failed: " + "; ".join(failures))
    return results


async def llm(binary):
    import aiohttp
    from jarvis.config import load_config
    from jarvis.engine import Engine
    cfg = load_config()
    cfg["llama_binary"] = binary
    async with aiohttp.ClientSession(trust_env=False) as http:
        engine = Engine(cfg, http)
        try:
            tokens = [piece async for piece in engine.tokens("What is the capital of France? Answer in one sentence.", [], [], [])]
            answer = "".join(tokens)
            if "paris" not in answer.lower():
                raise AssertionError(f"LLM smoke failed: {answer}")
            print("Offline llama.cpp reply:", answer)
            return answer
        finally:
            await engine.stop()


async def tts_protocol():
    from jarvis.engine import terminate
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "jarvis.tts_worker", cwd=ROOT,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
    try:
        ready = json.loads(await asyncio.wait_for(process.stdout.readline(), 30))
        if not ready.get("ready"):
            raise AssertionError("TTS worker did not become ready")
        process.stdin.write(b'{"text":"Hello. Your offline voice is ready."}\n')
        await process.stdin.drain()
        samples = 0
        while True:
            event = json.loads(await asyncio.wait_for(process.stdout.readline(), 30))
            if event.get("done"):
                break
            if event.get("rate") != 16000 or not event.get("pcm"):
                raise AssertionError("Invalid TTS PCM frame")
            samples += 1
        if samples < 1:
            raise AssertionError("TTS worker produced no PCM")
        print(f"Piper subprocess protocol: {samples} PCM frames")
        return samples
    finally:
        await terminate(process)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--llama-binary", help="Optional native server binary for a real LLM check")
    args = parser.parse_args()
    report = {"speech": speech()}
    report["tts_protocol_frames"] = asyncio.run(tts_protocol())
    if args.llama_binary:
        report["llm"] = asyncio.run(llm(args.llama_binary))
    (ROOT / "run/model-smoke.json").write_text(json.dumps(report, indent=2) + "\n")
