# Tech-Spec: Analytics Page Transformation & Unified Graph Engine

**Created:** 2025-12-15
**Status:** Ready for Development
**Scope:** Full production-ready implementation
**Estimated Impact:** 43% code reduction, 18 new metrics exposed, unified architecture

---

## Overview

### Problem Statement

The current analytics page is underwhelming and fails to deliver real value to merchants:

1. **Bug:** Campaign spend doesn't respect selected timeframe (shows lifetime spend)
2. **Hidden Data:** 22 metrics stored in database, only 4 exposed in UI
3. **Chart Fragmentation:** 3 charting libraries (Recharts, Chart.js, SVG) with ~900 lines of duplicate code
4. **No Segmentation:** Can't break down by device, placement, region, demographics
5. **No Comparison:** Can't compare periods, campaigns, or platforms side-by-side
6. **Dead Code:** ~1,500 lines of unused components polluting the codebase
7. **API Sprawl:** 8 routers with overlapping functionality

### Solution

Build a **Unified Graph Engine** that powers dashboard, analytics, and all future pages with:

1. **Single charting abstraction** - One component, multiple chart types
2. **Full metric exposure** - All 22 metrics available to users
3. **Deep segmentation** - Device, placement, region, demographic breakdowns
4. **Comparison mode** - Period vs period, campaign vs campaign
5. **Clean codebase** - Delete all dead code, consolidate duplicates
6. **Unified API** - Single data abstraction layer

### Scope

**In Scope:**
- Fix campaign spend timeframe bug
- Build UnifiedGraphEngine component
- Expose all 22 metrics in UI
- Add segmentation capabilities (device, placement, region)
- Add comparison mode
- Delete all dead/duplicate code
- Consolidate API endpoints
- Handle all connection permutations (Google only, Meta only, both, neither)
- Production-ready error handling and loading states

**Out of Scope (Phase 2+):**
- Drag-drop dashboard builder
- Custom saved reports
- Cohort analysis
- Product-level analytics
- Creative performance gallery
- Geographic heatmaps

---

## Context for Development

### Codebase Patterns

**Frontend:**
- Next.js 14 with App Router
- shadcn/ui for all components (MANDATORY)
- Recharts for charting (standardize on this)
- Server-side filtering (frontend is "dumb")
- Unified data fetching via `/dashboard/unified` endpoint

**Backend:**
- FastAPI with SQLAlchemy
- PostgreSQL with metric_snapshots table (15-min granularity)
- Campaign-level aggregation for KPIs
- Shopify-first revenue strategy when connected

**Data Flow:**
```
metric_snapshots (15-min) → API aggregation → Series-based response → Recharts render
```

### Files to Reference

**KEEP & ENHANCE (Foundation):**
```
ui/components/charts/MetricxChart.jsx          # 150 lines - THE graph engine foundation
ui/components/ui/chart.jsx                     # 306 lines - shadcn Recharts wrapper
backend/app/routers/analytics.py               # 816 lines - Best API pattern
```

**DELETE (Dead Code):**
```
# Orphaned landing components
ui/components/landing/HeroSection.jsx
ui/components/landing/HeroMinimal.jsx
ui/components/landing/FeaturesSection.jsx
ui/components/landing/PricingSection.jsx
ui/components/landing/CTASection.jsx
ui/components/landing/FooterSection.jsx
ui/components/landing/BentoGridSection.jsx
ui/components/landing/ROISection.jsx
ui/components/landing/ProblemSection.jsx
ui/components/landing/FeaturesDetailSection.jsx

# Duplicate dashboard components (keep Unified/Module versions)
ui/app/(dashboard)/dashboard/components/AiInsightsPanel.jsx
ui/app/(dashboard)/dashboard/components/AttributionCard.jsx
ui/app/(dashboard)/dashboard/components/MoneyPulseChart.jsx
ui/app/(dashboard)/dashboard/components/PlatformSpendMix.jsx
ui/app/(dashboard)/dashboard/components/LiveAttributionFeed.jsx
ui/app/(dashboard)/dashboard/components/HomeKpiStrip.jsx
ui/app/(dashboard)/dashboard/components/KpiStrip.jsx
ui/app/(dashboard)/dashboard/components/KpiStripUnified.jsx
ui/app/(dashboard)/dashboard/components/VisitorsChartCard.jsx

# Chart duplicates
ui/app/(dashboard)/analytics/components/AnalyticsChart.jsx      # 365 lines - Chart.js duplicate
ui/app/(dashboard)/analytics/components/TrendChart.jsx          # 85 lines - Stub

# Duplicate KPI components (consolidate to KpiCardsModule)
ui/components/KPIStatCard.jsx
ui/components/analytics/KPICard.jsx
ui/app/(dashboard)/dashboard/components/KPICard.jsx
```

