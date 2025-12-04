# QA System Architecture

This document describes the QA (Question Answering) system architecture, including the Agentic Copilot powered by LangGraph + Claude.

## Overview

The QA system provides a conversational interface for merchants to query their advertising data. It feels like "talking to a smart human" that understands natural language questions and generates insightful answers with visualizations.

**Version 4.0** - Agentic Copilot with LangGraph + Claude

## Architecture

```
User Question
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agentic Copilot                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Understand  │───▶│  Fetch Data  │───▶│   Respond    │  │
│  │   (Claude)   │    │  (Semantic)  │    │   (Claude)   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │           │
│         ▼                   ▼                   ▼           │
│   Intent + Query      Compiled Data      Natural Answer    │
│   Classification      from Semantic      + Visualizations  │
│                       Layer                                 │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                     Semantic Layer                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │    Query     │───▶│   Compiler   │───▶│   Results    │  │
│  │   Builder    │    │   (SQL Gen)  │    │   (Typed)    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
   Database
```

## Directory Structure

```
app/
├── agent/                    # LangGraph Agent (v4.0)
│   ├── __init__.py
│   ├── state.py              # AgentState TypedDict
│   ├── nodes.py              # understand, fetch_data, respond nodes
│   ├── tools.py              # SemanticTools wrapper
│   ├── graph.py              # LangGraph StateGraph
│   └── stream.py             # Redis Pub/Sub streaming
│
├── semantic/                 # Semantic Layer (v3.0)
│   ├── __init__.py
│   ├── model.py              # Metric definitions (METRICS dict)
│   ├── query.py              # SemanticQuery dataclass
│   ├── compiler.py           # SQL compilation
│   └── validator.py          # Query validation
│
├── routers/
│   └── qa.py                 # API endpoints
│
└── tests/qa_evaluation/      # Test suite
    ├── conftest.py
    ├── deepeval_config.py
    └── test_qa_golden.py
```

## Core Components

### 1. Agent Nodes (`app/agent/nodes.py`)

The agent uses three main nodes:

**understand_node**
- Uses Claude to classify intent and extract query parameters
- Intents: `metric_query`, `comparison`, `ranking`, `analysis`, `clarification_needed`, `out_of_scope`
- Extracts: metrics, time_range, breakdown_level, filters, compare_to_previous

**fetch_data_node**
- Calls SemanticTools to fetch data from the Semantic Layer
- Handles query_metrics, get_entities, analyze_change

**respond_node**
- Uses Claude to generate natural language response
- Streams tokens for typing effect
- Builds visualizations (charts, tables)

### 2. Semantic Layer (`app/semantic/`)

The Semantic Layer provides composable, type-safe queries:

```python
query = SemanticQuery(
    metrics=["spend", "revenue", "roas"],
    time_range=TimeRange(last_n_days=7),
    breakdown=Breakdown(dimension="entity", level="campaign"),
    comparison=Comparison(type=ComparisonType.PREVIOUS_PERIOD),
)
result = compiler.compile(workspace_id, query)
```

**Key Features:**
- Composable queries (breakdown + comparison + timeseries)
- Type-safe metric definitions
- Automatic calculated metrics (ROAS, CPC, CTR, etc.)
- Workspace-scoped security

### 3. Tools (`app/agent/tools.py`)

Agent tools wrap the Semantic Layer:

| Tool | Description |
|------|-------------|
| `query_metrics` | Fetch metrics with optional breakdown/comparison |
| `get_entities` | List campaigns, ad sets, or ads |
| `analyze_change` | Analyze why a metric changed |

### 4. Streaming (`app/agent/stream.py`)

Real-time token streaming via SSE:

```
POST /qa/agent/sse
     │
     ▼
┌─────────────────┐
│  SSE Events:    │
│  - thinking     │
│  - token        │
│  - visual       │
│  - done         │
│  - error        │
└─────────────────┘
```

## API Endpoints

