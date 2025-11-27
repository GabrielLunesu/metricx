# Analytics Page Implementation Plan

**Date**: 2025-10-09  
**Purpose**: Rebuild Analytics page with real backend data and dynamic filtering

---

## 📊 Current State Analysis

### Backend Endpoints Available

Based on `metricx_BUILD_LOG.md` and `QA_SYSTEM_ARCHITECTURE.md`:

1. **`POST /workspaces/{workspace_id}/kpis`** ✅ EXISTS
   - **Purpose**: Aggregate KPI metrics with time ranges, sparklines, breakdowns
   - **Features**:
     - Time range support (last_n_days or start/end dates)
     - Previous period comparison (`compare_to_previous`)
     - Sparkline data (`sparkline: true`)
     - **Provider filter** (google/meta/tiktok/other)
     - Level filter (campaign/adset/ad)
     - Active status filter
     - Breakdown support
   - **Returns**: Array of KpiValue objects with summary, previous, delta_pct, sparkline

2. **`POST /qa`** ✅ EXISTS
   - **Purpose**: Natural language query with DSL translation
   - **Features**:
     - Query types: metrics, providers, entities
     - DSL v2.1.4 with provider breakdown support
     - Context-aware follow-ups
   - **Use case**: metricx Insight widget

3. **Providers Query via DSL** ✅ EXISTS (via /qa endpoint)
   - **Query type**: `"providers"`
   - **Returns**: List of distinct ad platforms in workspace
   - **Example**: `{"providers": ["google", "meta", "tiktok"]}`

4. **Entities Query via DSL** ✅ EXISTS (via /qa endpoint)
   - **Query type**: `"entities"`
   - **Filters**: level, status, entity_ids
   - **Returns**: List of campaigns/adsets/ads
   - **Example**: `{"entities": [{"name": "Summer Sale", "level": "campaign", "status": "active"}]}`

---

## 🎯 Analytics Page Requirements

### UI Components Breakdown

```
┌─────────────────────────────────────────────────────────────┐
│ ANALYTICS PAGE                                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ [All] [Meta] [Google] [TikTok]    [7d] [30d] [Custom] ⬅️ Filters│
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ KPI CARDS (Revenue, Spend, ROAS, Conversions)               │
│ - Blended from all providers by default                     │
│ - Filterable by selected provider                           │
│ - Uses selected timeframe                                   │
├─────────────────────────────────────────────────────────────┤
│ CHART SECTION                                                │
│ - Sparkline data per metric                                 │
│ - Dropdown: [Revenue ▼] [By Provider ▼]                     │
│   Options: Revenue, Spend, ROAS, Clicks, etc.              │
│   Grouping: By Provider, By Campaign                        │
│ - Filterable by selected provider from top                  │
├─────────────────────────────────────────────────────────────┤
│ PLATFORM BREAKDOWN                                           │
│ - Shows revenue per provider                                │
│ - Filtered by selected timeframe                            │
│ - If provider selected, shows that provider only            │
├─────────────────────────────────────────────────────────────┤
│ ADDITIONAL METRICS (CTR, CPC, CPA, Conversion Rate)         │
│ - Same filtering as KPI cards                               │
├─────────────────────────────────────────────────────────────┤
│ metricx INSIGHT                                               │
│ - Uses /qa endpoint                                         │
│ - Dynamic question based on selected filters                │
│ - Example: "Give me a breakdown of Meta for the last 30d"  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔌 Backend Endpoints Needed

### ✅ Endpoints We Already Have

1. **KPI Data**: `POST /workspaces/{workspace_id}/kpis`
2. **Natural Language Queries**: `POST /qa`

### 🆕 Endpoints We Need to Create

#### 1. **Get Available Providers** 
**Endpoint**: `GET /workspaces/{workspace_id}/providers`

**Purpose**: Fetch distinct ad platforms that have data in this workspace

**Implementation**: Simple query on MetricFact
```python
@router.get("/{workspace_id}/providers")
def get_workspace_providers(workspace_id: str, db: Session = Depends(get_db)):
    """Get distinct providers with data in this workspace."""
    providers = (
        db.query(models.MetricFact.provider)
        .join(models.Entity, models.Entity.id == models.MetricFact.entity_id)
        .filter(models.Entity.workspace_id == workspace_id)
        .distinct()
        .all()
    )
    return {"providers": [p[0].value for p in providers if p[0]]}
