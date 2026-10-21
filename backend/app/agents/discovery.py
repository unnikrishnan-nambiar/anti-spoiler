"""Official metadata only. No scraping or public-video downloader."""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import httpx

@dataclass
class DiscoveryResult:
    status: str
    posts: list = field(default_factory=list)
    checkpoint: dict = field(default_factory=dict)
    detail: str = ''

class UnsupportedAdapter:
    def __init__(self,platform): self.platform=platform
    def discover(self,checkpoint):
        return DiscoveryResult('unsupported',checkpoint=checkpoint,
            detail=f'{self.platform}: approved API connector and permissions not configured; no coverage')

class InstagramAdapter(UnsupportedAdapter):
    def __init__(self): super().__init__('instagram')
class FacebookAdapter(UnsupportedAdapter):
    def __init__(self): super().__init__('facebook')

class MockAdapter:
    def __init__(self,posts=None): self.posts=posts or []
    def discover(self,checkpoint):
        offset=checkpoint.get('offset',0)
        return DiscoveryResult('mock',self.posts[offset:offset+50],{'offset':min(len(self.posts),offset+50)},'Synthetic fixtures only; no live platform coverage')

class YouTubeAdapter:
    def __init__(self,key,query,channel_id='',client=None):
        self.key,self.query,self.channel_id=key,query,channel_id
        self.client=client or httpx.Client(timeout=20)
    def discover(self,checkpoint):
        if not self.key or not (self.query or self.channel_id):
            return DiscoveryResult('unsupported',checkpoint=checkpoint,detail='YOUTUBE_API_KEY and YOUTUBE_QUERY or YOUTUBE_CHANNEL_ID required')
        # Replay an overlap to avoid losing boundary posts; DB deduplication handles repeats.
        since=checkpoint.get('since',(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat())
        params={'key':self.key,'part':'snippet','type':'video','order':'date','maxResults':50,'publishedAfter':since}
        if self.query: params['q']=self.query
        if self.channel_id: params['channelId']=self.channel_id
        if checkpoint.get('page'): params['pageToken']=checkpoint['page']
        response=self.client.get('https://www.googleapis.com/youtube/v3/search',params=params)
        # Do not propagate URLs (which contain the API key) into logs or errors.
        if response.status_code>=400: raise RuntimeError(f'YouTube API HTTP {response.status_code}; check quota and API permissions')
        data=response.json(); posts=[]
        for item in data.get('items',[]):
            video_id=item.get('id',{}).get('videoId')
            if video_id: posts.append({'external_id':video_id,'url':f'https://www.youtube.com/watch?v={video_id}', 'title':item['snippet']['title']})
        latest=max([item['snippet']['publishedAt'] for item in data.get('items',[])]+[since])
        watermark=max(checkpoint.get('latest',since),latest)
        next_checkpoint={'since':since,'page':data['nextPageToken'],'latest':watermark} if data.get('nextPageToken') else {
            'since':(datetime.fromisoformat(watermark.replace('Z','+00:00'))-timedelta(minutes=5)).isoformat()}
        return DiscoveryResult('metadata_only',posts,next_checkpoint,'Search API is partial coverage. Media requires rights-holder upload; no download API used.')

class DiscoveryAgent:
    def __init__(self,adapter): self.adapter=adapter
    def discover(self,checkpoint): return self.adapter.discover(checkpoint)
