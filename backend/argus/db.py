from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, event, String, Float, Integer, Boolean, JSON, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

def uid(): return uuid4().hex

def now(): return datetime.now(timezone.utc).isoformat()

class Base(DeclarativeBase): pass
class Record(Base):
    __abstract__ = True
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=uid)
    created_at: Mapped[str] = mapped_column(String(40), default=now, index=True)

class User(Record):
    __tablename__ = 'users'
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(40), default='Operator')
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class Session(Record):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires: Mapped[float] = mapped_column(Float)

class Video(Record):
    __tablename__ = 'videos'
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(Text)
    playback: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON)
    location: Mapped[dict] = mapped_column(JSON, default=dict)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)

class Geometry(Record):
    __tablename__ = 'geometries'
    video_id: Mapped[str] = mapped_column(ForeignKey('videos.id'), index=True)
    kind: Mapped[str] = mapped_column(String(10))
    config: Mapped[dict] = mapped_column(JSON)

class Job(Record):
    __tablename__ = 'jobs'
    video_id: Mapped[str] = mapped_column(ForeignKey('videos.id'), index=True)
    mode: Mapped[str] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(20), default='QUEUED', index=True)
    config: Mapped[dict] = mapped_column(JSON)
    progress: Mapped[float] = mapped_column(Float, default=0)
    frame: Mapped[int] = mapped_column(Integer, default=0)
    processing_fps: Mapped[float] = mapped_column(Float, default=0)
    elapsed: Mapped[float] = mapped_column(Float, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    heartbeat: Mapped[float] = mapped_column(Float, default=0)

class Track(Record):
    __tablename__ = 'tracks'
    job_id: Mapped[str] = mapped_column(ForeignKey('jobs.id'), index=True)
    track_id: Mapped[str] = mapped_column(String(40), index=True)
    object_class: Mapped[str] = mapped_column(String(30), index=True)
    data: Mapped[dict] = mapped_column(JSON)
    convoy_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    designated_at: Mapped[float | None] = mapped_column(Float, nullable=True)

class Event(Record):
    __tablename__ = 'events'
    job_id: Mapped[str] = mapped_column(ForeignKey('jobs.id'), index=True)
    video_id: Mapped[str] = mapped_column(ForeignKey('videos.id'), index=True)
    type: Mapped[str] = mapped_column(String(80), index=True)
    video_time: Mapped[float] = mapped_column(Float)
    frame: Mapped[int] = mapped_column(Integer)
    zone: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    track_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    object_class: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default='MEDIUM')
    status: Mapped[str] = mapped_column(String(30), default='NEW', index=True)
    snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule: Mapped[dict] = mapped_column(JSON)
    analytics: Mapped[dict] = mapped_column(JSON, default=dict)
    reviews: Mapped[list] = mapped_column(JSON, default=list)
    clip: Mapped[str | None] = mapped_column(Text, nullable=True)

class Incident(Record):
    __tablename__ = 'incidents'
    event_id: Mapped[str] = mapped_column(ForeignKey('events.id'), unique=True)
    number: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80))
    priority: Mapped[str] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(30), default='VERIFIED')
    assignment: Mapped[str | None] = mapped_column(String(80), nullable=True)
    timeline: Mapped[list] = mapped_column(JSON, default=list)

class Audit(Record):
    __tablename__ = 'audit'
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource: Mapped[str] = mapped_column(String(100), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)

class Service(Record):
    __tablename__ = 'services'
    name: Mapped[str] = mapped_column(String(80), unique=True)
    heartbeat: Mapped[float] = mapped_column(Float)
    data: Mapped[dict] = mapped_column(JSON, default=dict)

class Simulation(Record):
    __tablename__ = 'simulations'
    mode: Mapped[str] = mapped_column(String(30), default='No Person')
    speed: Mapped[float] = mapped_column(Float, default=1)
    started: Mapped[float] = mapped_column(Float)
    timeline: Mapped[list] = mapped_column(JSON, default=list)

engine = create_engine(settings.database_url, connect_args={'check_same_thread': False, 'timeout':30} if settings.database_url.startswith('sqlite') else {}, pool_pre_ping=True)
if settings.database_url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_setup(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA journal_mode=WAL')
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        yield db

def audit(db, actor, action, resource='', detail=None):
    db.add(Audit(actor=actor, action=action, resource=resource, detail=detail or {}))

def serialize(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name not in {'password','token_hash','path','playback','snapshot','observations','clip'}}

class Role(Record):
    __tablename__ = 'roles'
    name: Mapped[str] = mapped_column(String(40),unique=True)
    permissions: Mapped[list] = mapped_column(JSON)

class AIModel(Record):
    __tablename__ = 'ai_models'
    name: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(100))
    filename: Mapped[str] = mapped_column(String(200),unique=True)
    state: Mapped[str] = mapped_column(String(20),default='APPROVED')
    sha256: Mapped[str | None] = mapped_column(String(64),nullable=True)

class Camera(Record):
    """A live source. Its placeholder Video row (path live://<camera id>) anchors zones, sessions and events."""
    __tablename__ = 'cameras'
    name: Mapped[str] = mapped_column(String(120),unique=True)
    url: Mapped[str] = mapped_column(Text)
    video_id: Mapped[str] = mapped_column(ForeignKey('videos.id'),unique=True)
    mode: Mapped[str] = mapped_column(String(20),default='Detect & Annotate')
    fps: Mapped[float] = mapped_column(Float,default=5)
    confidence: Mapped[float] = mapped_column(Float,default=.3)
    imgsz: Mapped[int] = mapped_column(Integer,default=960)
    width: Mapped[int] = mapped_column(Integer,default=1280)
    enabled: Mapped[bool] = mapped_column(Boolean,default=True)
    lock_track_id: Mapped[str | None] = mapped_column(String(40),nullable=True)
    classes: Mapped[list | None] = mapped_column(JSON,nullable=True)
    tiling: Mapped[bool] = mapped_column(Boolean,default=False)
    min_box: Mapped[int] = mapped_column(Integer,default=0)
    status: Mapped[dict] = mapped_column(JSON,default=dict)
    heartbeat: Mapped[float] = mapped_column(Float,default=0)
    updated_at: Mapped[str] = mapped_column(String(40),default=now)

class SavedDetection(Record):
    """An operator-saved frame with the detections visible at that moment (after the chosen filters)."""
    __tablename__ = 'saved_detections'
    actor: Mapped[str] = mapped_column(String(80))
    job_id: Mapped[str] = mapped_column(ForeignKey('jobs.id'),index=True)
    video_id: Mapped[str] = mapped_column(ForeignKey('videos.id'),index=True)
    camera_id: Mapped[str | None] = mapped_column(String(40),nullable=True,index=True)
    video_time: Mapped[float] = mapped_column(Float)
    note: Mapped[str] = mapped_column(Text,default='')
    snapshot: Mapped[str] = mapped_column(Text)
    detections: Mapped[list] = mapped_column(JSON,default=list)
    filters: Mapped[dict] = mapped_column(JSON,default=dict)

class WatchTrack(Record):
    """A person track watched for the lifetime of one live camera session."""
    __tablename__ = 'watch_tracks'
    camera_id: Mapped[str] = mapped_column(ForeignKey('cameras.id'), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey('jobs.id'), index=True)
    track_id: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    alerted: Mapped[bool] = mapped_column(Boolean, default=False)