```

**Response**:
```json
{
  "providers": ["google", "meta", "tiktok"]
}
```

#### 2. **Get Workspace Campaigns** (for chart dropdown)
**Endpoint**: `GET /workspaces/{workspace_id}/campaigns`

**Purpose**: List all campaigns for dropdown filter in chart section

**Query params**:
- `provider` (optional): Filter by provider
- `status` (optional): Filter by status (default: active)

**Implementation**:
```python
@router.get("/{workspace_id}/campaigns")
def get_workspace_campaigns(
    workspace_id: str,
    provider: Optional[str] = None,
    status: str = "active",
    db: Session = Depends(get_db)
):
    """Get campaigns for dropdown filtering."""
    query = (
        db.query(models.Entity)
        .filter(models.Entity.workspace_id == workspace_id)
        .filter(models.Entity.level == "campaign")
    )
    if provider:
        # Get campaigns that have facts from this provider
        query = query.join(models.MetricFact).filter(models.MetricFact.provider == provider)
    if status:
        query = query.filter(models.Entity.status == status)
    
    campaigns = query.distinct().all()
    return {
        "campaigns": [
            {"id": str(c.id), "name": c.name, "status": c.status.value}
            for c in campaigns
        ]
    }
```

**Response**:
```json
{
  "campaigns": [
    {"id": "uuid-1", "name": "Summer Sale", "status": "active"},
    {"id": "uuid-2", "name": "Winter Promo", "status": "active"}
  ]
}
```

---

## 📝 Implementation Steps

### Phase 1: Backend Endpoints (30 minutes)

1. **Create providers endpoint** (`backend/app/routers/workspaces.py`)
   - Add `GET /workspaces/{workspace_id}/providers`
   - Simple distinct query on MetricFact.provider

2. **Create campaigns endpoint** (`backend/app/routers/workspaces.py`)
   - Add `GET /workspaces/{workspace_id}/campaigns`
   - Support provider and status filters

3. **Update main.py** to include new endpoints

### Phase 2: Frontend API Client (15 minutes)

**File**: `ui/lib/api.js`

Add new functions:
```javascript
export async function fetchWorkspaceProviders({ workspaceId }) {
  const res = await fetch(`${BASE}/workspaces/${workspaceId}/providers`, {
    credentials: "include"
  });
  if (!res.ok) throw new Error('Failed to fetch providers');
  return res.json();
}

