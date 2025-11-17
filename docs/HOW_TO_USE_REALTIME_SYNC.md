# How to Use Near-Realtime Sync

**Quick Reference Guide**

---

## For Users (UI)

### Setting Up Automated Sync

1. Go to **Settings** page (`/settings`)
2. Find your connected ad account
3. Select sync frequency from dropdown:
   - **Manual**: No automated sync (you click "Sync Now")
   - **Realtime**: Syncs every 30 seconds
   - **Every 30 min**: Syncs every 30 minutes
   - **Hourly**: Syncs every hour
   - **Daily**: Syncs once per day

4. Click **Save**

The system will now automatically sync based on your chosen frequency.

### Triggering Manual Sync

1. Go to **Settings** page
2. Click **"Sync Now"** button next to your connection
3. Job is enqueued instantly (you don't have to wait)
4. Check sync status to see when it completes

### Viewing Sync Status

On the Settings page, each connection shows:
- **Current frequency**: e.g., "Realtime (every 30s)"
- **Sync status**: "Idle", "Syncing", or "Error"
- **Last attempted**: "2 min ago"
- **Last completed**: "2 min ago"
- **Last change**: "15 min ago" (when data actually changed)
- **Stats**: "45 attempts | 12 changes (26.7%)"

---

## For Developers (API)

### Enqueue Sync Job

```bash
POST /connections/{connection_id}/sync-now

# Returns immediately:
{
  "job_id": "abc-123-def",
  "status": "queued"
}
```

### Update Sync Frequency

```bash
PATCH /connections/{connection_id}/sync-frequency
Content-Type: application/json

{
  "sync_frequency": "realtime"  # or: manual, 30min, hourly, daily
}

# Returns:
{
  "sync_frequency": "realtime",
  "sync_status": "idle",
  "last_sync_attempted_at": null,
  ...
}
```

### Get Sync Status

```bash
GET /connections/{connection_id}/sync-status

# Returns:
{
  "sync_frequency": "realtime",
  "sync_status": "idle",
  "last_sync_attempted_at": "2025-11-14T13:10:58",
  "last_sync_completed_at": "2025-11-14T13:11:01",
  "last_metrics_changed_at": "2025-11-14T12:45:00",
  "total_syncs_attempted": 45,
  "total_syncs_with_changes": 12,
  "last_sync_error": null
}
```

---

## For DevOps (Deployment)

### Production Deployment

```bash
# Deploy all services (backend, worker, scheduler, frontend)
defang compose up

# Verify services are running
defang ps

# Should see:
# - backend (FastAPI API)
# - worker (RQ worker)
# - scheduler (Sync scheduler)
# - frontend (Next.js UI)
```

### Monitoring

```bash
# Check worker logs
defang logs worker -f

# Check scheduler logs
defang logs scheduler -f

# Check backend logs
defang logs backend -f
```

### Troubleshooting

**If jobs aren't processing:**
```bash
# Check worker is running
defang ps | grep worker

# Check Redis queue
# (requires Redis CLI access)
redis-cli -u $REDIS_URL LLEN rq:queue:sync_jobs
```

**If scheduler isn't enqueueing:**
```bash
# Check scheduler logs
defang logs scheduler --tail 100

# Verify connections have frequency != "manual"
# Check database: SELECT sync_frequency FROM connections;
```

**If sync fails:**
```bash
# Check last_sync_error field
GET /connections/{id}/sync-status

# Check worker logs
defang logs worker --tail 100
```

---

## Architecture

### Components

```
┌─────────────┐
│   Backend   │ ← User clicks "Sync Now"
│   (API)     │ → Enqueues job to Redis
└──────┬──────┘
       │
┌──────▼──────┐
│    Redis    │ ← Job queue: sync_jobs
│  (Railway)  │ → Jobs stored here
└──────┬──────┘
       │
┌──────▼──────┐
│   Worker    │ ← Picks up jobs from queue
│   (RQ)      │ → Processes sync
└──────┬──────┘   → Updates connection status
       │
┌──────▼──────┐
│  Database   │ ← Writes metrics (if changed)
│(PostgreSQL) │ ← Updates connection tracking
└─────────────┘

Scheduler (loop every 30s)
       ↓
Checks active connections
       ↓
Enqueues jobs based on frequency
```

### Data Flow

1. **User Action or Scheduler**:
   - Manual: User clicks "Sync Now"
   - Automated: Scheduler checks if interval elapsed

2. **Job Enqueued**:
   - Added to Redis `sync_jobs` queue
   - Connection status → "queued"
   - Returns immediately (non-blocking)

3. **Worker Processes**:
   - Picks up job from Redis
   - Connection status → "syncing"
   - Fetches data from Meta/Google API
   - Compares with existing data
   - Writes ONLY if metrics changed
   - Updates connection tracking

4. **Completion**:
   - Connection status → "idle" or "error"
   - Timestamps updated
   - Counters incremented

---

## Configuration

### Sync Frequencies

| Setting | Interval | Use Case |
|---------|----------|----------|
| manual | None | Testing, low-traffic accounts |
| realtime | 30 seconds | High-spend accounts ($10k+/day) |
| 30min | 30 minutes | Medium-spend accounts ($1k-10k/day) |
| hourly | 60 minutes | Standard accounts ($100-1k/day) |
| daily | 24 hours | Low-spend accounts (<$100/day) |

### Rate Limits

- Meta Ads: 200 calls/hour (we use 180 for safety)
- Google Ads: varies (handled by SDK)

Scheduler enforces limits before enqueueing jobs.

---

## Common Tasks

### Enable Realtime Sync for High-Spend Account

```bash
curl -X PATCH http://your-api/connections/{id}/sync-frequency \
  -H "Content-Type: application/json" \
  -d '{"sync_frequency": "realtime"}' \
  --cookie "access_token=..."
```

### Manually Trigger Sync

```bash
curl -X POST http://your-api/connections/{id}/sync-now \
  --cookie "access_token=..."
```

### Check If Data Is Fresh

```bash
curl http://your-api/connections/{id}/sync-status \
  --cookie "access_token=..." | jq '.last_metrics_changed_at'
```

### Pause Automated Sync

```bash
curl -X PATCH http://your-api/connections/{id}/sync-frequency \
  -H "Content-Type: application/json" \
  -d '{"sync_frequency": "manual"}' \
  --cookie "access_token=..."
```

---

## FAQ

**Q: How do I know if data is fresh?**  
A: Check `last_metrics_changed_at` timestamp. This shows when metrics actually changed, not just when we checked.

**Q: Why does it show 0 changes?**  
A: If metrics haven't changed since last sync, we skip writing to save DB resources. This is normal.

**Q: Can I change frequency while syncing?**  
A: Yes! Update takes effect immediately. Current job will complete first.

**Q: What happens if sync fails?**  
A: Check `last_sync_error` field for details. Worker will retry on next scheduled interval.

**Q: How do I stop all automated syncs?**  
A: Set all connections to "manual" frequency, or stop the scheduler service.

---

## Migration Notes

**Updating Production Database**:

```bash
# SSH into backend container or connect to Railway DB
alembic upgrade head

# Verify migration applied
alembic current
# Should show: fe534aa60c90 (head)
```

**Existing connections** will default to "manual" frequency (no behavior change).

---

## Support

- **Implementation**: `docs/living-docs/REALTIME_SYNC_STATUS.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Summary**: `docs/REALTIME_SYNC_IMPLEMENTATION_SUMMARY.md`

