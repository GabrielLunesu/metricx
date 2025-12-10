# Metric Snapshots System

**Last Updated**: 2025-12-10
**Version**: 1.0.0
**Status**: Production

---

## Overview

**MetricSnapshot** is the primary storage for ad platform metrics, replacing the daily MetricFact table with 15-minute granularity.

### Key Features

- **15-minute sync frequency** - Matches Meta/Google's data refresh rate
- **Intraday analytics** - Real-time spend progression for stop-loss rules
- **Automatic compaction** - 15-min → hourly after 2 days (storage efficiency)
- **Attribution correction** - Daily re-fetch of last 7 days catches delayed conversions

---

## Why 15-Minute Granularity?

| Use Case | Daily (MetricFact) | 15-Min (MetricSnapshot) |
|----------|-------------------|------------------------|
| Intraday dashboards | No data until EOD | Real-time updates |
| Stop-loss rules | Can't detect mid-day | Alert at threshold |
| Spend progression charts | Flat line | Actual curve |
| Real-time ROAS | Delayed | Current |

---

## Data Model

### MetricSnapshot Table

```sql
CREATE TABLE metric_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key to Entity (campaign/adset/ad)
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,

    -- Provider for quick filtering
    provider VARCHAR(20) NOT NULL,  -- 'meta', 'google', 'tiktok'

    -- Timestamp of this snapshot
    captured_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Base measures (cumulative daily values)
    spend NUMERIC(18, 4),
    impressions BIGINT,
    clicks BIGINT,
    conversions NUMERIC(18, 4),
    revenue NUMERIC(18, 4),
    leads NUMERIC(18, 4),
    purchases INTEGER,
    installs INTEGER,
    visitors INTEGER,
    profit NUMERIC(18, 4),

    -- Currency
    currency VARCHAR(10) DEFAULT 'USD',

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Primary query index
CREATE INDEX idx_snapshot_entity_captured
    ON metric_snapshots (entity_id, captured_at DESC);

-- Dashboard queries (workspace-wide aggregation)
CREATE INDEX idx_snapshot_dashboard
    ON metric_snapshots (entity_id, captured_at DESC)
    INCLUDE (spend, revenue, conversions);
```

### Python Model

```python
# backend/app/models.py

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(20), nullable=False)
    captured_at = Column(DateTime(timezone=True), nullable=False)

    # Base measures
    spend = Column(Numeric(18, 4), nullable=True)
    impressions = Column(BigInteger, nullable=True)
    clicks = Column(BigInteger, nullable=True)
    conversions = Column(Numeric(18, 4), nullable=True)
    revenue = Column(Numeric(18, 4), nullable=True)
    leads = Column(Numeric(18, 4), nullable=True)
    purchases = Column(Integer, nullable=True)
    installs = Column(Integer, nullable=True)
    visitors = Column(Integer, nullable=True)
    profit = Column(Numeric(18, 4), nullable=True)

    currency = Column(String(10), default='USD')
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        METRIC SNAPSHOT ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────┐
                    │           Ad Platforms               │
                    │    (Meta Ads API, Google Ads API)    │
                    └──────────────────┬──────────────────┘
                                       │
                                       │ API calls
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        snapshot_sync_service.py                              │
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  Meta Client    │    │  Google Client  │    │  TikTok Client  │         │
│  │  (meta_ads_     │    │  (google_ads_   │    │  (future)       │         │
│  │   client.py)    │    │   client.py)    │    │                 │         │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘         │
│           │                      │                      │                   │
│           └──────────────────────┼──────────────────────┘                   │
│                                  │                                          │
│                                  ▼                                          │
│                    ┌─────────────────────────┐                              │
│                    │    Upsert Logic         │                              │
│                    │    (INSERT ... ON       │                              │
│                    │     CONFLICT UPDATE)    │                              │
│                    └────────────┬────────────┘                              │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │    metric_snapshots     │
                    │    (PostgreSQL)         │
                    │                         │
                    │  entity_id | captured_at│
                    │  ----------|------------|
                    │  campaign1 | 14:00      │
                    │  campaign1 | 14:15      │
                    │  campaign1 | 14:30      │
                    │  ...       | ...        │
                    └─────────────────────────┘
```

---

## Sync Modes

### 1. Realtime Mode (Every 15 Minutes)

**Purpose:** Capture today's cumulative metrics
**Date Range:** Today only
**When:** Scheduled every 15 minutes

```python
def _sync_meta_snapshots(db, connection, mode="realtime"):
    if mode == "realtime":
        start_date = date.today()
        end_date = date.today()
```

### 2. Attribution Mode (Daily)

**Purpose:** Re-fetch last 7 days to catch delayed conversions
**Date Range:** Today minus 7 days
**When:** Daily at 3:00 AM UTC

