# Agent System Architecture

This document describes the Agent System - autonomous monitoring entities that watch ad performance metrics, evaluate conditions over time, and take actions like notifications, budget scaling, and campaign pausing.

**Version**: 1.0.0
**Last Updated**: 2026-01-26
**Status**: Living Document

## Overview

The Agent System enables merchants to set up autonomous monitors ("agents") that:
- Watch specific campaigns, ad sets, or ads
- Evaluate conditions against real-time metrics (ROAS > 2, CPC < $3)
- Track accumulation over time ("ROAS > 2 for 3 consecutive days")
- Execute actions when triggered (email, scale budget, pause campaign)
- Provide full observability with event sourcing

**Design Principles:**
- **Event Sourced**: Every evaluation produces an immutable event
- **Stateful**: Agents track accumulation state per entity
- **Extensible**: Pluggable conditions and actions
- **Observable**: Full audit trail, real-time WebSocket updates
- **AI-Native**: Create agents via Copilot natural language

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Frontend (Next.js)                        │
│  Copilot (create via NL) │ /agents (list) │ /agents/[id] (detail)  │
└─────────────────────────────────────────────────────────────────────┘
                              │ REST + WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Backend (FastAPI)                           │
│                                                                     │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │ Agent Router    │  │ Evaluation Engine │  │ Action Executor  │   │
│  │ (CRUD + Status) │  │ (Core Logic)      │  │ (Platform APIs)  │   │
│  └─────────────────┘  └──────────────────┘  └──────────────────┘   │
│                                                                     │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │ Copilot Tools   │  │ Condition System │  │ Notification Svc │   │
│  │ (NL Agent Mgmt) │  │ (Threshold, etc) │  │ (Resend Email)   │   │
│  └─────────────────┘  └──────────────────┘  └──────────────────┘   │
│                                                                     │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │ State Machine   │  │ Platform Health  │  │ WebSocket Mgr    │   │
│  │ (Transitions)   │  │ (API Checks)     │  │ (Real-time)      │   │
│  └─────────────────┘  └──────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Background Workers (ARQ)                       │
│  scheduled_agent_evaluation() - Every 15 min (synced with metrics)  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        PostgreSQL                                   │
│  agents │ agent_entity_states │ agent_evaluation_events │ actions   │
└─────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
backend/app/
├── routers/
│   └── agents.py                    # REST API endpoints
│
├── agent/
│   └── tools.py                     # Copilot tools (AgentManagementTools)
│
├── services/agents/
│   ├── __init__.py
│   ├── conditions.py                # Condition classes (Threshold, Change, Composite)
│   ├── actions.py                   # Action classes (Email, ScaleBudget, Pause)
│   ├── evaluation_engine.py         # Core evaluation logic (AgentEvaluationEngine)
│   ├── state_machine.py             # State transitions (AgentStateMachine)
│   ├── action_executor.py           # Platform-aware action execution
│   ├── platform_health.py           # Connection health checks
│   ├── platform_actions_meta.py     # Meta Ads API integration
│   ├── platform_actions_google.py   # Google Ads API integration
│   ├── notification_service.py      # Resend email integration
│   └── websocket_manager.py         # Real-time event streaming
│
├── models.py                        # SQLAlchemy models (Agent, AgentEvaluationEvent, etc.)
├── schemas.py                       # Pydantic schemas (AgentCreate, AgentOut, etc.)
│
└── workers/
    └── arq_worker.py                # Background scheduler (scheduled_agent_evaluation)

ui/
├── app/(dashboard)/copilot/
│   └── components/
│       └── AgentPreviewCard.jsx     # Agent creation preview card
│
└── lib/
    └── api.js                       # createAgent API function
