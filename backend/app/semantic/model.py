"""
Semantic Model Definition
=========================

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Active

Single source of truth for metrics and dimensions in metricx.
This model defines WHAT can be queried, not HOW.

WHY THIS FILE EXISTS
--------------------
Previously, metric knowledge was scattered across:
- app/dsl/schema.py (Metric type literal)
- app/metrics/registry.py (formulas and dependencies)
- app/answer/formatters.py (display formats)
- app/nlp/prompts.py (metric descriptions for LLM)

This file consolidates ALL metric knowledge into one place:
- What metrics exist
- How to display them
- What operations they support
- What dimensions they can combine with

DESIGN PRINCIPLES
-----------------
1. **Single Source of Truth**: All metric definitions in one place
2. **Declarative**: Define properties, don't implement logic
3. **Composable**: Metrics define what dimensions they support
4. **Type-Safe**: Frozen sets and enums prevent typos
5. **Reuses Existing Code**: Leverages app/metrics/registry.py for formulas

RELATIONSHIP TO EXISTING CODE
-----------------------------
This file DOES NOT replace app/metrics/registry.py. Instead:
- registry.py: Formula implementations and dependencies
- model.py: Semantic properties (display, composition rules, inverse)

We import from registry.py to avoid duplication of formula logic.

RELATED FILES
-------------
- app/metrics/registry.py: Formula implementations (REUSED)
- app/metrics/formulas.py: Calculation functions (REUSED)
- app/semantic/query.py: Query structure using these definitions
- app/semantic/security.py: Allowlists derived from these definitions
- docs/living-docs/SEMANTIC_LAYER_IMPLEMENTATION_PLAN.md: Full plan
"""

from dataclasses import dataclass
from typing import Dict, Optional, Set, FrozenSet
from enum import Enum

# Import existing metric knowledge to avoid duplication
from app.metrics.registry import (
    BASE_MEASURES,
    METRIC_REGISTRY,
    get_metric_format,
    is_inverse_metric as _is_inverse_metric,
)


# =============================================================================
# ENUMS: Type-safe classifications
# =============================================================================

class MetricType(Enum):
    """
    How to format and display metric values.

    Used by:
    - Visual builder for number formatting
    - Answer builder for natural language
    - API responses for frontend rendering

    Maps to app/answer/formatters.py format functions.
    """
    CURRENCY = "currency"      # $1,234.56 (spend, revenue, cpc, cpa, etc.)
    RATIO = "ratio"            # 2.45x (roas, poas)
    PERCENTAGE = "percentage"  # 4.2% (ctr, cvr)
    COUNT = "count"            # 1,234 (clicks, impressions, conversions)


class DimensionType(Enum):
    """
    Type of dimension for query building.

    Each type has different properties:
    - ENTITY: Hierarchical (campaign > adset > ad), supports limit/top_n
    - CATEGORICAL: Flat enumeration (provider: google, meta, tiktok)
    - TEMPORAL: Time-based grouping (day, week, month)
    """
    ENTITY = "entity"          # campaign, adset, ad (hierarchical)
    CATEGORICAL = "categorical" # provider, status (flat)
    TEMPORAL = "temporal"       # day, week, month (time-based)


class MetricCategory(Enum):
    """
    Semantic category for metric grouping.

    Used for:
    - Organizing metrics in UI
    - Suggesting related metrics
    - Default metric selection based on campaign goals
    """
    BASE = "base"              # Raw measures (spend, clicks, etc.)
    COST = "cost"              # Efficiency metrics (cpc, cpa, etc.)
    VALUE = "value"            # Return metrics (roas, aov, etc.)
    ENGAGEMENT = "engagement"  # Rate metrics (ctr, cvr)


# =============================================================================
# DATA CLASSES: Structured definitions
# =============================================================================

@dataclass(frozen=True)
class Metric:
    """
    Definition of a single metric.

    WHAT: Describes a metric's properties for the semantic layer.

    WHY: Centralizes all metric knowledge:
    - Name and display name
    - Data type for formatting
    - Business semantics (is lower better?)
    - Composition rules (what dimensions can it combine with?)

    PARAMETERS:
        name: Internal identifier (e.g., "roas")
        display_name: Human-readable name (e.g., "Return on Ad Spend")
        type: How to format values (currency, ratio, percentage, count)
        category: Semantic grouping (base, cost, value, engagement)
        inverse: True if lower values are better (cpc, cpa, etc.)
        supports_timeseries: Can show over time (most metrics can)
        supports_comparison: Can compare to previous period (most can)
        supports_breakdown: Can break down by dimension (most can)

    EXAMPLES:
        >>> METRICS["roas"]
        Metric(name='roas', display_name='Return on Ad Spend',
               type=MetricType.RATIO, inverse=False, ...)

        >>> METRICS["cpc"].inverse
        True  # Lower CPC is better

    USAGE:
        # Get metric definition
        metric = get_metric("roas")
        if metric.inverse:
            # Lower is better - adjust language
            best_performer_label = "lowest"
        else:
            best_performer_label = "highest"
    """
    name: str
    display_name: str
    type: MetricType
    category: MetricCategory
    inverse: bool = False  # True if lower is better (cost metrics)
    supports_timeseries: bool = True
    supports_comparison: bool = True
    supports_breakdown: bool = True


