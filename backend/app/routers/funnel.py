"""Conversion Funnel Endpoint.

WHAT:
    Combines platform metrics (impressions, clicks from MetricSnapshot) with
    pixel events (page_viewed → product_viewed → ATC → checkout_started →
    checkout_completed from PixelEvent) into a unified conversion funnel.

WHY:
    Users need to see the full funnel from impression to purchase in one view,
    with drop-off rates between each stage. This competes directly with Triple
    Whale's funnel visualization.

DESIGN:
    - Platform metrics (top of funnel): DISTINCT ON latest snapshot per entity
      per day to avoid inflation from cumulative 15-min snapshots.
    - Pixel events (mid/bottom funnel): Simple COUNT GROUP BY event_type.
    - Response returns ordered stages with counts and stage-to-stage rates.

REFERENCES:
    - app/routers/analytics.py (DISTINCT ON pattern for MetricSnapshot)
    - app/routers/attribution.py (workspace permission pattern)
    - app/models.py: MetricSnapshot, PixelEvent, Entity
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, PixelEvent
from app.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class FunnelStage(BaseModel):
    """A single stage in the conversion funnel.

    WHAT: Represents one step (e.g. 'Impressions', 'Page Views') with its count,
          the drop-off rate from the previous stage, and the conversion rate
          from the previous stage.
    """
    key: str = Field(..., description="Stage identifier: impressions, clicks, page_viewed, etc.")
    label: str = Field(..., description="Human-readable label for the stage")
    count: int = Field(0, description="Total events/metrics for this stage")
    rate_from_previous: Optional[float] = Field(
        None,
        description="Conversion rate from the previous stage (0-100). None for first stage.",
    )
    drop_off: Optional[int] = Field(
        None,
        description="Absolute drop-off from the previous stage. None for first stage.",
    )


class FunnelKpi(BaseModel):
    """Highlight KPI derived from the funnel."""
    key: str
    label: str
    value: str
    description: str


class FunnelResponse(BaseModel):
    """Full funnel response combining platform metrics and pixel events.

    WHAT: Ordered list of funnel stages + highlight KPIs
    WHY: Frontend renders a horizontal bar visualization and KPI cards
    """
    stages: List[FunnelStage]
    kpis: List[FunnelKpi]
    period_days: int
    generated_at: str


# =============================================================================
# CONSTANTS
# =============================================================================

# Ordered funnel stages from top to bottom
FUNNEL_STAGE_ORDER = [
    ("impressions", "Impressions"),
    ("clicks", "Clicks"),
    ("page_viewed", "Page Views"),
    ("product_viewed", "Product Views"),
    ("product_added_to_cart", "Add to Cart"),
    ("checkout_started", "Checkout Started"),
    ("checkout_completed", "Purchases"),
]


# =============================================================================
# HELPERS
# =============================================================================

def _get_platform_metrics(
    db: Session,
    workspace_id: UUID,
    start_date,
    end_date,
    entity_id: Optional[UUID] = None,
) -> dict:
    """Fetch aggregated impressions and clicks from MetricSnapshot.

    WHAT: Gets latest snapshot per entity per day, then sums across entities.
    WHY: MetricSnapshot has multiple rows per entity per day (15-min syncs
         with cumulative totals). DISTINCT ON avoids ~30x inflation.

    When entity_id is provided, the query scopes to that entity and all its
    descendants (e.g. a campaign's adsets and ads, or just one ad). This uses
    a recursive CTE to walk the entity hierarchy.

    Args:
        db: Database session
        workspace_id: Workspace UUID
        start_date: Start date for the period
        end_date: End date for the period
        entity_id: Optional entity UUID to scope the funnel to

    Returns:
        Dict with 'impressions' and 'clicks' totals
    """
    if entity_id:
        # Recursive CTE: get entity + all descendants, then fetch their snapshots
        sql = text("""
            WITH RECURSIVE entity_tree AS (
                SELECT id FROM entities
                WHERE id = :entity_id AND workspace_id = :workspace_id
                UNION ALL
                SELECT e.id FROM entities e
                INNER JOIN entity_tree et ON e.parent_id = et.id
            ),
            latest_snapshots AS (
                SELECT DISTINCT ON (ms.entity_id, ms.metrics_date)
                    ms.entity_id,
                    ms.impressions,
                    ms.clicks
                FROM metric_snapshots ms
                WHERE ms.entity_id IN (SELECT id FROM entity_tree)
                  AND ms.metrics_date >= :start_date
                  AND ms.metrics_date <= :end_date
                ORDER BY ms.entity_id, ms.metrics_date, ms.captured_at DESC
            )
            SELECT
                COALESCE(SUM(impressions), 0) as total_impressions,
                COALESCE(SUM(clicks), 0) as total_clicks
            FROM latest_snapshots
        """)
        params = {
            "workspace_id": str(workspace_id),
            "entity_id": str(entity_id),
            "start_date": start_date,
            "end_date": end_date,
        }
    else:
        # Workspace-level: campaign-level entities only (avoids double counting)
        sql = text("""
            WITH latest_snapshots AS (
                SELECT DISTINCT ON (ms.entity_id, ms.metrics_date)
                    ms.entity_id,
                    ms.impressions,
                    ms.clicks
                FROM metric_snapshots ms
                INNER JOIN entities e ON e.id = ms.entity_id
                WHERE e.workspace_id = :workspace_id
                  AND e.level = 'campaign'
                  AND ms.metrics_date >= :start_date
                  AND ms.metrics_date <= :end_date
                ORDER BY ms.entity_id, ms.metrics_date, ms.captured_at DESC
            )
            SELECT
                COALESCE(SUM(impressions), 0) as total_impressions,
                COALESCE(SUM(clicks), 0) as total_clicks
            FROM latest_snapshots
        """)
        params = {
            "workspace_id": str(workspace_id),
            "start_date": start_date,
            "end_date": end_date,
        }

    result = db.execute(sql, params).fetchone()

    return {
        "impressions": int(result.total_impressions) if result else 0,
        "clicks": int(result.total_clicks) if result else 0,
    }


def _get_pixel_event_counts(db: Session, workspace_id: UUID, since: datetime) -> dict:
    """Fetch pixel event counts grouped by event_type.

    WHAT: Counts each event type in PixelEvent for the workspace
    WHY: These represent mid-to-bottom funnel stages tracked by the Shopify pixel

    Args:
        db: Database session
        workspace_id: Workspace UUID
        since: Start datetime to count from

    Returns:
        Dict mapping event_type → count
    """
    rows = (
        db.query(
            PixelEvent.event_type,
            func.count(PixelEvent.id).label("count"),
        )
        .filter(
            PixelEvent.workspace_id == workspace_id,
            PixelEvent.created_at >= since,
        )
        .group_by(PixelEvent.event_type)
        .all()
    )

    return {row.event_type: row.count for row in rows}


def _build_funnel_stages(platform_metrics: dict, pixel_counts: dict) -> List[FunnelStage]:
    """Combine platform metrics and pixel events into ordered funnel stages.

    WHAT: Merges two data sources into a single ordered funnel
    WHY: Users see the full journey from impression to purchase

    Args:
        platform_metrics: Dict with 'impressions' and 'clicks'
        pixel_counts: Dict mapping event_type → count

    Returns:
        List of FunnelStage objects in order
    """
    # Merge data sources into a single count map
    counts = {
        "impressions": platform_metrics.get("impressions", 0),
        "clicks": platform_metrics.get("clicks", 0),
        "page_viewed": pixel_counts.get("page_viewed", 0),
        "product_viewed": pixel_counts.get("product_viewed", 0),
        "product_added_to_cart": pixel_counts.get("product_added_to_cart", 0),
        "checkout_started": pixel_counts.get("checkout_started", 0),
        "checkout_completed": pixel_counts.get("checkout_completed", 0),
    }

    stages = []
    prev_count = None

    for key, label in FUNNEL_STAGE_ORDER:
        count = counts.get(key, 0)

        rate = None
        drop = None
        if prev_count is not None and prev_count > 0:
            rate = round((count / prev_count) * 100, 1)
            drop = prev_count - count

        stages.append(FunnelStage(
            key=key,
            label=label,
            count=count,
            rate_from_previous=rate,
            drop_off=drop,
        ))

        prev_count = count

    return stages


def _build_funnel_kpis(stages: List[FunnelStage]) -> List[FunnelKpi]:
    """Derive highlight KPIs from the funnel stages.

    WHAT: Computes ATC rate, checkout rate, and purchase rate
    WHY: Quick-glance metrics below the funnel visualization

    Args:
        stages: Ordered list of funnel stages

    Returns:
        List of FunnelKpi objects
    """
    stage_map = {s.key: s.count for s in stages}

    page_views = stage_map.get("page_viewed", 0)
    atc = stage_map.get("product_added_to_cart", 0)
    checkout_started = stage_map.get("checkout_started", 0)
    purchases = stage_map.get("checkout_completed", 0)

    kpis = []

    # ATC Rate: Add to Cart / Page Views
    atc_rate = (atc / page_views * 100) if page_views > 0 else 0
    kpis.append(FunnelKpi(
        key="atc_rate",
        label="ATC Rate",
        value=f"{atc_rate:.1f}%",
        description="Visitors who added to cart",
    ))

    # Checkout Rate: Checkout Started / ATC
    checkout_rate = (checkout_started / atc * 100) if atc > 0 else 0
    kpis.append(FunnelKpi(
        key="checkout_rate",
        label="Checkout Rate",
        value=f"{checkout_rate:.1f}%",
        description="Cart visitors who started checkout",
    ))

    # Purchase Rate: Purchases / Checkout Started
    purchase_rate = (purchases / checkout_started * 100) if checkout_started > 0 else 0
    kpis.append(FunnelKpi(
        key="purchase_rate",
        label="Purchase Rate",
        value=f"{purchase_rate:.1f}%",
        description="Checkouts that completed",
    ))

    return kpis


# =============================================================================
# TIMEFRAME PARSING
# =============================================================================

def _parse_funnel_timeframe(timeframe: str) -> int:
    """Convert timeframe string to number of days.

    Args:
        timeframe: One of 'last_7_days', 'last_14_days', 'last_30_days', 'last_90_days'

    Returns:
        Number of days
    """
    mapping = {
        "today": 1,
        "yesterday": 1,
        "last_7_days": 7,
        "last_14_days": 14,
        "last_30_days": 30,
        "last_90_days": 90,
    }
    return mapping.get(timeframe, 30)


# =============================================================================
# MAIN ENDPOINT
# =============================================================================

@router.get("/funnel", response_model=FunnelResponse)
def get_funnel(
    workspace_id: UUID = Query(..., description="Workspace UUID"),
    timeframe: str = Query(
        "last_30_days",
        description="Period: today, yesterday, last_7_days, last_14_days, last_30_days, last_90_days",
    ),
    entity_id: Optional[UUID] = Query(
        None,
        description="Optional entity UUID (campaign, ad set, or ad) to scope the funnel to. "
                    "When provided, impressions/clicks are filtered to this entity and its "
                    "descendants. Currently supported for Meta entities.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get conversion funnel data combining platform metrics and pixel events.

    WHAT: Returns ordered funnel stages (impressions → purchases) with drop-off
          rates, plus highlight KPIs (ATC rate, checkout rate, purchase rate).
    WHY: Users need to see where visitors drop off in the buying journey.

    Supports optional entity_id to scope the funnel to a specific campaign,
    ad set, or ad (Meta only for now). When filtering by entity, platform
    metrics (impressions, clicks) are scoped to that entity and its
    descendants using a recursive CTE. Pixel events remain workspace-wide
    since they aren't tied to specific ad entities.

    Args:
        workspace_id: Workspace UUID
        timeframe: Period preset
        entity_id: Optional entity to scope the funnel to
        db: Database session
        current_user: Authenticated user

    Returns:
        FunnelResponse with stages and KPIs

    Raises:
        HTTPException 403 if user doesn't have workspace access
    """
    # Verify workspace access
    if current_user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied to this workspace")

    # Calculate date range
    days = _parse_funnel_timeframe(timeframe)
    now = datetime.now(timezone.utc)
    today = now.date()
    start_date = today - timedelta(days=days - 1)
    since_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)

    # Fetch both data sources
    platform_metrics = _get_platform_metrics(
        db, workspace_id, start_date, today, entity_id=entity_id,
    )
    pixel_counts = _get_pixel_event_counts(db, workspace_id, since_dt)

    # Build funnel
    stages = _build_funnel_stages(platform_metrics, pixel_counts)
    kpis = _build_funnel_kpis(stages)

    logger.info(
        f"[FUNNEL] workspace={workspace_id} timeframe={timeframe} "
        f"entity_id={entity_id} "
        f"impressions={platform_metrics.get('impressions', 0)} "
        f"purchases={pixel_counts.get('checkout_completed', 0)}"
    )

    return FunnelResponse(
        stages=stages,
        kpis=kpis,
        period_days=days,
        generated_at=now.isoformat(),
    )
