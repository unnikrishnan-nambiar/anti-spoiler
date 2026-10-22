"""Opt-in live native demo smoke: synthetic media, actual API/FFmpeg/Laya.
Creates retained synthetic movie/reference records. Requires a ready local API.
"""
import argparse
import base64
import json
from pathlib import Path
import sys
import time

import cv2
import httpx
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args()
    env=dotenv_values(ROOT/'.env')
    with httpx.Client(base_url=f'http://127.0.0.1:{args.port}',timeout=120,trust_env=False) as client:
        response=client.get('/health/ready'); response.raise_for_status()
        assert client.get('/movies').status_code==401
        response=client.post('/auth/login',json={'username':env.get('ADMIN_USERNAME','admin'),'password':env['ADMIN_PASSWORD']})
        response.raise_for_status(); client.headers['Authorization']='Bearer '+response.json()['access_token']
        from app.samples import generate
        samples=generate(ROOT/'.local/native-smoke-samples')
        response=client.post('/movies',json={'title':'SYNTHETIC native smoke '+str(int(time.time()))}); response.raise_for_status()
        movie_id=response.json()['id']
        with (samples/'reference.mp4').open('rb') as file:
            response=client.post('/media',data={'kind':'reference','movie_id':str(movie_id),'authorized':'true'},files={'file':('reference.mp4',file,'video/mp4')})
        response.raise_for_status(); media_id=response.json()['id']
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            response=client.get('/media?limit=500'); response.raise_for_status()
            media=next(m for m in response.json() if m['id']==media_id)
            if media['status']=='ready': break
            if media['status']=='failed': raise RuntimeError('Indexing failed: '+str(media['error']))
            time.sleep(.5)
        else: raise RuntimeError('Reference indexing timed out')
        response=client.get(f'/media/{media_id}/index-summary'); response.raise_for_status()
        assert response.json()['frames']>2
        cap=cv2.VideoCapture(str(samples/'reference.mp4')); frames=[]
        for t in (6,8):
            cap.set(cv2.CAP_PROP_POS_MSEC,t*1000); ok,frame=cap.read(); assert ok
            frames.append({'png':base64.b64encode(cv2.imencode('.png',frame)[1]).decode(),'time':t})
        cap.release()
        response=client.post('/browser/match',json={'reference_id':media_id,'post_url':'https://www.instagram.com/reel/SYNTHETIC_NATIVE_SMOKE/','frames':frames})
        response.raise_for_status(); result=response.json()
        assert result['evidence']['matched_frames']>=2,result
        assert result['laya']['status']=='used',result['laya']
        assert result['laya']['revision']=='7b928d828b7b0e022f929d9bd2e44165aa270148'
        report={'scope':'Synthetic reference-derived frames; real API, FFmpeg and Laya; no Instagram capture',
                'movie_id':movie_id,'reference_id':media_id,'verdict':result['verdict'],
                'matched_frames':result['evidence']['matched_frames'],'laya':result['laya']}
        (ROOT/'.local/native-smoke-result.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))

if __name__=='__main__': main()
