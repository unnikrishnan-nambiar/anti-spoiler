#!/usr/bin/env bash
# Local Docker setup. Downloads the verified Laya model on first use.
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v docker >/dev/null; then
  if [ -n "${CODESPACE_NAME:-}" ];then
    printf '%s\n' 'Docker is missing in this Codespace. Run Codespaces: Rebuild Container to apply .devcontainer/devcontainer.json; Docker Desktop is not needed on your Mac.'
  else
    printf '%s\n' 'Install a compatible Docker runtime on this machine, or use REMOTE_SETUP.md to run the backend in Codespaces.'
  fi
  exit 1
fi
docker compose version >/dev/null
docker info >/dev/null
compose=(docker compose -f compose.yaml -f compose.laya.yaml -f compose.extension.yaml)
platform_args=()
if [ -n "${SCENEGUARD_COMPOSE_OVERRIDE:-}" ]; then compose+=(-f "$SCENEGUARD_COMPOSE_OVERRIDE"); fi
if [ -n "${SCENEGUARD_PLATFORM:-}" ]; then platform_args+=(--platform "$SCENEGUARD_PLATFORM"); fi
if [ "${SCENEGUARD_USE_DOCKER_PYTHON:-0}" = 1 ] || ! command -v python3 >/dev/null; then
  docker run --rm "${platform_args[@]}" --user "$(id -u):$(id -g)" \
    -v "$PWD:/work" -w /work python:3.12-slim python scripts/initialize_local.py
else
  python3 scripts/initialize_local.py
fi
mkdir -p .local/models/laya .local/huggingface
"${compose[@]}" build
if [ ! -f .local/models/laya/provenance.json ]; then
  docker run --rm "${platform_args[@]}" --user "$(id -u):$(id -g)" \
    -e HF_HUB_DISABLE_XET=1 -e USE_TF=0 -e HF_HOME=/work/.local/huggingface \
    -v "$PWD:/work" -w /work --entrypoint python sceneguard-laya scripts/prepare_laya.py
fi
"${compose[@]}" up --no-build -d
printf '%s\n' 'Waiting for local API and Laya readiness…'
ready=0
for ((attempt=1; attempt<=180; attempt++)); do
  if "${compose[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready',timeout=3)" >/dev/null 2>&1; then ready=1;break;fi
  if (( attempt % 6 == 0 )); then printf '%s\n' 'Services are still starting; model loading can take several minutes.';fi
  sleep 5
done
if [ "$ready" != 1 ]; then
  printf '%s\n' 'Startup did not reach readiness. Inspect: docker compose -f compose.yaml -f compose.laya.yaml -f compose.extension.yaml logs --tail=50 api laya'
  exit 1
fi
printf '%s\n' 'SceneGuard API: http://localhost:8000' 'SceneGuard dashboard: http://localhost:3000' 'Use the SceneGuard credentials in protected .env; do not enter Instagram credentials.'
