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
    ProviderEnum, User, LevelEnum, Workspace, ShopifyShop, ShopifyFinancialStatusEnum
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


class TopCampaignsData(BaseModel):
    """Top campaigns with disclaimer."""
    items: List[TopCampaignItem]
    disclaimer: Optional[str] = None


class UnifiedDashboardResponse(BaseModel):
    """Complete dashboard data in one response."""
    # KPIs
    kpis: List[KpiData]
    data_source: str  # "shopify" or "platform"
    has_shopify: bool
    connected_platforms: List[str]

    # Currency - derived from the primary connection's currency
    # WHAT: ISO 4217 currency code for all monetary values in this response
    # WHY: Frontend needs to display correct currency symbol (€ vs $)
    currency: str = "USD"

    # Chart metadata (explicit contract so UI never guesses)
    # WHAT: How to interpret chart_data[].date and format axes
    # WHY: Avoids timezone bugs from parsing date-only strings as timestamps
    chart_granularity: str  # "intraday_15m" | "daily"
    chart_timezone: str = "UTC"  # IANA timezone used for rendering chart labels
    data_as_of: Optional[str] = None  # ISO timestamp of freshest included data
    intraday_available_from: Optional[str] = None  # ISO timestamp of first intraday point (if any)
    intraday_reason_unavailable: Optional[str] = None  # Message key when intraday is not available

    # Chart data (same as KPIs but guaranteed sparklines)
    chart_data: List[Dict[str, Any]]

    # Top campaigns - wrapped with disclaimer
    top_campaigns: TopCampaignsData

    # Spend mix by platform
    spend_mix: List[SpendMixItem]

    # Provider totals (platform metrics) for reconciliation/debugging
    # Adds per-provider spend/conversions/conversion_value for the selected range.
    provider_totals: Optional[Dict[str, Dict[str, float]]] = None

    # Attribution (only if Shopify connected)
    attribution_summary: Optional[List[AttributionSummaryItem]] = None
    attribution_feed: Optional[List[AttributionFeedItem]] = None

    # Sync status - ISO timestamp of last successful sync for this workspace
    last_synced_at: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_date_range(timeframe: str, account_timezone: Optional[str] = None) -> tuple[datetime, datetime]:
    """Convert timeframe string to date range.

    WHAT:
        Calculates date ranges for dashboard queries using the ad account's timezone.

    WHY:
        Google Ads and Meta report data in the account's configured timezone.
        Using UTC for queries would misalign data boundaries (e.g., "yesterday" in
        UTC could span two calendar days in the account's timezone).

    Args:
        timeframe: One of "today", "yesterday", "last_7_days", "last_30_days", "last_90_days"
        account_timezone: IANA timezone string (e.g., "Europe/Amsterdam", "America/New_York")
                         Falls back to UTC if not provided or invalid.

    Returns:
        Tuple of (start, end) datetime objects in UTC for database queries.
    """
    from zoneinfo import ZoneInfo

    # Use account timezone if provided, otherwise fall back to UTC
    tz = timezone.utc
    if account_timezone:
        try:
            tz = ZoneInfo(account_timezone)
        except Exception:
            logger.warning("[DASHBOARD] Invalid timezone '%s', falling back to UTC", account_timezone)
            tz = timezone.utc

    # Get current time in account's timezone to determine "today" correctly
    now_local = datetime.now(tz)

    # Calculate "today" start in account's timezone
    today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert to UTC for database queries
    today_start = today_start_local.astimezone(timezone.utc)
    now = now_local.astimezone(timezone.utc)

    if timeframe == "today":
        return today_start, now
    elif timeframe == "yesterday":
        yesterday_start = today_start - timedelta(days=1)
        # Use microseconds=1 to include snapshots stored at 23:59:59.999999 (attribution sync)
        yesterday_end = today_start - timedelta(microseconds=1)
        return yesterday_start, yesterday_end
    elif timeframe == "last_7_days":
        start = today_start - timedelta(days=6)
        return start, now
    elif timeframe == "last_30_days":
        start = today_start - timedelta(days=29)
        return start, now
    elif timeframe == "last_90_days":
        start = today_start - timedelta(days=89)
        return start, now
    else:
        start = today_start - timedelta(days=6)
        return start, now


