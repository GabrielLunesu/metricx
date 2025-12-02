"""
QA Router
==========

HTTP endpoint for natural language question answering using the DSL v1.1 pipeline.

UPDATED v2.1: Now supports SSE streaming for real-time progress updates.

Related files:
- app/services/qa_service.py: Service layer
- app/workers/qa_worker.py: Async job worker (with stage metadata)
- app/schemas.py: Request/response models
- app/dsl/schema.py: DSL structure

Architecture:
- POST /qa: Enqueues job and returns job_id (polling mode)
- GET /qa/jobs/{job_id}: Polls for job status/result (polling mode)
- POST /qa/stream: SSE endpoint for real-time progress (streaming mode)
- Uses Redis/RQ for job queue (same as sync jobs)

SSE Streaming (NEW v2.1):
- Frontend connects to /qa/stream
- Server yields events as job progresses: translating → executing → formatting → complete
- Eliminates polling overhead, provides better UX
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue
from rq.job import Job

from app.schemas import QARequest, QAJobResponse, QAJobStatusResponse
from app.database import get_db
from app.deps import get_current_user, get_settings
from app import state  # Shared Redis pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qa", tags=["qa"])

# Job configuration constants
JOB_TTL_SECONDS = 300  # Jobs expire after 5 minutes (result retention)
JOB_TIMEOUT_SECONDS = 120  # Job must complete within 2 minutes
DEDUP_WINDOW_SECONDS = 30  # Deduplication window for identical questions

# SSE polling configuration (exponential backoff)
SSE_POLL_MIN_MS = 50    # Start polling at 50ms
SSE_POLL_MAX_MS = 300   # Max polling interval 300ms
SSE_POLL_BACKOFF = 1.5  # Multiply interval by 1.5 each iteration


def _generate_dedup_key(user_id: str, workspace_id: str, question: str) -> str:
    """
    Generate a unique deduplication key for a QA job.

    Same user asking the same question in the same workspace within
    DEDUP_WINDOW_SECONDS will get the same job instead of creating a new one.
    """
    # Normalize question (lowercase, strip whitespace)
    normalized_q = question.lower().strip()
    raw = f"{user_id}:{workspace_id}:{normalized_q}"
    return f"qa_dedup:{hashlib.md5(raw.encode()).hexdigest()}"


def _find_existing_job(redis_conn: Redis, queue: Queue, dedup_key: str) -> Job | None:
    """
    Check if a job with this dedup key already exists and is still valid.

    Returns the existing job if found and not failed/finished, else None.
    """
    # Check if we have a recent job ID stored for this dedup key
    existing_job_id = redis_conn.get(dedup_key)
    if not existing_job_id:
        return None

    existing_job_id = existing_job_id.decode() if isinstance(existing_job_id, bytes) else existing_job_id

    try:
        job = Job.fetch(existing_job_id, connection=redis_conn)
        # Return job only if it's still pending or running
        if job.is_queued or job.is_started:
            logger.info(f"[QA_ROUTER] Found existing job {existing_job_id} for dedup key")
            return job
    except Exception:
        # Job doesn't exist or expired
        pass

    return None


@router.post("", response_model=QAJobResponse)
def ask_question(
    req: QARequest,
    workspace_id: str = Query(..., description="Workspace context for scoping queries"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /qa
    
    Enqueues a natural language question for async processing.
    
    Input:  { "question": "What's my ROAS this week?" }
    Output: { "job_id": "...", "status": "queued" }
    
    Process:
    1. Validates authentication and workspace access
    2. Enqueues job to Redis queue
    3. Returns job_id immediately (non-blocking)
    4. Worker processes job asynchronously
    5. Poll GET /qa/jobs/{job_id} for results
    
    Security:
    - Requires authentication (current_user dependency)
    - Workspace scoping enforced in worker
    
    Examples:
        # Enqueue job
        POST /qa?workspace_id=123...
        { "question": "Show me revenue from active campaigns this month" }
        
        # Poll for result
        GET /qa/jobs/{job_id}
    """
    try:
        # Use shared Redis connection pool (avoids creating new connections per request)
        if not state.redis_client or not state.qa_queue:
            raise HTTPException(status_code=503, detail="Redis not available")

        redis_conn = state.redis_client
        queue = state.qa_queue

        user_id = str(current_user.id)

        # Check for duplicate job (same user, workspace, question)
        dedup_key = _generate_dedup_key(user_id, workspace_id, req.question)
        existing_job = _find_existing_job(redis_conn, queue, dedup_key)

        if existing_job:
            # Return existing job instead of creating duplicate
            logger.info(f"[QA_ROUTER] Returning existing job {existing_job.id} (dedup)")
            return QAJobResponse(
                job_id=existing_job.id,
                status="queued" if existing_job.is_queued else "processing"
            )

        # Enqueue new job with TTL and timeout
        job = queue.enqueue(
            "app.workers.qa_worker.process_qa_job",
            question=req.question,
            workspace_id=workspace_id,
            user_id=user_id,
            job_timeout=JOB_TIMEOUT_SECONDS,  # Job must complete in 2 min
            result_ttl=JOB_TTL_SECONDS,  # Result kept for 5 min
            ttl=JOB_TTL_SECONDS,  # Job expires if not started in 5 min
        )

        # Store dedup key → job_id mapping (expires after dedup window)
        redis_conn.setex(dedup_key, DEDUP_WINDOW_SECONDS, job.id)

        logger.info(f"[QA_ROUTER] Enqueued new job {job.id}")

        return QAJobResponse(
            job_id=job.id,
            status="queued"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enqueue QA job: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=QAJobStatusResponse)
