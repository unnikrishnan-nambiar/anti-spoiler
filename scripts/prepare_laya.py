"""Fetch a pinned official checkpoint, verify its published weight digest, prepare a local cache."""
import hashlib,json,os,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.agents.laya import MODEL_ID,REVISION,MODEL_SHA256
from huggingface_hub import snapshot_download
root=Path(__file__).resolve().parents[1]
os.environ.setdefault('HF_HUB_DISABLE_XET','1')
source=Path(snapshot_download(MODEL_ID,revision=REVISION,cache_dir=str(root/'.local/huggingface/hub'),allow_patterns=['rl_agent_config.json','model.safetensors','tokenizer/*','encoder/*']))
actual=hashlib.file_digest((source/'model.safetensors').open('rb'),'sha256').hexdigest()
if actual!=MODEL_SHA256:raise ValueError('Model checksum mismatch')
# The SDK's documented tokenizer compatibility normalization is applied only after weight verification.
from app.agents.laya import load_agent
os.environ['LAYA_MODEL_PATH']=str(source)
load_agent()
target=root/'.local/models/laya';target.mkdir(parents=True,exist_ok=True)
for item in source.rglob('*'):
 if item.is_file():
  out=target/item.relative_to(source);out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(item,out);out.chmod(0o644)
for directory in [target,*[p for p in target.rglob('*') if p.is_dir()]]:directory.chmod(0o755)
(target/'provenance.json').write_text(json.dumps({'model':MODEL_ID,'revision':REVISION,'model_sha256':actual,'source':'official pinned Hugging Face snapshot'},indent=2))
print('Prepared verified Laya model directory:',target)
