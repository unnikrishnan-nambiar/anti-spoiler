"""Reproducible content-matching evaluation on transformed copies of an owned reference.
This never labels derived evaluation clips as real Instagram discoveries.
"""
import argparse,json,subprocess,tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.features import extract
from app.agents.video import VideoMatchingAgent
from app.agents.audio import AudioMatchingAgent
from app.agents.decision import DecisionAgent
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--output',type=Path,default=Path('.local/real-reference-evaluation'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
def ffmpeg(*args):subprocess.run(['ffmpeg','-nostdin','-y','-v','error',*args],check=True)
with tempfile.TemporaryDirectory() as temp:
 reference=extract(a.source,Path(temp));results=[]
 for offset in (30,60,90,150):
  path=a.output/f'controlled-offset-{offset}.mp4'
  ffmpeg('-ss',str(offset),'-i',str(a.source),'-t','8','-vf','crop=340:190:40:20,scale=426:238,perspective=x0=4:y0=2:x1=W-2:y1=0:x2=0:y2=H-2:x3=W:y3=H','-af','volume=0.35,aeval=val(0)+0.02*(random(0)-0.5),aformat=channel_layouts=mono','-c:v','libx264','-crf','29','-preset','fast','-c:a','aac','-threads','2',str(path))
  with tempfile.TemporaryDirectory() as part:candidate=extract(path,part)
  video=VideoMatchingAgent().match(candidate,reference);audio=AudioMatchingAgent().match(candidate,reference)
  decision=DecisionAgent().decide({'video':video,'audio':audio,'candidate_video_available':True})
  results.append({'fixture':path.name,'known_reference_offset':offset,'video':video,'audio':audio,'decision':decision})
 report={'scope':'Transformed copies of user-provided footage; NOT Instagram detections','reference_frames':len(reference['frames']),'reference_audio_quality':reference['audio_quality'],'cases':results}
 (a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
