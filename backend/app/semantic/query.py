"""
Semantic Query Model
====================

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Active

Composable query structure that replaces the rigid DSL.
This is what the LLM outputs and what the compiler consumes.

WHY THIS FILE EXISTS
--------------------
The previous DSL (app/dsl/schema.py) had mutually exclusive fields:
- `breakdown` OR `compare_to_previous`, never both
- `entity_timeseries` OR `comparison`, never both

This prevented queries like:
    "compare CPC this week vs last week for top 3 ads"

Which needs breakdown (top 3 ads) + comparison (vs last week) TOGETHER.

COMPOSABILITY MODEL
-------------------
Components can be combined freely:

    breakdown + comparison = per-entity comparison data
                            (each ad's CPC this week vs last week)

    breakdown + timeseries = per-entity timeseries (multi-line chart)
                            (each ad's daily CPC over time)

    breakdown + comparison + timeseries = full flexibility
                            (each ad's daily CPC, both periods)

RELATED FILES
-------------
- app/semantic/model.py: Metric/dimension definitions
- app/semantic/compiler.py: Compiles these queries to data
- app/semantic/validator.py: Validates these queries
- app/semantic/security.py: Security checks
- app/nlp/translator.py: LLM outputs these queries
- docs/living-docs/SEMANTIC_LAYER_IMPLEMENTATION_PLAN.md: Full plan
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from datetime import date
from enum import Enum


# =============================================================================
# ENUMS: Type-safe classifications
# =============================================================================

class ComparisonType(Enum):
    """
    Type of time comparison.

    WHAT: Defines how to calculate the comparison period.

    WHY: Different comparison types serve different business needs:
    - PREVIOUS_PERIOD: "this week vs last week" - most common
    - YEAR_OVER_YEAR: "this month vs same month last year" - seasonality
    - CUSTOM: Advanced users with specific date ranges

    USAGE:
        comparison = Comparison(type=ComparisonType.PREVIOUS_PERIOD)
    """
    PREVIOUS_PERIOD = "previous_period"  # Default: compare to previous N days
    YEAR_OVER_YEAR = "year_over_year"    # Compare to same period last year
    CUSTOM = "custom"                     # Custom date range for comparison


class OutputFormat(Enum):
    """
    Preferred output format for the response.

    WHAT: Hints to the visual builder about desired presentation.

    WHY: Some questions have natural formats:
    - "Show me a chart" -> CHART
    - "List the top campaigns" -> TABLE
    - "What's my ROAS?" -> TEXT (simple answer)

    Note: AUTO lets the system choose based on query characteristics.

    USAGE:
        query = SemanticQuery(..., output_format=OutputFormat.CHART)
    """
    AUTO = "auto"      # System chooses based on query type
    CHART = "chart"    # Force chart visualization
    TABLE = "table"    # Force table visualization
    TEXT = "text"      # Force text-only response


# =============================================================================
# DATA CLASSES: Query components
# =============================================================================

@dataclass
class TimeRange:
    """
    Time range specification for the query.

    WHAT: Defines the time period to query data for.

    WHY: Every metric query needs a time scope. This supports:
    - Relative: "last 7 days" (last_n_days=7)
    - Absolute: "Nov 1 to Nov 30" (start, end)

    INVARIANT: Either last_n_days OR (start, end), never both.
    The validator enforces this constraint.

    PARAMETERS:
        start: Start date for absolute range (inclusive)
        end: End date for absolute range (inclusive)
        last_n_days: Number of days from today (relative range)

    EXAMPLES:
        # Relative: Last 7 days
        TimeRange(last_n_days=7)

        # Absolute: November 2025
        TimeRange(
            start=date(2025, 11, 1),
            end=date(2025, 11, 30)
        )
    """
    start: Optional[date] = None
    end: Optional[date] = None
    last_n_days: Optional[int] = None

    def is_relative(self) -> bool:
        """
        Check if this is a relative time range.

        RETURNS:
            True if using last_n_days, False if using start/end
        """
        return self.last_n_days is not None

    def is_absolute(self) -> bool:
        """
        Check if this is an absolute time range.

        RETURNS:
            True if using start/end, False if using last_n_days
        """
        return self.start is not None or self.end is not None

    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization.

        RETURNS:
            Dict with either last_n_days OR start/end
        """
        if self.last_n_days:
            return {"last_n_days": self.last_n_days}
        return {
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
        }


