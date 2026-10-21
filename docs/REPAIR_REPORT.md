# SceneGuard repair experiment — 21 October 2026

The content matcher now recognizes transformed clips derived from the user's actual uploaded reference, and the deployed workers use real Laya inference. Instagram content identification remains unverified because the accessible public pages supplied no playable candidate footage. This report supersedes the old audio-index and Laya limitations in the historical experiment report.

## What changed

The audio extractor previously fed integer PCM into an adaptive spectral threshold without normalizing its scale. Real AAC music yielded only four landmarks, while synthetic floating-point tests hid the fault. PCM normalization, finite-value validation, silence handling and peak normalization repair this. The real reference now has 28,324 audio landmarks (117.324/s), 121 keyframes, and feature/audio version 3. All 13 previously indexed references/promotional files were reindexed without deleting the original footage or old feature objects. An authenticated reindex endpoint and index-quality endpoint support upgrades from the dashboard.

Visual matching uses crop-aware perceptual hashes and ORB descriptors with homography/RANSAC verification, frame coverage checks and temporal consistency. Audio uses normalized spectral landmark fingerprints and aligned offsets. These test decisions use measured content, not captions or keywords. Optional CLIP embeddings and an external multimodal provider remain unvalidated live and were not used in these results.

The official Laya SDK/model interface was verified, the pinned 842.6 MB weight file was downloaded and SHA-256 verified, and a private CPU model service was deployed. The earlier download restriction was resolved. The service has bearer authentication, read-only weights, no public port and an offline internal network. It reviews structured matcher evidence; it cannot discover posts or replace video/audio comparisons. The decision engine prevents it from promoting weak matches. Missing footage is always `insufficient_evidence`; approved promotional exclusions remain authoritative. Model failure is explicitly recorded with deterministic fallback.

## Actual-reference experiment

Reference: the user's supplied 241.42-second, 426×240 lyric video, privately stored as movie 7 / media 38. SHA-256: `e4c9aa564e0ae9e4dfdce95d30a895ed76ef574da815e2e051a05df369fce31d`.

Four eight-second clips were created from that reference at known offsets. Transformations included a 340×190 crop, rescaling, mild perspective change, H.264 CRF 29 compression, audio gain reduction and additive noise. These are controlled derivatives, **not Instagram recordings** and not a benchmark of arbitrary theatre recordings. Reproduce the local matcher evaluation with `scripts/evaluate_reference.py <authorized-reference-path>`. The private clips and full evidence remain under ignored `.local/` storage.

The clips were then uploaded as explicitly labeled mock candidates and processed by the deployed FastAPI → PostgreSQL/S3 → Redis/Celery → matching → Laya → detection/alert pipeline. The reusable deployed check also asserts duplicate-upload identity, one persisted decision, one alert, the expected movie/timestamp and successful Laya execution:

```bash
.venv/bin/python scripts/validate_candidates.py \
  .local/real-reference-evaluation/report.json --movie-id 7 --require-laya
```

Run this only in the development workspace with alerts enabled and the intended reference active.

| Known offset | Matched offset | Visual score | Audio score | Combined evidence score | Deployed decision | Laya choice |
| --- | --- | --- | --- | --- | --- | --- |
| 30s | 30s | 0.8274 | 0.6558 | 0.8792 | confirmed | confirmed |
| 60s | 60s | 0.8913 | 0.1860 | 0.8913 | confirmed | confirmed |
| 90s | 90s | 0.9026 | 0.4846 | 0.9318 | confirmed | confirmed |
| 150s | 150s | 0.9243 | 0.2789 | 0.9470 | confirmed | confirmed |

The 60-second clip was confirmed through strong geometric video evidence; its noisy audio was below the configured support threshold. A separate unrelated synthetic candidate, compared with only the user's movie active, returned `no_match`, no movie ID, no alert, and a real Laya `no_match` decision. One negative example does not estimate false-positive rates.

See [machine-readable measured results](repair-results.json). Scores are uncalibrated similarities, **not** measured probabilities of a correct match. The SDK's `answer_confidence` is recorded separately from the legacy entropy-based `confidence` field. Laya answer confidence in the four positive cases ranged from 0.3785 to 0.5123; its movie-scene calibration and incremental benefit are not established. A positive choice here does not establish that Laya is production-ready for this domain.

## Verification

