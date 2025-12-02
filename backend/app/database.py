"""Database session and base configuration.

Reads DATABASE_URL from environment variables and exposes:
- engine: SQLAlchemy sync engine
- SessionLocal: session factory
- Base: declarative base for ORM models
- get_db: FastAPI dependency yielding a DB session

Note: Do not call Base.metadata.create_all(); use Alembic migrations only.
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Attempt to load from local .env for developer convenience
    # Attempt to load from local .env for developer convenience
    from app.utils.env import load_env_file
    load_env_file()
    DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Provide a clear error early if not configured
    raise RuntimeError("DATABASE_URL is not set. Ensure backend/.env is loaded or env var is exported.")

# Connection pool configuration for production performance
# - pool_size: Number of persistent connections to maintain
# - max_overflow: Additional connections allowed beyond pool_size during load spikes
# - pool_recycle: Recreate connections after 1 hour to prevent stale connections
# - pool_pre_ping: Check connection health before use (small overhead but prevents errors)
engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # Base pool size
    max_overflow=20,        # Allow up to 30 total connections under load
    pool_recycle=3600,      # Recycle connections every hour
    pool_pre_ping=True,     # Validate connections before use
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
# Base is defined in app.models to ensure a single registry across the app
from .models import Base  # noqa: E402


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it's closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


