# Agentic Copilot Architecture

**Status**: Implemented
**Last Updated**: 2025-12-03

---

## Goal

A fully agentic copilot that feels like talking to a smart human analyst. It should:
- Understand any natural language question
- Remember conversation context
- Explain why it can't answer something (never just fail)
- Stream answers and visuals in real-time (typing effect)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                    │
│  SSE subscribes to Redis channel: qa:{job_id}:stream                    │
│  Renders tokens as they arrive (typing effect)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ Redis Pub/Sub
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                           REDIS                                          │
│  • Queue: qa_jobs (RQ)                                                  │
│  • Pub/Sub: qa:{job_id}:stream (real-time tokens)                       │
│  • State: job.meta (stage, final result)                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                         WORKER (LangGraph Agent)                         │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                        LANGGRAPH AGENT                              │ │
│  │                                                                      │ │
│  │  State:                                                              │ │
│  │  • messages (conversation history)                                   │ │
│  │  • current_query (SemanticQuery)                                    │ │
│  │  • data (fetched results)                                           │ │
│  │  • answer (streaming)                                               │ │
│  │  • visuals (streaming)                                              │ │
│  │                                                                      │ │
│  │  Nodes:                                                              │ │
│  │  • understand    → classify intent, build SemanticQuery             │ │
│  │  • fetch_data    → call semantic layer tools                        │ │
│  │  • analyze       → reason about data (for "why?" questions)         │ │
│  │  • respond       → stream answer + visuals                          │ │
│  │  • clarify       → ask user for more info (if ambiguous)            │ │
│  │  • explain_limit → explain why we can't answer                      │ │
│  │                                                                      │ │
│  │  Tools:                                                              │ │
│  │  • query_metrics(SemanticQuery) → CompilationResult                 │ │
│  │  • get_entities(level, limit)   → list of campaigns/ads/etc         │ │
│  │  • compare_periods(metric)      → comparison data                   │ │
│  │  • analyze_change(metric)       → find what changed and why         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│                                    ▼                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      SEMANTIC LAYER (exists)                        │ │
│  │  • SemanticQuery, Validator, Compiler                               │ │
│  │  • Already built, agent uses as tools                               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                              API                                         │
│  POST /qa/agent → enqueue job → return job_id                           │
│  GET  /qa/agent/stream/{job_id} → SSE subscribe to Redis channel        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Streaming Flow

```
1. User asks: "Why is my ROAS down?"

2. API enqueues job, returns job_id
   Frontend connects to SSE: /qa/agent/stream/{job_id}

3. Worker starts LangGraph agent

4. Agent node: "understand"
   → Publishes: {"type": "thinking", "text": "Analyzing your question..."}

5. Agent node: "fetch_data"
   → Publishes: {"type": "tool_call", "tool": "compare_periods", "args": {...}}
   → Publishes: {"type": "tool_result", "preview": "ROAS: 6.24× (was 6.87×)"}

6. Agent node: "analyze"
   → Publishes: {"type": "thinking", "text": "Looking for what changed..."}
   → Calls analyze_change tool

7. Agent node: "respond"
   → Publishes: {"type": "answer", "token": "Your"}
   → Publishes: {"type": "answer", "token": " ROAS"}
   → Publishes: {"type": "answer", "token": " dropped"}
   → ... (token by token, typing effect)

   → Publishes: {"type": "visual", "partial": {"type": "chart", "title": "..."}}
   → Publishes: {"type": "visual", "data": [...]}  (data fills in)

8. Agent complete
   → Publishes: {"type": "done", "final": {...}}
   → Updates job.meta with final result
```

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Agent Framework | **LangGraph** | Stateful agents, built-in streaming, retries |
| LLM | **Claude** | Best reasoning, natural tone, good at explaining limits |
| Streaming | **Redis Pub/Sub** | Real-time, you already have Redis |
| Queue | **RQ** (existing) | Keep current worker infra |
| Data Layer | **Semantic Layer** (existing) | Already built, becomes agent's toolkit |

---

## Agent Behavior

### Always Responds
The agent never just fails. Every path leads to a response:

| Situation | Agent Behavior |
|-----------|----------------|
| Clear question | Answer it |
| Ambiguous question | Ask for clarification |
| Outside scope | Explain what it can/can't do |
| No data found | Explain why, suggest alternatives |
| Error occurs | Retry, or explain the issue |

### Knows Its Limits
The agent is honest about boundaries:

- "I can only answer questions about your advertising data"
- "I don't have access to data before [date]"
- "I can see performance but can't take actions like pausing campaigns"
- "I'm not sure about that - here's what I do know..."

### Remembers Context
Conversation flows naturally:

```
User: "What's my ROAS?"
Agent: "Your ROAS is 6.24× for the last 7 days."

User: "How about for Meta?"
Agent: "Your Meta ROAS is 7.1× for the same period."
       (understood "How about" = same metric, add filter)

User: "Why is it higher than Google?"
Agent: "Meta has higher ROAS because..."
       (understood comparison context)
```

---

## Files to Create/Modify

