# AI Copilot Architecture

**Version**: 5.0.0 (Free Agent + Smart Data Source Selection)
**Last Updated**: 2025-12-22
**Status**: Production

---

## Overview

The metricx AI Copilot is a **free-form ReAct-style agent** that autonomously decides what tools to call based on the question. Key features:

- **GPT-4o-mini** (OpenAI) for cost-effective reasoning (95% cost reduction from Claude)
- **Smart Data Source Selection** - Snapshots first, Live API fallback
- **LangGraph** for agent loop with tool execution
- **SSE Streaming** for real-time token-by-token responses
- **User Feedback Handling** - Automatically verifies data when user questions accuracy

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI COPILOT ARCHITECTURE (v5.0)                       │
└─────────────────────────────────────────────────────────────────────────────┘

  User Question
  ─────────────
       │
       ▼
  POST /qa/agent/sse
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FREE AGENT LOOP (ReAct Style)                         │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         agent_loop_node                               │   │
│  │                                                                       │   │
│  │   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐            │   │
│  │   │   LLM sees  │────▶│ Tool Calls? │────▶│  Execute    │            │   │
│  │   │   question  │     │             │     │  Tools      │            │   │
│  │   │   + tools   │     │   YES       │     │             │            │   │
│  │   └─────────────┘     └──────┬──────┘     └──────┬──────┘            │   │
│  │                              │                   │                    │   │
│  │                              │ NO                │                    │   │
│  │                              ▼                   │                    │   │
│  │                       ┌─────────────┐            │                    │   │
│  │                       │  Generate   │◄───────────┘                    │   │
│  │                       │  Answer     │     (loop until ready)          │   │
│  │                       └─────────────┘                                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  AVAILABLE TOOLS:                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │query_metrics │  │google_ads_   │  │meta_ads_     │  │list_entities │    │
│  │  (Snapshots) │  │query (Live)  │  │query (Live)  │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
│  SSE Events: thinking → tool_call → tool_result → token → done              │
└─────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                       │
│                                                                              │
│  ┌────────────────────────────────┐   ┌────────────────────────────────┐   │
│  │       SNAPSHOTS (Primary)      │   │      LIVE API (Fallback)       │   │
│  │                                │   │                                │   │
│  │  • Updated every 15 minutes    │   │  • Google Ads API              │   │
│  │  • Fast (no external calls)    │   │  • Meta Ads API                │   │
│  │  • Campaign-level aggregation  │   │  • Rate limited                │   │
│  │                                │   │                                │   │
│  │  USE FOR:                      │   │  USE FOR:                      │   │
│  │  - spend, revenue, ROAS        │   │  - Campaign start_date         │   │
│  │  - CPC, CTR, CPA               │   │  - Keywords, search terms      │   │
│  │  - Conversions, clicks         │   │  - Audiences, targeting        │   │
│  │  - Trends, comparisons         │   │  - "Real-time" requests        │   │
│  │                                │   │  - User data verification      │   │
│  └────────────────────────────────┘   └────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Change: Free Agent vs Rigid Pipeline

### Old Architecture (v4.0)

```
Question → understand_node (classify intent) → fixed route → specific tool → respond
```

The old system classified questions into rigid intents (metric_query, comparison, ranking) and followed pre-defined paths.

### New Architecture (v5.0)

```
Question → LLM with ALL tools → LLM decides what to call → execute →
        → LLM sees results → LLM decides: more tools? or answer? → respond
```

The new ReAct-style agent autonomously decides:
1. Which tools to call (if any)
2. What arguments to pass
3. Whether to call more tools or answer
4. How to present the data

---

## LLM Provider: OpenAI

**Model**: `gpt-4o-mini`

**Location**: `backend/app/agent/nodes.py`

**Why Changed from Claude**: 95% cost reduction while maintaining quality for tool-calling tasks.

**Environment**: `OPENAI_API_KEY`

```python
# backend/app/agent/nodes.py

from openai import OpenAI, AsyncOpenAI

def get_openai_client() -> OpenAI:
    return OpenAI()

def get_async_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI()
```

---

## Smart Data Source Selection

### Priority Order

| Data Type | First Choice | Fallback | When to Fallback |
|-----------|--------------|----------|------------------|
| Metrics (spend, ROAS, etc.) | Snapshots (DB) | Live API | User says "real-time" OR snapshot stale |
| Campaign config (budget, status) | Snapshots | Live API | start_date, keywords not in DB |
| Keywords, search terms | Live API only | N/A | Not stored in snapshots |
| Audiences, targeting | Live API only | N/A | Not stored in snapshots |

### Response Transparency

