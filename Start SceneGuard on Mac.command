#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$(uname -s)" != Darwin ]; then
  printf '%s\n' 'This launcher is for macOS. On Linux use: bash scripts/start_extension.sh';exit 1
fi
# Docker Desktop may expose its CLI in either of these standard locations.
export PATH="/usr/local/bin:$HOME/.docker/bin:$PATH"
if ! command -v docker >/dev/null 2>&1; then
  printf '%s\n' 'Install Docker Desktop for Mac, launch it, then run this installer again.' 'Official instructions: https://docs.docker.com/desktop/setup/install/mac-install/'
  open 'https://docs.docker.com/desktop/setup/install/mac-install/'
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  printf '%s\n' 'Starting Docker Desktop…'
  open -a Docker
  for ((attempt=1;attempt<=60;attempt++));do
    if docker info >/dev/null 2>&1;then break;fi
    sleep 3
  done
fi
docker info >/dev/null 2>&1 || { printf '%s\n' 'Docker Desktop is not ready. Finish its setup and rerun this launcher.';exit 1; }
export SCENEGUARD_PLATFORM=linux/amd64
export SCENEGUARD_COMPOSE_OVERRIDE=compose.macos.yaml
export SCENEGUARD_USE_DOCKER_PYTHON=1
printf '%s\n' 'Preparing SceneGuard and local Laya. First-time builds and model downloads can take several minutes.'
if [ "$(uname -m)" = arm64 ];then
  printf '%s\n' 'Apple Silicon detected: using the validated x86 Linux stack through Docker emulation. Scanning may be slower.'
fi
bash scripts/start_extension.sh
open 'http://localhost:3000'
open -a 'Google Chrome' 'chrome://extensions' || true
printf '%s\n' 'Next: enable Developer mode in Chrome, choose Load unpacked, and select the extension folder beside this launcher.' 'Open .env locally to read ADMIN_USERNAME and ADMIN_PASSWORD. Do not share that file.' 'Click the SceneGuard toolbar icon while viewing Instagram, connect to http://localhost:8000, upload references and set your duration.'
