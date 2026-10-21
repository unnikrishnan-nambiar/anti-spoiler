# Verified, deployed Laya integration

The official model is [convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya), Apache-2.0. Its documented interface is `laya.load(...).predict(state, questions)`. SceneGuard uses the `choice` interface on measured visual/audio evidence. Laya is a structured-text decision model; it does not retrieve Instagram footage, compare pixels or compute audio fingerprints.

Live CPU inference now works. The earlier weight-download blocker reported in the experiment report was resolved. The pinned model revision is `7b928d828b7b0e022f929d9bd2e44165aa270148`, with official SDK `laya==0.4.12`. The 842,609,210-byte model.safetensors SHA-256 was checked against its official LFS metadata: `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c`. Torch uses two CPU threads. Versions are pinned in the optional requirements and Dockerfile.

`compose.laya.yaml` deploys a private authenticated model service. Its weights are mounted read-only; runtime is offline, has no published port, and uses the internal service network. A separate random service token is stored in protected `.env`. API and workers use authenticated HTTP to the model service, avoiding separate model copies per worker. Check readiness and actual recorded decisions; configuration alone does not establish successful inference.

Four controlled derivatives of the user's actual reference, with cropping, compression, mild perspective change and noisy audio, produced a real `confirmed` Laya choice. Their reference timestamps were 30, 60, 90 and 150 seconds. These are local content-matching experiments, not Instagram captures or a platform accuracy benchmark. The deployed-pipeline report records subsequent queue-based results separately.

The SDK's legacy `confidence` field for choice questions is normalized-entropy confidence. SceneGuard uses `answer_confidence` when available and labels it separately as `model_confidence`. This field has **not** been calibrated for movie-scene verification. The geometric/audio similarity score is also an uncalibrated evidence measure. Neither should be marketed as a probability of infringement or a measured population accuracy.

Laya can downgrade a strong deterministic match to review; it cannot promote weak evidence to confirmed. Promotional exclusions remain authoritative. Missing candidate footage always produces `insufficient_evidence`, even if a model suggests a different choice. Service errors produce an explicit deterministic fallback in the evidence record.

For the prepared environment:

```bash
cd /workspace/anti-spoiler
docker compose -f compose.yaml -f compose.laya.yaml up --no-build -d
```

For a fresh machine, prepare dependencies and verified weights, generate a token without printing it, then build:

```bash
python scripts/bootstrap.py
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/pip install 'torch==2.14.1+cpu' --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r backend/requirements-laya.txt
HF_HUB_DISABLE_XET=1 USE_TF=0 .venv/bin/python scripts/prepare_laya.py
.venv/bin/python - <<'PY'
from pathlib import Path
import secrets
p=Path('.env')
if not any(line.startswith('LAYA_SERVICE_TOKEN=') and line.split('=',1)[1] for line in p.read_text().splitlines()):
    text=p.read_text()
    text='\n'.join(line for line in text.splitlines() if not line.startswith('LAYA_SERVICE_TOKEN='))
    p.write_text(text+'\nLAYA_SERVICE_TOKEN='+secrets.token_hex(32)+'\n');p.chmod(0o600)
PY
docker compose -f compose.yaml -f compose.laya.yaml up --build -d
```

Use `python scripts/cloud_build.py --target laya` for a cloud build requiring the existing trusted platform CA/proxy. Preserve TLS and model digest verification. See the repair report for validation scope and the remaining Instagram media-access gap.

## Browser visual-only mode

The browser extension supplies compact visual-only evidence with audio explicitly unavailable. Its measured SDK input is 110–111 tokens per review with zero generated output tokens. In the four controlled screenshot tests, Laya disagreed with strong geometric matches; these remain review leads. Do not extrapolate earlier audio/video-positive model results to this mode or claim Laya improves its accuracy. See [extension measurements](EXTENSION.md).
