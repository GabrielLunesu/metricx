# metricx Architecture Documentation

**Last Updated**: 2025-12-10
**Version**: 2.0.0

## Overview

metricx is an **ad analytics platform first** that helps merchants get the most out of their advertising spend. We aggregate data from multiple ad platforms (Meta Ads, Google Ads, TikTok) and optionally enhance it with e-commerce data (Shopify) for verified attribution.

### Strategic Focus: Ad Analytics First, Attribution Second

**Primary Features** (front and center):
- **Dashboard** → Ad performance, spend, ROAS (platform-reported), AI insights
- **Analytics** → Deep dive, campaign comparisons, trends
- **P&L** → Profitability view
- **Campaigns** → Manage and monitor

**Secondary Features** (enhancement layer):
- **Attribution** → Verification layer that enhances numbers when Shopify is connected
- **Pixel/UTM Config** → Lives in Settings/Integrations
- **Attribution Warnings** → Only surfaces when something's misconfigured

This focus means:
1. Onboarding = "Connect Meta + Google" → done
2. Dashboard shows value immediately (no empty boxes waiting for attribution)
3. Shopify users get verified data as a premium enhancement

### Core Capabilities

- **Multi-Platform Integration**: Meta Ads, Google Ads, TikTok, Shopify (optional)
- **AI-Powered Analytics**: Natural language query system (QA/Copilot)
- **Real-Time Metrics**: 15-minute sync frequency with intraday analytics
- **Financial Reporting**: P&L statements with manual cost tracking
- **Campaign Management**: Hierarchical entity management (Campaign → Ad Set → Ad → Creative)
- **Automated Sync**: ARQ-based background job processing
- **Attribution Engine**: Optional Shopify integration for verified order attribution

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              METRICX PLATFORM                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────────────┐
│    Frontend     │     │     Backend     │     │      Background Jobs        │
│   (Next.js)     │────▶│   (FastAPI)     │────▶│      (ARQ Workers)          │
│                 │     │                 │     │                             │
│ • Dashboard     │     │ • REST API      │     │ • 15-min metric sync        │
│ • Analytics     │     │ • Clerk Auth    │     │ • Daily attribution sync    │
│ • Copilot       │     │ • QA System     │     │ • Snapshot compaction       │
│ • Campaigns     │     │ • Unified API   │     │ • Shopify sync              │
└─────────────────┘     └────────┬────────┘     └─────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  PostgreSQL   │      │     Redis       │      │  External APIs  │
│               │      │                 │      │                 │
│ • Users       │      │ • ARQ queues    │      │ • Meta Ads      │
│ • Workspaces  │      │ • Job results   │      │ • Google Ads    │
│ • Entities    │      │ • JWKS cache    │      │ • Shopify       │
│ • Snapshots   │      │ • QA context    │      │ • Anthropic     │
│ • Attribution │      │                 │      │ • Clerk         │
└───────────────┘      └─────────────────┘      └─────────────────┘
```

---

## Recent Changes (December 2025)

### v2.0.0 - Major Platform Update

| Feature | Before | After |
|---------|--------|-------|
| **Authentication** | Custom JWT (HS256) | Clerk (RS256, JWKS) |
| **Dashboard** | 8+ API calls | 1 unified call |
| **Metric Storage** | Daily MetricFact | 15-min MetricSnapshot |
| **Background Jobs** | RQ/manual | ARQ workers + scheduler |
| **Observability** | Logging only | Sentry + structured logging |

**See Also:**
- [AUTH.md](./AUTH.md) - Clerk authentication details
- [UNIFIED_DASHBOARD.md](./UNIFIED_DASHBOARD.md) - Single-call dashboard API
- [METRIC_SNAPSHOTS.md](./METRIC_SNAPSHOTS.md) - 15-minute granularity metrics
- [ARQ_WORKERS.md](./ARQ_WORKERS.md) - Background job processing

---

## Backend Architecture

### Directory Structure

```
backend/app/
├── main.py                    # FastAPI app entrypoint, router registration
├── models.py                  # SQLAlchemy ORM models
├── schemas.py                 # Pydantic request/response schemas
├── database.py                # Database connection & session management
├── security.py                # Password hashing, legacy JWT
├── deps.py                    # Dependency injection (Clerk auth, settings)
├── state.py                   # Application-level singletons
├── telemetry.py               # Sentry integration, error tracking
│
├── routers/                   # API endpoints
│   ├── dashboard.py           # Unified dashboard API (NEW)
│   ├── clerk_webhooks.py      # Clerk user lifecycle webhooks (NEW)
│   ├── auth.py                # Legacy auth (deprecated)
│   ├── workspaces.py          # Workspace management
│   ├── connections.py         # Platform connection CRUD
│   ├── entities.py            # Entity CRUD
│   ├── kpis.py                # KPI aggregation
│   ├── finance.py             # P&L statements
│   ├── entity_performance.py  # Campaign/adset/ad performance
│   ├── qa.py                  # Natural language QA
│   ├── meta_sync.py           # Meta Ads entity/metrics sync
│   ├── google_sync.py         # Google Ads entity/metrics sync
│   ├── shopify_oauth.py       # Shopify OAuth flow
│   └── ...
│
├── services/                  # Business logic layer
│   ├── snapshot_sync_service.py   # 15-min metric syncing (NEW)
│   ├── sync_scheduler.py          # ARQ cron scheduler (NEW)
│   ├── qa_service.py              # QA orchestrator
│   ├── unified_metric_service.py  # Metric calculations
│   ├── meta_ads_client.py         # Meta API wrapper
│   ├── google_ads_client.py       # Google Ads API wrapper
│   ├── shopify_client.py          # Shopify API wrapper
│   └── ...
│
├── workers/                   # Background job processing (NEW)
│   ├── arq_worker.py          # Job definitions + WorkerSettings
│   ├── arq_enqueue.py         # Async enqueueing helper
│   └── start_arq_worker.py    # Worker entry point
│
├── dsl/                       # Domain-Specific Language for queries
│   ├── schema.py              # Pydantic models
│   ├── canonicalize.py        # Synonym mapping
│   ├── validate.py            # DSL validation
│   ├── executor.py            # Query execution
│   └── ...
│
├── nlp/                       # Natural Language Processing
│   ├── translator.py          # LLM → DSL translation
│   └── prompts.py             # System prompts
│
├── answer/                    # Answer Generation
│   ├── answer_builder.py      # LLM-based answers
│   └── formatters.py          # Display formatting
│
├── context/                   # Conversation Context
│   └── redis_context_manager.py
│
└── telemetry/                 # Observability
    ├── __init__.py            # Sentry setup, capture_exception
    └── logging.py             # Structured logging
