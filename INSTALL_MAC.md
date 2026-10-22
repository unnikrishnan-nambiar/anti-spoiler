# Native extension demo on macOS

The extension demo runs Python, FFmpeg, SQLite and a private local Laya process. Keep its terminal open; Ctrl-C stops both Python services. Docker is not required. This is the extension API, not the full dashboard/queue deployment.

With the pinned dependencies, native Mac installation requires **Apple Silicon and macOS 14 or newer**, Python 3.11/3.12 and FFmpeg. The published PyTorch 2.14.1 Python 3.12 wheel targets macOS 14 ARM64; the OpenCV wheel requires macOS 13. Mac hardware has not been tested here. Intel Macs and macOS Monterey should use the Linux backend in [REMOTE_SETUP.md](REMOTE_SETUP.md); Chrome and the extension remain on the Mac.

Install prerequisites through your normal package manager, for example `brew install python@3.12 ffmpeg`, then extract the source bundle and run:

```bash
cd /path/to/sceneguard
bash "Start SceneGuard on Mac.command"
```

First startup installs Python packages and downloads the official pinned model, verifies its SHA-256, and warms Laya. It may take several minutes. Offline startup requires the installed dependencies and verified weights. The API binds only to loopback port 8000; Laya binds only to loopback port 8001. There is no dashboard on port 3000 in this mode.

Open `chrome://extensions`, enable Developer mode and load the `extension` directory. Open the protected `.env` locally to read `ADMIN_USERNAME` and `ADMIN_PASSWORD`; enter them in SceneGuard's panel with API origin `http://localhost:8000`. Do not enter Instagram credentials into SceneGuard. Open Instagram yourself, click the extension, upload authorized references, wait for indexing and start the chosen scan duration. Keep the selected reel playing and visible.

Private references, indexes and SQLite state live under `.local/demo`; weights live under `.local/models/laya`. Existing Docker volumes are separate and are not migrated or deleted. Logs are `.local/demo/logs/demo.log` and `laya_service.log`. An interrupted index becomes an explicit failed record on restart; upload it again to retry. Back up `.env` and the complete `.local/demo` directory together while stopped. Do not share these files.

Browser capture still requires a final check in your actual Chrome/Instagram session. It samples visible frames only, captures no audio and provides review leads. Laya reviews numeric evidence, not screenshots; its confidence is uncalibrated. See [extension limits](docs/EXTENSION.md).
