#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ACTION="${1:-install}"
case "$ACTION" in
  install)
    if [[ "$EUID" -eq 0 ]]; then printf 'Run as your normal user.\n' >&2; exit 1; fi
    .venv/bin/python scripts/doctor.py --models --audio
    .venv/bin/python scripts/write_service.py > run/jarvis.service
    sudo install -m 644 run/jarvis.service /etc/systemd/system/jarvis.service
    sudo systemctl daemon-reload
    sudo systemctl enable --now jarvis
    sleep 3
    systemctl --no-pager --full status jarvis
    printf '\nOn the laptop: ssh -N -L 8765:127.0.0.1:8765 YOUR_USER@YOUR_PI\nOpen http://127.0.0.1:8765 on the laptop.\n'
    ;;
  start|stop|restart) sudo systemctl "$ACTION" jarvis ;;
  status) systemctl --no-pager --full status jarvis ;;
  logs) journalctl -u jarvis -n 80 --no-pager ;;
  uninstall)
    sudo systemctl disable --now jarvis
    sudo rm -- /etc/systemd/system/jarvis.service
    sudo systemctl daemon-reload
    ;;
  *) printf 'Use install, start, stop, restart, status, logs, or uninstall\n' >&2; exit 1 ;;
esac
