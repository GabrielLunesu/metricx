"""
DSL Schema (v1.2)
=================

Pydantic models defining the query DSL contract.

DSL v1.2 adds support for non-metrics queries:
- metrics: Query for metrics data (spend, revenue, ROAS, etc.)
- providers: List distinct ad platforms in the workspace
- entities: List entities (campaigns/adsets/ads) with filters

Related files:
- app/dsl/validate.py: Validation and repair logic
- app/dsl/planner.py: Converts these models into execution plans
- app/dsl/executor.py: Executes the plans
- app/nlp/translator.py: Translates natural language to these models
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Optional, List, Dict, Union, Any
from datetime import date

# Query types: different types of questions we can answer
class QueryType(str, Enum):
    """
    Type of query to execute.
    
    - METRICS: Aggregate metrics data (spend, revenue, ROAS, etc.)
    - PROVIDERS: List distinct ad platforms (providers) in workspace
    - ENTITIES: List entities (campaigns, adsets, ads) with filters
    - COMPARISON: Compare metrics between entities or time periods
    
    Example questions by type:
    - metrics: "What's my ROAS this week?"
    - providers: "Which platforms am I advertising on?"
    - entities: "List my active campaigns"
    - comparison: "Compare Holiday Sale vs App Install campaign ROAS"
    """
    METRICS = "metrics"
    PROVIDERS = "providers"
    ENTITIES = "entities"
    COMPARISON = "comparison"

# Metric types: base metrics (directly stored) and derived metrics (computed)
# Derived Metrics v1: Extended with new base measures and derived metrics
Metric = Literal[
    # Original base measures
    "spend",        # Base: ad spend amount
    "revenue",      # Base: revenue generated
    "clicks",       # Base: number of clicks
    "impressions",  # Base: number of ad impressions
    "conversions",  # Base: number of conversions
    
    # Derived Metrics v1: New base measures
    "leads",        # Base: lead form submissions (Meta Lead Ads, etc.)
    "installs",     # Base: app installations (App Install campaigns)
    "purchases",    # Base: purchase events (ecommerce tracking)
    "visitors",     # Base: landing page visitors (analytics)
    "profit",       # Base: net profit (revenue - costs)
    
    # Original derived metrics
    "roas",         # Derived: revenue / spend (Return on Ad Spend)
    "cpa",          # Derived: spend / conversions (Cost per Acquisition)
    "cvr",          # Derived: conversions / clicks (Conversion Rate)
    
    # Derived Metrics v1: New cost/efficiency metrics
    "cpc",          # Derived: spend / clicks (Cost per Click)
    "cpm",          # Derived: (spend / impressions) * 1000 (Cost per Mille)
    "cpl",          # Derived: spend / leads (Cost per Lead)
    "cpi",          # Derived: spend / installs (Cost per Install)
    "cpp",          # Derived: spend / purchases (Cost per Purchase)
    
    # Derived Metrics v1: New value metrics
    "poas",         # Derived: profit / spend (Profit on Ad Spend)
    "arpv",         # Derived: revenue / visitors (Average Revenue per Visitor)
    "aov",          # Derived: revenue / conversions (Average Order Value)
    
    # Derived Metrics v1: New engagement metrics
    "ctr",          # Derived: clicks / impressions (Click-Through Rate)
]


class TimeRange(BaseModel):
    """
    Selectable time window for metrics queries.
    
    Supports two modes:
    1. Relative: last_n_days (e.g., last 7 days)
    2. Absolute: explicit start and end dates
    
    Examples:
        {"last_n_days": 7}
        {"start": "2025-09-01", "end": "2025-09-30"}
    
    Validation:
    - If using absolute dates, end must be >= start
    - last_n_days must be between 1 and 365
    """
    last_n_days: Optional[int] = Field(default=None, ge=1, le=365)
    start: Optional[date] = None
    end: Optional[date] = None

    @model_validator(mode='after')
    def validate_xor(self):
        has_relative = self.last_n_days is not None
        has_absolute = self.start is not None and self.end is not None

        if not (has_relative ^ has_absolute):
            raise ValueError(
                "TimeRange must specify either 'last_n_days' OR 'start'/'end' dates, not both. "
                "Use last_n_days for relative timeframes (last week, this month). "
                "Use start/end for absolute timeframes (September, specific date ranges)."
            )
        return self

    @field_validator("end")
    @classmethod
    def _check_range(cls, v, info):
        """Ensure end date is not before start date."""
        if v and info.data.get("start") and v < info.data["start"]:
            raise ValueError("end date must be >= start date")
        return v


class Filters(BaseModel):
    """
    Optional query filters. All filters are ANDed together.
    
    Fields:
    - provider: Filter by ad platform (google, meta, tiktok, other, mock)
    - level: Filter by entity hierarchy level (account, campaign, adset, ad)
    - entity_ids: Filter by specific entity UUIDs
    - status: Filter by entity status (active, paused)
    - entity_name: Filter by entity name (NEW - case-insensitive partial match)
    - metric_filters: Filter by metric values (NEW - Phase 7)
    
    Examples:
        {"provider": "google", "status": "active"}
        {"level": "campaign", "entity_ids": ["uuid1", "uuid2"]}
        {"entity_name": "Holiday Sale"}  # NEW - matches "Holiday Sale - Purchases"
        {"level": "campaign", "entity_name": "Sale"}  # Matches all campaigns with "Sale"
        {"metric_filters": [{"metric": "roas", "operator": ">", "value": 4}]}  # NEW - Phase 7
    
    Named Entity Filtering (NEW):
    - Case-insensitive: "HOLIDAY" = "holiday" = "Holiday"
    - Partial match: "Sale" matches "Holiday Sale - Purchases", "Summer Sale Campaign"
    - SQL-safe: Uses ILIKE (no injection risk)
    - Enables natural queries: "How is Holiday Sale campaign performing?"
    """
    provider: Optional[str] = Field(
        default=None,
        description="Ad platform provider filter"
    )
    level: Optional[Literal["account", "campaign", "adset", "ad"]] = Field(
        default=None,
        description="Entity hierarchy level filter"
    )
    entity_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific entity UUIDs to include"
    )
    status: Optional[Literal["active", "paused"]] = Field(
        default=None,
        description="Entity status filter"
    )
    entity_name: Optional[str] = Field(
        default=None,
        description="Filter by entity name (case-insensitive partial match). Example: 'holiday' matches 'Holiday Sale - Purchases'"
    )
    
    # Phase 7: Metric value filtering
    metric_filters: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Filter entities based on metric values. Example: [{'metric': 'roas', 'operator': '>', 'value': 4}]"
    )


class Thresholds(BaseModel):
    """
    Optional significance guards to avoid outlier 'winners' in breakdowns.
    
    WHY this exists:
    - Prevents tiny/noisy entities from appearing as "top performers"
    - Example: Campaign with $1 spend and $10 revenue shows 10× ROAS, but not meaningful
    - Applied as HAVING constraints on grouped aggregates (only affects breakdowns)
    
    IMPORTANT:
    - Thresholds NEVER affect summary aggregates (total workspace metrics)
    - Only applied when breakdown is requested (group_by != "none")
    - All thresholds are ANDed together (entity must meet ALL if specified)
    
    Fields:
    - min_spend: Minimum total spend for inclusion (dollars)
    - min_clicks: Minimum total clicks for inclusion (count)
    - min_conversions: Minimum total conversions for inclusion (count)
    
    Examples:
        # Ignore campaigns with < $50 spend
        {"min_spend": 50.0}
        
        # Require both spend and conversions
        {"min_spend": 50.0, "min_conversions": 5}
        
        # CTR queries: require meaningful click volume
        {"min_clicks": 100}
    
    Use cases:
    - ROAS queries: Set min_spend to ignore tiny tests
    - CPA queries: Set min_conversions to avoid division by tiny numbers
    - CTR queries: Set min_clicks to require statistical significance
    
    Related:
    - Applied in: app/dsl/executor.py (HAVING clause on grouped queries)
    - Documented in: app/dsl/examples.md
    """
    min_spend: Optional[float] = Field(
        default=None,
        ge=0,
        description="Minimum total spend ($) for inclusion in breakdown"
    )
    min_clicks: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum total clicks for inclusion in breakdown"
    )
    min_conversions: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum total conversions for inclusion in breakdown"
    )


class MetricQuery(BaseModel):
    """
    DSL contract for all query types (v1.2).
    
    This is the validated structure that the executor uses to run queries.
    The LLM outputs JSON matching this schema, which gets validated via Pydantic.
    
    DSL v1.2 Changes:
    - Added query_type field to support providers and entities queries
    - Made metric and time_range optional (not needed for providers/entities)
    - Kept all other fields for backward compatibility
    
    Fields:
    - query_type: Type of query (metrics, providers, entities)
    - metric: Which metric(s) to aggregate (required for metrics queries, supports single metric or list)
    - time_range: Time window for the query (optional for providers/entities)
    - compare_to_previous: Whether to include previous period comparison
    - group_by: Grouping dimension (none = single aggregate)
    - breakdown: Driver analysis dimension (shows top movers)
    - top_n: How many items to return in breakdown or entities list
    - filters: Optional scoping filters
    
    Examples:
        # Single metric query: "What's my ROAS this week?"
        {
            "query_type": "metrics",
            "metric": "roas",
            "time_range": {"last_n_days": 7},
            "compare_to_previous": false,
            "group_by": "none",
            "breakdown": null,
            "filters": {}
        }
        
        # Multi-metric query: "What's my spend, revenue, and ROAS this week?"
        {
            "query_type": "metrics",
            "metric": ["spend", "revenue", "roas"],
            "time_range": {"last_n_days": 7},
            "compare_to_previous": false,
            "group_by": "none",
            "breakdown": null,
            "filters": {}
        }
        
        # Providers query: "Which platforms am I running ads on?"
        {
            "query_type": "providers"
        }
        
        # Entities query: "List my active campaigns"
        {
            "query_type": "entities",
            "filters": {"level": "campaign", "status": "active"},
            "top_n": 10
        }
    
    Validation notes:
    - For metrics queries: metric field is required
    - For providers/entities queries: metric and time_range are optional
    - Filters are applied to all query types where applicable
    
    Related:
    - Consumed by: app/dsl/planner.py, app/dsl/executor.py
    - Generated by: app/nlp/translator.py
    """
    query_type: QueryType = Field(
        default=QueryType.METRICS,
        description="Type of query to execute (metrics, providers, entities)"
    )
    
    metric: Optional[Union[Metric, List[Metric]]] = Field(
        default=None,
        description="Metric(s) to aggregate (required for metrics queries, ignored otherwise). Can be a single metric or list of metrics for multi-metric queries."
    )
    
    time_range: Optional[TimeRange] = Field(
        default=None,
        description="Time window for the query (required for metrics, optional for others)"
    )
    
    compare_to_previous: bool = Field(
        default=False,
        description="Include previous period comparison for delta calculation (metrics only)"
    )
    
    group_by: Literal["none", "provider", "campaign", "adset", "ad", "day", "week", "month"] = Field(
        default="none",
        description="Grouping dimension (none = single aggregate value). Temporal values: day, week, month"
    )
    
    breakdown: Optional[Literal["provider", "campaign", "adset", "ad", "day", "week", "month"]] = Field(
        default=None,
        description="Breakdown dimension for driver analysis (top movers). Temporal values: day, week, month"
    )
    
    top_n: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of items to return in breakdown or entities list"
    )
    
    sort_order: Literal["asc", "desc"] = Field(
        default="desc",
        description="Sort order for breakdown results: 'desc' for highest first (default), 'asc' for lowest first"
    )
    
    filters: Filters = Field(
        default_factory=Filters,
        description="Optional scoping filters (ANDed together)"
    )
    
    thresholds: Optional[Thresholds] = Field(
        default=None,
        description="Optional significance guards for breakdowns (min spend/clicks/conversions)"
    )
    
    # Comparison query fields (NEW in Step 3)
    comparison_type: Optional[Literal["entity_vs_entity", "time_vs_time", "provider_vs_provider"]] = Field(
        default=None,
        description="Type of comparison for comparison queries"
    )
    
    comparison_entities: Optional[List[str]] = Field(
        default=None,
        description="List of entity names to compare (for entity_vs_entity comparisons)"
    )
    
    comparison_metrics: Optional[List[Metric]] = Field(
        default=None,
        description="List of metrics to compare (for multi-metric comparisons)"
    )
    
    # NEW in Phase 1.1
    question: Optional[str] = Field(None, description="Original user question for tense/context")
    timeframe_description: Optional[str] = Field(None, description="Natural language timeframe like 'last week', 'today'")
    
    # NEW: For context-aware empty result handling
    workspace_id: Optional[str] = Field(None, description="Workspace ID for enhanced context (e.g., entity counts)")
    
    @model_validator(mode='after')
    def set_timeframe_description(self):
        """Auto-generate timeframe description from time_range and question.
        
        Phase 2 fix: Extract timeframe from original question when possible,
        otherwise fall back to generating from time_range.
        """
        time_range = self.time_range
        
        # If timeframe already set explicitly, use it
        if self.timeframe_description:
            return self
        
        # Try to extract timeframe from original question
        if self.question:
            question_lower = self.question.lower()
            # Check for explicit timeframe phrases in the question
            if 'today' in question_lower:
                self.timeframe_description = 'today'
                return self
            elif 'yesterday' in question_lower:
                self.timeframe_description = 'yesterday'
                return self
            elif 'this week' in question_lower:
                self.timeframe_description = 'this week'
                return self
            elif 'this month' in question_lower:
                self.timeframe_description = 'this month'
                return self
            elif 'last week' in question_lower or 'past week' in question_lower:
                self.timeframe_description = 'last week'
                return self
            elif 'last month' in question_lower or 'past month' in question_lower:
                self.timeframe_description = 'last month'
                return self
        
        # Fallback: Auto-generate from time_range
        # Phase 2 fix: last_n_days: 1 should default to "yesterday" not "today"
        # because it represents the most recent complete day of data
        if time_range and hasattr(time_range, 'last_n_days') and time_range.last_n_days:
            if time_range.last_n_days == 1:
                self.timeframe_description = 'yesterday'  # Fixed: was 'today'
            elif time_range.last_n_days == 7:
                self.timeframe_description = 'last week'
            elif time_range.last_n_days == 30:
                self.timeframe_description = 'last month'
            elif time_range.last_n_days == 90:
                self.timeframe_description = 'last quarter'
            elif time_range.last_n_days == 365:
                self.timeframe_description = 'last year'
            else:
                self.timeframe_description = f'last {time_range.last_n_days} days'
        elif time_range and hasattr(time_range, 'start') and hasattr(time_range, 'end') and time_range.start and time_range.end:
            # Format dates nicely
            self.timeframe_description = f'from {time_range.start} to {time_range.end}'
        
        return self
    
    def model_dump_json_schema(self) -> dict:
        """Export JSON Schema for LLM structured outputs."""
        return self.model_json_schema()


class MetricResult(BaseModel):
    """
    Executor response structure.
    
    Fields:
    - summary: Main aggregated value for the metric
    - previous: Previous period value (if compare_to_previous=True)
    - delta_pct: Percentage change vs previous period
    - timeseries: Daily values over the selected period
    - breakdown: Top entities by the selected breakdown dimension
    - workspace_avg: Workspace-wide average for this metric (NEW in v2.0.1)
    
    Examples:
        # Simple aggregate result:
        {
            "summary": 2.5,
            "previous": 2.1,
            "delta_pct": 0.19,
            "timeseries": null,
            "breakdown": null,
            "workspace_avg": 2.3
        }
        
        # Result with breakdown:
        {
            "summary": 1250.0,
            "previous": null,
            "delta_pct": null,
            "timeseries": [
                {"date": "2025-09-01", "value": 125.0},
                {"date": "2025-09-02", "value": 130.5}
            ],
            "breakdown": [
                {"label": "Summer Sale", "value": 450.0},
                {"label": "Winter Campaign", "value": 320.0}
            ],
            "workspace_avg": 1150.0
        }
    
    Related:
    - Returned by: app/dsl/executor.py
    - Consumed by: app/services/qa_service.py
    """
    summary: Optional[float] = Field(
        default=None,
        description="Main aggregated metric value"
    )
    
    previous: Optional[float] = Field(
        default=None,
        description="Previous period value (for comparison)"
    )
    
    delta_pct: Optional[float] = Field(
        default=None,
        description="Percentage change vs previous period (0.19 = +19%)"
    )
    
    timeseries: Optional[List[Dict[str, Union[str, float, None]]]] = Field(
        default=None,
        description="Daily values: [{date: 'YYYY-MM-DD', value: 123.4}, ...]"
    )
    timeseries_previous: Optional[List[Dict[str, Union[str, float, None]]]] = Field(
        default=None,
        description="Previous period daily values for comparison overlays"
    )
    
    breakdown: Optional[List[Dict[str, Union[str, float, int, None]]]] = Field(
        default=None,
        description="Top entities: [{label: 'Campaign Name', value: 450.0, spend: 1234.5, clicks: 5678, conversions: 90}, ...]"
    )
    
    workspace_avg: Optional[float] = Field(
        default=None,
        description="Workspace-wide average for this metric over the same time range (NEW in v2.0.1)"
    )
