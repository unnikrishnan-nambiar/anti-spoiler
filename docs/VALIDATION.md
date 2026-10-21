> Historical baseline: see [the repair report](REPAIR_REPORT.md) for the current audio v3, live Laya deployment, expanded tests and actual-reference results.

# Validation results — 21 October 2026

The SceneGuard MVP was built and deployed in this cloud machine using Docker Compose. The API, dashboard, PostgreSQL/pgvector, Redis, private S3-compatible SeaweedFS, Celery worker and scheduler remain running. The five agents are independently testable classes orchestrated by the workers; they are not five separate remote deployments.

## Completed checks

| Check | Result |
|---|---|
| Unit and real-media tests | 25 passed |
| Real-service integration | 6 passed |
| Browser end-to-end | 2 passed |
| Next.js production build | Passed |
| Python core dependency audit | No known vulnerabilities found |
| Frontend dependency audit | Zero reported vulnerabilities |
| Ten-minute service-health observation | 600.03 seconds; 61 observations; zero failures |
| Ten-minute repeated pipeline workload | 600.00 seconds; ten completed synthetic jobs; zero failures |
| Final job state | 12 indexed media objects; 25 completed candidates; none failed, processing or pending |
| Final observed agent errors | None |

Six integration cases deliberately skip in the standalone unit-test command, and were then executed separately against the actual PostgreSQL, Redis, S3 and Celery services. These skips are not counted as passes. Browser checks cover login/logout, navigation, movie creation, settings, anonymous access rejection, and CSRF Origin rejection. The CI workflow is supplied but has not been run on GitHub.

The integration pipeline verifies actual upload, FFmpeg decoding, indexing, visual/audio matching, approved-promo exclusion, unrelated-video rejection, unique alerts, duplicate upload reuse, private object access, viewer restrictions, explicit unsupported platform status and DB recovery after lost queue publication.

The soak alternates the transformed clip and a generated test-pattern clip. The test-pattern clip had itself been indexed during the durable-job recovery test, so identifying it later is an expected reference match. Five soak decisions were promotional exclusions and five were matches to that indexed synthetic reference. This is a processing/deduplication/stability exercise, not a blind classification-accuracy benchmark. The unrelated-video negative check executes before that additional reference is indexed.

## Failures diagnosed and corrected

An initial workload exposed an OpenCV exception when a homography returned zero geometric inliers against an unrelated promotional reference. The matcher now treats this as zero evidence, with a dedicated regression test. Recovery scans could also overlap task retries; processing now enforces a durable attempt bound and respects backoff. Earlier failed synthetic jobs were explicitly retried and completed after the fix. The successful ten-minute run began after these fixes and deployment validation.

The audio matcher now estimates an adaptive spectral noise floor and quantizes landmark time differences. A separate regression verifies six-second alignment with added broadband noise. This does not establish accuracy on arbitrary theatrical recordings. Fingerprint v2 mismatches are explicit; older audio indexes need reindexing for audio support.

The cloud's VFS Docker driver duplicated image layers and exhausted disk during repeated builds. Disposable build caches and superseded images were removed; volumes, secrets, source and footage were preserved. The local audited backend image was compacted and redeployed. Normal reproducible Dockerfiles remain in the repository. The final deployment has approximately eight GiB of free workspace disk.

## Scope that remains external or unverified

The user-supplied reel `https://www.instagram.com/reel/DcTxhjWiS11/` and original `https://youtu.be/hIHUeuw2yj8` are recorded as awaiting authorized media. No reel file or reference file was supplied, and there is no approved Instagram media connector. Their relationship, movie identity, timestamps and confidence have not been verified. No detection was created for these URLs.

Instagram and Facebook discovery explicitly report unsupported. YouTube's supported adapter uses the official metadata Search API and needs a Data API key and query/channel scope; no live YouTube credential was configured. None of these adapters downloads public video bytes.

Laya has no verified exact model/interface. The optional local CLIP path and external multimodal provider have not been exercised with real weights/credentials; the latter is contract-tested with a mock. Their optional dependency set is not included in the core dependency audit. The default validated decision path is deterministic. Similarity values are evidence scores, not calibrated probabilities.

This is a local MVP deployment, not a public production launch or a 24/7 reliability certification. HTTPS ingress, encrypted production storage, managed secrets, backups, capacity testing and a representative authorized evaluation corpus are deployment prerequisites. Saved cloud configuration is a draft: review/save it in environment settings and publish the environment to retain a reusable snapshot. A new-task restoration has not been independently tested.

Full measured observations are in [validation-run.json](validation-run.json). Representative, computed synthetic decisions are in [the sample dataset](../sample-data/observed-synthetic-detections.json).

## Commands

```bash
cd /workspace/anti-spoiler
# Restart the prepared local deployment; images and .env already exist.
docker compose up --no-build -d
docker compose ps

# Repeat validation against development data only.
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
bash scripts/integration.sh
(cd frontend && CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e)
.venv/bin/python scripts/soak.py --seconds 600
.venv/bin/python scripts/exercise.py --seconds 600
```

See the [README](../README.md) for a fresh build, credential setup, upload workflow and operational limitations. Synthetic test records remain visible for inspection.