### Primary (Agentic Copilot)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/qa/agent/sse` | POST | SSE streaming with typing effect |
| `/qa/agent/sync` | POST | Synchronous (no streaming) |
| `/qa/insights` | POST | Lightweight insights (no visuals) |

### Lightweight Insights (`/qa/insights`)

A fast endpoint for dashboard widgets that need AI-generated text without visualizations:

```python
# Request
{
    "question": "What is my biggest performance drop last 7 days?",
    "metrics_data": {}  # Optional: pass pre-fetched metrics
}

# Response
{
    "success": true,
    "answer": "Your CPC increased by 15% due to...",
    "intent": "analysis"
}
```

**Used by:**
- Dashboard: `AiInsightsPanel` (performance drops, opportunities)
- Analytics: `AnalyticsIntelligenceZone` (contextual analysis)
- Finance: `AIFinancialSummary` (financial summary)

### Fallback (Legacy)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/qa/semantic` | POST | Direct Semantic Layer |
| `/qa/stream` | POST | Legacy SSE streaming |
| `/qa` | POST | Legacy polling |

## Visual Output

The agent generates visualizations based on query type:

| Query Type | Visualization |
|------------|---------------|
| Single metric | Summary card |
| Comparison (aggregate) | Bar chart (Previous vs This Period) |
| Comparison (timeseries) | Line chart with overlaid series |
| Breakdown | Bar chart + Table |
| Multi-metric breakdown | Table with all metrics |
| Timeseries | Area/Line chart |

### Comparison Timeseries

When a user requests a comparison with a graph/chart, the system generates overlaid line charts:

```
User: "Compare this week's CPC with last week with a graph"

Result: Line chart with two series:
- "This Period" (current week data)
- "Previous Period" (last week data)
- X-axis normalized to "Day 1", "Day 2", etc. for proper overlay
```

This is controlled by `Comparison.include_timeseries=True` in the semantic query.

### Multi-Metric Table Generation

When multiple metrics are requested with a breakdown:

```python
# User: "Give me spend, revenue, ROAS, and profit for all campaigns"

# Generated table:
| Campaign | SPEND | REVENUE | ROAS | PROFIT |
|----------|-------|---------|------|--------|
| Campaign A | $1,000 | $5,000 | 5.00× | $4,000 |
| Campaign B | $2,000 | $8,000 | 4.00× | $6,000 |
```

Calculated metrics (ROAS, profit, CPC, CPA, CTR) are computed from base metrics if not directly available.

## Available Metrics

| Metric | Type | Calculation |
|--------|------|-------------|
| spend | Currency | Direct |
| revenue | Currency | Direct |
| clicks | Number | Direct |
| impressions | Number | Direct |
| conversions | Number | Direct |
| roas | Ratio | revenue / spend |
| cpc | Currency | spend / clicks |
| ctr | Percent | clicks / impressions |
| cpa | Currency | spend / conversions |
| profit | Currency | revenue - spend |
| aov | Currency | revenue / conversions |
| cvr | Percent | conversions / clicks |

## Example Queries

| Query | Intent | Output |
|-------|--------|--------|
| "What's my ROAS?" | metric_query | Single value |
| "Spend vs last week" | comparison | Bar chart comparison |
| "Top 5 campaigns by revenue" | ranking | Bar chart + table |
| "Why is my CPC up?" | analysis | Contributor analysis |
| "Show me daily spend trend" | metric_query | Area chart |
| "Give me spend, revenue, ROAS for all campaigns" | ranking | Multi-metric table |

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key for agent |
| `OPENAI_API_KEY` | OpenAI key for DeepEval metrics |
| `CONFIDENT_API_KEY` | Confident AI for test tracking |
| `REDIS_URL` | Redis for streaming (optional) |

### Prompts

The agent uses two main prompts in `app/agent/nodes.py`:

- `UNDERSTAND_PROMPT` - Intent classification and parameter extraction
- `RESPOND_PROMPT` - Natural language response generation