@dataclass(frozen=True)
class Dimension:
    """
    Definition of a dimension for grouping/filtering.

    WHAT: Describes how data can be sliced.

    WHY: Enables composable queries - any metric can be combined
    with any valid dimension.

    PARAMETERS:
        name: Internal identifier (e.g., "entity")
        display_name: Human-readable name (e.g., "Entity")
        type: Dimension type (entity, categorical, temporal)
        levels: For ENTITY type - hierarchy levels (campaign, adset, ad)
        granularities: For TEMPORAL type - time buckets (day, week, month)

    EXAMPLES:
        >>> DIMENSIONS["entity"]
        Dimension(name='entity', type=DimensionType.ENTITY,
                  levels=('campaign', 'adset', 'ad'))

        >>> DIMENSIONS["time"]
        Dimension(name='time', type=DimensionType.TEMPORAL,
                  granularities=('day', 'week', 'month'))
    """
    name: str
    display_name: str
    type: DimensionType
    levels: Optional[tuple] = None  # For ENTITY: hierarchy levels
    granularities: Optional[tuple] = None  # For TEMPORAL: time buckets


# =============================================================================
# METRIC DEFINITIONS
# =============================================================================
# These are derived from app/metrics/registry.py but with semantic properties

def _get_metric_type(name: str) -> MetricType:
    """
    Get MetricType for a metric name.

    Uses existing format info from registry.py.
    """
    fmt = get_metric_format(name)
    if fmt == "currency":
        return MetricType.CURRENCY
    elif fmt == "ratio":
        return MetricType.RATIO
    elif fmt == "percentage":
        return MetricType.PERCENTAGE
    else:
        return MetricType.COUNT


def _get_metric_category(name: str) -> MetricCategory:
    """
    Get MetricCategory for a metric name.

    Uses existing registry info.
    """
    if name in BASE_MEASURES:
        return MetricCategory.BASE
    if name in METRIC_REGISTRY:
        cat = METRIC_REGISTRY[name].get("category", "value")
        if cat == "cost":
            return MetricCategory.COST
        elif cat == "engagement":
            return MetricCategory.ENGAGEMENT
        else:
            return MetricCategory.VALUE
    return MetricCategory.BASE


# Build METRICS dictionary from existing definitions
METRICS: Dict[str, Metric] = {}

# Base measures
_BASE_DISPLAY_NAMES = {
    "spend": "Spend",
    "revenue": "Revenue",
    "profit": "Profit",
    "clicks": "Clicks",
    "impressions": "Impressions",
    "conversions": "Conversions",
    "leads": "Leads",
    "installs": "Installs",
    "purchases": "Purchases",
    "visitors": "Visitors",
}

for name in BASE_MEASURES:
    METRICS[name] = Metric(
        name=name,
        display_name=_BASE_DISPLAY_NAMES.get(name, name.title()),
        type=_get_metric_type(name),
        category=MetricCategory.BASE,
        inverse=False,  # Base measures are never inverse
    )

# Derived metrics
_DERIVED_DISPLAY_NAMES = {
    "cpc": "Cost per Click",
    "cpm": "Cost per 1K Impressions",
    "cpa": "Cost per Acquisition",
    "cpl": "Cost per Lead",
    "cpi": "Cost per Install",
    "cpp": "Cost per Purchase",
    "roas": "Return on Ad Spend",
    "poas": "Profit on Ad Spend",
    "aov": "Average Order Value",
    "arpv": "Average Revenue per Visitor",
    "ctr": "Click-through Rate",
    "cvr": "Conversion Rate",
}

for name, entry in METRIC_REGISTRY.items():
    METRICS[name] = Metric(
        name=name,
        display_name=_DERIVED_DISPLAY_NAMES.get(name, name.upper()),
        type=_get_metric_type(name),
        category=_get_metric_category(name),
        inverse=_is_inverse_metric(name),
    )


# =============================================================================
# DIMENSION DEFINITIONS
# =============================================================================

