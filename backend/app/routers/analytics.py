"""
Analytics Chart Router
======================

WHAT:
    Production-ready analytics API for chart data visualization.
    Server-side filtering by platform, campaign, and date range.
    Designed for heavy data loads and senior marketer needs.

WHY:
    - Frontend should be dumb - just render what backend sends
    - Server-side filtering scales better than client-side
    - Efficient SQL queries with proper indexing
    - Series-based response format for easy chart rendering

DESIGN PRINCIPLES:
    1. Server-side filtering: All filtering in SQL, not frontend
    2. Series-based response: [{key, label, color, data: [...]}]
    3. Efficient queries: Window functions, proper indexes
    4. Caching-ready: Response structure supports Redis caching
    5. Granularity auto-detection: hourly for short periods, daily for long

USAGE:
    GET /analytics/chart?workspace_id=...&timeframe=last_7_days&platforms=google,meta
    GET /analytics/chart?workspace_id=...&campaign_ids=uuid1,uuid2&group_by=campaign

REFERENCES:
    - app/models.py: MetricSnapshot, Entity
    - app/routers/dashboard.py: Original implementation (to be deprecated)
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from app.database import get_db
from app.models import Entity, MetricSnapshot, Connection, User, LevelEnum
from app.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class ChartDataPoint(BaseModel):
    """Single data point in a chart series."""
    date: str
    revenue: Optional[float] = 0
    spend: Optional[float] = 0
    conversions: Optional[float] = 0
    roas: Optional[float] = 0
    impressions: Optional[int] = 0
    clicks: Optional[int] = 0
    cpc: Optional[float] = None
    ctr: Optional[float] = None


class ChartSeries(BaseModel):
    """A single series in the chart (e.g., one platform or campaign)."""
    key: str  # 'google', 'meta', 'total', or campaign_id
    label: str  # 'Google Ads', 'Meta Ads', 'All Platforms', or campaign name
    color: str  # Hex color for the line
    data: List[ChartDataPoint]


class ChartTotals(BaseModel):
    """Aggregated totals for the entire period."""
    revenue: float = 0
    spend: float = 0
    conversions: float = 0
    roas: float = 0
    impressions: int = 0
    clicks: int = 0


class ChartMetadata(BaseModel):
    """Metadata about the chart response."""
    granularity: str  # 'hour' or 'day'
    period_start: str
    period_end: str
    generated_at: str
    platforms_available: List[str]
    campaigns_count: int
    disclaimer: Optional[str] = None  # Shown when drill-down ≠ KPI totals


class AnalyticsChartResponse(BaseModel):
    """
    Production-ready chart response.

    Frontend simply maps series[] to chart lines.
    Each series has its own color and data array.
    """
    series: List[ChartSeries]
    totals: ChartTotals
    metadata: ChartMetadata


# =============================================================================
# CONSTANTS
# =============================================================================

PLATFORM_COLORS = {
    'google': '#4285F4',
    'meta': '#0668E1',
    'tiktok': '#00F2EA',
    'total': '#64748b',
}

PLATFORM_LABELS = {
    'google': 'Google Ads',
    'meta': 'Meta Ads',
    'tiktok': 'TikTok Ads',
    'total': 'All Platforms',
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _parse_timeframe(
    timeframe: str,
    start_date: Optional[date],
    end_date: Optional[date]
) -> tuple[datetime, datetime, str]:
    """
    Parse timeframe into start/end datetimes and determine granularity.

    Returns:
        (start_dt, end_dt, granularity)
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if timeframe == "today":
        start = today_start
        end = now
        granularity = "hour"
    elif timeframe == "yesterday":
        start = today_start - timedelta(days=1)
        end = today_start - timedelta(seconds=1)
        granularity = "hour"
    elif timeframe == "last_7_days":
        start = today_start - timedelta(days=6)
        end = now
        granularity = "day"
    elif timeframe == "last_30_days":
        start = today_start - timedelta(days=29)
        end = now
        granularity = "day"
    elif timeframe == "custom" and start_date and end_date:
        start = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        # Auto-detect granularity based on date range
        days = (end_date - start_date).days
        granularity = "hour" if days <= 2 else "day"
    else:
        # Default to last 7 days
        start = today_start - timedelta(days=6)
        end = now
        granularity = "day"

    return start, end, granularity


