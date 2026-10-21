import httpx, pytest
from app.agents.discovery import DiscoveryAgent,MockAdapter,InstagramAdapter,FacebookAdapter,YouTubeAdapter
from app.agents.decision import DecisionAgent
from app.agents.audio import AudioMatchingAgent
from app.agents.video import VideoMatchingAgent
from app.agents.multimodal import MultimodalReviewer
from app.security import hash_password,verify_password

@pytest.mark.parametrize('adapter',[InstagramAdapter(),FacebookAdapter(),YouTubeAdapter('','')])
def test_unsupported_is_explicit(adapter):
    result=DiscoveryAgent(adapter).discover({})
    assert result.status=='unsupported' and result.posts==[]

def test_mock_checkpoint():
    agent=DiscoveryAgent(MockAdapter([{'external_id':str(i)} for i in range(70)]))
    first=agent.discover({});second=agent.discover(first.checkpoint)
    assert first.status=='mock' and len(first.posts)==50 and len(second.posts)==20
    assert agent.discover(second.checkpoint).posts==[]

def test_youtube_official_metadata_and_pagination():
    def handler(request):
        assert request.url.host=='www.googleapis.com'
        assert request.url.params['type']=='video' and request.url.params['channelId']=='authorized-channel'
        return httpx.Response(200,json={'items':[{'id':{'videoId':'abc'},'snippet':{'title':'Example','publishedAt':'2026-10-20T00:00:00Z'}}],'nextPageToken':'next'})
    adapter=YouTubeAdapter('test-key','movie','authorized-channel',httpx.Client(transport=httpx.MockTransport(handler)))
    result=adapter.discover({'since':'2026-10-19T00:00:00Z'})
    assert result.status=='metadata_only' and result.checkpoint['page']=='next'
    assert result.posts[0]['url']=='https://www.youtube.com/watch?v=abc'

def test_youtube_never_exposes_key_on_error():
    adapter=YouTubeAdapter('SENSITIVE','movie',client=httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(403))))
    with pytest.raises(RuntimeError) as exc:adapter.discover({})
    assert 'SENSITIVE' not in str(exc.value)

def evidence(v=.9,a=0,vt=6,at=6,frames=3,promo=False):
    return {'video':{'score':v,'timestamp':vt,'matched_frames':frames},'audio':{'score':a,'timestamp':at},'promotional':promo}

def test_decision_confirmed_and_severity():
    result=DecisionAgent().decide(evidence(),spoiler_start=10)
    assert result['verdict']=='confirmed' and result['severity']=='low'
    assert result['score_type']=='uncalibrated_evidence_similarity'

def test_promo_exclusion():assert DecisionAgent().decide(evidence(promo=True))['verdict']=='excluded_promotional'
def test_one_frame_cannot_confirm():assert DecisionAgent().decide(evidence(frames=1))['verdict']=='review'
def test_ambiguous_is_review():assert DecisionAgent().decide(evidence(v=.55))['verdict']=='review'
def test_audio_alignment_required():
    assert DecisionAgent().decide(evidence(v=.65,a=.7,at=60))['verdict']=='review'
    assert DecisionAgent().decide(evidence(v=.65,a=.7))['verdict']=='confirmed'
def test_audio_alone_cannot_confirm():assert DecisionAgent().decide(evidence(v=0,a=1,frames=0))['verdict']!='confirmed'
def test_empty_audio():assert AudioMatchingAgent().match({'audio':[]},{'audio':[]})['score']==0

def test_blank_frame_does_not_match():
    f={'hashes':['0'*63],'descriptors':[],'points':[],'size':[100,100],'t':0}
    assert VideoMatchingAgent().match({'frames':[f,f]},{'frames':[f]})['score']==0

def test_password_hash():
    encoded=hash_password('this is a password')
    assert verify_password('this is a password',encoded)
    assert not verify_password('wrong password',encoded)
    assert encoded!=hash_password('this is a password')