@dataclass
class Breakdown:
    """
    Breakdown specification for grouping data.

    WHAT: Defines how to slice/dice the data by a dimension.

    WHY: Breakdowns answer questions like:
    - "Show me spend BY campaign" (dimension=entity, level=campaign)
    - "Show me revenue BY platform" (dimension=provider)
    - "Show me clicks BY day" (dimension=time, granularity=day)

    PARAMETERS:
        dimension: What dimension to group by ("entity", "provider", "time")
        level: For entity dimension - hierarchy level ("campaign", "adset", "ad")
        granularity: For time dimension - time bucket ("day", "week", "month")
        limit: Maximum items to return (1-50, default 5)
        sort_order: How to sort results ("asc" or "desc", default "desc")

    DIMENSION TYPES:
        entity:
            - Groups by ad entity (campaign/adset/ad)
            - Requires `level` parameter
            - Supports `limit` for "top N"

        provider:
            - Groups by ad platform (google, meta, tiktok)
            - No additional parameters needed

        time:
            - Groups by time bucket
            - Requires `granularity` parameter

    EXAMPLES:
        # Top 5 campaigns
        Breakdown(dimension="entity", level="campaign", limit=5)

        # All ads sorted by metric ascending
        Breakdown(dimension="entity", level="ad", limit=50, sort_order="asc")

        # By platform
        Breakdown(dimension="provider")

        # Daily breakdown
        Breakdown(dimension="time", granularity="day")
    """
    dimension: str
    level: Optional[str] = None       # For entity dimension
    granularity: Optional[str] = None  # For time dimension
    limit: int = 5                     # Max items (1-50)
    sort_order: str = "desc"           # "asc" or "desc"

    def is_entity_breakdown(self) -> bool:
        """
        Check if this is an entity breakdown.

        RETURNS:
            True if dimension is "entity"
        """
        return self.dimension == "entity"

    def is_time_breakdown(self) -> bool:
        """
        Check if this is a time breakdown.

        RETURNS:
            True if dimension is "time"
        """
        return self.dimension == "time"

    def is_provider_breakdown(self) -> bool:
        """
        Check if this is a provider breakdown.

        RETURNS:
            True if dimension is "provider"
        """
        return self.dimension == "provider"

    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization.

        RETURNS:
            Dict with all breakdown parameters
        """
        return {
            "dimension": self.dimension,
            "level": self.level,
            "granularity": self.granularity,
            "limit": self.limit,
            "sort_order": self.sort_order,
        }


@dataclass
class Comparison:
    """
    Time comparison specification.

    WHAT: Defines comparison to a previous time period.

    WHY: Comparisons answer questions like:
    - "How does this week compare to last week?"
    - "Is my CPC better than before?"
    - "Show me year-over-year growth"

    PARAMETERS:
        type: Type of comparison (previous_period, year_over_year, custom)
        include_timeseries: Also fetch daily data for both periods

    COMPARISON TYPES:
        previous_period:
            - Compares to the immediately preceding period
            - 7-day query → compares to previous 7 days
            - Most common for weekly/monthly reviews

        year_over_year:
            - Compares to same period last year
            - Useful for seasonal businesses
            - E.g., November 2025 vs November 2024

        custom:
            - Future: Custom comparison date range
            - Not yet implemented

    EXAMPLES:
        # Simple comparison to previous period
        Comparison(type=ComparisonType.PREVIOUS_PERIOD)

        # Comparison with timeseries data for both periods
        Comparison(
            type=ComparisonType.PREVIOUS_PERIOD,
            include_timeseries=True
        )
    """
    type: ComparisonType = ComparisonType.PREVIOUS_PERIOD
    include_timeseries: bool = False

    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization.

        RETURNS:
            Dict with comparison type and timeseries flag
        """
        return {
            "type": self.type.value,
            "include_timeseries": self.include_timeseries,
        }


