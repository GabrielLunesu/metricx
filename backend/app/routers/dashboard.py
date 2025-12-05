"""
Unified Dashboard Router
========================

WHAT: Single endpoint returning all dashboard data in one request
WHY: Reduces 8+ API calls to 1, dramatically improving dashboard load time

BEFORE (8+ requests):
1. GET /auth/me
2. GET /workspaces/{id}/status
3. GET /workspaces/{id}/dashboard/kpis
4. POST /workspaces/{id}/kpis (MoneyPulseChart - redundant!)
5. POST /qa/insights x2 (AI calls - slow!)
6. GET /workspaces/{id}/attribution/summary
7. GET /workspaces/{id}/attribution/feed
8. GET /entity-performance (TopCreative)
9. GET /entity-performance (UnitEconomicsTable)

AFTER (1 request):
1. GET /workspaces/{id}/dashboard/unified

AI insights are NOT included - they should be lazy loaded separately.

REFERENCES:
- docs/PERFORMANCE_INVESTIGATION.md
- app/routers/dashboard_kpis.py (KPI logic)
- app/routers/attribution.py (Attribution logic)
- app/routers/entity_performance.py (Entity logic)
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.models import (
    Connection, ShopifyOrder, Attribution, MetricFact, Entity,
    ProviderEnum, User, LevelEnum
)
from app.deps import get_current_user
from app.schemas import SparkPoint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["dashboard"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class KpiData(BaseModel):
    """Single KPI value."""
    key: str
    value: float
    prev: Optional[float] = None
    delta_pct: Optional[float] = None
    sparkline: Optional[List[SparkPoint]] = None


class TopCreativeItem(BaseModel):
    """Top performing ad/creative."""
    id: str
    name: str
    platform: str
    spend: float
    revenue: float
    roas: float


class SpendMixItem(BaseModel):
    """Spend by platform."""
    provider: str
    spend: float
    pct: float


class AttributionSummaryItem(BaseModel):
    """Attribution by channel."""
    channel: str
    revenue: float
    orders: int
    pct: float


class AttributionFeedItem(BaseModel):
    """Recent attribution event."""
    order_id: str
    revenue: float
    provider: str
    campaign_name: Optional[str]
    attributed_at: str


class UnifiedDashboardResponse(BaseModel):
    """Complete dashboard data in one response."""
    # KPIs
    kpis: List[KpiData]
    data_source: str  # "shopify" or "platform"
    has_shopify: bool
    connected_platforms: List[str]

    # Chart data (same as KPIs but guaranteed sparklines)
    chart_data: List[Dict[str, Any]]

    # Top creatives
    top_creatives: List[TopCreativeItem]

    # Spend mix by platform
    spend_mix: List[SpendMixItem]

    # Attribution (only if Shopify connected)
    attribution_summary: Optional[List[AttributionSummaryItem]] = None
    attribution_feed: Optional[List[AttributionFeedItem]] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_date_range(timeframe: str) -> tuple[datetime, datetime]:
    """Convert timeframe string to date range."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if timeframe == "today":
        return today_start, now
    elif timeframe == "yesterday":
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_start - timedelta(seconds=1)
        return yesterday_start, yesterday_end
    elif timeframe == "last_7_days":
        start = today_start - timedelta(days=6)
        return start, now
    elif timeframe == "last_30_days":
        start = today_start - timedelta(days=29)
        return start, now
    else:
        start = today_start - timedelta(days=6)
        return start, now