**REFACTOR:**
```
ui/app/(dashboard)/analytics/components/AnalyticsGraphEngine.jsx  # Good but needs MetricxChart
ui/app/(dashboard)/analytics/components/AnalyticsMainChart.jsx    # 504 lines → split
ui/app/(dashboard)/dashboard/components/BlendedMetricsModule.jsx  # Use MetricxChart
ui/app/(dashboard)/finance/components/ChartsSection.jsx           # Chart.js → Recharts
```

### Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Charting Library | Recharts only | React-first, composable, shadcn compatible |
| Chart Engine | Extend MetricxChart | Already 150 lines, clean abstraction |
| API Pattern | Series-based responses | Easy to render multi-line charts |
| Data Source | metric_snapshots | 15-min granularity, proper DISTINCT ON |
| Segmentation | New API parameters | Server-side filtering, not client |
| State Management | URL params + React state | Shareable URLs, fast navigation |

---

## Implementation Plan

### Phase 1: Cleanup & Foundation (Days 1-3)

#### Task 1.1: Delete Dead Code
**Files to delete:** 21 files (~1,500 lines)

```bash
# Landing components (orphaned)
rm ui/components/landing/HeroSection.jsx
rm ui/components/landing/HeroMinimal.jsx
rm ui/components/landing/FeaturesSection.jsx
rm ui/components/landing/PricingSection.jsx
rm ui/components/landing/CTASection.jsx
rm ui/components/landing/FooterSection.jsx
rm ui/components/landing/BentoGridSection.jsx
rm ui/components/landing/ROISection.jsx
rm ui/components/landing/ProblemSection.jsx
rm ui/components/landing/FeaturesDetailSection.jsx

# Dashboard duplicates
rm ui/app/(dashboard)/dashboard/components/AiInsightsPanel.jsx
rm ui/app/(dashboard)/dashboard/components/AttributionCard.jsx
rm ui/app/(dashboard)/dashboard/components/MoneyPulseChart.jsx
rm ui/app/(dashboard)/dashboard/components/PlatformSpendMix.jsx
rm ui/app/(dashboard)/dashboard/components/LiveAttributionFeed.jsx
rm ui/app/(dashboard)/dashboard/components/HomeKpiStrip.jsx
rm ui/app/(dashboard)/dashboard/components/KpiStrip.jsx
rm ui/app/(dashboard)/dashboard/components/KpiStripUnified.jsx
rm ui/app/(dashboard)/dashboard/components/VisitorsChartCard.jsx

# Chart duplicates
rm ui/app/(dashboard)/analytics/components/AnalyticsChart.jsx
rm ui/app/(dashboard)/analytics/components/TrendChart.jsx
```

**Verification:** Run `npm run build` to ensure no broken imports.

#### Task 1.2: Create Unified Graph Engine
**New file:** `ui/components/charts/UnifiedGraphEngine.jsx`

```jsx
/**
 * UnifiedGraphEngine - Single chart component for all Metricx visualizations
 *
 * Supports: Area, Line, Bar, Composed charts
 * Used by: Dashboard, Analytics, Finance, Campaigns pages
 *
 * @param {Object} props
 * @param {Array} props.series - Array of {key, label, color, data: [{date, value}]}
 * @param {string} props.type - "area" | "line" | "bar" | "composed"
 * @param {Array} props.metrics - Metrics to show: ["revenue", "spend", "roas"]
 * @param {string} props.xAxisKey - Key for x-axis (default: "date")
 * @param {Object} props.formatters - {value: fn, axis: fn, tooltip: fn}
 * @param {boolean} props.showLegend - Show legend (default: true for multi-series)
 * @param {boolean} props.showTooltip - Show tooltip (default: true)
 * @param {string} props.height - Chart height (default: "400px")
 * @param {Object} props.emptyState - {icon, title, description} for no data
 */
```

