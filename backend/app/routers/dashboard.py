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
    Connection, ShopifyOrder, Attribution, MetricSnapshot, Entity,
    ProviderEnum, User, LevelEnum, Workspace
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


class TopCampaignItem(BaseModel):
    """Top performing campaign."""
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

    # Top campaigns
    top_campaigns: List[TopCampaignItem]

    # Spend mix by platform
    spend_mix: List[SpendMixItem]

    # Attribution (only if Shopify connected)
    attribution_summary: Optional[List[AttributionSummaryItem]] = None
    attribution_feed: Optional[List[AttributionFeedItem]] = None

    # Sync status - ISO timestamp of last successful sync for this workspace
    last_synced_at: Optional[str] = None


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
    has_shopify: bool,
    timeframe: str = "last_7_days"
) -> tuple[List[KpiData], List[Dict], str]:
    """Get KPIs and chart data from MetricSnapshot.

    WHAT:
        Aggregates metrics from MetricSnapshot table (15-min granularity).
        Uses latest snapshot per entity per time bucket for cumulative metrics.
        For today/yesterday: hourly granularity for detailed charts.
        For longer periods: daily granularity.

    WHY:
        MetricSnapshot captures point-in-time cumulative daily totals.
        The latest snapshot of each bucket has the complete picture.
        Hourly data for intraday views matches Google Ads UX.

    NOTE:
        We use DISTINCT ON to get the latest snapshot per entity-bucket,
        then sum across entities for the period total.
    """
    from sqlalchemy import text

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

    # Current period metrics - get latest snapshot per entity per day, then sum
    # Using raw SQL with DISTINCT ON for efficiency
    current_metrics_sql = text("""
        SELECT
            COALESCE(SUM(spend), 0) as spend,
            COALESCE(SUM(revenue), 0) as revenue,
            COALESCE(SUM(conversions), 0) as conversions
        FROM (
            SELECT DISTINCT ON (entity_id, date_trunc('day', captured_at))
                entity_id,
                spend,
                revenue,
                conversions
            FROM metric_snapshots
            WHERE entity_id IN (SELECT id FROM entities WHERE workspace_id = :workspace_id)
              AND date_trunc('day', captured_at) >= :start_date
              AND date_trunc('day', captured_at) <= :end_date
            ORDER BY entity_id, date_trunc('day', captured_at), captured_at DESC
        ) latest_snapshots
    """)

    current_metrics = db.execute(current_metrics_sql, {
        "workspace_id": str(workspace_id),
        "start_date": start_date,
        "end_date": end_date
    }).first()

    # Previous period metrics
    prev_metrics = db.execute(current_metrics_sql, {
        "workspace_id": str(workspace_id),
        "start_date": prev_start_date,
        "end_date": prev_end_date
    }).first()

    # Determine granularity: 15-min for today/yesterday (matches sync frequency), daily for longer periods
    use_intraday = timeframe in ("today", "yesterday")

    if use_intraday:
        # 15-minute breakdown for intraday charts (matches our sync frequency)
        # Generate ALL 15-min slots for the day and LEFT JOIN with actual data
        # This shows the full timeline with gaps where we don't have data yet
        chart_data_sql = text("""
            WITH time_slots AS (
                -- Generate all 15-min slots from start of day until now (or end of yesterday)
                SELECT generate_series(
                    date_trunc('day', CAST(:start_ts AS timestamp with time zone)),
                    LEAST(CAST(:end_ts AS timestamp with time zone), NOW()),
                    INTERVAL '15 minutes'
                ) as time_bucket
            ),
            actual_data AS (
                SELECT
                    time_bucket,
                    COALESCE(SUM(spend), 0) as spend,
                    COALESCE(SUM(revenue), 0) as revenue
                FROM (
                    SELECT DISTINCT ON (entity_id, date_trunc('hour', captured_at) +
                           INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM captured_at) / 15))
                        date_trunc('hour', captured_at) +
                        INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM captured_at) / 15) as time_bucket,
                        entity_id,
                        spend,
                        revenue
                    FROM metric_snapshots
                    WHERE entity_id IN (SELECT id FROM entities WHERE workspace_id = :workspace_id)
                      AND captured_at >= :start_ts
                      AND captured_at <= :end_ts
                    ORDER BY entity_id,
                             date_trunc('hour', captured_at) + INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM captured_at) / 15),
                             captured_at DESC
                ) latest_snapshots
                GROUP BY time_bucket
            )
            SELECT
                ts.time_bucket,
                ad.spend,
                ad.revenue
            FROM time_slots ts
            LEFT JOIN actual_data ad ON ad.time_bucket = ts.time_bucket
            ORDER BY ts.time_bucket
        """)

        chart_data_result = db.execute(chart_data_sql, {
            "workspace_id": str(workspace_id),
            "start_ts": start,
            "end_ts": end
        }).fetchall()

        # Fallback to daily if no intraday data
        if not chart_data_result:
            use_intraday = False

    if not use_intraday:
        # Daily breakdown for sparklines - latest snapshot per entity per day
        chart_data_sql = text("""
            SELECT
                day as time_bucket,
                COALESCE(SUM(spend), 0) as spend,
                COALESCE(SUM(revenue), 0) as revenue
            FROM (
                SELECT DISTINCT ON (entity_id, date_trunc('day', captured_at))
                    date_trunc('day', captured_at)::date as day,
                    entity_id,
                    spend,
                    revenue
                FROM metric_snapshots
                WHERE entity_id IN (SELECT id FROM entities WHERE workspace_id = :workspace_id)
                  AND date_trunc('day', captured_at) >= :start_date
                  AND date_trunc('day', captured_at) <= :end_date
                ORDER BY entity_id, date_trunc('day', captured_at), captured_at DESC
            ) latest_snapshots
            GROUP BY day
            ORDER BY time_bucket
        """)

        chart_data_result = db.execute(chart_data_sql, {
            "workspace_id": str(workspace_id),
            "start_date": start_date,
            "end_date": end_date
        }).fetchall()

    # Build sparklines with appropriate date format
    # Note: For intraday, some slots may have NULL values (no sync at that time)
    if use_intraday:
        # Format as ISO timestamp for intraday data (e.g., "2025-12-08T14:00:00")
        # Only include slots that have data for sparklines
        revenue_sparkline = [
            SparkPoint(date=d.time_bucket.isoformat(), value=float(d.revenue or 0))
            for d in chart_data_result if d.revenue is not None
        ]
        spend_sparkline = [
            SparkPoint(date=d.time_bucket.isoformat(), value=float(d.spend or 0))
            for d in chart_data_result if d.spend is not None
        ]
    else:
        # Format as date string for daily data (e.g., "2025-12-08")
        revenue_sparkline = [SparkPoint(date=str(d.time_bucket), value=float(d.revenue or 0)) for d in chart_data_result]
        spend_sparkline = [SparkPoint(date=str(d.time_bucket), value=float(d.spend or 0)) for d in chart_data_result]

    # Calculate ROAS
    spend_current = float(current_metrics.spend or 0)
    revenue_current = float(current_metrics.revenue or 0)
    spend_prev = float(prev_metrics.spend or 0)
    revenue_prev = float(prev_metrics.revenue or 0)
    conversions_current = float(current_metrics.conversions or 0)
    conversions_prev = float(prev_metrics.conversions or 0)

    roas_current = revenue_current / spend_current if spend_current > 0 else 0
    roas_prev = revenue_prev / spend_prev if spend_prev > 0 else 0

    # ROAS sparkline - use same time format as other sparklines
    roas_sparkline = []
    for d in chart_data_result:
        # Skip slots without data for sparklines
        if d.spend is None or d.revenue is None:
            continue
        bucket_roas = float(d.revenue or 0) / float(d.spend) if float(d.spend or 0) > 0 else 0
        if use_intraday:
            roas_sparkline.append(SparkPoint(date=d.time_bucket.isoformat(), value=bucket_roas))
        else:
            roas_sparkline.append(SparkPoint(date=str(d.time_bucket), value=bucket_roas))

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

    # Chart data (merged for Recharts) - use appropriate time format
    # For intraday: include ALL time slots, NULL values will create gaps in chart
    if use_intraday:
        chart_data = [
            {
                "date": d.time_bucket.isoformat(),
                "revenue": float(d.revenue) if d.revenue is not None else None,
                "spend": float(d.spend) if d.spend is not None else None
            }
            for d in chart_data_result
        ]
    else:
        chart_data = [
            {"date": str(d.time_bucket), "revenue": float(d.revenue or 0), "spend": float(d.spend or 0)}
            for d in chart_data_result
        ]

    data_source = "shopify" if has_shopify else "platform"

    return kpis, chart_data, data_source


