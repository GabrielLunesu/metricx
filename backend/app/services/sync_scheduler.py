"""Sync scheduler service.

WHAT:
    Periodically scans connections table and enqueues sync jobs via RQ.

WHY:
    - Supports configurable sync frequencies per connection
    - Centralizes rate-limit enforcement before hitting provider APIs

REFERENCES:
    - docs/living-docs/REALTIME_SYNC_STATUS.md
    - app/workers/sync_worker.py
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Dict, Optional

from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Connection

logger = logging.getLogger(__name__)

SYNC_INTERVALS: Dict[str, Optional[int]] = {
    "manual": None,
    # "realtime": 30,       # seconds (requires special access per docs/REALTIME_SYNC_IMPLEMENTATION_SUMMARY.md)
    "5min": 5 * 60,
    "10min": 10 * 60,
    "30min": 30 * 60,
    "hourly": 60 * 60,
    "daily": 24 * 60 * 60,
}


def _should_sync(connection: Connection, redis: Redis) -> bool:
    """Determine whether connection should be enqueued.
    
    WHAT:
        Checks if connection needs syncing based on frequency and rate limits.
    
    WHY:
        - Respects user-configured sync frequency
        - Prevents rate limit violations (Meta: 200 calls/hour)
        - Implements cooldown when errors detected
    
    RETURNS:
        True if should sync, False if should skip
    """
    interval = SYNC_INTERVALS.get(connection.sync_frequency)
    if not interval:
        return False

    # Check if in cooldown (rate limit or error)
    cooldown_key = f"sync_cooldown:{connection.id}"
    if redis.exists(cooldown_key):
        ttl = redis.ttl(cooldown_key)
        logger.debug(
            "[SCHEDULER] Connection %s in cooldown for %s more seconds",
            connection.id,
            ttl
        )
        return False

    # Check if last sync had rate limit error
    if connection.last_sync_error and "rate limit" in connection.last_sync_error.lower():
        # Set 15-minute cooldown
        redis.setex(cooldown_key, 900, "rate_limit")  # 15 minutes
        logger.warning(
            "[SCHEDULER] Rate limit detected for %s, cooldown for 15 minutes",
            connection.id
        )
        return False

    if not connection.last_sync_attempted_at:
        return True

    elapsed = (datetime.utcnow() - connection.last_sync_attempted_at).total_seconds()
    return elapsed >= interval


def run_scheduler() -> None:
    """Main scheduler loop."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis = Redis.from_url(redis_url)
    queue = Queue("sync_jobs", connection=redis)

    logger.info("[SCHEDULER] Starting scheduler (redis=%s)", redis_url)

    while True:
        try:
            db: Session = SessionLocal()

            active_connections = (
                db.query(Connection)
                .filter(Connection.status == "active")
                .all()
            )

            for connection in active_connections:
                if _should_sync(connection, redis):
                    queue.enqueue(
                        "app.workers.sync_worker.process_sync_job",
                        str(connection.id),
                        str(connection.workspace_id),
                    )
                    logger.info(
                        "[SCHEDULER] Enqueued sync job for %s (%s)",
                        connection.id,
                        connection.provider,
                    )

            db.close()
            time.sleep(30)
        except Exception as exc:  # pragma: no cover
            logger.exception("[SCHEDULER] Unexpected error: %s", exc)
            time.sleep(30)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_scheduler()