**Features:**
- Wraps Recharts with consistent styling
- Auto-detects chart type from data shape
- Handles loading, error, empty states
- Responsive by default
- Currency/percentage formatting built-in
- Gradient fills with platform colors
- Dual Y-axis support for different scales

#### Task 1.3: Create Chart Formatting Library
**New file:** `ui/lib/chartFormatting.js`

```javascript
/**
 * Unified chart formatting utilities
 * Consolidates 4 duplicate implementations
 */

export const formatCurrency = (value, currency = 'USD') => {...}
export const formatPercentage = (value, decimals = 1) => {...}
export const formatNumber = (value, compact = false) => {...}
export const formatDateForAxis = (date, granularity) => {...}
export const formatTimestamp = (ts, includeTime = false) => {...}
export const getMetricFormatter = (metricKey) => {...}

// Platform colors (consistent everywhere)
export const PLATFORM_COLORS = {
  google: '#4285F4',
  meta: '#0668E1',
  tiktok: '#00F2EA',
  shopify: '#96BF48',
  direct: '#6B7280',
  organic: '#10B981',
  unknown: '#9CA3AF'
}

// Metric definitions
export const METRIC_CONFIG = {
  revenue: { label: 'Revenue', format: 'currency', color: '#10B981' },
  spend: { label: 'Spend', format: 'currency', color: '#EF4444' },
  roas: { label: 'ROAS', format: 'multiplier', color: '#8B5CF6' },
  profit: { label: 'Profit', format: 'currency', color: '#059669' },
  poas: { label: 'POAS', format: 'multiplier', color: '#7C3AED' },
  conversions: { label: 'Conversions', format: 'number', color: '#F59E0B' },
  impressions: { label: 'Impressions', format: 'compact', color: '#6366F1' },
  clicks: { label: 'Clicks', format: 'compact', color: '#3B82F6' },
  cpc: { label: 'CPC', format: 'currency', color: '#EC4899' },
  cpm: { label: 'CPM', format: 'currency', color: '#F97316' },
  ctr: { label: 'CTR', format: 'percentage', color: '#14B8A6' },
  cvr: { label: 'CVR', format: 'percentage', color: '#84CC16' },
  aov: { label: 'AOV', format: 'currency', color: '#A855F7' },
  cpl: { label: 'CPL', format: 'currency', color: '#F43F5E' },
  cpi: { label: 'CPI', format: 'currency', color: '#FB923C' },
  cpp: { label: 'CPP', format: 'currency', color: '#E11D48' },
  leads: { label: 'Leads', format: 'number', color: '#0EA5E9' },
  installs: { label: 'Installs', format: 'number', color: '#22D3EE' },
  purchases: { label: 'Purchases', format: 'number', color: '#4ADE80' },
  visitors: { label: 'Visitors', format: 'compact', color: '#A78BFA' },
  arpv: { label: 'ARPV', format: 'currency', color: '#C084FC' },
  cpa: { label: 'CPA', format: 'currency', color: '#FB7185' }
}
```

---

### Phase 2: Fix Bugs & API Enhancement (Days 4-6)

#### Task 2.1: Fix Campaign Spend Timeframe Bug
**File:** `backend/app/routers/entity_performance.py`

**Problem:** `/entity-performance/list` doesn't filter by date range for spend calculation.

**Fix:**
```python
# Current (broken):
SELECT SUM(spend) FROM metric_snapshots WHERE entity_id = :id
# No date filter!

# Fixed:
SELECT SUM(spend) FROM metric_snapshots
WHERE entity_id = :id
  AND metrics_date >= :start_date
  AND metrics_date <= :end_date
```

**Also update:** Campaign selector in analytics page to pass date range.

#### Task 2.2: Add Segmentation Parameters to API
**File:** `backend/app/routers/analytics.py`

