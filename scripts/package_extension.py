"""Package the extension and source without credentials, footage, weights or dependencies."""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parents[1];out=root/'dist';out.mkdir(exist_ok=True)
exclude={'node_modules','.next','.local','.venv','.git','__pycache__','.pytest_cache','test-results','playwright-report','dist'}
def usable(p):
    return p.is_file() and not p.is_symlink() and not any(x in exclude for x in p.relative_to(root).parts) and p.suffix not in ('.pyc','.tsbuildinfo')
with zipfile.ZipFile(out/'sceneguard-extension.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for p in sorted((root/'extension').rglob('*')):
        if usable(p):archive.write(p,p.relative_to(root))
with zipfile.ZipFile(out/'sceneguard-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for folder in ('backend','frontend','scripts','deploy','docs','sample-data','extension','tests','.github'):
        for p in sorted((root/folder).rglob('*')):
            if usable(p):archive.write(p,Path('sceneguard')/p.relative_to(root))
    for name in ('README.md','INSTALL_MAC.md','.env.example','.gitignore','.dockerignore','compose.yaml','compose.laya.yaml','compose.extension.yaml','compose.macos.yaml','compose.dev.yaml','Start SceneGuard on Mac.command'):
        p=root/name
        if p.exists():archive.write(p,Path('sceneguard')/name)
    assert not any(Path(p).name=='.env' for p in archive.namelist())
manifest={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in out.iterdir() if p.suffix in ('.zip','.mp4','.webm')}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
