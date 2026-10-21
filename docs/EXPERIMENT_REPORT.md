> Historical report: the subsequent [repair experiment](REPAIR_REPORT.md) supersedes the audio-index and Laya deployment limitations below. Instagram media access remains unresolved.

# SceneGuard AI experiment report

Date: 21 October 2026. User-facing run times below are in India Standard Time (UTC+05:30).

## Overall finding

The experiment demonstrated a local development MVP and successful matching on controlled synthetic material. It did **not** demonstrate recognition of the uploaded video inside an Instagram reel. Two related public reel pages were observed, but no playable reel video/audio was available for end-to-end comparison. Laya's documented SDK interface was verified and an optional adapter was implemented; model inference did not succeed because the weights download was blocked.

The ten-minute run was a synthetic processing/stability test, **not ten minutes of Instagram video matching**. A separate public-browser Instagram scan ran for one minute.

## Objective

Find portions of a user-supplied reference video on Instagram using content-based visual/audio matching, with structured evidence optionally reviewed by Laya. The broader product goal includes continuous authorized discovery, private reference storage, decisions, monitoring and alerts. No reporting, takedowns or other enforcement actions were implemented or performed.

## Reference and snippets

The uploaded file was named “Ala Bolelo – Lyric Video / Jailer 2 … 240P.mp4.” The title is user-provided metadata, not independent proof of its identity or ownership.

| Property | Measured result |
|---|---|
| File size | 11,247,752 bytes |
| Duration | 241.416667 seconds |
| Video | H.264, 426 × 240 |
| Audio | AAC, stereo, 44.1 kHz |
| Private library media ID | 38 |
| Indexed keyframes | 121 |
| Stored audio landmarks | 4 |
| Feature/audio schema | Version 2 |

Source SHA-256: `e4c9aa564e0ae9e4dfdce95d30a895ed76ef574da815e2e051a05df369fce31d`.

Eight eight-second snippets were generated at offsets 0, 30, 60, 90, 120, 150, 180 and 210 seconds: 64 seconds of sampled footage. The original reference was separately indexed across its full duration. Snippet durations and hashes were recorded. Creating snippets did not itself discover or verify Instagram copies.

**Audio limitation:** only four landmarks were extracted from the approximately four-minute real upload. This is sparse coverage and needs investigation before claiming robust soundtrack matching on this material. Synthetic noisy-audio tests do not resolve this real-input weakness.

## Implementation prepared

A local Docker Compose deployment runs Next.js, FastAPI, PostgreSQL/pgvector, Redis, Celery, and credential-protected S3-compatible SeaweedFS. Five independently testable agent classes cover discovery, visual matching, audio matching, decisions and alert storage. They share a worker deployment; there are not five separate remote agent deployments.

Reference/candidate uploads, job states, late acknowledgements, retries, recovery sweeps, private storage, authentication, admin/analyst/viewer permissions, evidence records, unique in-app alerts, monitoring and a black-and-white dashboard were implemented. Services were running at report verification; API, database, Redis and object-store health checks reported healthy. A process being up is not a production reliability certification.

Visual matching uses sampled keyframes, pHash, ORB descriptors, RANSAC geometric verification and temporal alignment. Audio uses normalized decoding, adaptive spectral peak filtering and landmark offset voting. Default decisions use explicit deterministic evidence rules and approved-promotional exclusions. Similarity values are not calibrated probabilities. Spoiler severity is based on an operator-configured timestamp boundary, not validated semantic plot analysis.

CLIP embedding storage/ranking and an external multimodal advisory contract exist as optional paths, but neither was exercised with real weights/provider credentials. pgvector being installed is not evidence that embedding recognition was validated.

## Controlled validation

| Check | Recorded result | Qualification |
|---|---|---|
| Latest unit/media suite | 29 passed | Includes four mocked Laya interface/fallback tests |
| Core real-service integration | 6 passed | Earlier baseline deployment; not repeated as a live-Laya integration |
| Browser E2E | 2 passed | Earlier dashboard baseline: auth/navigation/settings and access checks |
| Frontend production build | Passed | Dashboard/application build, not recognition accuracy |
| Core Python dependency audit | No known vulnerabilities found | Audit at baseline validation time; optional AI dependencies were not included |
| Frontend dependency audit | Zero reported vulnerabilities | Audit at baseline validation time |

