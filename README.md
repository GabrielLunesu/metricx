# metricx — AI-Powered Marketing Analytics


```bash
# Infrastructure
docker compose up -d

# Backend
cd backend
python -m venv venv && source bin/activate 
pip install -r requirements.txt
alembic upgrade head
python start_api.py

# ARQ Worker (background jobs)
arq app.workers.arq_worker.WorkerSettings

# ARQ Scheduler (cron jobs)
python -m app.services.sync_scheduler

# Frontend
cd ui
npm install && npm run dev
```

Access: http://localhost:3000

---

## Vision

metricx eliminates the gap between data and decision-making in marketing analytics. Instead of learning dashboards, memorizing metrics, or writing SQL, marketers ask questions in plain English and get instant, accurate answers from their data.

**The North Star:** Natural language → Precise insights. No learning curve.

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
│ • Copilot       │     │ • Semantic QA   │     │ • Snapshot compaction       │
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
│ • Snapshots   │      │ • SSE streams   │      │ • Anthropic     │
│ • Attribution │      │                 │      │ • Clerk         │
└───────────────┘      └─────────────────┘      └─────────────────┘
```

---

## Key Features

### AI-Powered Copilot
- **Claude Sonnet 4** — Anthropic's latest model for understanding & response
- **Semantic Layer** — Composable queries (breakdown + comparison + timeseries)
- **SSE Streaming** — Token-by-token responses with typing effect
- **LangGraph Agent** — Structured flow: understand → fetch_data → respond

### Dashboard & Performance
- **Unified Dashboard API** — Single request returns all data (8+ calls → 1)
- **15-Minute Metric Snapshots** — Real-time intraday analytics
- **Multi-Provider Charts** — Per-platform breakdown (Meta, Google)

### Authentication & Security
- **Clerk Authentication** — OAuth, email/password, webhooks
- **Workspace Isolation** — SQL-level multi-tenancy
- **Token Encryption** — AES-256-GCM for OAuth tokens

### Background Processing
- **ARQ Workers** — Async job processing with Redis
- **Scheduled Syncs** — Every 15 min (realtime), daily (attribution)
- **Automatic Compaction** — 15-min → hourly after 2 days

### Observability
- **Sentry** — Error tracking & performance monitoring
- **Langfuse** — LLM call tracing (Claude usage, latency, costs)
- **Structured Logging** — `[ARQ]`, `[SYNC]`, `[SEMANTIC]` markers

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 15, React 19, Tailwind v4, Recharts |
| **Auth** | Clerk (RS256 JWT, JWKS) |
| **Backend** | FastAPI, SQLAlchemy 2.x, Pydantic |
| **AI** | Claude Sonnet 4 (Anthropic), LangGraph |
| **Database** | PostgreSQL 16 |
| **Cache/Queue** | Redis (Upstash), ARQ |
| **Observability** | Sentry, Langfuse, RudderStack |

---

## AI Copilot Architecture

### Question → Answer Flow

```
User: "Compare CPC this week vs last week for top 3 ads"
       ↓
[understand_node] Claude extracts intent → SemanticQuery
       ↓
[fetch_data_node] Semantic Layer → UnifiedMetricService
       ↓
[respond_node] Claude generates answer + visuals
       ↓
SSE Stream: tokens + chart spec + done event
```

### Semantic Layer (Composable Queries)

Unlike rigid DSL, the semantic layer allows **composition**:

```python
SemanticQuery(
    metrics=["cpc"],
    breakdown=Breakdown(dimension="entity", level="ad", limit=3),
    comparison=Comparison(type=ComparisonType.PREVIOUS_PERIOD),
    include_timeseries=True
)
```

This enables complex questions that were previously impossible.

### Streaming (Non-Blocking)

```python
# Async Claude client for non-blocking streaming
async with client.messages.stream(...) as stream:
    async for text in stream.text_stream:
        yield f"data: {json.dumps({'type': 'token', 'data': text})}\n\n"

# DB queries run in thread pool (SQLAlchemy is sync)
result = await asyncio.to_thread(fetch_data_sync)
```

---

## Data Flows

### Dashboard Load (Unified API)

```
GET /dashboard/unified?timeframe=last_7_days
       ↓
