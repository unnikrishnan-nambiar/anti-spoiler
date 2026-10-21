# Browser extension delivery and validation — 21 October 2026

SceneGuard Feed Check is a Manifest V3 Chrome side-panel extension. It accepts one to five authorized reference uploads, indexes them through the existing authenticated backend, lets the user select references and a scan duration from 15 to 600 seconds, and compares frames from reels playing in the selected Instagram tab. It returns grouped reel links, corresponding reference filenames/IDs, timestamps, visual evidence, Laya status and unfinished comparisons. A focused Related reels list and CSV contain visual matches and review leads; JSON contains all observations. Upload/indexing occur before the timed scan.

Install and operate it using [the extension guide](../extension/README.md). Prepared backend startup:

```bash
docker compose -f compose.yaml -f compose.laya.yaml -f compose.extension.yaml up --no-build -d
```

The extension zip contains only the browser extension. The full source zip contains the backend, deployment scripts, extension and tests; it excludes credentials, private footage, model weights, dependencies and caches. A fresh Linux/WSL setup helper is `bash scripts/start_extension.sh`; it builds the services and prepares verified Laya weights. That helper was syntax-checked, while this environment was validated using prepared images and model files. Build/download time is outside the scan duration. A laptop's localhost is not this cloud environment; run the backend locally or configure an authenticated HTTPS API origin reachable from Chrome. This environment does not currently provide a public API URL.

## Capture and privacy

The extension uses the temporary active-tab grant from clicking its toolbar action on Instagram. It checks the selected active tab before and after each screenshot, requires a visible playing video and an identifiable post link, crops the screenshot to the video rectangle, then sends only cropped frames to SceneGuard. Instagram cookies and passwords are not accessed. The SceneGuard session token is held in Chrome session storage, and the entered SceneGuard password is cleared after login. Optional HTTPS host permission is requested only for the API origin entered by the user.

Only the visible loaded feed is sampled. Two frames about two seconds apart support geometric comparison. Paused, obscured, looping/changing or inaccessible video samples are skipped. Full video and audio are not captured. There is no guarantee of comprehensive discovery, a particular reel count, all matching clips, or a complete scan of each sampled reel. The extension stops capture at the selected deadline, cancels pending requests, and preserves completed comparisons with remaining reference IDs marked unfinished. Partial or timed-out comparisons are not represented as negative content findings.

Captured frames are decoded within bounded dimensions and sizes, then matched with crop-aware perceptual hashes, ORB/RANSAC geometry and temporal consistency. Reference descriptor arrays are cached using the index key and update timestamp. The fast mode caps each reference and its applicable approved promo library to a 450-frame comparison budget. Promotional exclusions remain authoritative. Results are review leads held in the side panel until exported; this mode does not create full-video dashboard detections, issue notifications or perform enforcement.

## Laya and actual measurements

The private service uses the previously verified `convaiinnovations/laya` revision and weight digest documented in [LAYA.md](LAYA.md). It is warmed before readiness. Screenshots, thumbnails, captions, credentials and full videos do not enter Laya. A visual-only request explicitly marks audio unavailable and supplies a compact structured state. There is no OpenAI API call.

Four actual controlled derivative clips from the user's reference were sampled at two frames each and sent through the deployed browser endpoint. All four geometric comparisons found the expected reference offsets (30, 60, 90, 150 seconds). Laya ran for all four, reporting 110–111 SDK input tokens, zero output tokens and no truncation. First-request wall latency was 3.142 seconds; subsequent requests were 1.428, 1.442 and 1.492 seconds on this machine. These include geometric matching and model review; they do not include browser playback sampling or network latency from another computer. SDK token counts are recorded directly, not estimated from string length. Local CPU inference does not incur billed OpenAI tokens.

**Laya returned `no_match` despite strong geometric support in these four screenshot cases.** The tool therefore retains them as `review` leads rather than advertising model-confirmed matches. This is evidence that Laya's movie-scene decision quality remains unvalidated; adding it did not establish better accuracy or faster matching. Earlier complete-video/audio tests used different evidence and did receive positive model choices. The current browser mode does not capture audio. No model result has been changed to make the demonstration appear successful.

Each Laya HTTP review has a four-second timeout; each client comparison is bounded by 6.5 seconds or the remaining scan budget. An unavailable/timed-out model is explicit and downgrades an otherwise strong match to review. Laya cannot promote weak evidence. Similarity and SDK model confidence remain uncalibrated for this domain. See `extension-results.json` for compact measured output.

## Checks performed

- 41 backend unit/media/service tests passed; seven full-service integration cases skip in the standalone command and are not counted as passes here.
- A Chromium UI test with a simulated Chrome bridge and mock API passed multiple-reference selection, actual 60-second stopping (60.039 seconds), Stop behavior, tab-change stopping, CSV export/escaping and invalid-duration rejection. Its synthetic match counts measure UI behavior, not real Instagram detection or throughput.
- Four DOM-fixture checks passed for playing/paused footage, letterbox cropping, post attribution and fully visible video requirements.
- Four mocked Chrome-bridge checks passed for selected-tab authorization, site restrictions and discarding captures when the tab changes during capture.
- Actual deployed API requests exercised real frame decoding, geometric comparisons and real private Laya inference. The captured source was controlled local derivatives, not Instagram.
- A recorded controlled demonstration exercises real uploads/indexing and the real browser-matching endpoint, with a simulated Chrome bridge/feed. It uses two reference files and a configurable 25-second timer. The video carries a persistent controlled-demo label. Its result/export metrics are recorded below after the final run.

Managed policy on this cloud Chromium blocks installation of new extensions (`ExtensionInstallBlocklist: ["*"]`). The unpacked extension could not be installed here. Policy was preserved. Consequently full capture permission behavior and end-to-end interaction with a real logged-in Instagram feed require a final check in the user's own Chrome after loading the extension. No claim of that live-feed validation is made.

## Recording your own real-feed demonstration

Load the extension in Chrome, start/connect the backend, upload authorized reference files, and wait for them to become indexed. Select the references and desired duration. Start your normal screen recorder with the feed and side panel visible, then click Start scan. Keep the selected Instagram tab active and let reels play. When the timer finishes, show the Related reels list, open a result link, and download the CSV/JSON. Label review leads as needing review and show Laya's actual status. The supplied controlled demo is an example of the workflow, not evidence of comprehensive Instagram monitoring.

## Final controlled recording

The final 25-second demo uploaded and indexed two actual reference files and produced two grouped reel review leads, one for each uploaded reference. All model decisions shown are real; neither is labeled a confirmed match. Reel URLs are clearly marked DEMO_A/DEMO_B fixture placeholders and are not real discoveries. The downloadable MP4/WebM displays the simulated-feed/real-backend notice throughout.