The agent ALWAYS tells the user about data freshness:

```
✅ "Your spend today is $1,234 (data from 12:30 PM, ~8 min ago)"
✅ "Your ROAS is 3.2x (live from Google Ads)"
❌ "Your ROAS is 3.2x" (no context - BAD!)
```

### User Feedback Handling

When user says "this is wrong", "doesn't match", etc.:

1. **Acknowledge**: "I apologize for the discrepancy."
2. **Explain**: "The previous data came from our cached snapshots."
3. **Verify**: Automatically call live API to fetch fresh data
4. **Compare**: Show live vs cached and explain the difference

---

## Available Tools

### 1. query_metrics (Snapshots - Primary)

```python
{
    "name": "query_metrics",
    "description": "Query metrics from database snapshots (updated every 15 min)",
    "parameters": {
        "metrics": ["spend", "revenue", "roas", "cpc", "ctr", "conversions"],
        "time_range": "7d",  # 1d, 7d, 14d, 30d, 90d
        "breakdown_level": "campaign",  # campaign, adset, ad, provider
        "compare_to_previous": false,
        "include_timeseries": false
    }
}
```

**Returns**: Metric values + `snapshot_time` + `snapshot_age_minutes`

### 2. google_ads_query (Live API)

```python
{
    "name": "google_ads_query",
    "description": "Query Google Ads API directly for data not in snapshots",
    "parameters": {
        "query_type": "campaigns",  # campaigns, keywords, search_terms, metrics
        "fields": ["name", "status", "start_date"],
        "filters": {"status": "ENABLED"},
        "date_range": "today"
    }
}
```

**Use for**: Campaign start_date, keywords, search terms, real-time data

### 3. meta_ads_query (Live API)

```python
{
    "name": "meta_ads_query",
    "description": "Query Meta Ads API directly",
    "parameters": {
        "query_type": "campaigns",  # campaigns, adsets, ads, metrics
        "fields": ["name", "status", "targeting"],
        "filters": {},
        "date_range": "last_7d"
    }
}
```

**Use for**: Audiences, targeting details, creative info

### 4. list_entities

```python
{
    "name": "list_entities",
    "description": "List campaigns/adsets/ads from database",
    "parameters": {
        "level": "campaign",
        "name_contains": "Summer",
        "provider": "google"
    }
}
```

### 5. get_business_context

```python
{
    "name": "get_business_context",
    "description": "Get user's business profile (company, industry, markets)"
}
```

---

## Agent Loop Implementation

```python
# backend/app/agent/nodes.py

MAX_ITERATIONS = 5
MAX_TOOL_CALLS_PER_ITERATION = 3

async def agent_loop_node(state: AgentState, db: Session, publisher) -> Dict:
    """
    ReAct-style agent loop.

    1. Send question + tools to LLM
    2. If LLM returns tool_calls → execute, add results, loop
    3. If LLM returns content → done, return answer
    4. Max 5 iterations to prevent runaway
    """
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": state["current_question"]}
    ]

    iteration = 0
    while iteration < MAX_ITERATIONS:
        iteration += 1

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=AGENT_TOOLS,
            tool_choice="auto"
        )

        message = response.choices[0].message

        # No tool calls = ready to answer
        if not message.tool_calls:
            return {"answer_chunks": [message.content], "stage": "done"}

        # Execute tool calls
        for tool_call in message.tool_calls:
            result = await execute_tool_async(tool_call.function.name, ...)
            messages.append({"role": "tool", "content": json.dumps(result)})

    return {"answer_chunks": ["Max iterations reached"], "stage": "done"}
```

---

## Critical: Campaign-Level Aggregation

### The Problem

The entity hierarchy stores metrics at ALL levels:
```
Campaign "Summer Sale" → spend: $500
  └─ Adset "US Audience" → spend: $500 (same data!)
      └─ Ad "Banner 1" → spend: $500 (same data again!)
```

Without filtering, queries would sum: $500 + $500 + $500 = $1,500 (3x actual)

### The Solution

All aggregation queries default to `level='campaign'`:

```python
# backend/app/services/unified_metric_service.py

def _get_base_totals(self, workspace_id, start_date, end_date, filters):
    # Default to campaign-level to avoid double/triple counting
    level_filter = filters.level if filters.level else "campaign"

    query = (
        self.db.query(...)
        .filter(self.E.level == level_filter)  # CRITICAL
        ...
    )
```

This matches dashboard behavior and ensures copilot numbers match UI.

---

## SSE Streaming

### Endpoint: `POST /qa/agent/sse`

**Location**: `backend/app/routers/qa.py`

### Event Types

