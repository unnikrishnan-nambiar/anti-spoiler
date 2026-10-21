from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, Float, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import JSON
from pgvector.sqlalchemy import Vector
from .config import settings

class Base(DeclarativeBase): pass

def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default='viewer')

class Movie(Base):
    __tablename__ = 'movies'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    spoiler_start: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Media(Base):
    __tablename__ = 'media'
    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int | None] = mapped_column(ForeignKey('movies.id'))
    kind: Mapped[str] = mapped_column(String(20)) # reference, promotional, candidate
    object_key: Mapped[str] = mapped_column(Text, unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    dedup_key: Mapped[str] = mapped_column(String(64), unique=True)
    platform: Mapped[str | None] = mapped_column(String(30))
    post_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default='pending')
    stage: Mapped[str] = mapped_column(String(40), default='queued')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    feature_key: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class SceneVector(Base):
    __tablename__ = 'scene_vectors'
    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey('media.id', ondelete='CASCADE'))
    timestamp: Mapped[float] = mapped_column(Float)
    embedding: Mapped[list] = mapped_column(Vector(512))
    __table_args__ = (UniqueConstraint('media_id', 'timestamp'), Index('scene_embedding_hnsw','embedding',postgresql_using='hnsw',postgresql_ops={'embedding':'vector_cosine_ops'}))

class Detection(Base):
    __tablename__ = 'detections'
    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey('media.id'), unique=True)
    movie_id: Mapped[int | None] = mapped_column(ForeignKey('movies.id'))
    scene_timestamp: Mapped[float] = mapped_column(Float, default=0)
    confidence: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(30))
    verdict: Mapped[str] = mapped_column(String(30))
    evidence: Mapped[dict] = mapped_column(JSON)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Alert(Base):
    __tablename__ = 'alerts'
    id: Mapped[int] = mapped_column(primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey('detections.id'), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class SourcePost(Base):
    __tablename__ = 'source_posts'
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(30))
    external_id: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default='awaiting_authorized_media')
    __table_args__ = (UniqueConstraint('platform', 'external_id'),)

class AgentState(Base):
    __tablename__ = 'agent_states'
    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    status: Mapped[str] = mapped_column(String(40))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class Preference(Base):
    __tablename__ = 'preferences'
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)

engine = create_engine(settings().database_url, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)
