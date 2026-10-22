"""Database engine/session setup.

SQLite by default; PostgreSQL (or any SQLAlchemy URL) can be used later by
setting DATABASE_URL in .env — no code changes required.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

# Env-based DATABASE_URL, defaulting to a local SQLite file.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recycling.db")

# check_same_thread=False is required for SQLite + FastAPI's threadpool.
# For a concurrent-claim test we need cross-thread writes, so enable it.
engine_kwargs = {"future": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

# Enable WAL mode + foreign keys on every SQLite connection so concurrent
# writes and FK enforcement behave sensibly.
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db():
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables (idempotent)."""
    from app import models  # noqa: F401  (register mappers)
    Base.metadata.create_all(bind=engine)
