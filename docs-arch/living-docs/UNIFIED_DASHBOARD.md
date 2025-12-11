# Unified Dashboard API

**Last Updated**: 2025-12-10
**Version**: 1.0.0
**Status**: Production

---

## Overview

The Unified Dashboard API returns **all dashboard data in a single request**, replacing 8+ separate API calls with 1. This dramatically improves dashboard load time.

### Before (8+ Requests)

```
1. GET /auth/me
2. GET /workspaces/{id}/status
3. GET /workspaces/{id}/dashboard/kpis
4. POST /workspaces/{id}/kpis (MoneyPulseChart - redundant!)
5. POST /qa/insights x2 (AI calls - slow!)
6. GET /workspaces/{id}/attribution/summary
7. GET /workspaces/{id}/attribution/feed
8. GET /entity-performance (TopCreative)
9. GET /entity-performance (UnitEconomicsTable)
```

### After (1 Request)

```
GET /workspaces/{id}/dashboard/unified
```

**Note:** AI insights are NOT included - they should be lazy-loaded separately.

---

## API Endpoint

### GET /workspaces/{workspace_id}/dashboard/unified

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeframe` | string | `last_7_days` | Preset: `today`, `yesterday`, `last_7_days`, `last_30_days`, `last_90_days` |
| `start_date` | string | null | Custom start (YYYY-MM-DD), overrides timeframe |
| `end_date` | string | null | Custom end (YYYY-MM-DD), overrides timeframe |

**Response:**

```typescript
interface UnifiedDashboardResponse {
  // Core KPIs
  kpis: KpiData[];
  data_source: "shopify" | "platform";
  has_shopify: boolean;
  connected_platforms: string[];  // ["meta", "google"]
  currency: string;  // "USD", "EUR", etc.

  // Chart data (for Recharts)
  chart_data: ChartDataPoint[];

  // Top campaigns (last 48 hours)
  top_campaigns: TopCampaignItem[];

  // Spend mix by platform
  spend_mix: SpendMixItem[];

  // Attribution (only if Shopify connected)
  attribution_summary?: AttributionSummaryItem[];
  attribution_feed?: AttributionFeedItem[];

  // Sync status
  last_synced_at?: string;  // ISO timestamp
}
```

---

## Response Models

### KpiData

```typescript
interface KpiData {
  key: string;           // "revenue", "roas", "spend", "conversions"
  value: number;         // Current period value
  prev: number | null;   // Previous period value
  delta_pct: number | null;  // % change
  sparkline: SparkPoint[];   // Chart data points
}

interface SparkPoint {
  date: string;   // "2025-12-08" or "2025-12-08T14:00:00"
  value: number;
}
```

### ChartDataPoint

```typescript
interface ChartDataPoint {
  date: string;  // ISO date or timestamp

  // Totals
  revenue: number;
  spend: number;
  conversions: number;
  roas: number;

  // Per-provider breakdown
  meta_revenue?: number;
  meta_spend?: number;
  meta_conversions?: number;
  meta_roas?: number;

  google_revenue?: number;
  google_spend?: number;
  google_conversions?: number;
  google_roas?: number;
}
```

### TopCampaignItem

```typescript
interface TopCampaignItem {
  id: string;
  name: string;
  platform: string;  // "meta" | "google"
  spend: number;
  revenue: number;
  roas: number;
}
```

### SpendMixItem

```typescript
interface SpendMixItem {
  provider: string;  // "meta" | "google"
  spend: number;
  pct: number;       // Percentage of total
}
```

### AttributionSummaryItem

```typescript
interface AttributionSummaryItem {
  channel: string;   // "meta" | "google"
  revenue: number;
  orders: number;
  pct: number;       // Percentage of total
}
```

### AttributionFeedItem

```typescript
interface AttributionFeedItem {
  order_id: string;
  revenue: number;
  provider: string;
  campaign_name: string | null;
  attributed_at: string;  // ISO timestamp
}
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED DASHBOARD DATA FLOW                          │
└─────────────────────────────────────────────────────────────────────────────┘

  Browser Request
  ───────────────
       │
       ▼
  GET /dashboard/unified?timeframe=last_7_days
       │
       ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                    get_unified_dashboard()                       │
  │                   backend/app/routers/dashboard.py               │
  └─────────────────────────────────────────────────────────────────┘
       │
       │  Parallel queries to MetricSnapshot table
       │
       ├──▶ _get_kpis_and_chart_data()
       │         │
       │         ├─ Current period aggregation (DISTINCT ON)
       │         ├─ Previous period aggregation (for delta)
       │         └─ Time-bucketed breakdown (daily or 15-min)
       │
       ├──▶ _get_top_campaigns()
       │         │
       │         └─ Last 48 hours, ACTIVE campaigns, roll up child metrics
       │
       ├──▶ _get_spend_mix()
       │         │
       │         └─ Spend by provider (meta, google)
       │
       └──▶ _get_attribution_data() [if Shopify connected]
                 │
                 ├─ Attribution summary by channel
                 └─ Recent attribution feed (last 10)
       │
       ▼
  JSON Response (single payload)