**Why 7 days?** Ad platforms update conversion data retroactively:
- View-through conversions (up to 7 days)
- Cross-device attribution
- Offline conversion uploads

```python
def _sync_meta_snapshots(db, connection, mode="attribution"):
    if mode == "attribution":
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
```

### 3. Backfill Mode (New Connections)

**Purpose:** Initial historical data load
**Date Range:** Last 90 days
**When:** New connection setup

```python
def _sync_meta_snapshots(db, connection, mode="backfill"):
    if mode == "backfill":
        start_date = date.today() - timedelta(days=90)
        end_date = date.today()
```

---

## Sync Service Implementation

### Main Entry Point

```python
# backend/app/services/snapshot_sync_service.py

def sync_snapshots_for_connection(
    db: Session,
    connection_id: UUID,
    mode: str = "realtime",
    sync_entities: bool = True
) -> SnapshotSyncResult:
    """
    1. Sync entity hierarchy and status (if enabled)
    2. Fetch metrics from ad platform
    3. Upsert to MetricSnapshot table
    """

    # Step 1: Sync entities (captures paused/active changes)
    if sync_entities:
        _sync_entities_for_connection(db, connection)

    # Step 2: Sync metrics based on provider
    if connection.provider == ProviderEnum.meta:
        return _sync_meta_snapshots(db, connection, mode)
    elif connection.provider == ProviderEnum.google:
        return _sync_google_snapshots(db, connection, mode)
```

### Upsert Pattern

```python
def _upsert_snapshots(db: Session, snapshots: List[dict]) -> SnapshotSyncResult:
    """
    Atomic upsert using PostgreSQL INSERT ... ON CONFLICT.

    Key: (entity_id, captured_at) - unique per entity per timestamp
    """
    from sqlalchemy.dialects.postgresql import insert

    result = SnapshotSyncResult()

    stmt = insert(MetricSnapshot).values(snapshots)
    stmt = stmt.on_conflict_do_update(
        index_elements=['entity_id', 'captured_at'],
        set_={
            'spend': stmt.excluded.spend,
            'impressions': stmt.excluded.impressions,
            'clicks': stmt.excluded.clicks,
            'conversions': stmt.excluded.conversions,
            'revenue': stmt.excluded.revenue,
        }
    )

    db.execute(stmt)
    db.commit()

    return result
```

---

## Compaction

### Why Compact?

| Granularity | Rows/Day | Rows/Month |
|-------------|----------|------------|
| 15-minute | 96 | 2,880 |
| Hourly | 24 | 720 |
| Savings | 75% | 75% |

### Compaction Process

**Schedule:** Daily at 1:00 AM UTC
**Target:** Data from 2 days ago

```python
async def scheduled_compaction(ctx: Dict) -> Dict:
    """
    1. Target date = today - 2 days
    2. Group 15-min snapshots into hourly buckets
    3. Take MAX of each metric (cumulative)
    4. Insert hourly snapshot
    5. Delete original 15-min rows
    """
    target_date = date.today() - timedelta(days=2)

    hourly_count = await compact_snapshots_to_hourly(db, target_date)
```

### Compaction SQL

```sql
-- Insert hourly aggregates
INSERT INTO metric_snapshots (entity_id, provider, captured_at, spend, ...)
SELECT
    entity_id,
    provider,
    date_trunc('hour', captured_at) as captured_at,
    MAX(spend) as spend,     -- Cumulative, so MAX is correct
    MAX(impressions),
    MAX(clicks),
    MAX(conversions),
    MAX(revenue)
FROM metric_snapshots
WHERE captured_at::date = :target_date
GROUP BY entity_id, provider, date_trunc('hour', captured_at)
ON CONFLICT (entity_id, captured_at) DO UPDATE SET ...;

-- Delete original 15-min rows
DELETE FROM metric_snapshots
WHERE captured_at::date = :target_date
  AND EXTRACT(MINUTE FROM captured_at) NOT IN (0);  -- Keep hourly rows
```

---

## Querying Snapshots

### Latest Per Day (Dashboard)

```sql
-- Get latest snapshot per entity per day, then sum
SELECT
    COALESCE(SUM(spend), 0) as spend,
    COALESCE(SUM(revenue), 0) as revenue
FROM (
    SELECT DISTINCT ON (entity_id, date_trunc('day', captured_at))
        spend, revenue
    FROM metric_snapshots
    WHERE entity_id IN (SELECT id FROM entities WHERE workspace_id = :ws)
      AND captured_at BETWEEN :start AND :end
    ORDER BY entity_id, date_trunc('day', captured_at), captured_at DESC
) latest;
```

### Time Series (Charts)

```sql
-- Daily breakdown
SELECT
    date_trunc('day', captured_at)::date as day,
    provider,
    SUM(spend), SUM(revenue)
FROM (
    SELECT DISTINCT ON (entity_id, date_trunc('day', captured_at))
        captured_at, provider, spend, revenue
    FROM metric_snapshots
    WHERE workspace_id = :ws
    ORDER BY entity_id, date_trunc('day', captured_at), captured_at DESC
) latest
GROUP BY day, provider
ORDER BY day;
```

