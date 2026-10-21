import hashlib, json, logging, os, tempfile, time, uuid
from datetime import timedelta
from urllib.parse import urlsplit
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, func, text
from redis import Redis
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from .config import settings
from .db import Session, Movie, Media, Detection, Alert, AgentState, SourcePost, Preference, User, now
from .security import current_user, roles, verify_password, issue_token, hash_password
from . import storage
from .tasks import enqueue, discover
from .agents.decision import DecisionAgent

logging.basicConfig(level=logging.INFO,format='%(message)s')
app=FastAPI(title='SceneGuard AI',version='0.1.0',docs_url='/docs')
requests=Counter('sceneguard_requests_total','HTTP requests',['method','status'])
latency=Histogram('sceneguard_request_seconds','HTTP latency')

@app.middleware('http')
async def instrumentation(request:Request,call_next):
    start=time.monotonic(); response=await call_next(request)
    requests.labels(request.method,str(response.status_code)).inc(); latency.observe(time.monotonic()-start)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    logging.getLogger('sceneguard').info(json.dumps({'event':'http','method':request.method,'path':request.url.path,'status':response.status_code,'elapsed_ms':round((time.monotonic()-start)*1000)}))
    return response

class Login(BaseModel):
    username:str=Field(max_length=100)
    password:str=Field(max_length=1000)
class MovieInput(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    spoiler_start:float=Field(default=0,ge=0)
class MovieUpdate(BaseModel):
    active:bool
class Preferences(BaseModel):
    match_threshold:float=Field(default=.75,ge=.5,le=1)
    review_threshold:float=Field(default=.45,ge=.1,le=.9)
    audio_threshold:float=Field(default=.2,ge=.01,le=1)
    alerts_enabled:bool=True
    @model_validator(mode='after')
    def ordered(self):
        if self.review_threshold>=self.match_threshold: raise ValueError('review threshold must be lower than match threshold')
        return self
class UserInput(BaseModel):
    username:str=Field(min_length=1,max_length=100)
    password:str=Field(min_length=12,max_length=1000)
    role:str=Field(pattern='^(admin|analyst|viewer)$')

def serialize(row):
    return {c.name:(getattr(row,c.name).isoformat() if hasattr(getattr(row,c.name),'isoformat') else getattr(row,c.name)) for c in row.__table__.columns}

def redis_client(): return Redis.from_url(settings().redis_url,socket_connect_timeout=3,socket_timeout=3)

@app.get('/health/live')
def live(): return {'status':'ok'}
@app.get('/health/ready')
def ready():
    try:
        with Session() as db: db.execute(text('SELECT 1'))
        redis_client().ping(); storage.client().head_bucket(Bucket=settings().s3_bucket)
        return {'status':'ready'}
    except Exception: raise HTTPException(503,'Dependency unavailable')
@app.get('/metrics')
def metrics(user=Depends(roles('admin'))): return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)

@app.post('/auth/login')
def login(body:Login,request:Request):
    key='login:'+hashlib.sha256((request.client.host+':'+body.username).encode()).hexdigest()
    r=redis_client(); count=r.incr(key)
    if count==1: r.expire(key,300)
    if count>20: raise HTTPException(429,'Too many login attempts; retry in 5 minutes')
    with Session() as db: user=db.scalar(select(User).where(User.username==body.username))
    # Perform password work even for unknown users.
    if not user:
        hashlib.pbkdf2_hmac('sha256',body.password.encode(),b'unknown-user',600000)
        raise HTTPException(401,'Invalid credentials')
    if not verify_password(body.password,user.password_hash): raise HTTPException(401,'Invalid credentials')
    return {'access_token':issue_token(user),'token_type':'bearer','role':user.role,'expires_in':3600}
