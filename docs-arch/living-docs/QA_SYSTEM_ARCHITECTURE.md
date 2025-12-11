# AI Copilot Architecture

**Version**: 4.0.0 (Semantic Layer + Claude + LangGraph)
**Last Updated**: 2025-12-10
**Status**: Production

---

## Overview

The metricx AI Copilot is a **semantic query engine** that translates natural language questions into analytics queries using:

- **Claude Sonnet 4** (Anthropic) for understanding and response generation
- **Semantic Layer** for composable, type-safe queries
- **LangGraph** for structured agent workflows
- **SSE Streaming** for real-time token-by-token responses

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI COPILOT ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────┘

  User Question
  ─────────────
       │
       ▼
  POST /qa/agent/sse
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LANGGRAPH AGENT                                    │
│                                                                              │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │  understand_node │────▶│  fetch_data_node │────▶│   respond_node   │    │
│  │                  │     │                  │     │                  │    │
│  │  Claude extracts │     │  SemanticTools   │     │  Claude generates│    │
│  │  intent →        │     │  execute query → │     │  answer +        │    │
│  │  SemanticQuery   │     │  CompilationResult│     │  visuals         │    │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘    │
│           │                                                │                │
│           │                                                │                │
│           ▼                                                ▼                │
│  ┌──────────────────┐                              ┌──────────────────┐    │
│  │  error_node      │                              │  SSE Streaming   │    │
│  │  (if validation  │                              │  • tokens        │    │
│  │   fails)         │                              │  • visuals       │    │
│  └──────────────────┘                              │  • done          │    │
│                                                    └──────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SEMANTIC LAYER                                     │
│                                                                              │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │  SemanticQuery   │────▶│    Validator     │────▶│    Compiler      │    │
│  │  (model.py)      │     │  (validator.py)  │     │  (compiler.py)   │    │
│  │                  │     │                  │     │                  │    │
│  │  • metrics       │     │  • Schema check  │     │  • Strategy      │    │
│  │  • breakdown     │     │  • Permissions   │     │    selection     │    │
│  │  • comparison    │     │  • Data exists   │     │  • SQL building  │    │
│  │  • timeseries    │     │                  │     │  • Aggregation   │    │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘    │
│                                                             │               │
│                                                             ▼               │
│                                                    ┌──────────────────┐    │
│                                                    │ UnifiedMetric    │    │
│                                                    │ Service          │    │
│                                                    └──────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## LLM Provider: Claude (Anthropic)

**Model**: `claude-sonnet-4-20250514`

**Location**: `backend/app/agent/nodes.py`

**Clients**:
- `Anthropic()` - Synchronous client for blocking calls
- `AsyncAnthropic()` - Async client for SSE streaming

**Environment**: `ANTHROPIC_API_KEY`

```python
# backend/app/agent/nodes.py

from anthropic import Anthropic, AsyncAnthropic

def get_claude_client() -> Anthropic:
    return Anthropic()

def get_async_claude_client() -> AsyncAnthropic:
    return AsyncAnthropic()
```

---

## Semantic Layer (Composable Queries)

### What It Replaces

The old **DSL (Domain-Specific Language)** had mutually exclusive fields - you could have breakdown OR comparison, but not both. The semantic layer allows **composition**:

```python
# OLD DSL - IMPOSSIBLE to combine:
{
    "breakdown": "ad",      # Can't also have comparison!
    "compare_to_previous": true  # XOR
}

# NEW Semantic Layer - COMPOSABLE:
SemanticQuery(
    metrics=["cpc"],
    breakdown=Breakdown(dimension="entity", level="ad", limit=3),
    comparison=Comparison(type=ComparisonType.PREVIOUS_PERIOD),
    include_timeseries=True
)
```

### Files

| File | Purpose |
|------|---------|
| `app/semantic/model.py` | Metric/dimension definitions |
| `app/semantic/query.py` | SemanticQuery, Breakdown, Comparison classes |
| `app/semantic/validator.py` | Query validation (permissions, data existence) |
| `app/semantic/compiler.py` | Query → SQL execution strategy |

### SemanticQuery Structure

```python
@dataclass
class SemanticQuery:
    # What to measure
    metrics: List[str]  # ["cpc", "roas", "spend"]

    # Time range
    time_range: TimeRange  # last_n_days or start/end

    # Optional composition
    breakdown: Optional[Breakdown] = None      # Group by entity/provider/time
    comparison: Optional[Comparison] = None    # vs previous period
    include_timeseries: bool = False           # Daily/hourly breakdown

    # Filters
    filters: Optional[Filters] = None          # provider, level, status
```

### Breakdown Types

```python
class Breakdown:
    dimension: str  # "entity", "provider", "temporal"
    level: str      # "campaign", "adset", "ad" (for entity)
    limit: int      # Top N results
    sort_order: str # "desc" or "asc"
```

### Comparison Types

```python
class ComparisonType(Enum):
    PREVIOUS_PERIOD = "previous_period"   # Last 7 days vs 7-14 days ago
    YEAR_OVER_YEAR = "year_over_year"     # This week vs same week last year
    CUSTOM = "custom"                      # Custom date range
```

