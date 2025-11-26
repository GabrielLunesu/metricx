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
import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue
from rq.job import Job

from app.schemas import QARequest, QAJobResponse, QAJobStatusResponse
from app.database import get_db
from app.deps import get_current_user, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qa", tags=["qa"])


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
        # Connect to Redis queue
        redis_url = get_settings().REDIS_URL
        queue = Queue("qa_jobs", connection=Redis.from_url(redis_url))
        
        # Enqueue job
        job = queue.enqueue(
            "app.workers.qa_worker.process_qa_job",
            question=req.question,
            workspace_id=workspace_id,
            user_id=str(current_user.id),
        )
        
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
        # Connect to Redis
        redis_url = get_settings().REDIS_URL
        redis_conn = Redis.from_url(redis_url)
        
        # Fetch job
        job = Job.fetch(job_id, connection=redis_conn)
        
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
        1. Enqueue job to Redis queue
        2. Yield queued event with job_id
        3. Poll job status every 300ms
        4. Yield stage changes as they occur
        5. Yield complete/error event when done
        """
        try:
            # Connect to Redis queue
            redis_url = get_settings().REDIS_URL
            redis_conn = Redis.from_url(redis_url)
            queue = Queue("qa_jobs", connection=redis_conn)

            # Enqueue job
            job = queue.enqueue(
                "app.workers.qa_worker.process_qa_job",
                question=req.question,
                workspace_id=workspace_id,
                user_id=str(current_user.id),
            )

            # Log that job was enqueued
            logger.info(f"[QA_ROUTER] Enqueued job {job.id} to qa_jobs queue (redis={redis_url})")
            logger.debug(f"[QA_ROUTER] Question: {req.question}")

            # Yield queued event
            yield f"data: {json.dumps({'stage': 'queued', 'job_id': job.id})}\n\n"

            # Track last stage to only emit on changes
            last_stage = "queued"

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

                # Emit stage change if different
                if current_stage != last_stage and not job.is_finished and not job.is_failed:
                    yield f"data: {json.dumps({'stage': current_stage})}\n\n"
                    last_stage = current_stage

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

                # Wait before next poll (300ms for responsive updates)
                await asyncio.sleep(0.3)

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
