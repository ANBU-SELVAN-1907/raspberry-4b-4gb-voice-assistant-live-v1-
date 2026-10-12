"""Disposable Piper worker. NDJSON PCM stream; no audio files or network."""
import base64
import json
import sys


def emit(event):
    print(json.dumps(event), flush=True)


def main():
    from piper import SynthesisConfig
    from .config import load_config, resolve
    from .voice import load_voice
    config = load_config()
    voice = load_voice(resolve(config["voice_model"]))
    emit({"ready": True})
    for line in sys.stdin:
        text = json.loads(line)["text"][:240]
        for chunk in voice.synthesize(text, syn_config=SynthesisConfig(length_scale=0.95)):
            pcm = chunk.audio_int16_bytes
            for start in range(0, len(pcm), 2048):
                emit({"rate": chunk.sample_rate, "pcm": base64.b64encode(pcm[start:start+2048]).decode("ascii")})
        emit({"done": True})


if __name__ == "__main__":
    main()
