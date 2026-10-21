import boto3
from botocore.config import Config
from .config import settings

def client():
    s = settings()
    return boto3.client('s3', endpoint_url=s.s3_endpoint, aws_access_key_id=s.s3_access_key,
                        aws_secret_access_key=s.s3_secret_key, config=Config(signature_version='s3v4', retries={'max_attempts': 5}))

def put_file(path, key, content_type='application/octet-stream'):
    client().upload_file(str(path), settings().s3_bucket, key, ExtraArgs={'ContentType': content_type})

def download(key, path): client().download_file(settings().s3_bucket, key, str(path))
def put_json(key, data):
    import json
    client().put_object(Bucket=settings().s3_bucket, Key=key, Body=json.dumps(data).encode(), ContentType='application/json')
def get_json(key):
    import json
    return json.loads(client().get_object(Bucket=settings().s3_bucket, Key=key)['Body'].read())
