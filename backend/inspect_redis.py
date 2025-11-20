import sys
import os
from pathlib import Path
from redis import Redis
from rq import Queue, Worker

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from app.utils.env import load_env_file

# Load env
load_env_file()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
print(f"Connecting to Redis at: {redis_url}")

try:
    redis = Redis.from_url(redis_url)
    redis.ping()
    print("Connected to Redis successfully.")
    
    queue = Queue("sync_jobs", connection=redis)
    print(f"Queue 'sync_jobs' length: {len(queue)}")
    
    workers = Worker.all(connection=redis)
    print(f"Registered workers: {len(workers)}")
    
    for worker in workers:
        print(f"Worker: {worker.name}")
        print(f"  Queues: {worker.queue_names()}")
        print(f"  State: {worker.state}")
        print(f"  Last heartbeat: {worker.last_heartbeat}")
        print(f"  Current job: {worker.get_current_job_id()}")
        
except Exception as e:
    print(f"Error: {e}")
