"""
Dashboard KPIs Router
=====================

Purpose:
- Provide KPI data for the dashboard with smart data source selection
- Uses Shopify orders as source of truth when available (e-commerce)
- Falls back to platform metrics when no Shopify connection (SaaS)

Design Principles:
- Isolated endpoint - doesn't affect existing /kpis endpoint
- Same response shape as existing KpiValue for frontend compatibility
- Production-safe with clear fallback behavior

Data Sources:
- Revenue: shopify_orders (preferred) OR metric_facts.revenue (fallback)
- Conversions: attributions count (preferred) OR metric_facts.conversions (fallback)
- Spend: metric_facts.spend (always from ad platforms)
- ROAS: Computed from revenue/spend

References:
- app/routers/kpis.py: Original platform-based KPIs
- app/routers/attribution.py: Attribution data endpoints
- docs/living-docs/ATTRIBUTION_ENGINE.md: Attribution architecture
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database import get_db
from app.models import (
    Connection, ShopifyOrder, Attribution, MetricFact, Entity,
    ProviderEnum, User
)
from app.deps import get_current_user
from app.schemas import KpiValue, SparkPoint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["dashboard-kpis"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class DashboardKpisResponse(BaseModel):
    """Response for dashboard KPIs endpoint."""
    kpis: List[KpiValue]
    data_source: str  # "shopify" or "platform" - tells UI where data came from
    has_shopify: bool
    connected_platforms: List[str]  # List of connected ad platforms: ["meta", "google", "tiktok"]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_date_range(timeframe: str) -> tuple[datetime, datetime]:
    """
    Convert timeframe string to date range.

    Returns (start_datetime, end_datetime) in UTC.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if timeframe == "today":
        return today_start, now
    elif timeframe == "yesterday":
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_start - timedelta(seconds=1)
        return yesterday_start, yesterday_end
    elif timeframe == "last_7_days":
        start = today_start - timedelta(days=6)  # Include today
        return start, now
    elif timeframe == "last_30_days":
        start = today_start - timedelta(days=29)  # Include today
        return start, now
    else:
        # Default to last 7 days
        start = today_start - timedelta(days=6)
        return start, now


