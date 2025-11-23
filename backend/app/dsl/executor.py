"""
Query Executor
==============

Executes query plans against the database using SQLAlchemy.

Derived Metrics v1 changes:
- Uses app/metrics/registry for ALL metric computations
- Aggregates all base measures (including new ones: leads, installs, purchases, visitors, profit)
- Defers derived metric math to formulas (single source of truth)

WHY separate executor?
- Single source of truth for metric calculations → app/metrics/registry
- Workspace scoping enforced at query level
- Divide-by-zero guards for derived metrics → app/metrics/formulas
- Clear separation: planning vs execution

Related files:
- app/dsl/planner.py: Creates the Plan that we execute
- app/dsl/schema.py: MetricResult that we return
- app/models.py: Database models (MetricFact, Entity)
- app/metrics/registry.py: Maps metrics → formulas (USED HERE)
- app/metrics/formulas.py: Pure functions for derived metrics

Design:
- Workspace-scoped: ALL queries filter by workspace_id
- Safe math: Divide-by-zero guards in app/metrics/formulas
- Efficient: Single query for summary, separate for timeseries/breakdown
- Flexible: Supports all filter combinations
"""

from __future__ import annotations

from datetime import timedelta, datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from app.dsl.schema import MetricResult, MetricQuery, TimeRange
from app.dsl.planner import Plan
from app import models
from app.metrics.registry import compute_metric, get_required_bases

logger = logging.getLogger(__name__)


# =====================================================================
# Phase 3: Data Availability Helpers
# =====================================================================

def get_available_platforms(db: Session, workspace_id: str) -> List[str]:
    """
    Get list of platforms that actually have data in this workspace.
    
    WHY: Needed for graceful handling of platform filter queries
    WHEN: Before executing queries with provider filters
    WHERE: Called by QA service before execute_plan()
    
    Args:
        db: Database session
        workspace_id: Workspace UUID
        
    Returns:
        List of provider names that have metric data (lowercase strings)
        
    Example:
        >>> platforms = get_available_platforms(db, workspace_id)
        >>> platforms
        ['meta', 'tiktok', 'other']  # Google not present
        
    Related:
    - Used by: app/services/qa_service.py for pre-execution validation
    """
    E = models.Entity
    MF = models.MetricFact
    C = models.Connection

    providers_set = set()

    # Providers with metric facts
    result = (
        db.query(MF.provider)
        .join(E, E.id == MF.entity_id)
        .filter(E.workspace_id == workspace_id)
        .distinct()
        .all()
    )
    providers_set.update([r[0].value for r in result if r[0]])

    # Providers with connections (even if zero facts)
    connection_rows = (
        db.query(C.provider)
        .filter(C.workspace_id == workspace_id)
        .distinct()
        .all()
    )
    providers_set.update([r[0].value for r in connection_rows if r[0]])

    return sorted(list(providers_set))


# =====================================================================
# REMOVED: _derive_metric() function
# =====================================================================
# Derived Metrics v1 change:
# - Old: _derive_metric() function defined here (duplicated logic)
# - New: Use compute_metric() from app/metrics/registry (single source of truth)
# - WHY: Ensures formulas never diverge between executor and compute_service
# - HOW: Import compute_metric at top of file, call it instead of _derive_metric
# =====================================================================