def test_multimodal_contract_and_no_automatic_confirmation():
    def handle(request):
        assert request.headers['authorization']=='Bearer fake'
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"verdict":"uncertain","reason":"insufficient evidence"}'}}]})
    model=MultimodalReviewer('https://vision.example.invalid/v1/chat/completions','fake','test',httpx.Client(transport=httpx.MockTransport(handle)))
    assert model.review('a','b',{})['verdict']=='uncertain'

def test_multimodal_rejects_unknown_interface():
    model=MultimodalReviewer('https://vision.example.invalid/v1/chat/completions','','test',httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'choices':[{'message':{'content':'{"verdict":"definitely","confidence":1}'}}]}))))
    with pytest.raises(ValueError):model.review('a','b',{})

def test_zero_geometric_inliers_do_not_crash(monkeypatch):
    import cv2
    import numpy as np
    from app.features import frame_feature
    frame=np.random.default_rng(42).integers(0,256,(360,640,3),dtype=np.uint8)
    feature=frame_feature(frame,0)
    def degenerate(src,dst,*args):
        return np.eye(3),np.zeros((len(src),1),dtype=np.uint8)
    monkeypatch.setattr(cv2,'findHomography',degenerate)
    score,detail=VideoMatchingAgent().frame_score(feature,feature)
    assert score==0 and detail['inliers']==0

def test_incompatible_audio_indexes_are_explicit():
    result=AudioMatchingAgent().match({'audio':[],'audio_version':2},{'audio':[],'audio_version':1})
    assert result['score']==0 and result['status']=='incompatible_fingerprint_versions'

def test_laya_documented_evidence_interface():
    from app.agents.laya import LayaEvidenceReviewer,REVISION
    class Agent:
        def predict(self,state,questions):
            assert 'visual' in state and 'caption' not in state
            assert questions['verification']['type']=='choice'
            return {'answers':{'verification':{'choice':'review','confidence':.61}}}
    result=LayaEvidenceReviewer(Agent()).review(evidence())
    assert result['choice']=='review' and result['revision']==REVISION

def test_laya_cannot_promote_weak_match(monkeypatch):
    from app.config import settings
    from app.agents.laya import LayaEvidenceReviewer
    monkeypatch.setattr(settings(),'laya_enabled',True)
    monkeypatch.setattr(LayaEvidenceReviewer,'review',lambda *_:{'choice':'confirmed'})
    assert DecisionAgent().decide(evidence(v=.3,a=0))['verdict']=='no_match'

def test_laya_can_request_review(monkeypatch):
    from app.config import settings
    from app.agents.laya import LayaEvidenceReviewer
    monkeypatch.setattr(settings(),'laya_enabled',True)
    monkeypatch.setattr(LayaEvidenceReviewer,'review',lambda *_:{'choice':'review'})
    result=DecisionAgent().decide(evidence())
    assert result['verdict']=='review' and result['engine']=='deterministic+laya'

def test_laya_failure_is_explicit_fallback(monkeypatch):
    from app.config import settings
    from app.agents.laya import LayaEvidenceReviewer
    monkeypatch.setattr(settings(),'laya_enabled',True)
    def fail(*_):raise RuntimeError('weights unavailable')
    monkeypatch.setattr(LayaEvidenceReviewer,'review',fail)
    result=DecisionAgent().decide(evidence())
    assert result['engine']=='deterministic' and result['laya']['status']=='unavailable'

def test_missing_footage_never_becomes_match_or_negative_claim(monkeypatch):
    from app.config import settings
    from app.agents.laya import LayaEvidenceReviewer
    monkeypatch.setattr(settings(),'laya_enabled',True)
    for output in ('confirmed','no_match'):
        monkeypatch.setattr(LayaEvidenceReviewer,'review',lambda *_,value=output:{'choice':value})
        data=evidence(v=0,a=0,frames=0);data['candidate_video_available']=False
        assert DecisionAgent().decide(data)['verdict']=='insufficient_evidence'
