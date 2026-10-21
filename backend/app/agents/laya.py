"""Documented Laya SDK integration: structured evidence only, never video retrieval."""
from functools import lru_cache
import math
import os
import httpx

MODEL_ID='convaiinnovations/laya'
REVISION='7b928d828b7b0e022f929d9bd2e44165aa270148'
MODEL_SHA256='891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c'

@lru_cache
def load_agent():
    import torch
    import laya
    torch.set_num_threads(2)
    model_path=os.environ.get('LAYA_MODEL_PATH') or MODEL_ID
    return laya.load(model_path,revision=REVISION,device='cpu',expected_sha256={'model.safetensors':MODEL_SHA256})

class LayaEvidenceReviewer:
    def __init__(self,agent=None): self.agent=agent
    def review(self,evidence,timeout=45):
        state={
            'candidate_video_compared':evidence.get('candidate_video_available',True),
            'visual':{k:evidence['video'].get(k) for k in ('score','matched_frames','timestamp')},
            'audio':{k:evidence['audio'].get(k) for k in ('score','aligned_landmarks','timestamp')},
            'promotional':bool(evidence.get('promotional',False)),
        }
        questions={'verification':{'type':'choice',
            'instructions':'Evaluate only supplied measured scene evidence. Metadata, captions and posters alone never verify a video match. Missing candidate footage requires review. Conflicting timestamps or absent visual evidence do not verify footage.',
            'criteria':{'confirmed':'Candidate video was compared, with strong multiple-frame geometric matches and consistent reference timing.',
                        'review':'Evidence is ambiguous or candidate footage was unavailable; human review is needed.',
                        'no_match':'Compared footage has no supporting geometric or temporally aligned audio evidence.'}}}
        if evidence.get('audio_available') is False:
            state['audio']=None
            questions={'verification':{'type':'choice',
                'instructions':'Review measured visual evidence only. Audio was not captured. Scores are similarities, not probabilities.',
                'criteria':{'confirmed':'Multiple geometrically verified frames support the same reference offset.',
                            'review':'Visual support is ambiguous or inconsistent.',
                            'no_match':'Sampled frames have no supporting geometric matches.'}}}
        if self.agent is None:
            from ..config import settings
            config=settings()
            if config.laya_service_url:
                response=httpx.post(config.laya_service_url.rstrip('/')+'/review',json=evidence,
                    headers={'Authorization':'Bearer '+config.laya_service_token},timeout=timeout,trust_env=False)
                response.raise_for_status()
                output=response.json()
                if output.get('model')!=MODEL_ID or output.get('revision')!=REVISION:raise ValueError('Unexpected Laya service model')
                if output.get('choice') not in ('confirmed','review','no_match'):raise ValueError('Unexpected Laya service choice')
                confidence=output.get('model_confidence')
                if confidence is not None and (not isinstance(confidence,(int,float)) or not math.isfinite(confidence) or not 0<=confidence<=1):raise ValueError('Invalid Laya confidence')
                return output
        result=(self.agent or load_agent()).predict(state,questions)
        answer=result['answers']['verification']
        choice=answer['choice']
        if choice not in ('confirmed','review','no_match'):raise ValueError('Unexpected Laya choice')
        output={'model':MODEL_ID,'revision':REVISION,'choice':choice,'scope':'structured_evidence_only','domain_calibration':'not calibrated for movie-scene verification'}
        confidence=answer.get('answer_confidence',answer.get('confidence'))
        if confidence is not None:
            if not isinstance(confidence,(int,float)) or not math.isfinite(confidence) or not 0<=confidence<=1:raise ValueError('Invalid Laya confidence')
            output['model_confidence']=confidence
            output['confidence_semantics']='SDK answer confidence; not calibrated for movie-scene verification'
        usage=result.get('usage',{})
        output['usage']={k:usage[k] for k in ('input_tokens','output_tokens','state_tokens','state_tokens_dropped','truncated') if k in usage}
        return output