def execute_plan(
    db: Session, 
    workspace_id: str, 
    plan: Optional[Plan],
    query: MetricQuery
) -> Dict[str, Any]:
    """
    Execute a query plan and return results.
    
    DSL v1.2 changes:
    - Accepts both plan (Optional) and query (MetricQuery)
    - Handles three query types:
      1. METRICS: Execute plan (existing logic)
      2. PROVIDERS: List distinct ad platforms in workspace
      3. ENTITIES: List entities with filters
    - Returns either MetricResult (metrics) or dict (providers/entities)
    
    Args:
        db: SQLAlchemy database session
        workspace_id: Workspace UUID for scoping (tenant safety)
        plan: Execution plan from build_plan() (None for non-metrics queries)
        query: Original MetricQuery with query_type and filters
        
    Returns:
        For metrics: MetricResult with summary, comparison, timeseries, and breakdown
        For providers: {"providers": ["google", "meta", ...]}
        For entities: {"entities": [{"name": "...", "status": "...", "level": "..."}, ...]}
        
    Examples:
        >>> # Metrics query
        >>> query = MetricQuery(query_type="metrics", metric="roas", time_range=TimeRange(last_n_days=7))
        >>> plan = build_plan(query)
        >>> result = execute_plan(db, workspace_id="...", plan=plan, query=query)
        >>> print(result.summary)
        2.45
        >>> 
        >>> # Providers query
        >>> query = MetricQuery(query_type="providers")
        >>> result = execute_plan(db, workspace_id="...", plan=None, query=query)
        >>> print(result["providers"])
        ["google", "meta", "tiktok"]
        >>> 
        >>> # Entities query
        >>> query = MetricQuery(query_type="entities", filters={"level": "campaign", "status": "active"})
        >>> result = execute_plan(db, workspace_id="...", plan=None, query=query)
        >>> print(result["entities"])
        [{"name": "Summer Sale", "status": "active", "level": "campaign"}, ...]
    
    Tenant safety:
    - ALL queries filter by workspace_id at the database level
    - No cross-workspace data leaks possible
    
    Related:
    - Input: app/dsl/planner.Plan, app/dsl/schema.MetricQuery
    - Output: app/dsl/schema.MetricResult or dict
    - Called by: app/services/qa_service.py
    """
    # DSL v1.2: Route to appropriate handler based on query_type
    
    # PROVIDERS: List distinct ad platforms in this workspace
    # Returns: {"providers": ["google", "meta", ...]}
    # Example question: "Which platforms am I advertising on?"
    if query.query_type == "providers":
        providers_set = set()
        # Providers with metric facts
        rows = (
            db.query(models.MetricFact.provider)
            .join(models.Entity, models.Entity.id == models.MetricFact.entity_id)
            .filter(models.Entity.workspace_id == workspace_id)
            .distinct()
            .all()
        )
        providers_set.update([row.provider.value for row in rows if row.provider])
        # Providers with connections (even if zero facts)
        conn_rows = (
            db.query(models.Connection.provider)
            .filter(models.Connection.workspace_id == workspace_id)
            .distinct()
            .all()
        )
        providers_set.update([r[0].value for r in conn_rows if r[0]])
        return {"providers": sorted(list(providers_set))}
    
    # ENTITIES: List entities (campaigns/adsets/ads) with optional filters
    # Returns: {"entities": [{"name": "...", "status": "...", "level": "..."}, ...]}
    # Example question: "List my active campaigns"
    if query.query_type == "entities":
        # Import UnifiedMetricService
        from app.services.unified_metric_service import UnifiedMetricService, MetricFilters
        
        # Initialize service
        service = UnifiedMetricService(db)
        
        # Convert DSL filters to service filters
        filters = MetricFilters(
            provider=query.filters.provider,
            level=query.filters.level,
            status=query.filters.status,
            entity_ids=query.filters.entity_ids,
            entity_name=query.filters.entity_name,
            metric_filters=query.filters.metric_filters
        )
        
        # Get entity list using service
        entities = service.get_entity_list(
            workspace_id=workspace_id,
            filters=filters,
            level=query.filters.level,
            limit=query.top_n
        )
        
        return {
            "entities": [
                {"name": entity["name"], "status": entity["status"], "level": entity["level"]} 
                for entity in entities
            ]
        }
    
    # COMPARISON: Execute comparison queries (NEW in Step 3)
    if query.query_type == "comparison":
        if not plan:
            raise ValueError("Plan is required for comparison queries")
        
        return _execute_comparison_plan(db, workspace_id, plan, query)
    
    # METRICS: Execute the plan (existing v1.1 logic + multi-metric support)
    # This is the default/legacy behavior
    if query.query_type == "metrics":
        if not plan:
            raise ValueError("Plan is required for metrics queries")
        
        # Phase 7: Handle multi-metric queries
        if isinstance(query.metric, list):
            return _execute_multi_metric_plan(db, workspace_id, plan, query)
        else:
            return _execute_metrics_plan(db, workspace_id, plan)
    
    # Unknown query type
    raise ValueError(f"Unsupported query_type: {query.query_type}")


