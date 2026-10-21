"""Create bounded local reference snippets, never post them to social platforms."""
import argparse,hashlib,json,subprocess,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=float,default=8);p.add_argument('--stride',type=float,default=30);a=p.parse_args()
if a.seconds<=0 or a.stride<=0:raise SystemExit('seconds and stride must be positive')
os.umask(0o077);a.output.mkdir(parents=True,exist_ok=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(a.source)]));duration=float(probe['format']['duration']);entries=[];start=0
while start+a.seconds<=duration:
 target=a.output/f'snippet-{int(start):04d}s.mp4'
 subprocess.run(['ffmpeg','-y','-v','error','-nostdin','-ss',str(start),'-i',str(a.source),'-t',str(a.seconds),'-c:v','libx264','-preset','fast','-crf','20','-c:a','aac','-threads','2',str(target)],check=True)
 decoded=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(target)]))
 entries.append({'file':target.name,'reference_start_seconds':start,'duration_seconds':float(decoded['format']['duration']),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()});start+=a.stride
report={'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'source_duration_seconds':duration,'snippets':entries,'scope':'Local reference material only; not Instagram detections'}
(a.output/'manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