@app.get('/auth/me')
def me(user=Depends(current_user)): return {'username':user.username,'role':user.role}
@app.post('/users',status_code=201)
def add_user(body:UserInput,user=Depends(roles('admin'))):
    with Session.begin() as db:
        if db.scalar(select(User.id).where(User.username==body.username)): raise HTTPException(409,'Username exists')
        item=User(username=body.username,password_hash=hash_password(body.password),role=body.role); db.add(item); db.flush()
        return {'id':item.id,'username':item.username,'role':item.role}

@app.get('/overview')
def overview(user=Depends(current_user)):
    with Session() as db:
        return {'active_movies':db.scalar(select(func.count()).select_from(Movie).where(Movie.active.is_(True))),
                'detected_clips':db.scalar(select(func.count()).select_from(Detection).where(Detection.verdict=='confirmed')),
                'review_clips':db.scalar(select(func.count()).select_from(Detection).where(Detection.verdict=='review')),
                'pending_media':db.scalar(select(func.count()).select_from(Media).where(Media.status.in_(['pending','processing','waiting_reference']))),
                'alerts':db.scalar(select(func.count()).select_from(Alert).where(Alert.acknowledged.is_(False)))}
@app.get('/movies')
def movies(user=Depends(current_user)):
    with Session() as db:
        return [{**serialize(m),'media':[serialize(r) for r in db.scalars(select(Media).where(Media.movie_id==m.id)).all()]} for m in db.scalars(select(Movie).order_by(Movie.id.desc())).all()]
@app.post('/movies',status_code=201)
def create_movie(body:MovieInput,user=Depends(roles('admin','analyst'))):
    with Session.begin() as db:
        movie=Movie(**body.model_dump()); db.add(movie); db.flush(); return serialize(movie)
@app.patch('/movies/{movie_id}')
def update_movie(movie_id:int,body:MovieUpdate,user=Depends(roles('admin','analyst'))):
    with Session.begin() as db:
        movie=db.get(Movie,movie_id)
        if not movie: raise HTTPException(404,'Movie not found')
        movie.active=body.active; return serialize(movie)

def validate_url(platform,url):
    if platform=='mock':
        if not url.startswith('https://example.invalid/'): raise HTTPException(422,'Mock links must use https://example.invalid/')
        return
    host=urlsplit(url).hostname
    hosts={'youtube':{'www.youtube.com','youtube.com','youtu.be'},'instagram':{'www.instagram.com','instagram.com'},'facebook':{'www.facebook.com','facebook.com','fb.watch'}}
    if platform not in hosts or urlsplit(url).scheme!='https' or host not in hosts[platform]:
        raise HTTPException(422,'A valid HTTPS platform post URL is required')

@app.post('/media',status_code=202)
def upload(file:UploadFile=File(...),kind:str=Form(...),movie_id:int|None=Form(None),platform:str=Form('mock'),
           post_url:str=Form('https://example.invalid/authorized-upload'),authorized:bool=Form(False),user=Depends(roles('admin','analyst'))):
    if not authorized: raise HTTPException(422,'Confirm you are authorized to process this footage')
    if kind not in ('reference','promotional','candidate'): raise HTTPException(422,'Invalid media kind')
    if kind!='candidate' and movie_id is None: raise HTTPException(422,'movie_id required')
    if kind=='candidate': validate_url(platform,post_url)
    with Session() as db:
        if movie_id is not None and not db.get(Movie,movie_id): raise HTTPException(404,'Movie not found')
    digest=hashlib.sha256(); size=0
    with tempfile.NamedTemporaryFile(suffix='.bin') as temp:
        while chunk:=file.file.read(1024*1024):
            size+=len(chunk)
            if size>settings().max_media_bytes: raise HTTPException(413,'Media exceeds upload size limit')
            digest.update(chunk); temp.write(chunk)
        if not size: raise HTTPException(422,'Empty upload')
        temp.flush()
        from .features import probe
        try: probe(temp.name)
        except Exception: raise HTTPException(422,'Invalid or unsupported video; maximum duration exceeded or probe failed')
        sha=digest.hexdigest()
        # Serialize equivalent uploads across API instances. Prevent duplicate media/notifications.
        with redis_client().lock(f'upload:{sha}:{kind}:{movie_id}:{hashlib.sha256(post_url.encode()).hexdigest()}',timeout=90,blocking_timeout=5):
            with Session() as db:
                statement=select(Media).where(Media.sha256==sha,Media.kind==kind,Media.movie_id==movie_id)
                if kind=='candidate': statement=statement.where(Media.post_url==post_url,Media.platform==platform)
                existing=db.scalar(statement)
                if existing: return serialize(existing)
            key=f'media/{uuid.uuid4().hex}.bin'; storage.put_file(temp.name,key)
            try:
                with Session.begin() as db:
                    item=Media(movie_id=movie_id,kind=kind,object_key=key,sha256=sha,
                               dedup_key=hashlib.sha256(json.dumps([sha,kind,movie_id,platform if kind=='candidate' else None,post_url if kind=='candidate' else None]).encode()).hexdigest(),
                               platform=platform if kind=='candidate' else None,post_url=post_url if kind=='candidate' else None)
                    db.add(item); db.flush(); result=serialize(item); media_id=item.id
            except Exception:
                storage.client().delete_object(Bucket=settings().s3_bucket,Key=key); raise
    enqueue(media_id); return result

