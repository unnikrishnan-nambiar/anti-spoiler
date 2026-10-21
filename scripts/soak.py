"""Authenticated 10-minute live-service observation. Does not invent source traffic."""
import argparse,json,time,sys
from datetime import datetime,timezone
from pathlib import Path
import httpx
from dotenv import dotenv_values
p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=600);p.add_argument('--base-url',default='http://127.0.0.1:3000');p.add_argument('--output',default='.local/soak-result.json');args=p.parse_args()
root=Path(__file__).resolve().parents[1];env=dotenv_values(root/'.env')
client=httpx.Client(base_url=args.base_url,timeout=15,trust_env=False,headers={'Origin':env.get('APP_ORIGIN') or 'http://localhost:3000'})
login=client.post('/api/auth/login',json={'username':env.get('ADMIN_USERNAME','admin'),'password':env['ADMIN_PASSWORD']});login.raise_for_status()
start=time.monotonic();start_iso=datetime.now(timezone.utc).isoformat();observations=[]
print(json.dumps({'event':'soak_started','started_at':start_iso,'duration_seconds':args.seconds}),flush=True)
while True:
    elapsed=time.monotonic()-start
    errors=[];snapshot={}
    for path in ('health/ready','overview','agents'):
        try:
            response=client.get('/api/'+path);response.raise_for_status();snapshot[path]=response.json()
        except Exception as exc: errors.append({'path':path,'error':type(exc).__name__})
    agents=snapshot.get('agents',{});states=agents.get('agents',[])
    failures=[s['name'] for s in states if s['status']=='error']
    if failures:errors.append({'agent_errors':failures})
    observation={'elapsed_seconds':round(elapsed,2),'healthy':not errors,'errors':errors,
                 'queue_depth':agents.get('queue_depth'),'overview':snapshot.get('overview'),
                 'agents':[{k:s.get(k) for k in ('name','status','updated_at','stale')} for s in states]}
    observations.append(observation)
    print(json.dumps({'event':'soak_observation','elapsed_seconds':round(elapsed),'healthy':not errors,'queue_depth':agents.get('queue_depth')}),flush=True)
    if time.monotonic()-start>=args.seconds:break
    time.sleep(min(10,max(0,args.seconds-(time.monotonic()-start))))
result={'started_at':start_iso,'ended_at':datetime.now(timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-start,2),
        'passed':all(o['healthy'] for o in observations),'scope':'Authenticated service-health observation only; input traffic is not generated and no Instagram discovery coverage is implied','observations':observations}
output=root/args.output;output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2));print(json.dumps({'event':'soak_complete','passed':result['passed'],'duration_seconds':result['duration_seconds'],'output':str(output)}),flush=True)
sys.exit(0 if result['passed'] else 1)
