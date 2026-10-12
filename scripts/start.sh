#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if systemctl is-active --quiet jarvis; then printf 'Jarvis service is already running.\n' >&2; exit 1; fi
exec .venv/bin/python -m jarvis.app "$@"
