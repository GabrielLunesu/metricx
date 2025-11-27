# metricx Agentic Marketing Copilot - Evolution Plan

## Executive Summary

Transform metricx from a **reactive Q&A tool** into a **proactive, intelligent marketing agent** that can explain, diagnose, recommend, and act.

**Immediate Priority**: Fix context/follow-up issues (system struggles with conversation context)

---

## User Requirements

| Requirement | Decision |
|-------------|----------|
| Platform Support | Meta only (no Google OAuth yet) |
| Action Execution | Never auto-execute - ALL actions require approval |
| Memory Persistence | Session-based only |
| Alert Delivery | Real-time (critical) |
| LLM Budget | No ceiling - use best models |

---

## Phase 0: Fix Context Management (Weeks 1-2) ⭐ IMMEDIATE

### Problem
Follow-up questions fail because:
- Context window too small (only 5 entries)
- Context summary too abbreviated (only top 3 breakdown items)
- Missing DSL info (breakdown dimension not preserved)
- No topic change detection
- No tests for follow-up scenarios

### Solution

| Fix | File | Change |
|-----|------|--------|
| Increase context window | `context_manager.py:85` | 5 → 15 entries |
| More breakdown items | `translator.py:361` | 3 → 10 items |
| Add breakdown dimension | `translator.py:378` | Include in context summary |
| Topic change detection | New: `topic_detector.py` | Detect new topic vs follow-up |
| Enhanced few-shot examples | `prompts.py` | Add 5+ follow-up patterns |
| Test suite | New: `test_follow_up_resolution.py` | 10+ test cases |

### Success Criteria
- "Which one performed best?" → Works after breakdown
- "And yesterday?" → Inherits metric correctly
- "What about CPA?" → Inherits breakdown dimension
- 10+ turn conversations → Context maintained

---

## Phase 1: Multi-Model Router (Weeks 3-6)

### Architecture
```
User Query → Intent Router → Appropriate Pipeline
                ↓
    ┌──────────┼──────────┬──────────┐
    ↓          ↓          ↓          ↓
 Factual   Educational  Causal    Rule
 (DSL)     (Knowledge)  (Reason)  (Tool)
```

### Model Strategy (Best per task)

| Intent | Model | Why |
|--------|-------|-----|
| Factual (DSL) | GPT-4o-mini | Fast, accurate |
| Educational | Claude Sonnet | Better explanations |
| Causal Reasoning | Claude Opus | Deep reasoning |
| Tool Calling | GPT-4o | Best tool use |

### Deliverables
- Intent router with 6-way classification
- Tool registry and base interface
- Core data tools (metrics, timeseries, breakdown)
- Streaming for multi-step responses

---

## Phase 2: Educational Intelligence (Weeks 7-10)

### Goal
Answer "What is X?" questions with marketing expertise

### Approach
- Marketing knowledge base (500+ concepts: ROAS, CPA, CTR definitions)
- RAG system with embeddings for context-aware explanations
- Personalized by user expertise level
- Visual explainers for metrics

### Example
```
User: "What is ROAS and why does it matter?"

Copilot: "ROAS = Revenue ÷ Ad Spend. You're at 3.45× (earning $3.45 per $1 spent).
Industry average: 2-4×. You're above average - good performance!"
```

---

## Phase 3: Causal Analysis (Weeks 11-14)

### Goal
Answer "Why did X happen?" with root cause analysis

### Approach
- Anomaly detection (identify significant changes)
- Correlation analysis (find factors that correlate)
- Hypothesis generation and ranking
- Evidence-based explanations

### Example
```
User: "Why did my ROAS drop this week?"

Copilot: "3 contributing factors:
1. CPC Spike (+51%) - Meta auction more competitive
2. CVR Drop (-34%) - Landing page load time increased
3. Budget concentration - 70% went to lowest performer

Recommendations: Reduce Meta bids 15%, check landing page, reallocate budget"
```

---

## Phase 4: Rule Engine (Weeks 15-18)

### Vision
Users create custom automation rules. Copilot can suggest and create rules via tool calling.

### User Flow
1. User: "Notify me when I hit $10k revenue today"
2. Copilot: "I'll create a rule - when daily revenue >= $10,000, notify you. Want me to create it?"
3. User: "Yes"
4. Rule saved, monitoring starts, real-time notification when triggered

### Architecture

| Component | Purpose |
|-----------|---------|
| Rule Model | Store trigger conditions + actions |
| Rule Manager | CRUD + validation |
| Rule Executor | Evaluate conditions, dispatch actions |
| Rule Tool | Copilot can suggest/create rules |
| Rules UI | `/rules` page for manual management |
| Scheduler | 5-min evaluation cycle |

### Rule Types

| Trigger | Example |
|---------|---------|
| Metric Threshold | Revenue >= $10,000 |
| Metric Change | ROAS drops > 20% |
| Anomaly | Statistical deviation detected |

| Action | Example |
|--------|---------|
| Notify | In-app, email (real-time) |
| Pause Campaign | Future - requires approval |
| Scale Budget | Future - requires approval |

---

## Phase 5: Recommendations + Memory (Weeks 19-22)

### Recommendations
- Opportunity detector framework
- Budget reallocation suggestions
- Scaling opportunities for high performers
- Creative fatigue detection
- "Simulate impact" feature

### Memory (Session-Based)
- Short-term: Last 15 queries (in-memory)
- User preferences learned during session
- Patterns detected during conversation
- Resets when session ends

---

## Phase 6: Actions (Future)

Deferred to later stage. When implemented:
- Meta API integration only (initially)
- ALL actions require explicit approval
- Audit trail for every action
- Monitoring for executed changes

---

## Key Files to Modify

### Phase 0 (Context Fixes)
- `backend/app/context/context_manager.py`
- `backend/app/nlp/translator.py`
- `backend/app/nlp/prompts.py`
- New: `backend/app/nlp/topic_detector.py`
- New: `backend/app/tests/test_follow_up_resolution.py`

### Phase 1 (Router)
- New: `backend/app/routing/intent_router.py`
- New: `backend/app/tools/registry.py`

### Phase 4 (Rules)
- New: `backend/app/models/rule.py`
- New: `backend/app/services/rule_manager.py`
- New: `backend/app/services/rule_executor.py`
- New: `backend/app/tools/rule_tool.py`
- New: `ui/app/(dashboard)/rules/page.jsx`

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Follow-up success rate | ~60% | 95% |
| Educational query support | 0% | 95% |
| Causal query support | 0% | 80% |
| Rule adoption | N/A | 50% of users |
| Real-time alert latency | N/A | < 30 seconds |

---

## Timeline Summary

| Phase | Weeks | Focus |
|-------|-------|-------|
| 0 | 1-2 | Context fixes (IMMEDIATE) |
| 1 | 3-6 | Multi-model router + tools |
| 2 | 7-10 | Educational intelligence |
| 3 | 11-14 | Causal analysis |
| 4 | 15-18 | Rule engine |
| 5 | 19-22 | Recommendations + memory |
| 6 | Future | Actions (Meta API) |

---

*Last Updated: 2025-11-25*
