"""
Entity Performance Router
=========================

WHAT:
    FastAPI router exposing campaign/ad set performance listings and trends.

WHY:
    The campaigns UI needs a single, well-defined API to fetch paginated
    performance data (spend, revenue, ROAS, etc.), hierarchy metadata, and
    sparkline trends without re-implementing metrics logic in the frontend.

REFERENCES:
    - app/schemas.py::EntityPerformanceResponse (response contract)
    - app/dsl/hierarchy.py (campaign/ad set ancestor CTE helpers)
    - docs/ADNAVI_BUILD_LOG.md (Campaigns integration section)
"""

from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, literal_column, desc, asc

from app.deps import get_current_user, get_db
from app import models
from app.dsl.hierarchy import campaign_ancestor_cte, adset_ancestor_cte
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

    * preset="7d" → last 7 days ending yesterday
    * preset="30d" → last 30 days ending yesterday
    * Otherwise requires explicit start/end (end exclusive).
    """

    today = date.today()
    if preset == "7d":
        end_date = today
        start_date = end_date - timedelta(days=7)
        return start_date, end_date
    if preset == "30d":
        end_date = today
        start_date = end_date - timedelta(days=30)
        return start_date, end_date
    if start and end:
        if start >= end:
            raise HTTPException(status_code=400, detail="date_start must be before date_end")
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
    HOW: Start from Entity, LEFT JOIN MetricFact to include entities without metrics.
    
    IMPORTANT: Uses LEFT JOIN so entities without metric facts in the date range
    still appear with $0 values. This is critical for newly synced campaigns.
    """

    if level not in (
        models.LevelEnum.campaign,
        models.LevelEnum.adset,
        models.LevelEnum.ad,
        models.LevelEnum.creative,
    ):
        raise HTTPException(status_code=400, detail="Unsupported entity level")

    MF = models.MetricFact
    Connection = models.Connection
    
    connection_alias = None

    # For leaf levels (ads/creatives), start from Entity and LEFT JOIN MetricFact
    if level in (models.LevelEnum.ad, models.LevelEnum.creative):
        entity = aliased(models.Entity)
        connection_alias = aliased(models.Connection)
        query = (
            db.query(
                entity.id.label("entity_id"),
                entity.name.label("entity_name"),
                entity.status,
                func.coalesce(func.max(MF.provider), connection_alias.provider).label("provider"),  # Get provider from connection if no facts
                func.max(MF.ingested_at).label("last_updated"),
                func.coalesce(func.sum(MF.spend), 0).label("spend"),
                func.coalesce(func.sum(MF.revenue), 0).label("revenue"),
                func.coalesce(func.sum(MF.clicks), 0).label("clicks"),
                func.coalesce(func.sum(MF.impressions), 0).label("impressions"),
                func.coalesce(func.sum(MF.conversions), 0).label("conversions"),
            )
            .select_from(entity)
            .join(connection_alias, connection_alias.id == entity.connection_id)
            .outerjoin(MF, 
                (MF.entity_id == entity.id) &
                (func.date(MF.event_date) >= start) &
                (func.date(MF.event_date) < end)
            )
            .filter(entity.workspace_id == workspace_id)
            .filter(entity.level == level)
        )
    else:
        # For campaigns and adsets, use hierarchy CTEs
        # Start from ancestor entities, LEFT JOIN through hierarchy to MetricFact
        leaf = aliased(models.Entity)
        ancestor = aliased(models.Entity)
        connection_alias = aliased(models.Connection)
        mapping = campaign_ancestor_cte(db) if level == models.LevelEnum.campaign else adset_ancestor_cte(db)

        query = (
            db.query(
                ancestor.id.label("entity_id"),
                ancestor.name.label("entity_name"),
                ancestor.status,
                func.coalesce(func.max(MF.provider), connection_alias.provider).label("provider"),  # Get provider from connection if no facts
                func.max(MF.ingested_at).label("last_updated"),
                func.coalesce(func.sum(MF.spend), 0).label("spend"),
                func.coalesce(func.sum(MF.revenue), 0).label("revenue"),
                func.coalesce(func.sum(MF.clicks), 0).label("clicks"),
                func.coalesce(func.sum(MF.impressions), 0).label("impressions"),
                func.coalesce(func.sum(MF.conversions), 0).label("conversions"),
            )
            .select_from(ancestor)
            .join(connection_alias, connection_alias.id == ancestor.connection_id)
            .join(mapping, mapping.c.ancestor_id == ancestor.id)
            .join(leaf, leaf.id == mapping.c.leaf_id)
            .outerjoin(MF,
                (MF.entity_id == leaf.id) &
                (func.date(MF.event_date) >= start) &
                (func.date(MF.event_date) < end)
            )
            .filter(ancestor.workspace_id == workspace_id)
            .filter(ancestor.level == level)
        )

    # Apply filters - use the appropriate entity alias
    entity_alias = entity if level in (models.LevelEnum.ad, models.LevelEnum.creative) else ancestor
    
    if platform:
        try:
            provider = models.ProviderEnum(platform)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Unsupported platform filter") from exc
        # Filter by connection provider (works for both entities with and without facts)
        if level == models.LevelEnum.ad:
            query = query.filter(connection_alias.provider == provider)
        else:
            query = query.filter(connection_alias.provider == provider)

    if status and status.lower() != "all":
        query = query.filter(entity_alias.status == status)

    if parent_id and level != models.LevelEnum.campaign:
        # parent_id can be either a string or UUID object
        if isinstance(parent_id, str):
            try:
                parent_uuid = uuid.UUID(parent_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid parent_id format") from exc
        else:
            parent_uuid = parent_id
        query = query.filter(entity_alias.parent_id == parent_uuid)

    group_columns = [
        entity_alias.id,
        entity_alias.name,
        entity_alias.status,
    ]
    
    # Add provider to group_by - use connection provider since we're joining it
    group_columns.append(connection_alias.provider)

    return query.group_by(*group_columns)


def _apply_sort(query, sort_by: str, sort_dir: str):
    """
    Apply sorting to aggregated query results.
    
    IMPORTANT: PostgreSQL requires ORDER BY expressions in aggregate queries
    to either be in GROUP BY or be aggregate functions themselves.
    We use the aggregate expressions directly here.
    """
    sort_by = (sort_by or "roas").lower()
    sort_dir = (sort_dir or "desc").lower()
    if sort_by not in ALLOWED_SORT_KEYS:
        sort_by = "roas"

    # Build order expressions using the same aggregates as in SELECT
    # This matches PostgreSQL's requirement for GROUP BY queries
    if sort_by == "revenue":
        order_clause = func.coalesce(func.sum(models.MetricFact.revenue), 0)
    elif sort_by == "spend":
        order_clause = func.coalesce(func.sum(models.MetricFact.spend), 0)
    elif sort_by == "conversions":
        order_clause = func.coalesce(func.sum(models.MetricFact.conversions), 0)
    elif sort_by == "cpc":
        # CPC = spend / clicks (nullsafe)
        order_clause = func.coalesce(func.sum(models.MetricFact.spend), 0) / func.nullif(func.coalesce(func.sum(models.MetricFact.clicks), 0), 0)
    elif sort_by == "ctr":
        # CTR = clicks / impressions (nullsafe)
        order_clause = func.coalesce(func.sum(models.MetricFact.clicks), 0) / func.nullif(func.coalesce(func.sum(models.MetricFact.impressions), 0), 0)
    else:  # roas
        # ROAS = revenue / spend (nullsafe)
        order_clause = func.coalesce(func.sum(models.MetricFact.revenue), 0) / func.nullif(func.coalesce(func.sum(models.MetricFact.spend), 0), 0)

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
    HOW: Accumulate day totals and normalize to requested metric.
    """

    days = (end - start).days
    if days <= 0 or not entity_ids:
        return {}

    MF = models.MetricFact
    
    # For ads (leaf level), query MetricFacts directly
    if level == models.LevelEnum.ad:
        results = (
            db.query(
                MF.entity_id.label("entity_id"),
                func.date(MF.event_date).label("bucket_date"),
                func.coalesce(func.sum(MF.spend), 0).label("spend"),
                func.coalesce(func.sum(MF.revenue), 0).label("revenue"),
                func.coalesce(func.sum(MF.clicks), 0).label("clicks"),
                func.coalesce(func.sum(MF.impressions), 0).label("impressions"),
                func.coalesce(func.sum(MF.conversions), 0).label("conversions"),
            )
            .select_from(MF)
            .filter(MF.entity_id.in_(entity_ids))
            .filter(func.date(MF.event_date) >= start)
            .filter(func.date(MF.event_date) < end)
            .group_by(MF.entity_id, func.date(MF.event_date))
            .all()
        )
    else:
        # For campaigns and adsets, use hierarchy CTEs
        leaf = aliased(models.Entity)
        mapping = campaign_ancestor_cte(db) if level == models.LevelEnum.campaign else adset_ancestor_cte(db)

        results = (
            db.query(
                mapping.c.ancestor_id.label("entity_id"),
                func.date(MF.event_date).label("bucket_date"),
                func.coalesce(func.sum(MF.spend), 0).label("spend"),
                func.coalesce(func.sum(MF.revenue), 0).label("revenue"),
                func.coalesce(func.sum(MF.clicks), 0).label("clicks"),
                func.coalesce(func.sum(MF.impressions), 0).label("impressions"),
                func.coalesce(func.sum(MF.conversions), 0).label("conversions"),
            )
            .select_from(MF)
            .join(leaf, leaf.id == MF.entity_id)
            .join(mapping, mapping.c.leaf_id == leaf.id)
            .filter(mapping.c.ancestor_id.in_(entity_ids))
            .filter(func.date(MF.event_date) >= start)
            .filter(func.date(MF.event_date) < end)
            .group_by(mapping.c.ancestor_id, func.date(MF.event_date))
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
