"""Attribution and pixel health endpoints.

WHAT:
    Provides API endpoints for:
    - Pixel health and status monitoring
    - Pixel reinstallation
    - Attribution summary and analytics
    - Attribution comparison with ad platforms

WHY:
    Users need visibility into their pixel's health to trust attribution data.
    They also need to see attribution breakdowns and compare with platform data.

REFERENCES:
    - docs/ATTRIBUTION_UX_COMPREHENSIVE_PLAN.md
    - docs/living-docs/ATTRIBUTION_ENGINE.md
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import (
    User, Connection, ProviderEnum, WorkspaceMember, RoleEnum,
    PixelEvent, CustomerJourney, Attribution, ShopifyOrder, Entity, LevelEnum
)
from ..services.pixel_activation_service import PixelActivationService
from ..security import decrypt_secret

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/workspaces",
    tags=["Attribution"],
)


# =============================================================================
# SCHEMAS
# =============================================================================

class EventCounts(BaseModel):
    """Event counts for the last 24 hours."""
    page_viewed: int = 0
    product_viewed: int = 0
    product_added_to_cart: int = 0
    checkout_started: int = 0
    checkout_completed: int = 0


class PixelHealthResponse(BaseModel):
    """Response for pixel health endpoint.

    WHAT: Comprehensive pixel status and health information
    WHY: Users need to see if their pixel is working and capturing events
    """
    status: str = Field(..., description="Pixel status: active, inactive, not_installed, error")
    pixel_id: Optional[str] = Field(None, description="Shopify Web Pixel ID")
    shop_domain: Optional[str] = Field(None, description="Connected Shopify store domain")
    installed_at: Optional[datetime] = Field(None, description="When pixel was installed")
    last_event_at: Optional[datetime] = Field(None, description="Timestamp of most recent event")
    events_24h: EventCounts = Field(default_factory=EventCounts, description="Event counts last 24h")
    total_events_24h: int = Field(0, description="Total events in last 24 hours")
    unique_visitors_24h: int = Field(0, description="Unique visitors in last 24 hours")
    health_score: int = Field(0, description="Health score 0-100")
    issues: List[str] = Field(default_factory=list, description="List of detected issues")


class PixelReinstallResponse(BaseModel):
    """Response for pixel reinstall endpoint."""
    success: bool
    old_pixel_id: Optional[str] = None
    new_pixel_id: Optional[str] = None
    message: str


class AttributionByProvider(BaseModel):
    """Revenue attribution breakdown by provider."""
    provider: str
    revenue: float
    orders: int
    percentage: float
    avg_order_value: float


class ConfidenceBreakdown(BaseModel):
    """Attribution breakdown by confidence level."""
    confidence: str
    revenue: float
    orders: int
    percentage: float


class AttributionSummaryResponse(BaseModel):
    """Response for attribution summary endpoint.

    WHAT: Revenue attribution breakdown by channel
    WHY: Users need to see which channels are driving their revenue
    """
    total_attributed_revenue: float
    total_orders: int
    attribution_rate: float = Field(..., description="Percentage of orders with attribution")
    by_provider: List[AttributionByProvider]
    by_confidence: List[ConfidenceBreakdown]
    period_start: datetime
    period_end: datetime


class AttributedCampaign(BaseModel):
    """A campaign with attributed revenue."""
    entity_id: Optional[str] = None
    campaign_name: str
    provider: str
    attributed_revenue: float
    attributed_orders: int
    avg_order_value: float
    match_type: str
    confidence: str


class AttributionCampaignsResponse(BaseModel):
    """Response for attributed campaigns endpoint."""
    campaigns: List[AttributedCampaign]
    total_campaigns: int


class AttributionFeedItem(BaseModel):
    """A single item in the attribution feed."""
    id: str
    attributed_at: datetime
    order_id: Optional[str] = None
    revenue: float
    currency: str = "USD"
    provider: str
    campaign_name: Optional[str] = None
    match_type: str
    confidence: str


class AttributionFeedResponse(BaseModel):
    """Response for attribution feed endpoint.

    WHAT: Recent attributions for live feed display
    WHY: Users want to see attributions as they happen (WOW factor)
    """
    items: List[AttributionFeedItem]
    total_count: int


class CampaignAttributionWarning(BaseModel):
    """Attribution warning for a campaign."""
    campaign_id: str
    campaign_name: str
    provider: str
    warning_type: str  # 'no_attribution', 'no_utm', 'low_confidence'
    message: str
    spend: Optional[float] = None
    attributed_revenue: Optional[float] = None
    attributed_orders: int = 0


class CampaignWarningsResponse(BaseModel):
    """Response for campaign warnings endpoint.

    WHAT: Campaigns that have attribution issues
    WHY: Users need to know which campaigns aren't being tracked properly
    """
    warnings: List[CampaignAttributionWarning]
    campaigns_with_warnings: int
    total_campaigns: int


# =============================================================================
# HELPERS
# =============================================================================

def _require_workspace_permission(
    db: Session,
    user: User,
    workspace_id: UUID,
    roles=(RoleEnum.owner, RoleEnum.admin, RoleEnum.viewer),
):
    """Check if user has permission to access workspace.

    WHAT: Validates user membership and role for a workspace
    WHY: Security - ensure users can only access their own workspace data

    Args:
        db: Database session
        user: Current authenticated user
        workspace_id: Workspace to check access for
        roles: Allowed roles (default: all roles can read)

    Raises:
        HTTPException 403 if user doesn't have access
    """
    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this workspace"
        )
    if membership.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this action"
        )
    return membership


def _calculate_health_score(
    total_events: int,
    checkout_completed: int,
    last_event_time: Optional[datetime],
    issues: List[str],
) -> int:
    """Calculate pixel health score (0-100).

    WHAT: Determines overall pixel health based on event activity
    WHY: Users need a quick indicator of whether their pixel is working

    Scoring:
    - Base: 50 points
    - Events in 24h: +25 points if >100 events, +15 if >10, +5 if any
    - Checkout completions: +15 points if any
    - Recent activity: +10 points if event in last hour
    - Issues: -10 points per issue

    Args:
        total_events: Total events in last 24 hours
        checkout_completed: Checkout completion events
        last_event_time: Time of most recent event
        issues: List of detected issues

    Returns:
        Health score 0-100
    """
    score = 50  # Base score

    # Event volume scoring
    if total_events >= 100:
        score += 25
    elif total_events >= 10:
        score += 15
    elif total_events > 0:
        score += 5

    # Checkout completions indicate full funnel tracking
    if checkout_completed > 0:
        score += 15

    # Recent activity bonus
    if last_event_time:
        time_since_event = datetime.now(timezone.utc) - last_event_time
        if time_since_event < timedelta(hours=1):
            score += 10
        elif time_since_event < timedelta(hours=6):
            score += 5

    # Issue penalties
    score -= len(issues) * 10

    return max(0, min(100, score))


# =============================================================================
# PIXEL HEALTH ENDPOINTS
# =============================================================================

@router.get(
    "/{workspace_id}/pixel/health",
    response_model=PixelHealthResponse,
    summary="Get pixel health status",
    description="""
    Get the health status and event statistics for the workspace's Shopify pixel.

    Returns:
    - Pixel status (active/inactive/not_installed)
    - Event counts for the last 24 hours
    - Health score (0-100)
    - Any detected issues
    """
)
async def get_pixel_health(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get pixel health and event statistics.

    WHAT: Returns comprehensive pixel health information
    WHY: Users need visibility into whether their pixel is working

    Args:
        workspace_id: The workspace UUID
        db: Database session
        current_user: Authenticated user

    Returns:
        PixelHealthResponse with status, events, and health score
    """
    _require_workspace_permission(db, current_user, workspace_id)

    # Find Shopify connection for this workspace
    shopify_connection = (
        db.query(Connection)
        .filter(
            Connection.workspace_id == workspace_id,
            Connection.provider == ProviderEnum.shopify,
            Connection.status == "active",
        )
        .first()
    )

    if not shopify_connection:
        return PixelHealthResponse(
            status="not_installed",
            health_score=0,
            issues=["No Shopify connection found. Connect your Shopify store to enable tracking."],
        )

    # Check if pixel is installed
    pixel_id = shopify_connection.web_pixel_id

    if not pixel_id:
        return PixelHealthResponse(
            status="not_installed",
            shop_domain=shopify_connection.external_account_id,
            health_score=0,
            issues=["Pixel not installed. The pixel should auto-install during Shopify connection."],
        )

    # Get event statistics for last 24 hours
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    # Count events by type
    event_counts = (
        db.query(
            PixelEvent.event_type,
            func.count(PixelEvent.id).label("count"),
        )
        .filter(
            PixelEvent.workspace_id == workspace_id,
            PixelEvent.created_at >= day_ago,
        )
        .group_by(PixelEvent.event_type)
        .all()
    )

    # Build event counts dict
    counts_dict = {row.event_type: row.count for row in event_counts}
    events = EventCounts(
        page_viewed=counts_dict.get("page_viewed", 0),
        product_viewed=counts_dict.get("product_viewed", 0),
        product_added_to_cart=counts_dict.get("product_added_to_cart", 0),
        checkout_started=counts_dict.get("checkout_started", 0),
        checkout_completed=counts_dict.get("checkout_completed", 0),
    )

    total_events = sum(counts_dict.values()) if counts_dict else 0

    # Get unique visitors
    unique_visitors = (
        db.query(func.count(func.distinct(PixelEvent.visitor_id)))
        .filter(
            PixelEvent.workspace_id == workspace_id,
            PixelEvent.created_at >= day_ago,
        )
        .scalar()
    ) or 0

    # Get last event time
    last_event = (
        db.query(func.max(PixelEvent.created_at))
        .filter(PixelEvent.workspace_id == workspace_id)
        .scalar()
    )

    # Detect issues
    issues = []

    if total_events == 0:
        issues.append("No events received in the last 24 hours")

    if events.page_viewed == 0 and total_events > 0:
        issues.append("No page_viewed events - pixel may not be firing on all pages")

    if events.checkout_completed == 0 and events.checkout_started > 0:
        issues.append("Checkout started but no completions tracked - check checkout pixel")

    if last_event:
        hours_since_event = (now - last_event).total_seconds() / 3600
        if hours_since_event > 6:
            issues.append(f"No events in {int(hours_since_event)} hours - pixel may be inactive")

    # Calculate health score
    health_score = _calculate_health_score(
        total_events=total_events,
        checkout_completed=events.checkout_completed,
        last_event_time=last_event,
        issues=issues,
    )

    # Determine status
    if total_events > 0 and len(issues) <= 1:
        pixel_status = "active"
    elif total_events > 0:
        pixel_status = "degraded"
    else:
        pixel_status = "inactive"

    return PixelHealthResponse(
        status=pixel_status,
        pixel_id=pixel_id,
        shop_domain=shopify_connection.external_account_id,
        installed_at=shopify_connection.connected_at,
        last_event_at=last_event,
        events_24h=events,
        total_events_24h=total_events,
        unique_visitors_24h=unique_visitors,
        health_score=health_score,
        issues=issues,
    )


