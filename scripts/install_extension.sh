#!/usr/bin/env bash
# Native extension demo setup. Keeps source and existing credentials intact.
set -euo pipefail
cd "$(dirname "$0")/.."
python_bin="${SCENEGUARD_PYTHON:-python3}"
if [ "$(uname -s)" = Darwin ]; then
  major="$(sw_vers -productVersion)"; major="${major%%.*}"
  if [ "$(uname -m)" != arm64 ] || [ "$major" -lt 14 ]; then
    echo 'Pinned native PyTorch requires Apple Silicon and macOS 14+. Use a native Linux backend (REMOTE_SETUP.md) for Intel or older macOS.'; exit 1
  fi
fi
"$python_bin" -c 'import sys; assert sys.version_info[:2] in ((3,11),(3,12)), "Use Python 3.11 or 3.12 (SCENEGUARD_PYTHON may select it)"'
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null || { echo 'Install FFmpeg: brew install ffmpeg (macOS), or apt-get install ffmpeg (Linux).'; exit 1; }
"$python_bin" scripts/initialize_local.py
if [ ! -x .venv/bin/python ]; then "$python_bin" -m venv .venv; fi
export PIP_CACHE_DIR="$PWD/.local/pip-cache"
.venv/bin/python -m pip install -r backend/requirements.txt
if [ "$(uname -s)" = Linux ]; then
  .venv/bin/python -m pip install 'torch==2.14.1+cpu' --index-url https://download.pytorch.org/whl/cpu
else
  .venv/bin/python -m pip install 'torch==2.14.1'
fi
.venv/bin/python -m pip install -r backend/requirements-laya.txt
HF_HUB_DISABLE_XET=1 USE_TF=0 .venv/bin/python scripts/prepare_laya.py
.venv/bin/python -m pip check