```

### Key Backend Components

#### 1. **Unified Dashboard API** (`routers/dashboard.py`) - NEW

Single endpoint returning all dashboard data:
- **Before**: 8+ separate API calls
- **After**: 1 call to `/dashboard/unified`

**Data Included:**
- KPIs (revenue, ROAS, spend, conversions)
- Chart data with per-provider breakdown
- Top campaigns
- Spend mix
- Attribution summary/feed (if Shopify)

See [UNIFIED_DASHBOARD.md](./UNIFIED_DASHBOARD.md)

#### 2. **MetricSnapshot System** (`services/snapshot_sync_service.py`) - NEW

15-minute granularity metrics replacing daily MetricFact:
- Real-time intraday analytics
- Stop-loss rule support
- Automatic compaction (15-min → hourly after 2 days)
- Daily attribution re-fetch (last 7 days)

See [METRIC_SNAPSHOTS.md](./METRIC_SNAPSHOTS.md)

#### 3. **ARQ Workers** (`workers/arq_worker.py`) - NEW

Async background job processing:
- **Scheduler**: Runs cron jobs, enqueues work (single instance)
- **Workers**: Process jobs from queue (scalable)

Jobs:
- `process_sync_job` - Single connection sync
- `scheduled_realtime_sync` - Every 15 min
- `scheduled_attribution_sync` - Daily 3am
- `scheduled_compaction` - Daily 1am

See [ARQ_WORKERS.md](./ARQ_WORKERS.md)

#### 4. **Clerk Authentication** (`deps.py` + `routers/clerk_webhooks.py`) - NEW

Replaced custom JWT with Clerk:
- RS256 JWT validation via JWKS
- Webhook handlers for user lifecycle
- Repair endpoint for webhook failures

See [AUTH.md](./AUTH.md)

#### 5. **Unified Metric Service** (`services/unified_metric_service.py`)

Single source of truth for all metric calculations:
- Workspace-scoped security at SQL level
- Consistent aggregation logic
- Hierarchy-aware rollups
- Divide-by-zero guards

#### 6. **QA System** (`services/qa_service.py` + `dsl/` + `nlp/`)

Natural language → structured query → answer pipeline:
1. Retrieve context (Redis)
2. Canonicalize question
3. Translate to DSL via LLM
4. Validate & plan
5. Execute via UnifiedMetricService
6. Generate answer

See [QA_SYSTEM_ARCHITECTURE.md](./QA_SYSTEM_ARCHITECTURE.md)

---

## Frontend Architecture

### Directory Structure

```
ui/
├── app/                        # Next.js App Router
│   ├── layout.jsx              # Root layout + ClerkProvider
│   ├── middleware.ts           # Clerk route protection (NEW)
│   ├── sign-in/                # Clerk sign-in page (NEW)
│   ├── sign-up/                # Clerk sign-up page (NEW)
│   ├── (dashboard)/            # Dashboard route group
│   │   ├── layout.jsx          # Dashboard shell
│   │   ├── dashboard/          # Dashboard page
│   │   │   └── components/     # Unified components (NEW)
│   │   │       ├── KpiStripUnified.jsx
│   │   │       ├── MoneyPulseChartUnified.jsx
│   │   │       ├── TopCampaignsUnified.jsx
│   │   │       ├── SpendMixUnified.jsx
│   │   │       ├── AttributionCardUnified.jsx
│   │   │       └── LiveAttributionFeedUnified.jsx
│   │   ├── analytics/          # Analytics page
│   │   ├── copilot/            # AI Copilot
│   │   ├── finance/            # Finance/P&L
│   │   └── campaigns/          # Campaigns
│   └── globals.css
│
├── components/                  # Shared components
│   ├── ui/                     # Primitive components
│   └── ...
│
└── lib/                        # Utilities
    ├── api.js                  # API client (updated for unified)
    ├── workspace.js            # Workspace helpers (NEW)
    └── ...
