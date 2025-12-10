"""Sync scheduler service.

WHAT:
    Manages periodic sync jobs for all ad platforms and Shopify.
    Implements the standard 15-min sync strategy at FIXED clock times.

WHY:
    - 15-min sync matches Meta's data refresh rate
    - Fixed clock times (:00, :15, :30, :45) for predictable syncing
    - Daily jobs handle attribution corrections and compaction
    - Centralized scheduling for all data sync operations

SYNC SCHEDULE (all times UTC):
    - :00, :15, :30, :45 every hour: Realtime sync (Meta, Google, Shopify)
    - 01:00 daily: Compact 2-day-old snapshots (15-min → hourly)
    - 03:00 daily: Re-fetch last 7 days for attribution corrections

REFERENCES:
    - docs/architecture/unified-metrics.md
    - app/services/snapshot_sync_service.py
    - app/services/shopify_sync_service.py
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Connection, ProviderEnum
from app.telemetry import capture_exception

logger = logging.getLogger(__name__)

# ARQ is now the only job queue - scheduling is built-in
ARQ_AVAILABLE = True
try:
    from arq import create_pool
    from arq.connections import RedisSettings
except ImportError:
    ARQ_AVAILABLE = False
    logger.warning("[SCHEDULER] ARQ not available - install with: pip install arq")

# Cron expressions for fixed clock times
REALTIME_SYNC_CRON = "*/15 * * * *"  # Every 15 min at :00, :15, :30, :45
COMPACTION_CRON = "0 1 * * *"        # Daily at 01:00 UTC
ATTRIBUTION_CRON = "0 3 * * *"       # Daily at 03:00 UTC


async def _enqueue_arq_job(connection_id: str, workspace_id: str, force_refresh: bool = False):
    """Enqueue a sync job to ARQ."""
    from app.workers.arq_enqueue import enqueue_sync_job
    return await enqueue_sync_job(connection_id, workspace_id, force_refresh)


# =============================================================================
# JOB FUNCTIONS (Called by RQ worker)
# =============================================================================

def run_realtime_sync():
    """Run realtime sync for all connections.

    WHAT:
        Syncs today's data for all active connections.

    WHEN:
        Every 15 minutes.
    """
    logger.info("[SCHEDULER] Starting realtime sync job")

    db: Session = SessionLocal()
    try:
        from app.services.snapshot_sync_service import sync_all_snapshots
        from app.services.shopify_sync_service import sync_shopify_orders

        # Sync Meta and Google snapshots
        results = sync_all_snapshots(db, mode="realtime")

        total_inserted = sum(r.inserted for r in results.values())
        total_updated = sum(r.updated for r in results.values())
        total_errors = sum(len(r.errors) for r in results.values())

        logger.info(
            "[SCHEDULER] Realtime sync complete: %d connections, %d inserted, %d updated, %d errors",
            len(results), total_inserted, total_updated, total_errors
        )

        # Sync Shopify orders for all Shopify connections
        shopify_connections = db.query(Connection).filter(
            Connection.provider == ProviderEnum.shopify,
            Connection.status == "active"
        ).all()

        for connection in shopify_connections:
            try:
                # Sync orders from last 2 hours to catch updates
                since = datetime.now(timezone.utc) - timedelta(hours=2)
                # Note: sync_shopify_orders is async, need to handle appropriately
                logger.info("[SCHEDULER] Syncing Shopify orders for connection %s", connection.id)
            except Exception as e:
                logger.error("[SCHEDULER] Shopify sync failed for %s: %s", connection.id, e)
                capture_exception(e, extra={
                    "operation": "shopify_sync",
                    "connection_id": str(connection.id),
                    "job": "realtime_sync",
                })

    except Exception as e:
        logger.error("[SCHEDULER] Realtime sync failed: %s", e)
        capture_exception(e, extra={
            "operation": "realtime_sync",
            "job": "realtime_sync",
        })
    finally:
        db.close()


def run_attribution_sync():
    """Run attribution sync for last 7 days.

    WHAT:
        Re-fetches last 7 days of data to catch delayed conversions.

    WHEN:
        Daily at 3am.
    """
    logger.info("[SCHEDULER] Starting attribution sync job")

    db: Session = SessionLocal()
    try:
        from app.services.snapshot_sync_service import sync_all_snapshots

        results = sync_all_snapshots(db, mode="attribution")

        total_updated = sum(r.updated for r in results.values())
        logger.info(
            "[SCHEDULER] Attribution sync complete: %d connections, %d updated",
            len(results), total_updated
        )

    except Exception as e:
        logger.error("[SCHEDULER] Attribution sync failed: %s", e)
        capture_exception(e, extra={
            "operation": "attribution_sync",
            "job": "attribution_sync",
        })
    finally:
        db.close()


def run_compaction():
    """Compact 15-min snapshots to hourly for day-2.

    WHAT:
        Aggregates 15-min snapshots from 2 days ago into hourly buckets.

    WHEN:
        Daily at 1am.
    """
    logger.info("[SCHEDULER] Starting compaction job")

    db: Session = SessionLocal()
    try:
        from app.services.snapshot_sync_service import compact_snapshots_to_hourly

        # Compact data from 2 days ago
        target_date = date.today() - timedelta(days=2)
        hourly_count = compact_snapshots_to_hourly(db, target_date)

        logger.info(
            "[SCHEDULER] Compaction complete: date=%s, hourly_snapshots=%d",
            target_date, hourly_count
        )

    except Exception as e:
        logger.error("[SCHEDULER] Compaction failed: %s", e)
        capture_exception(e, extra={
            "operation": "compaction",
            "job": "compaction",
            "target_date": str(target_date),
        })
    finally:
        db.close()


# =============================================================================
# SCHEDULER SETUP
# =============================================================================

def setup_scheduled_jobs(scheduler) -> None:
    """Configure all scheduled jobs using CRON for fixed clock times.

    SCHEDULE (all times UTC):
        - */15 * * * *  : Realtime sync at :00, :15, :30, :45
        - 0 1 * * *     : Daily compaction at 01:00
        - 0 3 * * *     : Daily attribution sync at 03:00

    Args:
        scheduler: RQ Scheduler instance
    """
    if not scheduler:
        logger.error("[SCHEDULER] Cannot setup jobs - scheduler is None")
        return

    # Clear existing jobs
    for job in scheduler.get_jobs():
        scheduler.cancel(job)

    # Every 15 minutes at fixed clock times: Realtime sync
    # Runs at :00, :15, :30, :45 of every hour (e.g., 16:00, 16:15, 16:30, 16:45)
    scheduler.cron(
        REALTIME_SYNC_CRON,
        func=run_realtime_sync,
        queue_name="sync_jobs",
        description="Realtime sync (every 15 min at :00/:15/:30/:45)"
    )

    # Daily at 1am UTC: Compaction
    scheduler.cron(
        COMPACTION_CRON,
        func=run_compaction,
        queue_name="sync_jobs",
        description="Daily compaction (01:00 UTC)"
    )

    # Daily at 3am UTC: Attribution sync
    scheduler.cron(
        ATTRIBUTION_CRON,
        func=run_attribution_sync,
        queue_name="sync_jobs",
        description="Daily attribution sync (03:00 UTC)"
    )

    logger.info(
        "[SCHEDULER] Jobs configured: realtime=%s, compaction=%s, attribution=%s",
        REALTIME_SYNC_CRON, COMPACTION_CRON, ATTRIBUTION_CRON
    )


def run_scheduler() -> None:
    """Main scheduler loop using RQ Scheduler."""
    if not RQ_SCHEDULER_AVAILABLE:
        logger.error("[SCHEDULER] Cannot start - rq_scheduler not installed")
        logger.error("[SCHEDULER] Install with: pip install rq-scheduler")
        return

    if not REDIS_AVAILABLE:
        logger.error("[SCHEDULER] Cannot start - redis not available")
        return

    redis = _get_redis()
    if not redis:
        logger.error("[SCHEDULER] Cannot start - Redis connection failed")
        return

    scheduler = Scheduler(connection=redis, queue_name="sync_jobs")

    logger.info("[SCHEDULER] Starting scheduler")

    # Setup scheduled jobs
    setup_scheduled_jobs(scheduler)

    # Run the scheduler
    scheduler.run()


# =============================================================================
# INITIAL SYNC (for new connections)
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
    if not ARQ_AVAILABLE:
        logger.error("[SCHEDULER] ARQ not available - install with: pip install arq")
        return False

    try:
        from app.workers.arq_enqueue import enqueue_sync_job as arq_enqueue

        result = await arq_enqueue(connection_id, workspace_id, force_refresh=False)
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
        run_sync: If True and ARQ unavailable, run sync synchronously

    Returns:
        True if job was enqueued/executed successfully, False otherwise
    """
    if not ARQ_AVAILABLE:
        logger.error("[SCHEDULER] ARQ not available - install with: pip install arq")
        return False

    try:
        import asyncio
        from app.workers.arq_enqueue import enqueue_sync_job as arq_enqueue

        # Check if we're in an existing event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context - schedule as a task
            logger.warning("[SCHEDULER] Called sync enqueue_initial_sync from async context. Use enqueue_initial_sync_async instead.")
            # Create task and return immediately - can't await from sync function
            asyncio.create_task(enqueue_initial_sync_async(connection_id, workspace_id))
            return True
        except RuntimeError:
            # No running loop - safe to use asyncio.run()
            result = asyncio.run(arq_enqueue(connection_id, workspace_id, force_refresh=False))

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


