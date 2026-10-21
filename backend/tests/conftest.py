import os
# Deterministic test configuration, never deployment credentials.
os.environ.setdefault('S3_ACCESS_KEY','test-access')
os.environ.setdefault('S3_SECRET_KEY','test-secret')
os.environ.setdefault('JWT_SECRET','test-secret-not-for-deployment-123456789')
os.environ.setdefault('ADMIN_PASSWORD','test-password-not-for-deployment')