**New query parameters:**
```python
@router.get("/analytics/chart")
async def get_chart_data(
    workspace_id: UUID,
    timeframe: str = "last_7_days",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    platforms: Optional[str] = None,        # Existing
    campaign_ids: Optional[str] = None,     # Existing
    group_by: str = "total",                # Existing
    # NEW SEGMENTATION PARAMETERS:
    segment_by: Optional[str] = None,       # "device" | "placement" | "region" | "age" | "gender"
    devices: Optional[str] = None,          # "mobile,desktop,tablet"
    placements: Optional[str] = None,       # "feed,stories,reels,search"
    regions: Optional[str] = None,          # "US,UK,CA"
):
```

**Implementation notes:**
- Segmentation requires fetching additional dimensions from Google/Meta APIs
- Store in new `metric_snapshot_segments` table or as JSON in snapshots
- Phase 2+ feature - prepare API now, implement data collection later

#### Task 2.3: Add Comparison Endpoint
**File:** `backend/app/routers/analytics.py`

**New endpoint:**
```python
@router.get("/analytics/compare")
async def compare_data(
    workspace_id: UUID,
    compare_type: str,              # "period" | "campaign" | "platform"

    # For period comparison:
    period_a_start: Optional[date] = None,
    period_a_end: Optional[date] = None,
    period_b_start: Optional[date] = None,
    period_b_end: Optional[date] = None,

    # For campaign comparison:
    campaign_a_id: Optional[UUID] = None,
    campaign_b_id: Optional[UUID] = None,

    # For platform comparison:
    platform_a: Optional[str] = None,   # "google"
    platform_b: Optional[str] = None,   # "meta"

    metrics: str = "revenue,spend,roas"  # Comma-separated
):
    """
    Returns side-by-side comparison data.

    Response:
    {
      "comparison_type": "period",
      "metrics": ["revenue", "spend", "roas"],
      "a": {
        "label": "Dec 1-7",
        "values": {"revenue": 12500, "spend": 3200, "roas": 3.9}
      },
      "b": {
        "label": "Nov 24-30",
        "values": {"revenue": 11200, "spend": 3400, "roas": 3.3}
      },
      "delta": {
        "revenue": {"value": 1300, "pct": 11.6},
        "spend": {"value": -200, "pct": -5.9},
        "roas": {"value": 0.6, "pct": 18.2}
      }
    }
    """
```

---

### Phase 3: Analytics Page Rebuild (Days 7-12)

#### Task 3.1: New Analytics Page Layout
**File:** `ui/app/(dashboard)/analytics/page.jsx`

```
┌─────────────────────────────────────────────────────────────────────┐
│  HEADER: Analytics                                    [Date Range ▼]│
├─────────────────────────────────────────────────────────────────────┤
│  FILTERS BAR:                                                       │
│  [Platforms ▼] [Campaigns ▼] [Segment By ▼] [Compare ▼]            │
├─────────────────────────────────────────────────────────────────────┤
│  METRIC SELECTOR (scrollable):                                      │
│  [Revenue ✓] [Spend ✓] [ROAS] [Profit] [POAS] [Conv] [CTR] [CPC]...│
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                                                               │ │
│  │                   UNIFIED GRAPH ENGINE                        │ │
│  │                                                               │ │
│  │   Multi-line chart with selected metrics                      │ │
│  │   Supports: Revenue + Spend on left Y-axis                    │ │
│  │            ROAS on right Y-axis (different scale)             │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  KPI STRIP (selected metrics as cards):                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ Revenue  │ │  Spend   │ │   ROAS   │ │  Profit  │ ...          │
│  │ $45,230  │ │ $12,450  │ │   3.6x   │ │ $18,200  │              │
│  │  +12% ▲  │ │  +8% ▲   │ │  +0.4 ▲  │ │  +15% ▲  │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
├─────────────────────────────────────────────────────────────────────┤
│  BREAKDOWN TABLE (sortable):                                        │
│                                                                     │
│  Entity        │ Revenue  │ Spend   │ ROAS │ Conv │ CTR  │ CPC    │
│  ──────────────┼──────────┼─────────┼──────┼──────┼──────┼────────│
│  Google Ads    │ $25,400  │ $6,200  │ 4.1x │ 234  │ 3.2% │ $1.24  │
│  └ Campaign A  │ $12,300  │ $2,800  │ 4.4x │ 112  │ 3.5% │ $1.18  │
│  └ Campaign B  │ $8,100   │ $2,100  │ 3.9x │ 78   │ 2.9% │ $1.32  │
│  Meta Ads      │ $19,830  │ $6,250  │ 3.2x │ 189  │ 2.8% │ $1.56  │
│  └ Campaign C  │ $11,200  │ $3,400  │ 3.3x │ 98   │ 2.6% │ $1.62  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### Task 3.2: Metric Selector Component
**New file:** `ui/app/(dashboard)/analytics/components/MetricSelector.jsx`

```jsx
/**
 * Horizontal scrollable metric selector
 *
 * Features:
 * - Shows all 22 available metrics as toggleable chips
 * - Groups by category: Revenue, Cost, Performance, Engagement
 * - Max 4 metrics selected at once (chart readability)
 * - Persists selection to URL params
 */
