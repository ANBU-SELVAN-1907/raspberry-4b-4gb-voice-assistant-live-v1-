#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if systemctl is-active --quiet jarvis; then
  printf 'Stop Jarvis before testing: sudo systemctl stop jarvis\n' >&2; exit 1
fi
mkdir -p run
printf 'Speak for five seconds now. Then listen to your recording in the headset.\n'
arecord -D default -f S16_LE -r 48000 -c 1 -d 5 run/mic-test.wav
aplay -D default run/mic-test.wav
printf '\nTesting offline Piper speech…\n'
.venv/bin/python -c 'import wave; from jarvis.voice import load_voice; v=load_voice("models/tts/en_US-lessac-low.onnx"); f=wave.open("run/voice-test.wav","wb"); v.synthesize_wav("Hello. I am Jarvis. Your offline headset is ready.",f); f.close()'
aplay -D default run/voice-test.wav
printf 'Adjust capture/playback levels with alsamixer -c <card ID> if needed.\n'
