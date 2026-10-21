#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$(uname -s)" != Darwin ]; then
  printf '%s\n' 'This launcher is for macOS. On Linux use: bash scripts/start_extension.sh';exit 1
fi
macos_version="$(sw_vers -productVersion)"
docker_install_page='https://docs.docker.com/desktop/setup/install/mac-install/'
case "$macos_version" in
  12.*)
    docker_install_page='https://docs.docker.com/desktop/release-notes/#4412'
    printf '%s\n' 'macOS Monterey detected. Current Docker Desktop cannot run on this OS.' 'Docker Desktop 4.41.2 predates the macOS 13.3 minimum in 4.42. It is now unsupported; prefer a macOS upgrade if your Mac supports it.'
    ;;
esac
# Detect an already downloaded app whose own declared minimum exceeds this OS.
if [ -f /Applications/Docker.app/Contents/Info.plist ]; then
  required_os="$(/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' /Applications/Docker.app/Contents/Info.plist 2>/dev/null || true)"
  current_major="${macos_version%%.*}";required_major="${required_os%%.*}"
  if [[ "$required_major" =~ ^[0-9]+$ ]] && [ "$current_major" -lt "$required_major" ]; then
    printf '%s\n' "The installed Docker.app requires macOS $required_os; this Mac runs $macos_version." 'Install a compatible Docker version or upgrade macOS before running SceneGuard.' "$docker_install_page"
    open "$docker_install_page"
    exit 1
  fi
fi
# Docker Desktop may expose its CLI in either of these standard locations.
export PATH="/usr/local/bin:$HOME/.docker/bin:$PATH"
if ! command -v docker >/dev/null 2>&1; then
  printf '%s\n' 'Install Docker Desktop for Mac, launch it, then run this installer again.' "Official instructions: $docker_install_page"
  open "$docker_install_page"
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