```

**Metric categories:**
```javascript
const METRIC_GROUPS = {
  'Revenue & Profit': ['revenue', 'profit', 'poas', 'aov', 'arpv'],
  'Cost & Efficiency': ['spend', 'cpc', 'cpm', 'cpl', 'cpi', 'cpp', 'cpa'],
  'Performance': ['roas', 'conversions', 'purchases', 'leads', 'installs'],
  'Engagement': ['impressions', 'clicks', 'ctr', 'cvr', 'visitors']
}
```

#### Task 3.3: Segmentation Panel Component
**New file:** `ui/app/(dashboard)/analytics/components/SegmentationPanel.jsx`

```jsx
/**
 * Segmentation controls for breaking down data
 *
 * Segments available:
 * - Platform (Google, Meta, TikTok)
 * - Campaign
 * - Device (Desktop, Mobile, Tablet) - requires Google data
 * - Placement (Feed, Stories, Reels, Search) - requires Meta data
 * - Region (top 10 countries)
 * - Demographics (age, gender) - Phase 2
 */
```

#### Task 3.4: Comparison Mode Component
**New file:** `ui/app/(dashboard)/analytics/components/ComparisonMode.jsx`

```jsx
/**
 * Comparison controls and visualization
 *
 * Comparison types:
 * - Period vs Period: "This week vs Last week"
 * - Campaign vs Campaign: Side-by-side performance
 * - Platform vs Platform: Google vs Meta
 *
 * Visual output:
 * - Split chart (two lines, clearly labeled)
 * - Delta indicators (% change)
 * - Winner badges
 */
```

#### Task 3.5: Breakdown Table Component
**New file:** `ui/app/(dashboard)/analytics/components/BreakdownTable.jsx`

```jsx
/**
 * Hierarchical performance table with drill-down
 *
 * Features:
 * - Expandable rows (Platform → Campaign → Ad Set → Ad)
 * - Sortable columns (click header to sort)
 * - Sparkline trends in rows
 * - Color-coded performance (green/red for good/bad)
 * - Export to CSV
 */
```

---

### Phase 4: Dashboard Integration (Days 13-15)

#### Task 4.1: Update Dashboard to Use UnifiedGraphEngine
**File:** `ui/app/(dashboard)/dashboard/page.jsx`

Replace `BlendedMetricsModule` chart section with `UnifiedGraphEngine`:

```jsx
<UnifiedGraphEngine
  series={chartData}
  type="area"
  metrics={['revenue', 'spend']}
  height="300px"
  showLegend={connectedPlatforms.length > 1}
  formatters={{
    value: formatCurrency,
    tooltip: (v, metric) => `${METRIC_CONFIG[metric].label}: ${formatCurrency(v)}`
  }}
/>
```

#### Task 4.2: Expose More Metrics in Dashboard KPIs
**File:** `ui/app/(dashboard)/dashboard/components/KpiCardsModule.jsx`

Current: Revenue, ROAS, Spend, Conversions
Add: Profit, AOV, CPC, CTR (as secondary/expandable)

```jsx
// Primary KPIs (always visible)
const PRIMARY_KPIS = ['revenue', 'roas', 'spend', 'conversions'];

