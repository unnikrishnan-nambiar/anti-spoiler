import json, logging, tempfile
from datetime import timedelta
from pathlib import Path
from redis import Redis
from sqlalchemy import select, delete
from .config import settings
from .queue import celery
from .db import Session, Media, Movie, Detection, SceneVector, AgentState, Preference, SourcePost, now
from . import storage
from .features import extract
from .agents.video import VideoMatchingAgent
from .agents.audio import AudioMatchingAgent
from .agents.decision import DecisionAgent
from .agents.alert import AlertAgent
from .agents.discovery import DiscoveryAgent, YouTubeAdapter, InstagramAdapter, FacebookAdapter, MockAdapter

logger=logging.getLogger('sceneguard')
def redis(): return Redis.from_url(settings().redis_url)
def state(name,status,detail=None):
    with Session.begin() as db:
        existing=db.get(AgentState,name)
        if not existing: db.add(AgentState(name=name,status=status,detail=detail or {}))
        else: existing.status=status; existing.detail=detail or {}; existing.updated_at=now()

def enqueue(media_id):
    # Database pending status is the durable outbox; broker failures are recovered by beat.
    try: process_media.delay(media_id)
    except Exception: logger.warning(json.dumps({'event':'enqueue_deferred','media_id':media_id}))

@celery.task(bind=True,max_retries=4)
def process_media(self,media_id):
    lock=redis().lock(f'media:{media_id}',timeout=1900,blocking_timeout=0)
    if not lock.acquire(blocking=False): return
    try:
        with Session.begin() as db:
            media=db.get(Media,media_id)
            if not media or media.status in ('ready','complete','failed'): return
            if media.attempts>=8:
                media.status='failed'; media.error='RecoveryAttemptsExhausted'; return
            if media.stage=='error' and media.updated_at+timedelta(seconds=min(300,10*2**max(0,media.attempts-1)))>now(): return
            media.status='processing'; media.stage='extracting'; media.attempts+=1; media.error=None
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'input.bin'; storage.download(media.object_key,path)
            features=extract(path,temp)
            feature_key=f"features/{media.id}/v{features['version']}.json"; storage.put_json(feature_key,features)
        with Session.begin() as db:
            media=db.get(Media,media_id); media.feature_key=feature_key; media.stage='matching'
            if media.kind in ('reference','promotional'):
                db.execute(delete(SceneVector).where(SceneVector.media_id==media_id))
                for frame in features['frames']:
                    if frame.get('embedding'):
                        db.add(SceneVector(media_id=media_id,timestamp=frame['t'],embedding=frame['embedding']))
                media.status='ready'; media.stage='indexed'
                state('video','idle',{'last_indexed_media':media_id,'embeddings':bool(settings().clip_model)})
                return
            refs=db.scalars(select(Media).join(Movie,Media.movie_id==Movie.id).where(
                Media.kind.in_(['reference','promotional']),Media.status=='ready',Movie.active.is_(True))).all()
            pref=db.get(Preference,'matching'); options=pref.value if pref else {}
            if not any(r.kind=='reference' for r in refs):
                # A candidate must wait for a usable movie index, rather than receive a false negative.
                media.status='waiting_reference'; media.stage='waiting_reference'; return
            state('video','running',{'media_id':media_id}); state('audio','running',{'media_id':media_id})
            candidates=[]; promo=[]
            for ref in refs:
                indexed=storage.get_json(ref.feature_key)
                visual=VideoMatchingAgent().match(features,indexed)
                audio=AudioMatchingAgent().match(features,indexed)
                evidence={'video':visual,'audio':audio,'reference_media_id':ref.id,'promotional':False,'candidate_video_available':True,'index_versions':{'candidate':features['version'],'reference':indexed['version']},'audio_quality':{'candidate':features.get('audio_quality'),'reference':indexed.get('audio_quality')}}
                movie=db.get(Movie,ref.movie_id)
                decision=DecisionAgent()._deterministic(evidence,threshold=options.get('match_threshold',settings().match_threshold),
                    review_threshold=options.get('review_threshold',settings().review_threshold),
                    audio_threshold=options.get('audio_threshold',settings().audio_threshold),spoiler_start=movie.spoiler_start)
                (promo if ref.kind=='promotional' else candidates).append((decision['confidence'],ref,evidence,decision))
            best=max(candidates,key=lambda x:x[0])
            approved=[p for p in promo if p[3]['verdict']=='confirmed']
            if approved:
                # A positive approved-promo match takes precedence. All movie evidence remains recorded.
                best=max(approved,key=lambda x:x[0]); best[2]['promotional']=True
                best[3].update(verdict='excluded_promotional',severity='none')
            score,ref,evidence,decision=best
            matched_movie=db.get(Movie,ref.movie_id)
            decision=DecisionAgent().decide(evidence,threshold=options.get('match_threshold',settings().match_threshold),review_threshold=options.get('review_threshold',settings().review_threshold),audio_threshold=options.get('audio_threshold',settings().audio_threshold),spoiler_start=matched_movie.spoiler_start)
            if decision['verdict']=='review' and settings().multimodal_url and settings().multimodal_model:
                from .agents.multimodal import MultimodalReviewer
                try:
                    ref_features=storage.get_json(ref.feature_key)
                    target=evidence['video']['frames'][0] if evidence['video']['frames'] else {'candidate_t':0,'reference_t':0}
                    c=min(features['frames'],key=lambda f:abs(f['t']-target['candidate_t']))
                    r=min(ref_features['frames'],key=lambda f:abs(f['t']-target['reference_t']))
                    evidence['multimodal']=MultimodalReviewer(settings().multimodal_url,settings().multimodal_api_key,settings().multimodal_model).review(c['thumbnail'],r['thumbnail'],{'video':evidence['video'],'audio':evidence['audio']})
                    # A generative model never promotes a weak match to confirmed.
                    if evidence['multimodal']['verdict']=='different_scene': decision['verdict']='no_match'
                except Exception as exc:
                    evidence['multimodal']={'status':'unavailable','error':type(exc).__name__}
            evidence['candidate_sha256']=media.sha256
            evidence['source_kind']='mock' if media.platform=='mock' else 'authorized_upload'
            state('decision','running',{'engine':decision['engine'],'laya':decision.get('laya',{'enabled':settings().laya_enabled})})
            AlertAgent().store(db,media,ref.movie_id if decision['verdict']!='no_match' else None,evidence,decision)
            media.status='complete'; media.stage='complete'; media.error=None
        for name in ('video','audio','decision','alert'): state(name,'idle',{'last_processed_media':media_id,**({'engine':decision['engine'],'laya':decision.get('laya')} if name=='decision' else {})})
        logger.info(json.dumps({'event':'media_complete','media_id':media_id,'verdict':decision['verdict']}))
    except Exception as exc:
        # Store a bounded class/message, never credential-bearing HTTP URLs or FFmpeg stderr.
        safe_error=type(exc).__name__
        with Session.begin() as db:
            media=db.get(Media,media_id)
            if media:
                media.status='failed' if self.request.retries>=self.max_retries or media.attempts>=8 else 'pending'
                media.error=safe_error; media.stage='error'
        state('video','error',{'media_id':media_id,'error':safe_error})
        state('audio','error',{'media_id':media_id,'error':safe_error})
        raise self.retry(exc=RuntimeError(safe_error),countdown=min(300,10*2**max(0,media.attempts-1)))
    finally:
        try: lock.release()
        except Exception: pass

