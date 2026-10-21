"""Create local secrets without printing them or overwriting an existing .env."""
import os, secrets
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'.env'
if path.exists():
    print('.env already exists; preserved unchanged')
else:
    template=(root/'.env.example').read_text()
    for name in ('POSTGRES_PASSWORD','REDIS_PASSWORD','S3_ACCESS_KEY','S3_SECRET_KEY','JWT_SECRET','ADMIN_PASSWORD','LAYA_SERVICE_TOKEN'):
        template=template.replace(f'{name}=\n',f'{name}={secrets.token_hex(24)}\n')
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w') as output: output.write(template)
    print('Created protected .env with unique development secrets. Read ADMIN_PASSWORD locally to sign in; do not commit it.')