// Secondary KPIs (expandable section)
const SECONDARY_KPIS = ['profit', 'poas', 'aov', 'cpc', 'ctr', 'cvr'];
```

#### Task 4.3: Connection State Empty States
Ensure all components gracefully handle:

| State | UI Behavior |
|-------|-------------|
| No connections | "Connect your ad accounts to see data" CTA |
| Google only | Show Google data, hide Meta-specific features |
| Meta only | Show Meta data, hide Google-specific features |
| Both connected | Full functionality, platform selector enabled |
| Shopify connected | Show "Revenue (Shopify)" label, enable attribution |
| Syncing | Show skeleton + "Syncing..." indicator |
| Sync error | Show last good data + error banner |

---

### Phase 5: API Consolidation (Days 16-18)

#### Task 5.1: Deprecate Redundant Endpoints
**Mark for deprecation:**
```python
# backend/app/routers/dashboard_kpis.py - entire file
# Duplicate of logic in dashboard.py

# backend/app/routers/qa.py
POST /qa              # deprecated=True already
GET /qa/jobs/{job_id} # deprecated=True already
POST /qa/stream       # deprecated=True already
```

#### Task 5.2: Unify Data Layer
**New file:** `backend/app/services/metric_aggregation_service.py`

```python
"""
Unified Metric Aggregation Service

Single source of truth for all metric queries.
All routers (analytics, dashboard, kpis, entity_performance) use this service.
"""

class MetricAggregationService:
    async def aggregate(
        self,
        workspace_id: UUID,
        entity_ids: Optional[List[UUID]] = None,
        time_range: Tuple[date, date],
        granularity: Literal["hour", "day", "total"] = "day",
        grouping: Literal["total", "platform", "campaign", "entity"] = "total",
        metrics: List[str] = ["spend", "revenue", "conversions", "roas"],
        include_sparklines: bool = False,
        include_comparison: bool = False,
        comparison_range: Optional[Tuple[date, date]] = None,
    ) -> AggregationResult:
        """
        Returns aggregated metrics with optional sparklines and period comparison.

        Used by:
        - GET /analytics/chart
        - GET /workspaces/{id}/dashboard/unified
        - POST /workspaces/{id}/kpis
        - GET /entity-performance/list
        """
