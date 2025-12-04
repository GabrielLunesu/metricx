"""
Sentry Error Tracking
=====================

Centralized error tracking and performance monitoring using Sentry.

Related files:
- app/main.py: Initializes Sentry on app startup
- app/deps.py: Sets user context after authentication
- app/routers/*.py: Errors auto-captured with user context

Setup:
1. Create account at sentry.io
2. Create project with "FastAPI" platform
3. Copy DSN to SENTRY_DSN environment variable

Environment Variables:
- SENTRY_DSN: Sentry project DSN (required for Sentry to work)
- ENVIRONMENT: Environment name (production, staging, development)
"""

from __future__ import annotations

import os
import logging
from typing import Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


# Sentry SDK import - gracefully handle if not installed
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    sentry_sdk = None


@lru_cache()
def get_sentry_dsn() -> Optional[str]:
    """Get Sentry DSN from environment variable.

    Returns:
        DSN string if configured, None otherwise.
    """
    return os.environ.get("SENTRY_DSN")


def init_sentry() -> bool:
    """
    Initialize Sentry SDK for FastAPI.

    Should be called once during application startup, before any routes are defined.

    Returns:
        True if Sentry was initialized successfully, False otherwise.

    Side effects:
        - Configures global Sentry SDK
        - Sets up integrations for FastAPI, SQLAlchemy, Redis
        - Enables performance monitoring (traces)

    Example:
        from app.telemetry.sentry import init_sentry

        def create_app():
            init_sentry()  # Call before creating FastAPI app
            app = FastAPI()
            ...
    """
    if not SENTRY_AVAILABLE:
        logger.warning("[SENTRY] sentry-sdk not installed - error tracking disabled")
        return False

    dsn = get_sentry_dsn()
    if not dsn:
        return False

    environment = os.environ.get("ENVIRONMENT", "development")

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,

            # Integrations for comprehensive error capture
            integrations=[
                FastApiIntegration(
                    transaction_style="endpoint",  # Use route paths as transaction names
                ),
                SqlalchemyIntegration(),
                RedisIntegration(),
                LoggingIntegration(
                    level=logging.INFO,        # Capture INFO+ as breadcrumbs
                    event_level=logging.ERROR,  # Send ERROR+ as events
                ),
            ],

            # Performance monitoring
            traces_sample_rate=0.1,  # Sample 10% of transactions for performance
            profiles_sample_rate=0.1,  # Sample 10% of profiles

            # Error filtering
            send_default_pii=False,  # Don't send PII by default (we set user explicitly)

            # Release tracking (set via CI/CD)
            release=os.environ.get("RELEASE_VERSION"),
        )

        logger.debug(f"[SENTRY] Initialized for {environment} environment")
        return True

    except Exception as e:
        logger.error(f"[SENTRY] Failed to initialize: {e}")
        return False


def set_user_context(
    user_id: str,
    email: Optional[str] = None,
    workspace_id: Optional[str] = None
) -> None:
    """
    Set user context for Sentry error tracking.

    Should be called after successful authentication to attach user info
    to all subsequent errors in the request.

    Args:
        user_id: Unique user identifier
        email: User's email address (optional)
        workspace_id: User's current workspace (optional)

    Example:
        @app.get("/protected")
        def protected_route(user: User = Depends(get_current_user)):
            set_user_context(
                user_id=str(user.id),
                email=user.email,
                workspace_id=str(user.workspace_id)
            )
            # Any errors after this point will include user context
            ...
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        return

    try:
        sentry_sdk.set_user({
            "id": user_id,
            "email": email,
            "workspace_id": workspace_id,
        })
    except Exception as e:
        logger.debug(f"[SENTRY] Failed to set user context: {e}")


def clear_user_context() -> None:
    """
    Clear user context from Sentry.

    Should be called on logout or when user context should be removed.
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        return

    try:
        sentry_sdk.set_user(None)
    except Exception as e:
        logger.debug(f"[SENTRY] Failed to clear user context: {e}")


def capture_exception(exception: Exception, extra: Optional[dict] = None) -> None:
    """
    Manually capture an exception to Sentry.

    Use this for exceptions that are caught and handled but should still
    be tracked for monitoring purposes.

    Args:
        exception: The exception to capture
        extra: Additional context to attach to the event

    Example:
        try:
            risky_operation()
        except RiskyError as e:
            capture_exception(e, extra={"operation": "risky", "user_input": input})
            # Handle the error gracefully
            return fallback_response()
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        logger.error(f"Exception (Sentry disabled): {exception}")
        return

    try:
        with sentry_sdk.push_scope() as scope:
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_exception(exception)
    except Exception as e:
        logger.error(f"[SENTRY] Failed to capture exception: {e}")


def capture_message(message: str, level: str = "info", extra: Optional[dict] = None) -> None:
    """
    Capture a message to Sentry.

    Use this for important events that aren't exceptions but should
    be tracked.

    Args:
        message: The message to capture
        level: Severity level (debug, info, warning, error, fatal)
        extra: Additional context to attach

    Example:
        capture_message(
            "User exceeded rate limit",
            level="warning",
            extra={"user_id": user.id, "requests": count}
        )
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        logger.log(
            logging.getLevelName(level.upper()),
            f"Message (Sentry disabled): {message}"
        )
        return

    try:
        with sentry_sdk.push_scope() as scope:
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    except Exception as e:
        logger.error(f"[SENTRY] Failed to capture message: {e}")
