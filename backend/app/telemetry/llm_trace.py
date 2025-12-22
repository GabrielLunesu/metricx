"""
Langfuse LLM Observability
==========================

LLM call tracing and monitoring using Langfuse.

Related files:
- app/agent/nodes.py: LLM calls to trace
- app/routers/qa.py: Entry point for copilot queries

Setup:
1. Create account at langfuse.com
2. Create a new project
3. Copy credentials to environment variables

Environment Variables:
- LANGFUSE_PUBLIC_KEY: Project public key (required)
- LANGFUSE_SECRET_KEY: Project secret key (required)
- LANGFUSE_HOST: Langfuse host (default: https://cloud.langfuse.com)

Metrics Captured:
- User query and model response
- Latency (time to first token, total time)
- Token usage (input/output/total)
- Model and parameters used
- Errors and exceptions
- User ID for query attribution
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Dict, Any, Generator
from functools import lru_cache
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


# Langfuse SDK import - gracefully handle if not installed
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None


# Global Langfuse client
_langfuse_client: Optional["Langfuse"] = None


@lru_cache()
def get_langfuse_config() -> tuple[Optional[str], Optional[str], str]:
    """Get Langfuse configuration from environment.

    Returns:
        Tuple of (public_key, secret_key, host).
    """
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    return public_key, secret_key, host


def init_langfuse() -> bool:
    """
    Initialize Langfuse client for LLM observability.

    Should be called once during application startup.

    Returns:
        True if initialized successfully, False otherwise.

    Example:
        from app.telemetry.llm_trace import init_langfuse

        def create_app():
            init_langfuse()
            app = FastAPI()
            ...
    """
    global _langfuse_client

    if not LANGFUSE_AVAILABLE:
        logger.warning("[LANGFUSE] langfuse not installed - LLM tracing disabled")
        return False

    public_key, secret_key, host = get_langfuse_config()

    if not public_key or not secret_key:
        return False

    try:
        _langfuse_client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )

        # Test connection
        _langfuse_client.auth_check()

        logger.debug(f"[LANGFUSE] Initialized (host: {host})")
        return True

    except Exception as e:
        logger.error(f"[LANGFUSE] Failed to initialize: {e}")
        _langfuse_client = None
        return False


def get_langfuse() -> Optional["Langfuse"]:
    """Get the global Langfuse client.

    Returns:
        Langfuse client if initialized, None otherwise.
    """
    return _langfuse_client


@contextmanager
def trace_llm_call(
    name: str,
    user_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Generator[Optional[Any], None, None]:
    """
    Context manager for tracing an LLM call.

    Use this to wrap LLM calls and automatically capture timing,
    tokens, and errors.

    Args:
        name: Name of the trace (e.g., "understand_node", "respond_node")
        user_id: User making the query
        workspace_id: Workspace context
        metadata: Additional metadata to attach

    Yields:
        Trace object if Langfuse is enabled, None otherwise.

    Example:
        with trace_llm_call("understand_node", user_id=user_id) as trace:
            response = client.messages.create(...)
            if trace:
                trace.generation(
                    name="claude-classify",
                    model="claude-sonnet-4-20250514",
                    input=messages,
                    output=response.content,
                    usage={"input": response.usage.input_tokens, "output": response.usage.output_tokens}
                )
    """
    if not _langfuse_client:
        yield None
        return

    trace = None
    try:
        trace_metadata = metadata or {}
        if workspace_id:
            trace_metadata["workspace_id"] = workspace_id

        trace = _langfuse_client.trace(
            name=name,
            user_id=user_id,
            metadata=trace_metadata,
        )

        yield trace

    except Exception as e:
        logger.error(f"[LANGFUSE] Trace error: {e}")
        if trace:
            try:
                trace.update(metadata={"error": str(e)})
            except Exception:
                pass
        yield None

    finally:
        # Ensure trace is flushed
        if _langfuse_client:
            try:
                _langfuse_client.flush()
            except Exception:
                pass


def log_generation(
    trace: Any,
    name: str,
    model: str,
    input_messages: Any,
    output: Any,
    usage: Optional[Dict[str, int]] = None,
    latency_ms: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an LLM generation to an existing trace.

    Args:
        trace: Langfuse span object
        name: Generation name (e.g., "understand", "respond")
        model: Model used (e.g., "claude-sonnet-4-20250514")
        input_messages: Input messages sent to LLM
        output: Output received from LLM
        usage: Token usage dict with "input", "output", "total" keys
        latency_ms: Response latency in milliseconds
        metadata: Additional metadata
    """
    if not trace or not _langfuse_client:
        return

    try:
        gen_metadata = metadata or {}
        if latency_ms:
            gen_metadata["latency_ms"] = latency_ms
        gen_metadata["model"] = model

        # Langfuse v3 API: create a child generation span
        generation = _langfuse_client.start_generation(
            name=name,
            model=model,
            input=input_messages,
            metadata=gen_metadata,
        )

        # Update with output and usage, then end
        generation.update(
            output=output,
            usage_details=usage,
        )
        generation.end()

    except Exception as e:
        logger.error(f"[LANGFUSE] Failed to log generation: {e}")


