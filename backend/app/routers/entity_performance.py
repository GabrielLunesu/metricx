"""
Entity Performance Router
=========================

WHAT:
    FastAPI router exposing campaign/ad set performance listings and trends.

WHY:
    The campaigns UI needs a single, well-defined API to fetch paginated
    performance data (spend, revenue, ROAS, etc.), hierarchy metadata, and
    sparkline trends without re-implementing metrics logic in the frontend.

DATA SOURCE:
    Uses MetricSnapshot table (15-min granularity) instead of deprecated MetricFact.
    MetricSnapshot provides real-time data with proper backfill support.

REFERENCES:
    - app/schemas.py::EntityPerformanceResponse (response contract)
    - app/dsl/hierarchy.py (campaign/ad set ancestor CTE helpers)
    - app/models.py::MetricSnapshot (data source)
"""

from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, literal_column, desc, asc, text

from app.deps import get_current_user, get_db
from app import models
from app.dsl.hierarchy import adset_ancestor_cte
from app.schemas import (
    EntityPerformanceResponse,
    EntityPerformanceMeta,
    EntityPerformanceRow,
    EntityTrendPoint,
    PageMeta,
)


router = APIRouter(
    prefix="/entity-performance",
    tags=["Entity Performance"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"},
    },
)


ALLOWED_SORT_KEYS = {"roas", "revenue", "spend", "cpc", "ctr", "conversions"}

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def _resolve_entity_level(level: str) -> models.LevelEnum:
    """Validate and cast entity level string into LevelEnum."""

    try:
        return models.LevelEnum(level)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity level '{level}'. Expected campaign/adset/ad",
        ) from exc


def _date_range(start: Optional[date], end: Optional[date], preset: Optional[str]) -> Tuple[date, date]:
    """
    Resolve query timeframe.

    * preset="7d" → last 7 days including today (matches dashboard.py)
    * preset="30d" → last 30 days including today
    * Otherwise requires explicit start/end (end inclusive).

    IMPORTANT: Returns dates for INCLUSIVE filtering (metrics_date >= start AND metrics_date <= end).
    This matches dashboard.py's behavior and ensures today's data is included.
    """

    today = date.today()
    if preset == "7d":
        # 6 days back + today = 7 days total (matches dashboard.py last_7_days)
        end_date = today
        start_date = end_date - timedelta(days=6)
        return start_date, end_date
    if preset == "30d":
        # 29 days back + today = 30 days total
        end_date = today
        start_date = end_date - timedelta(days=29)
        return start_date, end_date
    if start and end:
        if start > end:
            raise HTTPException(status_code=400, detail="date_start must be before or equal to date_end")
        return start, end
    raise HTTPException(status_code=400, detail="Provide date_start/date_end or timeframe preset")