DIMENSIONS: Dict[str, Dimension] = {
    "entity": Dimension(
        name="entity",
        display_name="Entity",
        type=DimensionType.ENTITY,
        levels=("campaign", "adset", "ad"),
    ),
    "provider": Dimension(
        name="provider",
        display_name="Platform",
        type=DimensionType.CATEGORICAL,
    ),
    "time": Dimension(
        name="time",
        display_name="Time",
        type=DimensionType.TEMPORAL,
        granularities=("day", "week", "month"),
    ),
}


# =============================================================================
# FROZEN SETS FOR VALIDATION
# =============================================================================
# These are used by security.py for allowlist validation

ALLOWED_METRICS: FrozenSet[str] = frozenset(METRICS.keys())
ALLOWED_DIMENSIONS: FrozenSet[str] = frozenset(DIMENSIONS.keys())
ALLOWED_ENTITY_LEVELS: FrozenSet[str] = frozenset(["campaign", "adset", "ad"])
ALLOWED_TIME_GRANULARITIES: FrozenSet[str] = frozenset(["day", "week", "month"])
ALLOWED_PROVIDERS: FrozenSet[str] = frozenset(["google", "meta", "tiktok", "other", "mock"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_metric(name: str) -> Optional[Metric]:
    """
    Get metric definition by name.

    WHAT: Retrieves a Metric object for a given metric name.

    WHY: Provides safe access to metric properties without KeyError risk.

    PARAMETERS:
        name: Metric identifier (e.g., "roas", "spend", "cpc")

    RETURNS:
        Metric object if found, None otherwise

    EXAMPLES:
        >>> metric = get_metric("roas")
        >>> metric.display_name
        'Return on Ad Spend'

        >>> metric = get_metric("invalid")
        >>> metric is None
        True
    """
    return METRICS.get(name)


def get_dimension(name: str) -> Optional[Dimension]:
    """
    Get dimension definition by name.

    WHAT: Retrieves a Dimension object for a given dimension name.

    WHY: Provides safe access to dimension properties.

    PARAMETERS:
        name: Dimension identifier (e.g., "entity", "provider", "time")

    RETURNS:
        Dimension object if found, None otherwise

    EXAMPLES:
        >>> dim = get_dimension("entity")
        >>> dim.levels
        ('campaign', 'adset', 'ad')

        >>> dim = get_dimension("time")
        >>> dim.granularities
        ('day', 'week', 'month')
    """
    return DIMENSIONS.get(name)


def get_all_metric_names() -> Set[str]:
    """
    Get set of all valid metric names.

    WHAT: Returns all metric identifiers.

    WHY: Used for validation and autocompletion.

    RETURNS:
        Set of metric name strings

    EXAMPLES:
        >>> names = get_all_metric_names()
        >>> "roas" in names
        True
        >>> "invalid" in names
        False
    """
    return set(METRICS.keys())


def get_all_dimension_names() -> Set[str]:
    """
    Get set of all valid dimension names.

    WHAT: Returns all dimension identifiers.

    WHY: Used for validation.

    RETURNS:
        Set of dimension name strings
    """
    return set(DIMENSIONS.keys())


def is_inverse_metric(name: str) -> bool:
    """
    Check if a metric is inverse (lower is better).

    WHAT: Determines if lower values indicate better performance.

    WHY: Used for:
    - Correct "best/worst" language in answers
    - Proper sorting direction
    - Performance classification

    PARAMETERS:
        name: Metric identifier

    RETURNS:
        True if lower values are better (cost metrics)
        False if higher values are better (value/engagement metrics)

    EXAMPLES:
        >>> is_inverse_metric("cpc")
        True  # Lower cost per click = more efficient

        >>> is_inverse_metric("roas")
        False  # Higher return on ad spend = better

        >>> is_inverse_metric("ctr")
        False  # Higher click-through rate = better

    USAGE:
        Used in answer generation:
        "Campaign X had the {lowest if inverse else highest} {metric}"
    """
    metric = get_metric(name)
    return metric.inverse if metric else False


def get_metric_display_name(name: str) -> str:
    """
    Get human-readable display name for a metric.

    WHAT: Returns the formatted name for display.

    WHY: Used in answers and UI to show friendly metric names.

    PARAMETERS:
        name: Metric identifier

    RETURNS:
        Display name string, or titlecased name if not found

    EXAMPLES:
        >>> get_metric_display_name("roas")
        'Return on Ad Spend'

        >>> get_metric_display_name("cpc")
        'Cost per Click'
    """
    metric = get_metric(name)
    return metric.display_name if metric else name.title()