@dataclass
class Filter:
    """
    Filter specification for narrowing results.

    WHAT: Defines conditions to filter the data.

    WHY: Filters answer questions like:
    - "Show me only Meta campaigns"
    - "What's the CPC for 'Brand Campaign'?"
    - "Exclude paused campaigns"

    PARAMETERS:
        field: Field to filter on (provider, level, status, entity_name, etc.)
        operator: Comparison operator (=, !=, >, <, in, contains)
        value: Value to compare against

    SUPPORTED FIELDS:
        provider:    Platform (google, meta, tiktok)
        level:       Entity type (campaign, adset, ad)
        status:      Entity status (active, paused, etc.)
        entity_name: Name of campaign/adset/ad (supports contains)
        entity_id:   ID of specific entity

    OPERATORS:
        =:        Exact match (provider = "meta")
        !=:       Not equal (status != "paused")
        >:        Greater than (spend > 100)
        <:        Less than (cpc < 2.50)
        >=:       Greater than or equal
        <=:       Less than or equal
        in:       In list (provider in ["meta", "google"])
        contains: Substring match (entity_name contains "Brand")

    EXAMPLES:
        # Only Meta campaigns
        Filter(field="provider", operator="=", value="meta")

        # Campaigns containing "Brand"
        Filter(field="entity_name", operator="contains", value="Brand")

        # Multiple platforms
        Filter(field="provider", operator="in", value=["meta", "google"])
    """
    field: str
    operator: str
    value: Any

    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization.

        RETURNS:
            Dict with field, operator, and value
        """
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
        }


@dataclass
class SemanticQuery:
    """
    Composable query that can express any valid metric question.

    WHAT: The core query structure for the semantic layer.

    WHY: Unlike the DSL, these components COMPOSE freely:
    - breakdown + comparison = per-entity comparison data
    - breakdown + timeseries = per-entity timeseries (multi-line chart)
    - All three = full flexibility

    This enables previously impossible queries like:
        "compare CPC this week vs last week for top 3 ads"

    PARAMETERS:
        metrics: One or more metrics to calculate (required)
        time_range: Time period for the query (required)
        breakdown: Optional grouping by dimension
        comparison: Optional comparison to previous period
        include_timeseries: Include daily/hourly data
        filters: Optional filters to narrow results
        output_format: Preferred output format (chart, table, text, auto)
        metric_inferred: True if metric was auto-selected (not in question)

    COMPOSITION RULES:
        metrics only:
            → Simple summary (total spend, overall ROAS)

        metrics + breakdown:
            → Grouped summary (spend by campaign)

        metrics + comparison:
            → Period comparison (this week vs last week)

        metrics + breakdown + comparison:
            → Per-entity comparison (KEY FEATURE!)
            → Each entity's metrics for both periods

        metrics + timeseries:
            → Daily/weekly trend data

        metrics + breakdown + timeseries:
            → Per-entity trends (multi-line chart)

    EXAMPLES:
        Simple metric:
            SemanticQuery(
                metrics=["roas"],
                time_range=TimeRange(last_n_days=7)
            )

        Breakdown:
            SemanticQuery(
                metrics=["cpc"],
                time_range=TimeRange(last_n_days=7),
                breakdown=Breakdown(dimension="entity", level="ad", limit=3)
            )

        Full composition (THE MISSING QUERY):
            SemanticQuery(
                metrics=["cpc"],
                time_range=TimeRange(last_n_days=7),
                breakdown=Breakdown(dimension="entity", level="ad", limit=3),
                comparison=Comparison(type=ComparisonType.PREVIOUS_PERIOD),
                include_timeseries=True
            )

    RELATED FILES:
        - app/semantic/compiler.py: Compiles this to data
        - app/semantic/validator.py: Validates this structure
        - app/nlp/translator.py: LLM outputs this format
    """
    # Required fields
    metrics: List[str]
    time_range: TimeRange

    # Optional composable components - these COMPOSE freely
    breakdown: Optional[Breakdown] = None
    comparison: Optional[Comparison] = None
    include_timeseries: bool = False

    # Filters
    filters: List[Filter] = field(default_factory=list)

    # Output preferences
    output_format: OutputFormat = OutputFormat.AUTO

    # Metadata
    metric_inferred: bool = False

    # -------------------------------------------------------------------------
    # Query Type Detection Methods
    # -------------------------------------------------------------------------

    def has_breakdown(self) -> bool:
        """
        Check if query has a breakdown component.

        RETURNS:
            True if breakdown is specified
        """
        return self.breakdown is not None

    def has_comparison(self) -> bool:
        """
        Check if query has a comparison component.

        RETURNS:
            True if comparison is specified
        """
        return self.comparison is not None

    def has_filters(self) -> bool:
        """
        Check if query has any filters.

        RETURNS:
            True if at least one filter is specified
        """
        return len(self.filters) > 0

    def needs_entity_comparison(self) -> bool:
        """
        Check if query needs per-entity comparison data.

        WHAT: Determines if we need to fetch comparison data for each entity.

        WHY: This is the KEY composition that was missing in the old DSL:
            breakdown (entity) + comparison = per-entity previous period data

        Enables queries like:
            "compare CPC this week vs last week for top 3 ads"

        RETURNS:
            True if breakdown is entity-based AND comparison is requested

        EXAMPLE:
            query = SemanticQuery(
                metrics=["cpc"],
                time_range=TimeRange(last_n_days=7),
                breakdown=Breakdown(dimension="entity", level="ad", limit=3),
                comparison=Comparison(type=ComparisonType.PREVIOUS_PERIOD)
            )
            query.needs_entity_comparison()  # True
        """
        return (
            self.has_breakdown()
            and self.breakdown.dimension == "entity"
            and self.has_comparison()
        )

    def needs_entity_timeseries(self) -> bool:
        """
        Check if query needs per-entity timeseries data.

        WHAT: Determines if we need daily data for each entity separately.

        WHY: This enables multi-line charts where each line is an entity.
            E.g., "show me daily CPC for top 3 campaigns"

        RETURNS:
            True if breakdown is entity-based AND timeseries is requested

        EXAMPLE:
            query = SemanticQuery(
                metrics=["cpc"],
                time_range=TimeRange(last_n_days=7),
                breakdown=Breakdown(dimension="entity", level="campaign", limit=3),
                include_timeseries=True
            )
            query.needs_entity_timeseries()  # True
        """
        return (
            self.has_breakdown()
            and self.breakdown.dimension == "entity"
            and self.include_timeseries
        )

    def needs_provider_breakdown(self) -> bool:
        """
        Check if query needs data broken down by provider/platform.

        RETURNS:
            True if breakdown dimension is "provider"

        EXAMPLE:
            query = SemanticQuery(
                metrics=["spend"],
                time_range=TimeRange(last_n_days=7),
                breakdown=Breakdown(dimension="provider")
            )
            query.needs_provider_breakdown()  # True
        """
        return (
            self.has_breakdown()
            and self.breakdown.dimension == "provider"
        )

    def needs_time_breakdown(self) -> bool:
        """
        Check if query needs data broken down by time (timeseries).

        RETURNS:
            True if breakdown dimension is "time"

        EXAMPLE:
            query = SemanticQuery(
                metrics=["spend"],
                time_range=TimeRange(last_n_days=30),
                breakdown=Breakdown(dimension="time", granularity="week")
            )
            query.needs_time_breakdown()  # True
        """
        return (
            self.has_breakdown()
            and self.breakdown.dimension == "time"
        )

    # -------------------------------------------------------------------------
    # Accessor Methods
    # -------------------------------------------------------------------------

    def get_primary_metric(self) -> str:
        """
        Get the first/primary metric.

        WHAT: Returns the main metric for the query.

        WHY: Many operations need a single metric (sorting, charts).

        RETURNS:
            First metric name, or "spend" as fallback

        EXAMPLE:
            query = SemanticQuery(metrics=["cpc", "ctr"], ...)
            query.get_primary_metric()  # "cpc"
        """
        return self.metrics[0] if self.metrics else "spend"

    def get_entity_level(self) -> Optional[str]:
        """
        Get the entity level from breakdown, if entity breakdown.

        RETURNS:
            Entity level ("campaign", "adset", "ad") or None
        """
        if self.has_breakdown() and self.breakdown.dimension == "entity":
            return self.breakdown.level
        return None

    def get_breakdown_limit(self) -> int:
        """
        Get the limit from breakdown, with default.

        RETURNS:
            Limit value (default 5 if no breakdown)
        """
        if self.has_breakdown():
            return self.breakdown.limit
        return 5

    # -------------------------------------------------------------------------
    # Serialization Methods
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization.

        WHAT: Converts the query to a JSON-serializable dict.

        WHY: Used for:
        - Logging queries
        - Caching query results
        - Sending to frontend
        - Debugging

        RETURNS:
            Dict representation of the query
        """
        result = {
            "metrics": self.metrics,
            "time_range": self.time_range.to_dict(),
            "include_timeseries": self.include_timeseries,
            "output_format": self.output_format.value,
            "metric_inferred": self.metric_inferred,
        }

        if self.breakdown:
            result["breakdown"] = self.breakdown.to_dict()

        if self.comparison:
            result["comparison"] = self.comparison.to_dict()

        if self.filters:
            result["filters"] = [f.to_dict() for f in self.filters]

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> 'SemanticQuery':
        """
        Create SemanticQuery from dictionary.

        WHAT: Deserializes a dict back into a SemanticQuery.

        WHY: Used for:
        - Parsing LLM output
        - Loading cached queries
        - API input handling

        PARAMETERS:
            data: Dict with query fields (typically from JSON)

        RETURNS:
            SemanticQuery instance

        RAISES:
            KeyError: If required fields are missing
            ValueError: If values are invalid

        EXAMPLE:
            data = {
                "metrics": ["cpc"],
                "time_range": {"last_n_days": 7},
                "breakdown": {"dimension": "entity", "level": "ad", "limit": 3}
            }
            query = SemanticQuery.from_dict(data)
        """
        # Parse time_range
        time_range_data = data.get("time_range", {})
        time_range = TimeRange(
            start=date.fromisoformat(time_range_data["start"]) if time_range_data.get("start") else None,
            end=date.fromisoformat(time_range_data["end"]) if time_range_data.get("end") else None,
            last_n_days=time_range_data.get("last_n_days"),
        )

        # Parse breakdown (optional)
        breakdown = None
        if data.get("breakdown"):
            bd = data["breakdown"]
            breakdown = Breakdown(
                dimension=bd["dimension"],
                level=bd.get("level"),
                granularity=bd.get("granularity"),
                limit=bd.get("limit", 5),
                sort_order=bd.get("sort_order", "desc"),
            )

        # Parse comparison (optional)
        comparison = None
        if data.get("comparison"):
            comp = data["comparison"]
            comparison = Comparison(
                type=ComparisonType(comp.get("type", "previous_period")),
                include_timeseries=comp.get("include_timeseries", False),
            )

        # Parse filters (optional)
        filters = []
        for f in data.get("filters", []):
            filters.append(Filter(
                field=f["field"],
                operator=f["operator"],
                value=f["value"],
            ))

        # Parse output_format
        output_format_str = data.get("output_format", "auto")
        try:
            output_format = OutputFormat(output_format_str)
        except ValueError:
            output_format = OutputFormat.AUTO

        return cls(
            metrics=data.get("metrics", []),
            time_range=time_range,
            breakdown=breakdown,
            comparison=comparison,
            include_timeseries=data.get("include_timeseries", False),
            filters=filters,
            output_format=output_format,
            metric_inferred=data.get("metric_inferred", False),
        )

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """
        Detailed string representation for debugging.

        RETURNS:
            String with all query components
        """
        parts = [f"SemanticQuery(metrics={self.metrics}"]

        if self.time_range.last_n_days:
            parts.append(f"last_{self.time_range.last_n_days}d")
        else:
            parts.append(f"{self.time_range.start} to {self.time_range.end}")

        if self.breakdown:
            parts.append(f"breakdown={self.breakdown.dimension}/{self.breakdown.level}")

        if self.comparison:
            parts.append(f"comparison={self.comparison.type.value}")

        if self.include_timeseries:
            parts.append("timeseries=True")

        if self.filters:
            parts.append(f"filters={len(self.filters)}")

        return ", ".join(parts) + ")"

    def describe(self) -> str:
        """
        Human-readable description of the query.

        WHAT: Generates a natural language description.

        WHY: Used for:
        - Debugging and logging
        - User feedback
        - LLM context

        RETURNS:
            Human-friendly query description

        EXAMPLE:
            query.describe()
            # "CPC for top 3 ads, last 7 days, compared to previous period"
        """
        parts = []

        # Metrics
        metric_names = ", ".join(self.metrics).upper()
        parts.append(metric_names)

        # Breakdown
        if self.breakdown:
            if self.breakdown.dimension == "entity":
                parts.append(f"for top {self.breakdown.limit} {self.breakdown.level}s")
            elif self.breakdown.dimension == "provider":
                parts.append("by platform")
            elif self.breakdown.dimension == "time":
                parts.append(f"by {self.breakdown.granularity}")

        # Time range
        if self.time_range.last_n_days:
            parts.append(f"last {self.time_range.last_n_days} days")
        else:
            parts.append(f"{self.time_range.start} to {self.time_range.end}")

        # Comparison
        if self.comparison:
            if self.comparison.type == ComparisonType.PREVIOUS_PERIOD:
                parts.append("compared to previous period")
            elif self.comparison.type == ComparisonType.YEAR_OVER_YEAR:
                parts.append("year-over-year")

        # Timeseries
        if self.include_timeseries:
            parts.append("with daily data")

        # Filters
        if self.filters:
            filter_desc = []
            for f in self.filters:
                filter_desc.append(f"{f.field} {f.operator} {f.value}")
            parts.append(f"filtered by: {', '.join(filter_desc)}")

        return ", ".join(parts)