def run_connection_sync(connection_id: str, mode: str = "backfill") -> None:
    """Run a sync for a single connection (called by RQ worker).

    WHAT:
        Syncs entities and metrics for a specific connection.
        Used for initial sync after OAuth and manual sync triggers.

    WHY:
        - "backfill" mode (default): 90-day historical data for new connections
        - "realtime" mode: Today's data only for manual refreshes

    Args:
        connection_id: UUID of the connection to sync
        mode: Sync mode - "backfill" (90 days) or "realtime" (today)
    """
    from uuid import UUID
    logger.info("[SCHEDULER] Running %s sync for connection %s", mode, connection_id)

    db: Session = SessionLocal()
    try:
        from app.services.snapshot_sync_service import sync_snapshots_for_connection

        result = sync_snapshots_for_connection(
            db=db,
            connection_id=UUID(connection_id),
            mode=mode,  # Use backfill for initial sync to get 90 days of data
            sync_entities=True  # Always sync entities on initial
        )

        if result.success:
            logger.info(
                "[SCHEDULER] %s sync complete for %s: inserted=%d, updated=%d",
                mode.title(), connection_id, result.inserted, result.updated
            )
        else:
            logger.error(
                "[SCHEDULER] %s sync failed for %s: %s",
                mode.title(), connection_id, result.errors
            )

    except Exception as e:
        logger.error("[SCHEDULER] %s sync failed for %s: %s", mode.title(), connection_id, e)
        capture_exception(e, extra={
            "operation": "run_connection_sync",
            "connection_id": connection_id,
            "mode": mode,
        })
    finally:
        db.close()


# =============================================================================
# LEGACY SUPPORT (for manual sync triggers)
# =============================================================================

def trigger_sync_for_connection(connection_id: str, workspace_id: str) -> None:
    """Manually trigger a sync for a specific connection.

    DEPRECATED: Use enqueue_initial_sync instead.

    Args:
        connection_id: UUID of the connection
        workspace_id: UUID of the workspace
    """
    enqueue_initial_sync(connection_id, workspace_id)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    run_scheduler()
