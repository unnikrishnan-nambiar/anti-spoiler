"""Cloud-only build helper: use the platform proxy CA without weakening TLS."""
import os, socket, subprocess
from pathlib import Path
from urllib.parse import urlsplit
root=Path(__file__).resolve().parents[1]
proxy=urlsplit(os.environ.get('HTTPS_PROXY','')).hostname
import argparse
p=argparse.ArgumentParser();p.add_argument('--target',choices=['all','backend','frontend','laya'],default='all');args=p.parse_args()
for image,context,target in [('sceneguard-api','backend','backend'),('sceneguard-frontend','frontend','frontend'),('sceneguard-laya','backend','laya')]:
    if args.target=='all' and target=='laya': continue
    if args.target!='all' and target!=args.target: continue
    build_args=['docker','--config',str(root/'.local/docker'),'build','--network','host']
    if proxy: build_args+=['--add-host',f'{proxy}:{socket.gethostbyname(proxy)}','--build-arg','HTTPS_PROXY','--build-arg','HTTP_PROXY','--build-arg','NO_PROXY']
    ca=Path('/usr/local/share/ca-certificates/environment-proxy-ca.crt')
    if ca.exists():build_args+=['--secret',f'id=platform_ca,src={ca}']
    if target=='laya': build_args+=['-f','backend/Dockerfile.laya']
    subprocess.run([*build_args,'-t',image,context],cwd=root,check=True)
