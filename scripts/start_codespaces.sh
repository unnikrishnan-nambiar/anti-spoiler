#!/usr/bin/env bash
# Provision the backend inside a Codespace selected and created by the user.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${CODESPACE_NAME:-}" ];then
  printf '%s\n' 'Run this script in a GitHub Codespaces terminal, not on your Mac.'
  exit 1
fi
python3 scripts/initialize_local.py
python3 - <<'PY'
import os,re
from pathlib import Path
name=os.environ['CODESPACE_NAME']
domain=os.environ.get('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN','app.github.dev')
if not re.fullmatch('[a-z0-9-]+',name) or not re.fullmatch('[a-z0-9.-]+',domain):raise SystemExit('Invalid Codespaces hostname')
p=Path('.env');lines=[line for line in p.read_text().splitlines() if not line.startswith('APP_ORIGIN=')]
p.write_text('\n'.join(lines)+f'\nAPP_ORIGIN=https://{name}-3000.{domain}\n');p.chmod(0o600)
PY
bash scripts/start_extension.sh
printf '%s\n' 'Backend ready. The API port remains private unless you explicitly change its visibility in the Codespaces Ports panel.'
printf 'Extension API origin: https://%s-8000.%s\n' "$CODESPACE_NAME" "${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
printf '%s\n' 'See REMOTE_SETUP.md for port visibility, login and extension setup. Never share .env.'
