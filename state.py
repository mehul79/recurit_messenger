import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Text, JSON, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    link = Column(String, nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    stipend = Column(String, nullable=True)
    ctc = Column(String, nullable=True)
    location = Column(String, nullable=True)
    raw_json = Column(JSON, nullable=True)
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    new_alert_sent = Column(Boolean, default=False, nullable=False)

    state = relationship("JobState", back_populates="job", uselist=False, cascade="all, delete-orphan")

class JobState(Base):
    __tablename__ = "job_state"

    job_id = Column(String, ForeignKey("jobs.job_id"), primary_key=True)
    applied = Column(Boolean, default=False, nullable=False)
    opted_out = Column(Boolean, default=False, nullable=False)
    acknowledged = Column(Boolean, default=False, nullable=False)
    checkpoints_sent = Column(JSON, default=list, nullable=False)  # e.g. ["2h", "1.5h"]

    job = relationship("Job", back_populates="state")

class NotificationLog(Base):
    __tablename__ = "notification_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.job_id"), nullable=True)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    kind = Column(String, nullable=False)  # 'new_job' | 'checkpoint_2h' | ... | 'button_optout' | 'button_ack'
    message = Column(Text, nullable=True)

class Meta(Base):
    __tablename__ = "meta"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)

_engine = None
_SessionLocal = None

def get_engine():
    global _engine
    if _engine is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL environment variable is missing!")
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal()

def init_db():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
