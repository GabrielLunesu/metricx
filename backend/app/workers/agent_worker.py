"""
Agent Worker - RQ Job Handler
=============================

**Version**: 1.0.0
**Created**: 2025-12-03

RQ worker that processes agent jobs.
Runs the LangGraph agent with Redis Pub/Sub streaming.

WHY THIS FILE EXISTS
--------------------
The agent runs in a background worker (not the API process) because:
1. LLM calls can take 5-30 seconds
2. We don't want to block HTTP requests
3. RQ provides reliable job processing with retries

This worker:
1. Receives job from RQ queue
2. Creates StreamPublisher for real-time updates
3. Runs LangGraph agent
4. Publishes results via Redis Pub/Sub
5. Stores final result in job.meta

RELATED FILES
-------------
- app/agent/graph.py: The agent that gets run
- app/agent/stream.py: Redis pub/sub streaming
- app/routers/qa.py: API that enqueues jobs
- app/workers/qa_worker.py: Pattern reference (existing QA worker)
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


def _update_stage(job, stage: str) -> None:
    """
    Update job metadata with current processing stage.

    WHY: Enables SSE endpoint to report progress even without Redis Pub/Sub.
    This is a fallback for environments where pub/sub isn't available.

    STAGES:
        - queued: Job enqueued, not started
        - understanding: Classifying user intent
        - fetching: Getting data from semantic layer
        - responding: Generating natural language answer
        - complete: Job finished
        - error: Job failed
    """
    if job:
        job.meta['stage'] = stage
        job.save_meta()
        logger.debug(f"[AGENT_WORKER] Stage updated: {stage}")


def process_agent_job(
    question: str,
    workspace_id: str,
    user_id: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    RQ job handler for agent questions.

    WHAT: Main entry point for processing a question.

    WHY: Called by RQ when a job is dequeued.

    PARAMETERS:
        question: User's natural language question
        workspace_id: UUID string for workspace scoping
        user_id: UUID string for user tracking
        conversation_history: Previous Q&A for context

    RETURNS:
        Dict with:
            - success: bool
            - answer: Natural language answer
            - visuals: Chart/table specs
            - data: Raw data (for debugging)
            - error: Error message (if failed)

    FLOW:
        1. Get RQ job for stage tracking
        2. Create database session
        3. Create Redis publisher for streaming
        4. Run LangGraph agent
        5. Return result
    """
    from rq import get_current_job

    # Get job from RQ context
    job = get_current_job()
    job_id = job.id if job else "unknown"

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
        # Continue without publisher - will just not stream

    try:
        # Stage 1: Understanding
        _update_stage(job, "understanding")
        logger.info("[AGENT_WORKER] Stage: understanding")

        # Run the agent
        result = run_agent(
            question=question,
            workspace_id=workspace_id,
            user_id=user_id,
            db=db,
            publisher=publisher,
            conversation_history=conversation_history,
        )

        # Stage 2: Complete
        _update_stage(job, "complete")
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

        _update_stage(job, "error")

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
