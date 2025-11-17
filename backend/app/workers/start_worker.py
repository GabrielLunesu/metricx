"""RQ worker runner.

Usage:
    python -m app.workers.start_worker
"""

from __future__ import annotations

import os

from redis import Redis
from rq import Worker, Queue


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis = Redis.from_url(redis_url)
    queue = Queue("sync_jobs", connection=redis)

    worker = Worker([queue], connection=redis)
    print(f"[WORKER] Starting sync worker (queue=sync_jobs, redis={redis_url})")
    worker.work()


if __name__ == "__main__":
    main()