---

## LangGraph Agent

### State Machine

```
START
   │
   ▼
understand_node ───────────────────────────┐
   │                                       │
   │ [intent extracted]                    │ [clarification needed]
   │                                       │
   ▼                                       ▼
fetch_data_node                      respond_node (clarify)
   │                                       │
   │ [data fetched]                        │
   │                                       │
   ▼                                       │
respond_node ◄─────────────────────────────┘
   │
   ▼
END
```

### Nodes

**1. understand_node** (`app/agent/nodes.py`)
- Claude analyzes question and conversation context
- Extracts intent → SemanticQuery
- Routes to fetch_data or respond (if clarification needed)

**2. fetch_data_node** (`app/agent/nodes.py`)
- Calls SemanticTools with the query
- Tools call Semantic Layer → UnifiedMetricService
- Returns CompilationResult with metrics

**3. respond_node** (`app/agent/nodes.py`)
- Claude generates natural language answer
- Builds visual spec (chart/table/card)
- Streams response via SSE

**4. error_node** (`app/agent/nodes.py`)
- Handles validation errors gracefully
- Returns helpful error message

### State Schema

```python
# app/agent/state.py

class AgentState(TypedDict):
    question: str
    workspace_id: str
    user_id: str

    # Extracted by understand_node
    intent: Optional[str]
    semantic_query: Optional[SemanticQuery]

    # Fetched by fetch_data_node
    data: Optional[CompilationResult]

    # Generated by respond_node
    answer: Optional[str]
    visuals: Optional[dict]

    # Error handling
    error: Optional[str]
```

---

## SSE Streaming

### Endpoint: `POST /qa/agent/sse`

**Location**: `backend/app/routers/qa.py`

### Flow

```
Client Request
       ↓
FastAPI Handler (async)
       ↓
AsyncAnthropic Client
       ↓
async for token in stream.text_stream
       ↓
yield SSE events
       ↓
Client (typing effect)
```

### Event Types

| Event | Description | Example |
|-------|-------------|---------|
| `thinking` | Processing indicator | `{"type": "thinking", "data": "Understanding your question..."}` |
| `token` | Single token (typing) | `{"type": "token", "data": "Your"}` |
| `visual` | Chart/table spec | `{"type": "visual", "data": {...}}` |
| `done` | Final result | `{"type": "done", "data": {"answer": "...", "visuals": {...}}}` |
| `error` | Error occurred | `{"type": "error", "data": "..."}` |

### Non-Blocking Architecture

```python
# backend/app/routers/qa.py

@router.post("/qa/agent/sse")
async def agent_sse(request: AgentRequest, ...):

    # 1. Async Claude call (non-blocking)
    client = get_async_claude_client()

    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        messages=messages,
        max_tokens=1024,
    ) as stream:
        async for text in stream.text_stream:
            yield f"data: {json.dumps({'type': 'token', 'data': text})}\n\n"

    # 2. DB queries run in thread pool (SQLAlchemy is sync)
    def fetch_data_sync():
        tools = SemanticTools(db, workspace_id, user_id)
        return tools.query_metrics(semantic_query)

    result = await asyncio.to_thread(fetch_data_sync)
```

**Why this matters:**
- Sync Claude API would block event loop for 5+ seconds
- Async client allows FastAPI to handle other requests concurrently
- DB queries offloaded to thread pool (SQLAlchemy is sync)

---

## SemanticTools

**Location**: `backend/app/agent/tools.py`

Interface between LangGraph agent and Semantic Layer.

### Methods

```python
class SemanticTools:
    def __init__(self, db: Session, workspace_id: UUID, user_id: UUID):
        ...

    def query_metrics(self, query: SemanticQuery) -> CompilationResult:
        """
        Main data fetching - supports all compositions:
        - Simple metrics
        - Breakdowns (top N by entity/provider/time)
        - Comparisons (vs previous period)
        - Timeseries (daily/hourly)
        """

    def get_entities(self, filters: Filters) -> List[Entity]:
        """List campaigns/adsets/ads with filters."""

    def analyze_change(self, metric: str, time_range: TimeRange) -> ChangeAnalysis:
        """
        "Why" questions - compares periods, finds:
        - Top contributors to change
        - Anomalies
        - Trend direction
        """
```

### Security

All calls scoped by `workspace_id` - no raw SQL exposure:

```python
def query_metrics(self, query: SemanticQuery):
    # Workspace scoping at SQL level
    base = self.db.query(MetricSnapshot).join(Entity)
    base = base.filter(Entity.workspace_id == self.workspace_id)
    ...
```

---

## API Endpoints

### Current (v4.0)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/qa/agent/sse` | POST | **SSE streaming** (recommended) |
| `/qa/agent/sync` | POST | Synchronous (no streaming) |
| `/qa/semantic` | POST | Direct semantic layer access |
| `/qa/insights` | POST | Lightweight insights for dashboard widgets |

### Deprecated (410 Gone)

| Endpoint | Replacement |
|----------|-------------|
| `/qa` | `/qa/agent/sse` |
| `/qa/stream` | `/qa/agent/sse` |