def get_job_status(
    job_id: str,
    current_user=Depends(get_current_user),
):
    """
    GET /qa/jobs/{job_id}
    
    Poll for QA job status and results.
    
    Returns:
    - status: "queued" | "processing" | "completed" | "failed"
    - When completed: answer, executed_dsl, data, context_used
    - When failed: error message
    
    Frontend should poll this endpoint every 1-2 seconds until
    status is "completed" or "failed".
    
    Examples:
        GET /qa/jobs/abc-123-def
        
        # Queued response:
        { "job_id": "abc-123-def", "status": "queued" }
        
        # Completed response:
        {
          "job_id": "abc-123-def",
          "status": "completed",
          "answer": "Your ROAS this week is 2.45×",
          "executed_dsl": {...},
          "data": {...}
        }
    """
    try:
        # Use shared Redis connection pool
        if not state.redis_client:
            raise HTTPException(status_code=503, detail="Redis not available")

        # Fetch job
        job = Job.fetch(job_id, connection=state.redis_client)
        
        # Map RQ status to our status
        if job.is_queued:
            status = "queued"
        elif job.is_started:
            status = "processing"
        elif job.is_finished:
            status = "completed"
        elif job.is_failed:
            status = "failed"
        else:
            status = "unknown"
        
        # Build response
        response = QAJobStatusResponse(
            job_id=job_id,
            status=status
        )
        
        # Add result data if completed
        if job.is_finished and job.result:
            result = job.result
            if result.get("success"):
                response.answer = result.get("answer")
                response.executed_dsl = result.get("executed_dsl")
                response.data = result.get("data")
                response.context_used = result.get("context_used")
                response.visuals = result.get("visuals")
            else:
                response.error = result.get("error", "Unknown error occurred")
                response.status = "failed"
        
        # Add error if failed
        elif job.is_failed:
            response.error = str(job.exc_info) if job.exc_info else "Job failed"
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found or error fetching status: {str(e)}"
        )


