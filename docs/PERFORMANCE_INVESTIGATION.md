# Performance Investigation Report

**Date**: December 5, 2025
**Status**: CRITICAL - Multiple systemic issues identified
**Symptom**: Entire app slow, crashes when multiple users online

---

## Executive Summary

The app has **5 critical performance issues** causing slowness across all pages:

| Priority | Issue | Impact | Fix Effort |
|----------|-------|--------|------------|
| P0 | Missing database indexes | Full table scans on every request | Low |
| P0 | Sync SQLAlchemy in async endpoints | Blocks entire event loop | Medium |
| P1 | AI calls on every dashboard load | 3-10s per page load | Low |
| P1 | Waterfall of API calls per page | 8-10 sequential requests | Medium |
| P2 | Low memory allocation (512MB) | OOM under load | Low |

---

## Issue #1: Missing Database Indexes (P0 - CRITICAL)

### Problem
The `Entity` and `MetricFact` tables have **NO indexes** on `workspace_id`, but every query filters by it.

```python
# This query happens on EVERY request - NO INDEX = FULL TABLE SCAN
.filter(Entity.workspace_id == workspace_id)
```

### Evidence
```
backend/app/models.py:
- Entity table: No index on workspace_id (line 400)
- MetricFact table: No index on entity_id (line 449)
- MetricFact table: No index on event_date (line 453)
```

### Affected Queries (found 30+ occurrences)
- `unified_metric_service.py`: Lines 294, 315, 370, 391, 472, 679, 735
- `kpis.py`, `dashboard_kpis.py`, `entity_performance.py`
- Every workspace-scoped query

### Fix
Create Alembic migration to add indexes:

```python
# alembic/versions/xxx_add_performance_indexes.py
def upgrade():
    # Entity table
    op.create_index('ix_entities_workspace_id', 'entities', ['workspace_id'])
    op.create_index('ix_entities_workspace_level', 'entities', ['workspace_id', 'level'])
    op.create_index('ix_entities_connection_id', 'entities', ['connection_id'])

    # MetricFact table
    op.create_index('ix_metric_facts_entity_id', 'metric_facts', ['entity_id'])
    op.create_index('ix_metric_facts_event_date', 'metric_facts', ['event_date'])
    op.create_index('ix_metric_facts_entity_date', 'metric_facts', ['entity_id', 'event_date'])

    # ShopifyOrder table
    op.create_index('ix_shopify_orders_workspace_date', 'shopify_orders', ['workspace_id', 'order_created_at'])

    # Attribution table
    op.create_index('ix_attributions_workspace_id', 'attributions', ['workspace_id'])
    op.create_index('ix_attributions_workspace_date', 'attributions', ['workspace_id', 'attributed_at'])
```

---

## Issue #2: Sync SQLAlchemy Blocks Async Event Loop (P0 - CRITICAL)

### Problem
FastAPI runs async, but SQLAlchemy operations are synchronous. When one user makes a slow query, **ALL other users are blocked**.

```python
# This is why the app crashed with 2 users - blocking the event loop
async def get_dashboard_kpis(...):  # async endpoint
    db.query(Connection).filter(...)  # SYNC operation - BLOCKS EVENT LOOP
```

### Evidence
```
backend/app/deps.py:49 - get_current_user is SYNC, runs on every request
backend/app/routers/dashboard_kpis.py:341 - async def but uses sync db queries
backend/app/routers/kpis.py:90 - SYNC def (correct, but mixed patterns)
```

### Why This Causes Crashes
1. User A makes a slow query (5 seconds)
2. User B's request comes in
3. User B is blocked until User A finishes
4. With enough users, requests queue up → timeouts → crashes

### Fix Options

**Option A: Make all endpoints sync (simpler)**
```python
# Change async def to def - FastAPI will run in thread pool
def get_dashboard_kpis(...):  # NOT async
    db.query(...)  # Now runs in thread, doesn't block
```

