#!/usr/bin/env python3
"""Start ARQ worker for async sync jobs.

USAGE:
    python -m app.workers.start_arq_worker

    Or directly:
    arq app.workers.arq_worker.WorkerSettings
"""

import asyncio
import logging
import sys

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

        logger.info("Starting ARQ worker...")
        run_worker(WorkerSettings)
    except ImportError as e:
        logger.error("Failed to import ARQ. Install with: pip install arq")
        logger.error("Error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
