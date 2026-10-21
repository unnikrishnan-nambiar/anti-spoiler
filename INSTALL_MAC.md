# Install SceneGuard on a MacBook

This package contains the Chrome extension, local matching backend and a Mac launcher. The launcher has been syntax-checked, its command construction and credential handling tested, and its Compose configuration validated on Linux. It has **not** been executed on a physical Mac. Intel and Apple Silicon are configured to use the validated Linux x86-64 dependencies; Apple Silicon uses Docker emulation and can be slower.

## 1. Install Docker Desktop

Install the correct Docker Desktop version for your Mac from the [official Mac installation page](https://docs.docker.com/desktop/setup/install/mac-install/), open it and finish its setup. Docker Desktop must be running. No host Python installation or paid AI API key is needed; setup runs Python inside Docker.

### macOS 12 Monterey compatibility

Current Docker Desktop requires a newer OS and will not start on macOS 12.7.6. Docker's [official release notes](https://docs.docker.com/desktop/release-notes/#4420) document that 4.42 raised the minimum to macOS 13.3; 4.41.2 is the preceding release. Version 4.41.2 is now old and unsupported, so use it only as a temporary compatibility option and prefer upgrading macOS if your Mac supports it. Use the [4.41.2 release entry](https://docs.docker.com/desktop/release-notes/#4412) for the matching Intel or Apple Silicon download. An installed Docker app can be replaced by a compatible version without deleting its data; do not delete Docker volumes or use factory reset to solve this OS-version error.

The launcher now detects macOS 12 and an installed Docker app whose declared OS minimum is too new, and stops with compatibility instructions instead of repeatedly attempting to launch it.

## 2. Run the local installer

Extract `sceneguard-macos.zip` in Downloads. Open Terminal and run:

```bash
cd ~/Downloads/sceneguard
bash "Start SceneGuard on Mac.command"
```

If you extracted it elsewhere, use that folder instead. You can type `cd ` and drag the extracted `sceneguard` folder into Terminal to insert its path.

The installer creates protected `.env` credentials without printing them, builds Docker images, downloads and verifies the approximately 843 MB Laya weight file, and starts the backend, dashboard, workers and model service. First-time downloads/builds can take several minutes; they happen before the timed scan. Future launches reuse images and weights. Keep the Terminal window open until startup finishes. Docker Desktop may request normal first-run access to the folder you extracted.

The local dashboard is `http://localhost:3000`; the extension's API address is `http://localhost:8000`. The database, Redis and model service have no public ports. API access remains authenticated and loopback-only.

## 3. Load the extension into Chrome

Open `chrome://extensions`, enable **Developer mode**, choose **Load unpacked**, and select the `extension` folder inside `sceneguard`. Pin SceneGuard to the toolbar. Chrome requires you to perform this step; the launcher does not modify browser security policies or install extensions silently.

Read your local SceneGuard credentials with:

```bash
open -a TextEdit .env
```

Use `ADMIN_USERNAME` and `ADMIN_PASSWORD` in the SceneGuard side panel. Do not share `.env` or enter your Instagram password into SceneGuard.

Open Instagram in Chrome and sign in normally. Click the SceneGuard toolbar icon while that tab is selected. Connect to `http://localhost:8000`, upload up to five authorized references, wait for indexing, select the references, set a duration from 15 to 600 seconds, and start. Keep the selected tab active and a reel fully visible/playing. The final Related reels list and CSV include visual matches and review leads corresponding to each selected reference. JSON includes every completed, skipped or unfinished comparison.

## Performance and limitations

Apple Silicon emulation has not been benchmarked; matching and Laya may exceed the short per-comparison timeout on some Macs. Those calls remain explicit review/skipped results rather than false negatives. More selected references reduce how many reels fit in your chosen time. This extension samples visible loaded reels and cannot guarantee finding every matching reel. Audio is not captured in browser mode.

Laya runs locally on CPU and uses small structured inputs (about 110–111 SDK input tokens in the measured Linux screenshot tests; zero generated tokens), with no OpenAI API billing. It disagreed with strong visual matches in those tests, so its decisions remain advisory/reviewable. See `docs/EXTENSION.md`. The supplied demo is a simulated feed with real upload/matching/Laya processing, not a recording of live Instagram discovery.

## Restart, stop and diagnostics

Rerun the launcher to start the stack again. To stop services while retaining references and database state:

```bash
docker compose -f compose.yaml -f compose.laya.yaml -f compose.extension.yaml -f compose.macos.yaml stop
```

If startup fails, check:

```bash
docker compose -f compose.yaml -f compose.laya.yaml -f compose.extension.yaml -f compose.macos.yaml ps
docker compose -f compose.yaml -f compose.laya.yaml -f compose.extension.yaml -f compose.macos.yaml logs --tail=50 api laya worker
```

Do not share `.env` or credential-bearing logs. Do not use `down -v` unless you intend to delete private media and database volumes. Docker images, model files and footage stay on your Mac; no footage is bundled with this installer.
