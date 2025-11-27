# metricx — AI-Powered Marketing Analytics

**Test Login Credentials**
```
owner@defanglabs.com
password123
```

## 🌟 Vision

AdNavi eliminates the gap between data and decision-making in marketing analytics. Instead of learning dashboards, memorizing metrics, or writing SQL, marketers ask questions in plain English and get instant, accurate answers from their data.

**The North Star:** Natural language → Precise insights. No learning curve.

## 🎯 What We're Building

A **marketing analytics platform** that understands questions like:
- "What's my ROAS this week?"
- "Which campaign had the highest CPC?"
- "Compare my Meta and Google spend last month"
- "Why is my CPA volatile?"

And returns **accurate, contextual answers** powered by real-time data.

## ⚡ Safe AI Querying

Traditional AI + databases = **dangerous** (SQL injection, hallucinations, security leaks).

**Our approach:**
1. **User asks question** → "What's my ROAS?"
2. **LLM translates to DSL** → Structured JSON query (not SQL)
3. **DSL validated** → Pydantic schema catches errors
4. **Safe execution** → Workspace-scoped queries via SQLAlchemy ORM
5. **Intent-aware answer** → GPT rephrases facts into natural language

**Why this matters:**
- ✅ **Secure**: No SQL injection possible (JSON → ORM, never raw SQL)
- ✅ **Accurate**: Facts come from validated database queries
- ✅ **Natural**: Answers feel conversational, not robotic
- ✅ **Contextual**: Follow-up questions work ("and yesterday?")
- ✅ **Consistent**: Single source of truth ensures data matches across UI

## 📊 Data Flow: Question → Answer

```
User: "What's my ROAS this week?"
   ↓
[GPT-4-turbo translates to DSL]
   ↓
{
  "metric": "roas",
  "time_range": {"last_n_days": 7},
  "filters": {}
}
   ↓
[DSL validated & planned]
   ↓
[UnifiedMetricService queries database]
   ↓
[Derived metrics calculated: revenue ÷ spend]
   ↓
[Intent classifier: SIMPLE answer needed]
   ↓
[GPT-4o-mini rephrases fact into natural language]
   ↓
User: "Your ROAS this week is 2.45×"
```

**Key Innovation**: DSL acts as a **safe intermediary** between natural language and database queries.

## 🎨 System Architecture

### The DSL Layer (Domain-Specific Language)

**Problem:** LLMs hallucinate. Direct SQL generation = security risk.

**Solution:** Define a safe JSON schema that maps natural language → structured queries.

```json
{
  "query_type": "metrics",
  "metric": "roas",
  "time_range": {"last_n_days": 7},
  "compare_to_previous": true,
  "breakdown": "campaign",
  "top_n": 5
}
```

### Multi-Stage Pipeline

1. **Canonicalization**: Removes variance ("return on ad spend" → "roas")
2. **Translation**: GPT-4-turbo generates DSL from user question
3. **Validation**: Pydantic ensures DSL is valid and safe
4. **Planning**: Resolves dates, maps metrics to base measures
5. **Execution**: Workspace-scoped queries via ORM (no raw SQL)
6. **Answer Building**: Intent-aware natural language generation

### Conversation Context

**Challenge:** Follow-up questions lose context ("and yesterday?" needs to know previous metric)

**Solution:** Redis-backed context manager stores last 5 queries per user+workspace.

```
Q1: "What's my ROAS?" → stores "roas" metric
Q2: "And yesterday?" → inherits "roas" from context
```

## 🚀 Features

**24 Metrics Supported:**
- Cost: CPC, CPM, CPA, CPL, CPI, CPP
- Value: ROAS, POAS, ARPV, AOV  
- Engagement: CTR, CVR
- Base: Spend, Revenue, Clicks, Impressions, Conversions, Leads, Installs, Purchases, Visitors, Profit

**Query Capabilities:**
- Simple metrics: "What's my CPC?"
- Comparisons: "Compare Meta vs Google spend"
- Breakdowns: "Which campaign had highest ROAS?"
- Multi-metric: "Show me spend and revenue"
- Temporal: "Which day had lowest CPC?"
- Follow-ups: "And yesterday?"

**UI Dashboards:**
- Real-time KPIs with time range filtering
- Campaign performance drill-down (campaign → ad set → ad)
- Finance P&L with manual cost tracking
- AI Copilot chat interface

## 🛠️ Tech Stack

**AI & Backend:**
- FastAPI + Python 3.11
- PostgreSQL 16 + Redis
- OpenAI GPT-4-turbo (DSL translation)
- OpenAI GPT-4o-mini (answer generation)
- SQLAlchemy ORM (safe queries)

**Frontend:**
- Next.js 15.5.4 + React 19
- Tailwind CSS v4
- Recharts for visualizations

**Security:**
- JWT authentication (HTTP-only cookies)
- Workspace-scoped multi-tenancy
- Bcrypt password hashing
- No raw SQL execution

## 🧪 Technical Highlights

**130+ Unit Tests** covering DSL validation, translator mocking, context manager, and metric calculations.

**Success Rate:** 99%+ on production queries

**Performance:** <1.5s end-to-end latency (LLM translation + DB query + answer generation)

**Security:** Zero SQL injection possible (JSON → Pydantic → ORM)

## 🚦 Quick Start

```bash
# Infrastructure
docker compose up -d

# Backend
cd backend
python -m venv venv && source bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed_mock
python start_api.py

# Frontend  
cd ui
npm install && npm run dev
```

Access: http://localhost:3000

## 📖 Learn More

- **Build Log**: `docs/ADNAVI_BUILD_LOG.md` - Development history
- **Architecture**: `backend/docs/QA_SYSTEM_ARCHITECTURE.md` - DSL specification & AI pipeline
- **Context**: `backend/docs/REDIS_CONTEXT_MANAGER.md` - Conversation history system

## 🎯 Technical Innovation Summary


1. **Safe DSL Layer**: JSON schema prevents SQL injection and hallucinations
2. **Intent Classification**: Answers match question complexity (simple vs analytical)
3. **Unified Metrics**: Single source of truth eliminates data mismatches
4. **Context Awareness**: Redis-backed multi-turn conversations
5. **Workspace Scoping**: SQL-level multi-tenancy prevents data leaks

**Result:** A production-ready AI analytics system that's both powerful and safe.

---

Built at Defang Labs | Graduation Project 2025
