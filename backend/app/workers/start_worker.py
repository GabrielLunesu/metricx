"""RQ worker runner.

Usage:
    cd backend && python -m app.workers.start_worker

Options (via environment variables):
    CLEAR_STALE_JOBS=1  - Clear stale jobs older than STALE_JOB_AGE_SECONDS on startup
    STALE_JOB_AGE_SECONDS=300 - Jobs older than this (default 5 min) are considered stale
"""

from __future__ import annotations

import os
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.worker import SimpleWorker

# Configure logging BEFORE importing app modules
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    datefmt='%H:%M:%S',
    stream=sys.stdout,
    force=True  # Override any existing config
)

logger = logging.getLogger(__name__)

# Load .env file from backend directory
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)


def clear_stale_jobs(queue: Queue, max_age_seconds: int = 300) -> int:
    """
    Clear stale jobs from the queue that are older than max_age_seconds.

    This prevents the flood of old jobs when worker restarts after being down.

    Args:
        queue: RQ queue to clear stale jobs from
        max_age_seconds: Jobs older than this (in seconds) will be removed

    Returns:
        Number of jobs cleared
    """
    cleared = 0
    now = time.time()

    # Get all job IDs in the queue
    job_ids = queue.job_ids

    for job_id in job_ids:
        try:
            job = Job.fetch(job_id, connection=queue.connection)

            # Check job age based on enqueue time
            if job.enqueued_at:
                job_age = now - job.enqueued_at.timestamp()
                if job_age > max_age_seconds:
                    # Cancel the job
                    job.cancel()
                    job.delete()
                    cleared += 1
                    logger.info(f"[WORKER] Cleared stale job {job_id} (age: {job_age:.0f}s)")
        except Exception as e:
            # Job might have been deleted already
            logger.debug(f"[WORKER] Could not check job {job_id}: {e}")

    return cleared


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis = Redis.from_url(redis_url)

    # Listen on both queues: qa_jobs (QA questions) and sync_jobs (data sync)
    qa_queue = Queue("qa_jobs", connection=redis)
    sync_queue = Queue("sync_jobs", connection=redis)

    # Optionally clear stale jobs on startup
    clear_stale = os.getenv("CLEAR_STALE_JOBS", "1") == "1"
    stale_age = int(os.getenv("STALE_JOB_AGE_SECONDS", "300"))

    if clear_stale:
        logger.info(f"[WORKER] Checking for stale jobs (older than {stale_age}s)...")
        qa_cleared = clear_stale_jobs(qa_queue, stale_age)
        sync_cleared = clear_stale_jobs(sync_queue, stale_age)
        if qa_cleared or sync_cleared:
            logger.info(f"[WORKER] Cleared {qa_cleared} stale QA jobs, {sync_cleared} stale sync jobs")
        else:
            logger.info("[WORKER] No stale jobs found")

    # Log queue sizes
    logger.info(f"[WORKER] Queue sizes: qa_jobs={len(qa_queue)}, sync_jobs={len(sync_queue)}")

    # Use SimpleWorker to avoid macOS fork() issues
    worker = SimpleWorker([qa_queue, sync_queue], connection=redis)
    print(f"[WORKER] Starting SimpleWorker (queues=qa_jobs,sync_jobs, redis={redis_url})")
    worker.work()


if __name__ == "__main__":
    main()

