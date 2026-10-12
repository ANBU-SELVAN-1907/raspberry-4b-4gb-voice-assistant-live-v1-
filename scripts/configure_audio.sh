#!/usr/bin/env bash
set -Eeuo pipefail
if [[ "$EUID" -eq 0 ]]; then printf 'Run as your normal user.\n' >&2; exit 1; fi
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then printf 'Run install.sh first.\n' >&2; exit 1; fi
printf '\nCapture devices:\n'
arecord -l
printf '\nPlayback devices:\n'
aplay -l
"$ROOT/.venv/bin/python" "$ROOT/scripts/configure_audio.py" "$@"
printf '\nAudio setup saved. Verify both directions:\n  bash scripts/audio_test.sh\n'