def _base_query(
    db: Session,
    workspace_id: str,
    level: models.LevelEnum,
    start: date,
    end: date,
    parent_id: Optional[str],
    platform: Optional[str],
    status: Optional[str],
):
    """
    Build core aggregate query for entity performance.

    WHY: We need totals for spend/revenue/clicks etc. aggregated at requested level.

    CRITICAL FIX: Uses DISTINCT ON to get only the LATEST snapshot per entity per day.
    MetricSnapshot stores cumulative values every 15 minutes (up to 96 per day).
    Without DISTINCT ON, we'd sum all snapshots and massively overcount metrics.

    DATA SOURCE: Uses MetricSnapshot (15-min granularity, backfilled 90 days).

    IMPORTANT: Uses LEFT JOIN so entities without snapshots in the date range
    still appear with $0 values. This is critical for newly synced campaigns.
    """

    if level not in (
        models.LevelEnum.campaign,
        models.LevelEnum.adset,
        models.LevelEnum.ad,
        models.LevelEnum.creative,
    ):
        raise HTTPException(status_code=400, detail="Unsupported entity level")

    Connection = models.Connection

    # For campaigns, ads, and creatives - use raw SQL with DISTINCT ON for accuracy
    # This matches dashboard.py's approach
    if level in (models.LevelEnum.campaign, models.LevelEnum.ad, models.LevelEnum.creative):
        entity = aliased(models.Entity)
        connection_alias = aliased(models.Connection)

        # Build platform filter for SQL
        platform_filter = ""
        platform_param = None
        if platform:
            try:
                provider = models.ProviderEnum(platform)
                platform_filter = "AND ls.provider = :platform"
                platform_param = provider.value
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Unsupported platform filter") from exc

        # Use raw SQL subquery for latest snapshots per entity per day
        # WHY: DISTINCT ON is PostgreSQL-specific and gives us exactly one row
        # per (entity_id, metrics_date) - the most recent snapshot for that day
        latest_snapshots_sql = text(f"""
            SELECT
                ls.entity_id,
                COALESCE(SUM(ls.spend), 0) as spend,
                COALESCE(SUM(ls.revenue), 0) as revenue,
                COALESCE(SUM(ls.clicks), 0) as clicks,
                COALESCE(SUM(ls.impressions), 0) as impressions,
                COALESCE(SUM(ls.conversions), 0) as conversions,
                MAX(ls.captured_at) as last_updated
            FROM (
                SELECT DISTINCT ON (ms.entity_id, ms.metrics_date)
                    ms.entity_id,
                    ms.spend,
                    ms.revenue,
                    ms.clicks,
                    ms.impressions,
                    ms.conversions,
                    ms.captured_at,
                    c.provider
                FROM metric_snapshots ms
                JOIN entities e ON e.id = ms.entity_id
                JOIN connections c ON c.id = e.connection_id
                WHERE e.workspace_id = :workspace_id::uuid
                  AND e.level = :level
                  AND ms.metrics_date >= :start_date
                  AND ms.metrics_date <= :end_date
                  {platform_filter}
                ORDER BY ms.entity_id, ms.metrics_date, ms.captured_at DESC
            ) ls
            GROUP BY ls.entity_id
        """)

        # Build params
        params = {
            "workspace_id": workspace_id,
            "level": level.value,
            "start_date": start,
            "end_date": end,
        }
        if platform_param:
            params["platform"] = platform_param

        # Execute raw SQL to get metrics
        metrics_result = db.execute(latest_snapshots_sql, params).fetchall()
        metrics_by_entity = {
            str(row.entity_id): {
                "spend": float(row.spend or 0),
                "revenue": float(row.revenue or 0),
                "clicks": float(row.clicks or 0),
                "impressions": float(row.impressions or 0),
                "conversions": float(row.conversions or 0),
                "last_updated": row.last_updated,
            }
            for row in metrics_result
        }

        # Now query entities with their metadata
        query = (
            db.query(
                entity.id.label("entity_id"),
                entity.name.label("entity_name"),
                entity.status,
                connection_alias.provider.label("provider"),
            )
            .select_from(entity)
            .join(connection_alias, connection_alias.id == entity.connection_id)
            .filter(entity.workspace_id == workspace_id)
            .filter(entity.level == level)
        )

        if platform:
            query = query.filter(connection_alias.provider == provider)

        if status and status.lower() != "all":
            query = query.filter(entity.status == status)

        if parent_id and level != models.LevelEnum.campaign:
            if isinstance(parent_id, str):
                try:
                    parent_uuid = uuid.UUID(parent_id)
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail="Invalid parent_id format") from exc
            else:
                parent_uuid = parent_id
            query = query.filter(entity.parent_id == parent_uuid)

        # Return a special wrapper that combines entity query with pre-fetched metrics
        return _EntityMetricsQueryWrapper(query, metrics_by_entity)

    else:
        # For adsets, use hierarchy CTEs to roll up from leaf entities
        # WHY: AdSet-level snapshots may not exist; need to aggregate from ads
        # This path is less common and can be optimized later if needed
        leaf = aliased(models.Entity)
        ancestor = aliased(models.Entity)
        connection_alias = aliased(models.Connection)
        mapping = adset_ancestor_cte(db)
        MS = models.MetricSnapshot

        # For adsets, we still need DISTINCT ON but it's more complex
        # Use a subquery approach
        latest_leaf_snapshots = (
            db.query(
                MS.entity_id,
                MS.metrics_date,
                MS.spend,
                MS.revenue,
                MS.clicks,
                MS.impressions,
                MS.conversions,
                MS.captured_at,
            )
            .filter(MS.metrics_date >= start)
            .filter(MS.metrics_date <= end)
            .distinct(MS.entity_id, MS.metrics_date)
            .order_by(MS.entity_id, MS.metrics_date, MS.captured_at.desc())
            .subquery("latest_snapshots")
        )

        query = (
            db.query(
                ancestor.id.label("entity_id"),
                ancestor.name.label("entity_name"),
                ancestor.status,
                connection_alias.provider.label("provider"),
                func.max(latest_leaf_snapshots.c.captured_at).label("last_updated"),
                func.coalesce(func.sum(latest_leaf_snapshots.c.spend), 0).label("spend"),
                func.coalesce(func.sum(latest_leaf_snapshots.c.revenue), 0).label("revenue"),
                func.coalesce(func.sum(latest_leaf_snapshots.c.clicks), 0).label("clicks"),
                func.coalesce(func.sum(latest_leaf_snapshots.c.impressions), 0).label("impressions"),
                func.coalesce(func.sum(latest_leaf_snapshots.c.conversions), 0).label("conversions"),
            )
            .select_from(ancestor)
            .join(connection_alias, connection_alias.id == ancestor.connection_id)
            .join(mapping, mapping.c.ancestor_id == ancestor.id)
            .join(leaf, leaf.id == mapping.c.leaf_id)
            .filter(leaf.level.in_([models.LevelEnum.ad, models.LevelEnum.creative]))
            .outerjoin(latest_leaf_snapshots,
                latest_leaf_snapshots.c.entity_id == leaf.id
            )
            .filter(ancestor.workspace_id == workspace_id)
            .filter(ancestor.level == models.LevelEnum.adset)
        )

        if platform:
            try:
                provider = models.ProviderEnum(platform)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Unsupported platform filter") from exc
            query = query.filter(connection_alias.provider == provider)

        if status and status.lower() != "all":
            query = query.filter(ancestor.status == status)

        if parent_id:
            if isinstance(parent_id, str):
                try:
                    parent_uuid = uuid.UUID(parent_id)
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail="Invalid parent_id format") from exc
            else:
                parent_uuid = parent_id
            query = query.filter(ancestor.parent_id == parent_uuid)

        group_columns = [
            ancestor.id,
            ancestor.name,
            ancestor.status,
            connection_alias.provider,
        ]

        return query.group_by(*group_columns)


