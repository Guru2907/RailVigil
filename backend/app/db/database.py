"""SQLAlchemy engine/session setup. SQLite for local dev — one file, no
server needed. Swap DATABASE_URL in .env to a Postgres URL later;
nothing else in the codebase has to change."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core import config

connect_args = {"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {}
engine = create_engine(config.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a session, closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Called once on app startup. Imports models so SQLAlchemy knows
    about them, then creates any tables that don't exist yet."""
    from app.db.models import video, detection, incident, user  # noqa: F401
    Base.metadata.create_all(bind=engine)