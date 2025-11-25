"""RQ worker runner.

Usage:
    cd backend && python -m app.workers.start_worker
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from redis import Redis
from rq import Queue
from rq.worker import SimpleWorker

# Load .env file from backend directory
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis = Redis.from_url(redis_url)

    # Listen on both queues: qa_jobs (QA questions) and sync_jobs (data sync)
    qa_queue = Queue("qa_jobs", connection=redis)
    sync_queue = Queue("sync_jobs", connection=redis)

    # Use SimpleWorker to avoid macOS fork() issues
    worker = SimpleWorker([qa_queue, sync_queue], connection=redis)
    print(f"[WORKER] Starting SimpleWorker (queues=qa_jobs,sync_jobs, redis={redis_url})")
    worker.work()


if __name__ == "__main__":
    main()