```

## Core Components

### 1. Database Models (`app/models.py`)

#### Agent
Main agent configuration table:
```python
class Agent:
    id: UUID                         # Primary key
    workspace_id: UUID               # Owner workspace
    name: str                        # Display name
    description: str                 # Optional description

    # Scope - What entities to watch
    scope_type: ScopeTypeEnum        # 'specific', 'filter', 'all'
    scope_config: JSONB              # Entity IDs or filter criteria

    # Condition - When to trigger
    condition: JSONB                 # Serialized condition tree

    # Accumulation - How long condition must be true
    accumulation_required: int       # Count needed (e.g., 3)
    accumulation_unit: Enum          # 'evaluations', 'hours', 'days'
    accumulation_mode: Enum          # 'consecutive', 'within_window'

    # Trigger behavior
    trigger_mode: Enum               # 'once', 'cooldown', 'continuous'
    cooldown_duration_minutes: int   # Wait time after trigger

    # Actions - What to do when triggered
    actions: JSONB                   # Array of action configs

    # Status
    status: AgentStatusEnum          # 'active', 'paused', 'error', 'draft'

    # Stats
    last_evaluated_at: datetime
    total_evaluations: int
    total_triggers: int
    last_triggered_at: datetime
```

#### AgentEntityState
Per-entity state tracking:
```python
class AgentEntityState:
    agent_id: UUID                   # FK to agent
    entity_id: UUID                  # FK to entity
    state: AgentStateEnum            # 'watching', 'accumulating', 'triggered', 'cooldown', 'error'
    accumulation_count: int          # Current accumulation
    accumulation_started_at: datetime
    accumulation_history: JSONB      # Timestamps of condition=true
    last_triggered_at: datetime
    trigger_count: int
    next_eligible_trigger_at: datetime
```

#### AgentEvaluationEvent
Immutable evaluation record:
```python
class AgentEvaluationEvent:
    id: UUID
    agent_id: UUID
    entity_id: UUID
    evaluated_at: datetime

    result_type: ResultTypeEnum      # 'triggered', 'condition_met', 'condition_not_met', 'cooldown', 'error'
    headline: str                    # One-liner for display

    observations: JSONB              # Metrics at evaluation time
    entity_snapshot: JSONB           # Entity state snapshot

    condition_definition: JSONB      # What was evaluated
    condition_inputs: JSONB          # What values were used
    condition_result: bool           # Did it pass?
    condition_explanation: str       # Human-readable explanation

    accumulation_before: JSONB       # State before
    accumulation_after: JSONB        # State after

    state_before: str
    state_after: str
    state_transition_reason: str

    should_trigger: bool
    trigger_explanation: str
    summary: str                     # For Copilot queries
```

#### AgentActionExecution
Action audit record:
```python
class AgentActionExecution:
    id: UUID
    evaluation_event_id: UUID
    agent_id: UUID

    action_type: ActionTypeEnum      # 'email', 'scale_budget', 'pause_campaign'
    action_config: JSONB

    executed_at: datetime
    success: bool
    description: str
    details: JSONB
    error: str

    state_before: JSONB              # For rollback
    state_after: JSONB
    rollback_possible: bool
```

### 2. Condition System (`app/services/agents/conditions.py`)

Abstract `Condition` base class with concrete implementations:

#### ThresholdCondition
```python
ThresholdCondition(metric="roas", operator="gt", value=2.0)
# → "ROAS > 2.0" → True if ROAS exceeds 2.0
```

Operators: `gt`, `gte`, `lt`, `lte`, `eq`, `neq`

#### ChangeCondition
```python
ChangeCondition(metric="spend", direction="up", percent=50, reference_period="yesterday")
# → "Spend increased 50% vs yesterday"
```

#### CompositeCondition
```python
CompositeCondition(operator="AND", conditions=[
    ThresholdCondition(metric="roas", operator="gt", value=2.0),
    ThresholdCondition(metric="spend", operator="gt", value=100)
])
# → "ROAS > 2 AND spend > $100"
```

#### NotCondition
```python
NotCondition(condition=ThresholdCondition(metric="roas", operator="gt", value=2.0))
# → "ROAS is NOT > 2"
```

### 3. State Machine (`app/services/agents/state_machine.py`)

Manages entity state transitions:

```
State Transitions:
    WATCHING → condition=True → ACCUMULATING
    ACCUMULATING → accumulation_complete → TRIGGERED
    TRIGGERED → cooldown configured → COOLDOWN
    TRIGGERED → no cooldown → WATCHING
    COOLDOWN → cooldown_expired → WATCHING
    Any state → evaluation_error → ERROR
    ERROR → manual_resume → WATCHING
