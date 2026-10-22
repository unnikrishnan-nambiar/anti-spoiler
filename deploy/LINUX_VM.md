# Linux VM deployment package

Target: Ubuntu 24.04 LTS **x86_64**, 4 vCPU, 16 GB RAM and at least 30 GB SSD, with additional space for your reference footage. This is a small, single-instance extension demo. Use an existing administrative SSH account; the application runs as the separate locked `sceneguard` account.

`cloud-init.yaml` installs Python 3.12, FFmpeg, nginx, certificate tooling and the service account. Supply it as user data when creating a VM with your chosen provider. It contains no credentials, source download URL, application startup or public deployment. Preserve the provider's normal SSH access. Allow inbound SSH from your administrative addresses, HTTP 80 for certificate issuance, and HTTPS 443. Do not open 8000 or 8001.

## Transfer the current implementation

Use the generated `dist/sceneguard-source.zip` from this working checkout. Use the current `sceneguard-macos-delivery` revision containing `backend/app/demo.py`; older revisions still use the Docker setup. The archive excludes credentials, private footage, weights, dependencies and local state.

Transfer this archive to the VM with your normal SSH/SCP access. Wait for `sudo cloud-init status --wait` to complete. Extract and install as follows, substituting the uploaded archive path:

```bash
set -euo pipefail
staging=$(mktemp -d)
unzip /path/to/sceneguard-source.zip -d "$staging"
# Fresh installation only: stop here if application files already exist.
test ! -e /opt/sceneguard/scripts/run_extension.py
sudo cp -a "$staging/sceneguard/." /opt/sceneguard/
sudo chown -R sceneguard:sceneguard /opt/sceneguard
sudo chmod 0750 /opt/sceneguard
sudo -u sceneguard bash -c 'cd /opt/sceneguard && bash scripts/install_extension.sh'
```

Stop on any failed command. Model installation must finish with checksum verification. Required downloads include package registries, `download.pytorch.org`, `huggingface.co` and its weight storage hosts. Do not disable TLS or replace the expected model digest. The model download is blocked by network policy in the current onboarding machine; this package does not claim it has passed.

## Start and test on the VM

```bash
sudo systemd-analyze verify /opt/sceneguard/deploy/sceneguard-extension.service
sudo install -m 0644 /opt/sceneguard/deploy/sceneguard-extension.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sceneguard-extension
sudo systemctl status sceneguard-extension --no-pager
curl --fail http://127.0.0.1:8000/health/ready
sudo -u sceneguard bash -c 'cd /opt/sceneguard && .venv/bin/python scripts/smoke_extension.py'
```

Allow several minutes for the first model warmup. The smoke creates labeled synthetic records and requires actual Laya usage. A 503 readiness response, model fallback, open port or active systemd unit does not establish success. Logs are `/opt/sceneguard/.local/demo/logs/`; also inspect `journalctl -u sceneguard-extension`.

## Add the public domain

Point your approved domain's A record at the VM. Configure an AAAA record only if IPv6 routing and ingress are also prepared. On the VM obtain a certificate using your real domain and contact email, for example:

```bash
sudo certbot certonly --nginx -d YOUR_DOMAIN --email YOUR_EMAIL --agree-tos --no-eff-email
```

Copy `deploy/nginx.extension.conf.example` to a new nginx site file. Replace **every** `sceneguard.example.com` with that domain, including certificate paths. Enable that site using your distribution's normal nginx configuration. Preserve other sites and services. Before reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
sudo certbot renew --dry-run
```

From another machine, verify HTTPS `/health/ready`, verify anonymous `/movies` returns 401, and use the extension to log in, upload/index an authorized reference and perform a browser check showing `laya.status=used`. Enter only the API's HTTPS origin in the extension. The extension requests access to that specific host. Physical Chrome/Instagram capture must be tested by its user; the automated synthetic smoke does not establish it.

## Operate and recover

Read SceneGuard credentials locally from `/opt/sceneguard/.env` through your authorized administrator account. Never paste them into logs, shell arguments, tickets or chat. No Instagram credentials are needed by the backend.

For a consistent backup, stop `sceneguard-extension` and back up `.env` plus the complete `.local/demo` directory to protected storage. Restart the service afterward. Weights are reproducible from the pinned model; preserve `.local/models/laya` if offline recovery is needed. Restore credentials and state together with ownership `sceneguard:sceneguard`, directory mode 0700 and secret files mode 0600. Existing Docker data is separate and is not migrated.

For updates, preserve a recoverable copy of the current application and state before replacing source, rerun installation and tests, then restart and check readiness. Do not extract a new archive blindly over a running deployment. Model/store/database ports remain loopback-only. Watch disk capacity and restrict this demo to invited users.

## Current deployment truth

The source package, cloud-init prerequisites, systemd unit and HTTPS template are prepared. No VM, DNS record, public certificate or reachable HTTPS service has been created in this session. Provisioning requires a provider/account or existing VM and domain. Native Laya validation remains blocked until model download succeeds. See `docs/NATIVE_DEMO_STATUS.md` for measured current-machine results.
