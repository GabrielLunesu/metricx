# metricx Living Documentation

**Last Updated**: 2025-12-10
**Version**: 2.0.0

This directory contains living documentation for the metricx platform - an ad analytics tool that helps merchants optimize their advertising spend.

---

## Quick Navigation

### Core Architecture
| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System overview, tech stack, directory structure |
| [AUTH.md](./AUTH.md) | Clerk authentication system |
| [METRIC_SNAPSHOTS.md](./METRIC_SNAPSHOTS.md) | 15-minute granularity metrics system |
| [UNIFIED_DASHBOARD.md](./UNIFIED_DASHBOARD.md) | Single-call dashboard API |

### Background Processing
| Document | Description |
|----------|-------------|
| [ARQ_WORKERS.md](./ARQ_WORKERS.md) | Async job processing with ARQ |
| [REALTIME_DATA.md](./REALTIME_DATA.md) | Real-time sync architecture |

### Features
| Document | Description |
|----------|-------------|
| [QA_SYSTEM_ARCHITECTURE.md](./QA_SYSTEM_ARCHITECTURE.md) | AI-powered Q&A system (DSL, NLP, execution) |
| [ATTRIBUTION_ENGINE.md](./ATTRIBUTION_ENGINE.md) | Shopify pixel, journey tracking, CAPI |

### Operations
| Document | Description |
|----------|-------------|
| [OBSERVABILITY.md](./OBSERVABILITY.md) | Logging, Sentry, telemetry |

---

## System Architecture Overview

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
│ • Snapshots   │      │ • Context       │      │ • Anthropic     │
│ • Attribution │      │                 │      │ • Clerk         │
└───────────────┘      └─────────────────┘      └─────────────────┘
```

---

## Key Data Flows

### 1. Dashboard Load (Single Request)
```
Browser ─▶ GET /dashboard/unified ─▶ MetricSnapshot queries ─▶ Response
                                           │
                                           ├─ KPIs (revenue, ROAS, spend, conversions)
                                           ├─ Chart data (per-provider sparklines)
                                           ├─ Top campaigns
                                           ├─ Spend mix
                                           └─ Attribution (if Shopify connected)
```

### 2. Metric Sync (Every 15 Minutes)
```
ARQ Scheduler ─▶ enqueue_sync_job() ─▶ ARQ Worker
                                            │
                                            ├─ Sync entities (status changes)
                                            ├─ Fetch metrics from Meta/Google
                                            └─ Upsert to MetricSnapshot table
```

### 3. Authentication (Clerk)
```
User ─▶ Clerk (sign-in) ─▶ JWT ─▶ Backend validates ─▶ User record
                                        │
                                        └─ JWKS verification (RS256)
```

### 4. QA System (AI Copilot)
```
Question ─▶ understand_node ─▶ fetch_data_node ─▶ respond_node ─▶ SSE Stream
                   │                  │                  │
                   └─ Claude          └─ SemanticLayer   └─ Claude (streaming)
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js 15, Tailwind v4, Recharts | Dashboard UI |
| **Auth** | Clerk | Authentication, OAuth, user management |
| **Backend** | FastAPI, SQLAlchemy 2.x, Pydantic | REST API |
| **Database** | PostgreSQL (Railway) | Primary data store |
| **Cache** | Redis (Upstash) | Job queues, caching, context |
| **Jobs** | ARQ | Async background job processing |
| **AI** | Claude Sonnet 4 (Anthropic) | Intent extraction, streaming answers |
| **Observability** | Sentry, structured logging | Error tracking, monitoring |

---

## Recent Changes (December 2025)

### v2.0.0 - Major Platform Update

**Authentication**
- Migrated from custom JWT to **Clerk** authentication
- Added Clerk webhooks for user lifecycle (create/update/delete)
- Added repair endpoint for webhook failures

**Performance**
- New **Unified Dashboard API** - single request replaces 8+ calls
- **MetricSnapshot** table with 15-minute granularity (replaces daily MetricFact)
- Intraday charts for today/yesterday views

**Background Jobs**
- Migrated from RQ to **ARQ** for async job processing
- Separate scheduler and worker processes
- Parallel connection syncing

**Observability**
- Sentry integration for error tracking
- LLM tracing for AI calls
- Structured logging with markers

---

## Development Quick Start

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

---

## Environment Variables

### Required
```bash
# Database
DATABASE_URL=postgresql://...

# Redis
REDIS_URL=redis://... or rediss://... (SSL)

# Clerk Auth
CLERK_SECRET_KEY=sk_...
CLERK_PUBLISHABLE_KEY=pk_...
CLERK_WEBHOOK_SECRET=whsec_...

# AI
OPENAI_API_KEY=sk-...
```

### Optional
```bash
# Sentry
SENTRY_DSN=https://...

# Ad Platforms
META_APP_ID=...
META_APP_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

---

## Document Changelog

| Date | Change |
|------|--------|
| 2025-12-10 | Created living docs index, added new system docs |
| 2025-12-09 | Clerk authentication migration |
| 2025-12-08 | Unified Dashboard API, MetricSnapshot |
| 2025-12-07 | ARQ workers migration |
