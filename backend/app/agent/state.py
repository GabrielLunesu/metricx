"""
Agent State Schema
==================

**Version**: 1.0.0
**Created**: 2025-12-03

TypedDict schema for LangGraph agent state.
This defines what data flows through the agent graph.

WHY THIS FILE EXISTS
--------------------
LangGraph agents are stateful - they need to track:
- Conversation history (for context)
- Current query being built
- Fetched data
- Streaming answer chunks

This file defines that state in a type-safe way.

RELATED FILES
-------------
- app/agent/graph.py: Uses this state
- app/agent/nodes.py: Reads/writes this state
- app/semantic/query.py: SemanticQuery structure
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict, Optional, List, Dict, Any, Literal
from enum import Enum


class MessageRole(str, Enum):
    """Message role in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class Message:
    """
    Single message in conversation history.

    WHAT: Represents one turn in the conversation.

    WHY: Tracks full conversation for context understanding.
    Each message has a role and content, optionally tool info.
    """
    role: MessageRole
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM."""
        result = {"role": self.role.value, "content": self.content}
        if self.tool_name:
            result["tool_name"] = self.tool_name
        return result


class AgentState(TypedDict, total=False):
    """
    LangGraph agent state.

    WHAT: All data that flows through the agent graph.

    WHY: LangGraph uses TypedDict for type-safe state management.
    Each node can read/write to this state.

    FIELDS:
        messages: Full conversation history
        workspace_id: Current workspace (security scope)
        user_id: Current user

        current_question: The question being processed
        intent: Classified intent (metric_query, comparison, etc.)

        semantic_query: Built SemanticQuery (dict form)
        compilation_result: Data from semantic layer

        answer_chunks: Streaming answer tokens
        visuals: Chart/table specs

        error: Error message if something failed
        needs_clarification: True if we need to ask user
        clarification_question: What to ask user

        stage: Current processing stage (for UI feedback)
    """
    # Conversation context
    messages: List[Message]
    workspace_id: str
    user_id: str

    # Current turn
    current_question: str
    intent: Optional[str]  # metric_query, comparison, ranking, explanation, out_of_scope

    # Query building
    semantic_query: Optional[Dict[str, Any]]

    # Results
    compilation_result: Optional[Dict[str, Any]]
    answer_chunks: List[str]
    visuals: Optional[Dict[str, Any]]

    # Error handling
    error: Optional[str]
    needs_clarification: bool
    clarification_question: Optional[str]

    # Progress tracking
    stage: Literal["understanding", "checking_freshness", "fetching", "analyzing", "responding", "done", "error"]

    # Live API tracking (for real-time data queries)
    # WHAT: Tracks whether live API calls are needed and their results
    # WHY: Enables copilot to query Google/Meta APIs directly when snapshots are stale
    # REFERENCES: app/agent/live_api_tools.py
    needs_live_data: bool  # True if user requested "live" data or snapshots are stale
    live_data_reason: Optional[str]  # "user_requested" | "stale_snapshot" | None
    live_api_calls: List[Dict[str, Any]]  # Track API calls [{provider, endpoint, success, latency_ms}]
    live_api_errors: List[str]  # Any errors from live API calls


def create_initial_state(
    question: str,
    workspace_id: str,
    user_id: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> AgentState:
    """
    Create initial agent state for a new question.

    WHAT: Factory function for AgentState.

    WHY: Ensures all required fields are initialized properly.

    PARAMETERS:
        question: User's natural language question
        workspace_id: UUID of workspace
        user_id: UUID of user
        conversation_history: Previous messages for context

    RETURNS:
        Initialized AgentState ready for agent graph

    EXAMPLE:
        state = create_initial_state(
            question="What's my ROAS?",
            workspace_id="...",
            user_id="...",
        )
    """
    # Convert conversation history to Message objects
    messages: List[Message] = []
    if conversation_history:
        for entry in conversation_history:
            if entry.get("question"):
                messages.append(Message(
                    role=MessageRole.USER,
                    content=entry["question"],
                ))
            if entry.get("answer"):
                messages.append(Message(
                    role=MessageRole.ASSISTANT,
                    content=entry["answer"],
                ))

    # Add current question
    messages.append(Message(
        role=MessageRole.USER,
        content=question,
    ))

    return AgentState(
        messages=messages,
        workspace_id=workspace_id,
        user_id=user_id,
        current_question=question,
        intent=None,
        semantic_query=None,
        compilation_result=None,
        answer_chunks=[],
        visuals=None,
        error=None,
        needs_clarification=False,
        clarification_question=None,
        stage="understanding",
        # Live API tracking
        needs_live_data=False,
        live_data_reason=None,
        live_api_calls=[],
        live_api_errors=[],
    )
