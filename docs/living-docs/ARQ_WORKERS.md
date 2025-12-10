# ARQ Workers - Background Job Processing

**Last Updated**: 2025-12-10
**Version**: 1.0.0
**Status**: Production

---

## Overview

metricx uses **ARQ** (Async Redis Queue) for background job processing. ARQ handles:

- **15-minute metric syncs** - Real-time ad data from Meta/Google
- **Daily attribution syncs** - Re-fetch last 7 days for conversion corrections
- **Snapshot compaction** - Compress old 15-min data to hourly
- **Shopify syncs** - Products, customers, orders

### Why ARQ?

| Feature | RQ (Previous) | ARQ |
|---------|---------------|-----|
| Async native | No | Yes |
| Cron scheduling | External | Built-in |
| Connection pool | Per-job | Shared |
| macOS support | Fork issues | Works |
| Redis SSL | Limited | Full support |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ARQ WORKER ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│   Scheduler     │          │   Redis Queue   │          │    Worker(s)    │
│   (1 process)   │─────────▶│   (arq:queue)   │─────────▶│  (N processes)  │
│                 │          │                 │          │                 │
│ • Cron triggers │          │ • Job storage   │          │ • Job execution │
│ • Enqueues jobs │          │ • Result cache  │          │ • Platform APIs │
│                 │          │                 │          │ • DB writes     │
└─────────────────┘          └─────────────────┘          └─────────────────┘
        │                                                          │
        │                                                          │
        │                    ┌─────────────────┐                   │
        └───────────────────▶│   PostgreSQL    │◀──────────────────┘
                             │                 │
                             │ • MetricSnapshot│
                             │ • Entities      │
                             │ • Connections   │
                             └─────────────────┘

SEPARATION OF CONCERNS:
───────────────────────
• Scheduler: Runs cron jobs, enqueues work (single instance)
• Worker: Processes jobs from queue (can scale horizontally)
• This prevents duplicate cron execution when scaling workers
```

---

## Job Types

### 1. process_sync_job

**Purpose:** Sync metrics for a single ad platform connection

**Triggered by:**
- Scheduler (every 15 minutes)
- Manual trigger from UI
- New connection backfill

**Modes:**
| Mode | Days | Use Case |
|------|------|----------|
| `realtime` | Today only | Regular 15-min sync |
| `attribution` | Last 7 days | Daily re-fetch for conversion corrections |
| `backfill` | Last 90 days | New connection initial sync |

**Flow:**
```python
async def process_sync_job(ctx, connection_id, workspace_id, force_refresh, backfill):
    # 1. Validate connection exists and has valid tokens
    # 2. Update connection status to "syncing"
    # 3. Sync entities (campaign/adset/ad status changes)
    # 4. Sync metrics via snapshot_sync_service
    # 5. Update connection status to "idle" or "error"
```

### 2. scheduled_realtime_sync

**Purpose:** Enqueue sync jobs for ALL active connections

**Schedule:** Every 15 minutes (:00, :15, :30, :45)

**Flow:**
```python
async def scheduled_realtime_sync(ctx):
    # 1. Query all active Meta/Google connections
    # 2. Filter connections with valid tokens
    # 3. Enqueue jobs in PARALLEL using asyncio.gather
    # 4. Return stats (enqueued, skipped, failed)
```

### 3. scheduled_attribution_sync

**Purpose:** Re-fetch last 7 days to catch delayed conversions

**Schedule:** Daily at 03:00 UTC

**Why:** Ad platforms update conversion data for up to 7 days after the event (view-through, cross-device attribution)

### 4. scheduled_compaction

**Purpose:** Compress 15-min snapshots to hourly for day-2+

**Schedule:** Daily at 01:00 UTC

**Why:** Storage efficiency - 24 rows/day instead of 96 rows/day

### 5. process_shopify_sync_job

**Purpose:** Sync Shopify products, customers, orders

**Triggered by:** Manual or scheduled

---

## File Structure

```
backend/app/workers/
├── arq_worker.py       # Job definitions + WorkerSettings
├── arq_enqueue.py      # Async enqueueing helper
└── start_arq_worker.py # Worker entry point

backend/app/services/
├── snapshot_sync_service.py  # Core sync logic (called by jobs)
└── sync_scheduler.py         # Cron scheduler process
```

---

## Running Locally

### Start Worker (job processor)

```bash
cd backend

# Option 1: Direct ARQ command
arq app.workers.arq_worker.WorkerSettings

