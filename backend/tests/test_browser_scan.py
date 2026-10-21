import base64,struct
from types import SimpleNamespace
import cv2
import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app import browser_scan as scan
from app.security import current_user

URL='https://www.instagram.com/reel/test_clip/'
def frame(t=0):
    raw=cv2.imencode('.png',np.full((64,64,3),127,np.uint8))[1].tobytes()
    return {'png':base64.b64encode(raw).decode(),'time':t}
def body():return {'reference_id':1,'post_url':URL,'frames':[frame(),frame(2)]}
def test_rejects_static_time_and_non_instagram_urls():
    for changes in ({'frames':[frame(),frame()]},{'post_url':'https://attacker.example/reel/test/'},{'frames':[frame(),frame(10)]}):
        with pytest.raises(ValidationError):scan.BrowserCheck(**{**body(),**changes})
def test_bounded_png_header_before_decode(monkeypatch):
    raw=b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+struct.pack('>II',50000,50000)
    monkeypatch.setattr(cv2,'imdecode',lambda *_:pytest.fail('Oversized image reached decoder'))
    with pytest.raises(Exception) as exc:scan.decode_frame(scan.CapturedFrame(png=base64.b64encode(raw).decode(),time=0))
    assert exc.value.status_code==422

def setup_client(monkeypatch,choice='confirmed',failure=False,promo=False):
    scan.reference_features.cache_clear()
    app=FastAPI();app.include_router(scan.router)
    class DB:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,model,id):
            if model is scan.Media:return SimpleNamespace(id=1,kind='reference',status='ready',movie_id=3,feature_key='ref',updated_at='test')
            if model is scan.Movie:return SimpleNamespace(id=3,active=True,title='Test')
            return None
        def scalars(self,q):return [SimpleNamespace(feature_key='promo',updated_at='test')] if promo else []
    monkeypatch.setattr(scan,'Session',DB)
    monkeypatch.setattr(scan.storage,'get_json',lambda *_:{'frames':[{}]*2})
    monkeypatch.setattr(scan.VideoMatchingAgent,'match',lambda *_:{'score':.9,'timestamp':30,'matched_frames':2,'frames':[]})
    monkeypatch.setattr(scan.settings(),'laya_enabled',True);monkeypatch.setattr(scan.settings(),'laya_service_url','http://laya:8001')
    def review(self,evidence,timeout):
        assert timeout==4 and 'frames' not in evidence['video']
        assert len(str(evidence))<400
        if failure:raise TimeoutError()
        return {'choice':choice,'usage':{'input_tokens':150,'output_tokens':0}}
    monkeypatch.setattr(scan.LayaEvidenceReviewer,'review',review)
    return app,TestClient(app)

def test_auth_and_viewer_denied(monkeypatch):
    app,c=setup_client(monkeypatch)
    assert c.post('/browser/match',json=body()).status_code==401
    app.dependency_overrides[current_user]=lambda:SimpleNamespace(role='viewer')
    assert c.post('/browser/match',json=body()).status_code==403

@pytest.mark.parametrize('choice,failure,expected',[('confirmed',False,'visual_match'),('review',False,'review'),('confirmed',True,'review')])
def test_laya_review_and_timeout_are_explicit(monkeypatch,choice,failure,expected):
    app,c=setup_client(monkeypatch,choice,failure)
    app.dependency_overrides[current_user]=lambda:SimpleNamespace(role='analyst')
    r=c.post('/browser/match',json=body());assert r.status_code==200,r.text
    assert r.json()['verdict']==expected
    assert r.json()['laya']['status']==('unavailable' if failure else 'used')

def test_promotional_exclusion_survives_model_choice(monkeypatch):
    app,c=setup_client(monkeypatch,promo=True)
    app.dependency_overrides[current_user]=lambda:SimpleNamespace(role='analyst')
    assert c.post('/browser/match',json=body()).json()['verdict']=='excluded_promotional'

def test_visual_only_laya_does_not_treat_missing_audio_as_conflict():
    from app.agents.laya import LayaEvidenceReviewer
    class Agent:
        def predict(self,state,questions):
            assert state['audio'] is None
            assert 'Audio was not captured' in questions['verification']['instructions']
            return {'answers':{'verification':{'choice':'review','answer_confidence':.5}},'usage':{'input_tokens':123,'output_tokens':0}}
    result=LayaEvidenceReviewer(Agent()).review({'video':{'score':.9,'matched_frames':2,'timestamp':30},'audio':{'score':0,'timestamp':0},'audio_available':False})
    assert result['usage']=={'input_tokens':123,'output_tokens':0}
