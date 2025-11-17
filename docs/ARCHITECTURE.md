# AdNavi Architecture Documentation

**Last Updated**: 2025-01-16  
**Version**: 1.0

## Overview

AdNavi is a comprehensive advertising analytics and optimization platform that aggregates data from multiple ad platforms (Meta Ads, Google Ads, TikTok) and provides AI-powered insights through natural language queries.

### Core Capabilities

- **Multi-Platform Integration**: Meta Ads, Google Ads, TikTok
- **AI-Powered Analytics**: Natural language query system (QA/Copilot)
- **Real-Time Metrics**: Unified metric calculations across all platforms
- **Financial Reporting**: P&L statements with manual cost tracking
- **Campaign Management**: Hierarchical entity management (Campaign → Ad Set → Ad → Creative)
- **Automated Sync**: Scheduled data synchronization from ad platforms

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (UI)                         │
│  Next.js 15.5.4 (App Router) - JSX only                    │
│  - Dashboard, Analytics, Copilot, Finance, Campaigns      │
│  - Tailwind CSS v4, Recharts, Lucide React                 │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
                       │ JWT Cookies
┌──────────────────────▼──────────────────────────────────────┐
│                    Backend (API)                             │
│  FastAPI + SQLAlchemy 2.x + Alembic                         │
│  - REST API endpoints                                       │
│  - DSL-based QA system                                      │
│  - Unified metric calculations                              │
│  - Platform sync services                                   │
└──────┬──────────────────┬──────────────────┬─────────────────┘
       │                  │                  │
┌──────▼──────┐  ┌────────▼────────┐  ┌────▼──────┐
│ PostgreSQL  │  │      Redis       │  │  External  │
│   (Railway) │  │   (Context)     │  │    APIs    │
│             │  │                  │  │            │
│ - Entities  │  │ - Conversation   │  │ - Meta Ads │
│ - Metrics   │  │   History        │  │ - Google   │
│ - Users     │  │ - TTL-based       │  │ - TikTok   │
│ - Workspaces│  │   Cleanup        │  │            │
└─────────────┘  └──────────────────┘  └───────────┘
```

---

## Backend Architecture

### Directory Structure

```
backend/app/
├── main.py                    # FastAPI app entrypoint, router registration
├── models.py                   # SQLAlchemy ORM models (12 models)
├── schemas.py                  # Pydantic request/response schemas
├── database.py                 # Database connection & session management
├── security.py                 # JWT & password hashing
├── authentication.py           # Admin panel auth
├── deps.py                     # Dependency injection (DB sessions, settings)
├── state.py                    # Application-level singletons (Redis context)
│
├── routers/                    # API endpoints (17 routers)
│   ├── auth.py                 # Login, register, logout, /me
│   ├── workspaces.py           # Workspace info, management
│   ├── connections.py          # Platform connection CRUD
│   ├── entities.py             # Entity CRUD
│   ├── metrics.py              # Metrics summary endpoint
│   ├── kpis.py                 # KPI aggregation (dashboard)
│   ├── finance.py              # P&L statements, manual costs
│   ├── entity_performance.py   # Campaign/adset/ad performance listings
│   ├── qa.py                   # Natural language QA endpoint
│   ├── qa_log.py               # QA conversation history
│   ├── ingest.py               # Metrics ingestion API
│   ├── meta_sync.py            # Meta Ads entity/metrics sync
│   ├── google_sync.py          # Google Ads entity/metrics sync
│   ├── meta_oauth.py           # Meta OAuth flow
│   └── google_oauth.py         # Google OAuth flow
│
├── services/                   # Business logic layer
│   ├── qa_service.py           # QA orchestrator (main entry point)
│   ├── unified_metric_service.py  # Single source of truth for metrics
│   ├── meta_ads_client.py      # Meta API wrapper (rate limiting, pagination)
│   ├── google_ads_client.py    # Google Ads API wrapper (GAQL, rate limiting)
│   ├── meta_sync_scheduler.py  # Automated Meta sync scheduler
│   ├── token_service.py        # Token encryption/decryption
│   ├── compute_service.py     # P&L snapshot generation
│   ├── cost_allocation.py      # Manual cost pro-rating logic
│   └── metric_service.py       # Legacy (being phased out)
│
├── dsl/                        # Domain-Specific Language for queries
│   ├── schema.py               # Pydantic models (MetricQuery, MetricResult)
│   ├── canonicalize.py         # Synonym & time phrase mapping
│   ├── validate.py             # DSL validation logic
│   ├── planner.py               # DSL → execution plan
│   ├── executor.py              # Plan → SQL → results (uses UnifiedMetricService)
│   ├── hierarchy.py             # Entity ancestor resolution (CTEs)
│   └── date_parser.py           # Date range extraction
│
├── nlp/                        # Natural Language Processing
│   ├── translator.py            # LLM → DSL translation (OpenAI GPT-4-turbo)
│   └── prompts.py               # System prompts & few-shot examples
│
├── answer/                     # Answer Generation
│   ├── answer_builder.py       # Hybrid LLM-based answer builder
│   ├── formatters.py           # Display formatting (currency, ratios, %)
│   ├── intent_classifier.py    # Query intent detection (SIMPLE/COMPARATIVE/ANALYTICAL)
│   └── context_extractor.py    # Rich context extraction (trends, outliers)
│
├── context/                     # Conversation Context
│   ├── redis_context_manager.py # Redis-backed conversation history
│   └── context_manager.py       # Legacy in-memory (deprecated)
│
├── metrics/                     # Derived Metrics System
│   ├── formulas.py              # Pure functions for 12 derived metrics
│   └── registry.py              # Metric → formula mapping
│
├── telemetry/                   # Observability
│   └── logging.py               # Structured QA logging
│
└── tests/                       # Unit & integration tests
    ├── test_dsl_*.py
    ├── test_qa_service.py
    ├── test_unified_metric_service.py
    └── integration/