| Event | Description | Example |
|-------|-------------|---------|
| `thinking` | Processing indicator | `{"type": "thinking", "data": "Understanding..."}` |
| `tool_call` | Tool being executed | `{"type": "tool_call", "data": {"tool": "query_metrics"}}` |
| `tool_result` | Tool returned data | `{"type": "tool_result", "data": {"tool": "...", "preview": "..."}}` |
| `token` | Single token (typing) | `{"type": "token", "data": "Your"}` |
| `done` | Final result | `{"type": "done", "data": {...}}` |
| `error` | Error occurred | `{"type": "error", "data": "..."}` |

### Flow

```
Client Request
       ↓
FastAPI Handler (async)
       ↓
AsyncQueuePublisher (events queue)
       ↓
agent_loop_node runs in background
       ↓
Events streamed via SSE
       ↓
Client (typing effect + tool indicators)
```

---

## Guardrails

| Guardrail | Value | Why |
|-----------|-------|-----|
| Max iterations | 5 | Prevent runaway loops |
| Max tool calls per iteration | 3 | Limit API usage per turn |
| Tool execution timeout | 30s | Prevent hanging |
| Rate limits | Per workspace | Google 15/min, Meta 30/min |
| Default level filter | campaign | Prevent double-counting |

---

## Example Query Flows

### Basic Metrics (Snapshots)

```
User: "What's my ROAS today?"

1. Agent calls: query_metrics(metrics=["roas"], time_range="1d")
2. Tool returns: { roas: 1.11, snapshot_time: "12:30 PM", snapshot_age_minutes: 8 }
3. Agent responds: "Your ROAS today is 1.11x (data from 12:30 PM, ~8 min ago)"
```

### Campaign Config (Live API)

```
User: "Which campaigns went live yesterday?"

1. Agent recognizes: start_date NOT in snapshots → need live API
2. Agent calls: google_ads_query(query_type="campaigns", fields=["start_date"],
                                 filters={start_date: "yesterday"})
3. Tool returns: [{ name: "Summer Sale", start_date: "2025-12-21" }, ...]
4. Agent responds: "2 campaigns went live yesterday: Summer Sale, Holiday Promo"
```

### User Feedback (Verification)

```
User: "This is wrong, my Google Ads shows different"

1. Agent acknowledges: "I apologize for the discrepancy. Let me verify..."
2. Agent calls: google_ads_query(query_type="metrics", date_range="today")
3. Tool returns live data
4. Agent compares and explains: "Here's the live data vs cached..."
```

---

## Performance

| Stage | Latency | Notes |
|-------|---------|-------|
| Initial LLM call | 300-500ms | GPT-4o-mini tool selection |
| Tool execution | 50-200ms | DB query (snapshots) |
| Tool execution | 500-2000ms | Live API call |
| Response generation | 200-500ms | GPT-4o-mini streaming |
| **Total (snapshots)** | **0.5-1.5s** | Fast path |
| **Total (live API)** | **1-3s** | Slow path |

---

## Files Reference

| File | Purpose |
|------|---------|
| `app/routers/qa.py` | SSE endpoint, async queue publisher |
| `app/agent/graph.py` | LangGraph state machine (simplified) |
| `app/agent/nodes.py` | agent_loop_node, execute_tool_async, system prompts |
| `app/agent/state.py` | AgentState schema |
| `app/agent/tools.py` | AGENT_TOOLS schema, SemanticTools class |
| `app/agent/stream.py` | AsyncQueuePublisher for SSE |
| `app/agent/connection_resolver.py` | Get authenticated API clients |
| `app/agent/live_api_tools.py` | Live API tool implementations |
| `app/agent/rate_limiter.py` | Per-workspace rate limiting |
| `app/services/unified_metric_service.py` | Single source of truth (campaign-level default) |
| `app/services/google_ads_client.py` | Google Ads API client |

---

## Migration from v4.0

### What Changed

| Aspect | v4.0 (Rigid Pipeline) | v5.0 (Free Agent) |
|--------|----------------------|-------------------|
| LLM | Claude Sonnet 4 | GPT-4o-mini |
| Flow | understand → fetch → respond | Single agent loop |
| Tool Selection | Pre-defined by intent | LLM decides autonomously |
| Data Source | Snapshots only | Smart selection (snapshots + live) |
| User Feedback | Manual retry | Auto-verification with live API |
| Cost | ~$0.015/query | ~$0.0008/query (95% reduction) |

### Backward Compatibility

- Old `/qa/agent/sse` endpoint still works (uses new agent internally)
- Old `/qa/agent/sync` endpoint still works
- Legacy `/qa` returns 410 Gone