```

Key class: `AgentStateMachine`
- Tracks accumulation progress
- Determines trigger eligibility
- Handles cooldown periods
- Supports consecutive and within_window modes

### 4. Evaluation Engine (`app/services/agents/evaluation_engine.py`)

The heart of the system. Called every 15 minutes by ARQ:

```python
class AgentEvaluationEngine:
    async def evaluate_all_agents(self):
        """Called by scheduler every 15 minutes"""

    async def evaluate_agent(self, agent: Agent):
        """Evaluate single agent across all scoped entities"""

    async def evaluate_agent_entity(self, agent: Agent, entity: Entity):
        """Core evaluation - produces one immutable event"""
        # 1. Get or create entity state
        # 2. Fetch current metrics from MetricSnapshot
        # 3. Evaluate condition
        # 4. Process state machine
        # 5. Execute actions if triggered
        # 6. Store evaluation event
        # 7. Broadcast via WebSocket
```

### 5. Action System (`app/services/agents/actions.py`)

Abstract `Action` base class with implementations:

#### EmailAction
```python
EmailAction(config={
    "subject_template": "Agent triggered on {{entity_name}}",
    "body_template": "ROAS is now {{roas}}"
})
```

#### ScaleBudgetAction
```python
ScaleBudgetAction(config={
    "scale_percent": 20,  # +20%
    "max_budget": 1000,   # Hard cap
    "min_budget": 50      # Floor
})
```

#### PauseCampaignAction
```python
PauseCampaignAction()  # Pauses the triggering entity
```

### 6. Platform Action Executor (`app/services/agents/action_executor.py`)

Orchestrates safe, platform-aware action execution:

```python
class PlatformActionExecutor:
    async def execute_action(self, action_config, context):
        # 1. Parse action config
        # 2. Health check (is connection healthy?)
        # 3. Fetch live state from platform API
        # 4. Validate preconditions
        # 5. Execute via Meta/Google API
        # 6. Verify change took effect
        # 7. Log with before/after state
```

Safety features:
- Pre-action health checks
- Live state fetching (not cached)
- Budget caps enforcement
- State before/after logging
- Rollback capability

### 7. Notification Service (`app/services/agents/notification_service.py`)

Handles email notifications via Resend:

```python
class AgentNotificationService:
    async def send_trigger_notification(self, event, action_results)
    async def send_error_notification(self, agent, error)
    async def send_agent_stopped_notification(self, agent, reason)
```

### 8. WebSocket Manager (`app/services/agents/websocket_manager.py`)

Real-time event streaming:

```python
class AgentWebSocketManager:
    async def broadcast_evaluation_event(self, workspace_id, agent_id, event_data)
    async def broadcast_trigger(self, workspace_id, agent_id, entity_id, ...)
    async def broadcast_status_change(self, workspace_id, agent_id, old_status, new_status)
```

## API Endpoints (`app/routers/agents.py`)

```
# Agent CRUD
GET    /v1/agents                    - List agents (with status, stats)
POST   /v1/agents                    - Create agent
GET    /v1/agents/{id}               - Get agent detail
PATCH  /v1/agents/{id}               - Update agent
DELETE /v1/agents/{id}               - Delete agent

# Status Control
POST   /v1/agents/{id}/pause         - Pause agent
POST   /v1/agents/{id}/resume        - Resume agent
POST   /v1/agents/{id}/test          - Test evaluation (dry run)

