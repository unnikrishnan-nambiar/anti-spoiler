"""Private inference boundary and documented SDK confidence semantics."""
from fastapi.testclient import TestClient
from app import laya_service
from app.agents.laya import LayaEvidenceReviewer

def test_private_model_requires_auth_and_valid_evidence(monkeypatch):
    monkeypatch.setenv('LAYA_SERVICE_TOKEN','x'*32)
    class Agent:
        def predict(self,state,questions):
            return {'answers':{'verification':{'choice':'confirmed','confidence':.05,'answer_confidence':.48}}}
    monkeypatch.setattr(laya_service,'load_agent',lambda:Agent())
    body={'video':{'score':.9,'matched_frames':4,'timestamp':30},'audio':{'score':.7,'timestamp':30}}
    with TestClient(laya_service.app) as client:
        assert client.post('/review',json=body).status_code==401
        headers={'Authorization':'Bearer '+'x'*32}
        result=client.post('/review',json=body,headers=headers)
        assert result.status_code==200
        assert result.json()['model_confidence']==.48
        assert result.json()['domain_calibration'].startswith('not calibrated')
        body['video']['score']=1.5
        assert client.post('/review',json=body,headers=headers).status_code==422
