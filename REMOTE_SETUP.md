# Run SceneGuard without Docker on your Mac

Only Chrome and the SceneGuard extension run on your Mac. A Linux backend runs the video indexing, matching and Laya model. This avoids the macOS 12 / Docker Desktop compatibility issue. The project now includes a GitHub Codespaces configuration; this route has been statically checked but has not been deployed to an actual Codespace from this session.

## 1. Create your backend workspace

Sign in to GitHub, then open:

https://codespaces.new/unnikrishnan-nambiar/anti-spoiler?ref=sceneguard-macos-delivery

Select the supplied SceneGuard dev-container configuration and a machine meeting its recommendation (4 CPUs, 16 GB RAM). GitHub may charge for compute/storage after your included allowance is exhausted; check the creation screen. Create the Codespace in your browser. Creating it does not install anything on your Mac.

## 2. Start SceneGuard remotely

In the Codespace's browser Terminal:

```bash
bash scripts/start_codespaces.sh
```

This builds the containers, downloads/checks Laya weights and starts the services. Initial setup can take several minutes. Its configuration preserves private service networking and loopback-only bindings inside the remote workspace. The script sets the dashboard origin for the Codespace but does not change any forwarded port's visibility automatically.

## 3. Connect your local extension

In the Codespaces **Ports** panel, locate port **8000**. The extension cannot use a forwarded port that redirects requests to GitHub's browser-login gate. If your account/organization permits it, change **only port 8000** to **Public**. This exposes the authenticated SceneGuard API through GitHub's HTTPS forwarding service. Authentication, role checks and login rate limits still apply; other services and model/storage ports remain private. Keep port 3000 private. If policy prohibits a public API port, use another approved Linux host with authenticated HTTPS ingress instead; do not bypass the policy.

Copy port 8000's HTTPS **Forwarded Address** and enter that origin in the extension's SceneGuard API field. Allow the extension access to that specific host when Chrome prompts. The startup script also prints the expected API origin.

Read `ADMIN_USERNAME` and `ADMIN_PASSWORD` in the Codespace's protected `.env` file and enter them in the extension. Do not share them in chat. The password is for SceneGuard, not Instagram. Load the unpacked extension in your local Chrome, open Instagram, click SceneGuard on that tab, upload the references, set the duration and start the scan.

Reference uploads and cropped frame samples are sent to this remote backend, so use a host/account authorized to process your footage. Model inference remains on that host; no OpenAI API calls are made. Original footage, credentials and model weights are not in the GitHub source repository or extension zip.

## Stop and resume

Stop the Codespace in GitHub after testing to stop compute usage. GitHub can stop idle Codespaces automatically; this is a demonstration/development host, not a guaranteed 24/7 production deployment. Codespace storage can continue to incur charges until it is deleted. Preserve or export any footage/evidence before deleting the workspace.

On resume, rerun `bash scripts/start_codespaces.sh`. Builds and model downloads reuse persisted files when available. A deleted/recreated Codespace may need a new API URL and new local credentials.

## What has and has not been verified

The existing cloud deployment and local-frame/Laya tests already passed as described in `docs/EXTENSION.md`. The Codespaces JSON, shell syntax, source packaging and existing installer safety tests were checked. A new Codespace has not been provisioned, and public HTTPS forwarding has not been exercised here. Your real Instagram capture still needs the final check in your own Chrome; this route does not establish comprehensive coverage or improve the unvalidated Laya decision quality.

## If setup says Docker is missing

That means Docker is absent from the terminal environment running the command; it is not a request to install Docker Desktop on your Mac. Open the **browser editor for your Codespace** and ensure it is using this branch's latest configuration:

```bash
git pull --ff-only origin sceneguard-macos-delivery
```

Press **Cmd+Shift+P** (on your Mac keyboard) and select **Codespaces: Rebuild Container**. Let the rebuild finish. This applies `.devcontainer/devcontainer.json`, including the Docker-in-Docker feature inside the remote Linux workspace. If asked to choose a configuration, select SceneGuard. Then, in the new browser Terminal:

```bash
docker --version
docker compose version
bash scripts/start_codespaces.sh
```

Existing `.env` and footage under the workspace are preserved by these project scripts. Rebuilds can replace container-level Docker state, so back up any existing named-volume data before rebuilding an already-used deployment. During this first failed setup there should not yet be service data to preserve. If Docker remains unavailable, open the Codespace's creation log to see the failed feature installation; do not install Docker Desktop on the unsupported Mac as a workaround.