# Logs & Events
GET    /v1/agents/{id}/events        - Get evaluation events (paginated)
GET    /v1/agents/{id}/actions       - Get action executions
GET    /v1/agents/{id}/status        - Get current entity states

# WebSocket
WS     /v1/agents/{id}/stream        - Real-time event stream
```

## Copilot Integration

### Agent Management Tools (`app/agent/tools.py`)

Six tools for managing agents via natural language:

1. **list_agents** - List all user's agents with status
2. **get_agent_status** - Get detailed status of specific agent
3. **create_agent** - Create agent from natural language (returns preview)
4. **pause_agent** - Pause a running agent
5. **resume_agent** - Resume a paused agent
6. **explain_agent_behavior** - Explain why agent did/didn't fire

### AgentManagementTools Class

```python
class AgentManagementTools:
    def __init__(self, db, workspace_id, user_id):
        ...

    def list_agents(self) -> dict:
        """List all agents in workspace"""

    def get_agent_status(self, agent_name=None, agent_id=None) -> dict:
        """Get detailed agent status"""

    def create_agent(self, description, platform=None, confirmed=False) -> dict:
        """Create agent from natural language

        When confirmed=False: Returns preview with agent config
        When confirmed=True: Actually creates the agent
        """

    def pause_agent(self, agent_name=None, agent_id=None, reason=None) -> dict:
        """Pause a running agent"""

    def resume_agent(self, agent_name=None, agent_id=None) -> dict:
        """Resume a paused agent"""

    def explain_agent_behavior(self, agent_name=None, agent_id=None,
                               time_range="last_7d", question=None) -> dict:
        """Explain agent behavior

        If no agent specified: Returns summary of ALL agents
        If agent specified: Returns detailed evaluation history
        """
```

### Agent Preview Card (`ui/components/copilot/AgentPreviewCard.jsx`)

Deterministic UI for agent creation:

```
┌────────────────────────────────────────────┐
│  Create Agent                               │
│  Review and confirm before activating       │
│                                             │
│  Agent Name: High ROAS Alert                │
│                                             │
│  ┌──────────────────┐ ┌──────────────────┐ │
│  │ Condition        │ │ Scope            │ │
│  │ ROAS < 2         │ │ All Meta Camps   │ │
│  └──────────────────┘ └──────────────────┘ │
│                                             │
│  ┌──────────────────┐ ┌──────────────────┐ │
│  │ Action           │ │ Frequency        │ │
│  │ Email alert      │ │ Every 15 min     │ │
│  └──────────────────┘ └──────────────────┘ │
│                                             │
│  [ Create Agent ]    [ Edit ]               │
└────────────────────────────────────────────┘
```

## Background Scheduler (`app/workers/arq_worker.py`)

Agents are evaluated every 15 minutes:

```python
async def scheduled_agent_evaluation(ctx):
    """Run every 15 minutes, after metric sync completes"""
    engine = AgentEvaluationEngine(db)
    result = await engine.evaluate_all_agents()
    return result

class WorkerSettings:
    cron_jobs = [
        cron(scheduled_agent_evaluation, minute={0, 15, 30, 45}),
    ]
```

## Data Flow

### Evaluation Cycle

```
1. ARQ scheduler triggers (every 15 min)
   │
2. AgentEvaluationEngine.evaluate_all_agents()
   │
3. For each active agent:
   │
4. Get scoped entities (campaigns, ad sets, ads)
   │
5. For each entity:
   │
   ├─► Fetch metrics from MetricSnapshot (last 24h)
   │
   ├─► Evaluate condition against metrics
   │
   ├─► Update state machine (accumulation, transitions)
   │
   ├─► If should_trigger:
   │   │
   │   ├─► Execute actions via PlatformActionExecutor
   │   │   ├─► Health check
   │   │   ├─► Live state fetch
   │   │   ├─► API call (Meta/Google)
   │   │   └─► Verify change
   │   │
   │   └─► Send notifications
   │
   ├─► Store AgentEvaluationEvent (immutable)
   │
   └─► Broadcast via WebSocket
