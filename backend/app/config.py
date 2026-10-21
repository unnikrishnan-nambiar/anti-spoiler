from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'postgresql+psycopg://sceneguard:sceneguard@db/sceneguard'
    redis_url: str = 'redis://redis:6379/0'
    s3_endpoint: str = 'http://objectstore:9000'
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = 'sceneguard-private'
    jwt_secret: str
    admin_username: str = 'admin'
    admin_password: str
    youtube_api_key: str = ''
    youtube_query: str = ''
    youtube_channel_id: str = ''
    match_threshold: float = 0.75
    review_threshold: float = 0.45
    audio_threshold: float = 0.2
    max_media_bytes: int = 524288000
    max_duration_seconds: int = 7200
    frame_interval: float = 2.0
    laya_enabled: bool = False
    laya_service_url: str = ''
    laya_service_token: str = ''
    clip_model: str = ''
    multimodal_url: str = ''
    multimodal_api_key: str = ''
    multimodal_model: str = ''
    secure_cookie: bool = False

@lru_cache
def settings():
    value = Settings()
    if len(value.jwt_secret) < 32 or len(value.admin_password) < 12:
        raise ValueError('JWT_SECRET requires 32 characters; ADMIN_PASSWORD requires 12')
    return value
