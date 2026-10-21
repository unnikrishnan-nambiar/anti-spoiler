# SceneGuard AI

Detection-only movie-scene matching with five testable agents and a minimal black-and-white dashboard. Accepts authorized reference/candidate videos; combines geometric visual evidence and audio fingerprints; excludes approved promotional material; stores deduplicated in-app alerts. No reporting, takedown, authentication bypass, or public-video scraping.

See [measured validation results](docs/VALIDATION.md) and [architecture and phase status](docs/ARCHITECTURE.md) for working components, mocks, score semantics, credentials and production limitations.

## Start

Prerequisites: Docker Engine + Compose v2, Python 3 (for local secret generation). Use the existing checkout; do not create a worktree for cloud tasks.

```bash
cd /workspace/anti-spoiler
python scripts/bootstrap.py
docker compose up --build -d
docker compose ps
```

The prepared cloud deployment includes the verified Laya service and model weights. Restart that configuration with:

```bash
docker compose -f compose.yaml -f compose.laya.yaml up --no-build -d
```

For fresh Laya installation, follow [the verified model setup](docs/LAYA.md). The Movies page supports **Reindex** and **Index details**, including audio landmark counts and feature versions. Old reference indexes should be reindexed before matching candidates with audio fingerprint version 3.

The dashboard listens on loopback port 3000. Sign in as `ADMIN_USERNAME` with the generated `ADMIN_PASSWORD` in the protected `.env` file. Do not share or commit this file. Bootstrap preserves existing files; if you copy `.env.example` manually, fill all secret fields first. Production uses HTTPS ingress and secure cookies; see architecture documentation. No footage or synthetic detections is seeded on startup.

On this cloud machine, builds need the provided proxy CA and DNS mapping. This tested helper preserves certificate verification:

```bash
python scripts/cloud_build.py
docker tag sceneguard-api sceneguard-worker
docker tag sceneguard-api sceneguard-beat
docker tag sceneguard-api sceneguard-init
docker compose up --no-build -d
```

Cloud sandbox permissions may require the coding agent to run the helper with network execution privileges; it uses the already configured proxy, not a separate authentication method.

```bash
# Health and actual worker responsiveness
docker compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health/ready').read().decode())"
docker compose exec -T worker celery -A app.queue.celery inspect ping --timeout 5
# JSON application events, queue errors and discovery state
docker compose logs --tail 100 api worker beat
# Stop processes, retain all volumes
docker compose down
```

Never run `docker compose down -v` unless you intend to delete private footage and database state.

## First detection

1. Add a movie under Movies. Set the spoiler boundary in seconds relative to the uploaded reference.
2. Upload a reference and confirm indexing reaches `ready`.
3. Optionally upload approved promotional footage for exclusion.
4. Upload an **authorized** candidate, select its platform and original HTTPS post URL, and confirm processing rights. Mock fixtures must use `https://example.invalid/...`.
5. Inspect Detections for confirmed, review, no-match or promotional-exclusion decisions and measured evidence. A confirmed detection produces one in-app alert when enabled.

Source uploads accept MP4/MOV, Matroska/WebM, AVI, MPEG/TS with a video stream, up to 500 MiB and two hours by default. References must be indexed before candidates can finish. Larger/full-length libraries need throughput benchmarking and capacity planning.

## Synthetic demonstration and tests

```bash
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python scripts/generate_samples.py
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
cd frontend
npm ci
npm run build
cd ..
# All services must be running; tests create clearly labeled synthetic records.
bash scripts/integration.sh
# Browser tests use generated .env admin credentials without printing them.
cd frontend
npx playwright install chromium
npm run test:e2e
# On this cloud machine Chromium is already installed:
CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e
cd ..
.venv/bin/python scripts/soak.py --seconds 600
# Repeated synthetic candidate jobs (requires indexed synthetic references)
.venv/bin/python scripts/exercise.py --seconds 600
```

