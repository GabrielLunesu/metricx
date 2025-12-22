"""Database session and base configuration.

WHAT:
    Provides both sync and async SQLAlchemy engines and session factories.
    Exposes FastAPI dependencies for database access.

WHY:
    - Sync sessions: Background workers, migrations, existing code compatibility
    - Async sessions: High-performance API endpoints, parallel queries
    - Async is 2-5x faster for I/O-bound operations

ARCHITECTURE:
    ┌──────────────────┐     ┌───────────────────┐
    │  Sync Engine     │     │  Async Engine     │
    │  (psycopg2)      │     │  (asyncpg)        │
    └────────┬─────────┘     └─────────┬─────────┘
             │                         │
    ┌────────▼─────────┐     ┌─────────▼─────────┐
    │  SessionLocal    │     │ AsyncSessionLocal │
    └────────┬─────────┘     └─────────┬─────────┘
             │                         │
    ┌────────▼─────────┐     ┌─────────▼─────────┐
    │  get_db()        │     │  get_async_db()   │
    │  (sync dep)      │     │  (async dep)      │
    └──────────────────┘     └───────────────────┘

USAGE:
    # Sync (existing code, workers)
    from app.database import SessionLocal, get_db

    # Async (new endpoints)
    from app.database import AsyncSessionLocal, get_async_db

    @app.get("/fast-endpoint")
    async def fast_endpoint(db: AsyncSession = Depends(get_async_db)):
        result = await db.execute(select(Model).where(...))
        return result.scalars().all()

REFERENCES:
    - https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
    - app/routers/ (consumers of these sessions)
"""

import os
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker


# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================

def _get_database_url() -> str:
    """Get DATABASE_URL from environment, loading .env if needed.

    Returns:
        PostgreSQL connection string

    Raises:
        RuntimeError: If DATABASE_URL is not configured
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Attempt to load from local .env for developer convenience
        from app.utils.env import load_env_file
        load_env_file()
        database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Ensure backend/.env is loaded or env var is exported."
        )

    return database_url


def _get_async_database_url(sync_url: str) -> str:
    """Convert sync DATABASE_URL to async format.

    WHAT:
        Converts postgresql:// to postgresql+asyncpg://

    WHY:
        SQLAlchemy async engine requires asyncpg driver prefix.

    Args:
        sync_url: Standard PostgreSQL URL (postgresql://)

    Returns:
        Async-compatible URL (postgresql+asyncpg://)
    """
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif sync_url.startswith("postgres://"):
        # Heroku-style URL
        return sync_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return sync_url


DATABASE_URL = _get_database_url()
ASYNC_DATABASE_URL = _get_async_database_url(DATABASE_URL)


# =============================================================================
# SYNC ENGINE (existing code, workers, migrations)
# =============================================================================

# Connection pool configuration for production performance:
# - pool_size: Number of persistent connections to maintain
# - max_overflow: Additional connections allowed beyond pool_size during load spikes
# - pool_recycle: Recreate connections after 1 hour to prevent stale connections
# - pool_pre_ping: Check connection health before use (small overhead but prevents errors)
#
# NOTE: SQLite engines (used in some tests/dev) do not support pool_size/max_overflow.
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,           # Base pool size
        max_overflow=20,        # Allow up to 30 total connections under load
        pool_recycle=3600,      # Recycle connections every hour
        pool_pre_ping=True,     # Validate connections before use
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# =============================================================================
# ASYNC ENGINE (high-performance API endpoints)
# =============================================================================

# Async engine with similar pool settings
# asyncpg is ~2-5x faster than psycopg2 for I/O-bound operations
#
# NOTE: We only initialize the async engine for PostgreSQL. SQLite async usage
# would require aiosqlite, which is not a production dependency for this project.
async_engine = None
AsyncSessionLocal = None
if ASYNC_DATABASE_URL.startswith("postgresql+asyncpg://"):
    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        pool_size=10,           # Base pool size
        max_overflow=20,        # Allow up to 30 total connections under load
        pool_recycle=3600,      # Recycle connections every hour to prevent stale connections
        pool_pre_ping=True,     # Validate connections before use
        echo=False,             # Set True for SQL debugging
    )

    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Prevent lazy load issues after commit
        autoflush=False,
        autocommit=False,
    )


# =============================================================================
# BASE MODEL (imported from models for single registry)
# =============================================================================

# Base is defined in app.models to ensure a single registry across the app
from .models import Base  # noqa: E402


# =============================================================================
# FASTAPI DEPENDENCIES
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """Yield a sync database session for FastAPI dependency injection.

    WHAT:
        Creates a sync session, yields it, and ensures cleanup.

    WHY:
        Backward compatibility with existing sync endpoints.
        Use for endpoints that don't need async performance.

    Yields:
        SQLAlchemy Session instance

    Example:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI dependency injection.

    WHAT:
        Creates an async session, yields it, and ensures cleanup.

    WHY:
        High-performance endpoints that benefit from async I/O.
        ~2-5x faster than sync for database-heavy operations.

    Yields:
        AsyncSession instance

    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# =============================================================================
# CONTEXT MANAGERS (for non-FastAPI usage)
# =============================================================================

@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Context manager for sync sessions outside FastAPI.

    WHAT:
        Creates a sync session with automatic cleanup.

    WHY:
        For use in workers, scripts, and tests where FastAPI
        dependency injection isn't available.

    Yields:
        SQLAlchemy Session instance

    Example:
        with get_sync_session() as db:
            items = db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for async sessions outside FastAPI.

    WHAT:
        Creates an async session with automatic cleanup.

    WHY:
        For use in async workers, scripts, and tests where FastAPI
        dependency injection isn't available.

    Yields:
        AsyncSession instance

    Example:
        async with get_async_session() as db:
            result = await db.execute(select(Item))
            items = result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