```

#### Task 5.3: Simplify Unified Dashboard Endpoint
**File:** `backend/app/routers/dashboard.py`

Refactor `/dashboard/unified` to use `MetricAggregationService`:

```python
@router.get("/workspaces/{workspace_id}/dashboard/unified")
async def get_unified_dashboard(
    workspace_id: UUID,
    timeframe: str = "last_7_days",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Use unified service instead of inline SQL
    service = MetricAggregationService(db)

    kpis = await service.aggregate(
        workspace_id=workspace_id,
        time_range=parse_timeframe(timeframe),
        granularity="total",
        metrics=["revenue", "spend", "roas", "conversions"],
        include_sparklines=True,
        include_comparison=True,
    )

    chart_data = await service.aggregate(
        workspace_id=workspace_id,
        time_range=parse_timeframe(timeframe),
        granularity="day",  # or "hour" for today/yesterday
        grouping="platform",
        metrics=["revenue", "spend", "roas"],
    )

    # ... rest of response assembly
```

---

### Phase 6: Testing & Polish (Days 19-21)

#### Task 6.1: Component Tests
```
ui/components/charts/UnifiedGraphEngine.test.jsx
ui/app/(dashboard)/analytics/components/MetricSelector.test.jsx
ui/app/(dashboard)/analytics/components/SegmentationPanel.test.jsx
ui/app/(dashboard)/analytics/components/ComparisonMode.test.jsx
ui/app/(dashboard)/analytics/components/BreakdownTable.test.jsx
```

#### Task 6.2: API Tests
```
backend/app/tests/test_analytics_chart.py
backend/app/tests/test_analytics_compare.py
backend/app/tests/test_metric_aggregation_service.py
```

#### Task 6.3: Integration Tests
- All connection permutations (Google only, Meta only, both, neither)
- All timeframes (today, yesterday, 7d, 30d, custom)
- All chart types (area, line, bar)
- All segmentation options
- Comparison mode edge cases

---

## Acceptance Criteria

### Must Have (P0)

- [ ] **AC1:** Campaign spend in selector respects selected date range
- [ ] **AC2:** UnifiedGraphEngine renders area, line, and bar charts
- [ ] **AC3:** All 22 metrics available in metric selector
- [ ] **AC4:** Platform breakdown chart shows Google and Meta separately
- [ ] **AC5:** KPI cards show period-over-period comparison (delta %)
- [ ] **AC6:** Page works correctly with only Google connected
- [ ] **AC7:** Page works correctly with only Meta connected
- [ ] **AC8:** Page works correctly with both platforms connected
- [ ] **AC9:** Page shows appropriate empty state with no connections
- [ ] **AC10:** All dead code files deleted (21 files)
- [ ] **AC11:** Chart.js removed from analytics page (use Recharts only)
- [ ] **AC12:** Loading skeletons shown while data fetches
- [ ] **AC13:** Error states shown with retry option

### Should Have (P1)

- [ ] **AC14:** Comparison mode works for period vs period
- [ ] **AC15:** Breakdown table is sortable by any column
- [ ] **AC16:** Breakdown table supports drill-down (campaign → ad set)
- [ ] **AC17:** URL params persist filter state (shareable URLs)
- [ ] **AC18:** MetricAggregationService consolidates all data queries

### Nice to Have (P2)

- [ ] **AC19:** Device segmentation works (requires Google API enhancement)
- [ ] **AC20:** Placement segmentation works (requires Meta API enhancement)
- [ ] **AC21:** Export table to CSV
- [ ] **AC22:** Chart type selector (area/line/bar toggle)

---

## Additional Context

### Dependencies

**Frontend:**
- recharts: ^2.10.0 (already installed)
- @radix-ui/react-* (shadcn dependencies, already installed)

**Backend:**
- No new dependencies required

**Remove:**
- chart.js: Remove if no longer used after migration
- react-chartjs-2: Remove if no longer used

### Testing Strategy

**Unit Tests:**
- Chart formatting functions (100% coverage)
- Metric calculations (100% coverage)
- Date range parsing (100% coverage)

**Component Tests:**
- UnifiedGraphEngine with mock data
- MetricSelector state management
- Empty/loading/error states

**Integration Tests:**
- Full page render with API mocks
- All connection permutations
- Real database queries (staging)

**E2E Tests (optional):**
- Full user flow: connect account → view analytics → filter → compare

### Observability

**Logging:**
```python
# Add to analytics.py
logger.info(f"Analytics chart request", extra={
    "workspace_id": workspace_id,
    "timeframe": timeframe,
    "platforms": platforms,
    "group_by": group_by,
    "duration_ms": duration
})
```

**Metrics:**
- `analytics_chart_request_duration_seconds` (histogram)
- `analytics_chart_request_total` (counter by status)
- `analytics_metrics_selected` (counter by metric name)

**Alerts:**
- Chart endpoint p95 > 2s
- Error rate > 5%

### Notes

1. **Shopify Revenue Priority:** When Shopify is connected, always use Shopify order revenue, not platform conversion_value. The `data_source` field indicates which is being used.

2. **Campaign-Level Aggregation:** KPIs aggregate from campaign-level entities only, not ads. This ensures PMax and Shopping campaigns report accurate totals.

3. **Timezone Handling:** All date filtering uses `metrics_date` (account timezone), not `captured_at` (UTC sync time).

4. **Chart Granularity:** Auto-detect based on date range:
   - Today/Yesterday: 15-min or hourly
   - 2-7 days: Daily
   - 8+ days: Daily (no weekly aggregation)

5. **Series Response Format:** Always return data in series format for multi-line support:
   ```json
   {
     "series": [
       {"key": "google", "label": "Google Ads", "color": "#4285F4", "data": [...]},
       {"key": "meta", "label": "Meta Ads", "color": "#0668E1", "data": [...]}
     ]
   }
   ```

---

**Tech-Spec Complete!**

Saved to: `/docs/sprint-artifacts/tech-spec-analytics-transformation.md`