- 33 unit/media/private-service tests passed, covering matching, PCM encoding/gain regressions, silent audio, missing-media decisions, Laya contracts/fallback and service authentication/input validation. Seven integration tests are opt-in.
- Six deployed integration tests passed with live Laya enabled: dependency readiness/authentication, positive/negative matching, deduplication, promotional exclusion, RBAC/private storage, durable recovery and unsupported discovery status. A seventh targeted integration test passed for reference reindexing, feature version and audio quality.
- Two browser end-to-end tests passed for authentication, dashboard navigation/library/settings and CSRF/anonymous API rejection.
- A supplemental browser check caught an index-details notice being overwritten in the first frontend build. The source was corrected and the final build/check is recorded below after deployment.

The first service-monitoring attempt overlapped a deliberate frontend deployment and recorded an interruption. A new 600-second run was started after that deployment. Final measured monitoring results appear in the addendum below; neither monitoring run scans all Instagram or proves 24-hour reliability.

## Instagram findings and coverage

Two public reel pages were observed in the earlier limited browser scan: `DcTxhjWiS11` and `DcTbN_gi9Tb`. Their captions/audio labels relate to the supplied reference. Ordinary logged-out page and public-embed playback checks exposed posters but no playable video/audio. Search-engine CAPTCHA challenges were not bypassed. Poster-only comparison did not establish a match and cannot establish absence of the underlying video.

There are therefore **zero verified Instagram content matches**, and no supported conclusion that the video is absent from Instagram. The blocker is accessible candidate media, not demonstrated lack of videos. This is not whole-Instagram discovery. A logged-in account alone would not provide comprehensive coverage or bypass supported API scopes, rate limits and media permissions.

The Instagram/Facebook adapters explicitly report unsupported without an approved integration. YouTube Data API discovery requires a configured key/query or channel and supplies metadata only. No live Meta credentials or approved media-feed connector is configured. To validate an Instagram scene match, supply an authorized candidate reel file through the dashboard, or integrate a platform-approved media source that actually provides candidate bytes within its permitted scope. Credentials belong in protected environment configuration, never chat.

## Startup and scope of completion

```bash
cd /workspace/anti-spoiler
docker compose -f compose.yaml -f compose.laya.yaml up --no-build -d
docker compose -f compose.yaml -f compose.laya.yaml ps
```

Use the dashboard on the environment's port-3000 preview with credentials in protected `.env`. Follow [Laya setup](LAYA.md) for a fresh machine; the prepared environment already contains its image and verified weights. Core tests: `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q`. Deployed integration tests: `bash scripts/integration.sh`. Cloud browser tests: `cd frontend && CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e`.

Working: reference upload/indexing, actual content matching on controlled real footage, queued orchestration/recovery, live structured Laya review, persisted decisions, deduplicated in-app alerts, authenticated dashboard and monitoring. Mocked/limited: fixture sources; unsupported Instagram/Facebook discovery; quota-scoped YouTube metadata; unvalidated optional embeddings/external multimodal service. No reporting or enforcement exists.

This is a working local detection MVP. It is not yet a validated autonomous Instagram monitoring product. Production readiness still needs an authorized candidate feed, representative licensed evaluation data, measured accuracy/throughput, long-duration reliability testing, durable hosting, backups, TLS/operational hardening and appropriate platform permissions.

## Final monitoring result

The uninterrupted run completed in 600.1 seconds with 61 observations: 61 healthy, 0 failures. Final queue depth was 0. API, database, Redis, private storage, worker, scheduler and live Laya remained running. This establishes ten-minute local service stability under the recorded test workload, not whole-Instagram scanning or 24/7 production reliability.

## Final dashboard correction

After the successful monitoring window, the final frontend replacement exposed an intermittent binding fault: Next.js standalone inherited the container hostname and listened on a single interface, while the published port could use another interface. Compose now explicitly sets `HOSTNAME=0.0.0.0`, the Dockerfile sets the same fresh-build default, and a loopback HTTP frontend health check catches this fault. The recreated dashboard returned HTTP 200 externally; an authenticated browser verified media 38 index details show 28,324 landmarks. The notice-overwrite fix is present in the deployed bundle. No backend/model restart was required. The monitoring numbers above describe the completed pre-replacement window, not this subsequent frontend change.

Both browser end-to-end tests were rerun after the binding correction and passed. The final frontend health check is healthy and the Celery worker responded to a live ping.