# Option 2: Python module
python -m app.workers.start_arq_worker
```

**Expected output:**
```
[ARQ] Worker starting up (job processor)
[ARQ] Python: 3.11.x
[ARQ] Queue: arq:queue
[ARQ] Max concurrent jobs: 10
[ARQ] Job timeout: 600s (10 min)
*** Listening on arq:queue...
```

### Start Scheduler (cron triggers)

```bash
cd backend
python -m app.services.sync_scheduler
```

**Expected output:**
```
[SCHEDULER] Starting ARQ scheduler...
[SCHEDULER] Cron jobs:
  - realtime_sync: */15 * * * * (every 15 min)
  - attribution_sync: 0 3 * * * (daily 3am)
  - compaction: 0 1 * * * (daily 1am)
```

### Manual Job Enqueueing

```python
from app.workers.arq_enqueue import enqueue_sync_job

# Enqueue a sync job
await enqueue_sync_job(
    connection_id="uuid-here",
    workspace_id="uuid-here",
    force_refresh=False,  # True for attribution mode
    backfill=False,       # True for 90-day initial sync
)
```

---

## Configuration

### Worker Settings

```python
# backend/app/workers/arq_worker.py

class WorkerSettings:
    functions = [
        process_sync_job,
        process_shopify_sync_job,
        scheduled_realtime_sync,
        scheduled_attribution_sync,
        scheduled_compaction,
    ]

    cron_jobs = []  # Scheduler handles cron, not worker

    redis_settings = get_redis_settings()

    max_jobs = 10           # Concurrent jobs
    job_timeout = 600       # 10 minutes per job
    keep_result = 3600      # Keep results 1 hour
    retry_jobs = True       # Retry on failure
    max_tries = 3           # Max 3 attempts
    queue_name = "arq:queue"
