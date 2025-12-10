"""ARQ job enqueueing utilities.

WHAT:
    Async helper to enqueue sync jobs to ARQ worker.

WHY:
    - Provides async interface for FastAPI routes to enqueue jobs
    - Creates Redis pool on-demand, reuses connection

USAGE:
    from app.workers.arq_enqueue import enqueue_sync_job

    await enqueue_sync_job(connection_id, workspace_id, force_refresh=False)
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional, Dict, Any
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings, ArqRedis

logger = logging.getLogger(__name__)

# Global pool reference
_arq_pool: Optional[ArqRedis] = None


def get_redis_settings() -> RedisSettings:
    """Get Redis connection settings from environment.

    Supports:
    - redis://localhost:6379 (local)
    - redis://user:pass@host:port/db (authenticated)
    - rediss://user:pass@host:port (TLS/SSL - e.g., Upstash)
    """
    from urllib.parse import urlparse

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    parsed = urlparse(redis_url)

    # Determine if SSL is needed (rediss:// = SSL)
    use_ssl = parsed.scheme == "rediss"

    # Extract components
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    password = parsed.password
    database = int(parsed.path.lstrip("/")) if parsed.path and parsed.path != "/" else 0

    logger.info(f"[ARQ-ENQUEUE] Redis: host={host}, port={port}, ssl={use_ssl}, db={database}")

    return RedisSettings(
        host=host,
        port=port,
        password=password,
        database=database,
        ssl=use_ssl,
        ssl_cert_reqs='none' if use_ssl else None,  # For Upstash compatibility
    )


async def get_arq_pool() -> ArqRedis:
    """Get or create ARQ Redis pool."""
    global _arq_pool
    if _arq_pool is None:
        logger.info("[ARQ-ENQUEUE] Creating new Redis pool...")
        _arq_pool = await create_pool(get_redis_settings())
        logger.info("[ARQ-ENQUEUE] Redis pool created successfully")
    return _arq_pool


async def reset_arq_pool() -> None:
    """Reset the ARQ pool (useful for testing or reconnection)."""
    global _arq_pool
    if _arq_pool is not None:
        await _arq_pool.close()
        _arq_pool = None
        logger.info("[ARQ-ENQUEUE] Redis pool reset")


async def enqueue_sync_job(
    connection_id: str | UUID,
    workspace_id: str | UUID,
    force_refresh: bool = False,
    backfill: bool = False,
) -> Dict[str, Any]:
    """Enqueue a sync job to ARQ.

    Args:
        connection_id: Connection UUID
        workspace_id: Workspace UUID
        force_refresh: If True, re-sync last 7 days (attribution mode)
        backfill: If True, sync 90 days of historical data (for new connections)

    Returns:
        Dict with job_id and status
    """
    pool = await get_arq_pool()

    job = await pool.enqueue_job(
        "process_sync_job",
        str(connection_id),
        str(workspace_id),
        force_refresh,
        backfill,
        _queue_name="arq:queue",
    )

    if job:
        logger.info("[ARQ] Enqueued sync job %s for connection %s (backfill=%s)", job.job_id, connection_id, backfill)
        return {"job_id": job.job_id, "status": "enqueued"}
    else:
        logger.warning("[ARQ] Job might already exist for connection %s", connection_id)
        return {"job_id": None, "status": "skipped_or_duplicate"}


async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get status of an ARQ job."""
    from arq.jobs import Job

    pool = await get_arq_pool()
    job = Job(job_id, pool)

    status = await job.status()
    result = await job.result(timeout=0) if status.name == "complete" else None

    return {
        "job_id": job_id,
        "status": status.name,
        "result": result,
    }


def enqueue_sync_job_sync(
    connection_id: str | UUID,
    workspace_id: str | UUID,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """Synchronous wrapper for enqueue_sync_job.

    Use this in sync contexts (like FastAPI sync endpoints).
    """
    return asyncio.run(enqueue_sync_job(connection_id, workspace_id, force_refresh))
