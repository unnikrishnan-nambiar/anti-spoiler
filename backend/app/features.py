"""Bounded media decoding; no network URLs are accepted by FFmpeg."""
import subprocess, json, base64
from pathlib import Path
import cv2
import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter
from scipy.io import wavfile
from .config import settings


def run(args, timeout=300):
    return subprocess.run(args, check=True, capture_output=True, timeout=timeout)

def probe(path):
    result = run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-format_whitelist','mov,matroska,avi,mpegts,mpeg','-show_format','-show_streams','-of','json',str(path)])
    data = json.loads(result.stdout)
    duration = float(data.get('format', {}).get('duration', 0))
    if not 0 < duration <= settings().max_duration_seconds: raise ValueError('Invalid duration or media exceeds duration limit')
    if not any(s['codec_type']=='video' for s in data['streams']): raise ValueError('Video stream required')
    return data

def phash(frame):
    small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (32,32)).astype(np.float32)
    values = cv2.dct(small)[:8,:8].flatten()[1:]
    return ''.join('1' if x > np.median(values) else '0' for x in values)

def frame_feature(frame, timestamp):
    height,width = frame.shape[:2]
    frame = cv2.resize(frame, (int(width*min(1,640/width)),int(height*min(1,640/width))))
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    points, descriptors = cv2.ORB_create(nfeatures=600).detectAndCompute(gray,None)
    hashes = [phash(frame)]
    h,w = frame.shape[:2]
    for ratio in (.8,.6):
        dx,dy=int(w*(1-ratio)/2),int(h*(1-ratio)/2)
        hashes.append(phash(frame[dy:h-dy,dx:w-dx]))
    thumbnail=cv2.imencode('.jpg',cv2.resize(frame,(256,144)),[cv2.IMWRITE_JPEG_QUALITY,65])[1]
    return {'thumbnail':base64.b64encode(thumbnail).decode(), 't':timestamp, 'hashes':hashes,'points':[list(p.pt) for p in points],
            'descriptors':descriptors.tolist() if descriptors is not None else [], 'size':[w,h]}

def audio_fingerprints(samples, sample_rate):
    samples=np.asarray(samples)
    # Normalize PCM BEFORE the logarithmic spectrum. The old int16 path made
    # log compression inflate the relative MAD threshold and discard music peaks.
    if np.issubdtype(samples.dtype,np.unsignedinteger):
        midpoint=(np.iinfo(samples.dtype).max+1)/2
        samples=(samples.astype(np.float32)-midpoint)/midpoint
    elif np.issubdtype(samples.dtype,np.signedinteger):
        scale=max(abs(np.iinfo(samples.dtype).min),np.iinfo(samples.dtype).max)
        samples=samples.astype(np.float32)/scale
    else:
        samples=samples.astype(np.float32)
    if samples.ndim>1: samples=samples.mean(axis=1)
    if len(samples)<2048: return []
    if not np.isfinite(samples).all(): raise ValueError('Non-finite audio samples')
    peak=float(np.max(np.abs(samples)))
    if peak<1e-8: return []
    samples=samples/peak
    samples = signal.lfilter([1,-.97],[1],samples)
    _,times,spectrum=signal.stft(samples, sample_rate,nperseg=1024,noverlap=512)
    log=np.log1p(np.abs(spectrum))
    # Adaptive noise floor preserves tonal landmarks when broadband audience noise rises.
    median=np.median(log,axis=0)
    threshold=median+8*np.median(np.abs(log-median),axis=0)
    peaks=(log==maximum_filter(log,size=(15,9))) & (log>threshold)
    freq, steps=np.where(peaks)
    points=sorted(zip(steps.tolist(),freq.tolist()))
    fingerprints=[]
    for i,(t,f) in enumerate(points):
        paired=0
        for t2,f2 in points[i+1:i+100]:
            delta=t2-t
            if delta>50: break
            if 2<=delta<=50:
                fingerprints.append([f'{f//2}:{f2//2}:{delta//2}',round(float(times[t]),3)])
                paired+=1
                if paired>=5: break
    return fingerprints

def extract(path, directory):
    data=probe(path)
    frame_dir=Path(directory)/'frames'; frame_dir.mkdir(exist_ok=True)
    # Decode with fixed-rate sampling rather than seeking inaccurate timestamps.
    run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file,pipe','-format_whitelist','mov,matroska,avi,mpegts,mpeg','-i',str(path),'-vf',
         f'fps=1/{settings().frame_interval},scale=640:-2','-threads','2',str(frame_dir/'%06d.jpg')],timeout=900)
    frames=[]
    encoder=None
    if settings().clip_model:
        from .embeddings import get_encoder
        encoder=get_encoder()
    for i,file in enumerate(sorted(frame_dir.glob('*.jpg'))):
        frame=cv2.imread(str(file)); feat=frame_feature(frame,i*settings().frame_interval)
        if encoder is not None: feat['embedding']=encoder.encode_image(frame)
        frames.append(feat)
    audio=[]
    if any(s['codec_type']=='audio' for s in data['streams']):
        wav=Path(directory)/'audio.wav'
        run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file,pipe','-format_whitelist','mov,matroska,avi,mpegts,mpeg','-i',str(path),'-vn','-ac','1','-ar','11025','-threads','2',str(wav)],timeout=600)
        rate,samples=wavfile.read(wav); audio=audio_fingerprints(samples,rate)
    if not frames: raise ValueError('No decodable frames')
    return {'version':3,'audio_version':3,'duration':float(data['format']['duration']), 'frames':frames,'audio':audio,
            'embedding_model':settings().clip_model or None,
            'audio_quality':{'status':('absent' if not any(s['codec_type']=='audio' for s in data['streams']) else ('indexed' if len(audio)>=30 else 'sparse')),
                             'landmarks':len(audio),'landmarks_per_second':round(len(audio)/float(data['format']['duration']),3)}}
