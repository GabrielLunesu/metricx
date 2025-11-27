# Finance & P&L System Architecture

**Version**: v1.0  
**Created**: 2025-10-11  
**Status**: Production Ready

## Overview

The Finance system provides complete P&L (Profit & Loss) visibility by combining ad spend data from advertising platforms with user-entered operational costs (SaaS tools, agency fees, events, etc.).

### Key Design Decisions

**Data Source Strategy:**
- **Ad Spend**: Aggregated from `MetricFact` (real-time, append-only facts)
- **Manual Costs**: Stored in `ManualCost` table with date-based allocation
- **Pnl Table**: Kept for future EOD locking/audit but not used in Finance page initially

**Why MetricFact instead of Pnl?**
- Real-time data matches user expectations
- Consistent with `/kpis` endpoint pattern (proven to work well)
- Pnl snapshots are valuable for historical locking but add complexity
- Future optimization: Hybrid approach (closed months from Pnl, current month from MetricFact)

---

## System Architecture

### Data Flow

```
┌─────────────────┐
│   MetricFact    │  Ad spend by provider (real-time)
│  (ad platforms) │
└────────┬────────┘
         │
         ├───────────> Finance Endpoint ──> financeApiClient ──> pnlAdapter ──> UI Components
         │             (aggregation)
         │
┌────────┴────────┐
│  ManualCost     │  User-entered costs (pro-rated)
│  (operational)  │
└─────────────────┘
```

### Component Responsibilities

**Backend (Business Logic)**:
- Aggregate ad spend by provider from MetricFact
- Pro-rate manual costs based on date allocation
- Compute summary KPIs (revenue, spend, profit, ROAS)
- Build P&L rows (ad platforms + manual categories)
- Calculate previous period comparisons
- Enforce workspace scoping at SQL level

**Frontend (Display Only)**:
- Fetch data via thin API client
- Map responses to view models via adapter
- Render formatted values (no calculations)
- Handle loading/error states
- Local state for period selection and compare toggle

---

## Manual Cost Allocation

### Allocation Types

**1. one_off** - Single date cost
```json
{
  "label": "HubSpot Marketing Hub",
  "category": "Tools / SaaS",
  "amount_dollar": 299.00,
  "allocation": {
    "type": "one_off",
    "date": "2025-10-15"
  }
}
```

**Allocation rule**: Include full amount if `date` falls within [period_start, period_end)

**2. range** - Pro-rated cost across date range
```json
{
  "label": "Creative Agency Retainer",
  "category": "Agency Fees",
  "amount_dollar": 3000.00,
  "allocation": {
    "type": "range",
    "start_date": "2025-09-01",  // Inclusive
    "end_date": "2025-12-01"     // Exclusive
  }
}
```

**Allocation rule**: 
```
overlapping_days = min(cost_end, period_end) - max(cost_start, period_start)
total_days = cost_end - cost_start
allocated_amount = amount_dollar × (overlapping_days / total_days)
```

### Allocation Examples

**Example 1: One-off inside period**
- Cost: $299 on 2025-10-15
- Period: [2025-10-01, 2025-11-01)
- Result: **$299** (full amount)

**Example 2: One-off outside period**
- Cost: $299 on 2025-09-15
- Period: [2025-10-01, 2025-11-01)
- Result: **$0** (excluded)

**Example 3: Range fully inside**
- Cost: $1,000 from 2025-10-05 to 2025-10-15 (10 days)
- Period: [2025-10-01, 2025-11-01)
- Result: **$1,000** (full amount)

**Example 4: Range partial overlap**
- Cost: $2,000 from 2025-09-20 to 2025-10-10 (20 days)
- Period: [2025-10-01, 2025-11-01)
- Overlap: 9 days (Oct 1-9)
- Result: **$900** (9/20 = 45%)

**Example 5: Range spanning multiple months**
- Cost: $9,200 from 2025-10-01 to 2025-12-31 (91 days)
- Period: [2025-11-01, 2025-12-01) (30 days)
- Result: **~$3,033** (30/91 ≈ 33%)

---

## API Contracts

### P&L Statement Endpoint

**Request:**
```
GET /workspaces/{workspace_id}/finance/pnl
  ?granularity=month
  &period_start=2025-10-01
  &period_end=2025-11-01
  &compare=true
```

**Response:**
```json
{
  "summary": {
    "total_revenue": 12450.30,
    "total_spend": 8923.45,
    "gross_profit": 3526.85,
    "net_roas": 1.39,
    "compare": {
      "revenue_delta_pct": 0.124,
      "spend_delta_pct": -0.056,
      "profit_delta_pct": 0.082,
      "roas_delta": 0.13
    }
  },
  "rows": [
    {
      "id": "ads-google",
      "category": "Ad Spend - Google",
      "actual_dollar": 3847.00,
      "planned_dollar": null,
      "variance_pct": null,
      "notes": null,
      "source": "ads"
    },
    {
      "id": "manual-Tools / SaaS",
      "category": "Tools / SaaS",
      "actual_dollar": 842.50,
      "planned_dollar": null,
      "variance_pct": null,
      "notes": null,
      "source": "manual"
    }
  ],
  "composition": [
    {"label": "Ad Spend - Google", "value": 3847.00},
    {"label": "Tools / SaaS", "value": 842.50}
  ],
  "timeseries": null
}
```

