# Meta Ads API Integration Roadmap

> **Prerequisites**: Before starting Phase 1, complete the setup guide at [META_API_SETUP_GUIDE.md](../../../docs/meta-ads-lib/META_API_SETUP_GUIDE.md)

## Phase 0: Meta API Access Setup (REQUIRED FIRST)
**Time**: 2-3 hours  
**Status**: 🔴 Not Started  
**Blocking**: All subsequent phases

### Deliverables:
- ✅ Meta Developer account created
- ✅ App created with Marketing API product
- ✅ Long-lived access token generated (60 days)
- ✅ Ad account access verified
- ✅ Python SDK installed and tested
- ✅ Test script confirms API connectivity

**See**: [Complete Setup Guide](../../../docs/meta-ads-lib/META_API_SETUP_GUIDE.md)

**Known Issue (2025)**: Test user creation temporarily disabled by Meta. Use personal account or system user instead (guide covers workarounds).

---

## Phase 1: Foundational fixes (pre‑Meta)
Purpose: Stabilize ingestion before external APIs.

### 1.1 Database performance and integrity
Time: 2–3 hours  
Priority: Critical

Tasks:
- Create migration adding indexes:
  - `idx_metric_facts_event_date` on `event_date`
  - `idx_metric_facts_entity_id` on `entity_id`
  - `idx_metric_facts_provider` on `provider`
  - Composite: `idx_metric_facts_workspace_date` on `(entity_id, event_date)` via join to `Entity.workspace_id`
- Add unique constraint on `natural_key`
- Track down migration files to review current schema

Deliverable: Performance baseline; duplicate prevention

### 1.2 Ingestion API design
Time: 4–6 hours  
Priority: Critical

Tasks:
- Add endpoint: `POST /workspaces/{workspace_id}/metrics/ingest`
- Schema:
```python
MetricFactCreate:
  - entity_id (UUID, optional - can infer from external_id + provider)
  - external_entity_id (string) # Meta's campaign/ad_id
  - provider (enum: meta)
  - level (enum: campaign/adset/ad)
  - event_at (datetime with timezone)
  - spend, impressions, clicks, etc. (base measures)
  - currency (string)
  - natural_key (computed: f"{external_entity_id}-{event_at.isoformat()}")
```
- UPSERT by `natural_key`
- Validate workspace membership
- Optional batch ingest for efficiency

Deliverable: API that can accept Meta data

### 1.3 Timezone handling
Time: 2–3 hours  
Priority: High

Tasks:
- make the system dynamic on user timezone/ ad account timezone
- Convert provider timestamps to timezone selected on ad account or user profile on ingest
- Store timezone in DB; selected timezone on display

Deliverable: Consistent timestamps

### 1.4 Error handling and logging
Time: 3–4 hours  
Priority: High

Tasks:
- Structured logging for ingest ops
- Failed record tracking
- Metrics: success/failure/incomplete
- Alerting for repeated failures

Deliverable: Observability and debugging path

---

## Phase 2: Meta API connection setup
Purpose: Authenticate and explore structure.

### 2.1 Meta credentials management
Time: 4–6 hours  
Priority: Critical

Tasks:
- Token table stores `access_token_enc`, `refresh_token_enc`, `expires_at`, `scope`
- Add Meta fields (if needed): ad account IDs
- Store Long‑Lived Access Tokens and set up a refresh flow
- Encryption for tokens
- Scopes: `ads_read`, `ads_management` (as needed)

Deliverable: Secure token management for Meta

### 2.2 Meta SDK integration
Time: 6–8 hours  
Priority: Critical

Tasks:
- Add `facebook-business` (and `cryptography`)
- Service class `MetaAdsClient`:
  - `get_campaigns(account_id)`
  - `get_adsets(campaign_id)`
  - `get_ads(adset_id)`
  - `get_insights(entity_id, time_range, level)`
- Handle rate limits
- Graceful 400/401/403 handling
- Use Insights API for performance metrics

Deliverable: Client capable of reading Meta data

### 2.3 Entity synchronization
Time: 6–8 hours  
Priority: High

Tasks:
- Endpoint: `POST /workspaces/{workspace_id}/connections/{connection_id}/sync-entities`
- Map Meta → local `entities`:
  - Campaigns → `Entity(level=campaign)`
  - Ad Sets → `Entity(level=adset, parent_id=campaign.id)`
  - Ads → `Entity(level=ad, parent_id=adset.id)`
- Store Meta IDs as `external_id`
- Avoid duplicates
- Reflect status changes (active/paused/deleted)

Deliverable: Ad structure in metricx

---

## Phase 3: Data ingestion pipeline
Purpose: Automated daily/hourly pulls.

### 3.1 Metrics fetcher service
Time: 8–10 hours  
Priority: Critical

Tasks:
- `MetaMetricsFetcher`:
  - `fetch_insights(entity_id, date_range, granularity='hour')`
  - Iterate accounts/campaigns/adsets/ads, fetch hour‑level data for last N days, handle pagination
- Map fields:
  - `spend` → spend
  - `impressions` → impressions
  - `clicks` → clicks
  - `actions` → parse into conversions/leads/purchases
  - `objective` → derive `goal`
- Manage missing/delayed/revised data

Deliverable: Service that fetches Meta metrics

### 3.2 Scheduler
Time: 4–6 hours  
Priority: High

Tasks:
- Endpoint: `POST /workspaces/{workspace_id}/connections/{connection_id}/sync`
- Trigger `MetaMetricsFetcher` and ingest results via Ingestion API
- Use `Fetch`/`Import` records for audit
- Run daily (or hourly with rate limits)

