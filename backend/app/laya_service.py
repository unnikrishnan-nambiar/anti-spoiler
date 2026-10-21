"""Private, authenticated CPU model service. No media download or external data egress."""
import hmac,os,threading
from contextlib import asynccontextmanager
from fastapi import FastAPI,HTTPException,Header,Depends
from pydantic import BaseModel,Field
from .agents.laya import load_agent,LayaEvidenceReviewer,MODEL_ID,REVISION
lock=threading.Lock()
@asynccontextmanager
async def lifespan(app):
    if len(os.environ.get('LAYA_SERVICE_TOKEN',''))<32:raise ValueError('LAYA_SERVICE_TOKEN requires 32 characters')
    app.state.agent=load_agent()
    # Warm the CPU inference path before accepting requests with short deadlines.
    LayaEvidenceReviewer(app.state.agent).review({'video':{'score':0,'matched_frames':0,'timestamp':0},'audio':{'score':0,'aligned_landmarks':0,'timestamp':0},'candidate_video_available':False})
    yield
app=FastAPI(title='Private Laya evidence reviewer',lifespan=lifespan)
class Visual(BaseModel):
    score:float=Field(ge=0,le=1)
    matched_frames:int=Field(default=0,ge=0)
    timestamp:float=Field(default=0,ge=0)
class Audio(BaseModel):
    score:float=Field(ge=0,le=1)
    aligned_landmarks:int=Field(default=0,ge=0)
    timestamp:float=Field(default=0,ge=0)
class Evidence(BaseModel):
    video:Visual
    audio:Audio
    promotional:bool=False
    audio_available:bool=True
    candidate_video_available:bool=True

def authorize(authorization:str=Header(default='')):
    expected='Bearer '+os.environ.get('LAYA_SERVICE_TOKEN','')
    if not hmac.compare_digest(authorization,expected):raise HTTPException(401,'Authentication required')
@app.get('/health/ready')
def ready():return {'status':'ready','model':MODEL_ID,'revision':REVISION}
@app.post('/review',dependencies=[Depends(authorize)])
def review(body:Evidence):
    with lock:return LayaEvidenceReviewer(app.state.agent).review(body.model_dump())