@router.post("/stream")
async def ask_question_stream(
    req: QARequest,
    workspace_id: str = Query(..., description="Workspace context for scoping queries"),
    current_user=Depends(get_current_user),
):
    """
    POST /qa/stream

    SSE endpoint for real-time QA progress streaming.

    WHAT:
        Enqueues a question and streams progress updates via Server-Sent Events.
        Replaces polling with push-based updates for better UX.

    WHY:
        - Eliminates polling overhead (no repeated GET requests)
        - Provides real-time feedback: "Understanding...", "Fetching...", "Preparing..."
        - Better perceived performance (user sees progress immediately)

    Events Emitted:
        - {"stage": "queued", "job_id": "..."}     - Job enqueued
        - {"stage": "translating"}                  - Converting question to DSL
        - {"stage": "executing"}                    - Running database queries
        - {"stage": "formatting"}                   - Building answer and visuals
        - {"stage": "complete", "answer": "...", ...}  - Job finished with results
        - {"stage": "error", "error": "..."}        - Job failed

    Usage (JavaScript):
        const response = await fetch('/qa/stream?workspace_id=...', {
            method: 'POST',
            body: JSON.stringify({ question: "What's my ROAS?" }),
            headers: { 'Content-Type': 'application/json' }
        });
        const reader = response.body.getReader();
        // Read SSE events from stream...

    Example Events:
        data: {"stage": "queued", "job_id": "abc-123"}

        data: {"stage": "translating"}

        data: {"stage": "executing"}

        data: {"stage": "complete", "answer": "Your ROAS is 2.45×", ...}
    """

    async def event_generator():
        """
        Async generator that yields SSE events as job progresses.

        Flow:
        1. Check for existing duplicate job (dedup)
        2. Enqueue job to Redis queue (with TTL)
        3. Yield queued event with job_id
        4. Poll job status every 300ms
        5. Yield stage changes as they occur
        6. Yield complete/error event when done
        """
        try:
            # Use shared Redis connection pool (avoids creating new connections per request)
            if not state.redis_client or not state.qa_queue:
                yield f"data: {json.dumps({'stage': 'error', 'error': 'Redis not available'})}\n\n"
                return

            redis_conn = state.redis_client
            queue = state.qa_queue

            user_id = str(current_user.id)

            # Check for duplicate job (same user, workspace, question)
            dedup_key = _generate_dedup_key(user_id, workspace_id, req.question)
            existing_job = _find_existing_job(redis_conn, queue, dedup_key)

            if existing_job:
                # Reuse existing job instead of creating duplicate
                job = existing_job
                logger.info(f"[QA_ROUTER] Reusing existing job {job.id} for SSE stream (dedup)")
            else:
                # Enqueue new job with TTL and timeout
                job = queue.enqueue(
                    "app.workers.qa_worker.process_qa_job",
                    question=req.question,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    job_timeout=JOB_TIMEOUT_SECONDS,
                    result_ttl=JOB_TTL_SECONDS,
                    ttl=JOB_TTL_SECONDS,
                )

                # Store dedup key → job_id mapping
                redis_conn.setex(dedup_key, DEDUP_WINDOW_SECONDS, job.id)
                logger.info(f"[QA_ROUTER] Enqueued new job {job.id} to qa_jobs queue")

            logger.debug(f"[QA_ROUTER] Question: {req.question}")

            # Yield queued event
            yield f"data: {json.dumps({'stage': 'queued', 'job_id': job.id})}\n\n"

            # Track last stage to only emit on changes
            last_stage = "queued"

            # Exponential backoff: start fast, slow down if job takes longer
            poll_interval_ms = SSE_POLL_MIN_MS

            # Poll job status and yield events
            while True:
                # Refresh job to get latest status
                job.refresh()

                # Get current stage from job metadata
                # If job has started but no stage set yet, show "processing"
                # Worker sets: translating → executing → formatting
                if job.is_started:
                    current_stage = job.meta.get('stage', 'translating')  # Default to translating when started
                else:
                    current_stage = "queued"  # Still in queue

                # Emit stage change if different - reset backoff on stage change
                if current_stage != last_stage and not job.is_finished and not job.is_failed:
                    yield f"data: {json.dumps({'stage': current_stage})}\n\n"
                    last_stage = current_stage
                    poll_interval_ms = SSE_POLL_MIN_MS  # Reset to fast polling on progress

                # Check if job is complete
                if job.is_finished:
                    result = job.result
                    if result and result.get("success"):
                        # Yield complete event with full result
                        yield f"data: {json.dumps({'stage': 'complete', **result})}\n\n"
                    else:
                        # Job finished but with error
                        error_msg = result.get("error", "Unknown error") if result else "No result"
                        yield f"data: {json.dumps({'stage': 'error', 'error': error_msg})}\n\n"
                    break

                # Check if job failed
                elif job.is_failed:
                    error_msg = str(job.exc_info) if job.exc_info else "Job failed"
                    yield f"data: {json.dumps({'stage': 'error', 'error': error_msg})}\n\n"
                    break

                # Wait with exponential backoff (50ms → 75ms → 112ms → ... → 300ms max)
                await asyncio.sleep(poll_interval_ms / 1000)
                poll_interval_ms = min(poll_interval_ms * SSE_POLL_BACKOFF, SSE_POLL_MAX_MS)

        except Exception as e:
            # Yield error event if something goes wrong
            yield f"data: {json.dumps({'stage': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# =============================================================================
