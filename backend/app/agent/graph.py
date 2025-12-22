"""
LangGraph Agent Definition
==========================

**Version**: 2.0.0
**Created**: 2025-12-03
**Updated**: 2025-12-22

Defines the LangGraph state machine for the QA agent.
This is where nodes are connected into a flow.

WHY THIS FILE EXISTS
--------------------
LangGraph uses a graph structure where:
- Nodes are functions that process state
- Edges define transitions between nodes
- Conditional edges route based on state

This file defines the graph topology.

GRAPH STRUCTURE (v2 - Free Agent)
---------------------------------
```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    agent    │ ─── ReAct loop: LLM decides tools → execute → repeat
                    │   (loop)    │     until answer is ready
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    END      │
                    └─────────────┘
```

The agent_loop_node handles everything internally:
1. LLM sees question + all available tools
2. LLM decides what tool(s) to call (or answer directly)
3. Tools execute, results added to context
4. Loop until LLM has enough info to answer (max 5 iterations)

DATA SOURCE PRIORITY (embedded in tool descriptions):
- Snapshots FIRST (updated every 15 min) for metrics
- Live API only for data not in snapshots (start_date, keywords, audiences)
- Response always includes data freshness info

RELATED FILES
-------------
- app/agent/nodes.py: Node implementations (including agent_loop_node)
- app/agent/tools.py: AGENT_TOOLS schema for OpenAI function calling
- app/agent/state.py: State schema
- app/routers/qa.py: SSE endpoint that runs this graph
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Dict, Any
from functools import partial

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.agent.state import AgentState, create_initial_state
from app.agent.nodes import agent_loop_node
from app.agent.stream import StreamPublisher

logger = logging.getLogger(__name__)


# =============================================================================
# GRAPH BUILDER (v2 - Simplified Free Agent)
# =============================================================================

def create_agent_graph(
    db: Session,
    publisher: Optional[StreamPublisher] = None,
) -> StateGraph:
    """
    Create the LangGraph agent graph (v2 - Free Agent).

    WHAT: Builds a simple state machine with a single ReAct-style agent node.

    WHY: The free agent approach lets the LLM decide what tools to call,
         rather than following rigid intent-classification routes.

    HOW IT WORKS:
        1. User question enters the agent node
        2. LLM sees ALL available tools and decides what to call
        3. Tools execute, results added to conversation
        4. LLM decides: need more info? → call more tools
                        have enough? → generate answer
        5. Max 5 iterations to prevent runaway loops

    DATA SOURCE PRIORITY:
        The tool descriptions guide the LLM to:
        - Use snapshots FIRST (fast, no external API calls)
        - Use live API only when snapshots can't answer
        - Always include data freshness in responses

    PARAMETERS:
        db: SQLAlchemy session (passed to nodes for DB access)
        publisher: Optional StreamPublisher for real-time SSE updates

    RETURNS:
        Compiled LangGraph ready to invoke

    USAGE:
        graph = create_agent_graph(db, publisher)
        result = graph.invoke(initial_state)
    """
    logger.info("[GRAPH] Creating free agent graph (v2)")

    # Create graph with state schema
    workflow = StateGraph(AgentState)

    # Create the agent node with bound db and publisher
    # This single node handles the entire ReAct loop internally
    agent = partial(agent_loop_node, db=db, publisher=publisher)

    # Add the single agent node
    workflow.add_node("agent", agent)

    # Set entry point
    workflow.set_entry_point("agent")

    # Agent goes directly to END (it handles all logic internally)
    workflow.add_edge("agent", END)

    # Compile
    graph = workflow.compile()
    logger.info("[GRAPH] Free agent graph compiled")

    return graph


# =============================================================================
# RUN FUNCTION (Sync - wrapper around async)
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
    Run the agent to answer a question (sync wrapper).

    WHAT: Main entry point for running the agent synchronously.

    WHY: Simple interface for callers - just pass the question and context.
         Wraps the async version for backwards compatibility.

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
            - tool_calls_made: List of tools called and their success
            - iterations: Number of agent loop iterations
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
    # Run the async version in a new event loop
    return asyncio.run(run_agent_async(
        question=question,
        workspace_id=workspace_id,
        user_id=user_id,
        db=db,
        publisher=publisher,
        conversation_history=conversation_history,
    ))


# =============================================================================
# RUN FUNCTION (Async - primary implementation)
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
    Run the agent to answer a question (async).

    WHAT: Main entry point for running the agent asynchronously.

    WHY: The agent_loop_node uses async OpenAI calls, so this is
         the primary implementation.

    HOW IT WORKS:
        1. Creates initial state with question and context
        2. Builds the graph with single agent node
        3. Invokes the graph (agent handles all logic internally)
        4. Extracts and returns the result

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
            - tool_calls_made: List of tools the LLM decided to call
            - iterations: Number of agent loop iterations
            - error: Error message if failed
    """
    logger.info(f"[AGENT] Running free agent: {question[:50]}...")

    try:
        # Create initial state
        state = create_initial_state(
            question=question,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_history=conversation_history,
        )

        # Create the graph
        graph = create_agent_graph(db, publisher)

        # Run the graph (agent_loop_node is async, but LangGraph handles it)
        # For async execution, we need to run the agent node directly
        # since LangGraph's invoke is sync
        final_state = await _run_graph_async(graph, state, db, publisher)

        # Extract result
        answer_chunks = final_state.get("answer_chunks", [])
        answer = "".join(answer_chunks) if answer_chunks else "I couldn't generate an answer."

        result = {
            "success": not final_state.get("error"),
            "answer": answer,
            # New fields from free agent
            "tool_calls_made": final_state.get("tool_calls_made", []),
            "iterations": final_state.get("iterations", 1),
            # Legacy fields for backwards compatibility
            "visuals": final_state.get("visuals"),
            "data": final_state.get("data"),
        }

        if final_state.get("error"):
            result["error"] = final_state["error"]

        # Publish done event
        if publisher:
            publisher.done(result)

        logger.info(
            f"[AGENT] Complete: success={result['success']}, "
            f"iterations={result['iterations']}, "
            f"tools_called={len(result['tool_calls_made'])}"
        )
        return result

    except Exception as e:
        logger.exception(f"[AGENT] Failed: {e}")
        error_result = {
            "success": False,
            "answer": "I encountered an unexpected error. Please try again.",
            "error": str(e),
            "tool_calls_made": [],
            "iterations": 0,
        }

        if publisher:
            publisher.error(str(e))

        return error_result


async def _run_graph_async(
    graph: StateGraph,
    state: AgentState,
    db: Session,
    publisher: Optional[StreamPublisher] = None,
) -> Dict[str, Any]:
    """
    Run the graph asynchronously.

    WHAT: Executes the agent_loop_node directly since it's async.

    WHY: LangGraph's invoke() is sync, but our agent_loop_node is async
         (uses async OpenAI client). This helper runs it properly.

    PARAMETERS:
        graph: Compiled LangGraph (unused, kept for signature consistency)
        state: Initial agent state
        db: SQLAlchemy session
        publisher: Optional StreamPublisher

    RETURNS:
        Final agent state after execution
    """
    # Import here to avoid circular imports
    from app.agent.nodes import agent_loop_node

    # Run the agent loop directly (it's async)
    result = await agent_loop_node(state, db, publisher)

    # Merge result into state
    final_state = {**state, **result}
    return final_state
