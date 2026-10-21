from collections import defaultdict, Counter

class AudioMatchingAgent:
    def match(self,candidate,reference):
        if candidate.get('audio_version',1)!=reference.get('audio_version',1):
            return {'score':0.,'timestamp':0.,'aligned_landmarks':0,'status':'incompatible_fingerprint_versions'}
        lookup=defaultdict(list)
        for fingerprint,timestamp in reference['audio']: lookup[fingerprint].append(timestamp)
        offsets=Counter(); matching=set()
        for fingerprint,timestamp in candidate['audio']:
            # Repetitive tones/silence must not dominate alignment votes.
            if len(lookup[fingerprint])>30: continue
            for ref_time in lookup[fingerprint]:
                offsets[round((ref_time-timestamp)*10)]+=1
                matching.add(fingerprint)
        if not offsets: return {'score':0.,'timestamp':0.,'aligned_landmarks':0}
        best,count=offsets.most_common(1)[0]
        aligned=sum(n for offset,n in offsets.items() if abs(offset-best)<=1)
        total=max(1,len(candidate['audio']))
        score=min(1.,aligned/total)*min(1.,len(matching)/30)
        return {'score':round(score,4),'timestamp':max(0,best/10),'aligned_landmarks':aligned,'distinct_landmarks':len(matching)}