class _EntityMetricsQueryWrapper:
    """
    Wrapper that combines an entity query with pre-fetched metrics.

    WHY: For campaigns/ads, we fetch metrics using raw SQL (DISTINCT ON)
    for accuracy, then combine with entity metadata from ORM query.
    This class provides a query-like interface for the rest of the code.
    """

    def __init__(self, entity_query, metrics_by_entity: dict):
        self._entity_query = entity_query
        self._metrics_by_entity = metrics_by_entity
        self._sort_by = "revenue"
        self._sort_dir = "desc"
        self._offset = 0
        self._limit = None

    def count(self):
        """Count total entities matching the query."""
        return self._entity_query.count()

    def set_sort(self, sort_by: str, sort_dir: str):
        """Set sort parameters for Python-based sorting."""
        self._sort_by = sort_by
        self._sort_dir = sort_dir

    def order_by(self, *args):
        """Compatibility method - sorting is done via set_sort."""
        return self

    def offset(self, n):
        """Store offset for later use."""
        self._offset = n
        return self

    def limit(self, n):
        """Store limit for later use."""
        self._limit = n
        return self

    def all(self):
        """Execute query and return results with metrics."""
        # Get entities
        entities = self._entity_query.all()

        # Build result rows combining entity data with metrics
        results = []
        for ent in entities:
            entity_id = str(ent.entity_id)
            metrics = self._metrics_by_entity.get(entity_id, {})

            # Create a result object that matches the expected interface
            results.append(_EntityMetricsRow(
                entity_id=ent.entity_id,
                entity_name=ent.entity_name,
                status=ent.status,
                provider=ent.provider,
                spend=metrics.get("spend", 0),
                revenue=metrics.get("revenue", 0),
                clicks=metrics.get("clicks", 0),
                impressions=metrics.get("impressions", 0),
                conversions=metrics.get("conversions", 0),
                last_updated=metrics.get("last_updated"),
            ))

        # Apply sorting based on sort_by and sort_dir
        reverse = self._sort_dir == "desc"

        def get_sort_key(row):
            if self._sort_by == "revenue":
                return row.revenue or 0
            elif self._sort_by == "spend":
                return row.spend or 0
            elif self._sort_by == "conversions":
                return row.conversions or 0
            elif self._sort_by == "cpc":
                # CPC = spend / clicks
                return (row.spend / row.clicks) if row.clicks and row.clicks > 0 else 0
            elif self._sort_by == "ctr":
                # CTR = clicks / impressions
                return (row.clicks / row.impressions) if row.impressions and row.impressions > 0 else 0
            else:  # roas
                # ROAS = revenue / spend
                return (row.revenue / row.spend) if row.spend and row.spend > 0 else 0

        results.sort(key=get_sort_key, reverse=reverse)

        # Apply pagination
        if self._offset:
            results = results[self._offset:]
        if self._limit:
            results = results[:self._limit]

        return results


