#!/usr/bin/env python3
"""Start ARQ worker for all background jobs.

WHAT:
    Single worker that handles ALL background jobs:
    - Sync jobs (Google, Meta, Shopify)
    - Scheduled 15-minute syncs (built-in cron)
    - Any future background tasks

WHY:
    - ARQ is async-native with parallel operations
    - Built-in cron scheduling (no separate scheduler process)
    - Single process instead of multiple (RQ + rq-scheduler)

USAGE:
    # From backend directory:
    python -m app.workers.start_worker

    # Or directly with arq:
    arq app.workers.arq_worker.WorkerSettings

PRODUCTION:
    # Use process manager like supervisord or systemd
    # Example supervisord config:
    #
    # [program:arq-worker]
    # command=arq app.workers.arq_worker.WorkerSettings
    # directory=/app/backend
    # autostart=true
    # autorestart=true
    # stdout_logfile=/var/log/arq-worker.log
"""

import logging
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main():
    """Start the ARQ worker."""
    try:
        from arq import run_worker
        from app.workers.arq_worker import WorkerSettings

        logger.info("=" * 60)
        logger.info("Starting ARQ Worker")
        logger.info("=" * 60)
        logger.info("Handles: Sync jobs, Scheduled syncs (cron)")
        logger.info("Queue: arq:queue")
        logger.info("Cron: Every 15 min (:00, :15, :30, :45)")
        logger.info("=" * 60)

        run_worker(WorkerSettings)

    except ImportError as e:
        logger.error("Failed to import ARQ. Install with: pip install arq")
        logger.error("Error: %s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Worker failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
