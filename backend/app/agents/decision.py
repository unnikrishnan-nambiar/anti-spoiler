"""Evidence scores are NOT calibrated probabilities. Optional Laya evaluates structured evidence only."""
class DecisionAgent:
    laya_status='verified SDK: convaiinnovations/laya, laya 0.4.12; verified pinned CPU model; structured-evidence reviewer'

    def decide(self,evidence,threshold=.75,review_threshold=.45,audio_threshold=.2,spoiler_start=0):
        decision=self._deterministic(evidence,threshold=threshold,review_threshold=review_threshold,audio_threshold=audio_threshold,spoiler_start=spoiler_start)
        from ..config import settings
        if settings().laya_enabled:
            try:
                from .laya import LayaEvidenceReviewer
                review=LayaEvidenceReviewer().review(evidence)
                decision['laya']=review
                decision['engine']='deterministic+laya'
                # The model may request review; it cannot manufacture evidence or promote a weak match.
                if decision['verdict']=='confirmed' and review['choice']!='confirmed':
                    decision['verdict']='review'; decision['severity']='unknown'
            except Exception as exc:
                decision['laya']={'status':'unavailable','error':type(exc).__name__}
        if evidence.get('candidate_video_available') is False:
            decision.update(verdict='insufficient_evidence',severity='unknown',reason='Candidate footage is unavailable; no content-match conclusion is possible')
        return decision

    def _deterministic(self,evidence,threshold=.75,review_threshold=.45,audio_threshold=.2,spoiler_start=0):
        video=evidence['video']; audio=evidence['audio']
        v,a=video['score'],audio['score']
        aligned=abs(video['timestamp']-audio['timestamp'])<=4
        # Audio strengthens visual evidence only with consistent temporal alignment.
        score=min(1.,.7*v+.3*min(1,a/max(audio_threshold,.01))) if aligned and a>=audio_threshold else v
        confirmed=(v>=threshold and video['matched_frames']>=2) or (v>=review_threshold and a>=audio_threshold and aligned and score>=threshold)
        if evidence.get('promotional'):
            return {'verdict':'excluded_promotional','confidence':score,'severity':'none','engine':'deterministic'}
        verdict='confirmed' if confirmed else ('review' if max(v,a)>=review_threshold else 'no_match')
        timestamp=video['timestamp'] if v else audio['timestamp']
        return {'verdict':verdict,'confidence':round(score,4),
                'severity':('high' if timestamp>=spoiler_start else 'low') if verdict=='confirmed' else 'unknown',
                'engine':'deterministic','score_type':'uncalibrated_evidence_similarity'}
