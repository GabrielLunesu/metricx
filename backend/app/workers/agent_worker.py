"""
Agent Worker - LangGraph Agent Functions
=========================================

**Version**: 2.0.0
**Updated**: 2025-12-08

Agent job processing functions for QA system.

WHY THIS FILE EXISTS
--------------------
Provides synchronous agent execution for:
1. /qa/agent/sync - Direct synchronous endpoint
2. /qa/agent/sse - SSE streaming endpoint

Note: The RQ-based async job system has been deprecated.
All QA endpoints now run synchronously or via SSE streaming.

RELATED FILES
-------------
- app/agent/graph.py: The agent that gets run
- app/agent/stream.py: Redis pub/sub streaming
- app/routers/qa.py: API endpoints
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.agent.graph import run_agent
from app.agent.stream import create_publisher, StreamPublisher
from app import state as app_state

logger = logging.getLogger(__name__)


def _update_stage(job_id: str, stage: str, publisher=None) -> None:
    """
    Log processing stage for debugging.

    STAGES:
        - understanding: Classifying user intent
        - fetching: Getting data from semantic layer
        - responding: Generating natural language answer
        - complete: Job finished
        - error: Job failed
    """
    logger.debug(f"[AGENT_WORKER] Job {job_id} stage: {stage}")
    if publisher:
        try:
            publisher.thinking(f"Stage: {stage}")
        except Exception:
            pass


def process_agent_job(
    question: str,
    workspace_id: str,
    user_id: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    job_id: str = "direct",
) -> Dict[str, Any]:
    """
    Process an agent question.

    WHAT: Main entry point for processing a question.

    PARAMETERS:
        question: User's natural language question
        workspace_id: UUID string for workspace scoping
        user_id: UUID string for user tracking
        conversation_history: Previous Q&A for context
        job_id: Optional job identifier for logging

    RETURNS:
        Dict with:
            - success: bool
            - answer: Natural language answer
            - visuals: Chart/table specs
            - data: Raw data (for debugging)
            - error: Error message (if failed)
    """
    logger.info(f"[AGENT_WORKER] ===== Processing agent job {job_id} =====")
    logger.info(f"[AGENT_WORKER] Question: {question}")
    logger.info(f"[AGENT_WORKER] Workspace: {workspace_id}")
    logger.info(f"[AGENT_WORKER] User: {user_id}")

    # Create database session
    db: Session = SessionLocal()

    # Create Redis publisher for streaming
    publisher: Optional[StreamPublisher] = None
    try:
        publisher = create_publisher(job_id)
        logger.info(f"[AGENT_WORKER] Publisher created for job {job_id}")
    except Exception as e:
        logger.warning(f"[AGENT_WORKER] Failed to create publisher: {e}")

    try:
        _update_stage(job_id, "understanding", publisher)

        # Run the agent
        result = run_agent(
            question=question,
            workspace_id=workspace_id,
            user_id=user_id,
            db=db,
            publisher=publisher,
            conversation_history=conversation_history,
        )

        _update_stage(job_id, "complete", publisher)
        logger.info(f"[AGENT_WORKER] Job {job_id} completed: success={result.get('success')}")

        # Store context for follow-ups
        if result.get("success") and app_state.context_manager:
            try:
                app_state.context_manager.add_entry(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    question=question,
                    dsl=result.get("semantic_query", {}),
                    result=result.get("data", {}),
                )
                logger.info("[AGENT_WORKER] Context stored for follow-ups")
            except Exception as e:
                logger.warning(f"[AGENT_WORKER] Failed to store context: {e}")

        return {
            "success": result.get("success", False),
            "answer": result.get("answer", ""),
            "visuals": result.get("visuals"),
            "data": result.get("data"),
            "semantic_query": result.get("semantic_query"),
            "intent": result.get("intent"),
            "error": result.get("error"),
        }

    except Exception as e:
        error_msg = str(e)
        logger.exception(f"[AGENT_WORKER] Job {job_id} failed: {e}")

        _update_stage(job_id, "error", publisher)

        if publisher:
            publisher.error(error_msg)

        return {
            "success": False,
            "answer": "I encountered an error processing your question. Please try again.",
            "error": error_msg,
        }

    finally:
        db.close()
        logger.info(f"[AGENT_WORKER] Database session closed for job {job_id}")


def process_agent_job_sync(
    question: str,
    workspace_id: str,
    user_id: str,
    db: Session,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Synchronous version for direct calls (no RQ).

    WHAT: Run agent directly without job queue.

    WHY: Useful for:
        - Testing
        - Development
        - Low-latency scenarios where streaming isn't needed

    PARAMETERS:
        Same as process_agent_job, plus:
        db: Pre-existing database session

    RETURNS:
        Same as process_agent_job
    """
    logger.info(f"[AGENT_WORKER] Sync processing: {question[:50]}...")

    try:
        result = run_agent(
            question=question,
            workspace_id=workspace_id,
            user_id=user_id,
            db=db,
            publisher=None,  # No streaming for sync
            conversation_history=conversation_history,
        )

        return {
            "success": result.get("success", False),
            "answer": result.get("answer", ""),
            "visuals": result.get("visuals"),
            "data": result.get("data"),
            "semantic_query": result.get("semantic_query"),
            "intent": result.get("intent"),
            "error": result.get("error"),
        }

    except Exception as e:
        logger.exception(f"[AGENT_WORKER] Sync processing failed: {e}")
        return {
            "success": False,
            "answer": "I encountered an error. Please try again.",
            "error": str(e),
        }
