"""RQ worker entrypoint for QA jobs.

WHAT:
    Processes natural language question-answering jobs outside HTTP request cycle.

WHY:
    - Prevents HTTP timeouts during long LLM/DB operations (can take 5-30 seconds)
    - Keeps FastAPI responses fast (enqueue job instead of blocking)
    - Enables production-ready QA system with reliable job processing
    - Aligns with existing worker architecture for sync jobs

UPDATED v2.1: Added stage metadata for SSE streaming support.
    - job.meta['stage'] tracks: translating → executing → formatting → complete
    - Enables real-time progress updates via /qa/stream endpoint

REFERENCES:
    - docs/living-docs/QA_SYSTEM_ARCHITECTURE.md
    - backend/app/services/qa_service.py
    - backend/app/workers/sync_worker.py (pattern reference)
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.qa_service import QAService

logger = logging.getLogger(__name__)


def _update_stage(job, stage: str) -> None:
    """
    Update job metadata with current processing stage.

    WHY: Enables SSE streaming endpoint to report real-time progress.

    Stages:
    - translating: Converting question to DSL
    - executing: Running database queries
    - formatting: Building answer and visuals
    - complete: Job finished

    Args:
        job: RQ job instance
        stage: Current stage name
    """
    if job:
        job.meta['stage'] = stage
        job.save_meta()
        logger.debug(f"[QA_WORKER] Stage updated: {stage}")


def process_qa_job(
    question: str,
    workspace_id: str,
    user_id: str
) -> dict:
    """RQ job handler for QA questions.

    Args:
        question: Natural language question from user
        workspace_id: UUID string for workspace scoping
        user_id: UUID string for user tracking

    Returns:
        dict: Job result containing answer, executed_dsl, and data
              or error information if processing failed

    Stage Progression (for SSE streaming):
        1. translating - Understanding the question
        2. executing - Fetching data from database
        3. formatting - Preparing the answer
        4. complete - Job finished (in result)
    """
    from rq import get_current_job

    # Get job from RQ context for stage tracking
    job = get_current_job()
    job_id = job.id if job else "unknown"

    db: Session = SessionLocal()
    try:
        print(f"[QA_WORKER] Processing job {job_id} for user {user_id} (workspace={workspace_id})", flush=True)
        print(f"[QA_WORKER] Question: {question}", flush=True)

        # Stage 1: Translating (LLM converts question → DSL)
        # NOTE: Set stage immediately so SSE endpoint can pick it up
        _update_stage(job, "translating")
        print("[QA_WORKER] Stage: translating - Understanding question", flush=True)

        # Initialize QA service
        service = QAService(db)

        # Stage 2: Executing (after translation completes, we're executing)
        # Set this BEFORE calling service.answer() since that's where the work happens
        _update_stage(job, "executing")
        print("[QA_WORKER] Stage: executing - Fetching data", flush=True)

        # Process the question (this can take 5-30 seconds)
        # NOTE: service.answer() handles translate → execute → format internally
        result = service.answer(
            question=question,
            workspace_id=workspace_id,
            user_id=user_id
        )

        # Stage 3: Formatting (building response)
        _update_stage(job, "formatting")
        print("[QA_WORKER] Stage: formatting - Preparing answer", flush=True)

        print(f"[QA_WORKER] Job {job_id} completed successfully", flush=True)

        # Result is already a dict (QAResult model is serialized)
        return {
            "success": True,
            "answer": result["answer"] if isinstance(result, dict) else result.answer,
            "executed_dsl": result["executed_dsl"] if isinstance(result, dict) else result.executed_dsl,
            "data": result["data"] if isinstance(result, dict) else result.data,
            "context_used": result.get("context_used") if isinstance(result, dict) else result.context_used,
            "visuals": result.get("visuals") if isinstance(result, dict) else getattr(result, "visuals", None),
        }

    except Exception as exc:
        error_msg = str(exc)
        logger.exception(
            "[QA_WORKER] Job %s failed: %s",
            job_id,
            exc,
        )

        return {
            "success": False,
            "error": error_msg,
        }

    finally:
        db.close()
