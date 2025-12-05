"""
QA Router
==========

HTTP endpoint for natural language question answering using the Agentic Copilot.

VERSION 4.0 - Agentic Copilot with LangGraph + Claude

Related files:
- app/agent/nodes.py: Agent nodes (understand, fetch_data, respond)
- app/agent/tools.py: SemanticTools wrapper
- app/agent/graph.py: LangGraph StateGraph
- app/services/semantic_qa_service.py: Semantic QA service (fallback)
- app/schemas.py: Request/response models

Primary Endpoints (v4.0):
- POST /qa/agent/sse: SSE streaming with typing effect (RECOMMENDED)
- POST /qa/agent/sync: Synchronous agent (no streaming)
- POST /qa/semantic: Direct semantic layer access

Legacy Endpoints (DEPRECATED):
- POST /qa: Deprecated - use /qa/agent/sse
- POST /qa/stream: Deprecated - use /qa/agent/sse
- GET /qa/jobs/{job_id}: Deprecated
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import timedelta

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue
from rq.job import Job

from app.schemas import QARequest, QAJobResponse, QAJobStatusResponse
from app.database import get_db
from app.deps import get_current_user, get_settings
from app import state  # Shared Redis pool
from app.telemetry import (
    track_copilot_query_sent,
    create_copilot_trace,
    complete_copilot_trace,
    log_generation,
    set_user_context,
)

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


@router.post("", response_model=QAJobResponse, deprecated=True)
def ask_question(
    req: QARequest,
    workspace_id: str = Query(..., description="Workspace context for scoping queries"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /qa

    DEPRECATED: Use POST /qa/agent/sse instead.

    This endpoint used the legacy DSL-based QA system which has been replaced
    by the Agentic Copilot (v4.0).
    """
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Use POST /qa/agent/sse for streaming or POST /qa/agent/sync for synchronous responses."
    )


@router.get("/jobs/{job_id}", response_model=QAJobStatusResponse, deprecated=True)
def get_job_status(
    job_id: str,
    current_user=Depends(get_current_user),
):
    """
    GET /qa/jobs/{job_id}

    DEPRECATED: The job-based QA system has been replaced by streaming.

    Use POST /qa/agent/sse for real-time streaming responses.
    """
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Use POST /qa/agent/sse for streaming responses."
    )


@router.post("/stream", deprecated=True)
async def ask_question_stream(
    req: QARequest,
    workspace_id: str = Query(..., description="Workspace context for scoping queries"),
    current_user=Depends(get_current_user),
):
    """
    POST /qa/stream

    DEPRECATED: Use POST /qa/agent/sse instead.

    This endpoint used the legacy DSL-based QA worker which has been replaced
    by the Agentic Copilot (v4.0).
    """
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Use POST /qa/agent/sse for streaming responses."
    )


# =============================================================================
# INSIGHTS ENDPOINT (Widget/Dashboard Integration)
# =============================================================================


class InsightsRequest(BaseModel):
    """Request for insights endpoint."""
    question: str
    metrics_data: Optional[Dict[str, Any]] = None  # Optional pre-fetched metrics


class InsightsResponse(BaseModel):
    """Response from insights endpoint."""
    success: bool
    answer: str
    intent: Optional[str] = None


def _normalize_question(question: str) -> str:
    """Normalize question for cache key.

    WHY: Questions like "What is my biggest drop today?" and
         "what is my biggest drop today" should hit same cache.
    """
    import re
    # Lowercase, remove extra spaces, remove punctuation
    normalized = question.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized


def _get_insight_cache_key(workspace_id: str, question: str) -> str:
    """Generate cache key for insight.

    Cache is scoped by:
    - workspace_id: Different workspaces have different data
    - question: Normalized question text
    - date: Insights refresh daily (data changes)
    """
    from datetime import date
    import hashlib

    normalized = _normalize_question(question)
    question_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
    date_str = date.today().isoformat()

    return f"insight:{workspace_id}:{question_hash}:{date_str}"


