"""Pixel events endpoint for Shopify Web Pixel Extension.

WHAT:
    Receives events from the Shopify Web Pixel Extension.
    Stores events for journey tracking and attribution.
    Streams pixel events in real-time via WebSocket to dashboard viewers.

WHY:
    The Web Pixel captures customer journey events (page views, add to cart, checkout)
    that we use to attribute orders to marketing campaigns.
    Real-time streaming lets merchants see customer activity as it happens.

REFERENCES:
    - docs/living-docs/ATTRIBUTION_ENGINE.md
    - Shopify Web Pixels API: https://shopify.dev/docs/api/web-pixels-api
    - backend/app/services/pixel_websocket_manager.py (WebSocket manager)
    - ui/hooks/usePixelStream.js (frontend consumer)
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import authenticate_websocket
from app.models import (
    Workspace,
    PixelEvent,
    CustomerJourney,
    JourneyTouchpoint,
)
from app.services.pixel_websocket_manager import pixel_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Pixel Events"])


# =============================================================================
# CORS HELPERS FOR PIXEL ENDPOINT
# =============================================================================
# WHAT: Pixel events come from any Shopify store, so we need to allow all origins
# WHY: The web pixel runs on customer stores (e.g., mystore.myshopify.com)


def add_cors_headers(response: Response, origin: str = "*") -> Response:
    """Add CORS headers to response for pixel endpoint."""
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Max-Age"] = "86400"  # Cache preflight for 24h
    return response


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================


class Attribution(BaseModel):
    """Attribution data captured by the pixel.

    WHAT: UTM parameters and click IDs from the landing page
    WHY: Used to attribute conversions to marketing campaigns
    """
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    fbclid: Optional[str] = None
    gclid: Optional[str] = None
    ttclid: Optional[str] = None
    landing_page: Optional[str] = None
    landed_at: Optional[str] = None


class EventContext(BaseModel):
    """Context data from the browser.

    WHAT: Current page URL and referrer
    WHY: Provides context for the event and can be used for attribution inference
    """
    url: Optional[str] = None
    referrer: Optional[str] = None


class PixelEventRequest(BaseModel):
    """Request body for pixel events.

    WHAT: Event data from the Shopify Web Pixel Extension
    WHY: Standardized schema for all pixel events

    Example:
        {
            "workspace_id": "uuid",
            "visitor_id": "mx_12345abc",
            "event_id": "evt_unique123",
            "event": "page_viewed",
            "data": {"path": "/products/test"},
            "attribution": {"utm_source": "meta", "fbclid": "abc123"},
            "context": {"url": "https://store.myshopify.com/products/test"},
            "ts": "2025-11-30T12:00:00Z"
        }
    """
    workspace_id: str = Field(..., description="Workspace UUID")
    visitor_id: str = Field(..., description="Pixel-generated visitor ID")
    event_id: Optional[str] = Field(None, description="Client-generated UUID for deduplication")
    event: str = Field(..., description="Event type (page_viewed, checkout_completed, etc.)")
    data: Optional[Dict[str, Any]] = Field(default={}, description="Event-specific data")
    attribution: Optional[Attribution] = Field(None, description="Attribution data")
    context: Optional[EventContext] = Field(None, description="Browser context")
    ts: Optional[str] = Field(None, description="Event timestamp (ISO 8601)")


class PixelEventResponse(BaseModel):
    """Response for pixel events.

    WHAT: Confirmation of event receipt with deduplication status
    WHY: Client needs to know if event was accepted or deduplicated
    """
    status: str = Field(..., description="ok, duplicate, or error")
    event_id: Optional[str] = Field(None, description="Server-assigned event ID")
    journey_id: Optional[str] = Field(None, description="Associated journey ID")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _has_attribution_data(attribution: Optional[Attribution]) -> bool:
    """Check if attribution object contains any attribution data.

    WHAT: Returns True if any UTM, click ID, or landing page is present
    WHY: Only create touchpoints for events with attribution data
    """
    if not attribution:
        return False
    return any([
        attribution.utm_source,
        attribution.utm_campaign,
        attribution.fbclid,
        attribution.gclid,
        attribution.ttclid,
    ])


def _is_touchpoint_event(event_type: str) -> bool:
    """Check if event type should create a touchpoint.

    WHAT: Touchpoints are created for first visit and checkout events
    WHY: We track attribution at key conversion points, not every page view
    """
    # Create touchpoint for page_viewed (first visit captures UTMs) and checkout events
    return event_type in [
        "page_viewed",
        "checkout_started",
        "checkout_completed",
    ]


def _get_or_create_journey(
    db: Session,
    workspace_id: UUID,
    visitor_id: str,
    attribution: Optional[Attribution],
) -> CustomerJourney:
    """Get existing journey or create new one.

    WHAT: Finds journey by workspace + visitor_id, creates if not exists
    WHY: One journey per visitor per workspace (upsert pattern)

    Args:
        db: Database session
        workspace_id: Workspace UUID
        visitor_id: Pixel visitor ID
        attribution: Optional attribution data for first touch

    Returns:
        CustomerJourney: Existing or newly created journey
    """
    journey = db.query(CustomerJourney).filter(
        CustomerJourney.workspace_id == workspace_id,
        CustomerJourney.visitor_id == visitor_id,
    ).first()

    now = datetime.utcnow()

    if journey:
        # Update last_seen_at
        journey.last_seen_at = now
        logger.debug(f"[PIXEL] Updated journey {journey.id} for visitor {visitor_id}")
    else:
        # Create new journey
        journey = CustomerJourney(
            workspace_id=workspace_id,
            visitor_id=visitor_id,
            first_seen_at=now,
            last_seen_at=now,
            touchpoint_count=0,
            total_orders=0,
            total_revenue=0,
        )

        # Set first touch attribution if available
        if attribution and _has_attribution_data(attribution):
            journey.first_touch_source = attribution.utm_source
            journey.first_touch_medium = attribution.utm_medium
            journey.first_touch_campaign = attribution.utm_campaign

        db.add(journey)
        logger.info(f"[PIXEL] Created new journey for visitor {visitor_id}")

    return journey


def _update_last_touch(journey: CustomerJourney, attribution: Attribution) -> None:
    """Update last touch attribution on journey.

    WHAT: Updates the last_touch_* fields with new attribution data
    WHY: Last touch is used for last-click attribution model
    """
    if attribution.utm_source:
        journey.last_touch_source = attribution.utm_source
    if attribution.utm_medium:
        journey.last_touch_medium = attribution.utm_medium
    if attribution.utm_campaign:
        journey.last_touch_campaign = attribution.utm_campaign


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.options("/pixel-events")
async def pixel_events_preflight(request: Request):
    """Handle CORS preflight for pixel events.

    WHAT: Responds to OPTIONS request with CORS headers
    WHY: Browser sends preflight before cross-origin POST
    """
    response = Response(status_code=200)
    origin = request.headers.get("origin", "*")
    return add_cors_headers(response, origin)


@router.post("/pixel-events", response_model=PixelEventResponse)
async def receive_pixel_event(
    request: Request,
    payload: PixelEventRequest,
    db: Session = Depends(get_db),
):
    """Receive events from Shopify Web Pixel Extension.

    WHAT:
        Validates workspace, deduplicates by event_id, stores event,
        and updates customer journey.

    WHY:
        Central endpoint for pixel data collection. Enables attribution
        by tracking customer journeys from ad click to purchase.

    Args:
        payload: PixelEventRequest with event data
        db: Database session

    Returns:
        PixelEventResponse with status and IDs

    Raises:
        HTTPException 400: Invalid workspace_id
    """
    # 1. Validate workspace exists
    try:
        workspace_id = UUID(payload.workspace_id)
    except ValueError:
        logger.warning(f"[PIXEL] Invalid workspace_id format: {payload.workspace_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace_id format"
        )

    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        logger.warning(f"[PIXEL] Unknown workspace_id: {payload.workspace_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace"
        )

    # 2. Deduplicate by event_id (idempotency check)
    if payload.event_id:
        existing = db.query(PixelEvent).filter(
            PixelEvent.workspace_id == workspace_id,
            PixelEvent.event_id == payload.event_id,
        ).first()

        if existing:
            logger.debug(f"[PIXEL] Duplicate event_id: {payload.event_id}")
            from fastapi.responses import JSONResponse
            origin = request.headers.get("origin", "*")
            response = JSONResponse(
                content={
                    "status": "duplicate",
                    "event_id": str(existing.id),
                }
            )
            return add_cors_headers(response, origin)

    # 3. Parse timestamp
    event_ts = None
    if payload.ts:
        try:
            event_ts = datetime.fromisoformat(payload.ts.replace("Z", "+00:00"))
        except ValueError:
            event_ts = datetime.utcnow()
    else:
        event_ts = datetime.utcnow()

    # 4. Store PixelEvent (immutable log for event sourcing)
    attr = payload.attribution
    ctx = payload.context

    pixel_event = PixelEvent(
        workspace_id=workspace_id,
        visitor_id=payload.visitor_id,
        event_id=payload.event_id,
        event_type=payload.event,
        event_data=payload.data or {},
        # Attribution fields
        utm_source=attr.utm_source if attr else None,
        utm_medium=attr.utm_medium if attr else None,
        utm_campaign=attr.utm_campaign if attr else None,
        utm_content=attr.utm_content if attr else None,
        utm_term=attr.utm_term if attr else None,
        fbclid=attr.fbclid if attr else None,
        gclid=attr.gclid if attr else None,
        ttclid=attr.ttclid if attr else None,
        landing_page=attr.landing_page if attr else None,
        # Context
        url=ctx.url if ctx else None,
        referrer=ctx.referrer if ctx else None,
        # Timestamp
        created_at=event_ts,
    )
    db.add(pixel_event)
    db.flush()  # Get ID

    logger.info(
        f"[PIXEL] Stored event",
        extra={
            "event_id": str(pixel_event.id),
            "workspace_id": str(workspace_id),
            "visitor_id": payload.visitor_id,
            "event_type": payload.event,
        }
    )

    # 5. Get or create CustomerJourney
    journey = _get_or_create_journey(
        db=db,
        workspace_id=workspace_id,
        visitor_id=payload.visitor_id,
        attribution=payload.attribution,
    )
    # Flush to get journey.id for touchpoint foreign key
    db.flush()

    # 6. Add touchpoint if has attribution data and is a touchpoint event
    if (
        _is_touchpoint_event(payload.event)
        and _has_attribution_data(payload.attribution)
    ):
        touchpoint = JourneyTouchpoint(
            journey_id=journey.id,
            event_type=payload.event,
            utm_source=attr.utm_source if attr else None,
            utm_medium=attr.utm_medium if attr else None,
            utm_campaign=attr.utm_campaign if attr else None,
            utm_content=attr.utm_content if attr else None,
            utm_term=attr.utm_term if attr else None,
            fbclid=attr.fbclid if attr else None,
            gclid=attr.gclid if attr else None,
            ttclid=attr.ttclid if attr else None,
            landing_page=attr.landing_page if attr else None,
            referrer=ctx.referrer if ctx else None,
            touched_at=event_ts,
        )
        db.add(touchpoint)

        # Update journey touchpoint count
        journey.touchpoint_count = (journey.touchpoint_count or 0) + 1

        # Update last touch
        if attr:
            _update_last_touch(journey, attr)

        logger.info(
            f"[PIXEL] Created touchpoint for journey {journey.id}",
            extra={
                "utm_source": attr.utm_source if attr else None,
                "gclid": attr.gclid if attr else None,
            }
        )

    # 7. Link checkout_token to journey (for webhook merge)
    if payload.event == "checkout_completed" and payload.data:
        checkout_token = payload.data.get("checkout_token")
        if checkout_token:
            journey.checkout_token = checkout_token
            logger.info(
                f"[PIXEL] Linked checkout_token to journey",
                extra={
                    "journey_id": str(journey.id),
                    "checkout_token": checkout_token,
                }
            )

    # 8. Commit all changes
    db.commit()

    # NOTE: Do NOT trigger attribution here!
    # Attribution is triggered by orders/paid webhook

    # 9. Broadcast to connected WebSocket clients (fire-and-forget)
    # WHY: Real-time feed on attribution page — viewers see events as they arrive
    try:
        await pixel_ws_manager.broadcast(workspace_id, {
            "type": "pixel_event",
            "id": str(pixel_event.id),
            "event_type": pixel_event.event_type,
            "visitor_id": pixel_event.visitor_id,
            "url": pixel_event.url,
            "utm_source": pixel_event.utm_source,
            "utm_medium": pixel_event.utm_medium,
            "utm_campaign": pixel_event.utm_campaign,
            "created_at": pixel_event.created_at.isoformat(),
        })
    except Exception as e:
        # Never let broadcast failure affect pixel ingestion
        logger.warning(f"[PIXEL] WebSocket broadcast failed: {e}")

    # Build response with CORS headers
    from fastapi.responses import JSONResponse
    origin = request.headers.get("origin", "*")
    response = JSONResponse(
        content={
            "status": "ok",
            "event_id": str(pixel_event.id),
            "journey_id": str(journey.id),
        }
    )
    return add_cors_headers(response, origin)


# =============================================================================
# WEBSOCKET ENDPOINT — Real-Time Pixel Event Stream
# =============================================================================


@router.websocket("/pixel-events/stream")
async def pixel_event_stream(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """Stream pixel events in real-time via WebSocket.

    WHAT:
        Authenticated WebSocket endpoint that streams pixel events to
        dashboard viewers. On connect, sends last 30 events as initial
        payload, then pushes new events as they arrive via broadcast.

    WHY:
        The attribution page "Live Feed" panel needs instant event visibility
        without polling. Merchants can watch customer activity in real-time.

    PROTOCOL:
        1. Client connects with ?token=<clerk_jwt>
        2. Server authenticates and sends "connected" message with initial events
        3. New pixel events are pushed as "pixel_event" messages (via broadcast)
        4. Client sends {"type": "ping"} every 30s; server replies {"type": "pong"}
        5. Server closes with 4001/4003 on auth failure

    REFERENCES:
        - backend/app/routers/agents.py (agent WebSocket endpoint pattern)
        - backend/app/services/pixel_websocket_manager.py (connection manager)
        - ui/hooks/usePixelStream.js (frontend consumer)
    """
    # 1. Authenticate
    user, error = await authenticate_websocket(websocket, db)
    if error or not user:
        # Accept first so we can send close reason
        await websocket.accept()
        await websocket.close(code=4001, reason=error or "Authentication failed")
        return

    workspace_id = user.workspace_id
    if not workspace_id:
        await websocket.accept()
        await websocket.close(code=4003, reason="No workspace assigned")
        return

    # 2. Register connection (also accepts the WebSocket)
    await pixel_ws_manager.connect(websocket, workspace_id)

    # 3. Send initial batch of recent events so feed isn't empty on page load
    try:
        recent_events = (
            db.query(PixelEvent)
            .filter(PixelEvent.workspace_id == workspace_id)
            .order_by(desc(PixelEvent.created_at))
            .limit(30)
            .all()
        )

        initial_payload = [
            {
                "type": "pixel_event",
                "id": str(evt.id),
                "event_type": evt.event_type,
                "visitor_id": evt.visitor_id,
                "url": evt.url,
                "utm_source": evt.utm_source,
                "utm_medium": evt.utm_medium,
                "utm_campaign": evt.utm_campaign,
                "created_at": evt.created_at.isoformat() if evt.created_at else None,
            }
            for evt in recent_events
        ]

        await websocket.send_json({
            "type": "initial_batch",
            "events": initial_payload,
        })
    except Exception as e:
        logger.error(f"[PIXEL_WS] Failed to send initial batch: {e}")

    # 4. Keep connection alive — listen for pings and handle disconnects
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info(f"[PIXEL_WS] Client disconnected from workspace {workspace_id}")
    except Exception as e:
        logger.warning(f"[PIXEL_WS] Connection error: {e}")
    finally:
        await pixel_ws_manager.disconnect(websocket)


@router.get("/pixel-events/health")
async def pixel_health():
    """Health check endpoint for pixel service.

    WHAT: Simple health check that doesn't require auth
    WHY: Shopify pixel needs to verify endpoint is available
    """
    return {"status": "healthy", "service": "pixel-events"}
