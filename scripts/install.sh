#!/usr/bin/env bash
set -Eeuo pipefail
trap 'printf "Installation failed at line %s. Fix the reported error and rerun this script.\n" "$LINENO" >&2' ERR
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ "$EUID" -eq 0 ]]; then
  printf 'Run as your normal Pi user, not with sudo. The script uses sudo where needed.\n' >&2
  exit 1
fi
if [[ "$(uname -m)" != aarch64 ]]; then
  printf 'Install Raspberry Pi OS Lite 64-bit (Bookworm or Trixie) first. ARM32 is unsupported.\n' >&2
  exit 1
fi
if [[ "$ROOT" == *' '* || "$ROOT" == *'%'* || "$ROOT" == *'"'* || "$ROOT" == *\\* ]]; then
  printf 'Clone into a simple path such as ~/jarvis; spaces and special characters are unsupported in the service path.\n' >&2
  exit 1
fi
if [[ $(df --output=avail -B1 "$ROOT" | tail -n 1) -lt 5000000000 ]]; then
  printf 'Keep at least 5 GB free for dependencies, models and the source build.\n' >&2
  exit 1
fi
sudo apt-get update
sudo apt-get install -y git cmake ninja-build build-essential python3-venv python3-dev libportaudio2 libasound2-dev alsa-utils libespeak-ng1 ca-certificates curl
python3 -c 'import sys; assert (3,11) <= sys.version_info[:2] <= (3,13), "Use Python 3.11, 3.12 or 3.13"'
# Rebuild for Linux ARM64 even when the folder was copied from Windows.
python3 -m venv --clear .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
mkdir -p vendor models data/knowledge run
if [[ ! -f config.json ]]; then cp config.example.json config.json; fi
.venv/bin/python scripts/download_models.py
if [[ ! -f data/knowledge/assistant.md ]]; then cp knowledge_examples/assistant.md data/knowledge/assistant.md; fi
.venv/bin/python scripts/index_knowledge.py
# Resolve latest stable upstream at install time; record the exact tag/commit.
LLAMA_REF="${LLAMA_REF:-$(.venv/bin/python -c 'import json,urllib.request; print(json.load(urllib.request.urlopen("https://api.github.com/repos/ggml-org/llama.cpp/releases/latest",timeout=30))["tag_name"])')}"
if [[ ! "$LLAMA_REF" =~ ^[a-zA-Z0-9._-]+$ ]]; then printf 'Invalid LLAMA_REF\n' >&2; exit 1; fi
if [[ ! -d vendor/llama.cpp/.git ]]; then
  git clone --depth 1 --branch "$LLAMA_REF" https://github.com/ggml-org/llama.cpp.git vendor/llama.cpp
else
  if [[ "$(git -C vendor/llama.cpp remote get-url origin)" != 'https://github.com/ggml-org/llama.cpp.git' ]]; then
    printf 'Unexpected llama.cpp origin; refusing to change it.\n' >&2; exit 1
  fi
  git -C vendor/llama.cpp fetch --depth 1 origin "refs/tags/$LLAMA_REF"
  git -C vendor/llama.cpp checkout --detach FETCH_HEAD
fi
# Pi 4 Cortex-A72: ARMv8-A NEON; no dotprod/i8mm assumption, no GPU backend.
cmake -S vendor/llama.cpp -B vendor/llama.cpp/build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=armv8-a -DGGML_OPENMP=ON \
  -DGGML_BLAS=OFF -DGGML_VULKAN=OFF -DLLAMA_CURL=OFF \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=ON -DLLAMA_BUILD_SERVER=ON
# One build job limits memory pressure; this step can take quite a while on Pi 4.
cmake --build vendor/llama.cpp/build --parallel 1 --target llama-server llama-cli llama-bench
printf '%s\n' "$LLAMA_REF" > run/llama-release.txt
git -C vendor/llama.cpp rev-parse HEAD > run/llama-commit.txt
.venv/bin/python -m pip freeze > run/python-versions.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/doctor.py --models
printf '\nInstalled. Next: bash scripts/configure_audio.sh, then bash scripts/service.sh install\n'