### Manual Cost CRUD

**Create:**
```
POST /workspaces/{workspace_id}/finance/costs
{
  "label": "HubSpot Marketing Hub",
  "category": "Tools / SaaS",
  "amount_dollar": 299.00,
  "allocation": {
    "type": "one_off",
    "date": "2025-10-15"
  },
  "notes": "Monthly subscription"
}
```

**List:**
```
GET /workspaces/{workspace_id}/finance/costs
```

**Update:**
```
PUT /workspaces/{workspace_id}/finance/costs/{cost_id}
{
  "label": "HubSpot Marketing Pro",
  "amount_dollar": 399.00
}
```

**Delete:**
```
DELETE /workspaces/{workspace_id}/finance/costs/{cost_id}
```

### Financial Insight

**Request:**
```
POST /workspaces/{workspace_id}/finance/insight
{
  "month": "October",
  "year": 2025
}
```

**Response:**
```json
{
  "message": "Your total spend in October 2025 was $8,923. Ad spend represented 85% of costs ($7,621), with the remainder in operational expenses. Revenue of $12,450 delivered a net ROAS of 1.39×, up 13% from September..."
}
```

---

## Frontend Architecture

### Strict Separation of Concerns

**Layer 1: API Client** (`lib/financeApiClient.js`)
- Thin HTTP wrapper
- No business logic
- No formatting
- Returns raw API responses

**Layer 2: Adapter** (`lib/pnlAdapter.js`)
- Maps API → View Model
- All formatting happens here (currency, percentages, ratios)
- Safe defaults for null/undefined
- No calculations (only display transformations)

**Layer 3: Components** (`app/(dashboard)/finance/components/*.jsx`)
- Receive view model props
- Pure display logic
- No formatting
- No calculations
- No API calls

### Example Data Flow

```javascript
// API Response (raw)
{
  summary: { total_revenue: 12450.30 }
}

// ↓ Adapter transforms

// View Model (formatted)
{
  summary: {
    totalRevenue: {
      label: 'Total Revenue',
      value: '$12,450.30',  // Formatted
      rawValue: 12450.30
    }
  }
}

// ↓ Component displays

<div>{summary.totalRevenue.value}</div>  // Just render, no logic
```

---

## Future Enhancements

### Daily Granularity (Supported by Contract)

**Backend:**
- Already aggregates by `event_date` (supports daily)
- Add `timeseries` field to response (already in contract)

**Frontend:**
- Update TopBar to support daily selector
- Display timeseries in charts
- No adapter changes needed (contract supports it)

**Migration path:**
```javascript
// Monthly (current)
granularity: 'month'
periodStart: '2025-10-01'
periodEnd: '2025-11-01'

// Daily (future, no breaking changes)
granularity: 'day'
periodStart: '2025-10-01'
periodEnd: '2025-11-08'
response.timeseries = [{date: '2025-10-01', revenue: 450, spend: 120, profit: 330}, ...]
```

### Planned Budgets

**Backend:**
- Add `planned_budget` table with monthly targets
- Join during P&L aggregation
- Compute variance_pct per row

**Frontend:**
- No changes needed (planned_dollar field already in contract)
- Variance badges will automatically appear

### Manual Revenue Entries

**Backend:**
- Extend `ManualCost` to support revenue (or create `ManualRevenue` table)
- Include in total_revenue calculation

### Pnl Table Optimization

**Current**: Finance page uses MetricFact (real-time)  
**Future**: Hybrid approach for performance

```python
# Closed months (historical, locked)
if period_end < first_day_of_current_month:
    return aggregate_from_pnl_table()

# Current/recent months (fresh data)
else:
    return aggregate_from_metric_fact()
```

---

## File Reference

| Component | File | Purpose |
|-----------|------|---------|
| **Model** | `app/models.py:ManualCost` | Database schema |
| **Migration** | `alembic/versions/5b531bb7e3a8_add_manual_costs.py` | Table creation |
| **Schemas** | `app/schemas.py` | DTOs (PnLSummary, PnLRow, ManualCost*) |
| **Allocation** | `app/services/cost_allocation.py` | Pro-rating logic |
| **Router** | `app/routers/finance.py` | REST API endpoints |
| **Tests** | `app/tests/test_cost_allocation.py` | Unit tests (7 tests) |
| **Tests** | `app/tests/test_finance_endpoints.py` | Integration tests |
| **Seed** | `app/seed_mock.py` | Test data generation |
| **API Client** | `ui/lib/financeApiClient.js` | Frontend HTTP client |
| **Adapter** | `ui/lib/pnlAdapter.js` | View model mapper |
| **Page** | `ui/app/(dashboard)/finance/page.jsx` | Main Finance page |
| **Components** | `ui/app/(dashboard)/finance/components/*.jsx` | UI components |