```

### Authentication Flow (Clerk)

```
1. User visits protected route
       ↓
2. middleware.ts checks auth
       ↓
3. Unauthenticated → Redirect to /sign-in
       ↓
4. Clerk handles auth (OAuth/email)
       ↓
5. JWT stored in __session cookie
       ↓
6. API requests include JWT
       ↓
7. Backend validates via JWKS
```

### Dashboard Data Flow (Unified)

```
1. Dashboard page loads
       ↓
2. Single fetch: GET /dashboard/unified
       ↓
3. Response includes all widget data
       ↓
4. Unified components render:
   - KpiStripUnified
   - MoneyPulseChartUnified
   - TopCampaignsUnified
   - SpendMixUnified
   - AttributionCardUnified (if Shopify)
```

---

## Data Flow

### Metric Sync Flow (ARQ)

```
┌─────────────┐
│  Scheduler  │ (single instance)
└──────┬──────┘
       │ Every 15 min
       ▼
┌─────────────────────────────────┐
│  enqueue_sync_job() for each   │
│  active connection             │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│      Redis Queue (arq:queue)    │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│     Worker (N instances)        │
│                                 │
│  1. Validate connection tokens  │
│  2. Sync entities (status)      │
│  3. Fetch metrics from API      │
│  4. Upsert to MetricSnapshot    │
│  5. Update connection status    │
└─────────────────────────────────┘
```

### Dashboard Load Flow

```
Browser Request
       ↓
GET /dashboard/unified?timeframe=last_7_days
       ↓
┌─────────────────────────────────┐
│  get_unified_dashboard()        │
│                                 │
│  • Verify workspace access      │
│  • Query MetricSnapshot table   │
│  • Aggregate KPIs               │
│  • Build chart data             │
│  • Get top campaigns            │
│  • Get spend mix                │
│  • Get attribution (if Shopify) │
└─────────────────────────────────┘
       ↓
Single JSON Response (~200ms)
```

### QA System Flow

```
User Question
       ↓
POST /qa?workspace_id=...
       ↓
1. Get Context (Redis)
       ↓
2. Canonicalize (synonyms)
       ↓
3. Translate to DSL (LLM)
       ↓
4. Validate (Pydantic)
       ↓
5. Execute (UnifiedMetricService)
       ↓
6. Generate Answer (LLM)
       ↓
7. Store Context (Redis)
       ↓
Response
```

---

## Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `workspaces` | Company/organization accounts |
| `users` | Workspace members with `clerk_id` |
| `workspace_members` | User ↔ Workspace relationship |
| `connections` | Platform account links |
| `tokens` | Encrypted OAuth tokens |
| `entities` | Campaign hierarchy |
| `metric_snapshots` | 15-min granularity metrics (NEW) |
| `metric_facts` | Daily metrics (DEPRECATED) |
| `manual_costs` | User-entered costs |
| `pnl` | P&L snapshots |
| `qa_query_logs` | QA conversation history |
| `attributions` | Shopify order attribution |

### Key Models

```python
# User with Clerk integration
class User(Base):
    id = Column(UUID, primary_key=True)
    clerk_id = Column(String(255), unique=True)  # NEW
    email = Column(String, unique=True)
    workspace_id = Column(UUID, ForeignKey("workspaces.id"))