def create_copilot_trace(
    user_id: str,
    workspace_id: str,
    question: str,
    session_id: Optional[str] = None,
) -> Optional[Any]:
    """
    Create a trace for a copilot query session.

    This is the main entry point for tracing a full copilot interaction.
    Returns a trace that can be passed to individual LLM call functions.

    Args:
        user_id: User making the query
        workspace_id: Workspace context
        question: User's question
        session_id: Conversation session ID for grouping

    Returns:
        Trace object if Langfuse is enabled, None otherwise.

    Example:
        trace = create_copilot_trace(
            user_id=str(user.id),
            workspace_id=str(workspace_id),
            question=question,
            session_id=session_id,
        )

        # Pass trace to nodes
        state = run_agent(db, workspace_id, question, trace=trace)

        # Complete trace
        if trace:
            complete_copilot_trace(trace, success=True, answer=state["answer"])
    """
    if not _langfuse_client:
        return None

    try:
        # Langfuse v3 API uses start_span for traces
        trace = _langfuse_client.start_span(
            name="copilot_query",
            metadata={
                "user_id": user_id,
                "workspace_id": workspace_id,
                "question": question,
                "question_length": len(question),
                "session_id": session_id,
            },
            input={"question": question},
        )

        return trace

    except Exception as e:
        logger.error(f"[LANGFUSE] Failed to create copilot trace: {e}")
        return None


def complete_copilot_trace(
    trace: Any,
    success: bool,
    answer: Optional[str] = None,
    error: Optional[str] = None,
    latency_ms: Optional[int] = None,
    total_tokens: Optional[int] = None,
) -> None:
    """
    Complete a copilot trace with final results.

    Args:
        trace: Trace object from create_copilot_trace
        success: Whether the query succeeded
        answer: Generated answer text
        error: Error message if failed
        latency_ms: Total latency
        total_tokens: Total tokens used across all LLM calls
    """
    if not trace:
        return

    try:
        # Langfuse v3 API: update with output, then end
        trace.update(
            output={"answer": answer} if answer else {"error": error},
            metadata={
                "success": success,
                "latency_ms": latency_ms,
                "total_tokens": total_tokens,
            },
        )
        trace.end()

        if _langfuse_client:
            _langfuse_client.flush()

    except Exception as e:
        logger.error(f"[LANGFUSE] Failed to complete trace: {e}")


