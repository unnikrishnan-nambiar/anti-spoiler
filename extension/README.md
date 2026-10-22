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

The native demo backend runs Python, FFmpeg, SQLite and local Laya directly. From a checkout with Python 3.11/3.12 and FFmpeg:

```bash
bash scripts/start_extension.sh
```

First startup runs `scripts/install_extension.sh` to install dependencies and prepare checksum-verified weights. The foreground supervisor starts a private Laya process and the extension API, waits for readiness, and stops both on Ctrl-C. Existing credentials are preserved in protected `.env`; references and state are stored under `.local/demo`. No Docker services or dashboard are needed for this mode.

On the same machine as Chrome use API origin `http://localhost:8000`. On another machine use authenticated HTTPS hosting from [REMOTE_SETUP.md](../REMOTE_SETUP.md). Your laptop's localhost does not reach a cloud workspace. No public endpoint is currently provisioned by this source code. Use [INSTALL_MAC.md](../INSTALL_MAC.md) for Mac prerequisites and supported hardware.

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

Run `bash "Start SceneGuard on Mac.command"` from the extracted source root. Pinned native dependencies require Apple Silicon with macOS 14+. Older/Intel Macs can use the native Linux backend remotely. Physical Mac execution and live Instagram capture remain unverified in this session.
