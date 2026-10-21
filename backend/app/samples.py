"""Generate only synthetic footage. No movies, social posts, or detections are bundled."""
import json, subprocess, argparse
from pathlib import Path
import cv2
import numpy as np
from scipy.io import wavfile

def run(*args): subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
def generate(output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(7); width,height,fps,seconds=640,360,15,24
    texture=rng.integers(0,255,(height,width,3),dtype=np.uint8)
    texture=cv2.GaussianBlur(texture,(5,5),0)
    for _ in range(100):
        x,y=rng.integers([0,0],[width,height]); color=tuple(map(int,rng.integers(0,255,3)))
        cv2.circle(texture,(int(x),int(y)),int(rng.integers(3,15)),color,-1)
    video=output/'silent.avi'; writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'MJPG'),fps,(width,height))
    for n in range(fps*seconds):
        frame=texture.copy(); t=n/fps
        cv2.rectangle(frame,(int(40+t*8)%500,90),(int(40+t*8)%500+90,190),(245,245,245),-1)
        cv2.putText(frame,f'SYNTHETIC SCENE {int(t):02d}',(40,310),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,0),3)
        # Different scene content over time, while retaining useful non-repeating geometry.
        shift=int(t//2)*7; frame=np.roll(frame,shift,axis=1)
        writer.write(frame)
    writer.release()
    rate=11025; samples=[]
    for i in range(seconds*4):
        t=np.arange(rate//4)/rate
        frequencies=rng.choice(np.arange(240,3500,35),4,replace=False)
        tone=sum(np.sin(2*np.pi*f*t+rng.random()*6.28) for f in frequencies)
        samples.append(tone*np.hanning(len(t)))
    audio=np.concatenate(samples); audio=audio/max(abs(audio))*.7
    wavfile.write(output/'audio.wav',rate,(audio*32767).astype(np.int16))
    run('ffmpeg','-y','-v','error','-i',str(video),'-i',str(output/'audio.wav'),'-c:v','libx264','-preset','fast','-crf','18','-c:a','aac',str(output/'reference.mp4'))
    run('ffmpeg','-y','-v','error','-ss','6','-i',str(output/'reference.mp4'),'-t','10','-vf','crop=500:290:65:30,scale=480:278,perspective=x0=8:y0=4:x1=W-5:y1=0:x2=0:y2=H-5:x3=W:y3=H', '-af','highpass=f=180,lowpass=f=4200,aeval=val(0)+0.04*(random(0)-0.5),aformat=channel_layouts=mono','-c:v','libx264','-crf','29','-c:a','aac',str(output/'candidate.mp4'))
    run('ffmpeg','-y','-v','error','-ss','6','-i',str(output/'reference.mp4'),'-t','10','-c:v','libx264','-c:a','aac',str(output/'promotional.mp4'))
    run('ffmpeg','-y','-v','error','-f','lavfi','-i','testsrc2=size=480x278:rate=15:duration=10','-f','lavfi','-i','sine=frequency=100:duration=10','-c:v','libx264','-c:a','aac',str(output/'unrelated.mp4'))
    for file in ('silent.avi','audio.wav'): (output/file).unlink()
    (output/'manifest.json').write_text(json.dumps({'synthetic':True,'reference':'reference.mp4','candidate':'candidate.mp4','promotional':'promotional.mp4','unrelated':'unrelated.mp4','expected_scene_offset_seconds':6,'post_url':'https://example.invalid/synthetic-scene'},indent=2))
    return output
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='.local/samples');generate(p.parse_args().output)