def _get_previous_period(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Get the previous period of the same length for comparison."""
    period_length = end - start
    prev_end = start - timedelta(seconds=1)
    prev_start = prev_end - period_length
    return prev_start, prev_end


def _calculate_delta_pct(current: float, previous: float) -> Optional[float]:
    """Calculate percentage change between periods."""
    if previous is None or previous == 0:
        return None
    if current is None:
        return None
    return (current - previous) / previous


def _check_shopify_connection(db: Session, workspace_id: UUID) -> Optional[Connection]:
    """Check if workspace has an active Shopify connection."""
    return (
        db.query(Connection)
        .filter(
            Connection.workspace_id == workspace_id,
            Connection.provider == ProviderEnum.shopify,
            Connection.status == "active"
        )
        .first()
    )


def _get_connected_ad_platforms(db: Session, workspace_id: UUID) -> List[str]:
    """Get list of connected ad platforms (excluding Shopify)."""
    connections = (
        db.query(Connection.provider)
        .filter(
            Connection.workspace_id == workspace_id,
            Connection.status == "active",
            Connection.provider != ProviderEnum.shopify
        )
        .distinct()
        .all()
    )
    return [c.provider.value for c in connections if c.provider]


# =============================================================================
# SHOPIFY DATA QUERIES
# =============================================================================

def _get_shopify_revenue(
    db: Session,
    workspace_id: UUID,
    start: datetime,
    end: datetime
) -> float:
    """Get total revenue from Shopify orders in the period."""
    result = (
        db.query(func.coalesce(func.sum(ShopifyOrder.total_price), 0))
        .filter(
            ShopifyOrder.workspace_id == workspace_id,
            ShopifyOrder.order_created_at >= start,
            ShopifyOrder.order_created_at <= end
        )
        .scalar()
    )
    return float(result or 0)


def _get_shopify_conversions(
    db: Session,
    workspace_id: UUID,
    start: datetime,
    end: datetime
) -> int:
    """Get count of attributed orders (conversions) in the period."""
    # Count attributions that have a provider (not just direct/unknown)
    result = (
        db.query(func.count(Attribution.id))
        .filter(
            Attribution.workspace_id == workspace_id,
            Attribution.attributed_at >= start,
            Attribution.attributed_at <= end,
            Attribution.provider.notin_(["direct", "unknown", "organic"])
        )
        .scalar()
    )
    return int(result or 0)


def _get_shopify_revenue_sparkline(
    db: Session,
    workspace_id: UUID,
    start: datetime,
    end: datetime
) -> List[SparkPoint]:
    """Get daily revenue breakdown for sparkline."""
    results = (
        db.query(
            func.date(ShopifyOrder.order_created_at).label("day"),
            func.coalesce(func.sum(ShopifyOrder.total_price), 0).label("revenue")
        )
        .filter(
            ShopifyOrder.workspace_id == workspace_id,
            ShopifyOrder.order_created_at >= start,
            ShopifyOrder.order_created_at <= end
        )
        .group_by(func.date(ShopifyOrder.order_created_at))
        .order_by(func.date(ShopifyOrder.order_created_at))
        .all()
    )

    return [
        SparkPoint(date=str(row.day), value=float(row.revenue or 0))
        for row in results
    ]


def _get_shopify_conversions_sparkline(
    db: Session,
    workspace_id: UUID,
    start: datetime,
    end: datetime
) -> List[SparkPoint]:
    """Get daily conversions breakdown for sparkline."""
    results = (
        db.query(
            func.date(Attribution.attributed_at).label("day"),
            func.count(Attribution.id).label("conversions")
        )
        .filter(
            Attribution.workspace_id == workspace_id,
            Attribution.attributed_at >= start,
            Attribution.attributed_at <= end,
            Attribution.provider.notin_(["direct", "unknown", "organic"])
        )
        .group_by(func.date(Attribution.attributed_at))
        .order_by(func.date(Attribution.attributed_at))
        .all()
    )

    return [
        SparkPoint(date=str(row.day), value=float(row.conversions or 0))
        for row in results
    ]


# =============================================================================
# PLATFORM DATA QUERIES (FALLBACK)
# =============================================================================

def _get_platform_metric(
    db: Session,
    workspace_id: UUID,
    metric: str,
    start: datetime,
    end: datetime
) -> float:
    """Get aggregated metric from MetricFact (platform data)."""
    # Convert datetime to date for MetricFact which uses event_date
    start_date = start.date() if isinstance(start, datetime) else start
    end_date = end.date() if isinstance(end, datetime) else end

    # Get all entities for this workspace
    entity_ids = (
        db.query(Entity.id)
        .filter(Entity.workspace_id == workspace_id)
        .scalar_subquery()
    )

    column = getattr(MetricFact, metric, None)
    if column is None:
        return 0.0

    result = (
        db.query(func.coalesce(func.sum(column), 0))
        .filter(
            MetricFact.entity_id.in_(entity_ids),
            func.date(MetricFact.event_date) >= start_date,
            func.date(MetricFact.event_date) <= end_date
        )
        .scalar()
    )
    return float(result or 0)


def _get_platform_sparkline(
    db: Session,
    workspace_id: UUID,
    metric: str,
    start: datetime,
    end: datetime
) -> List[SparkPoint]:
    """Get daily metric breakdown from MetricFact for sparkline."""
    start_date = start.date() if isinstance(start, datetime) else start
    end_date = end.date() if isinstance(end, datetime) else end

    entity_ids = (
        db.query(Entity.id)
        .filter(Entity.workspace_id == workspace_id)
        .scalar_subquery()
    )

    column = getattr(MetricFact, metric, None)
    if column is None:
        return []

    results = (
        db.query(
            func.date(MetricFact.event_date).label("day"),
            func.coalesce(func.sum(column), 0).label("value")
        )
        .filter(
            MetricFact.entity_id.in_(entity_ids),
            func.date(MetricFact.event_date) >= start_date,
            func.date(MetricFact.event_date) <= end_date
        )
        .group_by(func.date(MetricFact.event_date))
        .order_by(func.date(MetricFact.event_date))
        .all()
    )

    return [
        SparkPoint(date=str(row.day), value=float(row.value or 0))
        for row in results
    ]


# =============================================================================
# MAIN ENDPOINT
# =============================================================================

@router.get(
    "/{workspace_id}/dashboard/kpis",
    response_model=DashboardKpisResponse,
    summary="Get dashboard KPIs with smart data source",
    description="""
    Returns KPIs for the dashboard with smart data source selection:

    - **E-commerce (Shopify connected)**: Revenue and conversions from Shopify orders
    - **SaaS (no Shopify)**: Revenue and conversions from ad platform metrics
    - **Ad Spend**: Always from ad platforms (MetricFact)
    - **ROAS**: Computed from revenue / spend

    This ensures merchants see "real" revenue from their store, not inflated
    platform-reported numbers.
    """
)
def get_dashboard_kpis(
    workspace_id: UUID,
    timeframe: str = Query(
        default="last_7_days",
        description="Time period: today, yesterday, last_7_days, last_30_days"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get dashboard KPIs with Shopify-first data source.

    NOTE: Changed from async def to def to prevent blocking the event loop.
    FastAPI will automatically run this in a thread pool.

    WHY: Sync SQLAlchemy in async endpoints blocks ALL concurrent requests.
    When User A runs a slow query, User B's requests are queued → crashes.

    Logic:
    1. Check if workspace has Shopify connection
    2. If YES: Revenue/Conversions from Shopify, Spend from platforms
    3. If NO: All metrics from platform data (fallback)
    4. ROAS computed from revenue/spend regardless of source
    """
    # Verify workspace access
    if current_user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied to this workspace")

    # Get date range
    start, end = _get_date_range(timeframe)
    prev_start, prev_end = _get_previous_period(start, end)

    # Check for Shopify connection
    shopify_connection = _check_shopify_connection(db, workspace_id)
    has_shopify = shopify_connection is not None

    # Get connected ad platforms
    connected_platforms = _get_connected_ad_platforms(db, workspace_id)

    # Initialize KPI values
    revenue_current = 0.0
    revenue_prev = 0.0
    conversions_current = 0
    conversions_prev = 0
    spend_current = 0.0
    spend_prev = 0.0

    revenue_sparkline = []
    conversions_sparkline = []
    spend_sparkline = []

    if has_shopify:
        # ─── SHOPIFY MODE: Use Shopify orders as source of truth ───
        logger.info(f"[DASHBOARD_KPI] Using Shopify data for workspace {workspace_id}")

        # Revenue from Shopify orders
        revenue_current = _get_shopify_revenue(db, workspace_id, start, end)
        revenue_prev = _get_shopify_revenue(db, workspace_id, prev_start, prev_end)
        revenue_sparkline = _get_shopify_revenue_sparkline(db, workspace_id, start, end)

        # Conversions from attributions (ad-attributed orders)
        conversions_current = _get_shopify_conversions(db, workspace_id, start, end)
        conversions_prev = _get_shopify_conversions(db, workspace_id, prev_start, prev_end)
        conversions_sparkline = _get_shopify_conversions_sparkline(db, workspace_id, start, end)

        # Spend still from platforms
        spend_current = _get_platform_metric(db, workspace_id, "spend", start, end)
        spend_prev = _get_platform_metric(db, workspace_id, "spend", prev_start, prev_end)
        spend_sparkline = _get_platform_sparkline(db, workspace_id, "spend", start, end)

        data_source = "shopify"
    else:
        # ─── PLATFORM MODE: Use ad platform data (SaaS fallback) ───
        logger.info(f"[DASHBOARD_KPI] Using platform data for workspace {workspace_id} (no Shopify)")

        revenue_current = _get_platform_metric(db, workspace_id, "revenue", start, end)
        revenue_prev = _get_platform_metric(db, workspace_id, "revenue", prev_start, prev_end)
        revenue_sparkline = _get_platform_sparkline(db, workspace_id, "revenue", start, end)

        conversions_current = _get_platform_metric(db, workspace_id, "conversions", start, end)
        conversions_prev = _get_platform_metric(db, workspace_id, "conversions", prev_start, prev_end)
        conversions_sparkline = _get_platform_sparkline(db, workspace_id, "conversions", start, end)

        spend_current = _get_platform_metric(db, workspace_id, "spend", start, end)
        spend_prev = _get_platform_metric(db, workspace_id, "spend", prev_start, prev_end)
        spend_sparkline = _get_platform_sparkline(db, workspace_id, "spend", start, end)

        data_source = "platform"

    # ─── COMPUTE ROAS ───
    roas_current = revenue_current / spend_current if spend_current > 0 else 0.0
    roas_prev = revenue_prev / spend_prev if spend_prev > 0 else 0.0

    # Compute ROAS sparkline (revenue / spend per day)
    roas_sparkline = []
    spend_by_day = {sp.date: sp.value for sp in spend_sparkline}
    for rev_point in revenue_sparkline:
        day_spend = spend_by_day.get(rev_point.date, 0)
        day_roas = rev_point.value / day_spend if day_spend > 0 else 0.0
        roas_sparkline.append(SparkPoint(date=rev_point.date, value=day_roas))

    # ─── BUILD RESPONSE ───
    kpis = [
        KpiValue(
            key="revenue",
            value=revenue_current,
            prev=revenue_prev,
            delta_pct=_calculate_delta_pct(revenue_current, revenue_prev),
            sparkline=revenue_sparkline
        ),
        KpiValue(
            key="roas",
            value=roas_current,
            prev=roas_prev,
            delta_pct=_calculate_delta_pct(roas_current, roas_prev),
            sparkline=roas_sparkline
        ),
        KpiValue(
            key="spend",
            value=spend_current,
            prev=spend_prev,
            delta_pct=_calculate_delta_pct(spend_current, spend_prev),
            sparkline=spend_sparkline
        ),
        KpiValue(
            key="conversions",
            value=float(conversions_current),
            prev=float(conversions_prev),
            delta_pct=_calculate_delta_pct(float(conversions_current), float(conversions_prev)),
            sparkline=conversions_sparkline
        ),
    ]

    logger.info(
        f"[DASHBOARD_KPI] Returned KPIs for workspace {workspace_id}: "
        f"source={data_source}, revenue=${revenue_current:.2f}, "
        f"spend=${spend_current:.2f}, roas={roas_current:.2f}x, "
        f"conversions={conversions_current}"
    )

    return DashboardKpisResponse(
        kpis=kpis,
        data_source=data_source,
        has_shopify=has_shopify,
        connected_platforms=connected_platforms
    )