def _execute_metrics_plan(
    db: Session,
    workspace_id: str,
    plan: Plan
) -> MetricResult:
    """
    Execute a metrics plan using UnifiedMetricService.
    
    REFACTORED: Now uses UnifiedMetricService for consistent calculations
    across all endpoints (QA, KPI, entity performance, finance).
    
    Args:
        db: SQLAlchemy database session
        workspace_id: Workspace UUID for scoping
        plan: Execution plan with dates, metrics, filters
        
    Returns:
        MetricResult with summary, comparison, timeseries, and breakdown
        
    Process:
    1. Convert plan to UnifiedMetricService inputs
    2. Call service methods for summary, timeseries, breakdown
    3. Convert service results back to MetricResult format
    4. Maintain backward compatibility with existing QA system
    """
    # Import UnifiedMetricService
    from app.services.unified_metric_service import UnifiedMetricService, MetricFilters
    
    # Initialize service
    service = UnifiedMetricService(db)
    
    # Convert plan to service inputs
    time_range = TimeRange(start=plan.start, end=plan.end)
    filters = MetricFilters(
        provider=plan.filters.get("provider"),
        level=plan.filters.get("level"),
        status=plan.filters.get("status"),
        entity_ids=plan.filters.get("entity_ids"),
        entity_name=plan.filters.get("entity_name"),
        metric_filters=plan.filters.get("metric_filters")
    )
    
    # Get primary metric name
    metric_name = plan.derived or plan.base_measures[0]
    metrics = [metric_name]
    
    # --- SUMMARY AGGREGATION ---
    # Use UnifiedMetricService for consistent calculations
    summary_result = service.get_summary(
        workspace_id=workspace_id,
        metrics=metrics,
        time_range=time_range,
        filters=filters,
        compare_to_previous=plan.need_previous
    )
    
    # Extract values from service result
    metric_value = summary_result.metrics[metric_name]
    summary_value = metric_value.value
    previous_value = metric_value.previous
    delta_pct = metric_value.delta_pct
    
    # --- TIMESERIES (daily values) ---
    timeseries = None
    
    if plan.need_timeseries:
        # Use UnifiedMetricService for consistent timeseries
        timeseries_dict = service.get_timeseries(
            workspace_id=workspace_id,
            metrics=metrics,
            time_range=time_range,
            filters=filters
        )
        
        # Extract timeseries for the primary metric
        # get_timeseries now returns Dict[str, List[MetricTimePoint]]
        timeseries_points = timeseries_dict.get(metric_name, [])
        
        # Convert to expected format
        timeseries = [
            {
                "date": point.date,
                "value": point.value
            }
            for point in timeseries_points
        ]
    
    # --- BREAKDOWN (top entities by dimension) ---
    breakdown = None
    
    if plan.breakdown:
        # Use UnifiedMetricService for consistent breakdown
        # Check if it's a temporal breakdown (day, week, month)
        if plan.breakdown in ["day", "week", "month"]:
            breakdown_items = service.get_time_based_breakdown(
                workspace_id=workspace_id,
                metric=metric_name,
                time_range=time_range,
                filters=filters,
                breakdown_dimension=plan.breakdown,
                top_n=plan.top_n,
                sort_order=plan.sort_order
            )
        else:
            # Regular entity breakdown (provider, campaign, adset, ad)
            breakdown_items = service.get_breakdown(
                workspace_id=workspace_id,
                metric=metric_name,
                time_range=time_range,
                filters=filters,
                breakdown_dimension=plan.breakdown,
                top_n=plan.top_n,
                sort_order=plan.sort_order
            )
        
        # Convert to expected format
        breakdown = [
            {
                "label": item.label,
                "value": item.value,
                "spend": item.spend,
                "clicks": item.clicks,
                "conversions": item.conversions,
                "revenue": item.revenue,
                "impressions": item.impressions
            }
            for item in breakdown_items
        ]
    
    # --- WORKSPACE AVERAGE CALCULATION ---
    # Use UnifiedMetricService for consistent workspace average
    workspace_avg = summary_result.workspace_avg
    
    # Log workspace average if available
    if workspace_avg is not None:
        logger.info(
            f"Calculated workspace average for {metric_name}: {workspace_avg} (query value: {summary_value})"
        )
    
    # --- BUILD RESULT ---
    return MetricResult(
        summary=summary_value,
        previous=previous_value,
        delta_pct=delta_pct,
        timeseries=timeseries,
        breakdown=breakdown,
        workspace_avg=workspace_avg
    )


