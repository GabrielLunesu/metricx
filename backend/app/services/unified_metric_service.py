"""
Unified Metric Service
=====================

Single source of truth for all metric calculations across the system.
Powers QA, KPI, entity performance, finance, and metrics endpoints.

WHAT: Centralized metric aggregation service
WHY: Eliminates data mismatches between endpoints
HOW: Uses existing metrics registry with consistent filtering

Design Principles:
- Single source of truth for all metric calculations
- Consistent filtering logic across all endpoints
- Workspace-scoped security at SQL level
- Built-in divide-by-zero guards
- Standardized input/output contracts

Usage:
    >>> service = UnifiedMetricService(db)
    >>> result = service.get_summary(
    ...     workspace_id="...",
    ...     metrics=["roas", "cpc"],
    ...     time_range=TimeRange(last_n_days=7),
    ...     filters=MetricFilters()
    ... )
    >>> print(result.metrics["roas"].value)
    6.29

References:
- app/metrics/registry.py: Metric formulas and dependencies
- app/metrics/formulas.py: Pure calculation functions
- app/models.py: Database models (MetricSnapshot, Entity)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, cast, Date, desc, asc

from app import models
from app.metrics.registry import compute_metric, get_required_bases, is_base_measure
from app.dsl.schema import TimeRange
from app.dsl.hierarchy import campaign_ancestor_cte, adset_ancestor_cte

logger = logging.getLogger(__name__)


@dataclass
class MetricFilters:
    """
    Standardized filter contract for all metric queries.
    
    Default behavior: Include ALL entities unless explicitly filtered.
    This matches the Finance page behavior where inactive campaigns
    still generated revenue and should be included.
    """
    provider: Optional[str] = None
    level: Optional[str] = None
    status: Optional[str] = None  # None = include all, "active" = active only
    entity_ids: Optional[List[str]] = None
    entity_name: Optional[str] = None
    metric_filters: Optional[List[Dict[str, Any]]] = None
    
    def normalize_provider(self) -> Optional[str]:
        """
        Normalize provider enum format to string.
        
        Handles both "meta" and "ProviderEnum.meta" formats.
        """
        if not self.provider:
            return None
        if self.provider.startswith("ProviderEnum."):
            return self.provider.split(".")[1]
        return self.provider


@dataclass
class MetricValue:
    """Single metric value with optional comparison."""
    value: Optional[float]
    previous: Optional[float] = None
    delta_pct: Optional[float] = None


@dataclass
class MetricSummary:
    """Summary results for multiple metrics."""
    metrics: Dict[str, MetricValue]
    workspace_avg: Optional[float] = None


@dataclass
class MetricTimePoint:
    """Single time point in a timeseries."""
    date: str
    value: Optional[float]


@dataclass
class MetricBreakdownItem:
    """Single item in a breakdown result.

    Includes optional creative fields for ad-level breakdowns (Meta only).
    """
    label: str
    value: Optional[float]
    spend: Optional[float] = None
    clicks: Optional[float] = None
    conversions: Optional[float] = None
    revenue: Optional[float] = None
    impressions: Optional[float] = None
    entity_id: Optional[str] = None  # For entity timeseries lookup (multi-line charts)
    # Creative fields (ad-level only, Meta only for now)
    thumbnail_url: Optional[str] = None
    image_url: Optional[str] = None
    media_type: Optional[str] = None  # "image", "video", "carousel", "unknown"




class UnifiedMetricService:
    """
    Unified metric aggregation service.

    Single source of truth for all metric calculations across the system.
    Ensures consistent filtering, calculations, and results.

    NOTE: As of 2025-12-07, this service queries from metric_snapshots table
    (15-min granularity) instead of metric_facts (daily granularity).
    The snapshot table uses 'captured_at' instead of 'event_date'.
    """

    def __init__(self, db: Session, use_snapshots: bool = True):
        """Initialize the service.

        Args:
            db: Database session
            use_snapshots: Always True - uses MetricSnapshot table (15-min granularity).
                          MetricFact is deprecated.
        """
        self.db = db
        self.use_snapshots = use_snapshots

        # Always use MetricSnapshot (MetricFact is deprecated)
        self.MF = models.MetricSnapshot
        self.date_field = models.MetricSnapshot.captured_at

        self.E = models.Entity
    
    def get_summary(
        self,
        workspace_id: str,
        metrics: List[str],
        time_range: TimeRange,
        filters: MetricFilters,
        compare_to_previous: bool = False
    ) -> MetricSummary:
        """
        Get summary values for multiple metrics.
        
        Args:
            workspace_id: Workspace UUID for scoping
            metrics: List of metric names to calculate
            time_range: Time range for calculation
            filters: Filtering criteria
            compare_to_previous: Include previous period comparison
            
        Returns:
            MetricSummary with all requested metrics
            
        Example:
            >>> service = UnifiedMetricService(db)
            >>> result = service.get_summary(
            ...     workspace_id="...",
            ...     metrics=["roas", "cpc"],
            ...     time_range=TimeRange(last_n_days=7),
            ...     filters=MetricFilters()
            ... )
            >>> print(result.metrics["roas"].value)
            6.29
        """
        logger.info(f"[UNIFIED_METRICS] Getting summary for {len(metrics)} metrics: {metrics}")
        logger.info(f"[UNIFIED_METRICS] Time range: {time_range}")
        logger.info(f"[UNIFIED_METRICS] Filters: provider={filters.provider}, level={filters.level}, status={filters.status}, entity_name={filters.entity_name}")
        
        # Resolve time range
        start_date, end_date = self._resolve_time_range(time_range)
        logger.info(f"[UNIFIED_METRICS] Resolved dates: {start_date} to {end_date}")
        
        # Get current period totals
        current_totals = self._get_base_totals(
            workspace_id, start_date, end_date, filters
        )
        logger.info(f"[UNIFIED_METRICS] Current period totals: {current_totals}")
        
        # Get previous period totals if requested
        previous_totals = None
        if compare_to_previous:
            prev_start, prev_end = self._get_previous_period(start_date, end_date)
            logger.info(f"[UNIFIED_METRICS] Previous period dates: {prev_start} to {prev_end}")
            previous_totals = self._get_base_totals(
                workspace_id, prev_start, prev_end, filters
            )
            logger.info(f"[UNIFIED_METRICS] Previous period totals: {previous_totals}")
        
        # Calculate all requested metrics
        metric_results = {}
        for metric_name in metrics:
            current_value = compute_metric(metric_name, current_totals)
            previous_value = None
            delta_pct = None
            
            if previous_totals:
                previous_value = compute_metric(metric_name, previous_totals)
                if previous_value is not None and previous_value != 0 and current_value is not None:
                    delta_pct = (current_value - previous_value) / previous_value
            
            metric_results[metric_name] = MetricValue(
                value=current_value,
                previous=previous_value,
                delta_pct=delta_pct
            )
        
        # Calculate workspace average for primary metric
        workspace_avg = None
        if metrics:
            workspace_avg = self.get_workspace_average(
                workspace_id, metrics[0], time_range
            )
        
        logger.info(f"[UNIFIED_METRICS] Calculated metrics: {metric_results}")
        logger.info(f"[UNIFIED_METRICS] Workspace average: {workspace_avg}")
        
        return MetricSummary(
            metrics=metric_results,
            workspace_avg=workspace_avg
        )
    
    def get_timeseries(
        self,
        workspace_id: str,
        metrics: List[str],
        time_range: TimeRange,
        filters: MetricFilters,
        granularity: str = "day",
        include_previous: bool = False
    ) -> Dict[str, List[MetricTimePoint]]:
        """
        Get timeseries data for metrics.
        
        Args:
            workspace_id: Workspace UUID for scoping
            metrics: List of metric names to calculate
            time_range: Time range for calculation
            filters: Filtering criteria
            granularity: 'day' or 'hour'
            include_previous: When True, also returns previous-period timeseries keyed as "<metric>_previous"
            
        Returns:
            Dictionary mapping metric name to list of time points
        """
        logger.info(f"[UNIFIED_METRICS] Getting timeseries for {len(metrics)} metrics (granularity={granularity})")
        
        # Resolve time range
        start_date, end_date = self._resolve_time_range(time_range)
        
        # Determine grouping expression
        if granularity == "hour":
            # For hourly, we group by the full datetime (truncated to hour if needed, 
            # but assuming seed data is already hourly aligned or we want raw timestamps)
            # In SQLite/Postgres, we might need specific functions. 
            # For now, assuming event_date is already the bucket or we group by it directly.
            # If using Postgres: func.date_trunc('hour', self.MF.event_date)
            # But to be safe across DBs (and since seed data is clean), let's try grouping by event_date directly
            # if it's hourly. Or better, use a conditional.
            # Let's stick to simple grouping for now.
            time_bucket = self.date_field
        else:
            time_bucket = cast(self.date_field, Date)

        # Build timeseries query
        # For hourly granularity, we need to handle datetime filtering differently
        if granularity == "hour":
            # Convert dates to datetime for proper hour-level filtering
            from datetime import datetime as dt, time
            start_datetime = dt.combine(start_date, time.min)  # Start at 00:00:00
            end_datetime = dt.combine(end_date, time.max)      # End at 23:59:59
            
            query = (
                self.db.query(
                    time_bucket.label("date"),
                    func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
                    func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
                    func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
                    func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
                    func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
                    func.coalesce(func.sum(self.MF.leads), 0).label("leads"),
                    func.coalesce(func.sum(self.MF.installs), 0).label("installs"),
                    func.coalesce(func.sum(self.MF.purchases), 0).label("purchases"),
                    func.coalesce(func.sum(self.MF.visitors), 0).label("visitors"),
                    func.coalesce(func.sum(self.MF.profit), 0).label("profit"),
                )
                .join(self.E, self.E.id == self.MF.entity_id)
                .filter(self.E.workspace_id == workspace_id)
                .filter(self.date_field.between(start_datetime, end_datetime))
                .group_by(time_bucket)
                .order_by(time_bucket)
            )
        else:
            query = (
                self.db.query(
                    time_bucket.label("date"),
                    func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
                    func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
                    func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
                    func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
                    func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
                    func.coalesce(func.sum(self.MF.leads), 0).label("leads"),
                    func.coalesce(func.sum(self.MF.installs), 0).label("installs"),
                    func.coalesce(func.sum(self.MF.purchases), 0).label("purchases"),
                    func.coalesce(func.sum(self.MF.visitors), 0).label("visitors"),
                    func.coalesce(func.sum(self.MF.profit), 0).label("profit"),
                )
                .join(self.E, self.E.id == self.MF.entity_id)
                .filter(self.E.workspace_id == workspace_id)
                .filter(cast(self.date_field, Date).between(start_date, end_date))
                .group_by(time_bucket)
                .order_by(time_bucket)
            )
        
        # Apply filters
        query = self._apply_filters(query, filters, workspace_id)
        
        # Execute query
        rows = query.all()
        
        # Build timeseries results for EACH metric
        results = {m: [] for m in metrics}
        
        for row in rows:
            totals = row._asdict()
            
            for metric in metrics:
                value = compute_metric(metric, totals)
                
                # Format date string based on granularity
                date_str = str(row.date)
                if granularity == "hour" and isinstance(row.date, datetime):
                    date_str = row.date.isoformat()
                
                results[metric].append(MetricTimePoint(
                    date=date_str,
                    value=value
                ))
        # Previous-period window
        if include_previous:
            days = (end_date - start_date).days + 1
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date - timedelta(days=days - 1)

            if granularity == "hour":
                from datetime import datetime as dt, time
                prev_start_datetime = dt.combine(prev_start_date, time.min)
                prev_end_datetime = dt.combine(prev_end_date, time.max)
                prev_query = (
                    self.db.query(
                        self.date_field.label("date"),
                        func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
                        func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
                        func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
                        func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
                        func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
                        func.coalesce(func.sum(self.MF.leads), 0).label("leads"),
                        func.coalesce(func.sum(self.MF.installs), 0).label("installs"),
                        func.coalesce(func.sum(self.MF.purchases), 0).label("purchases"),
                        func.coalesce(func.sum(self.MF.visitors), 0).label("visitors"),
                        func.coalesce(func.sum(self.MF.profit), 0).label("profit"),
                    )
                    .join(self.E, self.E.id == self.MF.entity_id)
                    .filter(self.E.workspace_id == workspace_id)
                    .filter(self.date_field.between(prev_start_datetime, prev_end_datetime))
                    .group_by(self.date_field)
                    .order_by(self.date_field)
                )
            else:
                prev_query = (
                    self.db.query(
                        cast(self.date_field, Date).label("date"),
                        func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
                        func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
                        func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
                        func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
                        func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
                        func.coalesce(func.sum(self.MF.leads), 0).label("leads"),
                        func.coalesce(func.sum(self.MF.installs), 0).label("installs"),
                        func.coalesce(func.sum(self.MF.purchases), 0).label("purchases"),
                        func.coalesce(func.sum(self.MF.visitors), 0).label("visitors"),
                        func.coalesce(func.sum(self.MF.profit), 0).label("profit"),
                    )
                    .join(self.E, self.E.id == self.MF.entity_id)
                    .filter(self.E.workspace_id == workspace_id)
                    .filter(cast(self.date_field, Date).between(prev_start_date, prev_end_date))
                    .group_by(cast(self.date_field, Date))
                    .order_by(cast(self.date_field, Date))
                )

            prev_query = self._apply_filters(prev_query, filters, workspace_id)
            prev_rows = prev_query.all()

            for metric in metrics:
                prev_points: List[MetricTimePoint] = []
                for row in prev_rows:
                    totals = row._asdict()
                    value = compute_metric(metric, totals)
                    date_str = str(row.date)
                    if granularity == "hour" and isinstance(row.date, datetime):
                        date_str = row.date.isoformat()
                    prev_points.append(MetricTimePoint(date=date_str, value=value))
                results[f"{metric}_previous"] = prev_points

        return results

    def get_entity_timeseries(
        self,
        workspace_id: str,
        metric: str,
        time_range: TimeRange,
        entity_ids: List[str],
        entity_labels: Dict[str, str],
        granularity: str = "day"
    ) -> List[Dict[str, Any]]:
        """
        Get timeseries data for multiple entities (for multi-line charts).

        WHY: When user asks "graph of top 5 ads", we need one line per entity
        showing how each performed over time.

        Args:
            workspace_id: Workspace UUID for scoping
            metric: Metric name to calculate
            time_range: Time range for calculation
            entity_ids: List of entity UUIDs to fetch timeseries for
            entity_labels: Mapping of entity_id -> display label (name)
            granularity: 'day' or 'hour'

        Returns:
            List of dicts with structure:
            [
                {
                    "entity_id": "uuid-1",
                    "entity_name": "Summer Sale",
                    "timeseries": [{"date": "2025-11-20", "value": 123.45}, ...]
                },
                ...
            ]
        """
        logger.info(f"[UNIFIED_METRICS] Getting entity timeseries for {len(entity_ids)} entities")

        # Resolve time range
        start_date, end_date = self._resolve_time_range(time_range)

        # Determine time bucket expression
        time_bucket = cast(self.date_field, Date) if granularity == "day" else self.date_field

        # Build query that groups by BOTH entity_id AND date
        query = (
            self.db.query(
                self.MF.entity_id.label("entity_id"),
                time_bucket.label("date"),
                func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
                func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
                func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
                func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
                func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
                func.coalesce(func.sum(self.MF.leads), 0).label("leads"),
                func.coalesce(func.sum(self.MF.installs), 0).label("installs"),
                func.coalesce(func.sum(self.MF.purchases), 0).label("purchases"),
                func.coalesce(func.sum(self.MF.visitors), 0).label("visitors"),
                func.coalesce(func.sum(self.MF.profit), 0).label("profit"),
            )
            .join(self.E, self.E.id == self.MF.entity_id)
            .filter(self.E.workspace_id == workspace_id)
            .filter(self.MF.entity_id.in_(entity_ids))
            .filter(cast(self.date_field, Date).between(start_date, end_date))
            .group_by(self.MF.entity_id, time_bucket)
            .order_by(self.MF.entity_id, time_bucket)
        )

        rows = query.all()

        # Group results by entity
        entity_data: Dict[str, List[Dict[str, Any]]] = {eid: [] for eid in entity_ids}

        for row in rows:
            totals = row._asdict()
            entity_id = str(totals.pop("entity_id"))
            value = compute_metric(metric, totals)
            date_str = str(totals.get("date"))

            if entity_id in entity_data:
                entity_data[entity_id].append({
                    "date": date_str,
                    "value": float(value) if value is not None else 0
                })

        # Build final result with labels
        results = []
        for entity_id in entity_ids:
            results.append({
                "entity_id": entity_id,
                "entity_name": entity_labels.get(entity_id, "Unknown"),
                "timeseries": entity_data.get(entity_id, [])
            })

        logger.info(f"[UNIFIED_METRICS] Built entity timeseries for {len(results)} entities")
        return results

    def get_breakdown(
        self,
        workspace_id: str,
        metric: str,
        time_range: TimeRange,
        filters: MetricFilters,
        breakdown_dimension: str,
        top_n: int = 5,
        sort_order: str = "desc"
    ) -> List[MetricBreakdownItem]:
        """
        Get breakdown results for a metric by dimension.
        
        Args:
            workspace_id: Workspace UUID for scoping
            metric: Metric name to calculate
            time_range: Time range for calculation
            filters: Filtering criteria
            breakdown_dimension: Dimension to group by (provider, campaign, adset, ad)
            top_n: Number of top results to return
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            List of breakdown items
            
        Example:
            >>> service = UnifiedMetricService(db)
            >>> breakdown = service.get_breakdown(
            ...     workspace_id="...",
            ...     metric="roas",
            ...     time_range=TimeRange(last_n_days=7),
            ...     filters=MetricFilters(),
            ...     breakdown_dimension="campaign"
            ... )
            >>> print(breakdown[0].label)
            Summer Sale Campaign
        """
        logger.info(f"[UNIFIED_METRICS] Getting breakdown for {metric} by {breakdown_dimension}")
        logger.info(f"[UNIFIED_METRICS] Time range: {time_range}")
        logger.info(f"[UNIFIED_METRICS] Filters: provider={filters.provider}, level={filters.level}, status={filters.status}, entity_name={filters.entity_name}")
        logger.info(f"[UNIFIED_METRICS] Top N: {top_n}, Sort order: {sort_order}")
        
        # Resolve time range
        start_date, end_date = self._resolve_time_range(time_range)
        logger.info(f"[UNIFIED_METRICS] Resolved dates: {start_date} to {end_date}")
        
        # Special handling: named entity + same-level breakdown → route to child-level
        query = None
        if filters.entity_name and breakdown_dimension in ["campaign", "adset", "ad"]:
            named_entity = self._resolve_entity_by_name(workspace_id, filters.entity_name)
            if named_entity is not None and named_entity.level == breakdown_dimension:
                child_level_map = {"campaign": "adset", "adset": "ad", "ad": "ad"}
                child_level = child_level_map.get(breakdown_dimension)
                logger.info(
                    f"[UNIFIED_METRICS] Routing named-entity same-level breakdown to child level: {breakdown_dimension}→{child_level}"
                )
                query = self._build_hierarchy_entity_breakdown_query(
                    workspace_id=workspace_id,
                    start_date=start_date,
                    end_date=end_date,
                    named_entity=named_entity,
                    child_level=child_level,
                    filters=filters,
                )

        # Regular path
        if query is None:
            if breakdown_dimension == "provider":
                query = self._build_provider_breakdown_query(
                    workspace_id, start_date, end_date, filters
                )
            elif breakdown_dimension in ["campaign", "adset", "ad"]:
                query = self._build_entity_breakdown_query(
                    workspace_id, start_date, end_date, filters, breakdown_dimension
                )
            else:
                raise ValueError(f"Unsupported breakdown dimension: {breakdown_dimension}")
        
        # Apply ordering and limit
        if sort_order == "asc":
            query = query.order_by(asc(self._get_order_expression(metric)))
        else:
            query = query.order_by(desc(self._get_order_expression(metric)))
        
        # Execute query to get all results first
        rows = query.all()
        
        # Build breakdown results
        breakdown = []
        for row in rows:
            totals = row._asdict()
            value = compute_metric(metric, totals)
            
            # Apply metric filters if specified
            if filters.metric_filters:
                if not self._passes_metric_filters(metric, value, filters.metric_filters):
                    continue
            
            # Extract creative fields if available (ad-level only, Meta only)
            thumbnail_url = totals.get("thumbnail_url")
            image_url = totals.get("image_url")
            media_type_val = totals.get("media_type")
            # Convert enum to string if needed
            media_type = media_type_val.value if hasattr(media_type_val, 'value') else (str(media_type_val) if media_type_val else None)

            breakdown.append(MetricBreakdownItem(
                label=str(row.group_name),
                value=value,
                spend=totals.get("spend"),
                clicks=totals.get("clicks"),
                conversions=totals.get("conversions"),
                revenue=totals.get("revenue"),
                impressions=totals.get("impressions"),
                entity_id=str(totals.get("entity_id")) if totals.get("entity_id") else None,
                thumbnail_url=thumbnail_url,
                image_url=image_url,
                media_type=media_type,
            ))
        
        # Apply top_n limit after filtering
        return breakdown[:top_n]
    
    def get_workspace_average(
        self,
        workspace_id: str,
        metric: str,
        time_range: TimeRange
    ) -> Optional[float]:
        """
        Get workspace-wide average for a metric.
        
        CRITICAL: This method does NOT apply any filters from the original query.
        It calculates the metric across ALL entities in the workspace to provide
        a true baseline for comparison.
        
        Args:
            workspace_id: Workspace UUID for scoping
            metric: Metric name to calculate
            time_range: Time range for calculation
            
        Returns:
            Workspace average value, or None if cannot compute
            
        Example:
            >>> service = UnifiedMetricService(db)
            >>> avg = service.get_workspace_average(
            ...     workspace_id="...",
            ...     metric="roas",
            ...     time_range=TimeRange(last_n_days=7)
            ... )
            >>> print(avg)
            6.29
        """
        logger.info(f"[UNIFIED_METRICS] Getting workspace average for {metric}")
        
        # Resolve time range
        start_date, end_date = self._resolve_time_range(time_range)
        
        # Get required base measures for this metric
        dependencies = get_required_bases(metric)
        if not dependencies:
            logger.warning(f"[UNIFIED_METRICS] Unknown metric: {metric}")
            return None
        
        # Build query for ALL entities (no filters except workspace and time)
        query = (
            self.db.query(
                *[func.coalesce(func.sum(getattr(self.MF, dep)), 0).label(dep) 
                  for dep in dependencies]
            )
            .join(self.E, self.E.id == self.MF.entity_id)
            .filter(self.E.workspace_id == workspace_id)
            .filter(cast(self.date_field, Date).between(start_date, end_date))
        )
        
        # Execute query
        row = query.first()
        if not row:
            logger.warning(f"[UNIFIED_METRICS] No data found for workspace {workspace_id}")
            return None
        
        # Compute metric
        base_measures = {dep: getattr(row, dep) or 0 for dep in dependencies}
        workspace_avg = compute_metric(metric, base_measures)
        
        logger.info(f"[UNIFIED_METRICS] Workspace average for {metric}: {workspace_avg}")
        return workspace_avg
    
    def _resolve_time_range(self, time_range: TimeRange) -> tuple[date, date]:
        """Resolve TimeRange to start/end dates."""
        if time_range.start and time_range.end:
            return (time_range.start, time_range.end)
        
        n = time_range.last_n_days or 7
        end_date = date.today()
        start_date = end_date - timedelta(days=n - 1)
        return (start_date, end_date)
    
    def _get_previous_period(self, start_date: date, end_date: date) -> tuple[date, date]:
        """Calculate previous period dates."""
        period_length = (end_date - start_date).days + 1
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_length - 1)
        return (prev_start, prev_end)
    
    def _get_base_totals(
        self,
        workspace_id: str,
        start_date: date,
        end_date: date,
        filters: MetricFilters
    ) -> Dict[str, float]:
        """Get aggregated base measures for a time period."""
        query = (
            self.db.query(
                func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
                func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
                func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
                func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
                func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
                func.coalesce(func.sum(self.MF.leads), 0).label("leads"),
                func.coalesce(func.sum(self.MF.installs), 0).label("installs"),
                func.coalesce(func.sum(self.MF.purchases), 0).label("purchases"),
                func.coalesce(func.sum(self.MF.visitors), 0).label("visitors"),
                func.coalesce(func.sum(self.MF.profit), 0).label("profit"),
            )
            .join(self.E, self.E.id == self.MF.entity_id)
            .filter(self.E.workspace_id == workspace_id)
            .filter(cast(self.date_field, Date).between(start_date, end_date))
        )
        
        # Apply filters
        query = self._apply_filters(query, filters, workspace_id)
        
        # Execute query
        row = query.first()
        if not row:
            return {}
        
        return row._asdict()
    
    def _resolve_entity_name_to_descendants(self, workspace_id: str, entity_name: str) -> Optional[List[str]]:
        """
        Resolve entity name to descendant entity IDs using hierarchy CTEs.
        
        When a user queries by entity name (e.g., "Product Launch Teaser campaign"),
        we need to roll up metrics from all descendant entities, NOT include the
        parent entity's own fact (which might be stale).
        
        Args:
            workspace_id: Workspace UUID for scoping
            entity_name: Name of the entity to resolve
            
        Returns:
            List of descendant entity IDs (UUIDs), or None if entity not found
            
        Example:
            >>> service._resolve_entity_name_to_descendants(workspace_id, "Product Launch Teaser")
            ['adset-id-1', 'adset-id-2', 'ad-id-1', 'ad-id-2', ...]
            
        References:
        - app/dsl/hierarchy.py: campaign_ancestor_cte, adset_ancestor_cte
        """
        logger.info(f"[UNIFIED_METRICS] Resolving entity name: '{entity_name}'")
        
        # Find the entity by name
        entity = (
            self.db.query(self.E)
            .filter(self.E.workspace_id == workspace_id)
            .filter(self.E.name.ilike(f"%{entity_name}%"))
            .first()
        )
        
        if not entity:
            logger.warning(f"[UNIFIED_METRICS] Entity not found: '{entity_name}'")
            return None
        
        logger.info(f"[UNIFIED_METRICS] Found entity: {entity.name} (ID: {entity.id}, Level: {entity.level})")
        
        # If it's an ad (leaf level), return just the entity itself
        if entity.level == "ad":
            logger.info(f"[UNIFIED_METRICS] Entity is ad level, returning itself only")
            return [str(entity.id)]
        
        # Use hierarchy CTE to find all descendants
        if entity.level == "campaign":
            mapping_cte = campaign_ancestor_cte(self.db)
            logger.info(f"[UNIFIED_METRICS] Using campaign hierarchy CTE")
        elif entity.level == "adset":
            mapping_cte = adset_ancestor_cte(self.db)
            logger.info(f"[UNIFIED_METRICS] Using adset hierarchy CTE")
        else:
            logger.warning(f"[UNIFIED_METRICS] Unknown entity level: {entity.level}")
            return [str(entity.id)]
        
        # Find all leaf entities that roll up to this ancestor
        descendants = (
            self.db.query(mapping_cte.c.leaf_id)
            .filter(mapping_cte.c.ancestor_id == entity.id)
            .all()
        )
        
        descendant_ids = [str(row.leaf_id) for row in descendants]
        logger.info(f"[UNIFIED_METRICS] Found {len(descendant_ids)} descendants for {entity.name}")
        
        # CRITICAL: Exclude the parent entity itself from descendants
        # We only want facts from children, not the parent's own fact
        if str(entity.id) in descendant_ids:
            descendant_ids.remove(str(entity.id))
            logger.info(f"[UNIFIED_METRICS] Excluded parent entity {entity.id} from descendants")
        
        logger.info(f"[UNIFIED_METRICS] Returning {len(descendant_ids)} descendant IDs for rollup")
        return descendant_ids
    
    def _apply_filters(self, query, filters: MetricFilters, workspace_id: str = None):
        """
        Apply filters to a query.
        
        Args:
            query: SQLAlchemy query object
            filters: MetricFilters object with filter criteria
            workspace_id: Workspace UUID (required for entity_name hierarchy resolution)
        """
        # Provider filter
        if filters.provider:
            provider_value = filters.normalize_provider()
            query = query.filter(self.MF.provider == provider_value)
            logger.debug(f"[UNIFIED_METRICS] Applied provider filter: {provider_value}")
        
        # Level filter (use E.level, not MF.level)
        # IMPORTANT: When filtering by entity_name (hierarchy rollup), do NOT also
        # constrain by E.level here, because we will restrict by descendants and/or
        # grouping level separately. Applying both can over-constrain to empty.
        if filters.level and not filters.entity_name:
            query = query.filter(self.E.level == filters.level)
            logger.debug(f"[UNIFIED_METRICS] Applied level filter: {filters.level}")
        
        # Status filter (default: include all entities)
        if filters.status:
            query = query.filter(self.E.status == filters.status)
            logger.debug(f"[UNIFIED_METRICS] Applied status filter: {filters.status}")
        
        # Entity IDs filter
        if filters.entity_ids:
            query = query.filter(self.MF.entity_id.in_(filters.entity_ids))
            logger.debug(f"[UNIFIED_METRICS] Applied entity_ids filter: {len(filters.entity_ids)} entities")
        
        # Entity name filter (case-insensitive partial match with hierarchy rollup)
        if filters.entity_name:
            if workspace_id:
                # Use hierarchy rollup to get descendant IDs
                descendant_ids = self._resolve_entity_name_to_descendants(workspace_id, filters.entity_name)
                if descendant_ids:
                    logger.info(f"[UNIFIED_METRICS] Using hierarchy rollup for '{filters.entity_name}': {len(descendant_ids)} descendants")
                    query = query.filter(self.MF.entity_id.in_(descendant_ids))
                else:
                    # Fallback to simple name match if hierarchy resolution fails
                    logger.warning(f"[UNIFIED_METRICS] Hierarchy resolution failed, falling back to name match")
                    pattern = f"%{filters.entity_name}%"
                    query = query.filter(self.E.name.ilike(pattern))
            else:
                # No workspace_id provided, use simple name match
                logger.warning(f"[UNIFIED_METRICS] No workspace_id provided for entity_name filter, using simple match")
                pattern = f"%{filters.entity_name}%"
                query = query.filter(self.E.name.ilike(pattern))
        
        return query

    def _resolve_entity_by_name(self, workspace_id: str, entity_name: str):
        """
        Resolve a single entity by name for a workspace.
        Tries exact match first, then partial (ILIKE) match.
        Returns the Entity ORM object or None if not found.
        """
        logger.info(f"[UNIFIED_METRICS] Resolving entity by name (exact first): '{entity_name}'")
        # Exact match
        exact = (
            self.db.query(self.E)
            .filter(self.E.workspace_id == workspace_id)
            .filter(self.E.name == entity_name)
            .first()
        )
        if exact:
            return exact

        # Case-insensitive partial match
        pattern = f"%{entity_name}%"
        partial = (
            self.db.query(self.E)
            .filter(self.E.workspace_id == workspace_id)
            .filter(self.E.name.ilike(pattern))
            .first()
        )
        if partial:
            logger.info(f"[UNIFIED_METRICS] Using partial match for '{entity_name}': {partial.name} ({partial.id})")
        else:
            logger.warning(f"[UNIFIED_METRICS] No entity found for name '{entity_name}' in workspace {workspace_id}")
        return partial

    def _build_hierarchy_entity_breakdown_query(
        self,
        workspace_id: str,
        start_date,
        end_date,
        named_entity,
        child_level: str,
        filters: MetricFilters,
    ):
        """
        Build a hierarchy-aware breakdown query for a named ancestor entity.
        Restrict facts to descendants of the named entity and group by the requested child level.

        child_level: 'adset' or 'ad' (when ancestor is campaign/adset respectively).
        """
        # Use entity_name-based descendant filtering (already working) instead of joining CTEs directly
        # This avoids SQLAlchemy CTE reuse issues while still getting the right data
        
        if named_entity.level == "campaign" and child_level == "adset":
            # For campaign→adset breakdown, filter by campaign descendants and group by adset ancestors
            from app.dsl.hierarchy import adset_ancestor_cte
            
            # Create unique CTE by creating a new session-bound one
            adset_cte = adset_ancestor_cte(self.db)
            adset_alias = aliased(self.E)
            
            query = (
                self.db.query(
                    adset_alias.name.label("group_name"),
                    func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
                    func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
                    func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
                    func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
                    func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
                )
                .select_from(self.MF)
                .join(self.E, self.E.id == self.MF.entity_id)
                .join(adset_cte, adset_cte.c.leaf_id == self.E.id)
                .join(adset_alias, adset_alias.id == adset_cte.c.ancestor_id)
                .filter(self.E.workspace_id == workspace_id)
                .filter(cast(self.date_field, Date).between(start_date, end_date))
                .group_by(adset_alias.name)
            )
            
            # Apply entity_name filter via descendants (this uses the working path)
            filters_no_name = MetricFilters(
                provider=filters.provider,
                level=None,
                status=filters.status,
                entity_ids=filters.entity_ids,
                entity_name=filters.entity_name,  # Keep entity_name to use descendant filtering
                metric_filters=filters.metric_filters,
            )
            query = self._apply_filters(query, filters_no_name, workspace_id)
            
        elif named_entity.level == "adset" and child_level == "ad":
            # For adset→ad breakdown, filter by adset descendants and group by ad names
            query = (
                self.db.query(
                    self.E.name.label("group_name"),
                    func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
                    func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
                    func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
                    func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
                    func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
                )
                .select_from(self.MF)
                .join(self.E, self.E.id == self.MF.entity_id)
                .filter(self.E.workspace_id == workspace_id)
                .filter(cast(self.date_field, Date).between(start_date, end_date))
                .group_by(self.E.name)
            )
            
            # Apply entity_name filter via descendants
            filters_no_name = MetricFilters(
                provider=filters.provider,
                level=None,
                status=filters.status,
                entity_ids=filters.entity_ids,
                entity_name=filters.entity_name,
                metric_filters=filters.metric_filters,
            )
            query = self._apply_filters(query, filters_no_name, workspace_id)
            
        elif named_entity.level == "ad":
            # Single ad entity
            query = (
                self.db.query(
                    self.E.name.label("group_name"),
                    func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
                    func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
                    func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
                    func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
                    func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
                )
                .select_from(self.MF)
                .join(self.E, self.E.id == self.MF.entity_id)
                .filter(self.E.id == named_entity.id)
                .filter(self.E.workspace_id == workspace_id)
                .filter(cast(self.date_field, Date).between(start_date, end_date))
                .group_by(self.E.name)
            )
        else:
            raise ValueError(f"Unsupported breakdown: {named_entity.level}→{child_level}")

        return query
    
    def _build_provider_breakdown_query(self, workspace_id: str, start_date: date, end_date: date, filters: MetricFilters):
        """Build query for provider breakdown."""
        query = (
            self.db.query(
                self.MF.provider.label("group_name"),
                func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
                func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
                func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
                func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
                func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
                func.coalesce(func.sum(self.MF.leads), 0).label("leads"),
                func.coalesce(func.sum(self.MF.installs), 0).label("installs"),
                func.coalesce(func.sum(self.MF.purchases), 0).label("purchases"),
                func.coalesce(func.sum(self.MF.visitors), 0).label("visitors"),
                func.coalesce(func.sum(self.MF.profit), 0).label("profit"),
            )
            .join(self.E, self.E.id == self.MF.entity_id)
            .filter(self.E.workspace_id == workspace_id)
            .filter(cast(self.date_field, Date).between(start_date, end_date))
            .group_by(self.MF.provider)
        )
        
        return self._apply_filters(query, filters, workspace_id)
    
    def _build_entity_breakdown_query(self, workspace_id: str, start_date: date, end_date: date, filters: MetricFilters, level: str):
        """Build query for entity breakdown (campaign/adset/ad).

        Includes creative fields (thumbnail_url, image_url, media_type) for ad-level
        breakdowns to support creative card displays. These fields are only populated
        for Meta ads currently.
        """
        # For now, implement simple ad-level breakdown
        # TODO: Add hierarchy support for campaign/adset rollups
        query = (
            self.db.query(
                self.E.id.label("entity_id"),  # Include entity_id for timeseries lookup
                self.E.name.label("group_name"),
                func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
                func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
                func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
                func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
                func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
                func.coalesce(func.sum(self.MF.leads), 0).label("leads"),
                func.coalesce(func.sum(self.MF.installs), 0).label("installs"),
                func.coalesce(func.sum(self.MF.purchases), 0).label("purchases"),
                func.coalesce(func.sum(self.MF.visitors), 0).label("visitors"),
                func.coalesce(func.sum(self.MF.profit), 0).label("profit"),
                # Creative fields for ad-level breakdowns (Meta only for now)
                self.E.thumbnail_url.label("thumbnail_url"),
                self.E.image_url.label("image_url"),
                self.E.media_type.label("media_type"),
            )
            .join(self.E, self.E.id == self.MF.entity_id)
            .filter(self.E.workspace_id == workspace_id)
            .filter(self.E.level == level)
            .filter(cast(self.date_field, Date).between(start_date, end_date))
            .group_by(
                self.E.id, self.E.name,
                self.E.thumbnail_url, self.E.image_url, self.E.media_type
            )
        )

        return self._apply_filters(query, filters, workspace_id)
    
    def _get_order_expression(self, metric: str):
        """Get SQL expression for ordering by metric."""
        if metric == "roas":
            return func.coalesce(func.sum(self.MF.revenue), 0) / func.nullif(func.coalesce(func.sum(self.MF.spend), 0), 0)
        elif metric == "cpc":
            return func.coalesce(func.sum(self.MF.spend), 0) / func.nullif(func.coalesce(func.sum(self.MF.clicks), 0), 0)
        elif metric == "cpa":
            return func.coalesce(func.sum(self.MF.spend), 0) / func.nullif(func.coalesce(func.sum(self.MF.conversions), 0), 0)
        elif metric == "ctr":
            return func.coalesce(func.sum(self.MF.clicks), 0) / func.nullif(func.coalesce(func.sum(self.MF.impressions), 0), 0)
        elif metric == "cpm":
            return (func.coalesce(func.sum(self.MF.spend), 0) / func.nullif(func.coalesce(func.sum(self.MF.impressions), 0), 0)) * 1000
        elif metric == "spend":
            return func.coalesce(func.sum(self.MF.spend), 0)
        elif metric == "revenue":
            return func.coalesce(func.sum(self.MF.revenue), 0)
        elif metric == "clicks":
            return func.coalesce(func.sum(self.MF.clicks), 0)
        elif metric == "conversions":
            return func.coalesce(func.sum(self.MF.conversions), 0)
        else:
            # Fallback to spend
            return func.coalesce(func.sum(self.MF.spend), 0)
    
    def _passes_metric_filters(self, metric: str, value: Optional[float], metric_filters: List[Dict[str, Any]]) -> bool:
        """
        Check if a metric value passes the specified filters.
        
        Args:
            metric: The metric name being checked
            value: The calculated metric value
            metric_filters: List of filter conditions
            
        Returns:
            True if the value passes all filters, False otherwise
            
        Example:
            >>> filters = [{"metric": "roas", "operator": ">", "value": 4}]
            >>> service._passes_metric_filters("roas", 5.2, filters)
            True
        """
        if value is None:
            return False
        
        for filter_condition in metric_filters:
            filter_metric = filter_condition.get("metric")
            operator = filter_condition.get("operator")
            filter_value = filter_condition.get("value")
            
            # Only apply filters for the current metric
            if filter_metric != metric:
                continue
            
            # Apply the filter condition
            if operator == ">":
                if not (value > filter_value):
                    return False
            elif operator == ">=":
                if not (value >= filter_value):
                    return False
            elif operator == "<":
                if not (value < filter_value):
                    return False
            elif operator == "<=":
                if not (value <= filter_value):
                    return False
            elif operator == "=":
                if not (value == filter_value):
                    return False
            elif operator == "!=":
                if not (value != filter_value):
                    return False
            else:
                logger.warning(f"[UNIFIED_METRICS] Unknown operator: {operator}")
                continue
        
        return True
    
    def get_entity_list(
        self,
        workspace_id: str,
        filters: MetricFilters,
        level: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get list of entities matching filters.
        
        IMPORTANT: Uses LEFT JOIN so entities without metric facts still appear.
        This is critical for newly synced campaigns that haven't delivered yet.
        
        Args:
            workspace_id: Workspace UUID for scoping
            filters: Filtering criteria
            level: Entity level to filter by (campaign, adset, ad)
            limit: Maximum number of entities to return
            
        Returns:
            List of entity dictionaries with name, status, level, provider
            
        Example:
            >>> service = UnifiedMetricService(db)
            >>> entities = service.get_entity_list(
            ...     workspace_id="...",
            ...     filters=MetricFilters(status="active"),
            ...     level="campaign"
            ... )
            >>> print(entities[0]["name"])
            Summer Sale Campaign
        """
        logger.info(f"[UNIFIED_METRICS] Getting entity list for level: {level}")
        
        # Build base query starting from Entity, LEFT JOIN MetricSnapshot to get provider
        # Also join Connection to get provider when MetricSnapshot is missing
        Connection = models.Connection
        query = (
            self.db.query(
                self.E.id,
                self.E.name,
                self.E.status,
                self.E.level,
                func.coalesce(
                    func.max(self.MF.provider),
                    Connection.provider
                ).label("provider")
            )
            .join(Connection, Connection.id == self.E.connection_id)
            .outerjoin(self.MF, self.MF.entity_id == self.E.id)
            .filter(self.E.workspace_id == workspace_id)
            .group_by(
                self.E.id,
                self.E.name,
                self.E.status,
                self.E.level,
                Connection.provider
            )
        )
        
        # Apply level filter if specified
        if level:
            query = query.filter(self.E.level == level)
        
        # Apply other filters
        query = self._apply_entity_filters(query, filters)
        
        # Order by name and limit
        query = query.order_by(self.E.name).limit(limit)
        
        # Execute query
        rows = query.all()
        
        # Convert to dictionaries
        entities = []
        for row in rows:
            entities.append({
                "id": str(row.id),
                "name": row.name,
                "status": row.status,
                "level": row.level,
                "provider": row.provider.value if row.provider else None
            })
        
        logger.info(f"[UNIFIED_METRICS] Found {len(entities)} entities")
        return entities
    
    def get_time_based_breakdown(
        self,
        workspace_id: str,
        metric: str,
        time_range: TimeRange,
        filters: MetricFilters,
        breakdown_dimension: str,
        top_n: int = 5,
        sort_order: str = "desc"
    ) -> List[MetricBreakdownItem]:
        """
        Get time-based breakdown results for a metric.
        
        Args:
            workspace_id: Workspace UUID for scoping
            metric: Metric name to calculate
            time_range: Time range for calculation
            filters: Filtering criteria
            breakdown_dimension: Time dimension to group by (day, week, month)
            top_n: Number of top results to return
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            List of breakdown items with time labels
            
        Example:
            >>> service = UnifiedMetricService(db)
            >>> breakdown = service.get_time_based_breakdown(
            ...     workspace_id="...",
            ...     metric="cpc",
            ...     time_range=TimeRange(last_n_days=7),
            ...     filters=MetricFilters(),
            ...     breakdown_dimension="day"
            ... )
            >>> print(breakdown[0].label)
            2025-10-15
        """
        logger.info(f"[UNIFIED_METRICS] Getting time-based breakdown for {metric} by {breakdown_dimension}")
        
        # Resolve time range
        start_date, end_date = self._resolve_time_range(time_range)
        
        # Build time-based breakdown query
        query = self._build_time_breakdown_query(
            workspace_id, start_date, end_date, filters, breakdown_dimension
        )
        
        # Apply ordering and limit
        if sort_order == "asc":
            query = query.order_by(asc(self._get_time_order_expression(metric, breakdown_dimension)))
        else:
            query = query.order_by(desc(self._get_time_order_expression(metric, breakdown_dimension)))
        
        # Execute query to get all results first
        rows = query.all()
        
        # Build breakdown results
        breakdown = []
        for row in rows:
            totals = row._asdict()
            value = compute_metric(metric, totals)
            
            # Apply metric filters if specified
            if filters.metric_filters:
                if not self._passes_metric_filters(metric, value, filters.metric_filters):
                    continue
            
            # Extract creative fields if available (ad-level only, Meta only)
            thumbnail_url = totals.get("thumbnail_url")
            image_url = totals.get("image_url")
            media_type_val = totals.get("media_type")
            # Convert enum to string if needed
            media_type = media_type_val.value if hasattr(media_type_val, 'value') else (str(media_type_val) if media_type_val else None)

            breakdown.append(MetricBreakdownItem(
                label=str(row.group_name),
                value=value,
                spend=totals.get("spend"),
                clicks=totals.get("clicks"),
                conversions=totals.get("conversions"),
                revenue=totals.get("revenue"),
                impressions=totals.get("impressions"),
                entity_id=str(totals.get("entity_id")) if totals.get("entity_id") else None,
                thumbnail_url=thumbnail_url,
                image_url=image_url,
                media_type=media_type,
            ))
        
        # Apply top_n limit after filtering
        return breakdown[:top_n]
    
    def get_entity_goals(self, workspace_id: str, entity_names: List[str]) -> Dict[str, str]:
        """
        Get goals for entities by name.
        
        Args:
            workspace_id: Workspace UUID for scoping
            entity_names: List of entity names to look up
            
        Returns:
            Dict mapping entity names to their goals (or None if not found)
        """
        if not entity_names:
            return {}
        
        # Build query to find entities by name
        entities = (
            self.db.query(self.E.name, self.E.goal)
            .filter(self.E.workspace_id == workspace_id)
            .filter(self.E.name.in_(entity_names))
            .all()
        )
        
        return {entity.name: entity.goal.value if entity.goal else None for entity in entities}
    
    def _apply_entity_filters(self, query, filters: MetricFilters):
        """Apply filters to entity queries (not metric queries)."""
        # Provider filter (from Connection since we're joining it)
        if filters.provider:
            provider_value = filters.normalize_provider()
            # Filter by Connection.provider since we're already joining Connection
            Connection = models.Connection
            query = query.filter(Connection.provider == provider_value)
        
        # Level filter
        if filters.level:
            query = query.filter(self.E.level == filters.level)
        
        # Status filter
        if filters.status:
            query = query.filter(self.E.status == filters.status)
        
        # Entity IDs filter
        if filters.entity_ids:
            query = query.filter(self.E.id.in_(filters.entity_ids))
        
        # Entity name filter (case-insensitive partial match)
        if filters.entity_name:
            pattern = f"%{filters.entity_name}%"
            query = query.filter(self.E.name.ilike(pattern))
        
        return query
    
    def _build_time_breakdown_query(self, workspace_id: str, start_date: date, end_date: date, filters: MetricFilters, breakdown_dimension: str):
        """Build query for time-based breakdown."""
        if breakdown_dimension == "day":
            group_expr = cast(self.date_field, Date)
            label_expr = cast(self.date_field, Date)
        elif breakdown_dimension == "week":
            group_expr = func.date_trunc('week', self.date_field)
            label_expr = func.date_trunc('week', self.date_field)
        elif breakdown_dimension == "month":
            group_expr = func.date_trunc('month', self.date_field)
            label_expr = func.date_trunc('month', self.date_field)
        else:
            raise ValueError(f"Unsupported time breakdown dimension: {breakdown_dimension}")
        
        query = (
            self.db.query(
                label_expr.label("group_name"),
                func.coalesce(func.sum(self.MF.spend), 0).label("spend"),
                func.coalesce(func.sum(self.MF.revenue), 0).label("revenue"),
                func.coalesce(func.sum(self.MF.clicks), 0).label("clicks"),
                func.coalesce(func.sum(self.MF.impressions), 0).label("impressions"),
                func.coalesce(func.sum(self.MF.conversions), 0).label("conversions"),
                func.coalesce(func.sum(self.MF.leads), 0).label("leads"),
                func.coalesce(func.sum(self.MF.installs), 0).label("installs"),
                func.coalesce(func.sum(self.MF.purchases), 0).label("purchases"),
                func.coalesce(func.sum(self.MF.visitors), 0).label("visitors"),
                func.coalesce(func.sum(self.MF.profit), 0).label("profit"),
            )
            .join(self.E, self.E.id == self.MF.entity_id)
            .filter(self.E.workspace_id == workspace_id)
            .filter(cast(self.date_field, Date).between(start_date, end_date))
            .group_by(group_expr)
        )
        
        return self._apply_filters(query, filters, workspace_id)
    
    def _get_time_order_expression(self, metric: str, breakdown_dimension: str):
        """Get SQL expression for ordering by metric in time-based breakdowns."""
        # Use the same logic as _get_order_expression but for time-based queries
        if metric == "roas":
            return func.coalesce(func.sum(self.MF.revenue), 0) / func.nullif(func.coalesce(func.sum(self.MF.spend), 0), 0)
        elif metric == "cpc":
            return func.coalesce(func.sum(self.MF.spend), 0) / func.nullif(func.coalesce(func.sum(self.MF.clicks), 0), 0)
        elif metric == "cpa":
            return func.coalesce(func.sum(self.MF.spend), 0) / func.nullif(func.coalesce(func.sum(self.MF.conversions), 0), 0)
        elif metric == "ctr":
            return func.coalesce(func.sum(self.MF.clicks), 0) / func.nullif(func.coalesce(func.sum(self.MF.impressions), 0), 0)
        elif metric == "cpm":
            return (func.coalesce(func.sum(self.MF.spend), 0) / func.nullif(func.coalesce(func.sum(self.MF.impressions), 0), 0)) * 1000
        elif metric == "spend":
            return func.coalesce(func.sum(self.MF.spend), 0)
        elif metric == "revenue":
            return func.coalesce(func.sum(self.MF.revenue), 0)
        elif metric == "clicks":
            return func.coalesce(func.sum(self.MF.clicks), 0)
        elif metric == "conversions":
            return func.coalesce(func.sum(self.MF.conversions), 0)
        else:
            # Fallback to spend
            return func.coalesce(func.sum(self.MF.spend), 0)
