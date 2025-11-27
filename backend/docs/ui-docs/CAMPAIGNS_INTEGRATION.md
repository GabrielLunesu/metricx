# Campaigns UI Integration Documentation

**Status:** ✅ Complete  
**Date:** October 12, 2025  
**Version:** 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Backend Implementation](#backend-implementation)
4. [Frontend Implementation](#frontend-implementation)
5. [Data Flow](#data-flow)
6. [API Contracts](#api-contracts)
7. [Hierarchy & Drill-Down](#hierarchy--drill-down)
8. [Testing](#testing)
9. [Known Limitations](#known-limitations)
10. [Future Enhancements](#future-enhancements)

---

## Overview

The Campaigns UI Integration connects the frontend Campaigns page to the backend API with strict separation of concerns, providing live metrics for campaigns, ad sets, and ads with three-level drill-down navigation.

### Key Features

- **Three-level drill-down**: Campaigns → Ad Sets → Ads
- **Live metrics**: Revenue, Spend, ROAS, Conversions, CPC, CTR
- **Hierarchy-aware rollup**: Metrics aggregated from leaf nodes (ads) to ancestors (campaigns/ad sets)
- **Trend sparklines**: Small timeseries (7d/30d) with gap filling
- **Last updated**: MetricFact.ingested_at formatted as relative time
- **Filters**: Platform, Status, Timeframe
- **Sorting**: ROAS (default), Revenue, Spend, Conversions, CPC, CTR
- **Pagination**: 8 rows per page with total count

### Design Principles

1. **Strict Separation of Concerns**
   - Backend: Metrics aggregation, hierarchy resolution, data validation
   - API Client: Thin HTTP layer with caching, zero business logic
   - Adapter: Formatting and view model mapping only
   - UI Components: Presentational, receive props, no data fetching

2. **WHAT/WHY/REFERENCES Comments**
   - Every new file includes header explaining purpose and cross-references

3. **Dumb Components**
   - UI components receive formatted data via props
   - No business logic, no data fetching, no calculations

4. **Workspace Safety**
   - All queries filter by workspace_id at SQL level
   - No cross-tenant data leaks

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (ui/)                           │
├─────────────────────────────────────────────────────────────────┤
│  Pages (Next.js App Router)                                      │
│  ├─ /campaigns                 ← Campaigns list                  │
│  ├─ /campaigns/[id]            ← Ad sets for campaign            │
│  └─ /campaigns/[id]/[adsetId]  ← Ads for ad set                 │
│                                                                   │
│  Components (Presentational)                                     │
│  ├─ TopToolbar                 ← Filters, sorting, timeframe     │
│  ├─ CampaignRow                ← Table row with metrics          │
│  ├─ EntityTable                ← Generic table for drill-down    │
│  ├─ EntityRow                  ← Ad set/ad row                   │
│  └─ TrendSparkline             ← SVG sparkline                   │
│                                                                   │
│  Data Layer (lib/)                                               │
│  ├─ campaignsApiClient.js      ← HTTP calls + caching            │
│  └─ campaignsAdapter.js        ← Formatting + view model         │
└─────────────────────────────────────────────────────────────────┘
                                  ↓ HTTP (fetch)
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND (backend/)                         │
├─────────────────────────────────────────────────────────────────┤
│  API Routes (FastAPI)                                            │
│  ├─ GET /entity-performance/list         ← List entities         │
│  └─ GET /entity-performance/{id}/children ← Drill-down           │
│                                                                   │
│  Router (app/routers/entity_performance.py)                      │
│  ├─ _base_query()              ← Core SQL with hierarchy CTEs    │
│  ├─ _apply_sort()              ← Server-side sorting             │
│  ├─ _fetch_trend()             ← Sparkline timeseries            │
│  └─ list_entities_performance() ← Main endpoint handler          │
│                                                                   │
│  Database Layer                                                  │
│  ├─ campaign_ancestor_cte()    ← Recursive CTE (hierarchy.py)    │
│  ├─ adset_ancestor_cte()       ← Recursive CTE (hierarchy.py)    │
│  └─ MetricFact                 ← Facts at ad level               │
└─────────────────────────────────────────────────────────────────┘
                                  ↓ PostgreSQL
┌─────────────────────────────────────────────────────────────────┐
│                          DATABASE                                 │
│  ├─ entities                   ← Campaign/adset/ad hierarchy      │
│  └─ metric_facts               ← Daily metrics at ad level        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Backend Implementation

### File Structure

```
backend/app/
├── routers/
│   └── entity_performance.py   ← Main API router
├── schemas.py                  ← Pydantic DTOs
├── dsl/
│   └── hierarchy.py            ← Recursive CTEs
└── tests/
    └── test_entity_performance.py ← Integration tests
```

### Key Functions

#### `_base_query()`

**Purpose**: Constructs the core SQLAlchemy query with hierarchy rollup.

**Logic**:
- For **campaign level**: Uses `campaign_ancestor_cte()` to aggregate metrics from all child ads
- For **ad set level**: Uses `adset_ancestor_cte()` to aggregate metrics from all child ads
- For **ad level**: Direct `MetricFact` query (leaf nodes, no hierarchy needed)
- Applies filters: workspace_id, date range, platform, status, parent_id
- Groups by entity (id, name, status, connection_id)

**Example SQL (campaign level)**:
```sql
SELECT
  ancestor.id AS entity_id,
  ancestor.name AS entity_name,
  ancestor.status,
  ancestor.connection_id,
  MAX(metric_facts.ingested_at) AS last_updated,
  COALESCE(SUM(metric_facts.spend), 0) AS spend,
  COALESCE(SUM(metric_facts.revenue), 0) AS revenue,
  COALESCE(SUM(metric_facts.clicks), 0) AS clicks,
  COALESCE(SUM(metric_facts.impressions), 0) AS impressions,
  COALESCE(SUM(metric_facts.conversions), 0) AS conversions
FROM metric_facts
JOIN entities AS leaf ON leaf.id = metric_facts.entity_id
JOIN campaign_ancestors ON campaign_ancestors.leaf_id = leaf.id
JOIN entities AS ancestor ON ancestor.id = campaign_ancestors.ancestor_id
WHERE
  ancestor.workspace_id = :workspace_id
  AND DATE(metric_facts.event_date) >= :start
  AND DATE(metric_facts.event_date) < :end
GROUP BY ancestor.id, ancestor.name, ancestor.status, ancestor.connection_id
```

#### `_apply_sort()`

**Purpose**: Applies server-side sorting using aggregate expressions.

**Why**: PostgreSQL requires ORDER BY expressions in GROUP BY queries to be aggregates or grouped columns.

**Implementation**:
- ROAS: `SUM(revenue) / NULLIF(SUM(spend), 0)`
- CPC: `SUM(spend) / NULLIF(SUM(clicks), 0)`
- CTR: `SUM(clicks) / NULLIF(SUM(impressions), 0)`
- Revenue/Spend/Conversions: Direct `SUM()`

**Example**:
```python
if sort_by == "roas":
    order_clause = func.coalesce(func.sum(MF.revenue), 0) / func.nullif(func.coalesce(func.sum(MF.spend), 0), 0)
return query.order_by(desc(order_clause) if sort_dir == "desc" else asc(order_clause))
```

#### `_fetch_trend()`

**Purpose**: Fetches daily trend data for sparklines.

**Logic**:
- Returns array of `{date, value}` for last N days
- Uses same hierarchy CTEs as `_base_query()`
- Groups by `event_date` for timeseries
- Fills missing days in adapter (frontend)

---

## Frontend Implementation

### File Structure

```
ui/
├── lib/
│   ├── campaignsApiClient.js   ← HTTP calls + caching
│   ├── campaignsAdapter.js     ← Formatting + view model
│   └── index.js                ← Central exports
├── app/(dashboard)/campaigns/
│   ├── page.jsx                ← Campaigns list page
│   ├── [id]/page.jsx           ← Ad sets for campaign
│   └── [id]/[adsetId]/page.jsx ← Ads for ad set
└── components/campaigns/
    ├── TopToolbar.jsx          ← Filters + sorting
    ├── CampaignRow.jsx         ← Table row
    ├── EntityTable.jsx         ← Generic table
    ├── EntityRow.jsx           ← Ad set/ad row
    ├── PlatformBadge.jsx       ← Platform icon
    └── TrendSparkline.jsx      ← SVG sparkline
```

### API Client (`campaignsApiClient.js`)

**Purpose**: Thin HTTP layer with caching.

**Functions**:
- `fetchEntityPerformance()`: Fetches list or children with caching
- `invalidateEntityPerformanceCache()`: Clears cache

**Caching Strategy**:
```javascript
const cache = new Map();
const key = JSON.stringify({ level, parentId, params });
if (cache.has(key)) return cache.get(key);
```

**Key feature**: Conditionally adds `entity_level` param only for list endpoint (not for children).

### Adapter (`campaignsAdapter.js`)

**Purpose**: Transform raw API response into UI-ready view model.

**Functions**:
- `formatCurrency(value)`: `$1,234.56` or `$1.2K`
- `formatRatio(value)`: `2.45×` (ROAS)
- `formatPercentage(value)`: `4.2%` (CTR)
- `relativeTime(isoDate)`: `"2h ago"`, `"3d ago"`
- `alignTrend(points, fillValue)`: Fill missing days with zeros
- `adaptEntityPerformance(payload)`: Main transformation

**View Model**:
```javascript
{
  rows: [
    {
      id: "uuid",
      name: "Campaign Name",
      platform: "meta",
      status: "active",
      level: "campaign", // Used to determine if has children
      revenueRaw: 12345.67,
      spendRaw: 5678.90,
      roasRaw: 2.17,
      conversionsRaw: 42,
      cpcRaw: 0.32,
      ctrRaw: 3.45,
      lastUpdatedAt: "2025-10-12T14:00:00Z",
      trendMetric: "revenue",
      trend: [{ date: "2025-10-05", value: 1234 }, ...],
      display: {
        revenue: "$12,345.67",
        spend: "$5,678.90",
        roas: "2.17×",
        conversions: "42",
        cpc: "$0.32",
        ctr: "3.45%",
        subtitle: "Last updated 2h ago"
      }
    }
  ],
  meta: {
    title: "Campaigns",
    level: "campaign",
    subtitle: "Last updated 2h ago"
  },
  pagination: {
    total: 42,
    page: 1,
    pageSize: 8
  }
}
```

### Pages

#### `/campaigns` (`page.jsx`)

**State Management**:
```javascript
const [filters, setFilters] = useState({
  platform: null,
  status: "active",
  timeframe: "7d",
  sortBy: "roas",
  sortDir: "desc",
  page: 1,
  pageSize: 8,
});
```

**Data Fetching**:
```javascript
useEffect(() => {
  fetchCampaigns();
}, [workspaceId, filters]);
```

**Navigation**:
```javascript
const handleCampaignClick = (campaignId) => {
  router.push(`/campaigns/${campaignId}`);
};
```

#### `/campaigns/[id]` (`[id]/page.jsx`)

**Same layout as campaigns list**, but:
- Fetches ad sets for parent campaign
- Title shows campaign name
- Breadcrumbs: "Campaigns › {Campaign Name}"
- Click ad set → navigate to `/campaigns/{id}/{adsetId}`

#### `/campaigns/[id]/[adsetId]` (`[id]/[adsetId]/page.jsx`)

**Same layout as above**, but:
- Fetches ads for parent ad set
- Title shows ad set name
- Breadcrumbs: "Campaigns › {Campaign Name} › {Ad Set Name}"
- Ads are leaf nodes (no further drill-down)

---

## Data Flow

### 1. User Loads `/campaigns`

```
┌──────────────────────────────────────────────────────────────┐
│ 1. User visits /campaigns                                     │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. page.jsx calls fetchCampaigns()                           │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. campaignsApiClient.fetchEntityPerformance({               │
│      entityLevel: "campaign",                                │
│      platform: null,                                         │
│      status: "active",                                       │
│      timeframe: "7d",                                        │
│      sortBy: "roas",                                         │
│      sortDir: "desc",                                        │
│      page: 1,                                                │
│      pageSize: 8                                             │
│    })                                                        │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. GET /entity-performance/list?entity_level=campaign&...    │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. Backend: _base_query() with campaign_ancestor_cte()      │
│    → Aggregates metrics from all child ads                   │
│    → Applies filters, sorting, pagination                    │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 6. Backend: _fetch_trend() for each campaign                │
│    → Returns small timeseries for sparklines                 │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 7. Backend returns EntityPerformanceResponse                 │
│    {                                                         │
│      meta: { title, level, last_updated_at },               │
│      pagination: { total, page, page_size },                │
│      rows: [{ id, name, revenue, spend, roas, ... }]        │
│    }                                                         │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 8. campaignsAdapter.adaptEntityPerformance(apiResponse)      │
│    → Formats currency, ratios, percentages                   │
│    → Fills trend gaps with zeros                             │
│    → Computes relative time strings                          │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 9. page.jsx receives view model                              │
│    {                                                         │
│      rows: [{ display: { revenue, spend, ... } }],          │
│      meta: { title: "Campaigns", subtitle: "..." },         │
│      pagination: { total, page, pageSize }                  │
│    }                                                         │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 10. UI renders CampaignRow for each row                     │
│     → Shows formatted values from row.display                │
│     → Renders TrendSparkline with row.trend                  │
│     → onClick → navigate to /campaigns/{id}                  │
└──────────────────────────────────────────────────────────────┘
```

### 2. User Clicks Campaign (Drill-Down)

```
┌──────────────────────────────────────────────────────────────┐
│ 1. User clicks campaign row                                  │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. router.push(`/campaigns/${campaignId}`)                   │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. [id]/page.jsx loads with campaignId from params          │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. campaignsApiClient.fetchEntityPerformance({               │
│      entityLevel: "adset",                                   │
│      parentId: campaignId, ← Key difference                  │
│      ... same filters as before                              │
│    })                                                        │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. GET /entity-performance/{campaignId}/children?...         │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 6. Backend: _base_query() with adset_ancestor_cte()         │
│    → Filters by parent_id = campaignId                       │
│    → Aggregates metrics for ad sets                          │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 7. Same formatting/rendering as campaigns list               │
│    BUT: meta.title = campaign name, level = "adset"          │
│    AND: Breadcrumbs = "Campaigns › {Campaign Name}"          │
└──────────────────────────────────────────────────────────────┘
```

### 3. User Clicks Ad Set (Second Drill-Down)

```
┌──────────────────────────────────────────────────────────────┐
│ 1. User clicks ad set row                                    │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. router.push(`/campaigns/${campaignId}/${adsetId}`)        │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. [id]/[adsetId]/page.jsx loads with adsetId               │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. campaignsApiClient.fetchEntityPerformance({               │
│      entityLevel: "ad",                                      │
│      parentId: adsetId, ← Key difference                     │
│      ... same filters as before                              │
│    })                                                        │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. GET /entity-performance/{adsetId}/children?...            │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 6. Backend: _base_query() with direct MetricFact query      │
│    → Filters by entity.parent_id = adsetId                   │
│    → No hierarchy CTE needed (ads are leaf nodes)            │
└──────────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────────┐
│ 7. Same formatting/rendering as above                        │
│    BUT: meta.title = ad set name, level = "ad"               │
│    AND: Breadcrumbs = "Campaigns › {Campaign} › {Ad Set}"    │
│    AND: No "View" button (ads are leaf nodes)                │
└──────────────────────────────────────────────────────────────┘
```

---

## API Contracts

### Request: `GET /entity-performance/list`

**Query Parameters**:
```
entity_level: "campaign" | "adset" | "ad"
timeframe: "7d" | "30d" | "custom"
date_start: "YYYY-MM-DD" (required if timeframe=custom)
date_end: "YYYY-MM-DD" (required if timeframe=custom)
platform: "meta" | "google" | "tiktok" | null
status: "active" | "paused" | "all" | null
sort_by: "roas" | "revenue" | "spend" | "conversions" | "cpc" | "ctr"
sort_dir: "asc" | "desc"
page: int (1-indexed)
page_size: int (default: 25, max: 100)
```

### Request: `GET /entity-performance/{entity_id}/children`

**Query Parameters**: Same as above, except:
- `entity_level` is omitted (inferred from parent entity level)
- `parent_id` is in the URL path

### Response: `EntityPerformanceResponse`

```json
{
  "meta": {
    "title": "Campaigns",
    "subtitle": null,
    "level": "campaign",
    "last_updated_at": "2025-10-12T14:00:00Z"
  },
  "pagination": {
    "total": 42,
    "page": 1,
    "page_size": 8
  },
  "rows": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Summer Sale Campaign",
      "platform": "meta",
      "revenue": 12345.67,
      "spend": 5678.90,
      "roas": 2.17,
      "conversions": 42,
      "cpc": 0.32,
      "ctr_pct": 3.45,
      "status": "active",
      "last_updated_at": "2025-10-12T14:00:00Z",
      "trend": [
        { "date": "2025-10-05", "value": 1234.56 },
        { "date": "2025-10-06", "value": 1345.67 },
        { "date": "2025-10-07", "value": 1456.78 }
      ],
      "trend_metric": "revenue"
    }
  ]
}
```

---

## Hierarchy & Drill-Down

### Entity Hierarchy

```
Workspace
  └─ Connection (platform)
       └─ Campaign (level=campaign)
            └─ Ad Set (level=adset, parent_id=campaign.id)
                 └─ Ad (level=ad, parent_id=adset.id)
                      └─ MetricFact (entity_id=ad.id, event_date, metrics)
```

### Metric Rollup Strategy

**Problem**: MetricFacts are stored at the ad level (leaf nodes), but users want to see aggregated metrics for campaigns and ad sets.

**Solution**: Recursive CTEs that map leaf entities to ancestors.

#### Campaign Rollup

```sql
-- campaign_ancestor_cte() creates a mapping: leaf_id → ancestor_id
WITH RECURSIVE campaign_ancestors AS (
  -- Base case: All campaigns map to themselves
  SELECT id AS ancestor_id, id AS leaf_id
  FROM entities
  WHERE level = 'campaign' AND workspace_id = :workspace_id
  
  UNION ALL
  
  -- Recursive case: Map children to ancestor
  SELECT ca.ancestor_id, e.id AS leaf_id
  FROM campaign_ancestors ca
  JOIN entities e ON e.parent_id = ca.leaf_id
  WHERE e.workspace_id = :workspace_id
)
SELECT * FROM campaign_ancestors;
```

**Usage in `_base_query()`**:
```sql
SELECT
  ancestor.id, ancestor.name,
  SUM(metric_facts.revenue) AS revenue,
  SUM(metric_facts.spend) AS spend
FROM metric_facts
JOIN entities AS leaf ON leaf.id = metric_facts.entity_id
JOIN campaign_ancestors ON campaign_ancestors.leaf_id = leaf.id
JOIN entities AS ancestor ON ancestor.id = campaign_ancestors.ancestor_id
WHERE ancestor.workspace_id = :workspace_id
GROUP BY ancestor.id, ancestor.name
```

**Result**: All ad-level metrics are summed up to their parent campaigns.

#### Ad Set Rollup

Same logic as campaigns, but:
- Base case: Ad sets (level='adset')
- Recursive case: Map ads to ad sets

#### Ad Level (No Rollup)

For ad-level queries, no CTE is needed:
```sql
SELECT
  entity.id, entity.name,
  SUM(metric_facts.revenue) AS revenue,
  SUM(metric_facts.spend) AS spend
FROM metric_facts
JOIN entities AS entity ON entity.id = metric_facts.entity_id
WHERE entity.level = 'ad' AND entity.workspace_id = :workspace_id
GROUP BY entity.id, entity.name
```

### Drill-Down Navigation

**Campaigns List** → Click row → **Ad Sets for Campaign** → Click row → **Ads for Ad Set**

**Key mechanism**:
1. `entity.level` field determines if "View" button is shown
2. `onClick` prop passes entity ID to parent page
3. Parent page navigates to child route with `parent_id` param
4. API fetches children filtered by `parent_id`

**Example**:
```javascript
// EntityRow.jsx
const hasChildren = row.level !== 'ad'; // Ads are leaf nodes

{hasChildren && onClick ? (
  <button onClick={() => onClick(row.id)}>View</button>
) : (
  <span>—</span>
)}
```

---

## Testing

### Backend Tests (`test_entity_performance.py`)

**Setup**:
```python
def _seed_entity_performance(db, workspace_id):
    # Create connection
    # Create 2 campaigns, 4 ad sets, 8 ads
    # Create 30 days of metric facts at ad level
```

**Test Coverage**:
1. ✅ Authentication (401 if not logged in)
2. ✅ Basic campaign listing (200, returns rows)
3. ✅ Pagination (page 1 vs page 2, total count)
4. ✅ Status filter (active vs paused)
5. ✅ Platform filter (meta vs google)
6. ✅ Sorting (by revenue, by ROAS asc)
7. ✅ Ad set listing (drill-down from campaign)
8. ✅ Empty state (no entities match filters)
9. ✅ Invalid entity level (400 error)

**Run Tests**:
```bash
cd backend
pytest app/tests/test_entity_performance.py -v
```

### Frontend Tests (TODO)

**Adapter Tests** (`campaignsAdapter.test.js`):
- ✅ formatCurrency: $1,234.56
- ✅ formatRatio: 2.45×
- ✅ formatPercentage: 4.2%
- ✅ relativeTime: "2h ago"
- ✅ alignTrend: Fill missing days with zeros
- ✅ adaptEntityPerformance: View model contract

**Component Tests** (TODO):
- Filter changes call API with correct params
- Clicking campaign navigates to detail
- Sorting updates order
- Pagination updates page

---

## Known Limitations

### 1. Authentication Context

**Issue**: Workspace ID is temporarily hardcoded in pages.

**Current**:
```javascript
const workspaceId = "1e72698a-1f6c-4abb-9b99-48dba86508ce"; // Hardcoded
```

**Future**:
```javascript
const { workspaceId } = useAuth(); // From context
```

**Impact**: Not production-ready (multi-tenant support broken).

### 2. Custom Date Range

**Issue**: UI has "Custom" timeframe button, but backend integration is missing.

**Current**: Selecting "Custom" sends `timeframe=custom` but no date pickers.

**Future**: Add date range picker, send `date_start` and `date_end` params.

### 3. Active Rules Module

**Issue**: Not implemented (out of scope for this task).

**Status**: Placeholder components exist, but no backend integration.

### 4. Frontend Tests

**Issue**: Adapter and component tests not yet written.

**Status**: Infrastructure in place (Vitest, Testing Library), tests TODO.

### 5. Relative Time Server-Side

**Issue**: Relative time ("2h ago") computed client-side, not server-side.

**Impact**: Time shown depends on user's local clock (potential inconsistency).

**Future**: Backend could return relative time strings if needed.

---

## Future Enhancements

### 1. Named Entity Filtering

**Feature**: Filter by specific campaign/ad set/ad name.

**DSL Extension**: Add `entity_name` filter to query.

**Example**: "Show me 'Summer Sale' campaign performance"

### 2. Bulk Actions

**Feature**: Select multiple rows, pause/activate/archive in bulk.

**UI**: Checkboxes on rows, action buttons in toolbar.

**Backend**: Batch update endpoint.

### 3. Export to CSV

**Feature**: Export table data to CSV file.

**UI**: "Download" button in toolbar.

**Backend**: CSV serialization endpoint.

### 4. Real-Time Updates

**Feature**: Auto-refresh table when new data is ingested.

**Tech**: WebSocket or polling.

**Impact**: Live dashboard experience.

### 5. Advanced Sorting

**Feature**: Multi-column sorting (e.g., "Sort by ROAS, then by Spend").

**UI**: Shift+Click to add secondary sort.

**Backend**: Multiple `sort_by` params.

### 6. Saved Views

**Feature**: Save filter/sort presets (e.g., "Top Meta Campaigns").

**UI**: "Save View" button, dropdown to load.

**Backend**: User preferences table.

### 7. Comparison Mode

**Feature**: Compare two campaigns side-by-side.

**UI**: Select two rows, click "Compare".

**Backend**: Fetch both entities, return diff.

---

## Changelog

- **2025-10-12**: Initial documentation created
- **2025-10-12**: Added three-level drill-down (campaigns → ad sets → ads)
- **2025-10-12**: Fixed PostgreSQL grouping error in `_apply_sort()`
- **2025-10-12**: Removed `created_at` field (not in Entity model)
- **2025-10-12**: Added ad-level query support (no hierarchy CTE)

---

## References

- **Backend Router**: `backend/app/routers/entity_performance.py`
- **Backend Tests**: `backend/app/tests/test_entity_performance.py`
- **Schemas**: `backend/app/schemas.py` (EntityPerformanceResponse)
- **Hierarchy CTEs**: `backend/app/dsl/hierarchy.py`
- **Frontend API Client**: `ui/lib/campaignsApiClient.js`
- **Frontend Adapter**: `ui/lib/campaignsAdapter.js`
- **Campaigns Page**: `ui/app/(dashboard)/campaigns/page.jsx`
- **Campaign Detail**: `ui/app/(dashboard)/campaigns/[id]/page.jsx`
- **Ad Set Detail**: `ui/app/(dashboard)/campaigns/[id]/[adsetId]/page.jsx`
- **Build Log**: `docs/metricx_BUILD_LOG.md`

---

**END OF DOCUMENT**