@router.post("/insights", response_model=InsightsResponse)
def get_insights(
    req: InsightsRequest,
    workspace_id: str = Query(..., description="Workspace UUID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /qa/insights

    Lightweight insights endpoint for dashboard widgets.

    WHAT:
        Returns AI-generated text insights WITHOUT visual generation.
        Optimized for widget integration where visuals are already rendered.

    CACHING:
        Insights are cached in Redis for 30 minutes per workspace + question.
        Cache key: insight:{workspace_id}:{question_hash}:{date}
        This prevents expensive Claude API calls on every dashboard load.

    WHY:
        - Dashboard/analytics pages already have their own charts
        - Faster response (skips visual building)
        - Lower token usage (no visual specs in response)
        - Caching reduces API costs and latency

    INPUT:
        {
            "question": "What is my biggest performance drop this week?",
            "metrics_data": { ... }  // Optional: pre-fetched metrics for context
        }

    OUTPUT:
        {
            "success": true,
            "answer": "Your CPC increased by 15% this week...",
            "intent": "analysis"
        }

    USAGE:
        - Dashboard insights widget
        - Analytics page summaries
        - Finance page highlights
    """
    import json as json_module
    from app.agent.nodes import get_claude_client, UNDERSTAND_PROMPT
    from app.agent.tools import SemanticTools

    user_id = str(current_user.id)
    question = req.question

    # ==========================================================================
    # CACHE CHECK: Return cached insight if available
    # ==========================================================================
    cache_key = _get_insight_cache_key(workspace_id, question)
    CACHE_TTL_SECONDS = 1800  # 30 minutes

    if state.redis_client:
        try:
            cached = state.redis_client.get(cache_key)
            if cached:
                logger.info(f"[QA_INSIGHTS] Cache HIT for {cache_key}")
                cached_data = json_module.loads(cached)
                return InsightsResponse(
                    success=cached_data.get("success", True),
                    answer=cached_data.get("answer", ""),
                    intent=cached_data.get("intent")
                )
        except Exception as e:
            logger.warning(f"[QA_INSIGHTS] Cache read failed: {e}")
            # Continue without cache - don't fail the request

    try:
        client = get_claude_client()

        # Step 1: Understand the question
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=UNDERSTAND_PROMPT,
            messages=[{"role": "user", "content": question}],
        )

        content = response.content[0].text
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
        else:
            json_str = content

        parsed = json_module.loads(json_str.strip())
        intent = parsed.get("intent", "metric_query")

        # Step 2: Fetch data (or use provided metrics_data)
        if req.metrics_data:
            # Use pre-fetched metrics data
            data = req.metrics_data
        else:
            # Fetch from semantic layer
            semantic_query = {
                "metrics": parsed.get("metrics") or ["roas"],
                "time_range": parsed.get("time_range") or "7d",
                "breakdown_level": parsed.get("breakdown_level"),
                "compare_to_previous": parsed.get("compare_to_previous") or True,  # Always compare for insights
                "include_timeseries": False,  # No charts needed
                "filters": parsed.get("filters") or {},
            }

            tools = SemanticTools(db, workspace_id, user_id)
            result = tools.query_metrics(
                metrics=semantic_query["metrics"],
                time_range=semantic_query["time_range"],
                breakdown_level=semantic_query.get("breakdown_level"),
                compare_to_previous=semantic_query.get("compare_to_previous", True),
                include_timeseries=False,  # No visuals
                filters=semantic_query.get("filters"),
            )

            if result.get("error"):
                return InsightsResponse(
                    success=False,
                    answer=f"Unable to analyze: {result['error']}",
                    intent=intent
                )

            data = result.get("data", {})

        # Step 3: Generate insight (no visuals, concise answer)
        INSIGHT_PROMPT = """You are a concise advertising analyst.

Generate a brief, actionable insight based on the data provided.

RULES:
- Maximum 2-3 sentences
- Focus on the most important finding
- Include specific numbers when available
- Be direct and actionable
- Do NOT mention charts, graphs, or visualizations
- Do NOT offer to show more data"""

        data_summary = json_module.dumps(data, indent=2, default=str)
        messages = [{
            "role": "user",
            "content": f"""Question: "{question}"

Data:
{data_summary}

Provide a brief insight."""
        }]

        insight_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,  # Keep responses short
            system=INSIGHT_PROMPT,
            messages=messages,
        )

        answer = insight_response.content[0].text

        # ==========================================================================
        # CACHE WRITE: Store result for future requests
        # ==========================================================================
        if state.redis_client:
            try:
                cache_data = json_module.dumps({
                    "success": True,
                    "answer": answer,
                    "intent": intent
                })
                state.redis_client.setex(cache_key, CACHE_TTL_SECONDS, cache_data)
                logger.info(f"[QA_INSIGHTS] Cache WRITE for {cache_key} (TTL: {CACHE_TTL_SECONDS}s)")
            except Exception as e:
                logger.warning(f"[QA_INSIGHTS] Cache write failed: {e}")
                # Don't fail the request if cache write fails

        return InsightsResponse(
            success=True,
            answer=answer,
            intent=intent
        )

    except Exception as e:
        logger.exception(f"[QA_INSIGHTS] Failed: {e}")
        return InsightsResponse(
            success=False,
            answer="Unable to generate insight at this time.",
            intent=None
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


# =============================================================================
# SEMANTIC LAYER ENDPOINT (NEW - for testing)
# =============================================================================

@router.post("/semantic")
def ask_question_semantic(
    req: QARequest,
    workspace_id: str = Query(..., description="Workspace context for scoping queries"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /qa/semantic

    **EXPERIMENTAL**: Test endpoint for the new Semantic Layer.

    This endpoint uses the new SemanticQAService which supports:
    - Composable queries (breakdown + comparison + timeseries together)
    - THE KEY FEATURE: "Compare CPC for top 3 ads this week vs last week"
    - Better observability via telemetry

    Input:  { "question": "Compare CPC for top 3 ads vs last week" }
    Output: { "answer": "...", "data": {...}, "query": {...}, "visuals": {...} }

    Unlike /qa and /qa/stream, this endpoint is SYNCHRONOUS (no Redis queue).
    Use for testing the semantic layer before full production rollout.
    """
    from app.services.semantic_qa_service import SemanticQAService
    import traceback

    try:
        logger.info(f"[QA_SEMANTIC] Processing: '{req.question}' for workspace={workspace_id}")
        service = SemanticQAService(db)
        result = service.answer(
            question=req.question,
            workspace_id=workspace_id,
            user_id=str(current_user.id),
        )
        logger.info(f"[QA_SEMANTIC] Success! Strategy: {result.get('telemetry', {}).get('strategy')}, has_visuals: {result.get('visuals') is not None}")
        return result

    except Exception as e:
        logger.error(f"[QA_SEMANTIC] Error: {type(e).__name__}: {e}")
        logger.error(f"[QA_SEMANTIC] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Semantic QA failed: {str(e)}"
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


# =============================================================================
# AGENTIC COPILOT ENDPOINTS (NEW - LangGraph Agent)
# =============================================================================

@router.post("/agent", response_model=QAJobResponse)
def ask_question_agent(
    req: QARequest,
    workspace_id: str = Query(..., description="Workspace context for scoping queries"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /qa/agent

    Enqueues a question for the LangGraph agent (agentic copilot).

    WHAT:
        This is the new fully agentic endpoint. Unlike /qa which uses DSL translation,
        this endpoint uses a LangGraph agent with Claude that can:
        - Understand natural language with context
        - Call semantic layer tools
        - Reason about data
        - Stream responses token-by-token

    Input:  { "question": "Why is my ROAS down?" }
    Output: { "job_id": "...", "status": "queued" }

    Use /qa/agent/stream/{job_id} to receive streaming updates.
    """
    try:
        if not state.redis_client or not state.qa_queue:
            raise HTTPException(status_code=503, detail="Redis not available")

        redis_conn = state.redis_client
        queue = state.qa_queue

        user_id = str(current_user.id)

        # Check for duplicate job
        dedup_key = _generate_dedup_key(user_id, workspace_id, f"agent:{req.question}")
        existing_job = _find_existing_job(redis_conn, queue, dedup_key)

        if existing_job:
            logger.info(f"[QA_AGENT] Returning existing job {existing_job.id} (dedup)")
            return QAJobResponse(
                job_id=existing_job.id,
                status="queued" if existing_job.is_queued else "processing"
            )

        # Get conversation history for context
        conversation_history = []
        if state.context_manager:
            try:
                context = state.context_manager.get_context(user_id, workspace_id)
                conversation_history = context[-5:]  # Last 5 entries
            except Exception as e:
                logger.warning(f"[QA_AGENT] Failed to get context: {e}")

        # Enqueue agent job
        job = queue.enqueue(
            "app.workers.agent_worker.process_agent_job",
            question=req.question,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_history=conversation_history,
            job_timeout=JOB_TIMEOUT_SECONDS,
            result_ttl=JOB_TTL_SECONDS,
            ttl=JOB_TTL_SECONDS,
        )

        # Store dedup key
        redis_conn.setex(dedup_key, DEDUP_WINDOW_SECONDS, job.id)

        logger.info(f"[QA_AGENT] Enqueued agent job {job.id}")

        return QAJobResponse(
            job_id=job.id,
            status="queued"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enqueue agent job: {str(e)}"
        )


@router.get("/agent/stream/{job_id}")
async def stream_agent_response(
    job_id: str,
    current_user=Depends(get_current_user),
):
    """
    GET /qa/agent/stream/{job_id}

    SSE endpoint for streaming agent responses via Redis Pub/Sub.

    WHAT:
        Subscribes to Redis Pub/Sub channel for the job and forwards events.
        Provides real-time typing effect for agent answers.

    Events:
        - {"type": "thinking", "data": {"text": "..."}}        - Agent is processing
        - {"type": "tool_call", "data": {"tool": "...", ...}}  - Tool being called
        - {"type": "tool_result", "data": {"preview": "..."}}  - Tool result
        - {"type": "answer", "data": {"token": "..."}}         - Answer token (typing)
        - {"type": "visual", "data": {"spec": {...}}}          - Chart/table spec
        - {"type": "done", "data": {...}}                      - Complete result
        - {"type": "error", "data": {"message": "..."}}        - Error occurred

    Usage (JavaScript):
        const eventSource = new EventSource('/qa/agent/stream/' + jobId);
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'answer') {
                // Append token to display (typing effect)
                display.textContent += data.data.token;
            }
        };
    """
    from app.agent.stream import create_subscriber

    async def event_generator():
        """
        Async generator that yields SSE events from Redis Pub/Sub.

        Flow:
        1. Subscribe to Redis channel for this job
        2. Also poll job.meta as fallback (if pub/sub fails)
        3. Forward events to client
        4. Close when done/error received
        """
        try:
            if not state.redis_client:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Redis not available'}})}\n\n"
                return

            # Try to subscribe to Redis pub/sub channel
            subscriber = None
            try:
                subscriber = create_subscriber(job_id)
                logger.info(f"[QA_AGENT] SSE subscriber created for job {job_id}")
            except Exception as e:
                logger.warning(f"[QA_AGENT] Failed to create subscriber: {e}")

            # Fallback: poll job meta if no subscriber
            if subscriber:
                # Use Redis Pub/Sub for real-time streaming
                for event in subscriber.listen():
                    # Forward event to SSE
                    yield f"data: {event.to_json()}\n\n"

                    if event.is_final:
                        break
            else:
                # Fallback to polling job status
                poll_interval_ms = SSE_POLL_MIN_MS
                last_stage = "queued"

                while True:
                    try:
                        job = Job.fetch(job_id, connection=state.redis_client)
                    except Exception:
                        yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Job not found'}})}\n\n"
                        break

                    # Get stage from meta
                    current_stage = job.meta.get('stage', 'queued') if job.is_started else 'queued'

                    # Emit stage changes
                    if current_stage != last_stage:
                        yield f"data: {json.dumps({'type': 'thinking', 'data': {'text': current_stage}})}\n\n"
                        last_stage = current_stage
                        poll_interval_ms = SSE_POLL_MIN_MS

                    # Check completion
                    if job.is_finished:
                        result = job.result or {}
                        yield f"data: {json.dumps({'type': 'done', 'data': result, 'is_final': True})}\n\n"
                        break

                    if job.is_failed:
                        error_msg = str(job.exc_info) if job.exc_info else "Job failed"
                        yield f"data: {json.dumps({'type': 'error', 'data': {'message': error_msg}, 'is_final': True})}\n\n"
                        break

                    await asyncio.sleep(poll_interval_ms / 1000)
                    poll_interval_ms = min(poll_interval_ms * SSE_POLL_BACKOFF, SSE_POLL_MAX_MS)

        except Exception as e:
            logger.exception(f"[QA_AGENT] SSE error for job {job_id}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}, 'is_final': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/agent/sync")
def ask_question_agent_sync(
    req: QARequest,
    workspace_id: str = Query(..., description="Workspace context for scoping queries"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /qa/agent/sync

    Synchronous endpoint for agent (no streaming).

    WHAT:
        Runs the agent synchronously and returns the full result.
        Use for testing or when streaming isn't needed.

    Note: This will block for 5-30 seconds depending on question complexity.
    Prefer /qa/agent + /qa/agent/stream/{job_id} for production use.
    """
    from app.workers.agent_worker import process_agent_job_sync

    try:
        user_id = str(current_user.id)

        # Get conversation history
        conversation_history = []
        if state.context_manager:
            try:
                context = state.context_manager.get_context(user_id, workspace_id)
                conversation_history = context[-5:]
            except Exception as e:
                logger.warning(f"[QA_AGENT] Failed to get context: {e}")

        # Run agent synchronously
        result = process_agent_job_sync(
            question=req.question,
            workspace_id=workspace_id,
            user_id=user_id,
            db=db,
            conversation_history=conversation_history,
        )

        return result

    except Exception as e:
        logger.exception(f"[QA_AGENT] Sync agent failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent failed: {str(e)}"
        )


# =============================================================================
# DIRECT SSE STREAMING ENDPOINT (no Redis)
# =============================================================================

@router.post("/agent/sse")
async def ask_question_agent_sse(
    req: QARequest,
    workspace_id: str = Query(..., description="Workspace context for scoping queries"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /qa/agent/sse

    Direct SSE streaming endpoint for agent (no Redis queue).

    WHAT:
        Streams agent response token-by-token via Server-Sent Events.
        Provides real-time typing effect in the frontend.

    EVENTS:
        - thinking: Agent is processing
        - token: Single answer token (for typing effect)
        - visual: Chart/table specification
        - done: Final result with all data
        - error: Something went wrong
    """
    from app.agent.graph import create_agent_graph
    from app.agent.state import create_initial_state
    from app.agent.nodes import get_claude_client, UNDERSTAND_PROMPT, RESPOND_PROMPT, _build_visuals_from_data
    from app.agent.tools import SemanticTools
    import json as json_module
    import time as time_module

    user_id = str(current_user.id)
    question = req.question

    # Set Sentry user context for error tracking
    set_user_context(
        user_id=user_id,
        email=current_user.email,
        workspace_id=workspace_id,
    )

    # Create Langfuse trace for LLM observability
    trace = create_copilot_trace(
        user_id=user_id,
        workspace_id=workspace_id,
        question=question,
    )

    # Track copilot query event (flows to Google Analytics)
    track_copilot_query_sent(
        user_id=user_id,
        workspace_id=workspace_id,
        question_length=len(question),
        has_context=False,  # TODO: Add context tracking
    )

    async def generate():
        """Generator that yields SSE events."""
        start_time = time_module.time()
        total_tokens = 0
        success = False

        try:
            # Stage 1: Understanding
            yield f"data: {json_module.dumps({'type': 'thinking', 'data': 'Understanding your question...'})}\n\n"

            client = get_claude_client()

            # Understand the question
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=UNDERSTAND_PROMPT,
                messages=[{"role": "user", "content": question}],
            )

            # Log understand generation to Langfuse
            if trace and response.usage:
                log_generation(
                    trace=trace,
                    name="understand",
                    model="claude-sonnet-4-20250514",
                    input_messages=[{"role": "user", "content": question}],
                    output=response.content[0].text,
                    usage={
                        "input": response.usage.input_tokens,
                        "output": response.usage.output_tokens,
                        "total": response.usage.input_tokens + response.usage.output_tokens,
                    },
                )
                total_tokens += response.usage.input_tokens + response.usage.output_tokens

            content = response.content[0].text
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            else:
                json_str = content

            parsed = json_module.loads(json_str.strip())
            intent = parsed.get("intent", "metric_query")

            # Build semantic query (use 'or' to handle null values)
            semantic_query = {
                "metrics": parsed.get("metrics") or ["roas"],
                "time_range": parsed.get("time_range") or "7d",
                "breakdown_level": parsed.get("breakdown_level"),
                "compare_to_previous": parsed.get("compare_to_previous") or False,
                "include_timeseries": parsed.get("include_timeseries") or False,
                "filters": parsed.get("filters") or {},
            }

            # Auto-enable timeseries for comparisons
            if semantic_query["compare_to_previous"] and not semantic_query["include_timeseries"]:
                semantic_query["include_timeseries"] = True

            yield f"data: {json_module.dumps({'type': 'thinking', 'data': 'Fetching your data...'})}\n\n"

            # Stage 2: Fetch data
            tools = SemanticTools(db, workspace_id, user_id)
            result = tools.query_metrics(
                metrics=semantic_query["metrics"],
                time_range=semantic_query["time_range"],
                breakdown_level=semantic_query.get("breakdown_level"),
                compare_to_previous=semantic_query.get("compare_to_previous", False),
                include_timeseries=semantic_query.get("include_timeseries", False),
                filters=semantic_query.get("filters"),
            )

            if result.get("error"):
                yield f"data: {json_module.dumps({'type': 'error', 'data': result['error']})}\n\n"
                return

            data = result.get("data", {})

            yield f"data: {json_module.dumps({'type': 'thinking', 'data': 'Preparing your answer...'})}\n\n"

            # Stage 3: Stream the response
            data_summary = json_module.dumps(data, indent=2, default=str)
            messages = [{
                "role": "user",
                "content": f"""User asked: "{question}"

Intent: {intent}

Data retrieved:
{data_summary}

Please write a helpful, conversational response based on this data."""
            }]

            full_answer = ""
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=RESPOND_PROMPT,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    full_answer += text
                    yield f"data: {json_module.dumps({'type': 'token', 'data': text})}\n\n"
                    await asyncio.sleep(0)  # Allow other tasks to run

                # Log respond generation to Langfuse (after stream completes)
                final_message = stream.get_final_message()
                if trace and final_message.usage:
                    log_generation(
                        trace=trace,
                        name="respond",
                        model="claude-sonnet-4-20250514",
                        input_messages=messages,
                        output=full_answer,
                        usage={
                            "input": final_message.usage.input_tokens,
                            "output": final_message.usage.output_tokens,
                            "total": final_message.usage.input_tokens + final_message.usage.output_tokens,
                        },
                    )
                    total_tokens += final_message.usage.input_tokens + final_message.usage.output_tokens

            # Stage 4: Send visuals
            visuals = _build_visuals_from_data(data, semantic_query)
            if visuals:
                yield f"data: {json_module.dumps({'type': 'visual', 'data': visuals}, default=str)}\n\n"

            # Stage 5: Done
            success = True
            final_result = {
                "success": True,
                "answer": full_answer,
                "visuals": visuals,
                "data": data,
                "semantic_query": semantic_query,
                "intent": intent,
            }
            yield f"data: {json_module.dumps({'type': 'done', 'data': final_result}, default=str)}\n\n"

            # Complete Langfuse trace
            latency_ms = int((time_module.time() - start_time) * 1000)
            complete_copilot_trace(
                trace=trace,
                success=True,
                answer=full_answer,
                latency_ms=latency_ms,
                total_tokens=total_tokens,
            )

        except Exception as e:
            logger.exception(f"[QA_AGENT_SSE] Failed: {e}")
            yield f"data: {json_module.dumps({'type': 'error', 'data': str(e)})}\n\n"

            # Complete Langfuse trace with error
            latency_ms = int((time_module.time() - start_time) * 1000)
            complete_copilot_trace(
                trace=trace,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
                total_tokens=total_tokens,
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
