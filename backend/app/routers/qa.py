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

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue
from rq.job import Job
import asyncio
import json
import os

from app.schemas import QARequest, QAJobResponse, QAJobStatusResponse
from app.database import get_db
from app.deps import get_current_user, get_settings


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

            # Debug: Log that job was enqueued
            print(f"[QA_ROUTER] Enqueued job {job.id} to qa_jobs queue (redis={redis_url})")
            print(f"[QA_ROUTER] Question: {req.question}")

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
