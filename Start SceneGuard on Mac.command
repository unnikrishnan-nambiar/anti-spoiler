#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$(uname -s)" != Darwin ]; then
  printf '%s\n' 'This launcher is for macOS. On Linux use: bash scripts/start_extension.sh'; exit 1
fi
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if command -v python3.12 >/dev/null; then export SCENEGUARD_PYTHON=python3.12; fi
printf '%s\n' 'Starting native Python / FFmpeg / local Laya demo.' 'First setup downloads dependencies and verified weights.' 'Keep this terminal open. Ctrl-C stops the demo.' 'Load the extension folder in Chrome and use API address http://localhost:8000.'
bash scripts/start_extension.sh