```

### Key Backend Components

#### 1. **Unified Metric Service** (`services/unified_metric_service.py`)
- **Purpose**: Single source of truth for all metric calculations
- **Used by**: QA system, KPI endpoint, Finance endpoint, Entity Performance
- **Features**:
  - Consistent aggregation logic across all endpoints
  - Workspace-scoped security at SQL level
  - Divide-by-zero guards
  - Multi-metric support
  - Timeseries, breakdowns, workspace averages
  - Hierarchy-aware rollups (campaign → adset → ad)

#### 2. **QA System** (`services/qa_service.py` + `dsl/` + `nlp/`)
- **Purpose**: Natural language → structured query → answer
- **Pipeline**:
  1. Retrieve conversation context (Redis)
  2. Canonicalize question (synonyms, time phrases)
  3. Translate to DSL via LLM (GPT-4-turbo)
  4. Validate DSL (Pydantic)
  5. Build execution plan
  6. Execute via UnifiedMetricService
  7. Format results
  8. Generate natural language answer (LLM)
  9. Store context for follow-ups

#### 3. **Platform Sync Services**
- **Meta Ads** (`services/meta_ads_client.py` + `routers/meta_sync.py`):
  - Rate limiting (200 calls/hour)
  - Entity hierarchy sync (campaigns → adsets → ads)
  - Metrics sync (90-day backfill, incremental, 7-day chunks)
  - Automated scheduler (configurable frequency)
  
- **Google Ads** (`services/google_ads_client.py` + `routers/google_sync.py`):
  - GAQL query builder
  - Rate limiting & retries
  - PMax hierarchy support (campaigns → asset groups → creatives)
  - Metrics sync (ad + asset group + creative level)

#### 4. **Data Models** (`models.py`)
- **Core**: Workspace, User, Connection, Token
- **Entities**: Entity (campaign/adset/ad/creative hierarchy)
- **Metrics**: MetricFact (raw performance data)
- **Financial**: ManualCost, Pnl (P&L snapshots)
- **Analytics**: QaQueryLog, ComputeRun
- **Auth**: AuthCredential (bcrypt password hashes)

---

## Frontend Architecture

### Directory Structure

```
ui/
├── app/                        # Next.js App Router
│   ├── layout.jsx              # Root layout (global styles, background)
│   ├── page.jsx                # Homepage
│   ├── login/                  # Login page
│   ├── (dashboard)/            # Dashboard route group
│   │   ├── layout.jsx          # Dashboard shell (sidebar, auth guard)
│   │   ├── dashboard/          # Dashboard page
│   │   ├── analytics/          # Analytics page
│   │   ├── copilot/            # AI Copilot chat
│   │   ├── finance/            # Finance/P&L page
│   │   ├── campaigns/          # Campaigns list
│   │   │   └── [id]/           # Campaign detail (ad sets)
│   │   │       └── [adsetId]/  # Ad set detail (ads)
│   │   ├── settings/           # Settings page
│   │   └── meta-telemetry/     # Meta sync telemetry
│   └── globals.css             # Global Tailwind styles
│
├── components/                  # React components (89 files)
│   ├── sections/               # Container components (data fetching)
│   ├── analytics/              # Analytics-specific components
│   ├── copilot/                # Copilot-specific components
│   ├── finance/                # Finance-specific components
│   ├── campaigns/              # Campaign-specific components
│   └── ui/                     # Primitive components (Card, Badge, etc.)
│
├── lib/                        # Utilities & API clients
│   ├── api.js                  # API client functions
│   ├── auth.js                 # Auth utilities
│   ├── cn.js                   # Class name utility
│   ├── campaignsApiClient.js   # Campaign API client
│   ├── campaignsAdapter.js     # Campaign data adapter
│   ├── financeApiClient.js     # Finance API client
│   └── pnlAdapter.js           # P&L data adapter
│
└── data/                       # Mock data (legacy, being phased out)
    ├── kpis.js
    ├── campaigns/
    └── ...