```

---

## KPI Calculations

### Revenue

```sql
SELECT SUM(revenue)
FROM (
    SELECT DISTINCT ON (entity_id, date_trunc('day', captured_at))
        revenue
    FROM metric_snapshots
    WHERE workspace_id = :workspace_id
      AND captured_at BETWEEN :start AND :end
    ORDER BY entity_id, date_trunc('day', captured_at), captured_at DESC
) latest_snapshots
```

**Why DISTINCT ON?** MetricSnapshot stores cumulative daily values. Multiple snapshots per day exist (15-min granularity). We want the LATEST snapshot per entity per day.

### ROAS

```python
roas = revenue / spend if spend > 0 else 0
```

### Delta Percentage

```python
delta_pct = (current - previous) / previous if previous > 0 else None
```

---

## Time Granularity

| Timeframe | Chart Granularity | Sparkline Format |
|-----------|-------------------|------------------|
| `today` | 15-minute buckets | `2025-12-08T14:00:00` |
| `yesterday` | 15-minute buckets | `2025-12-08T14:00:00` |
| `last_7_days` | Daily | `2025-12-08` |
| `last_30_days` | Daily | `2025-12-08` |
| `last_90_days` | Daily | `2025-12-08` |

**Why 15-minute for intraday?** Matches our sync frequency. Shows real-time spend progression.

---

## Top Campaigns Logic

```sql
-- Get active campaigns with highest spend in last 48 hours
-- Roll up child entity metrics (asset_group, adset, ad) to campaign level

WITH campaign_metrics AS (
    SELECT
        COALESCE(e.parent_id, e.id) as campaign_id,  -- Roll up to parent
        sub.spend,
        sub.revenue
    FROM entities e
    JOIN (
        SELECT DISTINCT ON (entity_id, date_trunc('day', captured_at))
            entity_id, spend, revenue
        FROM metric_snapshots
        WHERE captured_at >= NOW() - INTERVAL '48 hours'
        ORDER BY entity_id, date_trunc('day', captured_at), captured_at DESC
    ) sub ON sub.entity_id = e.id
)
SELECT
    camp.id, camp.name, c.provider,
    SUM(cm.spend) as spend,
    SUM(cm.revenue) as revenue
FROM entities camp
JOIN campaign_metrics cm ON cm.campaign_id = camp.id
WHERE camp.level = 'campaign'
  AND camp.status = 'active'
GROUP BY camp.id, camp.name, c.provider
HAVING SUM(cm.spend) > 0
ORDER BY spend DESC
LIMIT 5
```

**Why 48-hour window?** Shows current activity regardless of dashboard timeframe.

**Why roll up child metrics?** Google PMax syncs metrics at asset_group level, not campaign level.

---

## Currency Handling

```python
# Get currency from first ad connection
primary_currency = "USD"
for conn in ad_connections:
    if conn.currency_code:
        primary_currency = conn.currency_code
        break

# All monetary values in response use this currency
return UnifiedDashboardResponse(
    currency=primary_currency,
    # ...
)
```

Frontend displays the correct symbol based on `currency` field.

---

## Frontend Integration

### Fetching Data

```javascript
// ui/lib/api.js