### Intraday (Today/Yesterday)

```sql
-- 15-minute breakdown for intraday charts
SELECT
    date_trunc('hour', captured_at) +
    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM captured_at) / 15) as bucket,
    provider,
    SUM(spend), SUM(revenue)
FROM (
    SELECT DISTINCT ON (entity_id, bucket)
        ...,
        spend, revenue
    FROM metric_snapshots
    WHERE captured_at::date = CURRENT_DATE
    ORDER BY entity_id, bucket, captured_at DESC
) latest
GROUP BY bucket, provider;
```

---

## Entity Relationship

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ENTITY HIERARCHY                                    │
└─────────────────────────────────────────────────────────────────────────────┘

  Workspace
      │
      └── Connection (Meta / Google)
              │
              └── Entity (campaign)
                      │
                      ├── Entity (adset)           [Meta]
                      │       │
                      │       └── Entity (ad)
                      │
                      └── Entity (asset_group)     [Google PMax]

  MetricSnapshot links to Entity at ANY level:
  - Campaign-level for standard campaigns
  - Asset_group level for Google PMax
  - Ad level for granular reporting
```

### Rolling Up Metrics

For campaign-level reporting, child entity metrics are rolled up:

```sql
-- Roll up child metrics to parent campaign
WITH campaign_metrics AS (
    SELECT
        COALESCE(e.parent_id, e.id) as campaign_id,
        ms.spend, ms.revenue
    FROM entities e
    JOIN metric_snapshots ms ON ms.entity_id = e.id
    WHERE e.workspace_id = :ws
)
SELECT campaign_id, SUM(spend), SUM(revenue)
FROM campaign_metrics
GROUP BY campaign_id;
```

---

## Migration from MetricFact

### Timeline

1. **2025-12-07**: MetricSnapshot table created
2. **2025-12-07**: Historical MetricFact data migrated
3. **2025-12-08**: New syncs write to MetricSnapshot
4. **Future**: MetricFact table will be dropped

### Migration Script

```python
# alembic/versions/20251207_000002_migrate_metric_facts_to_snapshots.py

def upgrade():
    """Migrate existing MetricFact data to MetricSnapshot."""
    op.execute("""
        INSERT INTO metric_snapshots (
            entity_id, provider, captured_at,
            spend, impressions, clicks, conversions, revenue
        )
        SELECT
            entity_id, provider::text, event_date as captured_at,
            spend, impressions, clicks, conversions, revenue
        FROM metric_facts
        ON CONFLICT (entity_id, captured_at) DO NOTHING;
    """)
```

### Dual-Read Period

```python
# backend/app/services/unified_metric_service.py

def get_metrics(workspace_id, start, end):
    """
    Query both tables during migration period.
    MetricSnapshot takes precedence for overlapping dates.
    """
    # Primary: MetricSnapshot (new data)
    # Fallback: MetricFact (old data before migration)
```

---

## Storage Estimates

### Per Workspace

| Connections | Campaigns | Snapshots/Day | Monthly Storage |
|-------------|-----------|---------------|-----------------|
| 2 | 10 | 960 (15-min) | ~2 MB |
| 2 | 10 | 240 (hourly, compacted) | ~0.5 MB |

### Platform-Wide

| Workspaces | Monthly (15-min) | Monthly (compacted) |
|------------|------------------|---------------------|
| 100 | 200 MB | 50 MB |
| 1000 | 2 GB | 500 MB |

---

## Database Indexes

```sql
-- Primary query pattern: entity + time range
CREATE INDEX idx_snapshot_entity_captured
    ON metric_snapshots (entity_id, captured_at DESC);

-- Dashboard aggregation with covering columns
CREATE INDEX idx_snapshot_dashboard
    ON metric_snapshots (entity_id, captured_at DESC)
    INCLUDE (spend, revenue, conversions);

-- Provider filtering (for spend mix)
CREATE INDEX idx_snapshot_provider
    ON metric_snapshots (provider, captured_at DESC);
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `backend/app/models.py` | MetricSnapshot model |
| `backend/app/services/snapshot_sync_service.py` | Sync logic |
| `backend/app/services/meta_ads_client.py` | Meta API integration |
| `backend/app/services/google_ads_client.py` | Google API integration |
| `backend/app/workers/arq_worker.py` | Scheduled sync jobs |
| `backend/app/routers/dashboard.py` | Dashboard queries |
| `backend/alembic/versions/20251207_000001_add_metric_snapshots.py` | Table creation |
| `backend/alembic/versions/20251207_000002_migrate_metric_facts_to_snapshots.py` | Data migration |
