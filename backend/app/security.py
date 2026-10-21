import hashlib, hmac, secrets, time
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings
from .db import Session, User
from sqlalchemy import select

bearer = HTTPBearer(auto_error=False)
def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
    return f'{salt}:{digest}'

def verify_password(password, encoded):
    salt, digest = encoded.split(':')
    return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex(), digest)

def issue_token(user):
    return jwt.encode({'sub': str(user.id), 'exp': int(time.time())+3600}, settings().jwt_secret, algorithm='HS256')

def current_user(auth: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        if not auth: raise ValueError()
        claims = jwt.decode(auth.credentials, settings().jwt_secret, algorithms=['HS256'])
        with Session() as db: user = db.get(User, int(claims['sub']))
        if not user: raise ValueError()
        return user
    except (ValueError, KeyError, jwt.PyJWTError):
        raise HTTPException(401, 'Authentication required')

def roles(*allowed):
    def check(user=Depends(current_user)):
        if user.role not in allowed: raise HTTPException(403, 'Insufficient role')
        return user
    return check
