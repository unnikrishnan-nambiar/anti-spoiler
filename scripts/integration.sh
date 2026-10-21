#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Use the checkout's exact tests even when the running image was built earlier.
docker compose exec -T api python -c "import pathlib,sys; pathlib.Path('/tmp/sceneguard-test-integration.py').write_bytes(sys.stdin.buffer.read())" < backend/tests/test_integration.py
docker compose exec -T -e RUN_INTEGRATION=1 api python -m pytest /tmp/sceneguard-test-integration.py -q -p no:cacheprovider --basetemp=/tmp/sceneguard-integration
