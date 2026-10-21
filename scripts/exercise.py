"""Repeated real pipeline jobs using local synthetic files; no platform download."""
import argparse,json,time,uuid
from datetime import datetime,timezone
from pathlib import Path
import httpx
from dotenv import dotenv_values
p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=600);args=p.parse_args()
root=Path(__file__).resolve().parents[1];env=dotenv_values(root/'.env')
client=httpx.Client(base_url='http://127.0.0.1:3000/api/',headers={'Origin':env.get('APP_ORIGIN','http://localhost:3000')},trust_env=False,timeout=30)
r=client.post('auth/login',json={'username':env.get('ADMIN_USERNAME','admin'),'password':env['ADMIN_PASSWORD']});r.raise_for_status()
start=time.monotonic();started=datetime.now(timezone.utc).isoformat();jobs=[];failures=[]
print(json.dumps({'event':'pipeline_exercise_started','started_at':started,'seconds':args.seconds,'scope':'synthetic only'}),flush=True)
while time.monotonic()-start<args.seconds:
    cycle_start=time.monotonic();name='candidate' if len(jobs)%2==0 else 'unrelated'
    url='https://example.invalid/soak-'+uuid.uuid4().hex
    try:
        def submit():
            with (root/'.local/samples'/f'{name}.mp4').open('rb') as f:
                r=client.post('media',files={'file':(name+'.mp4',f,'video/mp4')},data={'kind':'candidate','platform':'mock','post_url':url,'authorized':'true'})
            r.raise_for_status();return r.json()
        media=submit();assert submit()['id']==media['id'],'duplicate upload generated another job'
        deadline=time.monotonic()+50
        while time.monotonic()<deadline:
            r=client.get('media');r.raise_for_status();record=next(m for m in r.json() if m['id']==media['id'])
            if record['status']=='complete':break
            if record['status']=='failed':raise RuntimeError('processing failed: '+str(record['error']))
            time.sleep(1)
        else:raise RuntimeError('processing deadline exceeded')
        r=client.get('detections',params={'limit':100});r.raise_for_status();d=next(d for d in r.json() if d['media_id']==media['id'])
        assert d['evidence']['source_kind']=='mock'
        jobs.append({'media_id':media['id'],'fixture':name,'verdict':d['verdict'],'score':d['confidence'],'scene_timestamp':d['scene_timestamp'],'elapsed_seconds':round(time.monotonic()-start,2)})
        print(json.dumps({'event':'synthetic_job_complete',**jobs[-1]}),flush=True)
    except Exception as exc:
        failures.append({'elapsed_seconds':round(time.monotonic()-start,2),'error':type(exc).__name__,'detail':str(exc) if isinstance(exc,(RuntimeError,AssertionError)) else type(exc).__name__})
        print(json.dumps({'event':'synthetic_job_failed',**failures[-1]}),flush=True)
    remaining=min(60-(time.monotonic()-cycle_start),args.seconds-(time.monotonic()-start))
    if remaining>0:time.sleep(remaining)
result={'started_at':started,'ended_at':datetime.now(timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-start,2),
        'passed':len(jobs)>0 and not failures,'scope':'synthetic fixture uploads only; supplied Instagram/YouTube URLs not processed','jobs':jobs,'failures':failures}
(root/'.local/pipeline-exercise.json').write_text(json.dumps(result,indent=2));print(json.dumps({'event':'pipeline_exercise_complete','passed':result['passed'],'jobs':len(jobs),'duration_seconds':result['duration_seconds']}),flush=True)
raise SystemExit(0 if result['passed'] else 1)
