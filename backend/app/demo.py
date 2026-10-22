"""Single-process extension demo: SQLite, local files, FFmpeg and private Laya.
Not the distributed dashboard/monitoring API. Run with scripts/run_extension.py.
"""
import hashlib
import secrets
import shutil
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from . import storage
from .browser_scan import router
from .config import settings
from .db import Base, Media, Movie, Session, User, engine
from .features import extract, probe
from .security import current_user, hash_password, issue_token, roles, verify_password

_index_slot=threading.BoundedSemaphore(1)
_login_lock=threading.Lock()
_login_attempts={}

def row(item):
    return {c.name:(v.isoformat() if hasattr(v,'isoformat') else v)
            for c in item.__table__.columns for v in [getattr(item,c.name)]}

def index_media(media_id):
    with _index_slot:
        try:
            with Session.begin() as db:
                media=db.get(Media,media_id)
                media.status='processing'; media.stage='extracting'
                key=media.object_key
            with tempfile.TemporaryDirectory() as directory:
                video=Path(directory)/'input.bin'; storage.download(key,video)
                features=extract(video,directory)
                if len(features['frames'])>450: raise ValueError('Reference exceeds 450 frames')
                feature_key=f'features/{media_id}/v3.json'; storage.put_json(feature_key,features)
            with Session.begin() as db:
                media=db.get(Media,media_id)
                media.status='ready'; media.stage='indexed'; media.feature_key=feature_key; media.error=None
        except Exception as exc:
            with Session.begin() as db:
                media=db.get(Media,media_id)
                media.status='failed'; media.stage='error'; media.error=type(exc).__name__

@asynccontextmanager
async def lifespan(app):
    config=settings()
    if not config.local_storage_path or not config.database_url.startswith('sqlite:'):
        raise RuntimeError('Demo requires an explicit local storage path and SQLite database')
    Base.metadata.create_all(engine)
    with Session.begin() as db:
        if not db.scalar(select(User).where(User.username==config.admin_username)):
            db.add(User(username=config.admin_username,password_hash=hash_password(config.admin_password),role='admin'))
        # Interrupted indexing is explicit and can be retried by uploading again.
        for media in db.scalars(select(Media).where(Media.status.in_(['pending','processing']))):
            media.status='failed'; media.stage='error'; media.error='InterruptedIndexing'
    yield

app=FastAPI(title='SceneGuard extension demo',lifespan=lifespan)
app.include_router(router)

@app.get('/health/live')
def live(): return {'status':'ok','mode':'local_extension_demo'}

@app.get('/health/ready')
def ready():
    try:
        with Session() as db: db.execute(text('SELECT 1'))
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'): raise RuntimeError()
        path=Path(settings().local_storage_path)
        with tempfile.TemporaryFile(dir=path) as file: file.write(b'readiness')
        from .agents.laya import MODEL_ID, REVISION
        response=httpx.get(settings().laya_service_url+'/health/ready',timeout=5,trust_env=False)
        response.raise_for_status(); model=response.json()
        if model.get('model')!=MODEL_ID or model.get('revision')!=REVISION: raise RuntimeError()
        return {'status':'ready','mode':'local_extension_demo','laya':model}
    except Exception: raise HTTPException(503,'SQLite, local storage, FFmpeg or Laya unavailable')

class Login(BaseModel):
    username:str=Field(max_length=100)
    password:str=Field(max_length=1000)

@app.post('/auth/login')
def login(body:Login,request:Request):
    # Bounded, per-process rate limit. Hosting ingress must also limit requests.
    key=request.client.host
    with _login_lock:
        now=time.monotonic()
        for host,(_,expiry) in list(_login_attempts.items()):
            if expiry<=now: del _login_attempts[host]
        count,expiry=_login_attempts.get(key,(0,now+300))
        if count>=20 or (key not in _login_attempts and len(_login_attempts)>=1024):
            raise HTTPException(429,'Too many login attempts; retry in 5 minutes')
        _login_attempts[key]=(count+1,expiry)
    with Session() as db: user=db.scalar(select(User).where(User.username==body.username))
    if not user:
        hashlib.pbkdf2_hmac('sha256',body.password.encode(),b'unknown-user',600000)
        raise HTTPException(401,'Invalid credentials')
    if not verify_password(body.password,user.password_hash): raise HTTPException(401,'Invalid credentials')
    return {'access_token':issue_token(user),'token_type':'bearer','role':user.role,'expires_in':3600}

@app.get('/auth/me')
def me(user=Depends(current_user)): return {'username':user.username,'role':user.role}

class MovieInput(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    spoiler_start:float=Field(default=0,ge=0)

@app.post('/movies',status_code=201)
def add_movie(body:MovieInput,user=Depends(roles('admin','analyst'))):
    with Session.begin() as db:
        movie=Movie(**body.model_dump()); db.add(movie); db.flush(); return row(movie)

@app.get('/movies')
def movies(user=Depends(current_user)):
    with Session() as db:
        return [{**row(movie),'media':[row(media) for media in db.scalars(select(Media).where(Media.movie_id==movie.id))]}
                for movie in db.scalars(select(Movie).order_by(Movie.id.desc()))]

@app.get('/media')
def media(limit:int=Query(100,ge=1,le=500),user=Depends(current_user)):
    with Session() as db: return [row(m) for m in db.scalars(select(Media).order_by(Media.id.desc()).limit(limit))]

@app.get('/media/{media_id}/index-summary')
def summary(media_id:int,user=Depends(roles('admin','analyst'))):
    with Session() as db: media=db.get(Media,media_id)
    if not media: raise HTTPException(404,'Media not found')
    if media.status!='ready': raise HTTPException(409,'Reference is not indexed')
    data=storage.get_json(media.feature_key)
    return {'media_id':media.id,'feature_version':data['version'],'audio_version':data['audio_version'],
            'frames':len(data['frames']),'audio_quality':data['audio_quality']}

@app.post('/media',status_code=202)
def upload(tasks:BackgroundTasks,file:UploadFile=File(...),kind:str=Form(...),movie_id:int=Form(...),
           authorized:bool=Form(False),user=Depends(roles('admin','analyst'))):
    if not authorized: raise HTTPException(422,'Confirm processing authorization')
    if kind not in ('reference','promotional'): raise HTTPException(422,'Demo accepts references and approved promotional footage only')
    with Session() as db:
        if not db.get(Movie,movie_id): raise HTTPException(404,'Movie not found')
    digest=hashlib.sha256(); size=0
    with tempfile.NamedTemporaryFile() as temp:
        while chunk:=file.file.read(1024*1024):
            size+=len(chunk)
            if size>settings().max_media_bytes: raise HTTPException(413,'Maximum upload size exceeded')
            digest.update(chunk); temp.write(chunk)
        temp.flush()
        try:
            info=probe(temp.name)
            if float(info['format']['duration'])>900: raise ValueError()
        except Exception: raise HTTPException(422,'Valid video excerpt up to 15 minutes required')
        # Unique object keys keep concurrent uploads independent.
        key=f'media/{secrets.token_hex(16)}.bin'; storage.put_file(temp.name,key)
    with Session.begin() as db:
        item=Media(movie_id=movie_id,kind=kind,object_key=key,sha256=digest.hexdigest(),dedup_key=key)
        db.add(item); db.flush(); result=row(item)
    tasks.add_task(index_media,result['id'])
    return result