export async function fetchWorkspaceCampaigns({ workspaceId, provider = null, status = 'active' }) {
  const params = new URLSearchParams();
  if (provider) params.set('provider', provider);
  if (status) params.set('status', status);
  
  const res = await fetch(`${BASE}/workspaces/${workspaceId}/campaigns?${params}`, {
    credentials: "include"
  });
  if (!res.ok) throw new Error('Failed to fetch campaigns');
  return res.json();
}
```

### Phase 3: Analytics Page State Management (20 minutes)

**File**: `ui/app/(dashboard)/analytics/page.jsx`

State structure:
```javascript
const [workspaceId, setWorkspaceId] = useState(null);
const [selectedProvider, setSelectedProvider] = useState('all'); // 'all', 'meta', 'google', 'tiktok'
const [availableProviders, setAvailableProviders] = useState([]);
const [selectedTimeframe, setSelectedTimeframe] = useState('30d'); // '7d', '30d', 'custom'
const [rangeDays, setRangeDays] = useState(30);
const [selectedMetric, setSelectedMetric] = useState('revenue'); // For chart
const [selectedGrouping, setSelectedGrouping] = useState('provider'); // 'provider', 'campaign'
const [campaigns, setCampaigns] = useState([]);
const [selectedCampaign, setSelectedCampaign] = useState(null); // For campaign grouping
```

### Phase 4: Top Filters Component (30 minutes)

**File**: `ui/app/(dashboard)/analytics/components/TopFilters.jsx`

Features:
- Fetch available providers on mount
- Show provider buttons (All + each available provider)
- Timeframe selector (7d, 30d, Custom)
- Custom date picker
- Pass selected filters to parent

### Phase 5: KPI Cards Component (45 minutes)

**File**: `ui/app/(dashboard)/analytics/components/AnalyticsKpiGrid.jsx`

Features:
- Fetch KPI data using `fetchWorkspaceKpis`
- Apply provider filter if selected
- Apply timeframe from top filters
- Display 4 main KPIs: Revenue, Spend, ROAS, Conversions
- Show loading states
- Auto-refresh when filters change

API Call:
```javascript
fetchWorkspaceKpis({
  workspaceId,
  metrics: ['revenue', 'spend', 'roas', 'conversions'],
  lastNDays: rangeDays,
  provider: selectedProvider === 'all' ? null : selectedProvider,
  compareToPrevious: false, // Commented out for now
  sparkline: false // Don't need sparklines for KPI cards
});
```

### Phase 6: Chart Section Component (60 minutes)

**File**: `ui/app/(dashboard)/analytics/components/AnalyticsChart.jsx`

Features:
- Metric dropdown (Revenue, Spend, ROAS, Clicks, etc.)
- Grouping dropdown (By Provider, By Campaign)
- If "By Campaign" selected, show campaign dropdown
- Fetch sparkline data for selected metric
- Display Chart.js line chart
- Apply filters from top

**API Call - By Provider**:
```javascript
fetchWorkspaceKpis({
  workspaceId,
  metrics: [selectedMetric],
  lastNDays: rangeDays,
  sparkline: true,
  breakdown: 'provider', // Group by provider
  provider: selectedProvider === 'all' ? null : selectedProvider
});
```

**API Call - By Campaign**:
```javascript
fetchWorkspaceKpis({
  workspaceId,
  metrics: [selectedMetric],
  lastNDays: rangeDays,
  sparkline: true,
  breakdown: 'campaign',
  provider: selectedProvider === 'all' ? null : selectedProvider,
  filters: selectedCampaign ? { entity_ids: [selectedCampaign] } : {}
});
```

### Phase 7: Platform Breakdown Component (30 minutes)

**File**: `ui/app/(dashboard)/analytics/components/PlatformBreakdown.jsx`

Features:
- Fetch revenue breakdown by provider
- Show horizontal bars with percentages
- Apply timeframe filter
- If specific provider selected, show only that provider

API Call:
```javascript
fetchWorkspaceKpis({
  workspaceId,
  metrics: ['revenue'],
  lastNDays: rangeDays,
  breakdown: 'provider',
  provider: selectedProvider === 'all' ? null : selectedProvider
});
```

### Phase 8: Additional Metrics Component (30 minutes)

**File**: `ui/app/(dashboard)/analytics/components/AdditionalMetrics.jsx`

Features:
- Display CTR, CPC, CPA, Conversion Rate
- Same filtering as KPI cards
- Glass card styling

API Call:
```javascript
fetchWorkspaceKpis({
  workspaceId,
  metrics: ['ctr', 'cpc', 'cpa', 'cvr'],
  lastNDays: rangeDays,
  provider: selectedProvider === 'all' ? null : selectedProvider
});
```

### Phase 9: metricx Insight Component (30 minutes)

**File**: `ui/app/(dashboard)/analytics/components/metricxInsight.jsx`

Features:
- Dynamic question generation based on selected filters
- Call /qa endpoint
- Display AI response
- Loading state

**Question Generation Logic**:
```javascript
const generateQuestion = () => {
  const providerText = selectedProvider === 'all' 
    ? 'all platforms' 
    : selectedProvider;
  
  const timeframeText = selectedTimeframe === '7d' 
    ? 'last 7 days' 
    : selectedTimeframe === '30d' 
    ? 'last 30 days' 
    : `from ${startDate} to ${endDate}`;
  
  return `Give me a breakdown of ${providerText} for the ${timeframeText}`;
};
```

API Call:
```javascript
fetchQA({
  workspaceId,
  question: generateQuestion()
});
```

---

## 🗂️ File Structure

```
ui/app/(dashboard)/analytics/
├── page.jsx                          # Main analytics page with state management
└── components/
    ├── TopFilters.jsx                # Provider + timeframe filters
    ├── AnalyticsKpiGrid.jsx          # 4 main KPI cards
    ├── AnalyticsChart.jsx            # Chart with metric/grouping dropdowns
    ├── PlatformBreakdown.jsx         # Revenue by provider
    ├── AdditionalMetrics.jsx         # CTR, CPC, CPA, CVR cards
    └── metricxInsight.jsx             # AI insight widget
