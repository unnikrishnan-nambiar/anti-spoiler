from sqlalchemy import text, select
from .db import engine, Base, Session, User
from .config import settings
from .security import hash_password
from .storage import client
from botocore.exceptions import ClientError

def main():
    with engine.begin() as connection: connection.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
    Base.metadata.create_all(engine)
    with Session.begin() as db:
        if not db.scalar(select(User).where(User.username == settings().admin_username)):
            db.add(User(username=settings().admin_username, password_hash=hash_password(settings().admin_password), role='admin'))
    s3 = client()
    try: s3.head_bucket(Bucket=settings().s3_bucket)
    except ClientError as exc:
        if exc.response['Error']['Code'] not in ('404', 'NoSuchBucket'): raise
        s3.create_bucket(Bucket=settings().s3_bucket)
    # SeaweedFS denies anonymous S3 access when identity credentials are configured.
    # AWS deployments must separately enforce Block Public Access and SSE-KMS (see docs).

if __name__ == '__main__': main()