class _EntityMetricsRow:
    """Row object matching the expected interface from SQLAlchemy query results."""

    def __init__(self, entity_id, entity_name, status, provider, spend, revenue,
                 clicks, impressions, conversions, last_updated):
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.status = status
        self.provider = provider
        self.spend = spend
        self.revenue = revenue
        self.clicks = clicks
        self.impressions = impressions
        self.conversions = conversions
        self.last_updated = last_updated


def _apply_sort(query, sort_by: str, sort_dir: str):
    """
    Apply sorting to aggregated query results.

    Handles both regular SQLAlchemy queries and _EntityMetricsQueryWrapper.

    IMPORTANT: PostgreSQL requires ORDER BY expressions in aggregate queries
    to either be in GROUP BY or be aggregate functions themselves.
    We use the aggregate expressions directly here.
    """
    sort_by = (sort_by or "roas").lower()
    sort_dir = (sort_dir or "desc").lower()
    if sort_by not in ALLOWED_SORT_KEYS:
        sort_by = "roas"

    # Handle _EntityMetricsQueryWrapper - set sort params for Python-based sorting
    if isinstance(query, _EntityMetricsQueryWrapper):
        query.set_sort(sort_by, sort_dir)
        return query

    # Use MetricSnapshot instead of deprecated MetricFact
    MS = models.MetricSnapshot

    # Build order expressions using the same aggregates as in SELECT
    # This matches PostgreSQL's requirement for GROUP BY queries
    if sort_by == "revenue":
        order_clause = func.coalesce(func.sum(MS.revenue), 0)
    elif sort_by == "spend":
        order_clause = func.coalesce(func.sum(MS.spend), 0)
    elif sort_by == "conversions":
        order_clause = func.coalesce(func.sum(MS.conversions), 0)
    elif sort_by == "cpc":
        # CPC = spend / clicks (nullsafe)
        order_clause = func.coalesce(func.sum(MS.spend), 0) / func.nullif(func.coalesce(func.sum(MS.clicks), 0), 0)
    elif sort_by == "ctr":
        # CTR = clicks / impressions (nullsafe)
        order_clause = func.coalesce(func.sum(MS.clicks), 0) / func.nullif(func.coalesce(func.sum(MS.impressions), 0), 0)
    else:  # roas
        # ROAS = revenue / spend (nullsafe)
        order_clause = func.coalesce(func.sum(MS.revenue), 0) / func.nullif(func.coalesce(func.sum(MS.spend), 0), 0)

    if sort_dir == "asc":
        return query.order_by(asc(order_clause))
    return query.order_by(desc(order_clause))


