"""Native extension API with real SQLite, filesystem and FFmpeg; model mocked here.
Live model verification is a separate opt-in smoke test.
"""
import base64
import subprocess

import cv2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def demo(tmp_path,monkeypatch):
    from app import demo, security, browser_scan
    config=demo.settings()
    monkeypatch.setattr(config,'database_url','sqlite:///'+str(tmp_path/'demo.db'))
    objects=tmp_path/'objects'; objects.mkdir()
    monkeypatch.setattr(config,'local_storage_path',str(objects))
    monkeypatch.setattr(config,'laya_service_url','http://127.0.0.1:8001')
    monkeypatch.setattr(config,'laya_enabled',True)
    engine=create_engine(config.database_url)
    session=sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(demo,'engine',engine)
    for module in (demo,security,browser_scan): monkeypatch.setattr(module,'Session',session)
    demo._login_attempts.clear(); browser_scan.reference_features.cache_clear()
    with TestClient(demo.app) as client: yield client,config,tmp_path
    engine.dispose()

def login(client,config):
    result=client.post('/auth/login',json={'username':config.admin_username,'password':config.admin_password})
    assert result.status_code==200
    client.headers['Authorization']='Bearer '+result.json()['access_token']

def test_reference_upload_index_and_visual_check(demo,monkeypatch):
    client,config,folder=demo
    assert client.get('/movies').status_code==401
    login(client,config)
    movie=client.post('/movies',json={'title':'SYNTHETIC native demo'}).json()
    from app.samples import generate
    video=generate(folder/'samples')/'reference.mp4'
    form={'kind':'reference','movie_id':movie['id'],'authorized':'true'}
    with video.open('rb') as file:
        result=client.post('/media',data={**form,'authorized':'false'},files={'file':('reference.mp4',file)})
    assert result.status_code==422
    with video.open('rb') as file: result=client.post('/media',data=form,files={'file':('reference.mp4',file)})
    assert result.status_code==202,result.text
    media_id=result.json()['id']
    media=client.get('/media').json()[0]
    assert media['status']=='ready',media
    summary=client.get(f'/media/{media_id}/index-summary').json()
    assert summary['frames']==12 and summary['audio_version']==3
    assert client.get('/movies').json()[0]['media'][0]['id']==media_id
    cap=cv2.VideoCapture(str(video)); frames=[]
    for t in (0,2):
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000); ok,frame=cap.read(); assert ok
        frames.append({'png':base64.b64encode(cv2.imencode('.png',frame)[1]).decode(),'time':t})
    cap.release()
    from app import browser_scan
    calls=[]
    def review(self,evidence,timeout):
        calls.append(evidence)
        return {'choice':'review','usage':{'input_tokens':110,'output_tokens':0}}
    monkeypatch.setattr(browser_scan.LayaEvidenceReviewer,'review',review)
    result=client.post('/browser/match',json={'reference_id':media_id,'post_url':'https://www.instagram.com/reel/synthetic_native/','frames':frames})
    assert result.status_code==200,result.text
    assert result.json()['laya']['status']=='used' and calls[0]['audio_available'] is False
    assert result.json()['evidence']['matched_frames']>=2
    assert result.json()['verdict']=='review'

def test_login_rate_limit_and_storage_escape(demo):
    client,config,_=demo
    for _ in range(20):
        assert client.post('/auth/login',json={'username':'missing','password':'bad'}).status_code==401
    assert client.post('/auth/login',json={'username':'missing','password':'bad'}).status_code==429
    from app.storage import local_path
    for key in ('../escape','/etc/passwd','.'):
        with pytest.raises(ValueError): local_path(key)

def test_readiness_requires_model_and_valid_upload(demo,monkeypatch):
    client,config,_=demo
    assert client.get('/health/ready').status_code==503
    login(client,config)
    movie=client.post('/movies',json={'title':'invalid upload'}).json()
    result=client.post('/media',data={'kind':'reference','movie_id':movie['id'],'authorized':'true'},files={'file':('invalid.mp4',b'not video')})
    assert result.status_code==422
    assert client.get('/media').json()==[]
