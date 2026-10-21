"""Initialize local credentials without printing secrets or replacing existing credentials."""
from pathlib import Path
import runpy,secrets
root=Path(__file__).resolve().parents[1]
runpy.run_path(str(root/'scripts/bootstrap.py'),run_name='__main__')
p=root/'.env';lines=p.read_text().splitlines()
if not any(x.startswith('LAYA_SERVICE_TOKEN=') and len(x.split('=',1)[1])>=32 for x in lines):
    lines=[x for x in lines if not x.startswith('LAYA_SERVICE_TOKEN=')]
    p.write_text('\n'.join(lines)+'\nLAYA_SERVICE_TOKEN='+secrets.token_hex(32)+'\n');p.chmod(0o600)