def _fetch_trend(
    db: Session,
    entity_ids: List[uuid.UUID],
    metric: str,
    start: date,
    end: date,
    level: models.LevelEnum,
) -> dict[str, List[EntityTrendPoint]]:
    """
    Build trend series for entities.

    WHY: Frontend sparkline expects aligned daily values.

    CRITICAL FIX: Uses DISTINCT ON to get only the LATEST snapshot per entity per day.
    Without this, we'd sum all 15-min snapshots and massively overcount.

    DATA SOURCE: Uses MetricSnapshot (15-min granularity).
    """

    # Calculate number of days (inclusive)
    days = (end - start).days + 1
    if days <= 0 or not entity_ids:
        return {}

    # Convert entity_ids to strings for SQL
    entity_id_strs = [str(eid) for eid in entity_ids]

    # For campaigns, ads, and creatives - use raw SQL with DISTINCT ON
    if level in (models.LevelEnum.ad, models.LevelEnum.creative, models.LevelEnum.campaign):
        # Use raw SQL with DISTINCT ON to get latest snapshot per entity per day
        trend_sql = text("""
            SELECT
                entity_id,
                metrics_date as bucket_date,
                spend,
                revenue,
                clicks,
                impressions,
                conversions
            FROM (
                SELECT DISTINCT ON (ms.entity_id, ms.metrics_date)
                    ms.entity_id,
                    ms.metrics_date,
                    ms.spend,
                    ms.revenue,
                    ms.clicks,
                    ms.impressions,
                    ms.conversions
                FROM metric_snapshots ms
                WHERE ms.entity_id = ANY(:entity_ids::uuid[])
                  AND ms.metrics_date >= :start_date
                  AND ms.metrics_date <= :end_date
                ORDER BY ms.entity_id, ms.metrics_date, ms.captured_at DESC
            ) latest
        """)

        results = db.execute(trend_sql, {
            "entity_ids": entity_id_strs,
            "start_date": start,
            "end_date": end,
        }).fetchall()
    else:
        # For adsets, use hierarchy CTEs to roll up from leaf entities
        # This is more complex - use a subquery approach
        leaf = aliased(models.Entity)
        mapping = adset_ancestor_cte(db)
        MS = models.MetricSnapshot

        # Create subquery for latest snapshots per leaf entity per day
        latest_leaf_snapshots = (
            db.query(
                MS.entity_id,
                MS.metrics_date,
                MS.spend,
                MS.revenue,
                MS.clicks,
                MS.impressions,
                MS.conversions,
            )
            .filter(MS.metrics_date >= start)
            .filter(MS.metrics_date <= end)
            .distinct(MS.entity_id, MS.metrics_date)
            .order_by(MS.entity_id, MS.metrics_date, MS.captured_at.desc())
            .subquery("latest_snapshots")
        )

        results = (
            db.query(
                mapping.c.ancestor_id.label("entity_id"),
                latest_leaf_snapshots.c.metrics_date.label("bucket_date"),
                func.coalesce(func.sum(latest_leaf_snapshots.c.spend), 0).label("spend"),
                func.coalesce(func.sum(latest_leaf_snapshots.c.revenue), 0).label("revenue"),
                func.coalesce(func.sum(latest_leaf_snapshots.c.clicks), 0).label("clicks"),
                func.coalesce(func.sum(latest_leaf_snapshots.c.impressions), 0).label("impressions"),
                func.coalesce(func.sum(latest_leaf_snapshots.c.conversions), 0).label("conversions"),
            )
            .select_from(latest_leaf_snapshots)
            .join(leaf, leaf.id == latest_leaf_snapshots.c.entity_id)
            .filter(leaf.level.in_([models.LevelEnum.ad, models.LevelEnum.creative]))
            .join(mapping, mapping.c.leaf_id == leaf.id)
            .filter(mapping.c.ancestor_id.in_(entity_ids))
            .group_by(mapping.c.ancestor_id, latest_leaf_snapshots.c.metrics_date)
            .all()
        )

    buckets_by_entity: dict[str, dict[date, dict]] = {}
    for row in results:
        key = str(row.entity_id)
        buckets_by_entity.setdefault(key, {})[row.bucket_date] = {
            "spend": float(row.spend or 0),
            "revenue": float(row.revenue or 0),
            "clicks": float(row.clicks or 0),
            "impressions": float(row.impressions or 0),
            "conversions": float(row.conversions or 0),
        }

    series: dict[str, List[EntityTrendPoint]] = {}
    metric_key = "revenue" if metric == "revenue" else "roas"
    for entity_id in entity_ids:
        key = str(entity_id)
        values: List[EntityTrendPoint] = []
        day_cursor = start
        for _ in range(days):
            day_totals = buckets_by_entity.get(key, {}).get(day_cursor)
            if day_totals:
                if metric_key == "roas":
                    spend = day_totals.get("spend") or 0
                    revenue = day_totals.get("revenue") or 0
                    value = revenue / spend if spend > 0 else None
                else:
                    value = day_totals.get("revenue")
            else:
                value = 0 if metric_key == "revenue" else None
            values.append(EntityTrendPoint(date=day_cursor.isoformat(), value=value))
            day_cursor += timedelta(days=1)
        series[key] = values
    return series


