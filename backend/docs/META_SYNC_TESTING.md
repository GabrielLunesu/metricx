# Meta Sync Testing Guide

**WHAT**: Guide for testing Meta Ads sync endpoints with real Meta accounts  
**WHY**: Validates end-to-end functionality before UI integration  
**WHERE USED**: Manual testing, QA validation, troubleshooting

---

## Prerequisites

1. **Meta Ad Account**: Must have at least one campaign (active or inactive)
2. **System User Token**: Stored in `backend/.env` as `META_ACCESS_TOKEN`
3. **Connection Created**: Meta connection record in database
4. **API Running**: Backend server on `http://localhost:8000`

---

## Step 1: Create Connection

If you don't have a Meta connection yet:

```bash
cd backend
source bin/activate
python3 -c "
from dotenv import load_dotenv
load_dotenv()
from app.database import SessionLocal
from app.models import Connection, ProviderEnum
from datetime import datetime
import uuid

db = SessionLocal()
workspace_id = 'YOUR_WORKSPACE_ID'  # Get from /auth/me

connection = Connection(
    id=uuid.uuid4(),
    workspace_id=uuid.UUID(workspace_id),
    provider=ProviderEnum.meta,
    external_account_id='act_1205956121112122',  # Your Meta account ID
    name='Meta Ads - Your Account Name',
    status='active',
    connected_at=datetime.utcnow()
)
db.add(connection)
db.commit()
print(f'Connection ID: {connection.id}')
db.close()
"
```

---

## Step 2: Sync Entities

**WHAT**: Fetches campaigns, adsets, and ads from Meta and creates Entity records

**Command**:
```bash
curl -X POST "http://localhost:8000/workspaces/{workspace_id}/connections/{connection_id}/sync-entities" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=YOUR_TOKEN"
```

**Expected Response**:
```json
{
  "success": true,
  "synced": {
    "campaigns_created": 1,
    "campaigns_updated": 0,
    "adsets_created": 1,
    "adsets_updated": 0,
    "ads_created": 1,
    "ads_updated": 0,
    "duration_seconds": 2.57
  },
  "errors": []
}
```

**What to Check**:
- ✅ `success: true` if any entities found
- ✅ `campaigns_created + campaigns_updated` > 0 if campaigns exist
- ✅ `errors: []` if no API failures
- ✅ Duration reasonable (< 30 seconds for typical accounts)