def _get_previous_period(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Get the previous period of the same length."""
    period_length = end - start
    prev_end = start - timedelta(seconds=1)
    prev_start = prev_end - period_length
    return prev_start, prev_end


def _calculate_delta_pct(current: float, previous: float) -> Optional[float]:
    """Calculate percentage change."""
    if previous is None or previous == 0:
        return None
    if current is None:
        return None
    return (current - previous) / previous


# =============================================================================
# DATA FETCHING FUNCTIONS
# =============================================================================

def _get_kpis_and_chart_data(
    db: Session,
    workspace_id: UUID,
    start: datetime,
    end: datetime,
    prev_start: datetime,
    prev_end: datetime,
    has_shopify: bool
) -> tuple[List[KpiData], List[Dict], str]:
    """Get KPIs and chart data in one query batch."""

    # Get entity IDs for this workspace
    entity_ids = (
        db.query(Entity.id)
        .filter(Entity.workspace_id == workspace_id)
        .scalar_subquery()
    )

    start_date = start.date() if isinstance(start, datetime) else start
    end_date = end.date() if isinstance(end, datetime) else end
    prev_start_date = prev_start.date() if isinstance(prev_start, datetime) else prev_start
    prev_end_date = prev_end.date() if isinstance(prev_end, datetime) else prev_end

    # Current period metrics
    current_metrics = db.query(
        func.coalesce(func.sum(MetricFact.spend), 0).label("spend"),
        func.coalesce(func.sum(MetricFact.revenue), 0).label("revenue"),
        func.coalesce(func.sum(MetricFact.conversions), 0).label("conversions")
    ).filter(
        MetricFact.entity_id.in_(entity_ids),
        func.date(MetricFact.event_date) >= start_date,
        func.date(MetricFact.event_date) <= end_date
    ).first()

    # Previous period metrics
    prev_metrics = db.query(
        func.coalesce(func.sum(MetricFact.spend), 0).label("spend"),
        func.coalesce(func.sum(MetricFact.revenue), 0).label("revenue"),
        func.coalesce(func.sum(MetricFact.conversions), 0).label("conversions")
    ).filter(
        MetricFact.entity_id.in_(entity_ids),
        func.date(MetricFact.event_date) >= prev_start_date,
        func.date(MetricFact.event_date) <= prev_end_date
    ).first()

    # Daily breakdown for sparklines
    daily_data = db.query(
        func.date(MetricFact.event_date).label("day"),
        func.coalesce(func.sum(MetricFact.spend), 0).label("spend"),
        func.coalesce(func.sum(MetricFact.revenue), 0).label("revenue")
    ).filter(
        MetricFact.entity_id.in_(entity_ids),
        func.date(MetricFact.event_date) >= start_date,
        func.date(MetricFact.event_date) <= end_date
    ).group_by(
        func.date(MetricFact.event_date)
    ).order_by(
        func.date(MetricFact.event_date)
    ).all()

    # Build sparklines
    revenue_sparkline = [SparkPoint(date=str(d.day), value=float(d.revenue or 0)) for d in daily_data]
    spend_sparkline = [SparkPoint(date=str(d.day), value=float(d.spend or 0)) for d in daily_data]

    # Calculate ROAS
    spend_current = float(current_metrics.spend or 0)
    revenue_current = float(current_metrics.revenue or 0)
    spend_prev = float(prev_metrics.spend or 0)
    revenue_prev = float(prev_metrics.revenue or 0)
    conversions_current = float(current_metrics.conversions or 0)
    conversions_prev = float(prev_metrics.conversions or 0)

    roas_current = revenue_current / spend_current if spend_current > 0 else 0
    roas_prev = revenue_prev / spend_prev if spend_prev > 0 else 0

    # ROAS sparkline
    roas_sparkline = []
    for d in daily_data:
        day_roas = float(d.revenue or 0) / float(d.spend) if float(d.spend) > 0 else 0
        roas_sparkline.append(SparkPoint(date=str(d.day), value=day_roas))

    kpis = [
        KpiData(
            key="revenue",
            value=revenue_current,
            prev=revenue_prev,
            delta_pct=_calculate_delta_pct(revenue_current, revenue_prev),
            sparkline=revenue_sparkline
        ),
        KpiData(
            key="roas",
            value=roas_current,
            prev=roas_prev,
            delta_pct=_calculate_delta_pct(roas_current, roas_prev),
            sparkline=roas_sparkline
        ),
        KpiData(
            key="spend",
            value=spend_current,
            prev=spend_prev,
            delta_pct=_calculate_delta_pct(spend_current, spend_prev),
            sparkline=spend_sparkline
        ),
        KpiData(
            key="conversions",
            value=conversions_current,
            prev=conversions_prev,
            delta_pct=_calculate_delta_pct(conversions_current, conversions_prev),
            sparkline=None
        ),
    ]

    # Chart data (merged for Recharts)
    chart_data = [
        {"date": str(d.day), "revenue": float(d.revenue or 0), "spend": float(d.spend or 0)}
        for d in daily_data
    ]

    data_source = "shopify" if has_shopify else "platform"

    return kpis, chart_data, data_source


def _get_top_creatives(
    db: Session,
    workspace_id: UUID,
    start: datetime,
    end: datetime,
    limit: int = 3
) -> List[TopCreativeItem]:
    """Get top performing ads by revenue."""

    start_date = start.date() if isinstance(start, datetime) else start
    end_date = end.date() if isinstance(end, datetime) else end

    # Get ads with their metrics
    results = db.query(
        Entity.id,
        Entity.name,
        Connection.provider,
        func.coalesce(func.sum(MetricFact.spend), 0).label("spend"),
        func.coalesce(func.sum(MetricFact.revenue), 0).label("revenue")
    ).join(
        MetricFact, MetricFact.entity_id == Entity.id
    ).outerjoin(
        Connection, Connection.id == Entity.connection_id
    ).filter(
        Entity.workspace_id == workspace_id,
        Entity.level == LevelEnum.ad,
        func.date(MetricFact.event_date) >= start_date,
        func.date(MetricFact.event_date) <= end_date
    ).group_by(
        Entity.id, Entity.name, Connection.provider
    ).order_by(
        desc("revenue")
    ).limit(limit).all()

    return [
        TopCreativeItem(
            id=str(r.id),
            name=r.name or "Unknown",
            platform=r.provider.value if r.provider else "unknown",
            spend=float(r.spend or 0),
            revenue=float(r.revenue or 0),
            roas=float(r.revenue or 0) / float(r.spend) if float(r.spend) > 0 else 0
        )
        for r in results
    ]


def _get_spend_mix(
    db: Session,
    workspace_id: UUID,
    start: datetime,
    end: datetime
) -> List[SpendMixItem]:
    """Get spend breakdown by platform."""

    start_date = start.date() if isinstance(start, datetime) else start
    end_date = end.date() if isinstance(end, datetime) else end

    entity_ids = (
        db.query(Entity.id)
        .filter(Entity.workspace_id == workspace_id)
        .scalar_subquery()
    )

    results = db.query(
        MetricFact.provider,
        func.coalesce(func.sum(MetricFact.spend), 0).label("spend")
    ).filter(
        MetricFact.entity_id.in_(entity_ids),
        func.date(MetricFact.event_date) >= start_date,
        func.date(MetricFact.event_date) <= end_date
    ).group_by(
        MetricFact.provider
    ).all()

    total_spend = sum(float(r.spend or 0) for r in results)

    return [
        SpendMixItem(
            provider=r.provider.value if r.provider else "unknown",
            spend=float(r.spend or 0),
            pct=(float(r.spend or 0) / total_spend * 100) if total_spend > 0 else 0
        )
        for r in results
    ]


def _get_attribution_data(
    db: Session,
    workspace_id: UUID,
    start: datetime,
    end: datetime
) -> tuple[List[AttributionSummaryItem], List[AttributionFeedItem]]:
    """Get attribution summary and feed.

    NOTE: Attribution model links to Entity via entity_id.
    Entity.name contains the campaign/ad name.
    """

    # Summary by provider
    summary_results = db.query(
        Attribution.provider,
        func.coalesce(func.sum(Attribution.attributed_revenue), 0).label("revenue"),
        func.count(Attribution.id).label("orders")
    ).filter(
        Attribution.workspace_id == workspace_id,
        Attribution.attributed_at >= start,
        Attribution.attributed_at <= end,
        Attribution.provider.notin_(["direct", "unknown", "organic"])
    ).group_by(
        Attribution.provider
    ).all()

    total_revenue = sum(float(r.revenue or 0) for r in summary_results)

    summary = [
        AttributionSummaryItem(
            channel=r.provider or "unknown",
            revenue=float(r.revenue or 0),
            orders=r.orders,
            pct=(float(r.revenue or 0) / total_revenue * 100) if total_revenue > 0 else 0
        )
        for r in summary_results
    ]

    # Recent feed - join with Entity to get campaign name
    feed_results = db.query(
        Attribution.shopify_order_id,
        Attribution.attributed_revenue,
        Attribution.provider,
        Entity.name.label("campaign_name"),
        Attribution.attributed_at
    ).outerjoin(
        Entity, Entity.id == Attribution.entity_id
    ).filter(
        Attribution.workspace_id == workspace_id,
        Attribution.attributed_at >= start,
        Attribution.provider.notin_(["direct", "unknown", "organic"])
    ).order_by(
        desc(Attribution.attributed_at)
    ).limit(10).all()

    feed = [
        AttributionFeedItem(
            order_id=str(r.shopify_order_id) if r.shopify_order_id else "unknown",
            revenue=float(r.attributed_revenue or 0),
            provider=r.provider or "unknown",
            campaign_name=r.campaign_name,
            attributed_at=r.attributed_at.isoformat() if r.attributed_at else ""
        )
        for r in feed_results
    ]

    return summary, feed


# =============================================================================
# MAIN ENDPOINT
# =============================================================================

@router.get(
    "/{workspace_id}/dashboard/unified",
    response_model=UnifiedDashboardResponse,
    summary="Get all dashboard data in one request",
    description="""
    Returns ALL dashboard data in a single request:
    - KPIs (revenue, ROAS, spend, conversions)
    - Chart data (sparklines)
    - Top creatives
    - Spend mix by platform
    - Attribution summary & feed (if Shopify connected)

    This replaces 8+ separate API calls with 1, dramatically improving load time.

    NOTE: AI insights are NOT included - fetch them separately and lazy load.
    """
)
def get_unified_dashboard(
    workspace_id: UUID,
    timeframe: str = Query(
        default="last_7_days",
        description="Time period: today, yesterday, last_7_days, last_30_days"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get unified dashboard data.

    NOTE: This is a sync endpoint (not async) to prevent blocking the event loop.
    FastAPI runs it in a thread pool automatically.
    """
    # Verify workspace access
    if current_user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied to this workspace")

    # Get date ranges
    start, end = _get_date_range(timeframe)
    prev_start, prev_end = _get_previous_period(start, end)

    # Check Shopify connection
    shopify_conn = db.query(Connection).filter(
        Connection.workspace_id == workspace_id,
        Connection.provider == ProviderEnum.shopify,
        Connection.status == "active"
    ).first()
    has_shopify = shopify_conn is not None

    # Get connected platforms
    connections = db.query(Connection.provider).filter(
        Connection.workspace_id == workspace_id,
        Connection.status == "active",
        Connection.provider != ProviderEnum.shopify
    ).distinct().all()
    connected_platforms = [c.provider.value for c in connections if c.provider]

    # Fetch all data
    kpis, chart_data, data_source = _get_kpis_and_chart_data(
        db, workspace_id, start, end, prev_start, prev_end, has_shopify
    )

    top_creatives = _get_top_creatives(db, workspace_id, start, end)
    spend_mix = _get_spend_mix(db, workspace_id, start, end)

    # Attribution only if Shopify connected
    attribution_summary = None
    attribution_feed = None
    if has_shopify:
        attribution_summary, attribution_feed = _get_attribution_data(
            db, workspace_id, start, end
        )

    logger.info(
        f"[DASHBOARD_UNIFIED] workspace={workspace_id} timeframe={timeframe} "
        f"kpis={len(kpis)} creatives={len(top_creatives)} "
        f"spend_mix={len(spend_mix)} has_shopify={has_shopify}"
    )

    return UnifiedDashboardResponse(
        kpis=kpis,
        data_source=data_source,
        has_shopify=has_shopify,
        connected_platforms=connected_platforms,
        chart_data=chart_data,
        top_creatives=top_creatives,
        spend_mix=spend_mix,
        attribution_summary=attribution_summary,
        attribution_feed=attribution_feed
    )
