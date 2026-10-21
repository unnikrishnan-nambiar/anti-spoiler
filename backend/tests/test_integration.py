"""Opt-in tests against an isolated Compose deployment, never a production database."""
import os, time, uuid
import pytest
from fastapi.testclient import TestClient
pytestmark=pytest.mark.skipif(os.getenv('RUN_INTEGRATION')!='1',reason='Requires running PostgreSQL, Redis, S3, API, and worker')

@pytest.fixture(scope='module')
def context(tmp_path_factory):
    from app.main import app
    from app.config import settings
    from app.samples import generate
    client=TestClient(app)
    login=client.post('/auth/login',json={'username':settings().admin_username,'password':settings().admin_password})
    assert login.status_code==200
    client.headers['Authorization']='Bearer '+login.json()['access_token']
    # Retain prior fixture records but pause their references to isolate repeated runs.
    for prior in client.get('/movies').json():
        if prior['title'].startswith('SYNTHETIC integration '):
            assert client.patch(f"/movies/{prior['id']}",json={'active':False}).status_code==200
    samples=generate(tmp_path_factory.mktemp('integration'))
    movie=client.post('/movies',json={'title':'SYNTHETIC integration '+uuid.uuid4().hex[:8],'spoiler_start':5})
    assert movie.status_code==201
    return client,samples,movie.json()['id']

def upload(context,name,kind='candidate',url=None):
    client,samples,movie_id=context
    with (samples/f'{name}.mp4').open('rb') as file:
        result=client.post('/media',files={'file':(name+'.mp4',file,'video/mp4')},data={
            **({'movie_id':movie_id} if kind!='candidate' else {}), 'kind':kind,'platform':'mock','post_url':url or 'https://example.invalid/'+uuid.uuid4().hex,'authorized':'true'})
    assert result.status_code==202,result.text
    return result.json()

def wait_media(client,media_id):
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        media=next(m for m in client.get('/media').json() if m['id']==media_id)
        if media['status'] in ('ready','complete'):return media
        assert media['status']!='failed',media
        time.sleep(.5)
    pytest.fail(f'media {media_id} did not finish')

def test_dependencies_and_auth(context):
    client,_,_=context
    assert client.get('/health/ready').status_code==200
    from app.main import app
    anonymous=TestClient(app)
    for path in ('/movies','/detections','/agents','/settings','/metrics','/media'):
        assert anonymous.get(path).status_code==401

def test_upload_index_detect_deduplicate_and_no_match(context):
    client,_,movie_id=context
    ref=upload(context,'reference','reference');assert wait_media(client,ref['id'])['status']=='ready'
    url='https://example.invalid/'+uuid.uuid4().hex
    candidate=upload(context,'candidate',url=url);wait_media(client,candidate['id'])
    matches=[d for d in client.get('/detections').json() if d['media_id']==candidate['id']]
    assert len(matches)==1 and matches[0]['verdict']=='confirmed',matches
    assert abs(matches[0]['scene_timestamp']-6)<=2
    detection_id=matches[0]['id']
    assert len([a for a in client.get('/alerts').json() if a['detection_id']==detection_id])==1
    duplicate=upload(context,'candidate',url=url);assert duplicate['id']==candidate['id']
    from app.tasks import process_media
    process_media.delay(candidate['id'])
    time.sleep(1)
    assert len([a for a in client.get('/alerts').json() if a['detection_id']==detection_id])==1
    unrelated=upload(context,'unrelated');wait_media(client,unrelated['id'])
    result=next(d for d in client.get('/detections').json() if d['media_id']==unrelated['id'])
    assert result['verdict']=='no_match' and result['movie_id'] is None

def test_promotional_exclusion(context):
    client,_,_=context
    promo=upload(context,'promotional','promotional');wait_media(client,promo['id'])
    candidate=upload(context,'candidate');wait_media(client,candidate['id'])
    result=next(d for d in client.get('/detections').json() if d['media_id']==candidate['id'])
    assert result['verdict']=='excluded_promotional'
    assert not [a for a in client.get('/alerts').json() if a['detection_id']==result['id']]

def test_viewer_rbac_and_private_objects(context):
    client,_,_=context
    name='viewer-'+uuid.uuid4().hex[:8];password='test-viewer-password-unique'
    assert client.post('/users',json={'username':name,'password':password,'role':'viewer'}).status_code==201
    from app.main import app
    viewer=TestClient(app)
    token=viewer.post('/auth/login',json={'username':name,'password':password}).json()['access_token']
    viewer.headers['Authorization']='Bearer '+token
    assert viewer.get('/movies').status_code==200
    assert viewer.get('/settings').status_code==403
    assert viewer.get('/media/1/content').status_code==403
    assert viewer.post('/movies',json={'title':'forbidden'}).status_code==403
    from app.storage import client as s3
    from app.config import settings
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    anonymous=boto3.client('s3',endpoint_url=settings().s3_endpoint,config=Config(signature_version=UNSIGNED))
    from botocore.exceptions import ClientError
    with pytest.raises(ClientError): anonymous.list_objects_v2(Bucket=settings().s3_bucket)

def test_durable_pending_recovery(context,monkeypatch):
    import app.main as main
    from app.tasks import recover
    client,_,_=context
    monkeypatch.setattr(main,'enqueue',lambda _:None)
    ref=upload(context,'unrelated','reference',url='https://example.invalid/lost-publish')
    assert ref['status']=='pending'
    recover.delay();assert wait_media(client,ref['id'])['status']=='ready'

def test_discovery_reports_limits_without_credentials(context):
    from app.tasks import discover
    from app.config import settings
    if settings().youtube_api_key:pytest.skip('Live YouTube API configured; covered separately with authorized credentials')
    discover.run()
    client,_,_=context
    agents=client.get('/agents').json()['agents'];states={a['name']:a['status'] for a in agents}
    assert states['discovery:instagram']=='unsupported'
    assert states['discovery:facebook']=='unsupported'

def test_reference_reindex_reports_version_and_audio_quality(context):
    client,_,_=context
    ref=upload(context,'reference','reference');wait_media(client,ref['id'])
    before=client.get(f"/media/{ref['id']}/index-summary")
    assert before.status_code==200
    assert before.json()['feature_version']==3 and before.json()['audio_version']==3
    assert before.json()['audio_quality']['landmarks']>100
    assert client.post(f"/media/{ref['id']}/reindex").status_code==202
    assert wait_media(client,ref['id'])['status']=='ready'
    assert client.get(f"/media/{ref['id']}/index-summary").json()==before.json()