```

### Redis Connection

```python
def get_redis_settings() -> RedisSettings:
    """Supports redis:// and rediss:// (SSL)"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    parsed = urlparse(redis_url)

    return RedisSettings(
        host=parsed.hostname,
        port=parsed.port,
        password=parsed.password,
        database=int(parsed.path.lstrip("/")) or 0,
        ssl=parsed.scheme == "rediss",
        ssl_cert_reqs='none' if ssl else None,  # Upstash compatibility
        conn_timeout=30,
        conn_retries=5,
    )
```

---

## Scheduler vs Worker

**Critical Design Decision:** Cron scheduling is handled by a separate scheduler process, NOT by workers.

### Why?

| Scenario | Cron in Worker | Separate Scheduler |
|----------|----------------|-------------------|
| 3 workers running | Each fires cron = 3x jobs | Single scheduler = 1x jobs |
| Worker restarts | Cron timing resets | Scheduler independent |
| Horizontal scaling | Duplicate work | No duplication |

### Scheduler Implementation

```python
# backend/app/services/sync_scheduler.py

async def run_scheduler():
    """Run cron jobs and enqueue work to ARQ queue."""
    pool = await create_pool(get_redis_settings())

    while True:
        now = datetime.now(timezone.utc)

        # Every 15 minutes: realtime sync
        if now.minute % 15 == 0:
            await pool.enqueue_job("scheduled_realtime_sync")

        # Daily 3am: attribution sync
        if now.hour == 3 and now.minute == 0:
            await pool.enqueue_job("scheduled_attribution_sync")

        # Daily 1am: compaction
        if now.hour == 1 and now.minute == 0:
            await pool.enqueue_job("scheduled_compaction")

        # Sleep until next minute
        await asyncio.sleep(60 - now.second)
```

---

## Job Enqueueing API

### From FastAPI Routes

```python
# backend/app/routers/connections.py

@router.post("/{connection_id}/sync")
async def trigger_sync(connection_id: UUID, workspace_id: UUID):
    from app.workers.arq_enqueue import enqueue_sync_job

    result = await enqueue_sync_job(
        connection_id=str(connection_id),
        workspace_id=str(workspace_id),
        force_refresh=False,
        backfill=False,
    )

    return {"status": "enqueued", "job_id": result.get("job_id")}
```

### Enqueue Helper

```python
# backend/app/workers/arq_enqueue.py

_arq_pool: Optional[ArqRedis] = None

async def get_arq_pool() -> ArqRedis:
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(get_redis_settings())
    return _arq_pool

async def enqueue_sync_job(
    connection_id: str,
    workspace_id: str,
    force_refresh: bool = False,
    backfill: bool = False,
) -> dict:
    pool = await get_arq_pool()

    job = await pool.enqueue_job(
        "process_sync_job",
        connection_id,
        workspace_id,
        force_refresh,
        backfill,
        _queue_name="arq:queue",
    )

    return {"job_id": job.job_id if job else None}
```

---

## Error Handling

### Job Retries

```python
class WorkerSettings:
    retry_jobs = True
    max_tries = 3
```

Jobs are retried up to 3 times on failure with exponential backoff.

### Connection Status Tracking

```python
# On job start
connection.sync_status = "syncing"
connection.last_sync_attempted_at = now
connection.total_syncs_attempted += 1

# On success
connection.sync_status = "idle"
connection.last_sync_completed_at = now
connection.last_sync_error = None

# On failure
connection.sync_status = "error"
connection.last_sync_error = str(error)[:500]
```

### Token Validation

```python
def _validate_connection_tokens(connection: Connection) -> Optional[str]:
    """Returns error message if invalid, None if valid."""
    if not connection.token:
        return "No token configured. Please reconnect."

    if connection.provider == ProviderEnum.google:
        if not connection.token.refresh_token_enc:
            return "Missing refresh token. Please reconnect Google Ads."

    if connection.provider == ProviderEnum.meta:
        if not connection.token.access_token_enc:
            return "Missing access token. Please reconnect Meta Ads."

    return None
```

---

## Monitoring

### Job Stats

Workers track:
- Jobs processed count
- Uptime duration
- Current job status

```python
async def startup(ctx):
    ctx['startup_time'] = datetime.now(timezone.utc)
    ctx['jobs_processed'] = 0

async def on_job_end(ctx):
    ctx['jobs_processed'] += 1

async def shutdown(ctx):
    logger.info(f"Jobs processed: {ctx['jobs_processed']}")
    logger.info(f"Uptime: {datetime.now() - ctx['startup_time']}")
```

### Log Markers

| Marker | Location | Purpose |
|--------|----------|---------|
| `[ARQ]` | arq_worker.py | Job lifecycle |
| `[ARQ-ENQUEUE]` | arq_enqueue.py | Job enqueueing |
| `[SNAPSHOT_SYNC]` | snapshot_sync_service.py | Sync operations |
| `[ENTITY_SYNC]` | snapshot_sync_service.py | Entity updates |
| `[SCHEDULER]` | sync_scheduler.py | Cron scheduling |

---

## Production Deployment

### Docker Compose

```yaml
# compose.yaml

services:
  worker:
    build: ./backend
    command: arq app.workers.arq_worker.WorkerSettings
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis
      - db

  scheduler:
    build: ./backend
    command: python -m app.services.sync_scheduler
    environment:
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis
```

### Scaling

- **Workers:** Can run multiple instances (they share the queue)
- **Scheduler:** Run exactly ONE instance (prevents duplicate crons)

```bash
# Scale workers to 3
docker compose up --scale worker=3
```

---

## Troubleshooting

### Jobs Not Processing

1. **Check worker is running:**
   ```bash
   docker compose logs worker
   ```

2. **Check Redis connectivity:**
   ```python
   import redis
   r = redis.from_url(os.getenv("REDIS_URL"))
   r.ping()  # Should return True
   ```

3. **Check queue has jobs:**
   ```python
   r.llen("arq:queue")  # Should show pending jobs
   ```

### Duplicate Job Processing

**Symptom:** Same sync runs multiple times
**Cause:** Multiple schedulers running
**Fix:** Ensure only ONE scheduler process

### macOS Fork Issues

**Symptom:** `objc +[NSMutableString initialize] fork() crash`
**Cause:** macOS doesn't like fork() with certain libraries
**Fix:** ARQ uses async (no fork), but ensure no sync workers

### Redis SSL Errors

**Symptom:** Connection refused to Upstash/cloud Redis
**Fix:** Use `rediss://` URL and set `ssl_cert_reqs='none'`

---

## References

- [ARQ Documentation](https://arq-docs.helpmanual.io/)
- [Redis Queue Patterns](https://redis.io/docs/manual/patterns/distributed-locks/)
- `backend/app/workers/arq_worker.py` - Job definitions
- `backend/app/workers/arq_enqueue.py` - Enqueueing
- `backend/app/services/sync_scheduler.py` - Cron scheduler
- `backend/app/services/snapshot_sync_service.py` - Sync logic