┌─────────────────────────────┐
│  Single query returns:      │
│  • KPIs (revenue, ROAS...)  │
│  • Chart data               │
│  • Top campaigns            │
│  • Spend mix                │
│  • Attribution (if Shopify) │
└─────────────────────────────┘
       ↓
Response: ~200ms (was 4+ seconds)
```

### Metric Sync (ARQ)

```
Scheduler (every 15 min)
       ↓
Enqueue jobs for all connections
       ↓
Workers process in parallel
       ↓
MetricSnapshot table updated
```

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://...

# Redis
REDIS_URL=rediss://...

# Clerk Auth
CLERK_SECRET_KEY=sk_...
CLERK_PUBLISHABLE_KEY=pk_...
CLERK_WEBHOOK_SECRET=whsec_...

# AI (Anthropic)
ANTHROPIC_API_KEY=sk-ant-...

# Observability
SENTRY_DSN=https://...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# Ad Platforms
META_APP_ID=...
META_APP_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

---

## API Endpoints

### Copilot (QA)
| Endpoint | Description |
|----------|-------------|
| `POST /qa/agent/sse` | **SSE streaming** (recommended) |
| `POST /qa/agent/sync` | Synchronous (no streaming) |
| `POST /qa/semantic` | Direct semantic layer access |
| `POST /qa/insights` | Lightweight insights for widgets |

### Dashboard
| Endpoint | Description |
|----------|-------------|
| `GET /dashboard/unified` | All dashboard data in one call |

---

## Metrics Supported

**24 Metrics:**

| Category | Metrics |
|----------|---------|
| **Cost** | CPC, CPM, CPA, CPL, CPI, CPP |
| **Value** | ROAS, POAS, ARPV, AOV |
| **Engagement** | CTR, CVR |
| **Base** | Spend, Revenue, Clicks, Impressions, Conversions, Leads, Installs, Purchases, Visitors, Profit |

---

## Query Examples

```
"What's my CPC?"
"Compare Meta vs Google spend"
"Which campaign had highest ROAS?"
"Compare CPC this week vs last week for top 3 ads"
"Why did my ROAS drop?"
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/living-docs/ARCHITECTURE.md) | System overview, tech stack |
| [AUTH.md](docs/living-docs/AUTH.md) | Clerk authentication |
| [ARQ_WORKERS.md](docs/living-docs/ARQ_WORKERS.md) | Background job processing |
| [UNIFIED_DASHBOARD.md](docs/living-docs/UNIFIED_DASHBOARD.md) | Dashboard API |
| [METRIC_SNAPSHOTS.md](docs/living-docs/METRIC_SNAPSHOTS.md) | 15-min metrics system |
| [QA_SYSTEM_ARCHITECTURE.md](docs/living-docs/QA_SYSTEM_ARCHITECTURE.md) | AI Copilot architecture |
| [OBSERVABILITY.md](docs/living-docs/OBSERVABILITY.MD) | Monitoring stack |

---

## Recent Updates (v2.0.0 - December 2025)

| Feature | Change |
|---------|--------|
| **AI** | Migrated from OpenAI to Claude (Anthropic) |
| **QA System** | Semantic layer with composable queries |
| **Streaming** | SSE with AsyncAnthropic (non-blocking) |
| **Authentication** | Migrated from custom JWT to Clerk |
| **Dashboard** | New unified API (8+ calls → 1) |
| **Metrics** | 15-min snapshots (was daily) |
| **Background Jobs** | ARQ workers + scheduler |

---

## Project Structure

```
metricx/
├── backend/
│   ├── app/
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Business logic
│   │   ├── workers/        # ARQ jobs
│   │   ├── semantic/       # Semantic layer (query, compiler, validator)
│   │   ├── agent/          # LangGraph agent (nodes, tools, state)
│   │   ├── telemetry/      # Observability
│   │   └── models.py       # Database models
│   └── alembic/            # Migrations
├── ui/
│   ├── app/                # Next.js pages
│   ├── components/         # React components
│   └── lib/                # API clients
├── docs/
│   └── living-docs/        # Documentation
└── compose.yaml            # Docker setup
```

---

Built at Defang Labs | Graduation Project 2025
