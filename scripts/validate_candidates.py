"""Validate controlled candidate clips through the running deployment, never social discovery.
Input: a report produced by evaluate_reference.py, with clips in the same directory.
Requires an authorized development workspace. Creates labeled mock evidence records.
"""
import argparse,json,time,uuid
from pathlib import Path
import httpx
from dotenv import dotenv_values
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('report',type=Path);p.add_argument('--movie-id',type=int,required=True)
p.add_argument('--base-url',default='http://127.0.0.1:3000');p.add_argument('--require-laya',action='store_true')
p.add_argument('--output',type=Path,default=Path('.local/deployed-candidate-validation.json'))
a=p.parse_args();root=Path(__file__).resolve().parents[1];env=dotenv_values(root/'.env')
report=json.loads(a.report.read_text());results=[]
with httpx.Client(base_url=a.base_url.rstrip('/')+'/api/',trust_env=False,timeout=60,
 headers={'Origin':env.get('APP_ORIGIN','http://localhost:3000')}) as client:
 r=client.post('auth/login',json={'username':env.get('ADMIN_USERNAME','admin'),'password':env['ADMIN_PASSWORD']});r.raise_for_status()
 for case in report['cases']:
  clip=(a.report.parent/case['fixture']).resolve()
  if clip.parent!=a.report.parent.resolve():raise ValueError('Clip must be beside its report')
  url='https://example.invalid/controlled-evaluation/'+uuid.uuid4().hex
  def submit():
   with clip.open('rb') as file:
    response=client.post('media',files={'file':(clip.name,file,'video/mp4')},data={'kind':'candidate','platform':'mock','post_url':url,'authorized':'true'})
   response.raise_for_status();return response.json()
  media=submit();assert submit()['id']==media['id'],'Upload deduplication failed'
  deadline=time.monotonic()+180
  while time.monotonic()<deadline:
   r=client.get('media');r.raise_for_status();record=next(m for m in r.json() if m['id']==media['id'])
   if record['status']=='complete':break
   if record['status']=='failed':raise RuntimeError('Candidate processing failed: '+str(record['error']))
   time.sleep(1)
  else:raise RuntimeError('Candidate processing timed out')
  r=client.get('detections',params={'q':url,'limit':100});r.raise_for_status();matches=[d for d in r.json() if d['media_id']==media['id']]
  assert len(matches)==1,'Expected one persisted decision'
  d=matches[0];decision=d['evidence']['decision']
  assert d['movie_id']==a.movie_id and d['verdict']=='confirmed','Expected content match was not confirmed'
  assert abs(d['scene_timestamp']-case['known_reference_offset'])<=2,'Incorrect reference timestamp'
  if a.require_laya:assert decision['engine']=='deterministic+laya','Laya did not execute successfully'
  r=client.get('alerts');r.raise_for_status();assert len([x for x in r.json() if x['detection_id']==d['id']])==1,'Expected one deduplicated alert (enable test alerts)'
  result={'fixture':clip.name,'media_id':d['media_id'],'expected_timestamp':case['known_reference_offset'],
   'matched_timestamp':d['scene_timestamp'],'movie_id':d['movie_id'],'verdict':d['verdict'],'evidence_similarity':d['confidence'],'decision':decision}
  results.append(result);print(json.dumps(result),flush=True)
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps({'scope':'Controlled authorized-reference derivatives, NOT Instagram captures','passed':bool(results),'results':results},indent=2))
if not results:raise SystemExit('No cases supplied')
