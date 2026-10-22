#!/usr/bin/env bash
# Start the installed native demo in the foreground. No container runtime needed.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ] || [ ! -f .local/models/laya/provenance.json ]; then
  bash scripts/install_extension.sh
fi
exec .venv/bin/python scripts/run_extension.py "$@"
