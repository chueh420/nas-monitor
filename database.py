from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nas_monitor.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, unique=True, index=True)
    nas_type    = Column(String)       # synology / qnap
    api_key     = Column(String, unique=True, index=True)
    email       = Column(String)       # 負責人信箱
    last_seen   = Column(DateTime, nullable=True)
    last_status = Column(String, default="unknown")
    created_at  = Column(DateTime, default=datetime.now)


class NASReport(Base):
    __tablename__ = "nas_reports"
    id             = Column(Integer, primary_key=True, index=True)
    client_id      = Column(Integer, index=True)
    timestamp      = Column(DateTime, default=datetime.now, index=True)
    cpu_usage      = Column(Float)
    memory_usage   = Column(Float)
    disk_usage     = Column(Float)    # 最高使用率的磁碟
    backup_status  = Column(String)   # ok / failed / warning / unknown
    backup_details = Column(Text)


class Alert(Base):
    __tablename__ = "alerts"
    id          = Column(Integer, primary_key=True, index=True)
    client_id   = Column(Integer, index=True)
    client_name = Column(String)
    timestamp   = Column(DateTime, default=datetime.now)
    alert_type  = Column(String)   # backup_fail / disk_full / cpu_high / offline
    message     = Column(Text)
    resolved    = Column(Boolean, default=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
