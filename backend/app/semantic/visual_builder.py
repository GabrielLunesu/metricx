"""
Semantic Visual Builder
=======================

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Active

Builds visual payloads from SemanticQuery and CompilationResult.
This is the semantic layer replacement for app/answer/visual_builder.py.

WHY THIS FILE EXISTS
--------------------
The original visual_builder.py is tightly coupled to DSL structures.
This module works with SemanticQuery and CompilationResult, providing:
- Cleaner data flow
- Better support for entity_comparison and entity_timeseries
- Consistent chart specifications

VISUAL TYPES
------------
1. Summary Card: Single metric value with optional sparkline
2. Comparison Card: Current vs previous with delta
3. Entity Comparison: Per-entity comparison (THE KEY FEATURE)
4. Breakdown Bar: Top N entities by metric
5. Timeseries Line: Trend over time
6. Multi-line Entity: One line per entity
7. Data Table: Detailed breakdown data

OUTPUT FORMAT
-------------
{
    "cards": [
        {"id": "card-roas", "title": "ROAS", "value": 3.5, ...}
    ],
    "viz_specs": [
        {"id": "ts-roas", "type": "line", "series": [...], ...}
    ],
    "tables": [
        {"id": "table-breakdown", "columns": [...], "rows": [...]}
    ]
}

RELATED FILES
-------------
- app/semantic/query.py: SemanticQuery structure
- app/semantic/compiler.py: CompilationResult structure
- app/answer/visual_builder.py: OLD visual builder (DSL-based)
- app/answer/formatters.py: Shared value formatters
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.semantic.query import SemanticQuery, OutputFormat
from app.semantic.compiler import (
    CompilationResult,
    EntityComparisonItem,
    EntityTimeseriesItem,
)
from app.answer.formatters import format_metric_value, format_delta_pct

logger = logging.getLogger(__name__)


# =============================================================================
# METRIC DISPLAY NAMES
# =============================================================================

METRIC_DISPLAY_NAMES = {
    "roas": "ROAS",
    "poas": "POAS",
    "aov": "AOV",
    "cpc": "CPC",
    "cpa": "CPA",
    "cpm": "CPM",
    "cpl": "CPL",
    "cpi": "CPI",
    "cpp": "CPP",
    "ctr": "CTR",
    "cvr": "CVR",
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


def _metric_display_name(metric: str) -> str:
    """Get human-friendly metric display name."""
    return METRIC_DISPLAY_NAMES.get(metric.lower(), metric.upper())


# =============================================================================
# COLOR PALETTE
# =============================================================================

CHART_COLORS = [
    "#2563eb",  # Blue (primary)
    "#10b981",  # Emerald
    "#f59e0b",  # Amber
    "#ef4444",  # Red
    "#8b5cf6",  # Violet
    "#06b6d4",  # Cyan
    "#ec4899",  # Pink
    "#84cc16",  # Lime
]


# =============================================================================
# CARD BUILDERS
# =============================================================================

def build_summary_card(
    metric: str,
    value: Optional[float],
    previous: Optional[float] = None,
    delta_pct: Optional[float] = None,
    sparkline: Optional[List[Dict]] = None,
    timeframe: Optional[str] = None,
    workspace_avg: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Build a summary card for a single metric.

    WHAT: Creates a card showing metric value with optional comparison.

    WHY: Primary visualization for simple queries like "What's my ROAS?"

    PARAMETERS:
        metric: Metric name (e.g., "roas")
        value: Current metric value
        previous: Previous period value (optional)
        delta_pct: Percentage change (optional)
        sparkline: Mini timeseries data (optional)
        timeframe: Human-readable timeframe
        workspace_avg: Workspace average for context

    RETURNS:
        Card specification dict
    """
    return {
        "id": f"card-{metric}",
        "type": "summary",
        "title": _metric_display_name(metric),
        "metric": metric,
        "value": value,
        "formatted_value": format_metric_value(metric, value) if value is not None else None,
        "previous": previous,
        "delta_pct": delta_pct,
        "formatted_delta": format_delta_pct(delta_pct) if delta_pct is not None else None,
        "sparkline": sparkline,
        "timeframe": timeframe,
        "workspace_avg": workspace_avg,
    }


