# Attribution UI Integration Plan

## Goal
Display attribution data in the existing dashboard so users can see which channels/campaigns drove their sales.

---

## Phase 1: Backend API Endpoints

### 1.1 Attribution Summary Endpoint
`GET /workspaces/{workspace_id}/attribution/summary`

Returns revenue breakdown by provider:
```json
{
  "total_attributed_revenue": 45000.00,
  "total_orders": 150,
  "by_provider": [
    {"provider": "meta", "revenue": 25000, "orders": 80, "percentage": 55.5},
    {"provider": "google", "revenue": 15000, "orders": 50, "percentage": 33.3},
    {"provider": "direct", "revenue": 3000, "orders": 15, "percentage": 6.7},
    {"provider": "organic", "revenue": 2000, "orders": 5, "percentage": 4.5}
  ],
  "by_confidence": [
    {"confidence": "high", "revenue": 35000, "orders": 100},
    {"confidence": "medium", "revenue": 8000, "orders": 40},
    {"confidence": "low", "revenue": 2000, "orders": 10}
  ]
}
```

### 1.2 Attributed Campaigns Endpoint
`GET /workspaces/{workspace_id}/attribution/campaigns`

Returns top campaigns by attributed revenue:
```json
{
  "campaigns": [
    {
      "entity_id": "uuid",
      "name": "Summer Sale 2025",
      "provider": "meta",
      "attributed_revenue": 12500,
      "attributed_orders": 45,
      "match_type": "utm_campaign",
      "confidence": "high"
    }
  ]
}
```

### 1.3 Attribution Trends Endpoint
`GET /workspaces/{workspace_id}/attribution/trends`

Returns daily attributed revenue for charting:
```json
{
  "trends": [
    {"date": "2025-11-25", "meta": 1200, "google": 800, "direct": 200},
    {"date": "2025-11-26", "meta": 1500, "google": 900, "direct": 150}
  ]
}
```

---

## Phase 2: Frontend Integration

### 2.1 Dashboard Page (`/dashboard`)
Add **Attribution Card** showing:
- Pie chart: Revenue by channel (Meta, Google, Direct, Organic)
- Quick stats: "55% of revenue from Meta Ads"

### 2.2 Analytics Page (`/analytics`)
Add **Attribution Section** with:
- Channel breakdown chart (stacked bar or pie)
- Top attributed campaigns table
- Confidence indicator (high/medium/low quality matches)
- Trend line showing attribution over time

### 2.3 Campaign Detail Page (`/campaigns/[id]`)
Add **Attribution Stats**:
- Attributed revenue for this campaign
- Number of attributed orders
- Match quality breakdown

---

## Implementation Order

1. **Backend: Create `/attribution` router** with 3 endpoints
2. **Frontend: Add API client functions** in `lib/api.js`
3. **Frontend: Attribution card** on Dashboard
4. **Frontend: Attribution section** on Analytics page

---

## File Changes

### Backend (new files):
- `backend/app/routers/attribution.py` - New router with endpoints
- `backend/app/schemas.py` - Add attribution response schemas

### Backend (modify):
- `backend/app/main.py` - Register attribution router

### Frontend (modify):
- `ui/lib/api.js` - Add attribution fetch functions
- `ui/app/(dashboard)/dashboard/page.jsx` - Add attribution card
- `ui/app/(dashboard)/analytics/page.jsx` - Add attribution section

### Frontend (new files):
- `ui/components/attribution/AttributionPieChart.jsx`
- `ui/components/attribution/AttributionTable.jsx`

---

## Estimated Effort
- Backend endpoints: ~1 hour
- Frontend integration: ~2 hours
- Total: ~3 hours

Ready to implement?