# MetricSnapshot (replaces MetricFact)
class MetricSnapshot(Base):
    id = Column(UUID, primary_key=True)
    entity_id = Column(UUID, ForeignKey("entities.id"))
    provider = Column(String(20))
    captured_at = Column(DateTime(timezone=True))
    spend = Column(Numeric(18, 4))
    revenue = Column(Numeric(18, 4))
    conversions = Column(Numeric(18, 4))
    # ... other measures

# Workspace with sync tracking
class Workspace(Base):
    id = Column(UUID, primary_key=True)
    name = Column(String)
    last_synced_at = Column(DateTime(timezone=True))  # NEW
```

### Key Indexes

```sql
-- MetricSnapshot queries
CREATE INDEX idx_snapshot_entity_captured
    ON metric_snapshots (entity_id, captured_at DESC);

CREATE INDEX idx_snapshot_dashboard
    ON metric_snapshots (entity_id, captured_at DESC)
    INCLUDE (spend, revenue, conversions);

-- User lookup by Clerk ID
CREATE INDEX idx_users_clerk_id ON users (clerk_id);
```

---

## Security

### Authentication (Clerk)

- **Method**: Clerk JWT in `__session` cookie or Authorization header
- **Algorithm**: RS256 with JWKS validation
- **Verification**: Public key fetched from Clerk (cached 1 hour)
- **User Lifecycle**: Webhooks for create/update/delete

### Authorization

- **Workspace Isolation**: All queries filter by `workspace_id`
- **Role-Based**: Owner/Admin/Viewer roles
- **Token Encryption**: AES-256-GCM for OAuth tokens

### API Security

- **SQL Injection**: SQLAlchemy ORM
- **XSS**: Next.js auto-escaping
- **CORS**: Configurable origins
- **Webhook Verification**: HMAC-SHA256 (Clerk/Shopify)

---

## Infrastructure

### Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRODUCTION STACK                          │
└─────────────────────────────────────────────────────────────────┘

  Defang                Railway                    Upstash
  ──────                ───────                    ──────
  Frontend              Backend                    Redis
  (Next.js)             (FastAPI)                  (ARQ queues)
                        PostgreSQL
                        ARQ Workers
                        ARQ Scheduler
```

### Environment Variables

**Backend:**
```bash
# Database
DATABASE_URL=postgresql://...

# Redis
REDIS_URL=rediss://...

# Clerk
CLERK_SECRET_KEY=sk_...
CLERK_PUBLISHABLE_KEY=pk_...
CLERK_WEBHOOK_SECRET=whsec_...

# AI
OPENAI_API_KEY=sk-...

# Observability
SENTRY_DSN=https://...

# Ad Platforms
META_APP_ID=...
META_APP_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

**Frontend:**
```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
NEXT_PUBLIC_API_BASE=https://api.metricx.ai
```

### Observability

- **Error Tracking**: Sentry (backend + frontend)
- **Structured Logging**: JSON with markers (`[ARQ]`, `[SNAPSHOT_SYNC]`, etc.)
- **LLM Tracing**: AI call logging for cost/performance tracking

---

## Development Workflow

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python start_api.py
```

### Frontend
```bash
cd ui
npm install
npm run dev
```

### ARQ Worker
```bash
cd backend
arq app.workers.arq_worker.WorkerSettings
```

### ARQ Scheduler
```bash
cd backend
python -m app.services.sync_scheduler
```

### Testing
```bash
cd backend
pytest
```

---

## Key Integrations

### Meta Ads
- **SDK**: `facebook-business`
- **Rate Limiting**: 200 calls/hour
- **Sync**: 15-min snapshots + 7-day attribution refresh

### Google Ads
- **SDK**: `google-ads`
- **GAQL**: Structured query language
- **Sync**: PMax support, asset_group level metrics

### Shopify
- **API**: Admin GraphQL API
- **Features**: Products, customers, orders, attribution
- **Webhooks**: GDPR compliance

### Clerk
- **Features**: OAuth, email/password, webhooks
- **Integration**: JWT validation, user lifecycle

### Anthropic
- **Model**: Claude Sonnet 4
- **Usage**: Intent extraction, answer generation, streaming responses

---

## References

- [AUTH.md](./AUTH.md) - Clerk authentication
- [ARQ_WORKERS.md](./ARQ_WORKERS.md) - Background jobs
- [UNIFIED_DASHBOARD.md](./UNIFIED_DASHBOARD.md) - Dashboard API
- [METRIC_SNAPSHOTS.md](./METRIC_SNAPSHOTS.md) - Metrics system
- [QA_SYSTEM_ARCHITECTURE.md](./QA_SYSTEM_ARCHITECTURE.md) - AI query system
- [ATTRIBUTION_ENGINE.md](./ATTRIBUTION_ENGINE.md) - Shopify attribution
- [REALTIME_DATA.md](./REALTIME_DATA.md) - Real-time sync
