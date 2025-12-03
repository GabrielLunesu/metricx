"""
LangGraph Agent Definition
==========================

**Version**: 1.0.0
**Created**: 2025-12-03

Defines the LangGraph state machine for the QA agent.
This is where nodes are connected into a flow.

WHY THIS FILE EXISTS
--------------------
LangGraph uses a graph structure where:
- Nodes are functions that process state
- Edges define transitions between nodes
- Conditional edges route based on state

This file defines the graph topology.

GRAPH STRUCTURE
---------------
```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ understand  │ ─── Classify intent
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    (out_of_scope)   (needs_clarify)   (normal)
          │                │                │
          ▼                ▼                ▼
    ┌─────────┐      ┌─────────┐     ┌─────────┐
    │ respond │      │ respond │     │  fetch  │
    └────┬────┘      └────┬────┘     └────┬────┘
         │                │               │
         │                │        (error)│(success)
         │                │          ┌────┴────┐
         │                │          │         │
         │                │          ▼         ▼
         │                │    ┌─────────┐ ┌─────────┐
         │                │    │  error  │ │ respond │
         │                │    └────┬────┘ └────┬────┘
         │                │         │           │
         └────────────────┴─────────┴───────────┘
                                   │
                            ┌──────▼──────┐
                            │    END      │
                            └─────────────┘
```

RELATED FILES
-------------
- app/agent/nodes.py: Node implementations
- app/agent/state.py: State schema
- app/workers/agent_worker.py: Runs this graph
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, Literal
from functools import partial

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.agent.state import AgentState, create_initial_state
from app.agent.nodes import (
    understand_node,
    fetch_data_node,
    respond_node,
    error_node,
)
from app.agent.stream import StreamPublisher

logger = logging.getLogger(__name__)


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_after_understand(state: AgentState) -> Literal["fetch_data", "respond", "error"]:
    """
    Route after understand node.

    LOGIC:
        - If error occurred → error node
        - If needs clarification → respond (with clarification question)
        - If out of scope → respond (with explanation)
        - Otherwise → fetch data
    """
    if state.get("error") and state.get("stage") == "error":
        return "error"

    if state.get("needs_clarification"):
        return "respond"

    intent = state.get("intent")
    if intent == "out_of_scope":
        return "respond"

    return "fetch_data"


def route_after_fetch(state: AgentState) -> Literal["respond", "error"]:
    """
    Route after fetch_data node.

    LOGIC:
        - If error occurred → error node
        - Otherwise → respond
    """
    if state.get("error") or state.get("stage") == "error":
        return "error"

    return "respond"


# =============================================================================
# GRAPH BUILDER
# =============================================================================

def create_agent_graph(
    db: Session,
    publisher: Optional[StreamPublisher] = None,
) -> StateGraph:
    """
    Create the LangGraph agent graph.

    WHAT: Builds the state machine that processes questions.

    WHY: LangGraph provides:
        - State management
        - Conditional routing
        - Error handling
        - Streaming support

    PARAMETERS:
        db: SQLAlchemy session (passed to nodes)
        publisher: Optional StreamPublisher for real-time updates

    RETURNS:
        Compiled LangGraph ready to invoke

    USAGE:
        graph = create_agent_graph(db, publisher)
        result = graph.invoke(initial_state)
    """
    logger.info("[GRAPH] Creating agent graph")

    # Create graph with state schema
    workflow = StateGraph(AgentState)

    # Create node functions with bound db and publisher
    understand = partial(understand_node, db=db, publisher=publisher)
    fetch_data = partial(fetch_data_node, db=db, publisher=publisher)
    respond = partial(respond_node, db=db, publisher=publisher)
    error = partial(error_node, db=db, publisher=publisher)

    # Add nodes
    workflow.add_node("understand", understand)
    workflow.add_node("fetch_data", fetch_data)
    workflow.add_node("respond", respond)
    workflow.add_node("error", error)

    # Set entry point
    workflow.set_entry_point("understand")

    # Add conditional edges
    workflow.add_conditional_edges(
        "understand",
        route_after_understand,
        {
            "fetch_data": "fetch_data",
            "respond": "respond",
            "error": "error",
        }
    )

    workflow.add_conditional_edges(
        "fetch_data",
        route_after_fetch,
        {
            "respond": "respond",
            "error": "error",
        }
    )

    # Add terminal edges
    workflow.add_edge("respond", END)
    workflow.add_edge("error", END)

    # Compile
    graph = workflow.compile()
    logger.info("[GRAPH] Agent graph compiled")

    return graph


# =============================================================================
# RUN FUNCTION
# =============================================================================

def run_agent(
    question: str,
    workspace_id: str,
    user_id: str,
    db: Session,
    publisher: Optional[StreamPublisher] = None,
    conversation_history: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Run the agent to answer a question.

    WHAT: Main entry point for running the agent.

    WHY: Simple interface for callers - just pass the question and context.

    PARAMETERS:
        question: User's natural language question
        workspace_id: UUID of workspace (security scope)
        user_id: UUID of user
        db: SQLAlchemy session
        publisher: Optional StreamPublisher for streaming
        conversation_history: Previous Q&A for context

    RETURNS:
        Dict with:
            - success: bool
            - answer: Full answer text
            - visuals: Chart/table specs
            - error: Error message if failed

    EXAMPLE:
        result = run_agent(
            question="What's my ROAS this week?",
            workspace_id="...",
            user_id="...",
            db=db,
        )
        print(result["answer"])
    """
    logger.info(f"[AGENT] Running: {question[:50]}...")

    try:
        # Create initial state
        state = create_initial_state(
            question=question,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_history=conversation_history,
        )

        # Create and run graph
        graph = create_agent_graph(db, publisher)
        final_state = graph.invoke(state)

        # Extract result
        answer_chunks = final_state.get("answer_chunks", [])
        answer = "".join(answer_chunks) if answer_chunks else "I couldn't generate an answer."

        result = {
            "success": not final_state.get("error"),
            "answer": answer,
            "visuals": final_state.get("visuals"),
            "semantic_query": final_state.get("semantic_query"),
            "intent": final_state.get("intent"),
            "data": final_state.get("compilation_result", {}).get("data"),
        }

        if final_state.get("error"):
            result["error"] = final_state["error"]

        # Publish done event
        if publisher:
            publisher.done(result)

        logger.info(f"[AGENT] Complete: success={result['success']}")
        return result

    except Exception as e:
        logger.exception(f"[AGENT] Failed: {e}")
        error_result = {
            "success": False,
            "answer": "I encountered an unexpected error. Please try again.",
            "error": str(e),
        }

        if publisher:
            publisher.error(str(e))

        return error_result


# =============================================================================
# ASYNC VARIANT (for future use)
# =============================================================================

async def run_agent_async(
    question: str,
    workspace_id: str,
    user_id: str,
    db: Session,
    publisher: Optional[StreamPublisher] = None,
    conversation_history: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Async version of run_agent.

    NOTE: Currently just wraps sync version.
    LangGraph has async support that can be enabled later.
    """
    # For now, just call sync version
    # TODO: Use ainvoke when we switch to async db sessions
    return run_agent(
        question=question,
        workspace_id=workspace_id,
        user_id=user_id,
        db=db,
        publisher=publisher,
        conversation_history=conversation_history,
    )
