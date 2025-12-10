"""Sync scheduler service - ARQ-based cron scheduler.

WHAT:
    Dedicated cron scheduler for periodic sync jobs using ARQ.
    Runs cron jobs that enqueue work to the ARQ worker.

WHY:
    - Separation of concerns: scheduler handles timing, worker handles processing
    - Single scheduler instance prevents duplicate cron job execution
    - ARQ provides reliable, persistent cron scheduling with Redis

SYNC SCHEDULE (all times UTC):
    - :00, :15, :30, :45 every hour: Realtime sync (Meta, Google)
    - 01:00 daily: Compact 2-day-old snapshots (15-min → hourly)
    - 03:00 daily: Re-fetch last 7 days for attribution corrections

ARCHITECTURE:
    ┌──────────────────┐   enqueues jobs   ┌─────────────────┐
    │ sync_scheduler   │──────────────────▶│  arq_worker     │
    │ (cron only)      │                   │ (job processor) │
    └──────────────────┘                   └─────────────────┘

REFERENCES:
    - app/workers/arq_worker.py (job definitions)
    - app/workers/arq_enqueue.py (enqueueing)
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict

from arq import cron, run_worker
from arq.connections import RedisSettings

from app.telemetry import capture_exception

logger = logging.getLogger(__name__)


# =============================================================================
# REDIS SETTINGS
# =============================================================================

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

    use_ssl = parsed.scheme == "rediss"
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    password = parsed.password
    database = int(parsed.path.lstrip("/")) if parsed.path and parsed.path != "/" else 0

    logger.info(f"[SCHEDULER] Redis: host={host}, port={port}, ssl={use_ssl}, db={database}")

    return RedisSettings(
        host=host,
        port=port,
        password=password,
        database=database,
        ssl=use_ssl,
        ssl_cert_reqs='none' if use_ssl else None,
        conn_timeout=30,
        conn_retries=5,
        conn_retry_delay=1,
    )


# =============================================================================
# CRON JOB FUNCTIONS - Import from arq_worker to avoid duplication
# =============================================================================

# Import the scheduled job functions from arq_worker
# These functions enqueue work to be processed by the worker
from app.workers.arq_worker import (
    scheduled_realtime_sync,
    scheduled_attribution_sync,
    scheduled_compaction,
)


# =============================================================================
# SCHEDULER LIFECYCLE
# =============================================================================

async def scheduler_startup(ctx: Dict) -> None:
    """Scheduler startup - log configuration."""
    import platform

    logger.info("=" * 60)
    logger.info("[SCHEDULER] ARQ Scheduler starting up")
    logger.info("=" * 60)
    logger.info(f"[SCHEDULER] Python: {platform.python_version()}")
    logger.info(f"[SCHEDULER] Host: {platform.node()}")
    logger.info("[SCHEDULER] Cron schedule:")
    logger.info("[SCHEDULER]   - Realtime sync: every 15 min (:00, :15, :30, :45)")
    logger.info("[SCHEDULER]   - Compaction: daily at 01:00 UTC")
    logger.info("[SCHEDULER]   - Attribution: daily at 03:00 UTC")
    logger.info("=" * 60)

    ctx['startup_time'] = datetime.now(timezone.utc)


async def scheduler_shutdown(ctx: Dict) -> None:
    """Scheduler shutdown - log stats."""
    uptime = datetime.now(timezone.utc) - ctx.get('startup_time', datetime.now(timezone.utc))

    logger.info("=" * 60)
    logger.info("[SCHEDULER] ARQ Scheduler shutting down")
    logger.info(f"[SCHEDULER] Uptime: {uptime}")
    logger.info("=" * 60)


# =============================================================================
# SCHEDULER SETTINGS - Cron jobs only, no ad-hoc job processing
# =============================================================================

class SchedulerSettings:
    """ARQ scheduler configuration - runs cron jobs only.

    WHAT:
        Dedicated scheduler that ONLY runs cron jobs.
        Does NOT process ad-hoc sync jobs (that's the worker's job).

    WHY:
        - Single scheduler instance prevents duplicate cron execution
        - Workers can scale independently for job processing
        - Clear separation of concerns
    """

    # No ad-hoc job functions - this is a scheduler, not a worker
    # The cron jobs enqueue work to be processed by arq_worker
    functions = [
        scheduled_realtime_sync,
        scheduled_attribution_sync,
        scheduled_compaction,
    ]

    # Cron jobs (the main purpose of this service)
    cron_jobs = [
        # Every 15 minutes: realtime sync for today's data
        cron(scheduled_realtime_sync, minute={0, 15, 30, 45}, run_at_startup=False),

        # Daily at 01:00 UTC: compact 2-day-old snapshots to hourly
        cron(scheduled_compaction, hour=1, minute=0, run_at_startup=False),

        # Daily at 03:00 UTC: re-fetch last 7 days for attribution
        cron(scheduled_attribution_sync, hour=3, minute=0, run_at_startup=False),
    ]

    # Lifecycle hooks
    on_startup = scheduler_startup
    on_shutdown = scheduler_shutdown

    # Redis connection
    redis_settings = get_redis_settings()

    # Minimal resource usage - scheduler just triggers cron, doesn't process jobs
    max_jobs = 1                     # Only run one cron job at a time
    job_timeout = 60                 # Cron jobs just enqueue, should be fast
    keep_result = 300                # Keep results for 5 min
    health_check_interval = 30       # Health check every 30s

    # Queue name (same as worker so cron jobs can enqueue to it)
    queue_name = "arq:queue"


# =============================================================================
# INITIAL SYNC HELPERS (for new connections)
# =============================================================================

async def enqueue_initial_sync_async(connection_id: str, workspace_id: str) -> bool:
    """Async version of enqueue_initial_sync for use in async contexts (FastAPI).

    WHAT:
        Triggers an immediate sync job via ARQ so users see data right away
        instead of waiting up to 15 minutes for the next scheduled sync.

    Args:
        connection_id: UUID of the new connection
        workspace_id: UUID of the workspace

    Returns:
        True if job was enqueued successfully, False otherwise
    """
    try:
        from app.workers.arq_enqueue import enqueue_sync_job

        result = await enqueue_sync_job(connection_id, workspace_id, force_refresh=False)
        job_id = result.get("job_id")
        if job_id:
            logger.info("[SCHEDULER] Enqueued initial sync for connection %s, job_id=%s", connection_id, job_id)
            return True
        else:
            logger.warning("[SCHEDULER] Failed to enqueue job for %s", connection_id)
            return False
    except Exception as e:
        logger.exception("[SCHEDULER] Failed to enqueue initial sync for %s: %s", connection_id, e)
        capture_exception(e, extra={
            "operation": "enqueue_initial_sync",
            "connection_id": connection_id,
        })
        return False


def enqueue_initial_sync(connection_id: str, workspace_id: str, run_sync: bool = True) -> bool:
    """Enqueue an immediate sync for a newly created connection (sync version).

    WHAT:
        Triggers an immediate sync job via ARQ so users see data right away
        instead of waiting up to 15 minutes for the next scheduled sync.

    WHEN:
        Called immediately after a new connection is created via OAuth.
        NOTE: For async contexts (FastAPI), use enqueue_initial_sync_async instead.

    Args:
        connection_id: UUID of the new connection
        workspace_id: UUID of the workspace
        run_sync: Unused, kept for backwards compatibility

    Returns:
        True if job was enqueued successfully, False otherwise
    """
    try:
        import asyncio
        from app.workers.arq_enqueue import enqueue_sync_job

        # Check if we're in an existing event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context - schedule as a task
            logger.warning("[SCHEDULER] Called sync enqueue_initial_sync from async context. Use enqueue_initial_sync_async instead.")
            asyncio.create_task(enqueue_initial_sync_async(connection_id, workspace_id))
            return True
        except RuntimeError:
            # No running loop - safe to use asyncio.run()
            result = asyncio.run(enqueue_sync_job(connection_id, workspace_id, force_refresh=False))

        job_id = result.get("job_id")
        if job_id:
            logger.info("[SCHEDULER] Enqueued initial sync for connection %s, job_id=%s", connection_id, job_id)
            return True
        else:
            logger.warning("[SCHEDULER] Failed to enqueue job for %s", connection_id)
            return False
    except Exception as e:
        logger.exception("[SCHEDULER] Failed to enqueue initial sync for %s: %s", connection_id, e)
        capture_exception(e, extra={
            "operation": "enqueue_initial_sync",
            "connection_id": connection_id,
        })
        return False


# Legacy alias for backwards compatibility
trigger_sync_for_connection = enqueue_initial_sync


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def run_scheduler() -> None:
    """Main entry point - start the ARQ scheduler."""
    logger.info("[SCHEDULER] Starting ARQ-based scheduler...")
    run_worker(SchedulerSettings)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    run_scheduler()
