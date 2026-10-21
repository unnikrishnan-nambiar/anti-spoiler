import importlib.util
from pathlib import Path
import numpy as np
import pytest
from app.features import extract, probe
from app.agents.video import VideoMatchingAgent
from app.agents.audio import AudioMatchingAgent
from app.agents.decision import DecisionAgent

@pytest.fixture(scope='module')
def features(tmp_path_factory):
    from app.samples import generate
    output=generate(tmp_path_factory.mktemp('samples'))
    values={}
    for name in ('reference','candidate','unrelated','promotional'):
        values[name]=extract(output/f'{name}.mp4',tmp_path_factory.mktemp(name))
    return values

def test_transformed_video_finds_correct_scene(features):
    result=VideoMatchingAgent().match(features['candidate'],features['reference'])
    assert abs(result['timestamp']-6)<=2 and result['score']>.7 and result['matched_frames']>=2

def test_audio_alignment(features):
    result=AudioMatchingAgent().match(features['candidate'],features['reference'])
    assert abs(result['timestamp']-6)<.3 and result['score']>.15

def test_unrelated_video_not_confirmed(features):
    v=VideoMatchingAgent().match(features['unrelated'],features['reference']);a=AudioMatchingAgent().match(features['unrelated'],features['reference'])
    assert DecisionAgent().decide({'video':v,'audio':a})['verdict']=='no_match'

def test_promo_matching(features):
    v=VideoMatchingAgent().match(features['candidate'],features['promotional']);a=AudioMatchingAgent().match(features['candidate'],features['promotional'])
    assert DecisionAgent().decide({'video':v,'audio':a})['verdict']=='confirmed'

def test_invalid_media_rejected(tmp_path):
    path=tmp_path/'bad.mp4';path.write_text('not a video')
    with pytest.raises(Exception):probe(path)

def test_audio_with_broadband_background_noise_aligns():
    from app.features import audio_fingerprints
    rng=np.random.default_rng(123);rate=11025;pieces=[]
    for _ in range(80):
        t=np.arange(rate//4)/rate
        frequencies=rng.choice(np.arange(220,4000,31),3,replace=False)
        pieces.append(sum(np.sin(2*np.pi*f*t) for f in frequencies)*np.hanning(len(t)))
    reference=np.concatenate(pieces).astype(np.float32)
    candidate=reference[6*rate:14*rate].copy()+rng.normal(0,.2,8*rate)
    result=AudioMatchingAgent().match({'audio':audio_fingerprints(candidate,rate)}, {'audio':audio_fingerprints(reference,rate)})
    assert result['score']>.2 and abs(result['timestamp']-6)<.3

def test_pcm_encoding_and_gain_do_not_change_audio_alignment():
    from app.features import audio_fingerprints
    rng=np.random.default_rng(91);rate=11025
    pieces=[]
    for index in range(64):
        t=np.arange(rate//4)/rate
        frequencies=rng.choice(np.arange(200,4500,41),8,replace=False)
        pieces.append(sum(np.sin(2*np.pi*f*t+rng.random()*6.28) for f in frequencies)*np.hanning(len(t)))
    signal=np.concatenate(pieces).astype(np.float32);signal/=np.max(np.abs(signal))
    pcm=(signal*32000).astype(np.int16)
    ref={'audio':audio_fingerprints(pcm,rate),'audio_version':3}
    for candidate in (signal[4*rate:12*rate],signal[4*rate:12*rate]*.08):
        match=AudioMatchingAgent().match({'audio':audio_fingerprints(candidate,rate),'audio_version':3},ref)
        assert abs(match['timestamp']-4)<.2 and match['score']>.4
    assert len(ref['audio'])>100

def test_silent_audio_has_no_fingerprints():
    from app.features import audio_fingerprints
    assert audio_fingerprints(np.zeros(11025,dtype=np.int16),11025)==[]
