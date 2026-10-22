# Native extension demo status — 22 October 2026

The checked-out `work` branch began at `b66a6e9a001df8fdaa0c9b24e15259f10b7b667f`, identical to remote `sceneguard-macos-delivery`. This report records local validation of the native implementation. Git history and remote refs establish source publication; no public application deployment was performed by these checks.

## Current implementation

`scripts/start_extension.sh` now starts native Python services. `scripts/install_extension.sh` installs the pinned dependencies and prepares checksum-verified Laya weights. `scripts/run_extension.py` supervises the private model process and the API, waits for readiness, and stops both on interruption or child failure. The extension-specific API uses SQLite and private local files. Matching, authentication, bounded frame decoding and Laya evidence review reuse the existing backend code. The full dashboard/queue stack remains a separate Compose workflow.

Mac and Codespaces launchers no longer require Docker for this demo. Native Mac pins require Apple Silicon/macOS 14+; Intel or older Macs can use a remote Linux backend. Physical Mac execution has not been tested.

## Verified in this cloud machine

- Python dependencies, CPU PyTorch 2.14.1 and Laya SDK 0.4.12 installed; `pip check` passed.
- `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests tests/test_local_setup.py -q`: **46 passed, 7 skipped**. Skips require the separate distributed services. Native API tests use actual SQLite, local files, FFmpeg and geometric matching; model responses are mocked in these tests.
- Extension background tests: 4 passed. Feed DOM fixtures: 4 passed. Chromium panel test passed with mocked Chrome/API, 43 captures and 20 checks. These do not establish live Instagram access.
- A separately running native HTTP API authenticated a generated SceneGuard account, rejected anonymous `/movies` with 401, accepted a synthetic reference, and indexed 12 frames plus 2,375 audio landmarks. A two-frame synthetic browser check produced two geometric frame matches and `review` with explicit `laya.status=unavailable`. Restart preserved the indexed reference. Local evidence is `.local/native-http-result.json`.
- Shell syntax and Git whitespace checks passed. The systemd unit passed static validation after substituting this machine's executable path/user. The target `/opt/sceneguard` host and nginx/TLS configuration have not been provisioned or exercised.
- Earlier, before switching workflow, the full base Compose integration suite passed 7 tests. Those containers were then stopped. That result does not validate native Laya.

## Outstanding blockers and deployment truth

Hugging Face model download fails with proxy HTTP 403 for `huggingface.co`. No model checkpoint has been downloaded here, so actual native Laya inference, warmed two-process startup, and the live smoke test have **not passed**. A native API process was launched for partial validation, with its PID recorded in `.local/demo-api-validation.pid`; without Laya it intentionally returns **503** from `/health/ready`. An open port or working visual fallback is not a ready deployment.

Required Hugging Face domain additions, an installation script and startup instructions were saved in the cloud environment draft. Saving does not apply network policy or publish a snapshot. Review/save the network settings, rerun `bash scripts/install_extension.sh`, stop the verified partial validation process, start `bash scripts/start_extension.sh`, and run `.venv/bin/python scripts/smoke_extension.py`. That smoke requires real model usage and retains labeled synthetic records.

`deploy/sceneguard-extension.service`, `deploy/nginx.extension.conf.example` and `REMOTE_SETUP.md` prepare a small Linux VM demo. **No public server/domain/HTTPS endpoint or Codespace was deployed.** A hosting destination and authorized access are still needed. After deployment, validate HTTPS readiness, authentication, upload/index and a real Laya-backed browser match externally. No live Instagram capture or comprehensive discovery has been verified.