Six opt-in integration cases skip in the standalone unit command and were executed separately for the core baseline. They are not counted as unit passes. The CI workflow was written but was not executed on GitHub.

Controlled tests exercised crop/zoom/perspective/compression transformations, alignment to a known six-second reference offset, added broadband audio noise, unrelated-video rejection, approved-promotional exclusions, duplicate suppression, RBAC, anonymous object-store denial and recovery after lost queue publication.

These are limited synthetic checks. No real-world precision, recall, false-positive rate, missed-match rate or theatrical-recording accuracy was established.

## Ten-minute stability/workload run

Run window: **11:54:19–12:04:19 IST**, 21 October 2026.

- Health observation duration: 600.03 seconds.
- Health observations: 61; failed observations: 0.
- Repeated pipeline workload duration: 600.00 seconds.
- New synthetic jobs completed: 10; job failures: 0.
- Each duplicate upload was checked to reuse the existing job.
- Sampled queue depth stayed at zero; no agent errors were reported at the final check.
- Final state at that run's completion: 12 indexed objects and 25 completed candidates, with no failed, pending or processing jobs.

Five workload decisions were promotional exclusions with measured similarity 0.8553. Five were matches with similarity 1.0 to a generated test-pattern reference. The latter fixture was named “unrelated” because it was initially unrelated to the first reference, but it was subsequently indexed during recovery testing. Matching it afterward was expected. Those results are **not** proof of perfect accuracy or a false-positive evaluation. The separate negative check ran before that additional reference was indexed.

No Instagram media was processed in this ten-minute workload. Per-job completion observations were approximately 1.2 seconds after the scheduled minute boundaries on these small local synthetic fixtures; they are not an internet discovery-to-detection SLA or a large-library benchmark.

## Instagram browser experiment

Run window: **12:30:09–12:31:09 IST**, 21 October 2026. Measured duration: **60.004 seconds**.

Four public pages were visited: the supplied reel, `alabolelo_song`'s account, its linked audio page, and an additional public reel found through accessible links. Two unique reel URLs were observed:

| Reel | Public observation | Classification |
|---|---|---|
| https://www.instagram.com/reel/DcTxhjWiS11/ | `@alabolelo_song`; “ALA BOLELO SONG … JAILER 2”; audio label “Ala Bolelo” | User-supplied URL; related metadata candidate |
| https://www.instagram.com/reel/DcTbN_gi9Tb/ | `@alabolelo_song`; “ALA BOLELO SONG JAILER 2 OUT NOW … JAILER 2”; “Original audio” | One additional related metadata candidate |

All four pages returned HTTP 200, but their public logged-out DOM exposed no playable video element. HTTP 200 does not establish access to actual reel footage. Google and DuckDuckGo searches encountered human-verification barriers; those were not bypassed. No private accounts, authenticated-only footage or restricted endpoints were accessed.

**This was not an Instagram-wide scan.** It covered a supplied reel and a small set of connected public pages. It cannot establish the maximum number of copies on Instagram, and it cannot prove absence elsewhere.

## Content comparison actually performed

Two publicly displayed poster captures, from the reel/profile pages, were compared against all 121 reference keyframes. They were not a time sequence sampled from a playable reel.

| Capture | Accepted geometric inliers | Combined frame similarity | pHash support value |
|---|---:|---:|---:|
| Poster 0 | 0 | 0.0 | 0.5873 |
| Poster 1 | 0 | 0.0 | 0.5238 |

No accepted visual correspondence was found. These are poster-comparison measurements, not real-reel confidence scores. A poster mismatch does not establish that the underlying video is unrelated. A capture of the additional reel's poster timed out, so no visual result is assigned to it.

No playable Instagram video/audio was compared with the eight-second snippets. **Verified Instagram video matches: zero.** This means no match was verified; it does not mean zero copies exist. No confirmed SceneGuard detection or detection-confidence score was created for either real reel.

## Laya findings