def _execute_multi_metric_plan(
    db: Session,
    workspace_id: str,
    plan: Plan,
    query: MetricQuery
) -> Dict[str, Any]:
    """
    Execute a multi-metric query plan using UnifiedMetricService.
    
    REFACTORED: Now uses UnifiedMetricService for consistent calculations
    across all endpoints (QA, KPI, entity performance, finance).
    
    This function handles queries that request multiple metrics at once.
    It executes the same base aggregation for all metrics and returns
    a structured result with all requested metric values.
    
    Args:
        db: SQLAlchemy database session
        workspace_id: Workspace UUID for scoping
        plan: Execution plan with dates, filters
        query: Original MetricQuery with list of metrics
        
    Returns:
        Dict with structure:
        {
            "metrics": {
                "spend": {"summary": 1000.0, "previous": 900.0, "delta_pct": 11.1},
                "revenue": {"summary": 2000.0, "previous": 1800.0, "delta_pct": 11.1},
                "roas": {"summary": 2.0, "previous": 2.0, "delta_pct": 0.0}
            },
            "timeseries": [...],  # Optional
            "breakdown": [...]    # Optional
        }
    """
    from typing import Dict, Any, List
    
    logger.info(f"[MULTI_METRIC] Executing plan for metrics: {query.metric}")
    
    # Import UnifiedMetricService
    from app.services.unified_metric_service import UnifiedMetricService, MetricFilters
    
    # Initialize service
    service = UnifiedMetricService(db)
    
    # Convert plan to service inputs
    time_range = TimeRange(start=plan.start, end=plan.end)
    filters = MetricFilters(
        provider=plan.filters.get("provider"),
        level=plan.filters.get("level"),
        status=plan.filters.get("status"),
        entity_ids=plan.filters.get("entity_ids"),
        entity_name=plan.filters.get("entity_name"),
        metric_filters=plan.filters.get("metric_filters")
    )
    
    # Get requested metrics
    metrics = query.metric
    
    # --- SUMMARY AGGREGATION ---
    # Use UnifiedMetricService for consistent calculations
    summary_result = service.get_summary(
        workspace_id=workspace_id,
        metrics=metrics,
        time_range=time_range,
        filters=filters,
        compare_to_previous=plan.need_previous
    )
    
    # Convert service result to expected format
    metrics_result = {}
    for metric_name in metrics:
        metric_data = summary_result.metrics[metric_name]
        metrics_result[metric_name] = {
            "summary": metric_data.value,
            "previous": metric_data.previous,
            "delta_pct": metric_data.delta_pct
        }
    
    # --- TIMESERIES (daily values) ---
    timeseries = None
    
    if plan.need_timeseries:
        # Use UnifiedMetricService for consistent timeseries
        timeseries_dict = service.get_timeseries(
            workspace_id=workspace_id,
            metrics=metrics,
            time_range=time_range,
            filters=filters
        )
        
        # Convert to expected format
        # For multi-metric, we'll return timeseries for the first metric
        # (or we could return all metrics' timeseries)
        primary_metric = metrics[0]
        timeseries_points = timeseries_dict.get(primary_metric, [])
        
        timeseries = [
            {
                "date": point.date,
                "value": point.value
            }
            for point in timeseries_points
        ]
    
    # --- BREAKDOWN (top entities by dimension) ---
    breakdown = None
    
    if plan.breakdown:
        # Use UnifiedMetricService for consistent breakdown
        # Check if it's a temporal breakdown (day, week, month)
        if plan.breakdown in ["day", "week", "month"]:
            breakdown_items = service.get_time_based_breakdown(
                workspace_id=workspace_id,
                metric=metrics[0],  # Use first metric for breakdown
                time_range=time_range,
                filters=filters,
                breakdown_dimension=plan.breakdown,
                top_n=plan.top_n,
                sort_order=plan.sort_order
            )
        else:
            # Regular entity breakdown (provider, campaign, adset, ad)
            breakdown_items = service.get_breakdown(
                workspace_id=workspace_id,
                metric=metrics[0],  # Use first metric for breakdown
                time_range=time_range,
                filters=filters,
                breakdown_dimension=plan.breakdown,
                top_n=plan.top_n,
                sort_order=plan.sort_order
            )
        
        # Convert to expected format
        breakdown = [
            {
                "label": item.label,
                "value": item.value,
                "spend": item.spend,
                "clicks": item.clicks,
                "conversions": item.conversions,
                "revenue": item.revenue,
                "impressions": item.impressions
            }
            for item in breakdown_items
        ]
    
    logger.info(f"[MULTI_METRIC] Completed execution for {len(query.metric)} metrics")
    return {
        "metrics": metrics_result,
        "timeseries": timeseries,
        "breakdown": breakdown,
        "query_type": "multi_metrics"
    }