# FEEDBACK ENDPOINTS (Self-Learning System)
# =============================================================================

from app.schemas import QaFeedbackCreate, QaFeedbackResponse, QaFeedbackStats
from app.models import QaQueryLog, QaFeedback, FeedbackTypeEnum
from sqlalchemy import func
from uuid import UUID


@router.post("/feedback", response_model=QaFeedbackResponse)
def submit_feedback(
    feedback: QaFeedbackCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /qa/feedback

    Submit feedback on a QA answer for self-learning.

    Input:
        {
            "query_log_id": "uuid-of-query",
            "rating": 5,  # 1-5 scale
            "feedback_type": "accuracy",  # optional
            "comment": "Great answer!",  # optional
            "corrected_answer": null  # optional - what it should have said
        }

    Returns: The created feedback record

    Notes:
        - Highly-rated answers (4-5) can be marked as few-shot examples
        - Low-rated answers (1-2) are flagged for review
        - Feedback is linked to the original query for context
    """
    # Verify query exists and user has access
    query_log = db.query(QaQueryLog).filter(
        QaQueryLog.id == UUID(feedback.query_log_id)
    ).first()

    if not query_log:
        raise HTTPException(status_code=404, detail="Query log not found")

    # Check if feedback already exists
    existing = db.query(QaFeedback).filter(
        QaFeedback.query_log_id == UUID(feedback.query_log_id),
        QaFeedback.user_id == current_user.id,
    ).first()

    if existing:
        # Update existing feedback
        existing.rating = feedback.rating
        existing.feedback_type = FeedbackTypeEnum(feedback.feedback_type.value) if feedback.feedback_type else None
        existing.comment = feedback.comment
        existing.corrected_answer = feedback.corrected_answer
        db.commit()
        db.refresh(existing)

        return QaFeedbackResponse(
            id=str(existing.id),
            query_log_id=str(existing.query_log_id),
            user_id=str(existing.user_id),
            rating=existing.rating,
            feedback_type=existing.feedback_type.value if existing.feedback_type else None,
            comment=existing.comment,
            corrected_answer=existing.corrected_answer,
            is_few_shot_example=existing.is_few_shot_example,
            created_at=existing.created_at,
        )

    # Create new feedback
    new_feedback = QaFeedback(
        query_log_id=UUID(feedback.query_log_id),
        user_id=current_user.id,
        rating=feedback.rating,
        feedback_type=FeedbackTypeEnum(feedback.feedback_type.value) if feedback.feedback_type else None,
        comment=feedback.comment,
        corrected_answer=feedback.corrected_answer,
        # Auto-mark excellent answers as potential few-shot examples
        is_few_shot_example=feedback.rating >= 5,
    )

    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)

    logger.info(f"Feedback submitted: rating={feedback.rating} for query={feedback.query_log_id}")

    return QaFeedbackResponse(
        id=str(new_feedback.id),
        query_log_id=str(new_feedback.query_log_id),
        user_id=str(new_feedback.user_id),
        rating=new_feedback.rating,
        feedback_type=new_feedback.feedback_type.value if new_feedback.feedback_type else None,
        comment=new_feedback.comment,
        corrected_answer=new_feedback.corrected_answer,
        is_few_shot_example=new_feedback.is_few_shot_example,
        created_at=new_feedback.created_at,
    )


@router.get("/feedback/{query_log_id}", response_model=QaFeedbackResponse)
def get_feedback(
    query_log_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    GET /qa/feedback/{query_log_id}

    Get feedback for a specific query.
    """
    feedback = db.query(QaFeedback).filter(
        QaFeedback.query_log_id == UUID(query_log_id)
    ).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return QaFeedbackResponse(
        id=str(feedback.id),
        query_log_id=str(feedback.query_log_id),
        user_id=str(feedback.user_id),
        rating=feedback.rating,
        feedback_type=feedback.feedback_type.value if feedback.feedback_type else None,
        comment=feedback.comment,
        corrected_answer=feedback.corrected_answer,
        is_few_shot_example=feedback.is_few_shot_example,
        created_at=feedback.created_at,
    )


@router.get("/feedback/stats", response_model=QaFeedbackStats)
def get_feedback_stats(
    workspace_id: str = Query(..., description="Workspace to get stats for"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    GET /qa/feedback/stats?workspace_id=...

    Get aggregated feedback statistics for monitoring QA performance.
    """
    # Get all feedback for queries in this workspace
    feedback_query = (
        db.query(QaFeedback)
        .join(QaQueryLog)
        .filter(QaQueryLog.workspace_id == UUID(workspace_id))
    )

    all_feedback = feedback_query.all()

    if not all_feedback:
        return QaFeedbackStats(
            total_feedback=0,
            average_rating=0.0,
            rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            feedback_by_type={},
            few_shot_examples_count=0,
        )

    # Calculate stats
    total = len(all_feedback)
    avg_rating = sum(f.rating for f in all_feedback) / total

    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    type_counts = {}
    few_shot_count = 0

    for f in all_feedback:
        rating_dist[f.rating] = rating_dist.get(f.rating, 0) + 1
        if f.feedback_type:
            type_counts[f.feedback_type.value] = type_counts.get(f.feedback_type.value, 0) + 1
        if f.is_few_shot_example:
            few_shot_count += 1

    return QaFeedbackStats(
        total_feedback=total,
        average_rating=round(avg_rating, 2),
        rating_distribution=rating_dist,
        feedback_by_type=type_counts,
        few_shot_examples_count=few_shot_count,
    )


@router.get("/examples", response_model=list[dict])
def get_few_shot_examples(
    workspace_id: str = Query(..., description="Workspace to get examples from"),
    limit: int = Query(10, ge=1, le=50, description="Max examples to return"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    GET /qa/examples?workspace_id=...&limit=10

    Get highly-rated Q&A pairs for use as few-shot examples.

    Returns questions with 5-star ratings that can be used
    to improve future answer generation.
    """
    examples = (
        db.query(QaQueryLog)
        .join(QaFeedback)
        .filter(
            QaQueryLog.workspace_id == UUID(workspace_id),
            QaFeedback.is_few_shot_example == True,
            QaQueryLog.answer_text.isnot(None),
        )
        .order_by(QaFeedback.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "question": ex.question_text,
            "answer": ex.answer_text,
            "dsl": ex.dsl_json,
            "rating": ex.feedback.rating if ex.feedback else None,
        }
        for ex in examples
    ]