def log_span(
    trace: Any,
    name: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """
    Log a span (non-LLM operation) to a trace.

    Use this for tracing tool calls, database queries, or other
    operations that aren't direct LLM calls.

    Args:
        trace: Parent trace object
        name: Span name (e.g., "fetch_data", "query_metrics")
        start_time: When the operation started
        end_time: When the operation ended
        metadata: Additional metadata

    Returns:
        Span object for nested spans, None if tracing disabled.
    """
    if not trace:
        return None

    try:
        span = trace.span(
            name=name,
            start_time=start_time,
            end_time=end_time,
            metadata=metadata,
        )
        return span

    except Exception as e:
        logger.error(f"[LANGFUSE] Failed to log span: {e}")
        return None


def log_live_api_call(
    trace: Any,
    provider: str,
    endpoint: str,
    latency_ms: int,
    success: bool,
    error: Optional[str] = None,
    workspace_id: Optional[str] = None,
    account_id: Optional[str] = None,
    entity_count: Optional[int] = None,
) -> None:
    """
    Log a live API call to Langfuse for monitoring.

    WHAT:
        Records details of a live Google/Meta Ads API call as a span
        in the current trace.

    WHY:
        - Monitor live API usage patterns
        - Track success/failure rates per provider
        - Identify latency issues
        - Debug API errors
        - Audit API access by workspace

    PARAMETERS:
        trace: Parent trace object from create_copilot_trace
        provider: "google" or "meta"
        endpoint: API endpoint called (e.g., "get_metrics", "list_campaigns")
        latency_ms: Response latency in milliseconds
        success: Whether the call succeeded
        error: Error message if call failed
        workspace_id: Workspace making the call (for audit)
        account_id: Ad account ID queried
        entity_count: Number of entities returned (for monitoring)

    EXAMPLE:
        log_live_api_call(
            trace=trace,
            provider="google",
            endpoint="get_live_metrics",
            latency_ms=245,
            success=True,
            workspace_id="...",
            account_id="123-456-7890",
            entity_count=5,
        )
    """
    if not trace or not _langfuse_client:
        return

    try:
        # Build metadata
        metadata = {
            "provider": provider,
            "endpoint": endpoint,
            "latency_ms": latency_ms,
            "success": success,
        }

        if workspace_id:
            metadata["workspace_id"] = workspace_id
        if account_id:
            metadata["account_id"] = account_id
        if entity_count is not None:
            metadata["entity_count"] = entity_count
        if error:
            metadata["error"] = error

        # Create span for the API call
        span = trace.span(
            name=f"live_api_{provider}_{endpoint}",
            metadata=metadata,
        )

        if span:
            span.end()

    except Exception as e:
        logger.error(f"[LANGFUSE] Failed to log live API call: {e}")


def log_live_api_fallback(
    trace: Any,
    from_source: str,
    to_source: str,
    reason: str,
    workspace_id: Optional[str] = None,
) -> None:
    """
    Log a fallback event (e.g., live API → snapshot, or vice versa).

    WHAT:
        Records when the agent falls back from one data source to another.

    WHY:
        - Track how often live API is used vs snapshots
        - Identify patterns in fallback behavior
        - Monitor auto-fallback triggers (staleness, errors)

    PARAMETERS:
        trace: Parent trace object
        from_source: Original data source ("live_api" or "snapshot")
        to_source: Fallback data source ("live_api" or "snapshot")
        reason: Why fallback occurred (e.g., "stale_snapshot", "api_error", "rate_limited")
        workspace_id: Workspace context
    """
    if not trace or not _langfuse_client:
        return

    try:
        metadata = {
            "from_source": from_source,
            "to_source": to_source,
            "reason": reason,
        }

        if workspace_id:
            metadata["workspace_id"] = workspace_id

        span = trace.span(
            name="data_source_fallback",
            metadata=metadata,
        )

        if span:
            span.end()

    except Exception as e:
        logger.error(f"[LANGFUSE] Failed to log fallback: {e}")


def flush() -> None:
    """
    Flush any pending Langfuse events.

    Call this before application shutdown to ensure all traces are sent.
    """
    if _langfuse_client:
        try:
            _langfuse_client.flush()
            logger.info("[LANGFUSE] Flushed pending traces")
        except Exception as e:
            logger.error(f"[LANGFUSE] Failed to flush: {e}")


def shutdown() -> None:
    """
    Shutdown Langfuse client cleanly.

    Call this on application shutdown.
    """
    global _langfuse_client

    if _langfuse_client:
        try:
            _langfuse_client.flush()
            _langfuse_client.shutdown()
            logger.info("[LANGFUSE] Shutdown complete")
        except Exception as e:
            logger.error(f"[LANGFUSE] Shutdown error: {e}")
        finally:
            _langfuse_client = None