def _get_entity_ids_for_campaigns(
    db: Session,
    workspace_id: UUID,
    campaign_ids: List[UUID]
) -> List[UUID]:
    """
    Get all entity IDs for selected campaigns, including child entities.

    WHY: Metrics are stored at leaf level (ad/creative), so we need
    all descendant entity IDs to aggregate up to campaign level.

    Uses recursive CTE to walk the entity hierarchy.
    """
    if not campaign_ids:
        return []

    # Recursive CTE to get all descendants of selected campaigns
    # NOTE: Build UUID array literal directly to avoid SQLAlchemy parameter casting issues
    campaign_ids_str = ",".join(f"'{str(cid)}'" for cid in campaign_ids)

    sql = text(f"""
        WITH RECURSIVE entity_tree AS (
            -- Base case: selected campaigns
            SELECT id, id as root_campaign_id
            FROM entities
            WHERE id = ANY(ARRAY[{campaign_ids_str}]::uuid[])
              AND workspace_id = :workspace_id

            UNION ALL

            -- Recursive case: children of current level
            SELECT e.id, et.root_campaign_id
            FROM entities e
            INNER JOIN entity_tree et ON e.parent_id = et.id
        )
        SELECT DISTINCT id FROM entity_tree
    """)

    result = db.execute(sql, {
        "workspace_id": str(workspace_id)
    }).fetchall()

    return [row[0] for row in result]


