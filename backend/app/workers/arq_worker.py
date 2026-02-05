"""ARQ async worker - unified background job processor.

WHAT:
    Single async worker for all background jobs using ARQ.
    Delegates to snapshot_sync_service for all metric syncing.

WHY:
    - Single source of truth: snapshot_sync_service handles all sync logic
    - ARQ provides async job processing with built-in cron scheduling
    - Parallel connection syncing for maximum throughput
    - Clean separation: worker handles orchestration, service handles logic

ARCHITECTURE:
    ┌─────────────────┐      delegates to      ┌───────────────────────┐
    │  arq_worker.py  │───────────────────────▶│ snapshot_sync_service │
    │  (orchestrator) │                        │   (sync logic)        │
    └─────────────────┘                        └───────────────────────┘
                                                        │
                                                        ▼
                                               ┌────────────────┐
                                               │ MetricSnapshot │
                                               └────────────────┘

USAGE:
    # Start worker
    arq app.workers.arq_worker.WorkerSettings

    # Or use the start script
    python -m app.workers.start_arq_worker

REFERENCES:
    - https://arq-docs.helpmanual.io/
    - app/services/snapshot_sync_service.py
    - app/services/sync_scheduler.py
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, date, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from arq import cron
from arq.connections import RedisSettings

from app.database import SessionLocal
from app.models import Connection, ProviderEnum
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

    logger.info(f"[ARQ] Redis: host={host}, port={port}, ssl={use_ssl}, db={database}")

    return RedisSettings(
        host=host,
        port=port,
        password=password,
        database=database,
        ssl=use_ssl,
        ssl_cert_reqs='none' if use_ssl else None,
        # Connection stability settings for Upstash/cloud Redis
        conn_timeout=30,        # Connection timeout (seconds)
        conn_retries=5,         # Retry connection attempts
        conn_retry_delay=1,     # Delay between retries (seconds)
    )


# =============================================================================
# SYNC JOB - Delegates to snapshot_sync_service
# =============================================================================

async def process_sync_job(
    ctx: Dict,
    connection_id: str,
    workspace_id: str,
    force_refresh: bool = False,
    backfill: bool = False
) -> Dict:
    """Process a single connection sync job.

    WHAT:
        Syncs entities and metrics for one connection to MetricSnapshot table.

    WHY:
        Individual connection jobs allow parallel processing across connections.
        Delegates all sync logic to snapshot_sync_service for single source of truth.

    Args:
        ctx: ARQ context
        connection_id: Connection UUID string
        workspace_id: Workspace UUID string
        force_refresh: If True, use attribution mode (last 7 days)
        backfill: If True, use backfill mode (90 days for new connections)

    Returns:
        Dict with success status and sync results
    """
    logger.info("[ARQ] Starting sync job for connection %s (backfill=%s)", connection_id, backfill)

    db = SessionLocal()
    try:
        # Validate connection exists and has valid tokens
        connection = db.query(Connection).filter(
            Connection.id == UUID(connection_id),
            Connection.workspace_id == UUID(workspace_id),
        ).first()

        if not connection:
            return {"success": False, "error": "Connection not found"}

        # Token validation
        validation_error = _validate_connection_tokens(connection)
        if validation_error:
            connection.sync_status = "error"
            connection.last_sync_error = validation_error
            db.commit()
            return {"success": False, "error": validation_error}

        # Update status to syncing
        connection.last_sync_attempted_at = datetime.now(timezone.utc)
        connection.sync_status = "syncing"
        connection.total_syncs_attempted += 1
        connection.last_sync_error = None
        db.commit()

        # Delegate to snapshot_sync_service (run in thread pool for sync code)
        from app.services.snapshot_sync_service import sync_snapshots_for_connection

        # Determine sync mode:
        # - backfill: 90 days (for new connections)
        # - attribution: 7 days (force refresh)
        # - realtime: today only (regular 15-min sync)
        if backfill:
            mode = "backfill"
        elif force_refresh:
            mode = "attribution"
        else:
            mode = "realtime"

        logger.info("[ARQ] Using sync mode '%s' for connection %s", mode, connection_id)

        result = await asyncio.to_thread(
            sync_snapshots_for_connection,
            db,
            UUID(connection_id),
            mode=mode,
            sync_entities=True
        )

        # Update connection status based on result
        if result.success:
            connection.last_sync_completed_at = datetime.now(timezone.utc)
            connection.sync_status = "idle"
            connection.last_sync_error = None
            db.commit()

            logger.info(
                "[ARQ] Sync complete for %s: inserted=%d, updated=%d, skipped=%d",
                connection_id, result.inserted, result.updated, result.skipped
            )
            return {
                "success": True,
                "inserted": result.inserted,
                "updated": result.updated,
                "skipped": result.skipped,
            }
        else:
            connection.sync_status = "error"
            connection.last_sync_error = "; ".join(result.errors[:3])
            db.commit()

            logger.error("[ARQ] Sync failed for %s: %s", connection_id, result.errors)
            return {"success": False, "errors": result.errors}

    except Exception as e:
        logger.exception("[ARQ] Sync job failed for %s: %s", connection_id, e)
        capture_exception(e, extra={
            "operation": "process_sync_job",
            "connection_id": connection_id,
            "workspace_id": workspace_id,
        })

        try:
            connection = db.query(Connection).filter(
                Connection.id == UUID(connection_id)
            ).first()
            if connection:
                connection.sync_status = "error"
                connection.last_sync_error = str(e)[:500]
                db.commit()
        except Exception:
            pass

        return {"success": False, "error": str(e)}
    finally:
        db.close()


def _validate_connection_tokens(connection: Connection) -> Optional[str]:
    """Validate connection has required tokens.

    Returns:
        Error message if invalid, None if valid
    """
    if not connection.token:
        return "No token configured. Please reconnect."

    if connection.provider == ProviderEnum.google:
        if not connection.token.refresh_token_enc:
            return "Missing refresh token. Please reconnect Google Ads."

    elif connection.provider == ProviderEnum.meta:
        if not connection.token.access_token_enc:
            return "Missing access token. Please reconnect Meta Ads."

    elif connection.provider == ProviderEnum.shopify:
        if not connection.token.access_token_enc:
            return "Missing access token. Please reconnect Shopify."

    return None


# =============================================================================
# SCHEDULED JOBS - 15-min realtime, daily attribution, daily compaction
# =============================================================================

async def scheduled_realtime_sync(ctx: Dict) -> Dict:
    """Scheduled job: sync today's data for all connections.

    WHAT:
        Enqueues sync jobs for ALL active connections in PARALLEL.
        Each connection syncs today's cumulative metrics to MetricSnapshot.

    WHEN:
        Every 15 minutes at :00, :15, :30, :45.

    WHY:
        - Captures intraday spend progression for stop-loss rules
        - Enables real-time dashboard updates
        - Parallel enqueueing for maximum throughput
    """
    logger.info("[ARQ] Starting scheduled realtime sync")

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # =================================================================
        # PHASE 3: Reset stale "syncing" connections (stuck > 15 minutes)
        # =================================================================
        # WHY: Worker crashes mid-sync leave connections stuck in "syncing"
        # This auto-recovers them so they can be synced again
        stale_threshold = now - timedelta(minutes=15)
        stale_connections = db.query(Connection).filter(
            Connection.sync_status == "syncing",
            Connection.last_sync_attempted_at < stale_threshold
        ).all()

        for conn in stale_connections:
            logger.warning(
                "[ARQ] Resetting stale connection %s from 'syncing' to 'error' (stuck since %s)",
                conn.id, conn.last_sync_attempted_at
            )
            conn.sync_status = "error"
            conn.last_sync_error = "Sync timed out or worker crashed. Auto-reset."

        if stale_connections:
            db.commit()
            logger.info("[ARQ] Reset %d stale connections", len(stale_connections))

        # =================================================================
        # PHASE 2: Clear expired rate limits
        # =================================================================
        # WHY: Connections past their cooldown should be synced again
        expired_rate_limits = db.query(Connection).filter(
            Connection.rate_limited_until.isnot(None),
            Connection.rate_limited_until < now
        ).all()

        for conn in expired_rate_limits:
            logger.info("[ARQ] Clearing expired rate limit for connection %s", conn.id)
            conn.rate_limited_until = None
            conn.sync_status = "idle"

        if expired_rate_limits:
            db.commit()
            logger.info("[ARQ] Cleared %d expired rate limits", len(expired_rate_limits))

        # =================================================================
        # Get all active ad platform connections
        # =================================================================
        connections = db.query(Connection).filter(
            Connection.provider.in_([ProviderEnum.meta, ProviderEnum.google]),
            Connection.status == "active",
            Connection.sync_frequency != "manual",
        ).all()

        logger.info("[ARQ] Found %d connections to sync", len(connections))

        # Filter connections with valid tokens and not rate-limited
        valid_connections = []
        skipped_no_token = 0
        skipped_rate_limited = 0
        for conn in connections:
            # Skip rate-limited connections
            if conn.rate_limited_until and conn.rate_limited_until > now:
                skipped_rate_limited += 1
                continue

            if _validate_connection_tokens(conn) is None:
                valid_connections.append(conn)
            else:
                skipped_no_token += 1

        # Enqueue all jobs in PARALLEL using asyncio.gather
        from app.workers.arq_enqueue import enqueue_sync_job

        enqueue_tasks = [
            enqueue_sync_job(str(conn.id), str(conn.workspace_id), force_refresh=False)
            for conn in valid_connections
        ]

        results = await asyncio.gather(*enqueue_tasks, return_exceptions=True)

        # Count successes and failures
        enqueued = sum(1 for r in results if isinstance(r, dict) and r.get("job_id"))
        failed = len(results) - enqueued

        logger.info(
            "[ARQ] Realtime sync: %d enqueued, %d skipped (no token), %d skipped (rate limited), %d failed",
            enqueued, skipped_no_token, skipped_rate_limited, failed
        )

        return {
            "total_connections": len(connections),
            "enqueued": enqueued,
            "skipped_no_token": skipped_no_token,
            "skipped_rate_limited": skipped_rate_limited,
            "failed": failed,
        }

    except Exception as e:
        logger.exception("[ARQ] Scheduled realtime sync failed: %s", e)
        capture_exception(e, extra={"operation": "scheduled_realtime_sync"})
        return {"error": str(e)}
    finally:
        db.close()


async def scheduled_attribution_sync(ctx: Dict) -> Dict:
    """Scheduled job: re-fetch last 7 days for attribution corrections.

    WHAT:
        Re-syncs last 7 days of data to catch delayed conversion attribution.

    WHEN:
        Daily at 03:00 UTC.

    WHY:
        - Ad platforms update conversion data for up to 7 days after the event
        - Ensures accurate historical ROAS/CPA metrics
    """
    logger.info("[ARQ] Starting scheduled attribution sync")

    db = SessionLocal()
    try:
        from app.services.snapshot_sync_service import sync_all_snapshots

        # Run attribution sync (last 7 days) in thread pool
        results = await asyncio.to_thread(sync_all_snapshots, db, "attribution")

        total_updated = sum(r.updated for r in results.values())
        total_errors = sum(len(r.errors) for r in results.values())

        logger.info(
            "[ARQ] Attribution sync complete: %d connections, %d updated, %d errors",
            len(results), total_updated, total_errors
        )

        return {
            "connections": len(results),
            "updated": total_updated,
            "errors": total_errors,
        }

    except Exception as e:
        logger.exception("[ARQ] Attribution sync failed: %s", e)
        capture_exception(e, extra={"operation": "scheduled_attribution_sync"})
        return {"error": str(e)}
    finally:
        db.close()


async def scheduled_compaction(ctx: Dict) -> Dict:
    """Scheduled job: compact 15-min snapshots to hourly for day-2.

    WHAT:
        Aggregates 15-min snapshots from 2 days ago into hourly buckets.
        Deletes the original 15-min rows to save storage.

    WHEN:
        Daily at 01:00 UTC.

    WHY:
        - Storage efficiency: 24 rows/day instead of 96 rows/day
        - Historical data doesn't need 15-min granularity
        - Atomic operation prevents data loss
    """
    logger.info("[ARQ] Starting scheduled compaction")

    db = SessionLocal()
    try:
        from app.services.snapshot_sync_service import compact_snapshots_to_hourly

        # Compact data from 2 days ago
        target_date = date.today() - timedelta(days=2)

        hourly_count = await asyncio.to_thread(
            compact_snapshots_to_hourly, db, target_date
        )

        logger.info(
            "[ARQ] Compaction complete: date=%s, hourly_snapshots=%d",
            target_date, hourly_count
        )

        return {
            "target_date": str(target_date),
            "hourly_snapshots": hourly_count,
        }

    except Exception as e:
        logger.exception("[ARQ] Compaction failed: %s", e)
        capture_exception(e, extra={"operation": "scheduled_compaction"})
        return {"error": str(e)}
    finally:
        db.close()


# =============================================================================
# AGENT EVALUATION (Autonomous monitoring)
# =============================================================================

async def scheduled_agent_evaluation(ctx: Dict) -> Dict:
    """Scheduled job: evaluate all active agents.

    WHAT:
        Evaluates all active agents against their scoped entities.
        Executes actions when conditions are met.

    WHEN:
        Every 15 minutes at :00, :15, :30, :45 (after metric sync).

    WHY:
        - Agents need fresh data to evaluate accurately
        - Runs after metric sync to have latest data
        - 15-min cadence matches metric granularity

    REFERENCES:
        - Agent System Implementation Plan
        - backend/app/services/agents/evaluation_engine.py
    """
    logger.info("[ARQ] Starting scheduled agent evaluation")

    db = SessionLocal()
    try:
        from app.services.agents.evaluation_engine import AgentEvaluationEngine

        engine = AgentEvaluationEngine(db)
        results = await engine.evaluate_all_agents()

        logger.info(
            "[ARQ] Agent evaluation complete: agents=%d, entities=%d, triggers=%d, errors=%d",
            results.get("agents_evaluated", 0),
            results.get("entities_evaluated", 0),
            results.get("triggers", 0),
            results.get("errors", 0),
        )

        return results

    except Exception as e:
        logger.exception("[ARQ] Agent evaluation failed: %s", e)
        capture_exception(e, extra={"operation": "scheduled_agent_evaluation"})
        return {"error": str(e)}
    finally:
        db.close()


async def scheduled_agent_check(ctx: Dict) -> Dict:
    """Scheduled job: check and run scheduled agents.

    WHAT:
        Checks all scheduled agents (daily, weekly, monthly) and runs those
        whose schedule time has arrived.

    WHEN:
        Every minute - checks if any scheduled agent should run now.

    WHY:
        - Users want scheduled reports (daily at 1am, weekly summaries)
        - Separate from realtime evaluation (runs every 15 min)
        - Allows "always send" mode without condition requirement

    REFERENCES:
        - Scheduled Reports & Multi-Channel Notifications Plan
        - backend/app/services/agents/evaluation_engine.py
    """
    logger.info("[ARQ] Checking scheduled agents")

    db = SessionLocal()
    try:
        from app.services.agents.evaluation_engine import AgentEvaluationEngine

        engine = AgentEvaluationEngine(db)
        results = await engine.evaluate_scheduled_agents()

        if results.get("agents_evaluated", 0) > 0:
            logger.info(
                "[ARQ] Scheduled agent check: ran=%d, triggers=%d, errors=%d",
                results.get("agents_evaluated", 0),
                results.get("triggers", 0),
                results.get("errors", 0),
            )
        else:
            logger.debug("[ARQ] Scheduled agent check: no agents due to run")

        return results

    except Exception as e:
        logger.exception("[ARQ] Scheduled agent check failed: %s", e)
        capture_exception(e, extra={"operation": "scheduled_agent_check"})
        return {"error": str(e)}
    finally:
        db.close()


# =============================================================================
# SHOPIFY SYNC (Separate from ad platforms)
# =============================================================================

async def process_shopify_sync_job(
    ctx: Dict,
    connection_id: str,
    workspace_id: str
) -> Dict:
    """Process Shopify sync job.

    WHAT:
        Syncs Shopify products, customers, and orders.
        Separate from ad platform sync because it's a different data model.

    Args:
        ctx: ARQ context
        connection_id: Shopify connection UUID
        workspace_id: Workspace UUID

    Returns:
        Dict with sync results
    """
    logger.info("[ARQ] Starting Shopify sync for connection %s", connection_id)

    db = SessionLocal()
    try:
        from app.services.shopify_sync_service import sync_shopify_all

        result = await sync_shopify_all(
            db=db,
            workspace_id=UUID(workspace_id),
            connection_id=UUID(connection_id),
            force_full_sync=False,
        )

        logger.info(
            "[ARQ] Shopify sync complete for %s: success=%s",
            connection_id, result.success
        )

        return {
            "success": result.success,
            "products": result.stats.products_created + result.stats.products_updated,
            "customers": result.stats.customers_created + result.stats.customers_updated,
            "orders": result.stats.orders_created + result.stats.orders_updated,
            "errors": result.errors,
        }

    except Exception as e:
        logger.exception("[ARQ] Shopify sync failed for %s: %s", connection_id, e)
        capture_exception(e, extra={
            "operation": "process_shopify_sync_job",
            "connection_id": connection_id,
        })
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# =============================================================================
# WORKER LIFECYCLE
# =============================================================================

async def startup(ctx: Dict) -> None:
    """Worker startup - initialize resources and log config."""
    import platform

    logger.info("=" * 60)
    logger.info("[ARQ] Worker starting up (job processor)")
    logger.info("=" * 60)
    logger.info(f"[ARQ] Python: {platform.python_version()}")
    logger.info(f"[ARQ] Host: {platform.node()}")
    logger.info(f"[ARQ] Queue: arq:queue")
    logger.info(f"[ARQ] Max concurrent jobs: 10")
    logger.info(f"[ARQ] Job timeout: 600s (10 min)")
    logger.info("[ARQ] Note: Cron scheduling handled by scheduler service")
    logger.info("=" * 60)

    ctx['startup_time'] = datetime.now(timezone.utc)
    ctx['jobs_processed'] = 0


async def shutdown(ctx: Dict) -> None:
    """Worker shutdown - cleanup and log stats."""
    jobs = ctx.get('jobs_processed', 0)
    uptime = datetime.now(timezone.utc) - ctx.get('startup_time', datetime.now(timezone.utc))

    logger.info("=" * 60)
    logger.info("[ARQ] Worker shutting down")
    logger.info(f"[ARQ] Jobs processed: {jobs}")
    logger.info(f"[ARQ] Uptime: {uptime}")
    logger.info("=" * 60)


async def on_job_end(ctx: Dict) -> None:
    """Called after each job completes."""
    ctx['jobs_processed'] = ctx.get('jobs_processed', 0) + 1


# =============================================================================
# WORKER SETTINGS
# =============================================================================

class WorkerSettings:
    """ARQ worker configuration - processes jobs only.

    WHAT:
        Worker that processes sync jobs enqueued by the scheduler.
        Does NOT run cron jobs (that's the scheduler's responsibility).

    WHY:
        - Separation of concerns: scheduler runs cron, worker processes jobs
        - Workers can scale independently (multiple workers, one scheduler)
        - Prevents duplicate cron execution

    Production-ready settings:
    - max_jobs=10: Process up to 10 connections concurrently
    - job_timeout=600: 10 minutes per job (handles large accounts)
    - retry_jobs=True: Retry on transient failures
    - max_tries=3: Don't retry forever
    """

    # Job functions (what can be executed)
    # NOTE: scheduled_* functions are included so they can be called by the scheduler
    functions = [
        process_sync_job,
        process_shopify_sync_job,
        scheduled_realtime_sync,
        scheduled_attribution_sync,
        scheduled_compaction,
        scheduled_agent_evaluation,
        scheduled_agent_check,
    ]

    # NO cron_jobs here - the scheduler handles cron scheduling
    # This worker ONLY processes jobs from the queue
    cron_jobs = []

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown
    after_job_end = on_job_end

    # Redis connection
    redis_settings = get_redis_settings()

    # Performance settings
    max_jobs = 10                    # Concurrent jobs (10 connections at once)
    job_timeout = 600                # 10 minutes per job
    keep_result = 3600               # Keep results for 1 hour
    retry_jobs = True                # Retry failed jobs
    max_tries = 3                    # Max 3 attempts
    health_check_interval = 30       # Health check every 30s

    # Queue name
    queue_name = "arq:queue"