def _execute_comparison_plan(
    db: Session,
    workspace_id: str,
    plan: Plan,
    query: MetricQuery
) -> Dict[str, Any]:
    """
    Execute a comparison query plan using UnifiedMetricService.
    
    NEW in Step 3: Handles comparison queries between entities, providers, or time periods.
    
    Args:
        db: SQLAlchemy database session
        workspace_id: Workspace UUID for scoping
        plan: Execution plan with dates, filters
        query: Original MetricQuery with comparison fields
        
    Returns:
        Dict with comparison results
        
    Example:
        >>> query = MetricQuery(
        ...     query_type="comparison",
        ...     comparison_type="entity_vs_entity",
        ...     comparison_entities=["Holiday Sale", "App Install"],
        ...     comparison_metrics=["roas", "revenue"]
        ... )
        >>> result = _execute_comparison_plan(db, workspace_id, plan, query)
        >>> print(result["comparison"])
        [{"entity": "Holiday Sale", "roas": 5.2, "revenue": 1000}, ...]
    """
    from typing import Dict, Any, List
    
    logger.info(f"[COMPARISON] Executing comparison plan for type: {query.comparison_type}")
    
    # Import UnifiedMetricService
    from app.services.unified_metric_service import UnifiedMetricService, MetricFilters
    
    # Initialize service
    service = UnifiedMetricService(db)
    
    # Convert plan to service inputs
    time_range = TimeRange(start=plan.start, end=plan.end)
    filters = MetricFilters(
        provider=plan.filters.get("provider"),
        level=plan.filters.get("level"),
        status=plan.filters.get("status"),
        entity_ids=plan.filters.get("entity_ids"),
        entity_name=plan.filters.get("entity_name"),
        metric_filters=plan.filters.get("metric_filters")
    )
    
    # Get comparison metrics
    metrics = query.comparison_metrics or ["roas"]  # Default to ROAS if not specified
    
    comparison_results = []
    
    if query.comparison_type == "entity_vs_entity":
        # Compare specific entities
        entities = query.comparison_entities or []
        
        for entity_name in entities:
            # Create entity-specific filters
            entity_filters = MetricFilters(
                provider=filters.provider,
                level=filters.level,
                status=filters.status,
                entity_ids=filters.entity_ids,
                entity_name=entity_name,  # Filter by specific entity
                metric_filters=filters.metric_filters
            )
            
            # Get summary for this entity
            summary_result = service.get_summary(
                workspace_id=workspace_id,
                metrics=metrics,
                time_range=time_range,
                filters=entity_filters,
                compare_to_previous=plan.need_previous
            )
            
            # Build comparison result
            entity_result = {"entity": entity_name}
            for metric_name in metrics:
                metric_data = summary_result.metrics[metric_name]
                entity_result[metric_name] = metric_data.value
            
            comparison_results.append(entity_result)
    
    elif query.comparison_type == "provider_vs_provider":
        # Compare providers
        providers = ["google", "meta", "tiktok", "other"]  # All providers
        
        for provider in providers:
            # Create provider-specific filters
            provider_filters = MetricFilters(
                provider=provider,
                level=filters.level,
                status=filters.status,
                entity_ids=filters.entity_ids,
                entity_name=filters.entity_name,
                metric_filters=filters.metric_filters
            )
            
            # Get summary for this provider
            summary_result = service.get_summary(
                workspace_id=workspace_id,
                metrics=metrics,
                time_range=time_range,
                filters=provider_filters,
                compare_to_previous=plan.need_previous
            )
            
            # Build comparison result
            provider_result = {"provider": provider}
            for metric_name in metrics:
                metric_data = summary_result.metrics[metric_name]
                provider_result[metric_name] = metric_data.value
            
            comparison_results.append(provider_result)
    
    elif query.comparison_type == "time_vs_time":
        # Basic time vs time: compare current window (plan.start/end) vs previous window of same length
        metrics = query.comparison_metrics or [query.metric] if isinstance(query.metric, str) else (query.comparison_metrics or ["revenue"])  # default revenue

        # Prepare service
        from app.services.unified_metric_service import UnifiedMetricService, MetricFilters
        service = UnifiedMetricService(db)

        time_range_current = TimeRange(start=plan.start, end=plan.end)
        # Derive previous window
        period_length = (plan.end - plan.start).days + 1
        prev_end = plan.start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_length - 1)
        time_range_previous = TimeRange(start=prev_start, end=prev_end)

        filters = MetricFilters(
            provider=plan.filters.get("provider"),
            level=plan.filters.get("level"),
            status=plan.filters.get("status"),
            entity_ids=plan.filters.get("entity_ids"),
            entity_name=plan.filters.get("entity_name"),
            metric_filters=plan.filters.get("metric_filters"),
        )

        # Fetch summaries
        current_summary = service.get_summary(workspace_id, metrics, time_range_current, filters, compare_to_previous=False)
        previous_summary = service.get_summary(workspace_id, metrics, time_range_previous, filters, compare_to_previous=False)

        # Build comparison result
        comparison_item = {"period": "current"}
        for metric_name in metrics:
            mv = current_summary.metrics.get(metric_name)
            comparison_item[metric_name] = mv.value if mv else None

        previous_item = {"period": "previous"}
        for metric_name in metrics:
            mv = previous_summary.metrics.get(metric_name)
            previous_item[metric_name] = mv.value if mv else None

        comparison_results = [comparison_item, previous_item]
        logger.info(f"[COMPARISON] time_vs_time computed for metrics={metrics}")
        return {
            "comparison": comparison_results,
            "comparison_type": query.comparison_type,
            "metrics": metrics,
            "query_type": "comparison"
        }
    
    else:
        raise ValueError(f"Unsupported comparison type: {query.comparison_type}")
    
    logger.info(f"[COMPARISON] Completed execution for {len(comparison_results)} items")
    return {
        "comparison": comparison_results,
        "comparison_type": query.comparison_type,
        "metrics": metrics,
        "query_type": "comparison"
    }
