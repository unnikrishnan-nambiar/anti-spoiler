#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${CODESPACE_NAME:-}" ]; then echo 'Run this script in a GitHub Codespaces terminal.'; exit 1; fi
printf '%s\n' 'Native backend only; keep port 8001 private.' 'Use the HTTPS forwarded address for port 8000 in your extension. Port visibility is your choice in the Ports panel.'
exec bash scripts/start_extension.sh
