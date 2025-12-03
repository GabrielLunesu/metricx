"""
Agentic Copilot for QA System
=============================

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Active Development

LangGraph-based conversational agent that wraps the Semantic Layer.
Provides natural language understanding, tool calling, and streaming responses.

WHY THIS EXISTS
---------------
The Semantic Layer (app/semantic/) provides the "what" - composable queries.
This agent provides the "how" - understanding natural language and deciding
what queries to run, handling follow-ups, explaining limits, etc.

ARCHITECTURE
------------
```
User Question
    |
    v
LangGraph Agent
    |-- understand: Classify intent, identify metrics/entities
    |-- fetch_data: Call semantic layer tools
    |-- analyze: Reason about results (for "why" questions)
    |-- respond: Stream natural language answer
    |-- clarify: Ask for more info if ambiguous
    |-- explain_limit: Explain why we can't answer
    |
    v
Streaming Response (via Redis Pub/Sub)
```

COMPONENTS
----------
- state.py: Agent state schema (TypedDict)
- tools.py: Semantic layer wrapped as LangGraph tools
- nodes.py: Agent decision nodes
- graph.py: LangGraph state machine definition
- stream.py: Redis pub/sub for real-time streaming

USAGE
-----
```python
from app.agent import run_agent, AgentState

result = await run_agent(
    question="What's my ROAS this week?",
    workspace_id="...",
    user_id="...",
    stream_callback=publish_to_redis,
)
```

RELATED FILES
-------------
- app/semantic/: The toolkit this agent uses
- app/workers/agent_worker.py: RQ job handler
- app/routers/qa.py: API endpoints
- docs/living-docs/SEMANTIC_LAYER_IMPLEMENTATION_PLAN.md: Architecture doc
"""

from app.agent.state import AgentState, Message
from app.agent.graph import create_agent_graph, run_agent
from app.agent.stream import StreamPublisher, StreamEvent

__all__ = [
    "AgentState",
    "Message",
    "create_agent_graph",
    "run_agent",
    "StreamPublisher",
    "StreamEvent",
]