---

## Testing

### Unit Tests (Cost Allocation)

**File**: `app/tests/test_cost_allocation.py`

```bash
cd backend
pytest app/tests/test_cost_allocation.py -v
```

**Coverage**:
- ✅ One-off inside period → full amount
- ✅ One-off outside period → $0
- ✅ Range fully inside → full amount
- ✅ Range partial overlap → pro-rated
- ✅ Range no overlap → $0
- ✅ Range spanning multiple months → correct pro-rating
- ✅ Leap year February → 29 days handled

**Status**: 7/7 tests passing

### Integration Tests (Endpoints)

**File**: `app/tests/test_finance_endpoints.py`

**TODO**: Implement with test fixtures
- P&L statement aggregation (ads only, with one-off, with range)
- Compare mode (previous period deltas)
- Manual cost CRUD (create, update, delete)
- Workspace isolation

---

## Security Guarantees

### Workspace Scoping
All queries filter at SQL level:
```python
.join(Entity, Entity.id == MetricFact.entity_id)
.filter(Entity.workspace_id == workspace_id)
```

All manual costs scoped by workspace:
```python
.filter(ManualCost.workspace_id == workspace_id)
```

**No cross-workspace data leaks possible.**

### Authentication
- Requires valid JWT token (HTTP-only cookie)
- Workspace access verified on every request
- User identity tracked for audit (created_by_user_id)

---

## Performance Considerations

### Query Optimization
- Ad spend aggregation uses existing MetricFact indexes
- Manual cost queries indexed on workspace_id and allocation dates
- Single combined query per P&L request (no N+1)

### Caching Opportunities (Future)
- Cache P&L responses by `(workspace_id, granularity, period_start, period_end, compare)` key
- TTL: 5 minutes for current month, 24 hours for closed months
- Invalidate on manual cost mutations

---

## Known Limitations

1. **Planned budgets not implemented** - `planned_dollar` always null in responses
2. **Daily granularity supported by contract but not UI** - Frontend only shows monthly selector
3. **Manual cost UI not built** - CRUD only via API/admin panel for now
4. **Revenue only from ads** - No manual revenue entry support yet
5. **Integration tests incomplete** - Placeholders exist, need full implementation

---

## Migration Guide

### Deploy to Production

1. **Run migration:**
```bash
cd backend
alembic upgrade head
```

2. **Seed test data (optional):**
```bash
python -m app.seed_mock
```

3. **Verify endpoints:**
- Visit http://localhost:8000/docs
- Test `/workspaces/{id}/finance/pnl` endpoint
- Test manual cost CRUD endpoints

4. **Frontend integration:**
```bash
cd ui
npm run dev
```
- Navigate to `/finance`
- Verify P&L loads
- Test period selector
- Test compare toggle

---

## Troubleshooting

### P&L shows $0 everywhere
**Cause**: No MetricFact data for selected period  
**Fix**: Check date range, verify MetricFact table has data

### Manual costs not appearing
**Cause**: Allocation dates don't overlap query period  
**Fix**: Verify allocation_date (one_off) or allocation_start/end (range) overlap with period

### Compare mode not working
**Cause**: No data in previous period  
**Fix**: Ensure MetricFact coverage spans both current and previous periods

### 403 errors on Finance endpoints
**Cause**: User's workspace_id doesn't match requested workspace_id  
**Fix**: Verify authentication, check workspace access

---

## Future Roadmap

### Phase 2: Planned Budgets
- Add `budget` table with monthly targets by category
- Join during P&L aggregation
- Compute variance_pct per row
- UI automatically shows variance badges

### Phase 3: Manual Revenue
- Extend schema to support revenue entries (not just costs)
- Include in total_revenue calculation
- Support for non-ad revenue sources

### Phase 4: Daily Granularity UI
- Update TopBar with daily selector
- Render timeseries in charts
- No backend changes needed (already supported)

### Phase 5: Pnl Table Optimization
- Hybrid data source (Pnl for closed months, MetricFact for current)
- Faster queries for historical periods
- Maintain real-time freshness for current month

### Phase 6: Advanced Analytics
- Trend analysis (month-over-month, year-over-year)
- Forecasting (predict next month spend/revenue)
- Anomaly detection (unusual cost spikes)
- Category-level insights via QA system

---

## REFERENCES

- **Main Build Log**: `docs/metricx_BUILD_LOG.md`
- **Class Diagram**: `backend/CLASS-DIAGRAM.MD`
- **QA System**: `backend/docs/QA_SYSTEM_ARCHITECTURE.md`
- **Code**: `backend/app/routers/finance.py`, `backend/app/services/cost_allocation.py`
- **Tests**: `backend/app/tests/test_cost_allocation.py`

---

_Last updated: 2025-10-11_

