"""
RudderStack User Analytics
==========================

User event tracking that flows to Google Analytics 4.

Related files:
- app/routers/auth.py: Tracks user_signed_up, user_logged_in
- app/routers/google_oauth.py: Tracks connected_google_ads
- app/routers/meta_oauth.py: Tracks connected_meta_ads
- app/routers/shopify_oauth.py: Tracks connected_shopify
- app/routers/qa.py: Tracks copilot_query_sent

Setup:
1. Create account at rudderstack.com
2. Create a new source, select "Python"
3. Copy write key to RUDDERSTACK_WRITE_KEY
4. Copy data plane URL to RUDDERSTACK_DATA_PLANE_URL
5. Add Google Analytics 4 as a destination

Environment Variables:
- RUDDERSTACK_WRITE_KEY: Source write key (required)
- RUDDERSTACK_DATA_PLANE_URL: Data plane URL (required)

Events Tracked:
- user_signed_up: New user registration
- user_logged_in: User login
- connected_google_ads: Google Ads OAuth connected
- connected_meta_ads: Meta Ads OAuth connected
- connected_shopify: Shopify OAuth connected
- copilot_query_sent: AI copilot question asked
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from datetime import datetime

logger = logging.getLogger(__name__)


# RudderStack SDK import - gracefully handle if not installed
try:
    from rudderstack import analytics as rudderstack_analytics
    RUDDERSTACK_AVAILABLE = True
except ImportError:
    RUDDERSTACK_AVAILABLE = False
    rudderstack_analytics = None


# Track whether RudderStack has been initialized
_initialized = False


@lru_cache()
def get_rudderstack_config() -> tuple[Optional[str], Optional[str]]:
    """Get RudderStack configuration from environment.

    Returns:
        Tuple of (write_key, data_plane_url) or (None, None) if not configured.
    """
    write_key = os.environ.get("RUDDERSTACK_WRITE_KEY")
    data_plane_url = os.environ.get("RUDDERSTACK_DATA_PLANE_URL")
    return write_key, data_plane_url


def init_analytics() -> bool:
    """
    Initialize RudderStack analytics client.

    Should be called once during application startup.

    Returns:
        True if initialized successfully, False otherwise.

    Side effects:
        - Configures global RudderStack client
        - Enables async event sending

    Example:
        from app.telemetry.analytics import init_analytics

        def create_app():
            init_analytics()
            app = FastAPI()
            ...
    """
    global _initialized

    if not RUDDERSTACK_AVAILABLE:
        logger.warning("[ANALYTICS] rudderstack-sdk-python not installed - user tracking disabled")
        return False

    write_key, data_plane_url = get_rudderstack_config()

    if not write_key or not data_plane_url:
        logger.warning("[ANALYTICS] RudderStack not configured - user tracking disabled")
        return False

    try:
        rudderstack_analytics.write_key = write_key
        rudderstack_analytics.dataPlaneUrl = data_plane_url

        # Configure for async operation
        rudderstack_analytics.debug = os.environ.get("RUDDERSTACK_DEBUG", "false").lower() == "true"
        rudderstack_analytics.on_error = _on_rudderstack_error
        rudderstack_analytics.send = True
        rudderstack_analytics.sync_mode = False  # Async for better performance

        _initialized = True
        logger.debug("[ANALYTICS] RudderStack initialized")
        return True

    except Exception as e:
        logger.error(f"[ANALYTICS] Failed to initialize RudderStack: {e}")
        return False


def _on_rudderstack_error(error: Exception, items: list) -> None:
    """Error callback for RudderStack async operations."""
    logger.error(f"[ANALYTICS] RudderStack error: {error}, items: {len(items)}")


def identify(
    user_id: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
    traits: Optional[Dict[str, Any]] = None
) -> None:
    """
    Identify a user in the analytics system.

    Call this on signup and login to associate user properties with their ID.

    Args:
        user_id: Unique user identifier
        email: User's email address
        name: User's display name
        traits: Additional user properties

    Example:
        identify(
            user_id=str(user.id),
            email=user.email,
            name=user.name,
            traits={"workspace_id": str(user.workspace_id), "role": user.role}
        )
    """
    if not RUDDERSTACK_AVAILABLE or not _initialized:
        return

    try:
        user_traits = traits or {}
        if email:
            user_traits["email"] = email
        if name:
            user_traits["name"] = name

        rudderstack_analytics.identify(user_id, user_traits)

    except Exception as e:
        logger.error(f"[ANALYTICS] Failed to identify user: {e}")


def track(
    user_id: str,
    event: str,
    properties: Optional[Dict[str, Any]] = None
) -> None:
    """
    Track a user event.

    Args:
        user_id: User who performed the action
        event: Event name (e.g., "user_signed_up", "copilot_query_sent")
        properties: Event properties/metadata

    Events to track:
        - user_signed_up: New user registration
        - user_logged_in: User login
        - connected_google_ads: Google Ads OAuth connected
        - connected_meta_ads: Meta Ads OAuth connected
        - connected_shopify: Shopify OAuth connected
        - copilot_query_sent: AI copilot question asked

    Example:
        track(
            user_id=str(user.id),
            event="copilot_query_sent",
            properties={
                "workspace_id": str(workspace_id),
                "question_length": len(question),
                "has_context": bool(context),
            }
        )
    """
    if not RUDDERSTACK_AVAILABLE or not _initialized:
        return

    try:
        event_properties = properties or {}
        event_properties["timestamp"] = datetime.utcnow().isoformat()

        rudderstack_analytics.track(user_id, event, event_properties)

    except Exception as e:
        logger.error(f"[ANALYTICS] Failed to track event: {e}")


# Convenience functions for specific events


def track_user_signed_up(
    user_id: str,
    email: str,
    name: Optional[str] = None,
    workspace_id: Optional[str] = None
) -> None:
    """Track user signup event.

    Args:
        user_id: New user's ID
        email: User's email
        name: User's name
        workspace_id: Created workspace ID
    """
    # First identify the user
    identify(
        user_id=user_id,
        email=email,
        name=name,
        traits={"workspace_id": workspace_id} if workspace_id else None
    )

    # Then track the signup event
    track(
        user_id=user_id,
        event="user_signed_up",
        properties={
            "email": email,
            "name": name,
            "workspace_id": workspace_id,
        }
    )


def track_user_logged_in(
    user_id: str,
    email: str,
    workspace_id: Optional[str] = None
) -> None:
    """Track user login event.

    Args:
        user_id: User's ID
        email: User's email
        workspace_id: User's workspace ID
    """
    # Re-identify to update any changed properties
    identify(
        user_id=user_id,
        email=email,
        traits={"workspace_id": workspace_id, "last_login": datetime.utcnow().isoformat()}
    )

    track(
        user_id=user_id,
        event="user_logged_in",
        properties={
            "email": email,
            "workspace_id": workspace_id,
        }
    )


def track_connected_google_ads(
    user_id: str,
    workspace_id: str,
    account_id: Optional[str] = None,
    account_name: Optional[str] = None
) -> None:
    """Track Google Ads connection event.

    Args:
        user_id: User who connected
        workspace_id: Workspace where connection was added
        account_id: Google Ads account ID
        account_name: Google Ads account name
    """
    track(
        user_id=user_id,
        event="connected_google_ads",
        properties={
            "workspace_id": workspace_id,
            "account_id": account_id,
            "account_name": account_name,
            "provider": "google",
        }
    )


def track_connected_meta_ads(
    user_id: str,
    workspace_id: str,
    account_id: Optional[str] = None,
    account_name: Optional[str] = None
) -> None:
    """Track Meta Ads connection event.

    Args:
        user_id: User who connected
        workspace_id: Workspace where connection was added
        account_id: Meta Ads account ID
        account_name: Meta Ads account name
    """
    track(
        user_id=user_id,
        event="connected_meta_ads",
        properties={
            "workspace_id": workspace_id,
            "account_id": account_id,
            "account_name": account_name,
            "provider": "meta",
        }
    )


def track_connected_shopify(
    user_id: str,
    workspace_id: str,
    shop_domain: Optional[str] = None
) -> None:
    """Track Shopify connection event.

    Args:
        user_id: User who connected
        workspace_id: Workspace where connection was added
        shop_domain: Shopify shop domain
    """
    track(
        user_id=user_id,
        event="connected_shopify",
        properties={
            "workspace_id": workspace_id,
            "shop_domain": shop_domain,
            "provider": "shopify",
        }
    )


def track_copilot_query_sent(
    user_id: str,
    workspace_id: str,
    question_length: int,
    has_context: bool = False,
    success: Optional[bool] = None,
    latency_ms: Optional[int] = None
) -> None:
    """Track AI copilot query event.

    Args:
        user_id: User who asked
        workspace_id: Workspace context
        question_length: Length of question in characters
        has_context: Whether conversation context was provided
        success: Whether query succeeded (call after response)
        latency_ms: Response time in milliseconds
    """
    track(
        user_id=user_id,
        event="copilot_query_sent",
        properties={
            "workspace_id": workspace_id,
            "question_length": question_length,
            "has_context": has_context,
            "success": success,
            "latency_ms": latency_ms,
        }
    )


def flush() -> None:
    """
    Flush any pending analytics events.

    Call this before application shutdown to ensure all events are sent.
    """
    if not RUDDERSTACK_AVAILABLE or not _initialized:
        return

    try:
        rudderstack_analytics.flush()
    except Exception as e:
        logger.error(f"[ANALYTICS] Failed to flush events: {e}")