The tests generate their own media: crop/zoom/perspective/compression transformations, known audio alignment, unrelated video, and approved promo. There are no prerecorded detection results. Integration tests need a development database, S3 and running Celery worker. E2E tests create one synthetic empty movie. Test data is retained for inspection; repeated integration runs pause prior movies with the reserved `SYNTHETIC integration ` test prefix to isolate fixtures. Tests do not delete footage or reset the database. Do not run integration tests on a production database.

## Platform access

- **YouTube:** enable YouTube Data API v3, configure `YOUTUBE_API_KEY` and `YOUTUBE_QUERY` or `YOUTUBE_CHANNEL_ID` securely in `.env`, then recreate workers. Official Search API discovers metadata only, within a quota-limited scope. It does not provide downloadable video bytes; matching requires authorized media uploads. Normal cadence is ten minutes. Discovery states explain this coverage limit.
- **Instagram / Facebook:** separate adapters report unsupported. No approved connector or platform permission is configured. A public reel URL alone is insufficient to process its bytes. Supply the authorized reel file and matching movie reference through the upload workflow; this is an upload test, not continuous Instagram monitoring.
- **Mock:** deterministic adapter tests supplied fixtures and checkpoints. Generated media/URLs are labeled synthetic.
- **Laya:** verified and running as a private CPU evidence-review service in the prepared deployment. See [setup and limitations](docs/LAYA.md). The base Compose file keeps deterministic-only operation available; enable the Laya override to use real inference.

## Optional AI

For local CLIP embeddings, install `backend/requirements-ai.txt` in a derived backend image, prefetch the model with valid TLS trust, and set `CLIP_MODEL=openai/clip-vit-base-patch32` on every backend process. Mount a writable model cache outside the read-only root filesystem and pre-provision weights. Existing references must be reindexed; this optional path is not part of the default validated deployment.

For ambiguous-match vision review, configure `MULTIMODAL_URL` (full HTTPS OpenAI-compatible chat-completions endpoint), `MULTIMODAL_MODEL`, and `MULTIMODAL_API_KEY`. The service requires JSON `verdict` (`same_scene`, `different_scene`, or `uncertain`) and `reason`; unknown outputs or service failures remain reviewable. It cannot confirm an uncertain match. This sends candidate/reference thumbnails outside your deployment: authorize this data flow first and configure the destination in network policy. Provider integration is unit-tested with a mock, not live credentials.

## Security and operations

Roles: admin, analyst, viewer. Use the admin-only `POST /users` API for additional users; API docs are at `/docs` inside the private API service. Settings expose credential presence, never values. Bearer tokens expire after an hour; logout clears the browser cookie. No self-service password reset/SSO is implemented.

Redis AOF, PostgreSQL and object storage have named volumes; workers and beat restart automatically. API commits a durable pending job before publishing, and beat recovers missing/stale jobs. Read [durability and operational limits](docs/ARCHITECTURE.md) before enabling continuous production use. Alerts are in-app records only; no messages, enforcement actions, or third-party notifications are sent.

Current repair results: real audio indexing is fixed and Laya is deployed. See [the repair experiment report](docs/REPAIR_REPORT.md). The earlier [one-minute Instagram scan](docs/INSTAGRAM-MINUTE.md) found metadata only; no playable Instagram reel has been verified.

## Browser extension with Laya

The [SceneGuard Feed Check extension](extension/README.md) uploads up to five authorized references and runs a user-started visual scan with a configurable 15–600-second duration of playing reels in the active Instagram tab. It sends cropped frames to the backend and compact numeric evidence to local Laya. Model usage, latency, skipped samples and matches are explicit. This is limited browser sampling; it does not enable whole-platform discovery. See [extension validation and limits](docs/EXTENSION.md).

Prepared startup: `docker compose -f compose.yaml -f compose.laya.yaml -f compose.extension.yaml up --no-build -d`. Fresh Linux/WSL setup helper: `bash scripts/start_extension.sh`. Remote Chrome needs a reachable authenticated HTTPS API; its localhost is not this cloud workspace.
