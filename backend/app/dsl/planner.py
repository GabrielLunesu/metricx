"""
Query Planner
=============

Converts high-level DSL (MetricQuery) into low-level execution plans.

WHY a planner?
- Separates WHAT (DSL intent) from HOW (database operations)
- Makes execution logic testable independently
- Enables query optimization in the future
- Clear documentation of query semantics

Related files:
- app/dsl/schema.py: Input type (MetricQuery)
- app/dsl/executor.py: Consumes Plan to run actual queries
- app/services/metric_service.py: Legacy aggregation logic (being replaced)

Design:
- Pure function: DSL → Plan (no side effects)
- Resolves time ranges (relative → absolute dates)
- Determines which base measures are needed
- Identifies derived metric formulas
- Plans comparison windows
- Plans breakdown dimensions
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, List

from app.dsl.schema import MetricQuery, TimeRange


@dataclass
class Plan:
    """
    Low-level execution plan for a MetricQuery.
    
    This plan describes:
    - Which date range to query (absolute dates)
    - Which base measures to aggregate (spend, clicks, etc.)
    - Which derived metric formula to apply (if any)
    - Whether to compute timeseries
    - Whether to compute previous period comparison
    - Which dimension to break down by
    
    Attributes:
        start: Query start date (inclusive)
        end: Query end date (inclusive)
        group_by: Grouping dimension ("none", "campaign", "adset", "ad")
        breakdown: Breakdown dimension for driver analysis (None or same as group_by)
        derived: Derived metric name ("roas", "cpa", "cvr") or None for base metrics
        need_timeseries: Whether to compute daily timeseries
        need_previous: Whether to compute previous period comparison
        base_measures: Which base columns to SUM (spend, revenue, clicks, etc.)
        filters: Pass-through filters from the DSL
        top_n: How many items to return in breakdown
        query: Original MetricQuery (for accessing thresholds and other advanced features)
        
    Example:
        Plan(
            start=date(2025, 9, 24),
            end=date(2025, 9, 30),
            group_by="none",
            breakdown=None,
            derived="roas",
            need_timeseries=True,
            need_previous=True,
            base_measures=["spend", "revenue"],
            filters={},
            top_n=5,
            query=original_query
        )
    
    Related:
    - Created by: build_plan() in this module
    - Consumed by: execute_plan() in app/dsl/executor.py
    """
    start: date
    end: date
    group_by: str
    breakdown: Optional[str]
    derived: Optional[str]
    need_timeseries: bool
    need_previous: bool
    base_measures: List[str]
    filters: dict
    top_n: int
    sort_order: str  # "asc" or "desc" - sort order for breakdown results
    query: MetricQuery  # Original query for accessing thresholds


def build_plan(query: MetricQuery) -> Optional[Plan]:
    """
    Build an execution plan from a MetricQuery.
    
    DSL v1.2 changes:
    - Returns None for non-metrics queries (providers, entities)
    - These queries are handled directly in the executor
    - Only metrics and comparison queries need a plan with time ranges and derived metric logic
    
    Args:
        query: Validated DSL query
        
    Returns:
        Low-level execution plan for metrics queries, or None for others
        
    Examples:
        >>> from app.dsl.schema import MetricQuery, TimeRange, Filters, QueryType
        >>> 
        >>> # Metrics query: returns Plan
        >>> q = MetricQuery(
        ...     query_type=QueryType.METRICS,
        ...     metric="roas",
        ...     time_range=TimeRange(last_n_days=7),
        ...     compare_to_previous=True
        ... )
        >>> plan = build_plan(q)
        >>> plan.derived
        'roas'
        >>> plan.base_measures
        ['revenue', 'spend']
        >>> 
        >>> # Providers query: returns None (no plan needed)
        >>> q2 = MetricQuery(query_type=QueryType.PROVIDERS)
        >>> build_plan(q2)
        None
        >>> 
        >>> # Comparison query: returns Plan
        >>> q3 = MetricQuery(
        ...     query_type=QueryType.COMPARISON,
        ...     comparison_type="entity_vs_entity",
        ...     comparison_entities=["Holiday Sale", "App Install"],
        ...     comparison_metrics=["roas", "revenue"],
        ...     time_range=TimeRange(last_n_days=7)
        ... )
        >>> plan = build_plan(q3)
        >>> plan.base_measures
        ['revenue', 'spend', 'revenue', 'spend']
    
    Logic:
    1. Check query_type: if not metrics or comparison, return None (executor handles it)
    2. Resolve time range (relative → absolute dates)
    3. Determine if metric is derived (roas/cpa/cvr) or base
    4. Map derived metrics to required base measures
    5. Set flags for timeseries and previous period
    6. Pass through filters and breakdown settings
    """
    # DSL v1.2: Non-metrics queries don't need a plan
    # Providers and entities queries are handled directly in executor
    # Step 3: Comparison queries also need a plan
    if query.query_type not in ["metrics", "comparison"]:
        return None
    
    # Metrics queries require a metric field
    if query.query_type == "metrics" and not query.metric:
        raise ValueError("metric field is required for metrics queries")
    
    # Comparison queries require comparison_metrics field
    if query.query_type == "comparison" and not query.comparison_metrics:
        raise ValueError("comparison_metrics field is required for comparison queries")
    
    # Phase 7: Handle multi-metric queries
    # Normalize metric to list for consistent processing
    if query.query_type == "metrics":
        if isinstance(query.metric, str):
            metrics = [query.metric]
        else:
            metrics = query.metric
    else:  # comparison query
        metrics = query.comparison_metrics
    
    # Step 1: Resolve time range to absolute dates
    # For metrics queries, use default if not specified
    if not query.time_range:
        query.time_range = TimeRange(last_n_days=7)
    
    if query.time_range.start and query.time_range.end:
        # Absolute date range provided
        # Ensure they're date objects (Pydantic should handle this, but be defensive)
        start = query.time_range.start
        end = query.time_range.end
        
        # Convert strings to date objects if needed
        if isinstance(start, str):
            from datetime import datetime as dt
            start = dt.fromisoformat(start).date()
        if isinstance(end, str):
            from datetime import datetime as dt
            end = dt.fromisoformat(end).date()
    else:
        # Relative date range (last_n_days)
        timeframe_desc = query.timeframe_description.lower() if query.timeframe_description else ""
        if timeframe_desc == "yesterday":
            end = date.today() - timedelta(days=1)
            start = end
        elif timeframe_desc == "today":
            start = date.today()
            end = start
        else:
            end = date.today()
            days = query.time_range.last_n_days or 7
            start = end - timedelta(days=days - 1)  # -1 because range is inclusive
    
    # Step 2: Determine base measures needed for all metrics
    # Collect all unique base measures required by the requested metrics
    derived_metrics = {"roas", "cpa", "cvr", "cpc", "cpm", "cpl", "cpi", "cpp", "poas", "arpv", "aov", "ctr"}
    all_base_measures = set()
    
    for metric in metrics:
        if metric == "roas":
            all_base_measures.update(["spend", "revenue"])
        elif metric == "cpa":
            all_base_measures.update(["spend", "conversions"])
        elif metric == "cvr":
            all_base_measures.update(["clicks", "conversions"])
        elif metric == "cpc":
            all_base_measures.update(["spend", "clicks"])
        elif metric == "cpm":
            all_base_measures.update(["spend", "impressions"])
        elif metric == "cpl":
            all_base_measures.update(["spend", "leads"])
        elif metric == "cpi":
            all_base_measures.update(["spend", "installs"])
        elif metric == "cpp":
            all_base_measures.update(["spend", "purchases"])
        elif metric == "poas":
            all_base_measures.update(["profit", "spend"])
        elif metric == "arpv":
            all_base_measures.update(["revenue", "visitors"])
        elif metric == "aov":
            all_base_measures.update(["revenue", "purchases"])
        elif metric == "ctr":
            all_base_measures.update(["clicks", "impressions"])
        else:
            # Base metric: just need itself
            all_base_measures.add(metric)
    
    base_measures = list(all_base_measures)
    
    # For single metric queries, keep the original derived logic
    # For multi-metric queries, we'll handle derivation in the executor
    if len(metrics) == 1:
        is_derived = metrics[0] in derived_metrics
        derived = metrics[0] if is_derived else None
    else:
        # Multi-metric: no single derived metric
        derived = None
    
    # Step 4: Compute timeseries only when needed (PERFORMANCE OPTIMIZATION 2025-10-29)
    # WHY: Timeseries queries add 10-20 seconds to simple metric queries
    # WHEN to compute:
    # - Breakdown queries (for sparklines in UI)
    # - Comparison queries (for trend visualization)
    # - When explicitly requested
    # WHEN to skip:
    # - Simple metric queries with no breakdown (e.g., "what is my CPC this month?")
    need_timeseries = query.breakdown is not None or query.compare_to_previous
    
    # Step 5: Pass through settings from DSL
    return Plan(
        start=start,
        end=end,
        group_by=query.group_by,
        breakdown=query.breakdown,
        derived=derived,
        need_timeseries=need_timeseries,
        need_previous=query.compare_to_previous,
        base_measures=sorted(base_measures),  # Sort for consistency
        filters=query.filters.model_dump() if hasattr(query.filters, 'model_dump') else query.filters,
        top_n=query.top_n,
        sort_order=query.sort_order,  # NEW: Pass sort order for breakdown ordering
        query=query  # Include original query for accessing thresholds
    )


def explain_plan(plan: Plan) -> str:
    """
    Generate human-readable explanation of a query plan.
    
    Useful for debugging and telemetry.
    
    Args:
        plan: Execution plan
        
    Returns:
        Human-readable description
        
    Example:
        >>> plan = Plan(start=date(2025,9,24), end=date(2025,9,30), ...)
        >>> print(explain_plan(plan))
        Query: 2025-09-24 to 2025-09-30 (7 days)
        Metric: roas (derived from revenue, spend)
        Breakdown: none
        Comparison: yes
        Timeseries: yes
    """
    days = (plan.end - plan.start).days + 1
    
    parts = [
        f"Query: {plan.start} to {plan.end} ({days} days)",
    ]
    
    if plan.derived:
        parts.append(f"Metric: {plan.derived} (derived from {', '.join(plan.base_measures)})")
    else:
        parts.append(f"Metric: {plan.base_measures[0]} (base)")
    
    if plan.breakdown:
        parts.append(f"Breakdown: {plan.breakdown} (top {plan.top_n})")
    else:
        parts.append(f"Breakdown: none")
    
    parts.append(f"Comparison: {'yes' if plan.need_previous else 'no'}")
    parts.append(f"Timeseries: {'yes' if plan.need_timeseries else 'no'}")
    
    if plan.filters:
        filter_strs = [f"{k}={v}" for k, v in plan.filters.items() if v is not None]
        if filter_strs:
            parts.append(f"Filters: {', '.join(filter_strs)}")
    
    return "\n".join(parts)
