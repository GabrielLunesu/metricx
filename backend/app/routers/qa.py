"""
QA Router
==========

HTTP endpoint for natural language question answering using the DSL v1.1 pipeline.

UPDATED: Now uses async job queue for production reliability.

Related files:
- app/services/qa_service.py: Service layer
- app/workers/qa_worker.py: Async job worker
- app/schemas.py: Request/response models
- app/dsl/schema.py: DSL structure

Architecture:
- POST /qa: Enqueues job and returns job_id
- GET /qa/jobs/{job_id}: Polls for job status/result
- Uses Redis/RQ for job queue (same as sync jobs)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue
from rq.job import Job
import os

from app.schemas import QARequest, QAJobResponse, QAJobStatusResponse
from app.database import get_db
from app.deps import get_current_user


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
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
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
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
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
