"""
Database engine, session management, and schema initialization
"""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.config import settings

# Ensure data directory exists
data_dir = Path("./data")
data_dir.mkdir(parents=True, exist_ok=True)

# Reports directory for generated exports
reports_dir = Path("./data/reports")
reports_dir.mkdir(parents=True, exist_ok=True)

# SQLite database engine
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI database session dependency"""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from backend.app.models import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