@app.get('/media')
def list_media(limit:int=Query(100,ge=1,le=500),user=Depends(current_user)):
    with Session() as db: return [serialize(m) for m in db.scalars(select(Media).order_by(Media.id.desc()).limit(limit)).all()]
@app.post('/media/{media_id}/retry')
def retry_media(media_id:int,user=Depends(roles('admin','analyst'))):
    with Session.begin() as db:
        media=db.get(Media,media_id)
        if not media: raise HTTPException(404,'Media not found')
        if media.status not in ('failed','waiting_reference'): raise HTTPException(409,'Only failed or waiting media may be retried')
        media.status='pending'; media.attempts=0; media.error=None
    enqueue(media_id); return {'status':'queued'}
@app.post('/media/{media_id}/reindex',status_code=202)
def reindex_media(media_id:int,user=Depends(roles('admin','analyst'))):
    with Session.begin() as db:
        media=db.get(Media,media_id)
        if not media: raise HTTPException(404,'Media not found')
        if media.kind not in ('reference','promotional'): raise HTTPException(409,'Only references can be reindexed')
        if media.status not in ('ready','failed'): raise HTTPException(409,'Media is already queued or processing')
        media.status='pending';media.stage='queued';media.attempts=0;media.error=None
    enqueue(media_id); return {'status':'queued','media_id':media_id}

@app.get('/media/{media_id}/index-summary')
def index_summary(media_id:int,user=Depends(roles('admin','analyst'))):
    with Session() as db: media=db.get(Media,media_id)
    if not media: raise HTTPException(404,'Media not found')
    if not media.feature_key: raise HTTPException(409,'Media has no index yet')
    features=storage.get_json(media.feature_key)
    return {'media_id':media_id,'feature_version':features['version'],'audio_version':features.get('audio_version'),
            'frames':len(features['frames']),'audio_quality':features.get('audio_quality',{'status':'legacy','landmarks':len(features['audio'])})}

@app.get('/media/{media_id}/content')
def media_content(media_id:int,user=Depends(roles('admin','analyst'))):
    with Session() as db: media=db.get(Media,media_id)
    if not media: raise HTTPException(404,'Media not found')
    body=storage.client().get_object(Bucket=settings().s3_bucket,Key=media.object_key)['Body']
    def chunks():
        try: yield from body.iter_chunks(chunk_size=1024*1024)
        finally: body.close()
    return StreamingResponse(chunks(),media_type='application/octet-stream',headers={'Content-Disposition':f'attachment; filename="evidence-{media_id}.bin"'})

