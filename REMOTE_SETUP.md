# Host the native extension backend

Run the backend on a Linux machine; the Mac needs Chrome and the unpacked extension only. The demo uses one Python API process, one local CPU Laya process, SQLite and private local files. No Docker, Redis, PostgreSQL, S3, worker or dashboard is required for this demo. The full pipeline remains available separately through Compose.

For the concrete Ubuntu VM sizing, cloud-init configuration, transfer and deployment commands, follow [the Linux VM runbook](deploy/LINUX_VM.md).

## Linux preparation

Use Python 3.11/3.12, FFmpeg, at least 4 CPU cores, 8 GB RAM (16 GB recommended), and 10 GB free storage plus footage capacity. Install `python3-venv`, `ffmpeg`, and, for public hosting, nginx and your normal certificate tooling with your distribution's package manager.

Check out the source into `/opt/sceneguard` as a dedicated unprivileged `sceneguard` account. Existing cloud tasks should use their existing isolated checkout rather than create a worktree. Run as that account:

```bash
cd /opt/sceneguard
bash scripts/install_extension.sh
bash scripts/start_extension.sh
```

Installation preserves existing `.env` credentials. First setup needs package registries, `download.pytorch.org`, `huggingface.co` and Hugging Face's weight-download hosts. TLS and the pinned weight digest remain verified. A download denial is a setup blocker; do not treat a deterministic fallback as live Laya.

Readiness is `GET /health/ready` on loopback port 8000. It requires SQLite, writable local storage, FFmpeg and the pinned Laya service. `GET /health/live` alone does not establish readiness. Run `.venv/bin/python scripts/smoke_extension.py` for synthetic upload/index/matching and an actual Laya review; it fails if model usage is unavailable and retains labeled synthetic records. Stop with Ctrl-C before installing the background service.

## Persistent Linux service and HTTPS

`deploy/sceneguard-extension.service` is a systemd unit for `/opt/sceneguard` and the `sceneguard` user. Create `.local` as that user before installing the unit. After copying it into `/etc/systemd/system`, run `systemctl daemon-reload` and `systemctl enable --now sceneguard-extension`. Inspect `systemctl status sceneguard-extension`, its journal, and `.local/demo/logs`. The supervisor starts Laya first, waits for readiness, starts the API, and terminates both if either exits. Run exactly one instance; SQLite and local upload/indexing limits are intended for a small demo.

Point an approved domain at the host. Configure a valid TLS certificate and adapt `deploy/nginx.extension.conf.example` with that domain and certificate paths. Validate with `nginx -t` before reloading nginx. Expose only HTTPS/HTTP for certificate renewal and your administrative access; keep 8000 and 8001 private. The template proxies the API, caps upload sizes, and rate limits login. Do not expose model port 8001. Set host disk quotas/monitoring and restrict access to an invited demo audience before accepting uploads.

Verify externally that `/health/ready` returns ready over HTTPS, anonymous `/movies` returns 401, and a SceneGuard login, reference upload/index, and `/browser/match` succeed with `laya.status=used`. The extension requests permission for the exact HTTPS API origin entered. Your Mac's localhost does not reach this cloud workspace.

No public host or HTTPS endpoint is provisioned merely by adding these files. This session has no selected hosting account/server/domain; those are needed for deployment and an external smoke test.

## Codespaces alternative

The dev-container uses Python 3.12 and installs FFmpeg without Docker-in-Docker. In a user-created Codespace on `sceneguard-macos-delivery`, run `bash scripts/start_codespaces.sh` and keep its terminal running. Port 8000 must have an approved HTTPS forwarded address reachable by the extension without GitHub's login redirect. Change its visibility only if your organization permits that exposure; keep 8001 private. This route has not been deployed or externally tested in this session.

## Data and scope

`.env` holds private local credentials; `.local/demo` holds uploaded references, indexes and SQLite state. Protect and back them up together while stopped. This demo does not migrate existing Docker volumes, provide full-video candidate jobs, continuous discovery, dashboard alerts, or multi-instance durability. The extension's existing review/export workflow is the supported interface. For anything beyond a small invited demo, plan database/storage migration, retention, monitoring, and capacity testing first.