```

### Frontend Patterns

#### **Separation of Concerns**
- **API Clients** (`lib/*ApiClient.js`): Thin HTTP wrappers, zero business logic
- **Adapters** (`lib/*Adapter.js`): View model transformation, formatting
- **Components**: Presentational only, receive ready-to-display data

#### **Data Flow**
```
User Action → Component → API Client → Backend API
                                    ↓
                              Adapter → View Model → Component Display
```

#### **Authentication**
- JWT stored in HTTP-only cookie (`access_token`)
- Auth guard in dashboard layout (`app/(dashboard)/layout.jsx`)
- Client-side auth check via `/auth/me` endpoint

---

## Data Flow

### QA System Flow

```
User Question
    ↓
POST /qa?workspace_id=...
    ↓
QAService.answer()
    ↓
1. Get Context (Redis) → Last N queries
    ↓
2. Canonicalize → Map synonyms, normalize time phrases
    ↓
3. Translate (LLM) → Natural language → DSL JSON
    ↓
4. Validate → Pydantic validation, constraints
    ↓
5. Plan → Resolve dates, map derived metrics → base measures
    ↓
6. Execute → UnifiedMetricService → SQL queries
    ↓
7. Format → Currency, ratios, percentages
    ↓
8. Answer Builder (LLM) → Facts + LLM rephrasing → Natural answer
    ↓
9. Store Context (Redis) → Save for follow-ups
    ↓
Response: { answer, executed_dsl, data, context_used }
```

### Platform Sync Flow

```
User clicks "Sync Meta Ads"
    ↓
POST /workspaces/{id}/connections/{id}/sync-entities
    ↓
MetaAdsClient → Meta API → Campaigns/AdSets/Ads
    ↓
UPSERT Entity records (hierarchy with parent_id)
    ↓
POST /workspaces/{id}/connections/{id}/sync-metrics
    ↓
MetaAdsClient → Meta Insights API (7-day chunks)
    ↓
Ingestion API → MetricFact records (deduplication via natural_key)
    ↓
UI refreshes → UnifiedMetricService aggregates → Display
```

### Metric Calculation Flow

```
Query Request (QA/KPI/Finance)
    ↓
UnifiedMetricService.get_summary()
    ↓
1. Build base query → Filter by workspace_id, time_range, filters
    ↓
2. Join Entity table → Apply level/status/provider filters
    ↓
3. Aggregate base measures → SUM(spend), SUM(revenue), etc.
    ↓
4. Compute derived metrics → ROAS = revenue/spend (with ÷0 guards)
    ↓
5. Previous period comparison → Delta percentages
    ↓
6. Return MetricSummaryResult → Consistent across all endpoints
```

---

## Key Integrations

### Meta Ads Integration
- **SDK**: `facebook-business==19.0.0`
- **Endpoints**: Entity sync, metrics sync, OAuth flow
- **Features**: Rate limiting, pagination, 90-day backfill, incremental sync
- **Scheduler**: Configurable frequency (manual, 30min, hourly, daily)

### Google Ads Integration
- **SDK**: `google-ads` library
- **Endpoints**: Entity sync, metrics sync, OAuth flow
- **Features**: GAQL queries, PMax support, rate limiting, retries
- **Hierarchy**: Campaign → Ad Group → Ad → Asset Group → Creative

### OpenAI Integration
- **Model**: GPT-4-turbo (QA translation), GPT-4o-mini (answer generation)
- **Usage**: Natural language → DSL translation, answer rephrasing
- **Configuration**: Temperature=0 (translation), Temperature=0.3 (answers)

### Redis Integration
- **Purpose**: Conversation context storage
- **Features**: TTL-based expiration (1 hour), FIFO eviction (max 5 entries)
- **Key Format**: `context:{user_id}:{workspace_id}`
- **Fail-Fast**: Application validates Redis on startup

---

## Database Schema

### Core Tables

- **workspaces**: Company/organization accounts
- **users**: Workspace members (Owner/Admin/Viewer roles)
- **connections**: Platform account links (Meta/Google/TikTok)
- **tokens**: Encrypted OAuth tokens (AES-256-GCM)
- **entities**: Hierarchical campaign structure (campaign → adset → ad → creative)
- **metric_facts**: Raw performance data (spend, revenue, clicks, etc.)
- **manual_costs**: User-entered costs (one-off or date ranges)
- **pnl**: P&L snapshots (computed from MetricFact + ManualCost)
- **qa_query_logs**: QA conversation history
- **auth_credentials**: Bcrypt password hashes

### Key Relationships

```
Workspace 1:N User
Workspace 1:N Connection
Connection 1:1 Token
Connection 1:N Entity
Entity N:1 Entity (parent)
Entity 1:N MetricFact
Workspace 1:N ManualCost
Workspace 1:N Pnl
```

### Indexes

- `metric_facts`: event_date, entity_id, provider, (entity_id, event_date)
- `entities`: external_id, workspace_id, connection_id
- Unique constraints: `metric_facts.natural_key`, `entities.external_id + connection_id`

---

## Security

### Authentication
- **Method**: JWT tokens in HTTP-only cookies
- **Algorithm**: HS256
- **Expiration**: Configurable (default 7 days)
- **Password Hashing**: Bcrypt (10 rounds)

### Authorization
- **Workspace Isolation**: All queries filter by `workspace_id` at SQL level
- **Role-Based**: Owner/Admin/Viewer roles (future enhancement)
- **Token Encryption**: AES-256-GCM for OAuth tokens

### Data Protection
- **SQL Injection**: SQLAlchemy ORM prevents injection
- **XSS**: Next.js auto-escaping, HTTP-only cookies
- **CORS**: Configurable allowed origins
- **Secrets**: Environment variables, never committed

---

## Infrastructure

### Deployment
- **Backend**: Railway (PostgreSQL + Redis)
- **Frontend**: Defang (Next.js static export)
- **Containerization**: Docker Compose
- **Health Checks**: `/health` endpoint for load balancers

### Environment Variables

**Backend**:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET`: JWT signing key
- `OPENAI_API_KEY`: OpenAI API key
- `ADMIN_SECRET_KEY`: Admin panel session secret
- `BACKEND_CORS_ORIGINS`: Allowed CORS origins

**Frontend**:
- `NEXT_PUBLIC_API_BASE`: Backend API URL (build-time)

### Monitoring & Observability
- **Structured Logging**: JSON logs with `[QA_PIPELINE]`, `[UNIFIED_METRICS]` markers
- **Telemetry**: QA latency tracking, error logging
- **Admin Panel**: SQLAdmin UI at `/admin` for database inspection

---

## Development Workflow

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head  # Run migrations
python start_api.py   # Start dev server
```

### Frontend
```bash
cd ui
npm install
npm run dev  # Start Next.js dev server
```

### Testing
- **Backend**: `pytest` (unit + integration tests)
- **QA System**: `./run_qa_tests.sh` (manual QA test suite)
- **Database**: Alembic migrations, seed script (`python -m app.seed_mock`)

---

## Future Enhancements

- **Phase 3**: Automated sync scheduler (in progress)
- **Phase 4**: Query layer enhancements (hourly breakdowns)
- **Phase 7**: OAuth user flow (click button → connected)
- **Multi-tenant**: Enhanced workspace isolation
- **Real-time**: WebSocket support for live updates
- **Advanced Analytics**: Predictive modeling, anomaly detection

---

## References

- **Build Log**: `docs/living-docs/ADNAVI_BUILD_LOG.md`
- **QA Architecture**: `docs/living-docs/QA_SYSTEM_ARCHITECTURE.md`
- **Redis Context**: `backend/docs/REDIS_CONTEXT_MANAGER.md`
- **Unified Metrics**: `backend/docs/architecture/unified-metrics.md`
- **Meta Integration**: `docs/living-docs/META_INTEGRATION_STATUS.md`
- **Google Integration**: `docs/living-docs/GOOGLE_INTEGRATION_STATUS.MD`