**Common Issues**:
- **0 campaigns**: Account has no campaigns (OK for new accounts)
- **401 error**: Token expired or invalid (check `.env`)
- **403 error**: Token lacks permissions (check Meta Business Manager)
- **429 error**: Rate limit hit (shouldn't happen with decorator)

---

## Step 3: Sync Metrics

**WHAT**: Fetches performance data (insights) for all ads and ingests into MetricFact table

**Command**:
```bash
curl -X POST "http://localhost:8000/workspaces/{workspace_id}/connections/{connection_id}/sync-metrics" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=YOUR_TOKEN" \
  -d '{}'
```

**Expected Response** (for new campaign):
```json
{
  "success": true,
  "synced": {
    "facts_ingested": 0,
    "facts_skipped": 0,
    "date_range": {
      "start": "2025-10-30",
      "end": "2025-10-30"
    },
    "ads_processed": 1,
    "duration_seconds": 1.02
  },
  "errors": []
}
```

**Expected Response** (for campaign with data):
```json
{
  "success": true,
  "synced": {
    "facts_ingested": 450,
    "facts_skipped": 0,
    "date_range": {
      "start": "2024-10-01",
      "end": "2024-10-31"
    },
    "ads_processed": 15,
    "duration_seconds": 245.7
  },
  "errors": []
}
```

**What to Check**:
- ✅ `success: true` if sync completed
- ✅ `facts_ingested` > 0 if campaign has historical data
- ✅ `date_range` shows correct backfill period (90 days max)
- ✅ `ads_processed` matches number of ads synced in Step 2
- ✅ `errors: []` if no API failures

**Common Issues**:
- **0 facts ingested**: Campaign has no historical data (OK for new campaigns)
- **"No ad entities found"**: Run entity sync first (Step 2)
- **Date range too short**: Check connection.connected_at date

---

## Step 4: Verify Data in Database

**Check Entities**:
```bash
psql $DATABASE_URL -c "
SELECT 
  level, 
  COUNT(*) as count,
  MIN(name) as sample_name
FROM entities 
WHERE connection_id = 'YOUR_CONNECTION_ID' 
GROUP BY level
ORDER BY level;
"
```

**Expected Output**:
```
level   | count | sample_name
--------+-------+------------------
campaign|     1 | New Leads ad
adset   |     1 | New Leads ad set
ad      |     1 | New Leads ad
```

**Check Metrics**:
```bash
psql $DATABASE_URL -c "
SELECT 
  event_date,
  COUNT(*) as fact_count,
  SUM(spend)::numeric(10,2) as total_spend,
  SUM(impressions) as total_impressions,
  SUM(clicks) as total_clicks
FROM metric_facts 
WHERE provider = 'meta'
GROUP BY event_date 
ORDER BY event_date DESC 
LIMIT 10;
"
```

**Expected Output** (if campaign has data):
```
event_date | fact_count | total_spend | total_impressions | total_clicks
-----------+------------+-------------+------------------+-------------
2025-10-30 |         24 |     125.50  |           12345  |         234
2025-10-29 |         24 |     98.75   |            9876 |         198
```

---

## Step 5: Test QA System

**Query Meta Data**:
```bash
curl -X POST "http://localhost:8000/qa/?workspace_id={workspace_id}" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=YOUR_TOKEN" \
  -d '{"question": "what was my Meta spend in the last 30 days?"}'
```

**Expected Response**:
```json
{
  "answer": "Your Meta spend in the last 30 days was $1,234.56.",
  "executed_dsl": {...},
  "data": {...}
}
```

---

## Real-World Test Results

**Test Date**: 2025-10-31  
**Meta Account**: `act_1205956121112122` (Gabriels portfolio)

### Entity Sync Test
- **Input**: 1 campaign ("New Leads ad"), 1 adset, 1 ad
- **Result**: ✅ Successfully synced all entities
- **Response**: `{"success": true, "synced": {"campaigns_created": 1, "adsets_created": 1, "ads_created": 1, ...}}`
- **Duration**: 2.57 seconds

### Metrics Sync Test
- **Input**: 1 ad (just published, no historical data)
- **Result**: ✅ Correctly handled empty account
- **Response**: `{"success": true, "synced": {"facts_ingested": 0, "ads_processed": 1, ...}}`
- **Duration**: 1.02 seconds
- **Date Range**: 2025-10-30 to 2025-10-30 (correctly calculated from connection date)

### Verification
- ✅ Entities created in database
- ✅ Hierarchy correct (campaign → adset → ad)
- ✅ Metrics sync ready for when campaign delivers data

---

## Troubleshooting

### Issue: "No campaigns found"
**Cause**: Meta account has no campaigns  
**Solution**: Create a test campaign in Meta Ads Manager, then re-run sync

### Issue: "Authentication failed" (401)
**Cause**: Token expired or invalid  
**Solution**: 
1. Check `backend/.env` has `META_ACCESS_TOKEN`
2. Verify token is valid: `python test_meta_api.py`
3. Generate new token if needed

### Issue: "Permission denied" (403)
**Cause**: Token lacks required permissions  
**Solution**: 
1. Check system user has `ads_read` permission
2. Verify ad account is assigned to system user in Business Manager

### Issue: "No ad entities found"
**Cause**: Entity sync not run yet  
**Solution**: Run entity sync first (Step 2)

### Issue: Migration error
**Cause**: Missing `created_at`/`updated_at` columns  
**Solution**: Run migration: `cd backend && ./bin/alembic upgrade head`

---

## Performance Expectations

### Entity Sync
- **Small account** (< 10 campaigns): < 5 seconds
- **Medium account** (10-50 campaigns): 5-30 seconds
- **Large account** (50+ campaigns): 30-120 seconds

### Metrics Sync
- **Small account** (1-10 ads): < 1 minute
- **Medium account** (10-50 ads): 1-10 minutes
- **Large account** (50+ ads): 10-60 minutes (90-day backfill)

**Note**: Metrics sync duration depends on:
- Number of ads
- Date range (90-day backfill = ~1300 API calls for 100 ads)
- Rate limiting (200 calls/hour = ~6.5 hours for full backfill)

---

## Next Steps After Testing

1. **UI Integration**: Add sync buttons to Dashboard/Campaigns/Settings pages
2. **Data Validation**: Compare Meta UI numbers vs metricx QA system (±5%)
3. **Automated Sync**: Implement scheduler for daily/hourly syncs (Phase 3)

---

## References

- **Setup Guide**: `docs/meta-ads-lib/META_API_SETUP_GUIDE.md`
- **Status Document**: `docs/living-docs/META_INTEGRATION_STATUS.md`
- **Roadmap**: `backend/docs/roadmap/meta-ads-roadmap.md`
- **API Docs**: `http://localhost:8000/docs` (Swagger UI)

