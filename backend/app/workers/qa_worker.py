"""RQ worker entrypoint for QA jobs.

WHAT:
    Processes natural language question-answering jobs outside HTTP request cycle.

WHY:
    - Prevents HTTP timeouts during long LLM/DB operations (can take 5-30 seconds)
    - Keeps FastAPI responses fast (enqueue job instead of blocking)
    - Enables production-ready QA system with reliable job processing
    - Aligns with existing worker architecture for sync jobs

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
    """
    from rq import get_current_job
    
    # Get job_id from RQ context
    job = get_current_job()
    job_id = job.id if job else "unknown"
    
    db: Session = SessionLocal()
    try:
        logger.info(
            "[QA_WORKER] Processing job %s for user %s (workspace=%s)",
            job_id,
            user_id,
            workspace_id,
        )
        logger.info("[QA_WORKER] Question: %s", question)

        # Initialize QA service
        service = QAService(db)

        # Process the question (this can take 5-30 seconds)
        result = service.answer(
            question=question,
            workspace_id=workspace_id,
            user_id=user_id
        )

        logger.info(
            "[QA_WORKER] Job %s completed successfully",
            job_id,
        )

        # Result is already a dict (QAResult model is serialized)
        return {
            "success": True,
            "answer": result["answer"] if isinstance(result, dict) else result.answer,
            "executed_dsl": result["executed_dsl"] if isinstance(result, dict) else result.executed_dsl,
            "data": result["data"] if isinstance(result, dict) else result.data,
            "context_used": result.get("context_used") if isinstance(result, dict) else result.context_used,
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