def _connection_platform_map(db: Session, workspace_id: str) -> dict[str, str]:
    """Map connection_id → provider value for quick lookup."""

    rows = (
        db.query(models.Connection.id, models.Connection.provider)
        .filter(models.Connection.workspace_id == workspace_id)
        .all()
    )
    return {str(r.id): r.provider.value for r in rows}


@router.get("/list", response_model=EntityPerformanceResponse)
def list_entities_performance(
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    entity_level: str = Query(..., description="campaign|adset"),
    parent_id: Optional[str] = Query(None, description="Parent entity id for ad sets/ads"),
    date_start: Optional[date] = Query(None),
    date_end: Optional[date] = Query(None),
    timeframe: Optional[str] = Query("7d", description="quick preset: 7d/30d"),
    platform: Optional[str] = Query(None, description="Provider filter"),
    status: Optional[str] = Query("active", description="Entity status or 'all'"),
    sort_by: str = Query("roas"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """
    WHAT: Returns paginated performance rows for campaigns/ad sets.

    WHY: Frontend campaigns list and detail pages use this data source exclusively.
    """

    workspace_id = str(current_user.workspace_id)
    level = _resolve_entity_level(entity_level)
    # Allow campaign, adset, and ad levels

    start, end = _date_range(date_start, date_end, timeframe)
    base = _base_query(
        db=db,
        workspace_id=workspace_id,
        level=level,
        start=start,
        end=end,
        parent_id=parent_id,
        platform=platform,
        status=status,
    )

    total = base.count()
    sorted_query = _apply_sort(base, sort_by, sort_dir)
    rows = sorted_query.offset((page - 1) * page_size).limit(page_size).all()

    if not rows:
        meta = EntityPerformanceMeta(
            title="Campaigns" if level == models.LevelEnum.campaign else "Ad Sets",
            level=level.value,
            last_updated_at=None,
        )
        return EntityPerformanceResponse(
            meta=meta,
            pagination=PageMeta(total=total, page=page, page_size=page_size),
            rows=[],
        )

    trend_metric = "revenue" if sort_by == "revenue" else "roas"
    entity_ids = [row.entity_id for row in rows]
    trend_series = _fetch_trend(db, entity_ids, trend_metric, start, end, level)

    response_rows: List[EntityPerformanceRow] = []
    # For campaign rows, determine a simple kind label (e.g., PMax) based on children
    kind_by_entity: dict[str, str] = {}
    if level == models.LevelEnum.campaign and rows:
        campaign_ids = [row.entity_id for row in rows]
        adset_alias = aliased(models.Entity)
        creative_alias = aliased(models.Entity)
        creative_campaigns = (
            db.query(adset_alias.parent_id)
            .join(creative_alias, creative_alias.parent_id == adset_alias.id)
            .filter(adset_alias.parent_id.in_(campaign_ids))
            .filter(creative_alias.level == models.LevelEnum.creative)
            .distinct()
            .all()
        )
        for cid_row in creative_campaigns:
            if cid_row[0]:
                kind_by_entity[str(cid_row[0])] = "PMax"

    for row in rows:
        spend = float(row.spend or 0)
        revenue = float(row.revenue or 0)
        clicks = float(row.clicks or 0)
        impressions = float(row.impressions or 0)
        conversions = float(row.conversions or 0)
        roas = revenue / spend if spend > 0 else None
        cpc = spend / clicks if clicks > 0 else None
        ctr_pct = (clicks / impressions * 100) if impressions > 0 else None
        response_rows.append(
            EntityPerformanceRow(
                id=str(row.entity_id),
                name=row.entity_name,
                platform=row.provider.value if row.provider else None,
                revenue=revenue,
                spend=spend,
                roas=roas,
                conversions=conversions,
                cpc=cpc,
                ctr_pct=ctr_pct,
                status=row.status,
                last_updated_at=row.last_updated,
                trend=trend_series.get(str(row.entity_id), []),
                trend_metric="revenue" if trend_metric == "revenue" else "roas",
                kind_label=kind_by_entity.get(str(row.entity_id)) if level == models.LevelEnum.campaign else None,
            )
        )

    latest_update = max((row.last_updated_at for row in response_rows if row.last_updated_at), default=None)
    if level == models.LevelEnum.campaign:
        title = "Campaigns"
    elif level == models.LevelEnum.adset:
        title = "Ad Sets"
    elif level == models.LevelEnum.creative:
        title = "Creatives"
    else:
        title = "Ads"
    meta = EntityPerformanceMeta(title=title, level=level.value, last_updated_at=latest_update)

    return EntityPerformanceResponse(
        meta=meta,
        pagination=PageMeta(total=total, page=page, page_size=page_size),
        rows=response_rows,
    )


@router.get("/{entity_id}/children", response_model=EntityPerformanceResponse)
def list_child_entities(
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    entity_id: str,
    date_start: Optional[date] = Query(None),
    date_end: Optional[date] = Query(None),
    timeframe: Optional[str] = Query("7d"),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query("active"),
    sort_by: str = Query("roas"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """Return performance rows for child level (campaign → ad sets)."""

    db_entity = db.query(models.Entity).filter(models.Entity.id == entity_id).first()
    if not db_entity or str(db_entity.workspace_id) != str(current_user.workspace_id):
        raise HTTPException(status_code=404, detail="Entity not found")

    if db_entity.level == models.LevelEnum.campaign:
        child_level = models.LevelEnum.adset
    else:
        # Prefer creative level if creatives exist under this adset (PMax)
        has_creatives = (
            db.query(models.Entity.id)
            .filter(models.Entity.parent_id == db_entity.id)
            .filter(models.Entity.level == models.LevelEnum.creative)
            .limit(1)
            .first()
        )
        child_level = models.LevelEnum.creative if has_creatives else models.LevelEnum.ad
    start, end = _date_range(date_start, date_end, timeframe)

    base = _base_query(
        db=db,
        workspace_id=str(current_user.workspace_id),
        level=child_level,
        start=start,
        end=end,
        parent_id=db_entity.id,
        platform=platform,
        status=status,
    )

    total = base.count()
    rows = _apply_sort(base, sort_by, sort_dir).offset((page - 1) * page_size).limit(page_size).all()

    trend_metric = "revenue" if sort_by == "revenue" else "roas"
    entity_ids = [row.entity_id for row in rows]
    trend_series = _fetch_trend(db, entity_ids, trend_metric, start, end, child_level)

    response_rows = []
    for row in rows:
        spend = float(row.spend or 0)
        revenue = float(row.revenue or 0)
        clicks = float(row.clicks or 0)
        impressions = float(row.impressions or 0)
        conversions = float(row.conversions or 0)
        roas = revenue / spend if spend > 0 else None
        cpc = spend / clicks if clicks > 0 else None
        ctr_pct = (clicks / impressions * 100) if impressions > 0 else None
        response_rows.append(
            EntityPerformanceRow(
                id=str(row.entity_id),
                name=row.entity_name,
                platform=row.provider.value if row.provider else None,
                revenue=revenue,
                spend=spend,
                roas=roas,
                conversions=conversions,
                cpc=cpc,
                ctr_pct=ctr_pct,
                status=row.status,
                last_updated_at=row.last_updated,
                trend=trend_series.get(str(row.entity_id), []),
                trend_metric="revenue" if trend_metric == "revenue" else "roas",
            )
        )

    latest_update = max((row.last_updated_at for row in response_rows if row.last_updated_at), default=None)
    # Title reflects child level: Ad Sets / Ads / Creatives
    if child_level == models.LevelEnum.adset:
        title = "Ad Sets"
    elif child_level == models.LevelEnum.creative:
        title = "Creatives"
    else:
        title = "Ads"
    meta = EntityPerformanceMeta(title=title, level=child_level.value, last_updated_at=latest_update)

    return EntityPerformanceResponse(
        meta=meta,
        pagination=PageMeta(total=total, page=page, page_size=page_size),
        rows=response_rows,
    )