```

---

## 🎨 Styling Guidelines

- Use glass morphism cards (`glass-card` class)
- Cyan accent color for active states
- Rounded corners (`rounded-3xl`)
- Smooth transitions and animations
- Loading spinners for async operations
- Skeleton loaders for initial load

---

## 🔄 Data Flow

```
User selects filter (Provider: Meta, Timeframe: 30d)
           ↓
State updates (selectedProvider, rangeDays)
           ↓
useEffect triggers in all components
           ↓
Each component fetches data with new filters
           ↓
           ├─→ KPI Cards: fetchWorkspaceKpis (provider=meta, lastNDays=30)
           ├─→ Chart: fetchWorkspaceKpis (provider=meta, lastNDays=30, sparkline=true)
           ├─→ Platform Breakdown: fetchWorkspaceKpis (breakdown=provider, provider=meta)
           ├─→ Additional Metrics: fetchWorkspaceKpis (provider=meta, metrics=[ctr,cpc,cpa,cvr])
           └─→ metricx Insight: fetchQA (question="breakdown of meta for last 30 days")
           ↓
Components re-render with new data
```

---

## ✅ Success Criteria

- [ ] Provider buttons show only providers with data
- [ ] KPI cards update when filters change
- [ ] Chart displays correct sparkline data
- [ ] Chart grouping switches between provider and campaign
- [ ] Platform breakdown reflects selected filters
- [ ] Additional metrics update with filters
- [ ] metricx Insight generates contextual questions
- [ ] All components have loading states
- [ ] Smooth transitions between filter changes
- [ ] Responsive layout

---

## 🚀 Estimated Timeline

- **Phase 1** (Backend): 30 minutes
- **Phase 2** (API Client): 15 minutes
- **Phase 3** (State Management): 20 minutes
- **Phase 4** (Top Filters): 30 minutes
- **Phase 5** (KPI Cards): 45 minutes
- **Phase 6** (Chart): 60 minutes
- **Phase 7** (Platform Breakdown): 30 minutes
- **Phase 8** (Additional Metrics): 30 minutes
- **Phase 9** (metricx Insight): 30 minutes

**Total**: ~4.5 hours

---

## 📋 Testing Checklist

### Before Starting
- [ ] Backend is running
- [ ] Database is seeded with mock data
- [ ] Multiple providers have data

### During Development
- [ ] Test with "All" providers selected
- [ ] Test with single provider selected
- [ ] Test timeframe changes
- [ ] Test chart metric dropdown
- [ ] Test chart grouping dropdown
- [ ] Test campaign filter when grouping by campaign

### Edge Cases
- [ ] Workspace with only 1 provider
- [ ] No data for selected timeframe
- [ ] Provider filter with no matching data
- [ ] Campaign filter with no data

---

## 🔗 API Endpoint Summary

| Endpoint | Method | Purpose | Exists? |
|----------|--------|---------|---------|
| `/workspaces/{id}/providers` | GET | Get available providers | ❌ CREATE |
| `/workspaces/{id}/campaigns` | GET | Get campaigns for dropdown | ❌ CREATE |
| `/workspaces/{id}/kpis` | POST | Get KPI data with filters | ✅ |
| `/qa` | POST | Natural language insights | ✅ |

---

## 💡 Key Implementation Notes

1. **Provider filter**: Use query param `provider` in KPI endpoint
2. **Breakdown**: Use `breakdown: 'provider'` or `breakdown: 'campaign'`
3. **Sparklines**: Set `sparkline: true` for chart data
4. **Timeframe**: Use `lastNDays` or `start/end` dates
5. **metricx Insight**: Generate question dynamically, don't hardcode
6. **Loading states**: Show skeletons during initial load, spinners during filter changes
7. **Error handling**: Display friendly error messages if API fails

---

## 🔮 Future Enhancements (Not in this phase)

- [ ] Compare vs last period (commented out for now)
- [ ] Normalize by spend (commented out for now)
- [ ] Export data functionality
- [ ] Save custom date ranges as presets
- [ ] Multiple metric selection for chart
- [ ] Drill-down from chart to campaign details

---

_This plan serves as the single source of truth for Analytics page implementation._