**Option B: Use async SQLAlchemy (complex, recommended for scale)**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# database.py
engine = create_async_engine(DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'))

# In endpoints
async def get_dashboard_kpis(...):
    async with async_session() as session:
        result = await session.execute(select(Connection).filter(...))
```

**Recommendation**: Option A for immediate fix, Option B for long-term.

---

## Issue #3: AI Calls on Every Dashboard Load (P1 - HIGH)

### Problem
`AiInsightsPanel` calls Claude API twice on every dashboard load.

```javascript
// ui/app/(dashboard)/dashboard/components/AiInsightsPanel.jsx:47-54
const questions = [
    { question: `What is my biggest performance drop ${timeStr}?`, type: 'warning' },
    { question: `What is my best performing area ${timeStr}?`, type: 'opportunity' }
];
const results = await Promise.all(questions.map(q => fetchInsights({...})));
```

This hits:
```python
# backend/app/routers/qa.py:237-242
response = client.messages.create(
    model="claude-sonnet-4-20250514",  # 2-5 seconds per call
    max_tokens=512,
    ...
)
```

### Impact
- 2 Claude API calls × 2-5s each = **4-10 seconds** added to every dashboard load
- Users pay for API calls that return the same answer repeatedly

### Fix
**Add caching with TTL**:

```python
# backend/app/routers/qa.py
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def _cached_insight(workspace_id: str, question_hash: str, date_key: str):
    # Cache insights for 30 minutes per workspace + question
    ...

# Or use Redis for distributed caching
async def get_insights(...):
    cache_key = f"insight:{workspace_id}:{hash(question)}:{date.today()}"
    cached = redis.get(cache_key)
    if cached:
        return cached

    result = await _generate_insight(...)
    redis.setex(cache_key, 1800, result)  # 30 min TTL
    return result
```

**Or lazy load in frontend**:
```javascript
// Only load after 2 seconds, or on scroll
useEffect(() => {
    const timer = setTimeout(fetchAllInsights, 2000);
    return () => clearTimeout(timer);
}, []);
```

---

## Issue #4: Waterfall of API Calls Per Page (P1 - HIGH)

### Problem
Dashboard loads **9+ components that each make their own API call**.

```
Dashboard Page Load:
1. currentUser()              → /auth/me
2. fetchWorkspaceStatus()     → /workspaces/{id}/status
3. fetchDashboardKpis()       → /workspaces/{id}/dashboard/kpis
4. fetchWorkspaceKpis()       → /workspaces/{id}/kpis (MoneyPulseChart - REDUNDANT)
5. fetchInsights() x2         → /qa/insights (AI SLOW)
6. fetchAttributionSummary()  → /workspaces/{id}/attribution/summary
7. fetchAttributionFeed()     → /workspaces/{id}/attribution/feed
8. fetchEntityPerformance()   → /entity-performance (TopCreative)
9. fetchEntityPerformance()   → /entity-performance (UnitEconomicsTable)
```

Each request has overhead: DNS, TCP, TLS, HTTP headers, auth check, DB connection.

### Evidence
```javascript
// ui/app/(dashboard)/dashboard/page.jsx
// Each component independently fetches:
<KpiStrip workspaceId={...} />           // fetch 1
<MoneyPulseChart workspaceId={...} />    // fetch 2 (redundant with KpiStrip!)
<AiInsightsPanel workspaceId={...} />    // fetches 3-4 (AI calls)
<AttributionCard workspaceId={...} />    // fetch 5
<LiveAttributionFeed workspaceId={...} /> // fetch 6
<TopCreative workspaceId={...} />        // fetch 7
<UnitEconomicsTable workspaceId={...} /> // fetch 8
```

### Fix
**Create a unified dashboard endpoint**:

```python
# backend/app/routers/dashboard.py
@router.get("/workspaces/{workspace_id}/dashboard")
def get_dashboard_data(workspace_id: str, timeframe: str = "last_7_days"):
    """Single endpoint returning all dashboard data."""
    return {
        "kpis": _get_kpis(...),
        "attribution_summary": _get_attribution(...),
        "attribution_feed": _get_feed(...),
        "top_creatives": _get_top_creatives(...),
        "spend_mix": _get_spend_mix(...),
        # Insights fetched separately (async/cached)
    }
```

```javascript
// Frontend: Single fetch, distribute to components
const dashboardData = await fetchDashboard({ workspaceId, timeframe });
<KpiStrip data={dashboardData.kpis} />
<MoneyPulseChart data={dashboardData.kpis} />
// etc.
```

---

## Issue #5: Low Memory Allocation (P2 - MEDIUM)

### Problem
Backend container has only 512MB memory. Under load, OOM kills likely.

```yaml
# compose.yaml:88
deploy:
  resources:
    reservations:
      memory: 512M
```

### Evidence
- Python + FastAPI + SQLAlchemy + Claude client = ~300MB baseline
- Each request with large result sets adds memory pressure
- No room for concurrent users

### Fix
```yaml
deploy:
  resources:
    reservations:
      memory: 1024M  # Double it
    limits:
      memory: 2048M  # Allow bursting
```

---

## Additional Issues Found

### 5.1: No Connection Pooling for External APIs
```python
# Each request creates new httpx client
async with httpx.AsyncClient() as client:  # New connection every time
```

**Fix**: Use persistent client with connection pooling.

### 5.2: `get_current_user` Queries DB on Every Request
```python
# backend/app/deps.py:75-79
user = db.query(User).filter(User.email == subject).first()  # Every request!
```

**Fix**: Cache user in Redis for session duration.

### 5.3: No Query Result Caching
Same KPI data fetched repeatedly. Consider:
- Redis cache for expensive queries
- HTTP cache headers for unchanged data

### 5.4: Large Response Payloads
Sparkline data returned even when not displayed.

---

## Recommended Fix Order

### Phase 1: Immediate (This Week)
1. **Add database indexes** - Biggest bang for buck
2. **Cache AI insights** - Reduces dashboard load by 4-10s
3. **Increase memory to 1GB** - Prevents crashes

### Phase 2: Short-term (Next 2 Weeks)
4. **Fix async/sync mismatch** - Prevents blocking
5. **Consolidate dashboard API calls** - Reduces frontend requests
6. **Remove redundant API calls** - MoneyPulseChart reuses KpiStrip data

### Phase 3: Medium-term
7. **Implement proper query caching** - Redis-backed
8. **Async SQLAlchemy migration** - Full async stack
9. **Add APM monitoring** - Track slow endpoints

---

## How to Verify Fixes

### Database Indexes
```sql
EXPLAIN ANALYZE SELECT * FROM entities WHERE workspace_id = 'xxx';
-- Before: Seq Scan (slow)
-- After: Index Scan (fast)
```

### Async Blocking
```bash
# Run load test with multiple concurrent users
ab -n 100 -c 10 https://api.metricx.ai/workspaces/xxx/dashboard/kpis
# Check: Are response times consistent or do they spike?
```

### Dashboard Load Time
```javascript
// Add timing to dashboard
console.time('dashboard-load');
// ...all fetches...
console.timeEnd('dashboard-load');
// Target: < 2 seconds
```

---

## Files Modified (Completed)

| File | Change | Status |
|------|--------|--------|
| `backend/alembic/versions/edfe2eb266dc_*.py` | Added 14 database indexes | DONE |
| `backend/app/routers/qa.py` | Added Redis caching (30min TTL), changed async→sync | DONE |
| `backend/app/routers/dashboard_kpis.py` | Changed async→sync | DONE |
| `backend/app/routers/attribution.py` | Changed 5 endpoints async→sync | DONE |
| `backend/app/routers/dashboard.py` | NEW: Unified dashboard endpoint (fixed Entity join) | DONE |
| `backend/app/main.py` | Registered dashboard router | DONE |
| `compose.yaml` | Backend: 512M→1024M, Worker: 256M→512M | DONE |
| `ui/lib/api.js` | Added fetchUnifiedDashboard | DONE |
| `ui/app/(dashboard)/dashboard/page.jsx` | Uses unified endpoint, lazy loads AI | DONE |
| `ui/app/(dashboard)/dashboard/components/*Unified.jsx` | 6 new components using props | DONE |

---

## Monitoring Recommendations

1. **Add Sentry Performance Monitoring** (already have Sentry)
   - Track slow transactions
   - Identify N+1 queries

2. **Add Database Query Logging**
   ```python
   # Log slow queries > 100ms
   import logging
   logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
   ```

3. **Add Frontend Performance Tracking**
   - Web Vitals (LCP, FID, CLS)
   - Custom timing for dashboard components