---

## Example Query Flow

### User Question

```
"Compare CPC this week vs last week for top 3 ads"
```

### Step 1: understand_node

Claude extracts intent:

```python
SemanticQuery(
    metrics=["cpc"],
    time_range=TimeRange(last_n_days=7),
    breakdown=Breakdown(
        dimension="entity",
        level="ad",
        limit=3,
        sort_order="desc"
    ),
    comparison=Comparison(
        type=ComparisonType.PREVIOUS_PERIOD
    ),
    include_timeseries=True
)
```

### Step 2: fetch_data_node

Semantic Layer executes:

```python
CompilationResult(
    summary={"cpc": 0.48, "cpc_prev": 0.52, "cpc_delta_pct": -7.7},
    breakdown=[
        {"entity": "Summer Sale Ad", "cpc": 0.35, "cpc_prev": 0.42},
        {"entity": "Winter Promo", "cpc": 0.48, "cpc_prev": 0.51},
        {"entity": "Holiday Special", "cpc": 0.55, "cpc_prev": 0.58},
    ],
    timeseries=[
        {"date": "2025-12-04", "Summer Sale Ad": 0.32, "Winter Promo": 0.45, ...},
        {"date": "2025-12-05", "Summer Sale Ad": 0.38, "Winter Promo": 0.49, ...},
        ...
    ]
)
```

### Step 3: respond_node

Claude generates answer:

```
Your overall CPC this week is $0.48, down 7.7% from last week's $0.52.

Top 3 ads by CPC:
1. Summer Sale Ad: $0.35 (↓17% from $0.42)
2. Winter Promo: $0.48 (↓6% from $0.51)
3. Holiday Special: $0.55 (↓5% from $0.58)

All three ads showed improvement week-over-week.
```

Visual spec:

```json
{
  "type": "multi_line",
  "series": [
    {"name": "Summer Sale Ad", "data": [...]},
    {"name": "Winter Promo", "data": [...]},
    {"name": "Holiday Special", "data": [...]}
  ],
  "comparison": true
}
```

---

## Performance

| Stage | Latency | Notes |
|-------|---------|-------|
| understand_node | 500-1000ms | Claude intent extraction |
| Semantic validation | <10ms | Pydantic + custom rules |
| Semantic compilation | 50-200ms | DB queries via UnifiedMetricService |
| respond_node | 500-1500ms | Claude answer + streaming |
| **Total** | **1-3 seconds** | End-to-end |

### Optimizations

1. **Async streaming**: Non-blocking Claude calls
2. **Thread pool**: DB queries don't block event loop
3. **Connection pooling**: SQLAlchemy connection reuse
4. **JWKS caching**: Clerk key caching (1 hour)

---

## Observability

### Langfuse Integration

All LLM calls traced:

```python
from app.telemetry import create_copilot_trace, log_generation

trace = create_copilot_trace(user_id, workspace_id, question)

log_generation(
    trace=trace,
    name="understand",
    model="claude-sonnet-4-20250514",
    input_messages=messages,
    output=response,
    usage={"input": 100, "output": 50, "total": 150}
)
```

### Log Markers

| Marker | Location |
|--------|----------|
| `[AGENT]` | agent/nodes.py |
| `[SEMANTIC]` | semantic/*.py |
| `[TOOLS]` | agent/tools.py |
| `[STREAM]` | routers/qa.py |

---

## Files Reference

| File | Purpose |
|------|---------|
| `app/routers/qa.py` | API endpoints (SSE, sync, semantic) |
| `app/agent/graph.py` | LangGraph state machine |
| `app/agent/nodes.py` | Node implementations (understand, fetch_data, respond) |
| `app/agent/state.py` | State schema |
| `app/agent/tools.py` | SemanticTools class |
| `app/agent/stream.py` | Redis Pub/Sub streaming (background jobs) |
| `app/semantic/model.py` | Metric/dimension definitions |
| `app/semantic/query.py` | SemanticQuery, Breakdown, Comparison |
| `app/semantic/validator.py` | Query validation |
| `app/semantic/compiler.py` | Query execution |
| `app/services/unified_metric_service.py` | Single source of truth for metrics |
| `app/telemetry/llm_trace.py` | Langfuse integration |

---

## Migration from DSL

### What Changed

| Aspect | DSL (old) | Semantic Layer (new) |
|--------|-----------|---------------------|
| LLM | OpenAI GPT-4o | Claude Sonnet 4 |
| Query format | JSON DSL | SemanticQuery dataclass |
| Composition | Mutually exclusive fields | Fully composable |
| Streaming | RQ workers + polling | Direct SSE with AsyncAnthropic |
| Threading | Blocking | async/await + thread pool |
| Agent | Pipeline functions | LangGraph state machine |

### Backward Compatibility

Old DSL files still exist for legacy endpoints:
- `app/dsl/schema.py` - Used by `/routers/metrics.py`, `/routers/finance.py`
- QA system exclusively uses Semantic Layer

Old endpoints return 410 Gone:
```python
@router.post("/qa")
async def legacy_qa():
    raise HTTPException(410, "Use /qa/agent/sse instead")
```