## Testing

### Run Golden Tests

```bash
pytest app/tests/qa_evaluation/test_qa_golden.py -v
```

### Run with DeepEval Metrics

```bash
CONFIDENT_METRIC_LOGGING_FLUSH=1 deepeval test run app/tests/qa_evaluation/test_qa_golden.py -v
```

### Test Agent Endpoint

```bash
curl -X POST 'http://localhost:8000/qa/agent/sync?workspace_id=YOUR_ID' \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is my ROAS this week?"}'
```

## Frontend Integration

### Copilot Page (Full Agent)

The Copilot page uses SSE streaming for typing effect:

```javascript
// ui/lib/api.js - fetchQA()
const res = await fetch(`${BASE}/qa/agent/sse?workspace_id=${id}`, {
  method: 'POST',
  body: JSON.stringify({ question })
});

const reader = res.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  // Process SSE events: thinking, token, visual, done
}
```

```javascript
// ui/app/(dashboard)/copilot/page.jsx
// Uses requestAnimationFrame to batch token updates for smooth typing
```

### Dashboard Widgets (Lightweight Insights)

Dashboard insight widgets use the lightweight `/qa/insights` endpoint:

```javascript
// ui/lib/api.js - fetchInsights()
const res = await fetch(`${BASE}/qa/insights?workspace_id=${id}`, {
  method: 'POST',
  body: JSON.stringify({ question })
});
const data = await res.json();
// Returns: { success, answer, intent }
```

**Widget Components:**
- `ui/app/(dashboard)/dashboard/components/AiInsightsPanel.jsx`
- `ui/app/(dashboard)/analytics/components/AnalyticsIntelligenceZone.jsx`
- `ui/app/(dashboard)/finance/components/AIFinancialSummary.jsx`

## Fallback Chain

The frontend tries endpoints in order:

1. **Agent SSE** (`/qa/agent/sse`) - Primary, streaming
2. **Semantic** (`/qa/semantic`) - Fallback, synchronous
3. **Legacy Stream** (`/qa/stream`) - Legacy SSE
4. **Legacy Polling** (`/qa`) - Final fallback

## Related Files

### Core Agent
- `app/agent/nodes.py` - Agent node implementations
- `app/agent/tools.py` - SemanticTools wrapper
- `app/agent/graph.py` - LangGraph StateGraph
- `app/agent/state.py` - AgentState definition
- `app/agent/stream.py` - Redis Pub/Sub streaming

### Semantic Layer
- `app/semantic/model.py` - Metric definitions
- `app/semantic/query.py` - SemanticQuery dataclass
- `app/semantic/compiler.py` - SQL compilation
- `app/semantic/validator.py` - Query validation

### API & Services
- `app/routers/qa.py` - API endpoints
- `app/services/semantic_qa_service.py` - Semantic QA service

### Frontend
- `ui/lib/api.js` - API client with SSE handling + fetchInsights
- `ui/hooks/useQA.js` - React hook for QA queries
- `ui/app/(dashboard)/copilot/page.jsx` - Copilot page
- `ui/app/(dashboard)/copilot/components/AnswerVisuals.jsx` - Charts and tables

### Insight Widgets
- `ui/app/(dashboard)/dashboard/components/AiInsightsPanel.jsx` - Dashboard insights
- `ui/app/(dashboard)/analytics/components/AnalyticsIntelligenceZone.jsx` - Analytics insights
- `ui/app/(dashboard)/finance/components/AIFinancialSummary.jsx` - Finance summary

## Version History

| Version | Description |
|---------|-------------|
| v1.0 | DSL-based translation |
| v2.0 | SSE streaming |
| v2.5 | Creative support |
| v3.0 | Semantic Layer |
| v4.0 | Agentic Copilot (LangGraph + Claude) |
| v4.1 | Lightweight insights endpoint, comparison timeseries |