export async function fetchUnifiedDashboard(workspaceId, timeframe = 'last_7_days') {
  const params = new URLSearchParams({ timeframe });
  const response = await fetch(
    `${API_URL}/workspaces/${workspaceId}/dashboard/unified?${params}`,
    { credentials: 'include' }
  );
  return response.json();
}
```

### Using the Data

```jsx
// ui/app/(dashboard)/dashboard/page.jsx

const { data, isLoading } = useQuery({
  queryKey: ['dashboard', workspaceId, timeframe],
  queryFn: () => fetchUnifiedDashboard(workspaceId, timeframe),
});

// KPIs
<KpiStripUnified kpis={data.kpis} currency={data.currency} />

// Chart
<MoneyPulseChartUnified data={data.chart_data} platforms={data.connected_platforms} />

// Top Campaigns
<TopCampaignsUnified campaigns={data.top_campaigns} />

// Spend Mix
<SpendMixUnified data={data.spend_mix} />

// Attribution (conditional)
{data.has_shopify && (
  <>
    <AttributionCardUnified summary={data.attribution_summary} />
    <LiveAttributionFeedUnified feed={data.attribution_feed} />
  </>
)}
```

---

## Performance

### Query Optimization

| Optimization | Technique |
|--------------|-----------|
| Index usage | `idx_snapshot_entity_captured` on (entity_id, captured_at) |
| DISTINCT ON | Gets latest snapshot without subquery |
| Parallel queries | KPIs, campaigns, mix fetched in same request |
| No N+1 | Single query per data section |

### Response Size

Typical response: ~5-15 KB depending on chart data points

| Timeframe | Chart Points | ~Size |
|-----------|--------------|-------|
| `today` | ~96 (15-min buckets) | 10 KB |
| `last_7_days` | 7 | 5 KB |
| `last_30_days` | 30 | 8 KB |

---

## AI Insights (Separate)

AI insights are **NOT included** in the unified response. They should be:

1. **Lazy loaded** after dashboard renders
2. **Streamed** for better UX
3. **Cached** to avoid repeated LLM calls

```javascript
// Load AI insights separately
const { data: insights } = useQuery({
  queryKey: ['insights', workspaceId],
  queryFn: () => fetchAIInsights(workspaceId),
  staleTime: 5 * 60 * 1000,  // Cache 5 minutes
});
```

---

## Error Handling

### Authorization

```python
@router.get("/{workspace_id}/dashboard/unified")
def get_unified_dashboard(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
):
    # Verify workspace access
    if current_user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied")
```

### Empty States

| Condition | Response |
|-----------|----------|
| No connections | Empty arrays, `connected_platforms: []` |
| No data in range | KPIs with 0 values, empty sparklines |
| No Shopify | `has_shopify: false`, no attribution data |

---

## Comparison: Before vs After

```
BEFORE: 8+ Network Requests
─────────────────────────────
Request 1: /auth/me                    → 50ms
Request 2: /workspaces/status          → 30ms
Request 3: /dashboard/kpis             → 150ms
Request 4: /kpis (chart)               → 150ms
Request 5: /qa/insights                → 2000ms (AI!)
Request 6: /qa/insights                → 2000ms (AI!)
Request 7: /attribution/summary        → 100ms
Request 8: /attribution/feed           → 100ms
Request 9: /entity-performance         → 200ms
                                       ──────────
                              Total:    4780ms

AFTER: 1 Network Request
─────────────────────────────
Request 1: /dashboard/unified          → 200ms
                                       ──────────
                              Total:    200ms

Improvement: ~24x faster (excluding AI insights)
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `backend/app/routers/dashboard.py` | Unified endpoint |
| `backend/app/schemas.py` | Response models |
| `ui/lib/api.js` | Frontend fetch |
| `ui/app/(dashboard)/dashboard/components/KpiStripUnified.jsx` | KPI display |
| `ui/app/(dashboard)/dashboard/components/MoneyPulseChartUnified.jsx` | Chart |
| `ui/app/(dashboard)/dashboard/components/TopCampaignsUnified.jsx` | Top campaigns |
| `ui/app/(dashboard)/dashboard/components/SpendMixUnified.jsx` | Spend breakdown |
| `ui/app/(dashboard)/dashboard/components/AttributionCardUnified.jsx` | Attribution |
| `ui/app/(dashboard)/dashboard/components/LiveAttributionFeedUnified.jsx` | Attribution feed |