@router.post(
    "/{workspace_id}/pixel/reinstall",
    response_model=PixelReinstallResponse,
    summary="Reinstall the pixel",
    description="""
    Delete the existing pixel and install a fresh one.
    Use this if the pixel is not working correctly.
    """
)
async def reinstall_pixel(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reinstall the Shopify web pixel.

    WHAT: Deletes existing pixel and creates a new one
    WHY: Sometimes pixels need to be reset if they're not working

    Args:
        workspace_id: The workspace UUID
        db: Database session
        current_user: Authenticated user

    Returns:
        PixelReinstallResponse with old/new pixel IDs
    """
    # Only owner/admin can reinstall
    _require_workspace_permission(
        db, current_user, workspace_id,
        roles=(RoleEnum.owner, RoleEnum.admin)
    )

    # Find Shopify connection
    shopify_connection = (
        db.query(Connection)
        .filter(
            Connection.workspace_id == workspace_id,
            Connection.provider == ProviderEnum.shopify,
            Connection.status == "active",
        )
        .first()
    )

    if not shopify_connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Shopify connection found for this workspace"
        )

    # Get access token
    if not shopify_connection.token_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shopify connection has no token - reconnect required"
        )

    # Decrypt access token
    if not shopify_connection.token or not shopify_connection.token.access_token_enc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shopify token not found - reconnect required"
        )

    label = f"{shopify_connection.provider.value}:{shopify_connection.external_account_id}"
    try:
        access_token = decrypt_secret(shopify_connection.token.access_token_enc, context=f"{label}:access")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not decrypt Shopify token - reconnect required"
        )

    shop_domain = shopify_connection.external_account_id
    old_pixel_id = shopify_connection.web_pixel_id

    service = PixelActivationService()

    # Delete existing pixel if present
    if old_pixel_id:
        logger.info(f"[PIXEL_REINSTALL] Deleting old pixel {old_pixel_id}")
        await service.delete_pixel(shop_domain, access_token, old_pixel_id)

    # Create new pixel
    logger.info(f"[PIXEL_REINSTALL] Creating new pixel for {shop_domain}")
    new_pixel_id = await service.activate_pixel(
        shop_domain=shop_domain,
        access_token=access_token,
        workspace_id=str(workspace_id),
    )

    if new_pixel_id:
        # Update connection with new pixel ID
        shopify_connection.web_pixel_id = new_pixel_id
        db.commit()

        logger.info(f"[PIXEL_REINSTALL] Success - old: {old_pixel_id}, new: {new_pixel_id}")

        return PixelReinstallResponse(
            success=True,
            old_pixel_id=old_pixel_id,
            new_pixel_id=new_pixel_id,
            message="Pixel reinstalled successfully",
        )
    else:
        logger.error(f"[PIXEL_REINSTALL] Failed to create new pixel for {shop_domain}")

        return PixelReinstallResponse(
            success=False,
            old_pixel_id=old_pixel_id,
            new_pixel_id=None,
            message="Failed to create new pixel. Check Shopify connection.",
        )


# =============================================================================
# ATTRIBUTION ENDPOINTS
# =============================================================================

@router.get(
    "/{workspace_id}/attribution/summary",
    response_model=AttributionSummaryResponse,
    summary="Get attribution summary",
    description="""
    Get revenue attribution breakdown by channel/provider.

    Returns:
    - Total attributed revenue
    - Breakdown by provider (Meta, Google, Direct, etc.)
    - Breakdown by confidence level
    - Attribution rate (% of orders attributed)
    """
)
async def get_attribution_summary(
    workspace_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get attribution summary by channel.

    WHAT: Returns revenue attribution breakdown
    WHY: Users need to see which channels drive their sales

    Args:
        workspace_id: The workspace UUID
        days: Number of days to analyze (default 30)
        db: Database session
        current_user: Authenticated user

    Returns:
        AttributionSummaryResponse with breakdowns
    """
    _require_workspace_permission(db, current_user, workspace_id)

    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # Get attributions with orders for this workspace
    attributions = (
        db.query(Attribution)
        .join(ShopifyOrder, Attribution.shopify_order_id == ShopifyOrder.id)
        .filter(
            Attribution.workspace_id == workspace_id,
            Attribution.attributed_at >= period_start,
        )
        .all()
    )

    # Get total orders for the period
    total_orders = (
        db.query(func.count(ShopifyOrder.id))
        .filter(
            ShopifyOrder.created_at >= period_start,
        )
        .scalar()
    ) or 0

    # Calculate breakdowns
    by_provider = {}
    by_confidence = {}
    total_revenue = 0.0

    for attr in attributions:
        revenue = float(attr.attributed_revenue or 0)
        total_revenue += revenue

        # By provider
        provider = attr.provider or "unknown"
        if provider not in by_provider:
            by_provider[provider] = {"revenue": 0.0, "orders": 0}
        by_provider[provider]["revenue"] += revenue
        by_provider[provider]["orders"] += 1

        # By confidence
        confidence = attr.confidence or "unknown"
        if confidence not in by_confidence:
            by_confidence[confidence] = {"revenue": 0.0, "orders": 0}
        by_confidence[confidence]["revenue"] += revenue
        by_confidence[confidence]["orders"] += 1

    # Build response
    provider_list = []
    for provider, data in sorted(by_provider.items(), key=lambda x: x[1]["revenue"], reverse=True):
        percentage = (data["revenue"] / total_revenue * 100) if total_revenue > 0 else 0
        avg_order = (data["revenue"] / data["orders"]) if data["orders"] > 0 else 0
        provider_list.append(AttributionByProvider(
            provider=provider,
            revenue=round(data["revenue"], 2),
            orders=data["orders"],
            percentage=round(percentage, 1),
            avg_order_value=round(avg_order, 2),
        ))

    confidence_list = []
    for confidence, data in by_confidence.items():
        percentage = (data["revenue"] / total_revenue * 100) if total_revenue > 0 else 0
        confidence_list.append(ConfidenceBreakdown(
            confidence=confidence,
            revenue=round(data["revenue"], 2),
            orders=data["orders"],
            percentage=round(percentage, 1),
        ))

    # Sort confidence by custom order
    confidence_order = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
    confidence_list.sort(key=lambda x: confidence_order.get(x.confidence, 99))

    attributed_orders = len(attributions)
    attribution_rate = (attributed_orders / total_orders * 100) if total_orders > 0 else 0

    return AttributionSummaryResponse(
        total_attributed_revenue=round(total_revenue, 2),
        total_orders=attributed_orders,
        attribution_rate=round(attribution_rate, 1),
        by_provider=provider_list,
        by_confidence=confidence_list,
        period_start=period_start,
        period_end=now,
    )


@router.get(
    "/{workspace_id}/attribution/campaigns",
    response_model=AttributionCampaignsResponse,
    summary="Get attributed campaigns",
    description="""
    Get top campaigns by attributed revenue.

    Returns list of campaigns with:
    - Attributed revenue
    - Number of attributed orders
    - Match type (utm_campaign, gclid, fbclid, etc.)
    - Confidence level
    """
)
async def get_attributed_campaigns(
    workspace_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(20, ge=1, le=100, description="Number of campaigns to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get top campaigns by attributed revenue.

    WHAT: Returns campaigns ranked by attributed revenue
    WHY: Users need to see which campaigns are performing best

    Args:
        workspace_id: The workspace UUID
        days: Number of days to analyze (default 30)
        limit: Max campaigns to return (default 20)
        db: Database session
        current_user: Authenticated user

    Returns:
        AttributionCampaignsResponse with top campaigns
    """
    _require_workspace_permission(db, current_user, workspace_id)

    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # Get attributions with campaign info
    attributions = (
        db.query(Attribution)
        .filter(
            Attribution.workspace_id == workspace_id,
            Attribution.attributed_at >= period_start,
        )
        .all()
    )

    # Group by campaign name
    campaigns = {}
    for attr in attributions:
        # Get campaign name from entity relationship (entity_id can be None for direct/organic)
        if attr.entity:
            campaign_name = attr.entity.name
        elif attr.provider in ("direct", "organic"):
            campaign_name = f"{attr.provider.capitalize()} Traffic"
        else:
            campaign_name = "Unknown Campaign"
        if campaign_name not in campaigns:
            campaigns[campaign_name] = {
                "entity_id": str(attr.entity_id) if attr.entity_id else None,
                "provider": attr.provider or "unknown",
                "revenue": 0.0,
                "orders": 0,
                "match_type": attr.match_type or "unknown",
                "confidence": attr.confidence or "unknown",
            }
        campaigns[campaign_name]["revenue"] += float(attr.attributed_revenue or 0)
        campaigns[campaign_name]["orders"] += 1

    # Build response list
    campaign_list = []
    for name, data in campaigns.items():
        avg_order = (data["revenue"] / data["orders"]) if data["orders"] > 0 else 0
        campaign_list.append(AttributedCampaign(
            entity_id=data["entity_id"],
            campaign_name=name,
            provider=data["provider"],
            attributed_revenue=round(data["revenue"], 2),
            attributed_orders=data["orders"],
            avg_order_value=round(avg_order, 2),
            match_type=data["match_type"],
            confidence=data["confidence"],
        ))

    # Sort by revenue descending and limit
    campaign_list.sort(key=lambda x: x.attributed_revenue, reverse=True)
    campaign_list = campaign_list[:limit]

    return AttributionCampaignsResponse(
        campaigns=campaign_list,
        total_campaigns=len(campaigns),
    )


@router.get(
    "/{workspace_id}/attribution/feed",
    response_model=AttributionFeedResponse,
    summary="Get recent attribution feed",
    description="""
    Get recent attributions for live feed display.

    Returns the most recent attributions with:
    - Order revenue and timestamp
    - Campaign name and provider
    - Match type and confidence level
    """
)
async def get_attribution_feed(
    workspace_id: UUID,
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent attributions for live feed.

    WHAT: Returns recent attributions in chronological order
    WHY: Users want real-time visibility into attribution activity (WOW factor)

    Args:
        workspace_id: The workspace UUID
        limit: Max items to return (default 20)
        db: Database session
        current_user: Authenticated user

    Returns:
        AttributionFeedResponse with recent attribution items
    """
    _require_workspace_permission(db, current_user, workspace_id)

    # Get recent attributions with order info
    attributions = (
        db.query(Attribution)
        .join(ShopifyOrder, Attribution.shopify_order_id == ShopifyOrder.id)
        .filter(Attribution.workspace_id == workspace_id)
        .order_by(Attribution.attributed_at.desc())
        .limit(limit)
        .all()
    )

    # Build feed items
    items = []
    for attr in attributions:
        # Get order info
        order = db.query(ShopifyOrder).filter(ShopifyOrder.id == attr.shopify_order_id).first()
        currency = order.currency if order else "USD"
        order_number = order.order_number if order else None

        # Get campaign name from entity relationship (entity_id can be None for direct/organic)
        campaign_name = None
        if attr.entity:
            campaign_name = attr.entity.name
        elif attr.provider in ("direct", "organic"):
            campaign_name = f"{attr.provider.capitalize()} Traffic"
        else:
            campaign_name = "Unknown Source"

        items.append(AttributionFeedItem(
            id=str(attr.id),
            attributed_at=attr.attributed_at,
            order_id=str(order_number) if order_number else None,
            revenue=float(attr.attributed_revenue or 0),
            currency=currency,
            provider=attr.provider or "unknown",
            campaign_name=campaign_name,
            match_type=attr.match_type or "unknown",
            confidence=attr.confidence or "unknown",
        ))

    # Get total count
    total_count = (
        db.query(func.count(Attribution.id))
        .filter(Attribution.workspace_id == workspace_id)
        .scalar()
    ) or 0

    return AttributionFeedResponse(
        items=items,
        total_count=total_count,
    )


@router.get(
    "/{workspace_id}/attribution/warnings",
    response_model=CampaignWarningsResponse,
    summary="Get campaign attribution warnings",
    description="""
    Get campaigns that have attribution issues.

    Returns campaigns with:
    - No attributed orders (despite having spend)
    - Low confidence attributions
    - Missing UTM tracking
    """
)
async def get_campaign_warnings(
    workspace_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get campaigns with attribution warnings.

    WHAT: Returns campaigns that have attribution issues
    WHY: Users need to know which campaigns aren't being tracked properly

    Args:
        workspace_id: The workspace UUID
        days: Number of days to analyze (default 30)
        db: Database session
        current_user: Authenticated user

    Returns:
        CampaignWarningsResponse with warning details
    """
    _require_workspace_permission(db, current_user, workspace_id)

    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # Get all campaigns for this workspace
    campaigns = (
        db.query(Entity)
        .filter(
            Entity.workspace_id == workspace_id,
            Entity.level == LevelEnum.campaign,
        )
        .all()
    )

    # Get attributions grouped by campaign
    attributions_by_campaign = {}
    attributions = (
        db.query(Attribution)
        .filter(
            Attribution.workspace_id == workspace_id,
            Attribution.attributed_at >= period_start,
            Attribution.entity_id.isnot(None),
        )
        .all()
    )

    for attr in attributions:
        entity_id = str(attr.entity_id)
        if entity_id not in attributions_by_campaign:
            attributions_by_campaign[entity_id] = {
                "orders": 0,
                "revenue": 0.0,
                "match_types": set(),
                "confidences": set(),
            }
        attributions_by_campaign[entity_id]["orders"] += 1
        attributions_by_campaign[entity_id]["revenue"] += float(attr.attributed_revenue or 0)
        if attr.match_type:
            attributions_by_campaign[entity_id]["match_types"].add(attr.match_type)
        if attr.confidence:
            attributions_by_campaign[entity_id]["confidences"].add(attr.confidence)

    # Get proactive UTM status for each campaign by checking ad tracking_params
    # WHY: Detect missing UTM params BEFORE orders come in
    # REFERENCES: docs/living-docs/FRONTEND_REFACTOR_PLAN.md
    campaign_utm_status = {}
    for campaign in campaigns:
        # Get all adset IDs under this campaign
        adset_ids = (
            db.query(Entity.id)
            .filter(
                Entity.workspace_id == workspace_id,
                Entity.level == LevelEnum.adset,
                Entity.parent_id == campaign.id,
            )
            .all()
        )
        adset_id_list = [a[0] for a in adset_ids]

        # Get all ads under those adsets
        ads_with_tracking = []
        if adset_id_list:
            ads_with_tracking = (
                db.query(Entity)
                .filter(
                    Entity.workspace_id == workspace_id,
                    Entity.level == LevelEnum.ad,
                    Entity.parent_id.in_(adset_id_list),
                )
                .all()
            )

        # Check if any ads have UTM tracking configured
        has_utm = False
        for ad in ads_with_tracking:
            if ad.tracking_params:
                # Check for utm_source or utm_campaign (minimum required)
                if ad.tracking_params.get("has_utm_source") or ad.tracking_params.get("has_utm_campaign"):
                    has_utm = True
                    break
                # For Google, also check gclid
                if ad.tracking_params.get("has_gclid"):
                    has_utm = True
                    break

        campaign_utm_status[str(campaign.id)] = has_utm

    # Analyze each campaign for warnings
    warnings = []

    for campaign in campaigns:
        campaign_id = str(campaign.id)
        campaign_attrs = attributions_by_campaign.get(campaign_id)
        has_utm_configured = campaign_utm_status.get(campaign_id, False)

        # Get campaign spend (from metrics if available)
        # For now, we'll flag campaigns without any attributions
        spend = 0.0  # Would need to join with metrics table

        # Check for proactive UTM warning FIRST (before orders come in)
        # WHY: This is the key value - warn users before they waste ad spend
        if not has_utm_configured and not campaign_attrs:
            warnings.append(CampaignAttributionWarning(
                campaign_id=campaign_id,
                campaign_name=campaign.name or "Unknown",
                provider=campaign.connection.provider.value if campaign.connection and campaign.connection.provider else "unknown",
                warning_type="no_utm",
                message="No UTM parameters configured. Add UTM tracking to attribute conversions.",
                spend=spend,
                attributed_revenue=0.0,
                attributed_orders=0,
            ))
        elif not campaign_attrs:
            # No attributed orders at all (but UTM might be configured)
            warnings.append(CampaignAttributionWarning(
                campaign_id=campaign_id,
                campaign_name=campaign.name or "Unknown",
                provider=campaign.connection.provider.value if campaign.connection and campaign.connection.provider else "unknown",
                warning_type="no_attribution",
                message="No attributed orders yet. UTM tracking is configured - waiting for conversions.",
                spend=spend,
                attributed_revenue=0.0,
                attributed_orders=0,
            ))
        elif "low" in campaign_attrs.get("confidences", set()) and "high" not in campaign_attrs.get("confidences", set()):
            # Only low confidence attributions
            warnings.append(CampaignAttributionWarning(
                campaign_id=campaign_id,
                campaign_name=campaign.name or "Unknown",
                provider=campaign.connection.provider.value if campaign.connection and campaign.connection.provider else "unknown",
                warning_type="low_confidence",
                message="Only low-confidence attributions. Add UTM parameters for better tracking.",
                spend=spend,
                attributed_revenue=campaign_attrs["revenue"],
                attributed_orders=campaign_attrs["orders"],
            ))
        elif not campaign_attrs.get("match_types", set()).intersection({"utm_campaign", "gclid"}):
            # No UTM or gclid matches (only fbclid, referrer, etc.)
            warnings.append(CampaignAttributionWarning(
                campaign_id=campaign_id,
                campaign_name=campaign.name or "Unknown",
                provider=campaign.connection.provider.value if campaign.connection and campaign.connection.provider else "unknown",
                warning_type="no_utm",
                message="No UTM tracking detected. Add UTM parameters for campaign-level attribution.",
                spend=spend,
                attributed_revenue=campaign_attrs["revenue"],
                attributed_orders=campaign_attrs["orders"],
            ))

    return CampaignWarningsResponse(
        warnings=warnings,
        campaigns_with_warnings=len(warnings),
        total_campaigns=len(campaigns),
    )


# =============================================================================
# META CAPI TEST ENDPOINT
# =============================================================================

class MetaCAPITestRequest(BaseModel):
    """Request body for testing Meta CAPI."""
    test_event_code: str = Field(
        description="Test event code from Meta Events Manager (Test Events tab)"
    )
    value: float = Field(default=99.99, description="Test purchase value")
    currency: str = Field(default="USD", description="Currency code")


class MetaCAPITestResponse(BaseModel):
    """Response from Meta CAPI test."""
    success: bool
    message: str
    pixel_id: Optional[str] = None
    events_received: Optional[int] = None
    error: Optional[str] = None


@router.post(
    "/{workspace_id}/meta-capi/test",
    response_model=MetaCAPITestResponse,
    summary="Test Meta CAPI integration",
    description="""
    Send a test purchase event to Meta Conversions API.

    To use this:
    1. Go to Meta Events Manager → Your Pixel → Test Events
    2. Copy the "Test event code" (looks like TEST12345)
    3. Call this endpoint with that code
    4. Watch the event appear in Meta Events Manager

    The test event won't affect your actual data or ad optimization.
    """
)
async def test_meta_capi(
    workspace_id: UUID,
    payload: MetaCAPITestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test Meta CAPI by sending a test purchase event.

    WHAT: Sends a test purchase event to verify CAPI is working
    WHY: Users need to verify their pixel configuration before relying on it

    Args:
        workspace_id: The workspace UUID
        payload: Test event code and optional purchase details
        db: Database session
        current_user: Authenticated user

    Returns:
        MetaCAPITestResponse with success status and details
    """
    from decimal import Decimal
    from app.services.meta_capi_service import MetaCAPIService, MetaCAPIError
    from app.services.token_service import get_decrypted_token

    _require_workspace_permission(db, current_user, workspace_id)

    # Find Meta connection (prefer one with pixel configured)
    meta_connection = db.query(Connection).filter(
        Connection.workspace_id == workspace_id,
        Connection.provider == ProviderEnum.meta,
        Connection.status == "active",
        Connection.meta_pixel_id.isnot(None),
    ).first()

    # Fallback to any Meta connection if none have pixel
    if not meta_connection:
        meta_connection = db.query(Connection).filter(
            Connection.workspace_id == workspace_id,
            Connection.provider == ProviderEnum.meta,
            Connection.status == "active",
        ).first()

    if not meta_connection:
        return MetaCAPITestResponse(
            success=False,
            message="No active Meta connection found",
            error="Connect a Meta ad account first in Settings",
        )

    # Get pixel ID
    pixel_id = meta_connection.meta_pixel_id
    if not pixel_id:
        return MetaCAPITestResponse(
            success=False,
            message="No pixel configured for this Meta connection",
            error="Configure a CAPI pixel in Settings → Meta connection → Configure",
        )

    # Get access token
    access_token = get_decrypted_token(db, meta_connection.id, "access")
    if not access_token:
        return MetaCAPITestResponse(
            success=False,
            message="No valid access token",
            error="Please reconnect your Meta account",
        )

    # Send test event
    try:
        import uuid
        service = MetaCAPIService(pixel_id=pixel_id, access_token=access_token)
        result = await service.send_purchase_event(
            event_id=f"test_{uuid.uuid4().hex[:8]}",
            value=Decimal(str(payload.value)),
            currency=payload.currency,
            email="test@example.com",
            order_id=f"TEST-{uuid.uuid4().hex[:8].upper()}",
            test_event_code=payload.test_event_code,
        )

        events_received = result.get("events_received", 0) if result else 0

        if events_received > 0:
            return MetaCAPITestResponse(
                success=True,
                message=f"Test event sent successfully! Check Meta Events Manager.",
                pixel_id=pixel_id,
                events_received=events_received,
            )
        else:
            return MetaCAPITestResponse(
                success=False,
                message="Event sent but Meta reported 0 events received",
                pixel_id=pixel_id,
                events_received=0,
                error=str(result) if result else "No response from Meta",
            )

    except MetaCAPIError as e:
        logger.error(f"[META_CAPI_TEST] Failed: {e}")
        return MetaCAPITestResponse(
            success=False,
            message="Failed to send test event",
            pixel_id=pixel_id,
            error=str(e),
        )
    except Exception as e:
        logger.exception(f"[META_CAPI_TEST] Unexpected error: {e}")
        return MetaCAPITestResponse(
            success=False,
            message="Unexpected error",
            error=str(e),
        )