### New Files
```
backend/app/agent/
├── __init__.py
├── graph.py          # LangGraph definition
├── nodes.py          # Agent nodes (understand, fetch, respond, etc.)
├── tools.py          # Semantic layer wrappers
├── state.py          # Agent state schema
└── stream.py         # Redis pub/sub streaming

backend/app/workers/
└── agent_worker.py   # RQ job handler for agent
```

### Modified Files
```
backend/app/routers/qa.py      # Add /qa/agent endpoints
backend/app/state.py           # Add Redis pub/sub client
```

---

## Acceptance Criteria

**All questions from `backend/run_qa_tests.sh` must work.** Categories:

### Basic Metrics
- [ ] "What's my CPC this month?"
- [ ] "How much did I spend this month?"
- [ ] "What's my ROAS this week?"
- [ ] "How much revenue did I generate yesterday?"
- [ ] "What's my conversion rate?"
- [ ] "How many clicks did I get last week?"
- [ ] "What is my average order value?"

### Time Ranges
- [ ] "How much revenue in the last week?"
- [ ] "What was my revenue last month?"
- [ ] "What is my revenue this year?"
- [ ] "All ad sets above roas 4 in the last 3 days"

### Comparisons
- [ ] "How does this week compare to last week?"
- [ ] "Compare Google vs Meta performance"
- [ ] "Is my ROAS improving or declining?"
- [ ] "Compare holiday campaign performance to app install campaign"
- [ ] "Which had highest cpc, holiday campaign or app install campaign?"

### Breakdowns & Rankings
- [ ] "Which campaign had the highest ROAS last week?"
- [ ] "Show me top 5 campaigns by revenue"
- [ ] "List all active campaigns"
- [ ] "Which adset had the highest cpc last week?"
- [ ] "Which ad has the highest CTR?"
- [ ] "Rank platforms by cost per conversion"

### Filters
- [ ] "Show me campaigns with ROAS above 4"
- [ ] "Show me adsets with cpc below 1 dollar"
- [ ] "All campaigns with conversion rate above 5%"
- [ ] "Show me ads with revenue above 1000"
- [ ] "What's my ROAS for Google campaigns only?"

### Named Entity Queries
- [ ] "How is the Summer Sale campaign performing?"
- [ ] "What's the revenue for Black Friday campaign?"
- [ ] "How much did Holiday Sale campaign spend last week?"
- [ ] "Best performing ad set in Holiday Sale campaign yesterday?"
- [ ] "Worst performing ad in App Install campaign?"

### Follow-up Questions (Context)
- [ ] "How much did I spend last month?" → "Which campaign had the highest spend?" → "Which ads in that campaign performed best?"
- [ ] "How much revenue in the last week?" → "Which campaign brought in the most?" → "How many conversions did that campaign deliver?"

### Multi-Entity + Multi-Metric Combinations
- [ ] "Compare CPC, CTR, and ROAS for Holiday Sale and App Install campaigns last week"
- [ ] "What's the spend, revenue, and ROAS for all Google campaigns in September?"
- [ ] "Give me CTR, CPC, and conversion rate for Summer Sale campaign last month"
- [ ] "Compare spend and revenue between Morning Audience and Evening Audience adsets"

### Typos & Natural Language
- [ ] "wich ad had the lowest cpc last week?" (typo: wich)
- [ ] "wich google campaigns are live?" (typo: wich)
- [ ] "give me a breakdown of holiday campaign performance"

### Edge Cases
- [ ] "How much revenue would I have last week if my CPC was 0.20?" (hypothetical - should explain can't do)
- [ ] "What's my cost per install?" (may have no data - should explain)
- [ ] "How many leads did I generate today?" (may be zero - should handle gracefully)

### Must Feel Right
- [ ] Typing effect feels natural (not too fast, not choppy)
- [ ] Visuals appear progressively
- [ ] Errors are friendly explanations, not technical messages
- [ ] Agent sounds like a knowledgeable analyst
- [ ] Handles typos gracefully

---

## Implementation Complete

All components have been built:

### Files Created
```
backend/app/agent/
├── __init__.py       # Module exports
├── state.py          # AgentState TypedDict, Message dataclass
├── tools.py          # SemanticTools class wrapping semantic layer
├── nodes.py          # understand, fetch_data, respond, error nodes
├── graph.py          # LangGraph StateGraph definition
└── stream.py         # Redis Pub/Sub StreamPublisher/StreamSubscriber

backend/app/workers/
└── agent_worker.py   # RQ job handler with streaming support
```

### API Endpoints Added
- `POST /qa/agent` - Enqueue agent job, returns job_id
- `GET /qa/agent/stream/{job_id}` - SSE stream for real-time responses
- `POST /qa/agent/sync` - Synchronous agent (for testing)

### Next Steps
1. Set ANTHROPIC_API_KEY in environment
2. Test with `POST /qa/agent/sync?workspace_id=...`
3. Connect frontend to `/qa/agent/stream/{job_id}`
4. Iterate on prompt engineering in `nodes.py` for better responses
