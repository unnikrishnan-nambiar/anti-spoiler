from collections import defaultdict
import cv2
import numpy as np

class VideoMatchingAgent:
    def frame_score(self,candidate,reference):
        hash_score=max(1-sum(a!=b for a,b in zip(x,y))/63 for x in candidate['hashes'] for y in reference['hashes'])
        # Hashes alone are unreliable for blank/simple frames. Require geometric support.
        a=np.asarray(candidate['descriptors'],dtype=np.uint8); b=np.asarray(reference['descriptors'],dtype=np.uint8)
        geometry=0.; inliers=0
        if len(a)>=12 and len(b)>=12:
            matches=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(a,b,k=2)
            good=[m[0] for m in matches if len(m)==2 and m[0].distance<.72*m[1].distance]
            if len(good)>=8:
                src=np.float32([candidate['points'][m.queryIdx] for m in good])
                dst=np.float32([reference['points'][m.trainIdx] for m in good])
                try:
                    _,mask=cv2.findHomography(src,dst,cv2.RANSAC,4)
                except cv2.error:
                    mask=None
                if mask is not None and int(mask.sum())>=8:
                    inliers=int(mask.sum())
                    # Reject clustered matches (logos/subtitles) that cover little of the frame.
                    covered=cv2.contourArea(cv2.convexHull(src[mask.ravel().astype(bool)]))
                    area=candidate['size'][0]*candidate['size'][1]
                    if covered/area >= .08 and inliers>=8:
                        geometry=min(1.,inliers/25)*(inliers/len(good))
        score=.85*geometry+.15*hash_score if geometry else 0.
        return score,{'phash_similarity':round(hash_score,4),'geometric_similarity':round(geometry,4),'inliers':inliers}

    def match(self,candidate,reference):
        votes=defaultdict(list)
        for frame in candidate['frames']:
            best=(0,None,None)
            # Optional CLIP ranks candidate frames before geometric verification; it never confirms alone.
            refs=reference['frames']
            if frame.get('embedding') and reference.get('embedding_model')==candidate.get('embedding_model'):
                refs=sorted(refs,key=lambda r:np.dot(frame['embedding'],r.get('embedding',np.zeros(512))),reverse=True)[:30]
            for ref in refs:
                score,detail=self.frame_score(frame,ref)
                if score>best[0]: best=(score,ref,detail)
            if best[1] and best[0]>=.35:
                offset=best[1]['t']-frame['t']; bucket=round(offset/2)
                votes[bucket].append({'candidate_t':frame['t'],'reference_t':best[1]['t'],'score':best[0],**best[2]})
        if not votes: return {'score':0.,'timestamp':0.,'matched_frames':0,'frames':[]}
        matches=max(votes.values(),key=lambda v:sum(x['score'] for x in v))
        # At least two consistent frames are needed for strong evidence.
        score=float(np.mean([x['score'] for x in matches]))*min(1,len(matches)/2)
        offset=float(np.median([x['reference_t']-x['candidate_t'] for x in matches]))
        return {'score':round(score,4),'timestamp':max(0,offset),'matched_frames':len(matches),'frames':matches[:12]}
