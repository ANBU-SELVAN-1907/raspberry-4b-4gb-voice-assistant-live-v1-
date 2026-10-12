#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
printf '=== Offline assets and device checks ===\n'
.venv/bin/python scripts/doctor.py --models --verify-hashes
printf '\n=== Service memory cap ===\n'
systemctl show jarvis -p MemoryCurrent -p MemoryPeak -p MemoryMax -p MemorySwapMax -p ActiveState -p SubState
printf '\n=== Cgroup and filtering support ===\n'
stat -fc %T /sys/fs/cgroup
journalctl -u jarvis -n 20 --no-pager
printf '\nManual acceptance (record results in docs/ACCEPTANCE.md):\n'
printf '1. Disconnect the internet, keeping your SSH link. Wake and ask three questions.\n'
printf '2. Say okay stop while talking. Check playback and generation stop.\n'
printf '3. Repeat twenty turns. Record first-audio times and MemoryPeak.\n'
printf '4. Say exit. Service must become inactive without restarting.\n'