The verified model is `convaiinnovations/laya`, with a model-card Apache-2.0 license and a documented typed-decision SDK. SDK version `laya==0.4.12` was installed locally with CPU Torch and Transformers dependencies. The integration pins model revision `7b928d828b7b0e022f929d9bd2e44165aa270148` and uses the documented `laya.load(...).predict(state, questions)` interface.

An optional structured-evidence adapter was implemented and four contract/fallback tests passed with injected model responses. It evaluates measured visual/audio evidence without captions, can request review, and cannot promote weak evidence to a confirmed detection. Its model confidence is kept separate from matching similarity and is not assumed calibrated for movie-scene verification.

The real weights download failed at **us.aws.cdn.hf.co** with a proxy/network-policy denial. The SDK and model identity are verified; successful weight loading, live inference and domain accuracy are not. The required domain addition was saved to the environment draft, which does not itself apply the change.

**Laya was not used for the browser findings or the ten-minute synthetic run.** It remains disabled in the active worker. Installing dependencies in the host virtualenv does not install them in the immutable worker image. No successful Laya inference artifact exists.

Laya cannot retrieve Instagram media, scan the platform, extract visual fingerprints, compare audio, or compensate for unavailable footage. Its proposed role is evidence review after the actual matchers have processed candidate content.

## Problems discovered and handled

- Initially blocked Instagram and supporting domains: required domains were added through environment settings, after which public pages and posters became reachable.
- Chromium certificate errors: the platform-provided proxy CA was added in the browser execution context; TLS verification was retained.
- Search-engine verification challenges: searches stopped at the barriers.
- Missing playable reel media: recorded as an access/coverage limitation, not a negative match.
- OpenCV zero-inlier failure: fixed with guarded geometric evaluation and a regression test.
- Recovery scans overlapping retries: bounded attempt/backoff handling added; earlier failed synthetic jobs were retried successfully.
- Disk exhaustion from repeated VFS Docker layers: disposable caches/intermediate images removed and local images compacted; source, credentials, database volumes and footage preserved.
- Vulnerable baseline dependencies: updated and baseline core/frontend audits rerun successfully.
- Sparse landmarks on the real upload: newly observed reporting limitation; not yet diagnosed or corrected.

## Conclusions and next acceptance milestone

The software can demonstrate a local matching pipeline, controlled transformations, background processing, private reference handling, a working dashboard and limited public metadata discovery. It cannot presently support a claim that this uploaded video was recognized inside Instagram, that all Instagram is monitored, that Laya successfully evaluated a real match, or that production accuracy/24-hour reliability has been proven.

Before an operational launch:

1. Obtain a supported, authorized source of actual candidate reel files or playable media; explicitly define account/URL/API coverage.
2. Compare real matching and nonmatching reels against the supplied reference, recording independent ground-truth timestamps.
3. Investigate sparse real-audio fingerprints, then measure precision, recall, false positives, missed matches and processing delay on held-out data.
4. Unblock/download the pinned Laya weights, validate real inference, install dependencies in the worker image, and benchmark its decisions against the deterministic baseline before enabling it.
5. Add production HTTPS, encrypted storage, managed secrets, backups, capacity testing and operational alerting; perform longer representative workload tests.

Decision: suitable for an honestly labeled **prototype/development milestone**. Insufficient evidence for a production Instagram scene-detection launch or claims of comprehensive monitoring.

## Evidence and deliverables

- `docs/validation-run.json`: measured ten-minute observations and synthetic workload records.
- `docs/VALIDATION.md`: core validation interpretation and commands.
- `.local/instagram-browser/one-minute/report.json`: one-minute public browser observations.
- `.local/instagram-browser/one-minute/poster-comparison.json`: measured poster comparisons.
- `.local/snippets/user-reference-38/manifest.json`: snippet offsets, durations and hashes.
- `.local/snippets/user-reference-38.zip`: eight generated snippets.
- `docs/LAYA.md`: verified SDK interface, implementation status and blocked inference prerequisite.
- `backend/app/agents/laya.py`: optional evidence-review adapter.

Private credentials and signed download URLs are deliberately excluded from this report.