def _build_chart_query(
    db: Session,
    workspace_id: UUID,
    start: datetime,
    end: datetime,
    granularity: str,
    platforms: Optional[List[str]],
    entity_ids: Optional[List[UUID]],
    group_by: str
) -> List[Dict]:
    """
    Build and execute the main chart data query.

    DESIGN:
        - Uses DISTINCT ON to get latest snapshot per entity per time bucket
        - Groups by time bucket and optionally by provider/campaign
        - Server-side filtering by platform and entity IDs

    Args:
        group_by: 'total' | 'platform' | 'campaign'
    """

    # Build the time truncation based on granularity
    # NOTE: For daily granularity, use metrics_date (date from ad platform in account timezone)
    # For hourly granularity, use captured_at (actual timestamp of the sync)
    if granularity == "hour":
        time_trunc = "date_trunc('hour', ms.captured_at)"
        # Hourly uses timestamp filtering
        # IMPORTANT: Filter to campaign-level entities to avoid double-counting
        # (same logic as dashboard.py - campaign metrics are source of truth)
        where_clauses = [
            "e.workspace_id = :workspace_id",
            "e.level = 'campaign'",
            "ms.captured_at >= :start_ts",
            "ms.captured_at <= :end_ts"
        ]
        params = {
            "workspace_id": str(workspace_id),
            "start_ts": start,
            "end_ts": end
        }
    else:
        time_trunc = "ms.metrics_date"
        # Daily uses metrics_date filtering for accurate day boundaries
        # IMPORTANT: Filter to campaign-level entities to avoid double-counting
        # (same logic as dashboard.py - campaign metrics are source of truth)
        start_date = start.date() if hasattr(start, 'date') else start
        end_date = end.date() if hasattr(end, 'date') else end
        where_clauses = [
            "e.workspace_id = :workspace_id",
            "e.level = 'campaign'",
            "ms.metrics_date >= :start_date",
            "ms.metrics_date <= :end_date"
        ]
        params = {
            "workspace_id": str(workspace_id),
            "start_date": start_date,
            "end_date": end_date
        }

    # Platform filter
    if platforms:
        where_clauses.append("ms.provider = ANY(:platforms)")
        params["platforms"] = platforms

    # Entity filter (for campaign filtering)
    # NOTE: Build UUID array literal directly to avoid SQLAlchemy parameter casting issues
    if entity_ids:
        entity_ids_str = ",".join(f"'{str(eid)}'" for eid in entity_ids)
        where_clauses.append(f"ms.entity_id = ANY(ARRAY[{entity_ids_str}]::uuid[])")

    where_sql = " AND ".join(where_clauses)

    # Main query with DISTINCT ON for latest snapshot per entity per bucket
    if group_by == "campaign":
        # Need to join to get campaign from hierarchy
        sql = text(f"""
            WITH latest_snapshots AS (
                SELECT DISTINCT ON (ms.entity_id, {time_trunc})
                    {time_trunc} as time_bucket,
                    ms.entity_id,
                    ms.provider,
                    ms.spend,
                    ms.revenue,
                    ms.conversions,
                    ms.impressions,
                    ms.clicks
                FROM metric_snapshots ms
                INNER JOIN entities e ON e.id = ms.entity_id
                WHERE {where_sql}
                ORDER BY ms.entity_id, {time_trunc}, ms.captured_at DESC
            ),
            with_campaigns AS (
                SELECT
                    ls.*,
                    -- Walk up to find campaign ancestor
                    COALESCE(
                        (SELECT id FROM entities WHERE id = (
                            WITH RECURSIVE parents AS (
                                SELECT id, parent_id, level FROM entities WHERE id = ls.entity_id
                                UNION ALL
                                SELECT e.id, e.parent_id, e.level
                                FROM entities e
                                INNER JOIN parents p ON p.parent_id = e.id
                            )
                            SELECT id FROM parents WHERE level = 'campaign' LIMIT 1
                        )),
                        ls.entity_id
                    ) as campaign_id
                FROM latest_snapshots ls
            )
            SELECT
                time_bucket,
                campaign_id::text as group_key,
                COALESCE(SUM(spend), 0) as spend,
                COALESCE(SUM(revenue), 0) as revenue,
                COALESCE(SUM(conversions), 0) as conversions,
                COALESCE(SUM(impressions), 0) as impressions,
                COALESCE(SUM(clicks), 0) as clicks
            FROM with_campaigns
            GROUP BY time_bucket, campaign_id
            ORDER BY time_bucket, campaign_id
        """)
    elif group_by == "platform":
        # Group by platform - one line per provider
        sql = text(f"""
            WITH latest_snapshots AS (
                SELECT DISTINCT ON (ms.entity_id, {time_trunc})
                    {time_trunc} as time_bucket,
                    ms.entity_id,
                    ms.provider,
                    ms.spend,
                    ms.revenue,
                    ms.conversions,
                    ms.impressions,
                    ms.clicks
                FROM metric_snapshots ms
                INNER JOIN entities e ON e.id = ms.entity_id
                WHERE {where_sql}
                ORDER BY ms.entity_id, {time_trunc}, ms.captured_at DESC
            )
            SELECT
                time_bucket,
                provider as group_key,
                COALESCE(SUM(spend), 0) as spend,
                COALESCE(SUM(revenue), 0) as revenue,
                COALESCE(SUM(conversions), 0) as conversions,
                COALESCE(SUM(impressions), 0) as impressions,
                COALESCE(SUM(clicks), 0) as clicks
            FROM latest_snapshots
            GROUP BY time_bucket, provider
            ORDER BY time_bucket, provider
        """)
    else:
        # Total aggregate - single line, no grouping by extra column
        sql = text(f"""
            WITH latest_snapshots AS (
                SELECT DISTINCT ON (ms.entity_id, {time_trunc})
                    {time_trunc} as time_bucket,
                    ms.entity_id,
                    ms.provider,
                    ms.spend,
                    ms.revenue,
                    ms.conversions,
                    ms.impressions,
                    ms.clicks
                FROM metric_snapshots ms
                INNER JOIN entities e ON e.id = ms.entity_id
                WHERE {where_sql}
                ORDER BY ms.entity_id, {time_trunc}, ms.captured_at DESC
            )
            SELECT
                time_bucket,
                'total' as group_key,
                COALESCE(SUM(spend), 0) as spend,
                COALESCE(SUM(revenue), 0) as revenue,
                COALESCE(SUM(conversions), 0) as conversions,
                COALESCE(SUM(impressions), 0) as impressions,
                COALESCE(SUM(clicks), 0) as clicks
            FROM latest_snapshots
            GROUP BY time_bucket
            ORDER BY time_bucket
        """)

    result = db.execute(sql, params).fetchall()

    # Convert to list of dicts
    rows = []
    for row in result:
        rows.append({
            "time_bucket": row.time_bucket,
            "group_key": row.group_key,
            "spend": float(row.spend or 0),
            "revenue": float(row.revenue or 0),
            "conversions": float(row.conversions or 0),
            "impressions": int(row.impressions or 0),
            "clicks": int(row.clicks or 0),
        })

    return rows