def build_entity_comparison_cards(
    metric: str,
    entity_comparison: List[EntityComparisonItem],
    timeframe: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Build cards for entity comparison (THE KEY FEATURE).

    WHAT: Creates comparison cards for each entity showing current vs previous.

    WHY: This is THE KEY FEATURE - per-entity comparison that was impossible
    with the old DSL.

    PARAMETERS:
        metric: Metric name
        entity_comparison: List of EntityComparisonItem
        timeframe: Human-readable timeframe

    RETURNS:
        List of entity comparison card specs

    EXAMPLE:
        [
            {
                "id": "entity-card-uuid1",
                "entity_name": "Ad A",
                "current_value": 1.50,
                "previous_value": 1.80,
                "delta_pct": -0.167,
                ...
            }
        ]
    """
    cards = []

    for i, item in enumerate(entity_comparison):
        card = {
            "id": f"entity-card-{i}",
            "type": "entity_comparison",
            "entity_id": item.entity_id,
            "entity_name": item.entity_name,
            "metric": metric,
            "current_value": item.current_value,
            "formatted_current": format_metric_value(metric, item.current_value),
            "previous_value": item.previous_value,
            "formatted_previous": format_metric_value(metric, item.previous_value) if item.previous_value else None,
            "delta_pct": item.delta_pct,
            "formatted_delta": format_delta_pct(item.delta_pct) if item.delta_pct is not None else None,
            "timeframe": timeframe,
            "color": CHART_COLORS[i % len(CHART_COLORS)],
        }
        cards.append(card)

    return cards


# =============================================================================
# CHART BUILDERS
# =============================================================================

def build_timeseries_chart(
    metric: str,
    timeseries: List[Dict],
    timeframe: Optional[str] = None,
    previous_timeseries: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Build a timeseries line/area chart.

    WHAT: Creates a line chart showing metric trend over time.

    WHY: Visualizes daily/weekly trends for questions like "Show ROAS trend".

    PARAMETERS:
        metric: Metric name
        timeseries: List of {date, value} points
        timeframe: Human-readable timeframe
        previous_timeseries: Optional previous period data for overlay

    RETURNS:
        Chart specification dict
    """
    series = [
        {
            "name": _metric_display_name(metric),
            "dataKey": "current",
            "data": [{"x": p.get("date"), "y": p.get("value")} for p in timeseries],
            "color": CHART_COLORS[0],
        }
    ]

    chart_type = "area"

    # Add previous period overlay if available
    if previous_timeseries:
        chart_type = "line"  # Switch to line for comparison
        series.append({
            "name": "Previous Period",
            "dataKey": "previous",
            "data": [{"x": p.get("date"), "y": p.get("value")} for p in previous_timeseries],
            "color": "#94a3b8",  # Gray for previous
        })

    return {
        "id": f"ts-{metric}",
        "type": chart_type,
        "title": f"{_metric_display_name(metric)} over time",
        "description": timeframe,
        "series": series,
        "xKey": "x",
        "yKey": "y",
        "valueFormat": metric,
    }


def build_entity_timeseries_chart(
    metric: str,
    entity_timeseries: List[EntityTimeseriesItem],
    level: Optional[str] = None,
    timeframe: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a multi-line chart (one line per entity).

    WHAT: Creates a chart with multiple lines, one for each entity.

    WHY: Enables "graph daily CPC for top 3 campaigns" visualizations.

    PARAMETERS:
        metric: Metric name
        entity_timeseries: List of EntityTimeseriesItem
        level: Entity level (campaign/adset/ad)
        timeframe: Human-readable timeframe

    RETURNS:
        Multi-line chart specification
    """
    series = []

    for i, item in enumerate(entity_timeseries):
        series.append({
            "name": item.entity_name,
            "dataKey": f"entity_{i}",
            "data": [{"x": p.get("date"), "y": p.get("value")} for p in item.timeseries],
            "color": CHART_COLORS[i % len(CHART_COLORS)],
        })

    level_name = level.title() if level else "Entity"

    return {
        "id": f"entity-ts-{metric}",
        "type": "line",
        "title": f"{level_name} {_metric_display_name(metric)} over time",
        "description": timeframe,
        "series": series,
        "xKey": "x",
        "yKey": "y",
        "valueFormat": metric,
        "isMultiEntity": True,
    }


def build_breakdown_bar_chart(
    metric: str,
    breakdown: List[Dict],
    level: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a bar chart for breakdown data.

    WHAT: Creates a horizontal bar chart showing top N entities.

    WHY: Visualizes rankings like "Top 5 campaigns by ROAS".

    PARAMETERS:
        metric: Metric name
        breakdown: List of breakdown items with label and value
        level: Entity level (campaign/adset/ad)

    RETURNS:
        Bar chart specification
    """
    level_name = level.title() if level else "Entity"

    return {
        "id": f"bd-{metric}",
        "type": "bar",
        "title": f"{level_name}s by {_metric_display_name(metric)}",
        "series": [
            {
                "name": _metric_display_name(metric),
                "data": [{"x": item.label, "y": item.value} for item in breakdown],
            }
        ],
        "xKey": "x",
        "yKey": "y",
        "valueFormat": metric,
    }


def build_entity_comparison_chart(
    metric: str,
    entity_comparison: List[EntityComparisonItem],
    level: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a grouped bar chart for entity comparison (THE KEY FEATURE).

    WHAT: Creates a chart showing current vs previous for each entity.

    WHY: Visualizes "Compare CPC for top 3 ads this week vs last week".

    PARAMETERS:
        metric: Metric name
        entity_comparison: List of EntityComparisonItem
        level: Entity level

    RETURNS:
        Grouped bar chart specification
    """
    level_name = level.title() if level else "Entity"

    # Build data for grouped bars
    data = []
    for item in entity_comparison:
        data.append({
            "x": item.entity_name,
            "current": item.current_value,
            "previous": item.previous_value,
        })

    return {
        "id": f"entity-comparison-{metric}",
        "type": "grouped_bar",
        "title": f"{level_name} {_metric_display_name(metric)} Comparison",
        "series": [
            {"name": "Current", "dataKey": "current", "color": CHART_COLORS[0]},
            {"name": "Previous", "dataKey": "previous", "color": "#94a3b8"},
        ],
        "data": data,
        "xKey": "x",
        "valueFormat": metric,
        "isComparison": True,
    }


# =============================================================================
# TABLE BUILDERS
# =============================================================================

def build_breakdown_table(
    metric: str,
    breakdown: List[Dict],
    level: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a data table for breakdown.

    WHAT: Creates a table with entity metrics.

    WHY: Detailed view for "Show all campaigns in a table".

    PARAMETERS:
        metric: Primary metric name
        breakdown: List of breakdown items
        level: Entity level

    RETURNS:
        Table specification with columns and rows
    """
    level_name = level.title() if level else "Entity"

    # Build columns
    columns = [
        {"key": "label", "label": level_name},
        {"key": "value", "label": _metric_display_name(metric), "format": metric},
    ]

    # Add denominator columns if present
    for col_key, col_label in [
        ("spend", "Spend"),
        ("revenue", "Revenue"),
        ("clicks", "Clicks"),
        ("impressions", "Impressions"),
        ("conversions", "Conversions"),
    ]:
        if any(getattr(item, col_key, None) is not None for item in breakdown):
            columns.append({"key": col_key, "label": col_label})

    # Build rows
    rows = []
    for item in breakdown:
        row = {
            "label": item.label,
            "value": item.value,
            "spend": item.spend,
            "revenue": item.revenue,
            "clicks": item.clicks,
            "impressions": item.impressions,
            "conversions": item.conversions,
        }
        rows.append(row)

    return {
        "id": f"table-{metric}",
        "title": f"{level_name}s by {_metric_display_name(metric)}",
        "columns": columns,
        "rows": rows,
    }


def build_entity_comparison_table(
    metric: str,
    entity_comparison: List[EntityComparisonItem],
    level: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a table for entity comparison (THE KEY FEATURE).

    WHAT: Creates a table showing current, previous, and delta for each entity.

    WHY: Detailed comparison view.

    PARAMETERS:
        metric: Metric name
        entity_comparison: List of EntityComparisonItem
        level: Entity level

    RETURNS:
        Comparison table specification
    """
    level_name = level.title() if level else "Entity"

    columns = [
        {"key": "entity_name", "label": level_name},
        {"key": "current_value", "label": "Current", "format": metric},
        {"key": "previous_value", "label": "Previous", "format": metric},
        {"key": "delta_pct", "label": "Change", "format": "percent"},
    ]

    rows = []
    for item in entity_comparison:
        rows.append({
            "entity_name": item.entity_name,
            "current_value": item.current_value,
            "previous_value": item.previous_value,
            "delta_pct": item.delta_pct,
        })

    return {
        "id": f"table-entity-comparison-{metric}",
        "title": f"{level_name} {_metric_display_name(metric)} Comparison",
        "columns": columns,
        "rows": rows,
    }


# =============================================================================
# MAIN BUILDER
# =============================================================================

def build_semantic_visual_payload(
    query: SemanticQuery,
    result: CompilationResult,
    timeframe: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Build visual payload from SemanticQuery and CompilationResult.

    WHAT: Main entry point for building visuals from semantic layer data.

    WHY: Provides consistent visual output for semantic queries.

    PARAMETERS:
        query: SemanticQuery that was executed
        result: CompilationResult with data
        timeframe: Human-readable timeframe (optional)

    RETURNS:
        Visual payload dict or None if no visuals needed

    STRATEGY:
        1. Check output format preference
        2. Build cards (summary or entity comparison)
        3. Build charts (timeseries, bar, grouped bar)
        4. Build tables (breakdown details)
        5. Filter by output format

    EXAMPLE:
        payload = build_semantic_visual_payload(query, result)
        # payload = {"cards": [...], "viz_specs": [...], "tables": [...]}
    """
    # Check output format - text means no visuals
    if query.output_format == OutputFormat.TEXT:
        return None

    payload = {
        "cards": [],
        "viz_specs": [],
        "tables": [],
    }

    primary_metric = query.get_primary_metric()
    level = query.breakdown.level if query.breakdown else None

    # Resolve timeframe from result if not provided
    if not timeframe and result.time_range_resolved:
        timeframe = f"{result.time_range_resolved['start']} to {result.time_range_resolved['end']}"

    # ==========================================================================
    # BUILD CARDS
    # ==========================================================================

    if result.has_entity_comparison():
        # THE KEY FEATURE: Entity comparison cards
        payload["cards"] = build_entity_comparison_cards(
            metric=primary_metric,
            entity_comparison=result.entity_comparison,
            timeframe=timeframe,
        )
    elif result.summary:
        # Simple summary card
        metric_value = result.summary.get(primary_metric)
        if metric_value:
            payload["cards"].append(build_summary_card(
                metric=primary_metric,
                value=metric_value.value,
                previous=metric_value.previous,
                delta_pct=metric_value.delta_pct,
                timeframe=timeframe,
                workspace_avg=result.workspace_avg,
            ))

    # ==========================================================================
    # BUILD CHARTS
    # ==========================================================================

    # Entity comparison chart (THE KEY FEATURE)
    if result.has_entity_comparison():
        payload["viz_specs"].append(build_entity_comparison_chart(
            metric=primary_metric,
            entity_comparison=result.entity_comparison,
            level=level,
        ))

    # Entity timeseries (multi-line chart)
    elif result.has_entity_timeseries():
        payload["viz_specs"].append(build_entity_timeseries_chart(
            metric=primary_metric,
            entity_timeseries=result.entity_timeseries,
            level=level,
            timeframe=timeframe,
        ))

    # Simple timeseries
    elif result.has_timeseries():
        for metric, points in result.timeseries.items():
            payload["viz_specs"].append(build_timeseries_chart(
                metric=metric,
                timeseries=[{"date": p.date, "value": p.value} for p in points],
                timeframe=timeframe,
            ))

    # Breakdown bar chart
    if result.has_breakdown() and not result.has_entity_comparison() and not result.has_entity_timeseries():
        payload["viz_specs"].append(build_breakdown_bar_chart(
            metric=primary_metric,
            breakdown=result.breakdown,
            level=level,
        ))

    # ==========================================================================
    # BUILD TABLES
    # ==========================================================================

    # Entity comparison table
    if result.has_entity_comparison():
        payload["tables"].append(build_entity_comparison_table(
            metric=primary_metric,
            entity_comparison=result.entity_comparison,
            level=level,
        ))

    # Breakdown table
    elif result.has_breakdown():
        payload["tables"].append(build_breakdown_table(
            metric=primary_metric,
            breakdown=result.breakdown,
            level=level,
        ))

    # ==========================================================================
    # APPLY OUTPUT FORMAT FILTER
    # ==========================================================================

    if query.output_format == OutputFormat.CHART:
        # Only charts
        payload["cards"] = []
        payload["tables"] = []

    elif query.output_format == OutputFormat.TABLE:
        # Only tables
        payload["cards"] = []
        payload["viz_specs"] = []

    # Return None if nothing to show
    if not any(payload.values()):
        return None

    return payload