Deliverable: Automatable sync

### 3.3 Data validation
Time: 4–6 hours  
Priority: High

Tasks:
- Totals vs. drill‑down (day vs. hourly)
- Reconcile entity hierarchies
- Flag anomalies
- Admin alerts for discrepancies

Deliverable: Trusted data

---

## Phase 4: Query layer enhancements
Purpose: Support Meta‑level detail.

### 4.1 Hour/minute breakdown support
Time: 6–8 hours  
Priority: Medium

Tasks:
- Extend `UnifiedMetricService` to `breakdown_dimension`:
  - `hour`: `date_trunc('hour', event_at)`
  - `minute`: `date_trunc('minute', event_at)`
- UI controls for granularity
- Cache hourly aggregates
- Efficient `group_by`/index use

Deliverable: Hourly queries

### 4.2 Real‑time dashboard support
Time: 6–8 hours  
Priority: Medium

Tasks:
- Query latest hour(s)
- Incremental updates via API/SSE
- Show “last updated”
- Handle delayed data

Deliverable: Near‑real‑time dashboards

---

## Phase 5: Testing and validation
Purpose: Verify integrity before production.

### 5.1 Test data setup
Time: 4–6 hours  
Priority: High

Tasks:
- Seed from real Meta accounts
- Cover: active/paused/ended, multiple accounts/providers, gaps/duplicates, hierarchy variants
- E2E tests

Deliverable: Reliable test suite

### 5.2 Data quality checks
Time: 4–6 hours  
Priority: High

Tasks:
- Consistency across levels
- Alignment with Meta UI
- Completeness (esp. new entities)
- Auto‑validation on ingest

Deliverable: Quality monitoring

---

## Phase 6: Production hardening
Purpose: Handle scale and reliability.

### 6.1 Performance optimization
Time: 6–8 hours  
Priority: Medium

Tasks:
- Partition `metric_facts` by date
- Query speedups, caching, incremental aggregation, batch APIs
- Monitoring

Deliverable: Scales to larger data volumes

### 6.2 Error recovery
Time: 4–6 hours  
Priority: Medium

Tasks:
- Retries with backoff
- Backfill for gaps
- Resume on partial failures
- Dead letter handling

Deliverable: Resilient pipeline

### 6.3 Monitoring and alerting
Time: 4–6 hours  
Priority: Medium

Tasks:
- Ingest rate, failures, latency, freshness, capacity
- Dashboards and alerts

Deliverable: Visibility into health

---

## Implementation order summary

- **Week 0 (Day 1)**: Phase 0 (Meta API setup - REQUIRED FIRST)
  - Complete [META_API_SETUP_GUIDE.md](../../../docs/meta-ads-lib/META_API_SETUP_GUIDE.md)
  - Verify API connectivity with test script
  - Document credentials securely in `.env`
  
- **Week 1**: Phase 1 (foundational fixes), Phase 2.1–2.2 (auth/client)
- **Week 2**: Phase 2.3 (entities), Phase 3.1–3.2 (ingestion), Phase 5.1 (tests)
- **Week 3**: Phase 3.3 (validation), Phase 5.2 (quality), Phase 4.1 (hourly breakdowns)
- **Week 4**: Phase 4.2 (real‑time), Phase 6 (hardening)

---

## Critical decisions

- Hourly vs. daily: hourly preferred for Meta; add minute support in Phase 4
- Deduplication: UPSERT on `natural_key`
- Historical data: initial backfill → daily incremental syncs
- Rate limits: queuing/backoff; avoid parallel fetches
- Data retention: archive older rows optionally

---

## Success criteria

- Ingests Meta Ads data successfully
- Queries return correct values matching Meta UI (±5%)
- Supports hourly breakdowns
- Handles 1M+ rows efficiently
- Recovers from errors automatically
- Observability in place
- **User OAuth flow**: Click button → Modal → Meta login → Ad account selection → Connected

---

## Phase 7: OAuth User Flow (End Goal)
Purpose: Seamless user onboarding without manual token setup.

### 7.1 OAuth Backend Implementation
Time: 6-8 hours  
Priority: High (User Experience)

Tasks:
- Implement Meta OAuth 2.0 flow
- Endpoint: `GET /auth/meta/authorize` (redirects to Meta)
- Endpoint: `GET /auth/meta/callback` (handles OAuth callback)
- Store access_token, refresh_token in Token table (encrypted)
- Associate token with workspace
- Handle token refresh automatically

Deliverable: Backend OAuth endpoints

### 7.2 OAuth Frontend Implementation
Time: 4-6 hours  
Priority: High (User Experience)

Tasks:
- "Connect Meta Ads" button in UI
- Modal with Meta login flow
- Ad account selection UI (if user has multiple)
- Success/error states
- Token status indicator (connected/expired)

Deliverable: Complete user-facing OAuth flow

### 7.3 Multi-Account Support
Time: 2-3 hours  
Priority: Medium

Tasks:
- Allow users to connect multiple ad accounts
- UI to manage connected accounts
- Disconnect/reconnect functionality
- Per-account sync status

Deliverable: Multi-account management UI

**UX Flow**:
1. User clicks "Connect Meta Ads" button
2. Modal opens with "Login with Meta" button
3. Redirects to Meta OAuth consent screen
4. User grants permissions (ads_read, ads_management, read_insights)
5. Callback handler receives token
6. If multiple ad accounts: show selection UI
7. Store token(s) encrypted in database
8. Show "Connected ✅" status
9. Begin automatic sync

---

Should I proceed with Phase 1?