def _rows_to_series(
    rows: List[Dict],
    group_by: str,
    campaign_names: Dict[str, str],
    granularity: str
) -> tuple[List[ChartSeries], ChartTotals]:
    """
    Convert query rows to chart series format.

    Each unique group_key becomes a series with its own data array.
    """
    # Group rows by group_key
    series_data: Dict[str, List[Dict]] = {}
    totals = {"revenue": 0, "spend": 0, "conversions": 0, "impressions": 0, "clicks": 0}

    for row in rows:
        key = row["group_key"]
        if key not in series_data:
            series_data[key] = []

        # Format date based on granularity
        if granularity == "hour":
            date_str = row["time_bucket"].isoformat() if hasattr(row["time_bucket"], 'isoformat') else str(row["time_bucket"])
        else:
            date_str = str(row["time_bucket"])

        # Calculate derived metrics
        spend = row["spend"]
        revenue = row["revenue"]
        clicks = row["clicks"]
        impressions = row["impressions"]

        roas = revenue / spend if spend > 0 else 0
        cpc = spend / clicks if clicks > 0 else None
        ctr = (clicks / impressions * 100) if impressions > 0 else None

        series_data[key].append({
            "date": date_str,
            "revenue": revenue,
            "spend": spend,
            "conversions": row["conversions"],
            "roas": roas,
            "impressions": impressions,
            "clicks": clicks,
            "cpc": cpc,
            "ctr": ctr,
        })

        # Accumulate totals
        totals["revenue"] += revenue
        totals["spend"] += spend
        totals["conversions"] += row["conversions"]
        totals["impressions"] += impressions
        totals["clicks"] += clicks

    # Build series list
    series_list = []
    for key, data in series_data.items():
        if group_by == "platform":
            label = PLATFORM_LABELS.get(key, key.title())
            color = PLATFORM_COLORS.get(key, '#64748b')
        elif group_by == "campaign":
            label = campaign_names.get(key, f"Campaign {key[:8]}")
            # Generate consistent color from campaign ID
            color = f"#{hash(key) % 0xFFFFFF:06x}"
        else:
            label = "All Platforms"
            color = PLATFORM_COLORS["total"]

        series_list.append(ChartSeries(
            key=key,
            label=label,
            color=color,
            data=[ChartDataPoint(**d) for d in data]
        ))

    # Calculate total ROAS
    total_roas = totals["revenue"] / totals["spend"] if totals["spend"] > 0 else 0

    chart_totals = ChartTotals(
        revenue=totals["revenue"],
        spend=totals["spend"],
        conversions=totals["conversions"],
        roas=total_roas,
        impressions=totals["impressions"],
        clicks=totals["clicks"],
    )

    return series_list, chart_totals


# =============================================================================
# MAIN ENDPOINT
# =============================================================================