@app.get('/detections')
def detections(q:str='',verdict:str='',limit:int=Query(100,ge=1,le=500),offset:int=Query(0,ge=0),user=Depends(current_user)):
    with Session() as db:
        stmt=select(Detection,Media,Movie).join(Media,Media.id==Detection.media_id).outerjoin(Movie,Movie.id==Detection.movie_id)
        if q: stmt=stmt.where((Movie.title.ilike('%'+q+'%')) | (Media.post_url.ilike('%'+q+'%')))
        if verdict: stmt=stmt.where(Detection.verdict==verdict)
        return [{**serialize(d),'movie_title':m.title if m else None,'platform':media.platform,'post_url':media.post_url} for d,media,m in db.execute(stmt.order_by(Detection.id.desc()).offset(offset).limit(limit))]
@app.get('/alerts')
def alerts(user=Depends(current_user)):
    with Session() as db: return [serialize(a) for a in db.scalars(select(Alert).order_by(Alert.id.desc()).limit(200)).all()]
@app.post('/alerts/{alert_id}/acknowledge')
def acknowledge(alert_id:int,user=Depends(roles('admin','analyst'))):
    with Session.begin() as db:
        alert=db.get(Alert,alert_id)
        if not alert: raise HTTPException(404,'Alert not found')
        alert.acknowledged=True; return {'status':'acknowledged'}
@app.get('/sources')
def sources(user=Depends(current_user)):
    with Session() as db: return [serialize(p) for p in db.scalars(select(SourcePost).order_by(SourcePost.id.desc()).limit(200)).all()]
@app.get('/agents')
def agents(user=Depends(current_user)):
    with Session() as db:
        stored={r.name:serialize(r) for r in db.scalars(select(AgentState)).all()}
        for name in ('discovery','video','audio','decision','alert','scheduler'):
            if name not in stored: stored[name]={'name':name,'status':'not_observed','detail':{},'updated_at':None}
        for row in stored.values():
            timestamp=row['updated_at']
            if timestamp:
                from datetime import datetime
                row['stale']=(now()-datetime.fromisoformat(timestamp)).total_seconds()>1800
            else: row['stale']=True
        try: queue_depth=redis_client().llen('celery')
        except Exception: queue_depth=None
        return {'agents':list(stored.values()),'queue_depth':queue_depth,'coverage':'Partial, authorized sources only; metadata discovery does not imply media monitoring',
                'laya':DecisionAgent.laya_status,'embedding_backend':settings().clip_model or 'disabled'}
@app.post('/discovery/run',status_code=202)
def trigger_discovery(user=Depends(roles('admin','analyst'))):
    discover.delay(); return {'status':'queued'}
@app.get('/settings')
def get_settings(user=Depends(roles('admin'))):
    s=settings()
    with Session() as db:
        preference=db.get(Preference,'matching')
        return {'matching':preference.value if preference else Preferences().model_dump(),
            'credentials':{'youtube_api_key':'configured' if s.youtube_api_key else 'missing',
                           'instagram':'unsupported','facebook':'unsupported'},
            'credentials_help':'Set secrets in environment settings or the protected .env file; never submit them in chat or store them in the browser.',
            'decision':{'engine':('deterministic+laya configured' if s.laya_enabled else 'deterministic'),'laya':{'enabled':s.laya_enabled,'interface':DecisionAgent.laya_status,'backend':'private service' if s.laya_service_url else 'local SDK'},'multimodal':('configured: advisory-only review; external service not validated' if s.multimodal_url and s.multimodal_model else 'not configured; ambiguous matches require human review')},
            'score_type':'uncalibrated evidence similarity; validate thresholds on representative authorized footage'}
@app.put('/settings')
def set_settings(body:Preferences,user=Depends(roles('admin'))):
    with Session.begin() as db:
        pref=db.get(Preference,'matching')
        if pref: pref.value=body.model_dump()
        else: db.add(Preference(key='matching',value=body.model_dump()))
    return body.model_dump()

from .browser_scan import router as browser_router
app.include_router(browser_router)
