"""Supervise the two native Python services; Ctrl-C stops both. No Docker required."""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]

def configuration(data_dir=None):
    from dotenv import dotenv_values
    env=os.environ.copy()
    for key,value in dotenv_values(ROOT/'.env').items():
        if value is not None: env.setdefault(key,value)
    data=Path(data_dir or ROOT/'.local/demo').resolve()
    data.mkdir(parents=True,exist_ok=True,mode=0o700)
    objects=data/'objects'; objects.mkdir(exist_ok=True,mode=0o700)
    env.update(PYTHONPATH=str(ROOT/'backend'),DATABASE_URL='sqlite:///'+str(data/'demo.sqlite3'),
               LOCAL_STORAGE_PATH=str(objects),LAYA_ENABLED='true',
               LAYA_SERVICE_URL='http://127.0.0.1:8001',
               LAYA_MODEL_PATH=str(ROOT/'.local/models/laya'),HF_HUB_OFFLINE='1',
               TRANSFORMERS_OFFLINE='1',USE_TF='0',TOKENIZERS_PARALLELISM='false')
    return env

def wait_ready(url,process,timeout):
    deadline=time.monotonic()+timeout
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic()<deadline:
        if process.poll() is not None: raise RuntimeError('Service exited; inspect .local/demo/logs')
        try:
            with opener.open(url,timeout=3) as response:
                if json.load(response).get('status')=='ready': return
        except (OSError,ValueError): pass
        time.sleep(1)
    raise RuntimeError('Service readiness timeout; inspect .local/demo/logs')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--data-dir')
    args=parser.parse_args()
    if not 1<=args.port<=65535 or args.port==8001: parser.error('Choose an API port other than 8001')
    os.umask(0o077)
    # Refuse occupied ports before starting either child; never reuse an unknown service.
    for port in (args.port,8001):
        with socket.socket() as sock: sock.bind(('127.0.0.1',port))
    env=configuration(args.data_dir)
    if not (Path(env['LAYA_MODEL_PATH'])/'provenance.json').exists():
        raise SystemExit('Verified model missing. Run bash scripts/install_extension.sh first.')
    logs=Path(env['LOCAL_STORAGE_PATH']).parent/'logs'; logs.mkdir(exist_ok=True)
    children=[]; files=[]
    def stop(signum,frame): raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,stop)
    try:
        for module,port in [('app.laya_service',8001),('app.demo',args.port)]:
            log=(logs/(module.split('.')[-1]+'.log')).open('a'); files.append(log)
            process=subprocess.Popen([sys.executable,'-m','uvicorn',module+':app','--host','127.0.0.1',
                                      '--port',str(port),'--no-access-log','--workers','1'],
                                     cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            children.append(process)
            wait_ready(f'http://127.0.0.1:{port}/health/ready',process,180)
        print('SceneGuard extension API ready on loopback port '+str(args.port)+'. Local Laya is ready on private port 8001.',flush=True)
        print('Use protected .env SceneGuard credentials. Ctrl-C stops both services.',flush=True)
        while all(child.poll() is None for child in children): time.sleep(1)
        raise RuntimeError('A service exited; inspect '+str(logs))
    except KeyboardInterrupt: pass
    finally:
        for child in children:
            if child.poll() is None: child.terminate()
        for child in children:
            try: child.wait(timeout=15)
            except subprocess.TimeoutExpired: child.kill(); child.wait()
        for file in files: file.close()

if __name__=='__main__':
    try: main()
    except (OSError,RuntimeError) as exc: raise SystemExit(str(exc))