@celery.task
def recover():
    with Session.begin() as db:
        has_refs=db.scalar(select(Media.id).where(Media.kind=='reference',Media.status=='ready').limit(1))
        pending=db.scalars(select(Media).where(Media.status.in_(['pending','processing','waiting_reference']))).all()
        for media in pending:
            stale=media.updated_at < now()-timedelta(minutes=35)
            due=media.stage!='error' or media.updated_at+timedelta(seconds=min(300,10*2**max(0,media.attempts-1)))<=now()
            if (media.status=='pending' and due) or (media.status=='processing' and stale) or (media.status=='waiting_reference' and has_refs):
                if media.attempts>=8: media.status='failed'; media.error='RecoveryAttemptsExhausted'; continue
                media.status='pending'; enqueue(media.id)
    state('scheduler','running',{'heartbeat':now().isoformat()})

@celery.task(bind=True,max_retries=4)
def discover(self):
    lock=redis().lock('discovery:lock',timeout=120,blocking_timeout=0)
    if not lock.acquire(blocking=False): return
    try:
        s=settings(); details={}
        for platform,adapter in [('youtube',YouTubeAdapter(s.youtube_api_key,s.youtube_query,s.youtube_channel_id)),
                                  ('instagram',InstagramAdapter()),('facebook',FacebookAdapter()),('mock',MockAdapter())]:
            # Distributed rate limit survives worker restarts; respects the selected 10-minute search cadence.
            if platform=='youtube' and not redis().set('youtube:rate_limit','1',nx=True,ex=600): continue
            with Session.begin() as db:
                record=db.get(AgentState,f'discovery:{platform}')
                checkpoint=record.detail.get('checkpoint',{}) if record else {}
                result=DiscoveryAgent(adapter).discover(checkpoint)
                for post in result.posts:
                    exists=db.scalar(select(SourcePost.id).where(SourcePost.platform==platform,SourcePost.external_id==post['external_id']))
                    if not exists: db.add(SourcePost(platform=platform,**post))
                detail={'checkpoint':result.checkpoint,'coverage':result.detail,'discovered':len(result.posts)}
                if record: record.status=result.status; record.detail=detail; record.updated_at=now()
                else: db.add(AgentState(name=f'discovery:{platform}',status=result.status,detail=detail))
                details[platform]=result.status
        state('discovery','running',details)
    except Exception as exc:
        state('discovery','error',{'error':str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__})
        # Rate-limit expiry remains respected even on retries.
        raise self.retry(exc=RuntimeError(type(exc).__name__),countdown=600)
    finally:
        try: lock.release()
        except Exception: pass
