# SceneGuard Feed Check

Chrome 116+ or a compatible Chromium browser. This is an unpacked Manifest V3 extension, not a Chrome Web Store listing.

## Install

1. Extract `sceneguard-extension.zip`.
2. Open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select the extracted `extension` folder containing `manifest.json`.
3. Pin SceneGuard to the toolbar.
4. Start the SceneGuard backend with Laya (see below). Open Instagram yourself and sign in normally.
5. Click the SceneGuard toolbar icon **on the Instagram tab**. This grants temporary access to that tab. Enter your SceneGuard API address and SceneGuard credentials in the side panel. Do not enter your Instagram password into SceneGuard.
6. Upload your authorized reference video, or select an indexed reference. Upload up to five files together; select the indexed references you want to compare. Wait for indexing to finish. For this fast mode, use an excerpt up to 15 minutes; approved promotional references also count toward the 450-frame matching budget.
7. Confirm processing authorization. Keep the video fully visible and playing, then set a duration from **15 to 600 seconds** and click **Start scan**. Automatic feed advancement can be switched off if you prefer to navigate manually. Stop ends capture immediately.

Upload/indexing happen before the selected scan timer. During scanning, the extension captures two frames about two seconds apart, crops each screenshot to the visible video, and sends only those crops to your authenticated SceneGuard server. It requires a stable post URL and advancing playback. Paused, obscured, inaccessible and changing reels are skipped. Tab changes stop the run. Captures and scrolling require the selected Instagram tab to remain active.

Results show the post link, measured visual similarity, matching reference timestamp, supporting frame count, Laya status, model latency and SDK token usage when available. Export saves a JSON report. Download matching reels CSV includes matched and review leads, grouped by reel and reference, with evidence scores and Laya choices. Unfinished reference comparisons remain explicit when time runs out. A no-match result applies only to sampled frames; an unviewed section of the reel might contain a match. Results are review leads and do not send enforcement actions, external notifications, or create full-video dashboard detections. Browser-check results are held in the side panel until exported; they are not a persistent monitoring feed.

## Backend

The extension requires the matching backend; installing the extension alone is insufficient. On the **same computer as Chrome**, from the prepared SceneGuard checkout:

```bash
docker compose -f compose.yaml -f compose.laya.yaml -f compose.extension.yaml up --no-build -d
```

Use `http://localhost:8000` as the API address. The API is bound to loopback. Sign in with the SceneGuard credentials in your protected `.env`. If you run the backend on a different machine, use its authenticated HTTPS API origin and allow that specific host when Chrome prompts. Your laptop's `localhost` does not point to this cloud workspace. This workspace does not currently provide a public HTTPS API URL.

For a fresh Linux/WSL checkout with Docker Compose and Python 3, `bash scripts/start_extension.sh` builds the services and prepares verified weights. This fresh-install helper has been syntax-checked; the existing deployment was validated with its prepared images. Initial downloads/builds can take several minutes and are outside the scan timer.

A fresh checkout needs built images and the pinned Laya weights: follow `docs/LAYA.md` in the full source bundle, then run the Compose command above with `--build` instead of `--no-build`. `python scripts/bootstrap.py` creates local credentials without printing them. Keep `.env` private.

## Laya and runtime limits

The private model service uses `convaiinnovations/laya` with verified pinned weights. Laya receives compact numeric evidence only: visual score, supporting frame count, timestamps, absence of captured audio, and promotional status. It does not receive screenshots, captions, Instagram credentials, or the full reference video. Matching is performed by perceptual hashing and geometric feature verification before Laya's review.

Laya runs on your backend's CPU; this extension makes no OpenAI API calls. SDK input tokens and output-token counts are displayed when supplied by the model. Counts are not guessed from string length. Laya is warmed before readiness, each review has a four-second HTTP timeout, and each entire comparison is limited by the client to 6.5 seconds or the remaining scan time. An unavailable/timed-out model yields explicit review status for an otherwise strong match. Laya cannot promote weak visual evidence to a match. Approved promotional footage remains excluded.

There is no guarantee of a particular number of matches within the selected duration. Throughput depends on feed layout, loaded reels, playback, server latency and connection speed. The tool does not scan all Instagram. Audio is not captured in this browser mode. Heavily cropped, obstructed or rapidly changing footage can be missed. Similarity and model confidence are not calibrated correctness probabilities.

## Privacy and permissions

- `activeTab` and `scripting`: inspect the selected Instagram tab's playing video rectangle and post link, and optionally scroll it.
- `sidePanel`: show controls beside the feed.
- `storage`: retain the SceneGuard session token in browser session storage; passwords are cleared after login. Instagram cookies are never accessed.
- Loopback API host permissions: communicate with the locally running backend.
- Optional HTTPS hosts: requested only for the specific remote API origin you enter; no all-sites permission is requested at installation.

A visible-tab screenshot exists transiently in extension memory to crop the video. Only the cropped PNG frames leave your browser. The backend holds frame features transiently for comparison and does not persist captured screenshots in this mode. Reference uploads are stored privately by SceneGuard. Exported reports contain reel URLs and measured evidence; store them appropriately. No analytics or advertising scripts are included.

If Developer mode or extension installation is blocked by your browser administrator, use an approved browser profile or ask that administrator to approve this extension. Do not bypass managed policy.

## MacBook setup

Use the Mac source package and `bash "Start SceneGuard on Mac.command"` from its extracted root. See `INSTALL_MAC.md`. The launcher uses Docker Desktop and the validated Linux x86 stack on Intel/Apple Silicon; Apple Silicon uses emulation and may be slower. It does not require host Python. Mac hardware execution remains unverified.