@router.get("/chart", response_model=AnalyticsChartResponse)
def get_analytics_chart(
    workspace_id: UUID = Query(..., description="Workspace UUID"),
    timeframe: str = Query("last_7_days", description="Preset: today, yesterday, last_7_days, last_30_days, custom"),
    start_date: Optional[date] = Query(None, description="Start date for custom timeframe"),
    end_date: Optional[date] = Query(None, description="End date for custom timeframe"),
    platforms: Optional[str] = Query(None, description="Comma-separated platforms: google,meta,tiktok"),
    campaign_ids: Optional[str] = Query(None, description="Comma-separated campaign UUIDs"),
    group_by: str = Query("total", description="Grouping: total, platform, campaign"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get chart data for analytics visualization.

    DESIGN:
        - All filtering happens server-side
        - Response is series-based for easy chart rendering
        - Granularity auto-detected based on date range

    PARAMETERS:
        - workspace_id: Required workspace UUID
        - timeframe: Preset or 'custom' with start/end dates
        - platforms: Filter to specific platforms (comma-separated)
        - campaign_ids: Filter to specific campaigns (comma-separated)
        - group_by: How to group data:
            - 'total': Single aggregated line
            - 'platform': One line per platform
            - 'campaign': One line per campaign

    RESPONSE:
        {
            "series": [
                {
                    "key": "google",
                    "label": "Google Ads",
                    "color": "#4285F4",
                    "data": [{"date": "2025-12-01", "revenue": 1000, ...}, ...]
                }
            ],
            "totals": {"revenue": 50000, "spend": 10000, ...},
            "metadata": {...}
        }
    """
    # Verify workspace access
    if current_user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied to this workspace")

    # Parse timeframe
    start, end, granularity = _parse_timeframe(timeframe, start_date, end_date)

    # Parse platforms filter
    platform_list = None
    if platforms:
        platform_list = [p.strip().lower() for p in platforms.split(",") if p.strip()]

    # Parse campaign IDs and get all descendant entity IDs
    entity_ids = None
    campaign_uuid_list = []
    campaign_names = {}

    if campaign_ids:
        try:
            campaign_uuid_list = [UUID(c.strip()) for c in campaign_ids.split(",") if c.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid campaign UUID format")

        if campaign_uuid_list:
            # Get all entity IDs for these campaigns (including children)
            entity_ids = _get_entity_ids_for_campaigns(db, workspace_id, campaign_uuid_list)

            # Get campaign names for labels
            campaigns = db.query(Entity.id, Entity.name).filter(
                Entity.id.in_(campaign_uuid_list)
            ).all()
            campaign_names = {str(c.id): c.name for c in campaigns}

            # If campaign filtering is on, force group_by to campaign
            if group_by == "total":
                group_by = "campaign"

    # Get available platforms for metadata
    platforms_available = (
        db.query(MetricSnapshot.provider)
        .join(Entity, Entity.id == MetricSnapshot.entity_id)
        .filter(Entity.workspace_id == workspace_id)
        .distinct()
        .all()
    )
    platforms_available = [p[0] for p in platforms_available if p[0]]

    # Get campaign count for metadata
    campaigns_count = db.query(Entity).filter(
        Entity.workspace_id == workspace_id,
        Entity.level == LevelEnum.campaign
    ).count()

    # Build and execute query
    rows = _build_chart_query(
        db=db,
        workspace_id=workspace_id,
        start=start,
        end=end,
        granularity=granularity,
        platforms=platform_list,
        entity_ids=entity_ids,
        group_by=group_by
    )

    # Convert to series format
    series, totals = _rows_to_series(rows, group_by, campaign_names, granularity)

    # If no data, return empty series with totals
    if not series:
        # Create empty series based on group_by
        if group_by == "platform" and platform_list:
            series = [
                ChartSeries(
                    key=p,
                    label=PLATFORM_LABELS.get(p, p.title()),
                    color=PLATFORM_COLORS.get(p, '#64748b'),
                    data=[]
                )
                for p in platform_list
            ]
        else:
            series = [
                ChartSeries(
                    key="total",
                    label="All Platforms",
                    color=PLATFORM_COLORS["total"],
                    data=[]
                )
            ]

    # Add disclaimer when grouping by campaign to explain potential total mismatches
    disclaimer = None
    if group_by == "campaign":
        disclaimer = (
            "Campaign breakdowns show attributed metrics from child entities. "
            "For Performance Max and Shopping campaigns, individual campaign totals "
            "may not sum to workspace KPIs."
        )

    metadata = ChartMetadata(
        granularity=granularity,
        period_start=start.date().isoformat(),
        period_end=end.date().isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(),
        platforms_available=platforms_available,
        campaigns_count=campaigns_count,
        disclaimer=disclaimer,
    )

    logger.info(
        f"[ANALYTICS_CHART] workspace={workspace_id} timeframe={timeframe} "
        f"platforms={platform_list} campaigns={len(campaign_uuid_list)} "
        f"group_by={group_by} series={len(series)} rows={len(rows)}"
    )

    return AnalyticsChartResponse(
        series=series,
        totals=totals,
        metadata=metadata,
    )


# =============================================================================
# DAILY REVENUE BAR CHART ENDPOINT
# =============================================================================

class DailyRevenueBar(BaseModel):
    """Single bar in the daily revenue chart."""
    date: str  # ISO date string
    day_name: str  # 'Mon', 'Tue', etc.
    revenue: float
    is_today: bool = False


class DailyRevenueResponse(BaseModel):
    """Response for daily revenue bar chart."""
    bars: List[DailyRevenueBar]
    total_revenue: float
    average_revenue: float
    highest_day: Optional[str] = None  # Date of highest revenue day
    period_days: int


@router.get("/daily-revenue", response_model=DailyRevenueResponse)
def get_daily_revenue(
    workspace_id: UUID = Query(..., description="Workspace UUID"),
    days: int = Query(7, description="Number of days: 7 for week, 30 for month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get daily revenue data for bar chart visualization.

    WHAT: Returns one bar per day for the specified period
    WHY: Dashboard revenue bar chart needs individual daily values

    DESIGN:
        - Always returns one data point per day
        - Server-side aggregation, frontend just renders
        - Days with no data are included with revenue=0

    PARAMETERS:
        - workspace_id: Required workspace UUID
        - days: Number of days (7 for week view, 30 for month view)

    RESPONSE:
        {
            "bars": [
                {"date": "2025-12-09", "day_name": "Mon", "revenue": 1234.56, "is_today": true},
                ...
            ],
            "total_revenue": 12345.67,
            "average_revenue": 1763.67,
            "highest_day": "2025-12-05",
            "period_days": 7
        }
    """
    # Verify workspace access
    if current_user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied to this workspace")

    # Calculate date range
    now = datetime.now(timezone.utc)
    today = now.date()
    start_date = today - timedelta(days=days - 1)

    # Day name lookup
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    # Query: Get daily revenue aggregated from latest snapshots per entity per day
    # NOTE: Uses metrics_date (date from ad platform in account timezone) for accurate day grouping
    # IMPORTANT: Filter to campaign-level entities to avoid double-counting
    sql = text("""
        WITH latest_snapshots AS (
            SELECT DISTINCT ON (ms.entity_id, ms.metrics_date)
                ms.metrics_date as day,
                ms.entity_id,
                ms.revenue
            FROM metric_snapshots ms
            INNER JOIN entities e ON e.id = ms.entity_id
            WHERE e.workspace_id = :workspace_id
              AND e.level = 'campaign'
              AND ms.metrics_date >= :start_date
              AND ms.metrics_date <= :end_date
            ORDER BY ms.entity_id, ms.metrics_date, ms.captured_at DESC
        )
        SELECT
            day,
            COALESCE(SUM(revenue), 0) as revenue
        FROM latest_snapshots
        GROUP BY day
        ORDER BY day
    """)

    result = db.execute(sql, {
        "workspace_id": str(workspace_id),
        "start_date": start_date,
        "end_date": today
    }).fetchall()

    # Build a map of date -> revenue
    revenue_by_date = {row.day: float(row.revenue or 0) for row in result}

    # Generate all days in the range (including days with no data)
    bars = []
    total_revenue = 0.0
    highest_revenue = 0.0
    highest_date = None

    for i in range(days):
        current_date = start_date + timedelta(days=i)
        revenue = revenue_by_date.get(current_date, 0.0)
        is_today = current_date == today

        bars.append(DailyRevenueBar(
            date=current_date.isoformat(),
            day_name=day_names[current_date.weekday()],
            revenue=revenue,
            is_today=is_today
        ))

        total_revenue += revenue
        if revenue > highest_revenue:
            highest_revenue = revenue
            highest_date = current_date.isoformat()

    average_revenue = total_revenue / days if days > 0 else 0

    logger.info(
        f"[DAILY_REVENUE] workspace={workspace_id} days={days} "
        f"total={total_revenue:.2f} avg={average_revenue:.2f}"
    )

    return DailyRevenueResponse(
        bars=bars,
        total_revenue=total_revenue,
        average_revenue=average_revenue,
        highest_day=highest_date,
        period_days=days
    )