```

### Agent Creation via Copilot

```
1. User: "Alert me when ROAS drops below 2"
   │
2. Copilot calls create_agent(description="...", confirmed=false)
   │
3. AgentManagementTools parses intent, builds config
   │
4. Returns preview data (NOT creating agent yet)
   │
5. Frontend renders AgentPreviewCard
   │
6. User clicks "Create Agent" button
   │
7. AgentPreviewCard calls createAgent API directly
   │
8. Agent created and active
```

## Safety Mechanisms

### 1. Pre-Action Health Check
```python
health = await health_service.check_health(connection_id)
if not health.healthy:
    return ActionResult(skipped=True, reason=health.reason)
```

### 2. Live State Validation
```python
# Fetch CURRENT state from platform, not cached
live_state = await fetch_live_campaign_state(entity)
if live_state.status != "ACTIVE":
    return ActionResult(skipped=True, reason="Campaign not active")
```

### 3. Budget Caps
```python
new_budget = current_budget * (1 + scale_percent/100)
new_budget = min(new_budget, max_budget)  # Hard cap
new_budget = max(new_budget, min_budget)  # Floor
```

### 4. State Before/After Logging
```python
execution = AgentActionExecution(
    state_before={"budget": 500},
    state_after={"budget": 600},
    rollback_possible=True
)
```

### 5. Automatic Error Recovery
```python
# After 3 consecutive errors, agent is paused
if entity_state.consecutive_errors >= 3:
    await pause_agent(agent, reason="Too many errors")
    await notify_user(agent, "Agent stopped due to errors")
```

## Observability

### Logging
All evaluations and actions are logged with structured data:
```
INFO  Evaluating agent abc123: "High ROAS Scaler"
DEBUG Agent abc123 has 5 entities in scope
INFO  Action scale_budget: success=True, state: $500 → $600
```

### Metrics (Database)
- `agents.total_evaluations` - Total evaluation count
- `agents.total_triggers` - Total trigger count
- `agent_evaluation_events` - Full history (event sourced)
- `agent_action_executions` - Full action history

### Real-time (WebSocket)
- Evaluation events streamed as they happen
- Trigger notifications
- Status changes (active → error, etc.)

## Example Queries

### "Why didn't my agents fire yesterday?"
```python
# Copilot calls explain_agent_behavior() with no agent specified
# Returns summary of all agents:
{
    "total_agents": 3,
    "evaluations_yesterday": 45,
    "agents": [
        {
            "name": "High ROAS Alert",
            "evaluations": 15,
            "conditions_met": 0,
            "triggers": 0,
            "summary": "ROAS was above 2.0 for all campaigns"
        },
        ...
    ]
}
```

### "What is my budget scaler doing?"
```python
# Copilot calls get_agent_status(agent_name="budget scaler")
{
    "name": "Budget Scaler",
    "status": "active",
    "last_evaluated_at": "2026-01-26T10:15:00Z",
    "total_triggers": 5,
    "entity_states": [
        {
            "entity_name": "Summer Sale",
            "state": "accumulating",
            "accumulation": "2/3 consecutive evaluations"
        }
    ]
}
```

## Future Enhancements

1. **Agent Templates** - Pre-built agents (Stop Loss, Scaler, Anomaly Detector)
2. **Shadow Mode** - Test agents without actions
3. **Agent Edit UI** - Full CRUD in frontend
4. **Conflict Detection** - Warn when multiple agents target same entity
5. **Rollback UI** - One-click action reversal
6. **Mobile Optimization** - Responsive agent management

---

## Related Documents

- [QA System Architecture](./QA_SYSTEM_ARCHITECTURE.md) - Copilot/LangGraph integration
- [Observability](./OBSERVABILITY.md) - Logging and monitoring patterns
