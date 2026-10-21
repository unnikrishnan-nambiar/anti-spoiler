"""Bounded visual checks of frames captured from a user-visible playing reel.
No social-network requests, media URL downloads or automatic enforcement.
"""
import base64,struct,time,threading,json
from functools import lru_cache
from .config import settings
from .agents.laya import LayaEvidenceReviewer
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,model_validator
import cv2
import numpy as np
from .security import roles
from .db import Session,Media,Movie,Preference
from sqlalchemy import select
from . import storage
from .features import frame_feature
from .agents.video import VideoMatchingAgent
from .agents.decision import DecisionAgent
router=APIRouter(prefix='/browser',tags=['browser scanning'])
_slots=threading.BoundedSemaphore(2)

class CapturedFrame(BaseModel):
    # PNG IHDR allows dimension checks before native image decoding.
    png:str=Field(max_length=1400000)
    time:float=Field(ge=0,le=7200)
class BrowserCheck(BaseModel):
    reference_id:int=Field(gt=0)
    post_url:str=Field(pattern=r'^https://www\.instagram\.com/(?:reel|reels|p)/[A-Za-z0-9_-]+/$')
    frames:list[CapturedFrame]=Field(min_length=2,max_length=3)
    @model_validator(mode='after')
    def ordered(self):
        if any(b.time-a.time<.5 or b.time-a.time>4 for a,b in zip(self.frames,self.frames[1:])):
            raise ValueError('Require distinct advancing playback frames, 0.5–4 seconds apart')
        return self

def decode_frame(frame):
    try:
        raw=base64.b64decode(frame.png,validate=True)
        if raw[:8]!=b'\x89PNG\r\n\x1a\n' or raw[12:16]!=b'IHDR':raise ValueError()
        w,h=struct.unpack('>II',raw[16:24])
        if not 32<=w<=640 or not 32<=h<=640:raise ValueError()
        decoded=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
        if decoded is None or decoded.shape[:2]!=(h,w):raise ValueError()
        return frame_feature(decoded,frame.time)
    except (ValueError,struct.error,cv2.error):raise HTTPException(422,'Invalid or oversized captured PNG')

@lru_cache(maxsize=3)
def reference_features(key,revision):
    data=storage.get_json(key)
    for frame in data['frames']:
        frame['descriptors']=np.asarray(frame.get('descriptors',[]),dtype=np.uint8)
    return data

def compact_evidence(evidence):
    return {'candidate_video_available':True,'audio_available':False,
        'video':{k:evidence['video'][k] for k in ('score','timestamp','matched_frames')},
        'audio':{'score':0,'timestamp':0,'aligned_landmarks':0},'promotional':bool(evidence.get('promotional'))}

@router.post('/match')
def match(body:BrowserCheck,user=Depends(roles('admin','analyst'))):
    if not _slots.acquire(blocking=False):raise HTTPException(429,'Matcher busy; skip this sample and retry later')
    try:
        started=time.monotonic()
        with Session() as db:
            media=db.get(Media,body.reference_id)
            if not media or media.kind!='reference' or media.status!='ready':raise HTTPException(409,'Select an indexed reference first')
            movie=db.get(Movie,media.movie_id)
            promos=list(db.scalars(select(Media).where(Media.movie_id==media.movie_id,Media.kind=='promotional',Media.status=='ready')))
            preference=db.get(Preference,'matching'); options=preference.value if preference else {}
            if not movie or not movie.active:raise HTTPException(409,'Reference movie is paused')
        indexed=reference_features(media.feature_key,str(media.updated_at))
        if len(indexed['frames'])>450:raise HTTPException(422,'One-minute mode supports references up to 15 minutes; use a shorter reference excerpt')
        frames=[decode_frame(f) for f in body.frames]
        for frame in frames:frame['descriptors']=np.asarray(frame['descriptors'],dtype=np.uint8)
        # Times start at the first sampled frame, so returned offset is that frame's reference position.
        origin=frames[0]['t']
        for f in frames:f['t']-=origin
        visual=VideoMatchingAgent().match({'frames':frames},indexed)
        evidence={'video':visual,'audio':{'score':0,'timestamp':0,'aligned_landmarks':0},'candidate_video_available':True}
        thresholds={'threshold':options.get('match_threshold',settings().match_threshold),'review_threshold':options.get('review_threshold',settings().review_threshold)}
        decision=DecisionAgent()._deterministic(evidence,**thresholds)
        if decision['verdict'] in ('confirmed','review'):
            remaining=450-len(indexed['frames'])
            for promo in promos:
                approved=reference_features(promo.feature_key,str(promo.updated_at));remaining-=len(approved['frames'])
                if remaining<0:raise HTTPException(422,'Reference and approved promo library exceed fast-scan budget')
                pv=VideoMatchingAgent().match({'frames':frames},approved)
                if DecisionAgent()._deterministic({'video':pv,'audio':evidence['audio']},**thresholds)['verdict']=='confirmed':
                    evidence['promotional']=True;decision['verdict']='excluded_promotional';break

        model_started=time.monotonic()
        laya={'status':'unavailable','reason':'Private Laya service is not configured'}
        if settings().laya_enabled and settings().laya_service_url:
            try:
                laya=LayaEvidenceReviewer().review(compact_evidence(evidence),timeout=4.0)
                laya['status']='used'
                if decision['verdict']=='confirmed' and laya['choice']!='confirmed':decision['verdict']='review'
            except Exception as exc:laya={'status':'unavailable','error':type(exc).__name__}
        # A model outage is visible and cannot quietly become a model-reviewed match.
        if laya['status']!='used' and decision['verdict']=='confirmed':decision['verdict']='review'
        laya['elapsed_seconds']=round(time.monotonic()-model_started,3)
        laya['evidence_bytes']=len(json.dumps(compact_evidence(evidence),separators=(',',':')).encode())
        # Only compact numbers reach the model; thumbnails and frame correspondences are omitted.

        return {'post_url':body.post_url,'reference_id':media.id,'movie_id':movie.id,'movie_title':movie.title,
            'verdict':'visual_match' if decision['verdict']=='confirmed' else ('excluded_promotional' if decision['verdict']=='excluded_promotional' else ('review' if decision['verdict']=='review' else 'no_match_in_sample')),
            'reference_timestamp':visual['timestamp'],'sampled_reel_time':origin,'similarity':visual['score'],
            'score_type':'uncalibrated_visual_similarity','laya':laya,'evidence':visual,'elapsed_seconds':round(time.monotonic()-started,3),
            'scope':'User-visible sampled frames only; audio is not captured; Laya status is explicit; review leads only, no enforcement or alert generated'}
    finally:_slots.release()
