from sqlalchemy import select
from ..db import Detection, Alert, now

class AlertAgent:
    def store(self,db,media,movie_id,evidence,decision):
        existing=db.scalar(select(Detection).where(Detection.media_id==media.id))
        if existing: return existing
        detection=Detection(media_id=media.id,movie_id=movie_id,scene_timestamp=evidence['video']['timestamp'],
                            confidence=decision['confidence'],severity=decision['severity'],verdict=decision['verdict'],
                            evidence={**evidence,'decision':decision}, detected_at=now())
        db.add(detection); db.flush()
        from ..db import Preference
        preference=db.get(Preference,'matching')
        alerts_enabled=not preference or preference.value.get('alerts_enabled',True)
        if decision['verdict']=='confirmed' and alerts_enabled:
            db.add(Alert(detection_id=detection.id,payload={'platform':media.platform,'post_url':media.post_url,
                   'movie_id':movie_id,'scene_timestamp':detection.scene_timestamp,'detected_at':detection.detected_at.isoformat(),
                   'confidence':decision['confidence'],'score_type':'uncalibrated_evidence_similarity'}))
        return detection
