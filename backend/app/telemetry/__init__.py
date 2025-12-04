"""
Telemetry Module
================

Observability stack for metricx platform.

Components:
- logging.py: Structured QA query logging
- sentry.py: Error tracking and performance monitoring
- analytics.py: User event tracking (RudderStack → Google Analytics)
- llm_trace.py: LLM observability (Langfuse)

Environment Variables Required:
- SENTRY_DSN: Sentry project DSN
- RUDDERSTACK_WRITE_KEY: RudderStack source write key
- RUDDERSTACK_DATA_PLANE_URL: RudderStack data plane URL
- LANGFUSE_PUBLIC_KEY: Langfuse project public key
- LANGFUSE_SECRET_KEY: Langfuse project secret key
- LANGFUSE_HOST: Langfuse host (optional, defaults to cloud.langfuse.com)

Usage:
    from app.telemetry import init_observability, shutdown_observability

    # Initialize all observability tools on app startup
    init_observability()

    # Clean shutdown on app exit
    shutdown_observability()

Related modules:
- app/main.py: Initializes observability on startup
- app/deps.py: Sets user context after authentication
- app/routers/auth.py: Tracks user signup/login events
- app/agent/nodes.py: LLM calls traced with Langfuse
"""

from app.telemetry.sentry import (
    init_sentry,
    set_user_context,
    clear_user_context,
    capture_exception,
    capture_message,
)
from app.telemetry.analytics import (
    init_analytics,
    identify,
    track,
    track_user_signed_up,
    track_user_logged_in,
    track_connected_google_ads,
    track_connected_meta_ads,
    track_connected_shopify,
    track_copilot_query_sent,
    flush as flush_analytics,
)
from app.telemetry.llm_trace import (
    init_langfuse,
    get_langfuse,
    trace_llm_call,
    log_generation,
    create_copilot_trace,
    complete_copilot_trace,
    log_span,
    flush as flush_langfuse,
    shutdown as shutdown_langfuse,
)
from app.telemetry.logging import log_qa_run, get_qa_stats


def init_observability() -> dict:
    """
    Initialize all observability tools.

    Should be called once during application startup.

    Returns:
        Dict with status of each tool initialization:
        {
            "sentry": True/False,
            "analytics": True/False,
            "langfuse": True/False,
        }

    Example:
        @app.on_event("startup")
        async def startup():
            status = init_observability()
            logger.info(f"Observability initialized: {status}")
    """
    return {
        "sentry": init_sentry(),
        "analytics": init_analytics(),
        "langfuse": init_langfuse(),
    }


def shutdown_observability() -> None:
    """
    Clean shutdown of all observability tools.

    Call this on application shutdown to flush pending events.

    Example:
        @app.on_event("shutdown")
        async def shutdown():
            shutdown_observability()
    """
    flush_analytics()
    flush_langfuse()
    shutdown_langfuse()


__all__ = [
    # Main initialization
    "init_observability",
    "shutdown_observability",
    # Sentry (error tracking)
    "init_sentry",
    "set_user_context",
    "clear_user_context",
    "capture_exception",
    "capture_message",
    # Analytics (user tracking)
    "init_analytics",
    "identify",
    "track",
    "track_user_signed_up",
    "track_user_logged_in",
    "track_connected_google_ads",
    "track_connected_meta_ads",
    "track_connected_shopify",
    "track_copilot_query_sent",
    "flush_analytics",
    # LLM tracing
    "init_langfuse",
    "get_langfuse",
    "trace_llm_call",
    "log_generation",
    "create_copilot_trace",
    "complete_copilot_trace",
    "log_span",
    "flush_langfuse",
    "shutdown_langfuse",
    # QA logging (existing)
    "log_qa_run",
    "get_qa_stats",
]
