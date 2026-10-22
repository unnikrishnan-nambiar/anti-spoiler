import boto3
from botocore.config import Config
from .config import settings

def client():
    s = settings()
    return boto3.client('s3', endpoint_url=s.s3_endpoint, aws_access_key_id=s.s3_access_key,
                        aws_secret_access_key=s.s3_secret_key, config=Config(signature_version='s3v4', retries={'max_attempts': 5}))

def put_file(path, key, content_type='application/octet-stream'):
    if settings().local_storage_path:
        import shutil
        target=local_path(key); target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target); target.chmod(0o600); return
    client().upload_file(str(path), settings().s3_bucket, key, ExtraArgs={'ContentType': content_type})

def local_path(key):
    from pathlib import Path
    root=Path(settings().local_storage_path).resolve()
    path=(root/key).resolve()
    if path==root or root not in path.parents: raise ValueError('Invalid storage key')
    return path

def download(key, path):
    if settings().local_storage_path:
        import shutil
        shutil.copyfile(local_path(key),path); return
    client().download_file(settings().s3_bucket, key, str(path))
def put_json(key, data):
    import json
    if settings().local_storage_path:
        target=local_path(key); target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(data)); target.chmod(0o600); return
    client().put_object(Bucket=settings().s3_bucket, Key=key, Body=json.dumps(data).encode(), ContentType='application/json')
def get_json(key):
    import json
    if settings().local_storage_path: return json.loads(local_path(key).read_text())
    return json.loads(client().get_object(Bucket=settings().s3_bucket, Key=key)['Body'].read())