def _get_top_campaigns(
    db: Session,
    workspace_id: UUID,
    limit: int = 5
) -> List[TopCampaignItem]:
    """Get top performing ACTIVE campaigns by spend from last 48 hours.

    WHAT:
        Finds active campaigns with highest spend in the last 48 hours.
        Uses latest snapshot per entity per day for accurate totals.

    WHY:
        Top campaigns help merchants see where their budget is going RIGHT NOW.
        Fixed 48-hour window ensures we show current activity, not historical.
        Only active campaigns - paused/completed campaigns are excluded.
    """
    from sqlalchemy import text

    # Fixed 48-hour lookback window (not affected by dashboard timeframe)
    end_date = datetime.now(timezone.utc).date()
    start_date = (datetime.now(timezone.utc) - timedelta(days=2)).date()


    # Roll up child entity metrics (asset_group, adset, ad) to their parent campaigns
    # WHY: Google PMax syncs metrics at asset_group level, not campaign level
    # This query aggregates all child metrics up to the campaign level
    top_campaigns_sql = text("""
        WITH campaign_metrics AS (
            -- Get latest snapshot per entity per day, then sum
            SELECT
                -- Use parent_id for child entities, or entity's own id if it's a campaign
                COALESCE(e.parent_id, e.id) as campaign_id,
                sub.spend,
                sub.revenue
            FROM entities e
            JOIN (
                SELECT DISTINCT ON (ms.entity_id, date_trunc('day', ms.captured_at))
                    ms.entity_id,
                    ms.spend,
                    ms.revenue
                FROM metric_snapshots ms
                JOIN entities e2 ON e2.id = ms.entity_id
                WHERE e2.workspace_id = :workspace_id
                  AND date_trunc('day', ms.captured_at) >= :start_date
                  AND date_trunc('day', ms.captured_at) <= :end_date
                ORDER BY ms.entity_id, date_trunc('day', ms.captured_at), ms.captured_at DESC
            ) sub ON sub.entity_id = e.id
            WHERE e.workspace_id = :workspace_id
        )
        SELECT
            camp.id,
            camp.name,
            c.provider,
            COALESCE(SUM(cm.spend), 0) as spend,
            COALESCE(SUM(cm.revenue), 0) as revenue
        FROM entities camp
        JOIN connections c ON c.id = camp.connection_id
        JOIN campaign_metrics cm ON cm.campaign_id = camp.id
        WHERE camp.workspace_id = :workspace_id
          AND camp.level = 'campaign'
          AND camp.status = 'active'
        GROUP BY camp.id, camp.name, c.provider
        HAVING SUM(cm.spend) > 0
        ORDER BY spend DESC
        LIMIT :limit
    """)

    try:
        results = db.execute(top_campaigns_sql, {
            "workspace_id": str(workspace_id),
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit
        }).fetchall()

        return [
            TopCampaignItem(
                id=str(r.id),
                name=r.name or "Unknown",
                platform=r.provider if r.provider else "unknown",
                spend=float(r.spend or 0),
                revenue=float(r.revenue or 0),
                roas=float(r.revenue or 0) / float(r.spend) if float(r.spend) > 0 else 0
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"[TOP_CAMPAIGNS] ERROR: {type(e).__name__}: {e}")
        return []


def _get_spend_mix(
    db: Session,
    workspace_id: UUID,
    start: datetime,
    end: datetime
) -> List[SpendMixItem]:
    """Get spend breakdown by platform from MetricSnapshot.

    WHAT:
        Aggregates spend by provider (meta, google) for the period.

    WHY:
        Helps merchants understand their ad spend distribution.
    """
    from sqlalchemy import text

    start_date = start.date() if isinstance(start, datetime) else start
    end_date = end.date() if isinstance(end, datetime) else end

    # Get spend by provider - latest snapshot per entity per day
    spend_mix_sql = text("""
        SELECT
            provider,
            COALESCE(SUM(spend), 0) as spend
        FROM (
            SELECT DISTINCT ON (ms.entity_id, date_trunc('day', ms.captured_at))
                ms.provider,
                ms.spend
            FROM metric_snapshots ms
            JOIN entities e ON e.id = ms.entity_id
            WHERE e.workspace_id = :workspace_id
              AND date_trunc('day', ms.captured_at) >= :start_date
              AND date_trunc('day', ms.captured_at) <= :end_date
            ORDER BY ms.entity_id, date_trunc('day', ms.captured_at), ms.captured_at DESC
        ) latest_snapshots
        GROUP BY provider
    """)

    results = db.execute(spend_mix_sql, {
        "workspace_id": str(workspace_id),
        "start_date": start_date,
        "end_date": end_date
    }).fetchall()

    total_spend = sum(float(r.spend or 0) for r in results)

    return [
        SpendMixItem(
            provider=r.provider if r.provider else "unknown",
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

    # Fetch workspace for last_synced_at
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()

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
        db, workspace_id, start, end, prev_start, prev_end, has_shopify, timeframe
    )

    top_campaigns = _get_top_campaigns(db, workspace_id)
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
        f"kpis={len(kpis)} campaigns={len(top_campaigns)} "
        f"spend_mix={len(spend_mix)} has_shopify={has_shopify}"
    )

    # Format last_synced_at as ISO string
    last_synced_at_str = None
    if workspace and workspace.last_synced_at:
        last_synced_at_str = workspace.last_synced_at.isoformat()

    return UnifiedDashboardResponse(
        kpis=kpis,
        data_source=data_source,
        has_shopify=has_shopify,
        connected_platforms=connected_platforms,
        chart_data=chart_data,
        top_campaigns=top_campaigns,
        spend_mix=spend_mix,
        attribution_summary=attribution_summary,
        attribution_feed=attribution_feed,
        last_synced_at=last_synced_at_str
    )