def _get_previous_period(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Get the previous period of the same length."""
    period_length = end - start
    # Use microseconds=1 to include snapshots at 23:59:59.999999
    prev_end = start - timedelta(microseconds=1)
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
    timeframe: str = "last_7_days",
    reporting_timezone: str = "UTC",
    platform: Optional[str] = None,
) -> tuple[
    List[KpiData],
    List[Dict],
    str,
    str,
    Optional[datetime],
    Optional[datetime],
    Optional[str],
]:
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

    # For metrics_date filtering we must use the reporting timezone's calendar day,
    # not the UTC date of the boundary timestamps (which can be off by 1).
    from zoneinfo import ZoneInfo

    try:
        tz = ZoneInfo(reporting_timezone) if reporting_timezone else timezone.utc
    except Exception:
        tz = timezone.utc

    start_date = start.astimezone(tz).date()
    end_date = end.astimezone(tz).date()
    prev_start_date = prev_start.astimezone(tz).date()
    prev_end_date = prev_end.astimezone(tz).date()

    # Current period metrics - get latest snapshot per CAMPAIGN entity per day, then sum
    # WHY: Campaign-level metrics are SOURCE OF TRUTH for KPI totals.
    # PMax campaigns don't attribute all spend to asset_groups, Shopping campaigns
    # may have spend not fully attributed to ads. Campaign-level ensures accuracy.
    # Using raw SQL with DISTINCT ON for efficiency
    #
    # NOTE: Uses metrics_date (the date from ad platform in account timezone) for
    # accurate day filtering. captured_at is only used for ordering to get freshest data.
    # Build platform filter clause if specified
    platform_filter = ""
    if platform:
        platform_filter = "AND provider = :platform"

    current_metrics_sql = text(f"""
        SELECT
            COALESCE(SUM(spend), 0) as spend,
            COALESCE(SUM(revenue), 0) as revenue,
            COALESCE(SUM(conversions), 0) as conversions,
            COALESCE(SUM(clicks), 0) as clicks,
            COALESCE(SUM(impressions), 0) as impressions
        FROM (
            SELECT DISTINCT ON (entity_id, metrics_date)
                entity_id,
                spend,
                revenue,
                conversions,
                clicks,
                impressions
            FROM metric_snapshots
            WHERE entity_id IN (
                SELECT id FROM entities
                WHERE workspace_id = :workspace_id
                AND level = 'campaign'
            )
              AND metrics_date >= :start_date
              AND metrics_date <= :end_date
              {platform_filter}
            ORDER BY entity_id, metrics_date, captured_at DESC
        ) latest_snapshots
    """)

    # Build params dict, conditionally including platform
    current_params = {
        "workspace_id": str(workspace_id),
        "start_date": start_date,
        "end_date": end_date
    }
    if platform:
        current_params["platform"] = platform

    current_metrics = db.execute(current_metrics_sql, current_params).first()

    # Previous period metrics
    prev_params = {
        "workspace_id": str(workspace_id),
        "start_date": prev_start_date,
        "end_date": prev_end_date
    }
    if platform:
        prev_params["platform"] = platform

    prev_metrics = db.execute(current_metrics_sql, prev_params).first()

    # Determine granularity: 15-min for today/yesterday (matches sync frequency), daily for longer periods
    intraday_requested = timeframe in ("today", "yesterday")
    use_intraday = intraday_requested

    intraday_fallback_reason: Optional[str] = None

    # Build platform filter for chart queries (used in both intraday and daily queries)
    chart_platform_filter = ""
    if platform:
        chart_platform_filter = "AND provider = :platform"

    if use_intraday:
        # 15-minute breakdown for intraday charts (matches our sync frequency)
        # Now includes per-provider breakdown for multi-line charts
        # WHY: Uses campaign-level entities for accurate KPI totals
        #
        # IMPORTANT: For cumulative metrics (spend, revenue), we show LATEST KNOWN VALUE
        # for each entity at each time bucket. This means if Entity A synced at 14:45 and
        # Entity B's last sync was at 14:30, the 14:45 bucket shows:
        # - Entity A's 14:45 value + Entity B's 14:30 value (carried forward)
        # This ensures the chart matches the KPI totals at any point in time.
        chart_data_sql = text(f"""
            WITH time_buckets AS (
                -- Generate all 15-min buckets for the time range
                SELECT generate_series(
                    date_trunc('hour', CAST(:start_ts AS timestamp)),
                    date_trunc('hour', CAST(:end_ts AS timestamp)) +
                        INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM CAST(:end_ts AS timestamp)) / 15),
                    INTERVAL '15 minutes'
                ) as time_bucket
            ),
            entity_snapshots AS (
                -- Get all snapshots with their 15-min bucket
                SELECT
                    entity_id,
                    provider,
                    date_trunc('hour', captured_at) +
                        INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM captured_at) / 15) as snap_bucket,
                    spend,
                    revenue,
                    conversions,
                    captured_at
                FROM metric_snapshots
                WHERE entity_id IN (
                    SELECT id FROM entities
                    WHERE workspace_id = :workspace_id
                    AND level = 'campaign'
                )
                  AND captured_at >= :start_ts
                  AND captured_at <= :end_ts
                  {chart_platform_filter}
            ),
            latest_per_entity_bucket AS (
                -- For each time bucket, get each entity's LATEST snapshot up to that bucket
                -- This "carries forward" values so entities don't disappear from totals
                SELECT DISTINCT ON (tb.time_bucket, es.entity_id)
                    tb.time_bucket,
                    es.entity_id,
                    es.provider,
                    es.spend,
                    es.revenue,
                    es.conversions
                FROM time_buckets tb
                JOIN entity_snapshots es ON es.snap_bucket <= tb.time_bucket
                ORDER BY tb.time_bucket, es.entity_id, es.captured_at DESC
            )
            SELECT
                time_bucket,
                provider,
                COALESCE(SUM(spend), 0) as spend,
                COALESCE(SUM(revenue), 0) as revenue,
                COALESCE(SUM(conversions), 0) as conversions
            FROM latest_per_entity_bucket
            GROUP BY time_bucket, provider
            ORDER BY time_bucket, provider
        """)

        chart_params = {
            "workspace_id": str(workspace_id),
            "start_ts": start,
            "end_ts": end
        }
        if platform:
            chart_params["platform"] = platform

        chart_data_result = db.execute(chart_data_sql, chart_params).fetchall()

        # Fallback to daily if no intraday data (or only a single point, which is effectively daily)
        if not chart_data_result:
            use_intraday = False
            intraday_fallback_reason = "intraday_not_available_until_first_sync"
        else:
            distinct_buckets = {r.time_bucket for r in chart_data_result}
            # If we only have one bucket (often caused by backfill/end-of-day anchoring),
            # showing a time axis is misleading. Prefer daily + an explanatory message.
            if len(distinct_buckets) < 2:
                use_intraday = False
                intraday_fallback_reason = "intraday_insufficient_points"

    if not use_intraday:
        # Daily breakdown for sparklines - latest snapshot per CAMPAIGN entity per day
        # Now includes per-provider breakdown for multi-line charts
        # WHY: Uses campaign-level entities for accurate KPI totals
        # NOTE: Uses metrics_date (date from ad platform in account timezone) for accurate day grouping
        chart_data_sql = text(f"""
            SELECT
                metrics_date as time_bucket,
                provider,
                COALESCE(SUM(spend), 0) as spend,
                COALESCE(SUM(revenue), 0) as revenue,
                COALESCE(SUM(conversions), 0) as conversions
            FROM (
                SELECT DISTINCT ON (entity_id, metrics_date)
                    metrics_date,
                    entity_id,
                    provider,
                    spend,
                    revenue,
                    conversions
                FROM metric_snapshots
                WHERE entity_id IN (
                    SELECT id FROM entities
                    WHERE workspace_id = :workspace_id
                    AND level = 'campaign'
                )
                  AND metrics_date >= :start_date
                  AND metrics_date <= :end_date
                  {chart_platform_filter}
                ORDER BY entity_id, metrics_date, captured_at DESC
            ) latest_snapshots
            GROUP BY metrics_date, provider
            ORDER BY time_bucket, provider
        """)

        daily_chart_params = {
            "workspace_id": str(workspace_id),
            "start_date": start_date,
            "end_date": end_date
        }
        if platform:
            daily_chart_params["platform"] = platform

        chart_data_result = db.execute(chart_data_sql, daily_chart_params).fetchall()

    chart_granularity = "intraday_15m" if use_intraday else "daily"

    # Compute freshness metadata for UI debugging and messaging.
    # NOTE: We keep this separate from the main aggregation queries to keep SQL readable.
    data_as_of: Optional[datetime] = None
    intraday_available_from: Optional[datetime] = None
    intraday_reason_unavailable: Optional[str] = None

    if use_intraday:
        meta_sql = text("""
            SELECT
              MAX(ms.captured_at) AS data_as_of,
              MIN(ms.captured_at) AS intraday_available_from
            FROM metric_snapshots ms
            JOIN entities e ON e.id = ms.entity_id
            WHERE e.workspace_id = :workspace_id
              AND e.level = 'campaign'
              AND ms.captured_at >= :start_ts
              AND ms.captured_at <= :end_ts
        """)
        meta = db.execute(meta_sql, {
            "workspace_id": str(workspace_id),
            "start_ts": start,
            "end_ts": end,
        }).first()
        if meta:
            data_as_of = meta.data_as_of
            intraday_available_from = meta.intraday_available_from
    else:
        meta_sql = text("""
            SELECT MAX(ms.captured_at) AS data_as_of
            FROM metric_snapshots ms
            JOIN entities e ON e.id = ms.entity_id
            WHERE e.workspace_id = :workspace_id
              AND e.level = 'campaign'
              AND ms.metrics_date >= :start_date
              AND ms.metrics_date <= :end_date
        """)
        meta = db.execute(meta_sql, {
            "workspace_id": str(workspace_id),
            "start_date": start_date,
            "end_date": end_date,
        }).first()
        if meta:
            data_as_of = meta.data_as_of

        if intraday_requested:
            intraday_reason_unavailable = intraday_fallback_reason or "intraday_not_available_until_first_sync"

    # Build sparklines with appropriate date format
    # Note: For intraday, some slots may have NULL values (no sync at that time)
    if use_intraday:
        # Format as ISO timestamp for intraday data (e.g., "2025-12-08T14:00:00")
        # Only include slots that have data for sparklines
        spend_sparkline = [
            SparkPoint(date=d.time_bucket.isoformat(), value=float(d.spend or 0))
            for d in chart_data_result if d.spend is not None
        ]
        conversions_sparkline = [
            SparkPoint(date=d.time_bucket.isoformat(), value=float(d.conversions or 0))
            for d in chart_data_result if d.conversions is not None
        ]
    else:
        # Format as date string for daily data (e.g., "2025-12-08")
        spend_sparkline = [SparkPoint(date=str(d.time_bucket), value=float(d.spend or 0)) for d in chart_data_result]
        conversions_sparkline = [SparkPoint(date=str(d.time_bucket), value=float(d.conversions or 0)) for d in chart_data_result]

    # Revenue source: Shopify-first when connected, else platform conversion value.
    # NOTE: We keep platform per-provider revenue in chart_data for transparency, but the
    # top-level "revenue" series becomes Shopify revenue when available.
    revenue_sparkline: List[SparkPoint]
    if has_shopify:
        revenue_statuses = (
            ShopifyFinancialStatusEnum.paid,
            ShopifyFinancialStatusEnum.partially_paid,
            ShopifyFinancialStatusEnum.partially_refunded,
        )
        # Shopify timestamps are stored without timezone in our DB; treat them as UTC.
        shopify_start = start.replace(tzinfo=None)
        shopify_end = end.replace(tzinfo=None)
        shopify_prev_start = prev_start.replace(tzinfo=None)
        shopify_prev_end = prev_end.replace(tzinfo=None)

        # Totals for KPI + previous period
        revenue_current = float(
            db.query(func.coalesce(func.sum(ShopifyOrder.total_price), 0))
            .filter(
                ShopifyOrder.workspace_id == workspace_id,
                ShopifyOrder.order_created_at >= shopify_start,
                ShopifyOrder.order_created_at <= shopify_end,
                ShopifyOrder.financial_status.in_(revenue_statuses),
            )
            .scalar()
            or 0
        )
        revenue_prev = float(
            db.query(func.coalesce(func.sum(ShopifyOrder.total_price), 0))
            .filter(
                ShopifyOrder.workspace_id == workspace_id,
                ShopifyOrder.order_created_at >= shopify_prev_start,
                ShopifyOrder.order_created_at <= shopify_prev_end,
                ShopifyOrder.financial_status.in_(revenue_statuses),
            )
            .scalar()
            or 0
        )

        if use_intraday:
            # Match intraday chart start to first available platform snapshot to avoid misleading
            # flat lines for hours before the workspace started syncing.
            base_start = intraday_available_from or start
            intraday_start = base_start.replace(
                minute=(base_start.minute // 15) * 15,
                second=0,
                microsecond=0,
            )
            intraday_start_naive = intraday_start.replace(tzinfo=None)

            shopify_intraday_sql = text("""
                WITH time_buckets AS (
                    SELECT generate_series(
                        date_trunc('hour', CAST(:start_ts AS timestamp)),
                        date_trunc('hour', CAST(:end_ts AS timestamp)) +
                            INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM CAST(:end_ts AS timestamp)) / 15),
                        INTERVAL '15 minutes'
                    ) AS time_bucket
                ),
                bucket_revenue AS (
                    SELECT
                        date_trunc('hour', o.order_created_at) +
                            INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM o.order_created_at) / 15) AS time_bucket,
                        COALESCE(SUM(o.total_price), 0) AS revenue
                    FROM shopify_orders o
                    WHERE o.workspace_id = :workspace_id
                      AND o.order_created_at >= CAST(:start_ts AS timestamp)
                      AND o.order_created_at <= CAST(:end_ts AS timestamp)
                      AND o.financial_status IN ('paid', 'partially_paid', 'partially_refunded')
                    GROUP BY 1
                )
                SELECT
                    tb.time_bucket,
                    SUM(COALESCE(br.revenue, 0)) OVER (ORDER BY tb.time_bucket) AS cumulative_revenue
                FROM time_buckets tb
                LEFT JOIN bucket_revenue br ON br.time_bucket = tb.time_bucket
                ORDER BY tb.time_bucket
            """)

            rows = db.execute(shopify_intraday_sql, {
                "workspace_id": str(workspace_id),
                "start_ts": intraday_start_naive,
                "end_ts": shopify_end,
            }).fetchall()

            revenue_sparkline = [
                SparkPoint(date=r.time_bucket.isoformat(), value=float(r.cumulative_revenue or 0))
                for r in rows
            ]
        else:
            shopify_daily_sql = text("""
                SELECT
                    ((o.order_created_at AT TIME ZONE 'UTC') AT TIME ZONE CAST(:tz AS text))::date AS day,
                    COALESCE(SUM(o.total_price), 0) AS revenue
                FROM shopify_orders o
                WHERE o.workspace_id = :workspace_id
                  AND o.order_created_at >= CAST(:start_ts AS timestamp)
                  AND o.order_created_at <= CAST(:end_ts AS timestamp)
                  AND o.financial_status IN ('paid', 'partially_paid', 'partially_refunded')
                GROUP BY 1
                ORDER BY 1
            """)

            rows = db.execute(shopify_daily_sql, {
                "workspace_id": str(workspace_id),
                "start_ts": shopify_start,
                "end_ts": shopify_end,
                "tz": reporting_timezone,
            }).fetchall()

            revenue_sparkline = [
                SparkPoint(date=str(r.day), value=float(r.revenue or 0))
                for r in rows
            ]
    else:
        revenue_current = float(current_metrics.revenue or 0)
        revenue_prev = float(prev_metrics.revenue or 0)
        if use_intraday:
            revenue_sparkline = [
                SparkPoint(date=d.time_bucket.isoformat(), value=float(d.revenue or 0))
                for d in chart_data_result if d.revenue is not None
            ]
        else:
            revenue_sparkline = [SparkPoint(date=str(d.time_bucket), value=float(d.revenue or 0)) for d in chart_data_result]

    conversion_value_current = float(current_metrics.revenue or 0)
    conversion_value_prev = float(prev_metrics.revenue or 0)
    if has_shopify:
        # Platform conversion value sparkline (in the same granularity as chart_data_result).
        if use_intraday:
            conversion_value_sparkline = [
                SparkPoint(date=d.time_bucket.isoformat(), value=float(d.revenue or 0))
                for d in chart_data_result if d.revenue is not None
            ]
        else:
            conversion_value_sparkline = [SparkPoint(date=str(d.time_bucket), value=float(d.revenue or 0)) for d in chart_data_result]
    else:
        conversion_value_sparkline = revenue_sparkline

    # Calculate ROAS
    spend_current = float(current_metrics.spend or 0)
    spend_prev = float(prev_metrics.spend or 0)
    conversions_current = float(current_metrics.conversions or 0)
    conversions_prev = float(prev_metrics.conversions or 0)
    clicks_current = float(current_metrics.clicks or 0)
    clicks_prev = float(prev_metrics.clicks or 0)
    impressions_current = float(current_metrics.impressions or 0)
    impressions_prev = float(prev_metrics.impressions or 0)

    roas_current = revenue_current / spend_current if spend_current > 0 else 0
    roas_prev = revenue_prev / spend_prev if spend_prev > 0 else 0

    # Calculate CPC (Cost Per Click)
    cpc_current = spend_current / clicks_current if clicks_current > 0 else 0
    cpc_prev = spend_prev / clicks_prev if clicks_prev > 0 else 0

    # Calculate CTR (Click Through Rate as percentage)
    ctr_current = (clicks_current / impressions_current * 100) if impressions_current > 0 else 0
    ctr_prev = (clicks_prev / impressions_prev * 100) if impressions_prev > 0 else 0

    # Calculate CPM (Cost Per Mille / 1000 impressions)
    cpm_current = (spend_current / impressions_current * 1000) if impressions_current > 0 else 0
    cpm_prev = (spend_prev / impressions_prev * 1000) if impressions_prev > 0 else 0

    # ROAS sparkline - use same time format as other sparklines
    revenue_by_bucket = {p.date: float(p.value or 0) for p in revenue_sparkline}
    spend_by_bucket = {p.date: float(p.value or 0) for p in spend_sparkline}
    roas_sparkline = []
    for bucket in sorted(set(revenue_by_bucket.keys()) & set(spend_by_bucket.keys())):
        spend_val = float(spend_by_bucket[bucket] or 0)
        rev_val = float(revenue_by_bucket[bucket] or 0)
        roas_sparkline.append(SparkPoint(date=bucket, value=(rev_val / spend_val) if spend_val > 0 else 0))

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
            sparkline=conversions_sparkline
        ),
        KpiData(
            key="conversion_value",
            value=conversion_value_current,
            prev=conversion_value_prev,
            delta_pct=_calculate_delta_pct(conversion_value_current, conversion_value_prev),
            sparkline=conversion_value_sparkline
        ),
        KpiData(
            key="clicks",
            value=clicks_current,
            prev=clicks_prev,
            delta_pct=_calculate_delta_pct(clicks_current, clicks_prev),
        ),
        KpiData(
            key="impressions",
            value=impressions_current,
            prev=impressions_prev,
            delta_pct=_calculate_delta_pct(impressions_current, impressions_prev),
        ),
        KpiData(
            key="cpc",
            value=cpc_current,
            prev=cpc_prev,
            delta_pct=_calculate_delta_pct(cpc_current, cpc_prev),
        ),
        KpiData(
            key="ctr",
            value=ctr_current,
            prev=ctr_prev,
            delta_pct=_calculate_delta_pct(ctr_current, ctr_prev),
        ),
        KpiData(
            key="cpm",
            value=cpm_current,
            prev=cpm_prev,
            delta_pct=_calculate_delta_pct(cpm_current, cpm_prev),
        ),
    ]

    # Chart data (merged for Recharts) - include ALL 4 metrics per provider
    # Data format: {date, google_revenue, meta_revenue, google_spend, meta_spend, ...}
    # Also includes totals: {revenue, spend, conversions, roas}

    # Pivot provider data by date
    chart_data_by_date = {}
    for d in chart_data_result:
        if use_intraday:
            date_key = d.time_bucket.isoformat()
        else:
            date_key = str(d.time_bucket)

        if date_key not in chart_data_by_date:
            chart_data_by_date[date_key] = {
                "date": date_key,
                "revenue": 0,
                "conversion_value": 0,
                "spend": 0,
                "conversions": 0,
            }

        provider = d.provider or "unknown"
        spend_val = float(d.spend or 0)
        revenue_val = float(d.revenue or 0)
        conversions_val = float(d.conversions or 0)

        # Per-provider metrics
        chart_data_by_date[date_key][f"{provider}_revenue"] = revenue_val
        chart_data_by_date[date_key][f"{provider}_spend"] = spend_val
        chart_data_by_date[date_key][f"{provider}_conversions"] = conversions_val
        # Per-provider ROAS
        chart_data_by_date[date_key][f"{provider}_roas"] = (revenue_val / spend_val) if spend_val > 0 else 0

        # Aggregate totals
        chart_data_by_date[date_key]["revenue"] += revenue_val
        chart_data_by_date[date_key]["spend"] += spend_val
        chart_data_by_date[date_key]["conversions"] += conversions_val
        chart_data_by_date[date_key]["conversion_value"] += revenue_val

    # Shopify-first revenue: override top-level revenue series with Shopify revenue when connected.
    if has_shopify:
        for point in revenue_sparkline:
            date_key = point.date
            if date_key not in chart_data_by_date:
                chart_data_by_date[date_key] = {
                    "date": date_key,
                    "revenue": 0,
                    "conversion_value": 0,
                    "spend": 0,
                    "conversions": 0,
                }
            shopify_rev = float(point.value or 0)
            chart_data_by_date[date_key]["shopify_revenue"] = shopify_rev
            chart_data_by_date[date_key]["revenue"] = shopify_rev

    # Calculate total ROAS for each date
    chart_data = []
    for date_key in sorted(chart_data_by_date.keys()):
        entry = chart_data_by_date[date_key]
        entry["roas"] = (entry["revenue"] / entry["spend"]) if entry["spend"] > 0 else 0
        chart_data.append(entry)

    data_source = "shopify" if has_shopify else "platform"

    return (
        kpis,
        chart_data,
        data_source,
        chart_granularity,
        data_as_of,
        intraday_available_from,
        intraday_reason_unavailable,
    )


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


    # Get campaign metrics directly from campaign-level snapshots
    # WHY: We now sync campaign-level metrics as SOURCE OF TRUTH
    # No need to roll up from children - campaign metrics are accurate
    # NOTE: Uses metrics_date for accurate day filtering in account timezone
    top_campaigns_sql = text("""
        SELECT
            camp.id,
            camp.name,
            c.provider,
            COALESCE(SUM(sub.spend), 0) as spend,
            COALESCE(SUM(sub.revenue), 0) as revenue
        FROM entities camp
        JOIN connections c ON c.id = camp.connection_id
        JOIN (
            SELECT DISTINCT ON (ms.entity_id, ms.metrics_date)
                ms.entity_id,
                ms.spend,
                ms.revenue
            FROM metric_snapshots ms
            WHERE ms.metrics_date >= :start_date
              AND ms.metrics_date <= :end_date
            ORDER BY ms.entity_id, ms.metrics_date, ms.captured_at DESC
        ) sub ON sub.entity_id = camp.id
        WHERE camp.workspace_id = :workspace_id
          AND camp.level = 'campaign'
          AND camp.status = 'active'
        GROUP BY camp.id, camp.name, c.provider
        HAVING SUM(sub.spend) > 0
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

    # Get spend by provider - latest snapshot per CAMPAIGN entity per day
    # WHY: Campaign-level for accurate totals (same logic as KPIs)
    # NOTE: Uses metrics_date for accurate day filtering in account timezone
    spend_mix_sql = text("""
        SELECT
            provider,
            COALESCE(SUM(spend), 0) as spend
        FROM (
            SELECT DISTINCT ON (ms.entity_id, ms.metrics_date)
                ms.provider,
                ms.spend
            FROM metric_snapshots ms
            JOIN entities e ON e.id = ms.entity_id
            WHERE e.workspace_id = :workspace_id
              AND e.level = 'campaign'
              AND ms.metrics_date >= :start_date
              AND ms.metrics_date <= :end_date
            ORDER BY ms.entity_id, ms.metrics_date, ms.captured_at DESC
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
        description="Time period: today, yesterday, last_7_days, last_30_days, last_90_days"
    ),
    start_date: str = Query(
        default=None,
        description="Custom start date (YYYY-MM-DD). Overrides timeframe if provided with end_date."
    ),
    end_date: str = Query(
        default=None,
        description="Custom end date (YYYY-MM-DD). Overrides timeframe if provided with start_date."
    ),
    platform: str = Query(
        default=None,
        description="Platform filter: google, meta. If not provided, returns blended data."
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

    # Check Shopify connection
    shopify_conn = db.query(Connection).filter(
        Connection.workspace_id == workspace_id,
        Connection.provider == ProviderEnum.shopify,
        Connection.status == "active"
    ).first()
    has_shopify = shopify_conn is not None
    shopify_shop: Optional[ShopifyShop] = None
    if shopify_conn:
        shopify_shop = db.query(ShopifyShop).filter(
            ShopifyShop.connection_id == shopify_conn.id
        ).first()

    # Get connected platforms and determine primary currency + timezone
    ad_connections = db.query(Connection).filter(
        Connection.workspace_id == workspace_id,
        Connection.status == "active",
        Connection.provider != ProviderEnum.shopify
    ).all()
    connected_platforms = [c.provider.value for c in ad_connections if c.provider]

    # Determine reporting currency/timezone.
    # Shopify-first: if Shopify connected, use shop settings for consistent reporting.
    primary_currency = "USD"
    primary_timezone = None  # Ad account timezone (fallback)
    for conn in ad_connections:
        if conn.currency_code and primary_currency == "USD":
            primary_currency = conn.currency_code
        if conn.timezone and not primary_timezone:
            primary_timezone = conn.timezone
            logger.debug("[DASHBOARD] Using account timezone: %s", primary_timezone)

    reporting_timezone = (shopify_shop.timezone if shopify_shop and shopify_shop.timezone else None) or primary_timezone or "UTC"
    reporting_currency = (shopify_shop.currency if shopify_shop and shopify_shop.currency else None) or primary_currency

    # Get date ranges - use custom dates if provided, else use timeframe preset
    # CRITICAL: Use reporting timezone so "today"/"yesterday" aligns with what we show in the UI.
    if start_date and end_date:
        try:
            from datetime import date as date_type
            from zoneinfo import ZoneInfo

            # Parse custom dates in reporting timezone, then convert to UTC
            if reporting_timezone:
                try:
                    tz = ZoneInfo(reporting_timezone)
                except Exception:
                    tz = timezone.utc
                start = datetime.combine(
                    date_type.fromisoformat(start_date),
                    datetime.min.time(),
                    tzinfo=tz
                ).astimezone(timezone.utc)
                end = datetime.combine(
                    date_type.fromisoformat(end_date),
                    datetime.max.time(),
                    tzinfo=tz
                ).astimezone(timezone.utc)
            else:
                start = datetime.combine(
                    date_type.fromisoformat(start_date),
                    datetime.min.time()
                ).replace(tzinfo=timezone.utc)
                end = datetime.combine(
                    date_type.fromisoformat(end_date),
                    datetime.max.time()
                ).replace(tzinfo=timezone.utc)
        except ValueError:
            # Invalid date format - fall back to timeframe
            start, end = _get_date_range(timeframe, reporting_timezone)
    else:
        start, end = _get_date_range(timeframe, reporting_timezone)

    prev_start, prev_end = _get_previous_period(start, end)

    # Fetch all data
    (
        kpis,
        chart_data,
        data_source,
        chart_granularity,
        data_as_of,
        intraday_available_from,
        intraday_reason_unavailable,
    ) = _get_kpis_and_chart_data(
        db, workspace_id, start, end, prev_start, prev_end, has_shopify, timeframe, reporting_timezone, platform
    )

    top_campaigns = _get_top_campaigns(db, workspace_id)
    spend_mix = _get_spend_mix(db, workspace_id, start, end)

    # Provider totals (platform metrics) for reconciliation with ad dashboards.
    # NOTE: Uses metrics_date (platform day) and latest snapshot per entity/day.
    provider_totals: Optional[Dict[str, Dict[str, float]]] = None
    try:
        from sqlalchemy import text
        from zoneinfo import ZoneInfo

        try:
            tz = ZoneInfo(reporting_timezone) if reporting_timezone else timezone.utc
        except Exception:
            tz = timezone.utc

        range_start_date = start.astimezone(tz).date()
        range_end_date = end.astimezone(tz).date()

        provider_totals_sql = text("""
            SELECT
              provider,
              COALESCE(SUM(spend), 0) AS spend,
              COALESCE(SUM(conversions), 0) AS conversions,
              COALESCE(SUM(revenue), 0) AS conversion_value
            FROM (
              SELECT DISTINCT ON (entity_id, metrics_date)
                provider,
                entity_id,
                metrics_date,
                spend,
                conversions,
                revenue
              FROM metric_snapshots
              WHERE entity_id IN (
                SELECT id FROM entities
                WHERE workspace_id = :workspace_id
                  AND level = 'campaign'
              )
              AND metrics_date >= :start_date
              AND metrics_date <= :end_date
              ORDER BY entity_id, metrics_date, captured_at DESC
            ) latest
            GROUP BY provider
        """)

        rows = db.execute(provider_totals_sql, {
            "workspace_id": str(workspace_id),
            "start_date": range_start_date,
            "end_date": range_end_date,
        }).fetchall()

        provider_totals = {
            (r.provider or "unknown"): {
                "spend": float(r.spend or 0),
                "conversions": float(r.conversions or 0),
                "conversion_value": float(r.conversion_value or 0),
            }
            for r in rows
        }
    except Exception as e:
        logger.warning("[DASHBOARD] Failed to compute provider_totals: %s", e)

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

    chart_timezone = reporting_timezone
    data_as_of_str = data_as_of.isoformat() if data_as_of else None
    intraday_available_from_str = (
        intraday_available_from.isoformat() if intraday_available_from else None
    )

    # Wrap top campaigns with disclaimer for drill-down ≠ KPI totals clarity
    top_campaigns_data = TopCampaignsData(
        items=top_campaigns,
        disclaimer="Campaign metrics shown are based on campaign-level data. For Performance Max and Shopping campaigns, individual asset or ad metrics may not sum to campaign totals."
    )

    return UnifiedDashboardResponse(
        kpis=kpis,
        data_source=data_source,
        has_shopify=has_shopify,
        connected_platforms=connected_platforms,
        currency=reporting_currency,
        chart_granularity=chart_granularity,
        chart_timezone=chart_timezone,
        data_as_of=data_as_of_str,
        intraday_available_from=intraday_available_from_str,
        intraday_reason_unavailable=intraday_reason_unavailable,
        chart_data=chart_data,
        top_campaigns=top_campaigns_data,
        spend_mix=spend_mix,
        provider_totals=provider_totals,
        attribution_summary=attribution_summary,
        attribution_feed=attribution_feed,
        last_synced_at=last_synced_at_str
    )
