"""
Rich visual payload builder for QA responses.

WHAT:
- Translates executed DSL + results into ready-to-render cards, chart specs, and tables.
- Specs are intentionally lightweight so the frontend can plug them into Recharts or Vega-Lite without custom engines.
- NEW v2.1: Uses Visual Intent Classifier to select appropriate visuals.

WHY:
- Gives Copilot answers an immediate visual impact (sparklines, comparisons, breakdown tables).
- Keeps formatting centralized on the backend to avoid drift between text answers and visuals.
- NEW v2.1: Prevents visual noise by only showing relevant visualizations.

DATA FLOW (v2.1):
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT                                   │
│  DSL (MetricQuery) + Result Data + Window                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               STEP 1: CLASSIFY INTENT                           │
│  visual_intent.classify_visual_intent(dsl, result_data)        │
│  → VisualIntent.COMPARISON / FILTERING / RANKING / etc.        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               STEP 2: BUILD RAW VISUALS                         │
│  - Cards (summary metrics)                                      │
│  - Charts (timeseries, breakdown bars, comparison lines)        │
│  - Tables (breakdown details)                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               STEP 3: APPLY STRATEGY FILTER                     │
│  visual_intent.filter_visuals_by_strategy(payload, strategy)   │
│  → Remove irrelevant visuals based on intent                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         OUTPUT                                  │
│  { cards: [...], viz_specs: [...], tables: [...] }             │
│  (Filtered to only relevant visualizations)                    │
└─────────────────────────────────────────────────────────────────┘

REFERENCES:
- app/services/qa_service.py: calls build_visual_payload during QA responses.
- app/dsl/schema.py: source data shapes (MetricResult, comparison results, multi-metric results).
- app/answer/visual_intent.py: NEW - Intent classification and filtering.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.answer.formatters import format_metric_value, format_delta_pct
from app.answer.visual_intent import (
    classify_visual_intent,
    get_visual_strategy,
    filter_visuals_by_strategy,
    VisualIntent,
)

logger = logging.getLogger(__name__)


def _metric_key_list(dsl: Any) -> List[str]:
    """Normalize metric field to a list for consistent processing."""
    metric = getattr(dsl, "metric", None)
    if isinstance(metric, list):
        return metric
    if metric:
        return [metric]
    return []


def _metric_display_name(metric: str) -> str:
    """Human-friendly metric label for cards and charts."""
    names = {
        "roas": "ROAS",
        "cpa": "CPA",
        "cpc": "CPC",
        "cpm": "CPM",
        "cpl": "CPL",
        "cpi": "CPI",
        "cpp": "CPP",
        "poas": "POAS",
        "aov": "AOV",
        "arpv": "ARPV",
        "ctr": "CTR",
        "cvr": "CVR",
        "spend": "Spend",
        "revenue": "Revenue",
        "clicks": "Clicks",
        "impressions": "Impressions",
        "conversions": "Conversions",
    }
    return names.get(metric.lower(), metric.title() if metric else "Metric")


def _parse_date(value: Any) -> Optional[date]:
    """Best-effort ISO/date parsing for timeframe labels."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def _format_date_window(window: Optional[Dict[str, Any]]) -> Optional[str]:
    """Format a start/end window into a short human label."""
    if not window:
        return None
    start = _parse_date(window.get("start"))
    end = _parse_date(window.get("end"))
    if not start or not end:
        return None
    same_year = start.year == end.year
    if same_year:
        return f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
    return f"{start.strftime('%b %d, %Y')} – {end.strftime('%b %d, %Y')}"


def _build_summary_card(metric: str, result_data: Dict[str, Any], timeframe: Optional[str], sparkline: List[Dict[str, Any]], top_contributor: Optional[str]) -> Dict[str, Any]:
    """Create a single summary card payload."""
    summary = result_data.get("summary")
    delta = result_data.get("delta_pct")
    previous = result_data.get("previous")
    workspace_avg = result_data.get("workspace_avg")
    prev_period_label = result_data.get("previous_period_label")

    return {
        "id": f"card-{metric}",
        "title": _metric_display_name(metric),
        "metric": metric,
        "value": summary,
        "formatted_value": format_metric_value(metric, summary) if summary is not None else None,
        "delta": delta,
        "formatted_delta": format_delta_pct(delta) if delta is not None else None,
        "previous": previous,
        "previous_label": prev_period_label,
        "timeframe": timeframe,
        "sparkline": sparkline,
        "top_contributor": top_contributor,
        "workspace_avg": workspace_avg,
    }


def _build_timeseries_spec(
    metric: str,
    timeseries: List[Dict[str, Any]],
    timeframe: Optional[str],
    previous_timeseries: Optional[List[Dict[str, Any]]] = None,
    is_comparison: bool = False
) -> Dict[str, Any]:
    """
    Create a line/area spec for timeseries, with optional previous-period overlay.

    WHAT: Builds chart specification for timeseries visualization

    WHY:
    - Single series: Area chart shows trend
    - Dual series (comparison): Line chart shows both periods clearly

    COMPARISON FIX (v2.1):
    - When previous_timeseries has actual daily data (not flat), show dual-line chart
    - When previous_timeseries is flat (fallback), show area with reference line
    - is_comparison flag ensures we use line type for "vs" queries

    OVERLAY FIX (v2.1.1):
    - For comparison charts, use RELATIVE day indices (Day 1, Day 2, ...) instead of actual dates
    - This allows both periods to be plotted on the same x-axis for visual comparison
    - Without this, current (Nov 19-23) and previous (Nov 12-18) would appear as separate segments

    Args:
        metric: Metric key for labeling
        timeseries: Current period daily data [{date, value}, ...]
        timeframe: Human-readable timeframe for description
        previous_timeseries: Previous period daily data (optional)
        is_comparison: Force comparison chart style (from intent classifier)

    Returns:
        Chart specification for frontend rendering
    """
    logger.debug(f"[VISUAL_BUILDER] Building timeseries for {metric}, "
                 f"current={len(timeseries)} points, "
                 f"previous={len(previous_timeseries) if previous_timeseries else 0} points")

    # Check if we have real previous data (varying values, not flat fallback)
    has_real_previous_data = False
    if previous_timeseries and len(previous_timeseries) > 0:
        prev_values = [p.get("value") for p in previous_timeseries]
        unique_values = set(v for v in prev_values if v is not None)
        has_real_previous_data = len(unique_values) > 1
        if has_real_previous_data:
            logger.info(f"[VISUAL_BUILDER] Previous timeseries has {len(unique_values)} unique values - real comparison data")

    # OVERLAY COMPARISON: Use relative day indices so both periods align on same x-axis
    # This is the key fix - instead of different actual dates, we use Day 1, Day 2, etc.
    should_overlay = (is_comparison or has_real_previous_data) and previous_timeseries and len(previous_timeseries) > 0

    logger.debug(f"[VISUAL_BUILDER] Timeseries chart decision: "
                 f"is_comparison={is_comparison}, "
                 f"has_real_previous_data={has_real_previous_data}, "
                 f"should_overlay={should_overlay}")

    if should_overlay:
        logger.info(f"[VISUAL_BUILDER] Building OVERLAY comparison chart for {metric}")

        # Get the maximum length (handle different period lengths)
        max_len = max(len(timeseries), len(previous_timeseries))

        # Generate relative day labels (Day 1, Day 2, ...)
        day_labels = [f"Day {i+1}" for i in range(max_len)]

        # Build current period data aligned to relative days
        current_data = []
        for i, label in enumerate(day_labels):
            if i < len(timeseries):
                current_data.append({"x": label, "y": timeseries[i].get("value")})
            else:
                current_data.append({"x": label, "y": None})

        # Determine friendly name for current period
        current_name = "This week" if "week" in (timeframe or "").lower() else "Current"

        current_series = {
            "name": current_name,
            "dataKey": "current",
            "data": current_data,
            "color": "#2563eb",  # Blue for current
        }

        # Build previous period data aligned to relative days
        previous_data = []
        for i, label in enumerate(day_labels):
            if i < len(previous_timeseries):
                previous_data.append({"x": label, "y": previous_timeseries[i].get("value")})
            else:
                previous_data.append({"x": label, "y": None})

        # Determine friendly name for previous period
        previous_name = "Last week" if "week" in (timeframe or "").lower() else "Previous"

        previous_series = {
            "name": previous_name,
            "dataKey": "previous",
            "data": previous_data,
            "color": "#94a3b8",  # Slate for previous
        }

        return {
            "id": f"ts-{metric}",
            "type": "line",
            "title": f"{_metric_display_name(metric)} comparison",
            "description": f"{timeframe} vs previous",
            "series": [current_series, previous_series],
            "xKey": "x",
            "yKey": "y",
            "valueFormat": metric,
            "isComparison": True,
        }

    # SINGLE SERIES: Standard area chart for non-comparison queries
    current_series = {
        "name": _metric_display_name(metric),
        "dataKey": "current",
        "data": [{"x": p.get("date"), "y": p.get("value")} for p in timeseries]
    }

    return {
        "id": f"ts-{metric}",
        "type": "area",
        "title": f"{_metric_display_name(metric)} over time",
        "description": timeframe,
        "series": [current_series],
        "xKey": "x",
        "yKey": "y",
        "valueFormat": metric,
        "isComparison": False,
    }


def _build_entity_timeseries_spec(
    metric: str,
    entity_timeseries: List[Dict[str, Any]],
    breakdown_type: str = None,
    timeframe: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a multi-line chart spec for entity timeseries (one line per entity).

    WHY: When user asks "graph of top 5 ads", we show 5 lines - one per ad,
    showing how each performed over time.

    Args:
        metric: Metric key for labeling and formatting
        entity_timeseries: List of entity data from executor, each with:
            {
                "entity_id": "uuid-1",
                "entity_name": "Summer Sale",
                "timeseries": [{"date": "2025-11-20", "value": 123.45}, ...]
            }
        breakdown_type: Type of entity (campaign/adset/ad) for better title
        timeframe: Human-readable timeframe for description

    Returns:
        Multi-line chart specification for frontend rendering
    """
    if not entity_timeseries:
        return None

    logger.info(f"[VISUAL_BUILDER] Building multi-line entity chart for {len(entity_timeseries)} entities")

    # Build one series per entity
    series = []
    colors = ["#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16"]

    for idx, entity_data in enumerate(entity_timeseries):
        entity_name = entity_data.get("entity_name", f"Entity {idx+1}")
        ts_data = entity_data.get("timeseries", [])

        series.append({
            "name": entity_name,
            "dataKey": f"entity_{idx}",
            "data": [{"x": pt.get("date"), "y": pt.get("value")} for pt in ts_data],
            "color": colors[idx % len(colors)]  # Cycle through colors
        })

    entity_label = breakdown_type.title() if breakdown_type else "Entity"

    return {
        "id": f"entity-ts-{metric}",
        "type": "line",
        "title": f"{entity_label} {_metric_display_name(metric)} over time",
        "description": timeframe,
        "series": series,
        "xKey": "x",
        "yKey": "y",
        "valueFormat": metric,
        "isMultiEntity": True,  # Flag for frontend to render legend properly
    }


def _build_breakdown_spec(metric: str, breakdown: List[Dict[str, Any]], label_key: str = "label", breakdown_type: str = None) -> Dict[str, Any]:
    """Create a bar chart spec for breakdowns (campaign/ad/provider).

    Args:
        metric: Metric key for labeling
        breakdown: List of breakdown data [{label, value, ...}, ...]
        label_key: Key to use for x-axis labels (default: "label")
        breakdown_type: Type of breakdown (campaign/adset/ad/provider) for better titles
    """
    series_data = [{"x": item.get(label_key), "y": item.get("value")} for item in breakdown]

    # Use breakdown_type for better chart title if provided
    entity_name = breakdown_type.title() if breakdown_type else label_key.title()

    return {
        "id": f"bd-{metric}",
        "type": "bar",
        "title": f"{entity_name}s by {_metric_display_name(metric)}",
        "series": [{"name": _metric_display_name(metric), "data": series_data}],
        "xKey": "x",
        "yKey": "y",
        "valueFormat": metric,
    }


def _build_breakdown_table(metric: str, breakdown: List[Dict[str, Any]], label_key: str = "label", breakdown_type: str = None) -> Dict[str, Any]:
    """Create a table definition for breakdown rows.

    Args:
        metric: Metric key for labeling
        breakdown: List of breakdown data [{label, value, ...}, ...]
        label_key: Key to use for x-axis labels (default: "label")
        breakdown_type: Type of breakdown (campaign/adset/ad/provider) for better titles
    """
    # Use breakdown_type for better column and title names
    entity_label = breakdown_type.title() if breakdown_type else label_key.title()

    columns = [
        {"key": label_key, "label": entity_label},
        {"key": "value", "label": _metric_display_name(metric), "format": metric},
    ]

    # Add common denominators if present
    for denom_key, label in [("spend", "Spend"), ("clicks", "Clicks"), ("conversions", "Conversions"), ("revenue", "Revenue"), ("impressions", "Impressions")]:
        if any(row.get(denom_key) is not None for row in breakdown):
            columns.append({"key": denom_key, "label": label})

    rows = []
    for row in breakdown:
        rows.append({
            label_key: row.get(label_key),
            "value": row.get("value"),
            "spend": row.get("spend"),
            "clicks": row.get("clicks"),
            "conversions": row.get("conversions"),
            "revenue": row.get("revenue"),
            "impressions": row.get("impressions"),
        })

    # Better table title
    entity_name_plural = f"{entity_label}s" if entity_label else "Entities"
    table_title = f"{entity_name_plural} by {_metric_display_name(metric)}"

    return {
        "id": f"table-{metric}",
        "title": table_title,
        "columns": columns,
        "rows": rows,
    }


def _build_comparison_specs(result_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Handle comparison query results by emitting both a grouped bar spec and a table.

    Expected shape:
    {
        "comparison": [{"entity": "A", "roas": 3.2, "revenue": 1000}, ...],
        "comparison_type": "...",
        "metrics": ["roas", "revenue"]
    }
    """
    comparison = result_data.get("comparison") or []
    metrics = result_data.get("metrics") or []
    payload = {"viz_specs": [], "tables": []}

    if not comparison or not metrics:
        return payload

    # Build grouped bar data keyed by the first identifier in each row.
    first_key = None
    for candidate_key in ["entity", "provider", "period"]:
        if candidate_key in comparison[0]:
            first_key = candidate_key
            break
    if not first_key:
        first_key = "item"

    chart_data = []
    for row in comparison:
        entry = {
            "x": row.get(first_key),  # For charts (uses "x" as xKey)
            first_key: row.get(first_key),  # For tables (uses actual key like "entity")
        }
        for metric in metrics:
            entry[metric] = row.get(metric)
        chart_data.append(entry)

    # If time-like comparison, also emit a multi-line chart
    if first_key in ["period", "date", "day", "week", "month"]:
        line_series = []
        for metric in metrics:
            line_series.append({
                "name": _metric_display_name(metric),
                "dataKey": metric,
                "data": [{"x": row.get(first_key), "y": row.get(metric)} for row in comparison],
            })
        payload["viz_specs"].append({
            "id": "comparison-lines",
            "type": "line",
            "title": "Comparison over time",
            "series": line_series,
            "xKey": "x",
            "yKey": "y",
            "valueFormat": "mixed",
        })
    
    # NEW: Check for timeseries data in comparison results (for entity comparison over time)
    has_timeseries = any("timeseries" in row for row in comparison)
    
    if has_timeseries:
        # Build multi-line chart: One line per entity
        line_series = []
        # Use first metric for the chart (multi-metric comparison charts are complex)
        metric = metrics[0] if metrics else "value"
        
        for row in comparison:
            entity_name = row.get(first_key) or "Unknown"
            ts_data = row.get("timeseries", [])
            
            line_series.append({
                "name": entity_name,
                "dataKey": entity_name, # Unique key for Recharts
                "data": [{"x": p["date"], "y": p["value"]} for p in ts_data],
                "color": None # Let frontend assign colors
            })
            
        payload["viz_specs"].append({
            "id": "comparison-lines-entity",
            "type": "line",
            "title": f"Comparison of {_metric_display_name(metric)} over time",
            "series": line_series,
            "xKey": "x",
            "yKey": "y",
            "valueFormat": metric,
        })

    payload["viz_specs"].append({
        "id": "comparison",
        "type": "grouped_bar",
        "title": "Comparison",
        "series": [{"name": _metric_display_name(m), "dataKey": m} for m in metrics],
        "data": chart_data,
        "xKey": "x",
        "valueFormat": "mixed",
    })

    columns = [{"key": first_key, "label": first_key.title()}] + [
        {"key": m, "label": _metric_display_name(m), "format": m} for m in metrics
    ]
    payload["tables"].append({
        "id": "comparison-table",
        "title": "Comparison details",
        "columns": columns,
        "rows": chart_data,
    })

    return payload


def _build_multi_metric_cards(result_data: Dict[str, Any], timeframe: Optional[str]) -> List[Dict[str, Any]]:
    """Generate a card per metric for multi-metric responses."""
    cards = []
    metrics_block = result_data.get("metrics") or {}
    for metric_name, metric_values in metrics_block.items():
        sparkline = result_data.get("timeseries") or []
        cards.append(
            _build_summary_card(
                metric=metric_name,
                result_data=metric_values,
                timeframe=timeframe,
                sparkline=sparkline,
                top_contributor=None,
            )
        )
    return cards


def _apply_output_format_override(
    payload: Dict[str, List[Dict[str, Any]]],
    output_format: str,
    breakdown: Optional[List[Dict[str, Any]]] = None,
    metric: Optional[str] = None,
    breakdown_type: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Apply user's explicit output_format preference to the visual payload.

    WHY: Users may explicitly request "chart", "table", or "text" format.
    This override ensures we respect their preference over the auto-selected visuals.

    Args:
        payload: The visual payload with cards, viz_specs, tables
        output_format: User's preference ("auto", "table", "chart", "text")
        breakdown: Optional breakdown data (for building table if needed)
        metric: Metric name (for building table if needed)
        breakdown_type: Type of breakdown (campaign/adset/ad)

    Returns:
        Modified payload respecting output_format preference
    """
    if output_format == "auto":
        # No override needed
        return payload

    if output_format == "text":
        # Shouldn't reach here (handled earlier), but just in case
        return {"cards": [], "viz_specs": [], "tables": []}

    if output_format == "table":
        # User explicitly wants table - remove charts, keep tables
        logger.info("[VISUAL_BUILDER] output_format='table' - keeping only tables")
        # If no table exists but we have breakdown data, build one
        if not payload["tables"] and breakdown and metric:
            payload["tables"].append(_build_breakdown_table(metric, breakdown, breakdown_type=breakdown_type))
        payload["viz_specs"] = []  # Remove all charts
        payload["cards"] = []  # Remove cards too - table is the focus

    elif output_format == "chart":
        # User explicitly wants chart - remove tables, keep charts
        logger.info("[VISUAL_BUILDER] output_format='chart' - keeping only charts")
        payload["tables"] = []  # Remove tables
        payload["cards"] = []   # Remove cards

    return payload


def build_visual_payload(dsl: Any, result_data: Dict[str, Any], window: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    """
    Build a structured visual payload (cards, charts, tables) from DSL + results.

    UPDATED v2.1: Now uses Visual Intent Classifier for smarter visual selection.
    UPDATED v2.2: Respects user's output_format preference (table/chart/text).

    DATA FLOW:
    1. Check output_format preference (NEW)
    2. Classify query intent (COMPARISON, FILTERING, RANKING, etc.)
    3. Build raw visuals (all possible visualizations)
    4. Apply strategy filter (remove irrelevant visuals based on intent)
    5. Apply output_format override if specified (NEW)

    Args:
        dsl: MetricQuery DSL object with query parameters
        result_data: Execution result dictionary with metrics, timeseries, breakdown
        window: Optional date window for timeframe labeling

    Returns:
        Dict with {cards: [...], viz_specs: [...], tables: [...]}
        Returns None when there is nothing to visualize.

    Examples:
        >>> # Filtering query: only returns table
        >>> dsl.filters.metric_filters = [{"metric": "revenue", "operator": "=", "value": 0}]
        >>> payload = build_visual_payload(dsl, result_data, window)
        >>> len(payload['viz_specs'])  # No charts
        0
        >>> len(payload['tables'])  # Just the table
        1

        >>> # User explicitly wants table format
        >>> dsl.output_format = "table"
        >>> payload = build_visual_payload(dsl, result_data, window)
        >>> len(payload['tables'])  # Table is present
        1
        >>> len(payload['viz_specs'])  # No charts (user wanted table)
        0
    """
    query_type = getattr(dsl, "query_type", "metrics")
    timeframe = getattr(dsl, "timeframe_description", None) or _format_date_window(window)
    output_format = getattr(dsl, "output_format", "auto")

    # ==================================================================
    # OUTPUT FORMAT OVERRIDE (NEW v2.2)
    # If user explicitly requested a format, respect it
    # ==================================================================
    if output_format == "text":
        # User wants text-only response, no visuals
        logger.info("[VISUAL_BUILDER] output_format='text' - returning no visuals")
        return None

    # SPECIAL CASE: Comparison query with table format requested
    # When user asks "compare all campaigns in a table", we get:
    # - query_type = "comparison"
    # - result_data has "comparison" key (not "breakdown")
    # - output_format = "table"
    # We need to build a table from the comparison data directly
    if output_format == "table" and result_data.get("comparison"):
        logger.info("[VISUAL_BUILDER] Comparison query with table format - building comparison table")
        comparison_payload = _build_comparison_specs(result_data)
        # Return only the tables (not the charts)
        return {"cards": [], "viz_specs": [], "tables": comparison_payload["tables"]}

    # Non-metric listings (providers/entities) do not need visuals.
    if query_type in ("providers", "entities"):
        return None

    # ==================================================================
    # STEP 1: CLASSIFY VISUAL INTENT
    # WHY: Different queries need different visualizations
    # ==================================================================
    intent = classify_visual_intent(dsl, result_data)
    strategy = get_visual_strategy(intent)
    logger.info(f"[VISUAL_BUILDER] Intent={intent.value}, Strategy: {strategy.rationale}")

    # Check if this is a comparison query (for timeseries rendering)
    is_comparison = intent == VisualIntent.COMPARISON

    # ==================================================================
    # STEP 2: BUILD RAW VISUALS
    # Build all possible visualizations, then filter by strategy
    # ==================================================================
    payload: Dict[str, List[Dict[str, Any]]] = {"cards": [], "viz_specs": [], "tables": []}

    # Multi-metric: card per metric, optional timeseries and breakdown handled from primary metric.
    if query_type == "multi_metrics" or result_data.get("query_type") == "multi_metrics":
        payload["cards"].extend(_build_multi_metric_cards(result_data, timeframe))

        # ==================================================================
        # ENTITY TIMESERIES (NEW - for multi-line charts)
        # When output_format='chart' and executor fetched per-entity timeseries,
        # build a multi-line chart showing each entity's trend over time.
        # This is for queries like "graph of top 5 ads"
        # ==================================================================
        entity_timeseries = result_data.get("entity_timeseries")
        primary_metric = next(iter(result_data.get("metrics", {}).keys()), None)
        breakdown_type = getattr(dsl, 'breakdown', None)

        if entity_timeseries and output_format == "chart":
            # Build multi-line chart showing each entity's timeseries
            logger.info(f"[VISUAL_BUILDER] Building multi-line entity chart (output_format=chart, {len(entity_timeseries)} entities)")
            entity_chart = _build_entity_timeseries_spec(
                primary_metric or "spend",
                entity_timeseries,
                breakdown_type=breakdown_type,
                timeframe=timeframe
            )
            if entity_chart:
                payload["viz_specs"].append(entity_chart)
        else:
            # Standard behavior: aggregate timeseries + breakdown bar chart
            if result_data.get("timeseries"):
                first_metric = next(iter(result_data.get("metrics", {}).keys()), None)
                if first_metric:
                    payload["viz_specs"].append(_build_timeseries_spec(
                        first_metric,
                        result_data["timeseries"],
                        timeframe,
                        is_comparison=is_comparison
                    ))

            if result_data.get("breakdown"):
                if primary_metric:
                    payload["viz_specs"].append(_build_breakdown_spec(primary_metric, result_data["breakdown"], breakdown_type=breakdown_type))
                    payload["tables"].append(_build_breakdown_table(primary_metric, result_data["breakdown"], breakdown_type=breakdown_type))

        # Apply strategy filter
        payload = filter_visuals_by_strategy(payload, strategy)

        # Apply output_format override (CRITICAL: must happen AFTER strategy filter)
        payload = _apply_output_format_override(payload, output_format, result_data.get("breakdown"), primary_metric, breakdown_type)

        return payload if any(payload.values()) else None

    # Comparison queries.
    # IMPORTANT: Only go to comparison flow if intent is COMPARISON
    # "Compare all campaigns" should use RANKING intent, not comparison flow
    if (query_type == "comparison" or result_data.get("comparison")) and intent == VisualIntent.COMPARISON:
        comparison_payload = _build_comparison_specs(result_data)
        payload["viz_specs"].extend(comparison_payload["viz_specs"])
        payload["tables"].extend(comparison_payload["tables"])

        # Apply strategy filter
        payload = filter_visuals_by_strategy(payload, strategy)

        # Apply output_format override
        payload = _apply_output_format_override(payload, output_format)

        return payload if any(payload.values()) else None

    # ==================================================================
    # METRICS QUERIES (default)
    # ==================================================================
    metrics = _metric_key_list(dsl)
    metric = metrics[0] if metrics else "metric"

    timeseries = result_data.get("timeseries") or []
    previous_timeseries = result_data.get("previous_timeseries") or result_data.get("timeseries_previous")

    # Log what timeseries data we have for debugging
    logger.debug(f"[VISUAL_BUILDER] Timeseries data: "
                 f"current={len(timeseries)} points, "
                 f"previous={'None' if previous_timeseries is None else len(previous_timeseries)} points, "
                 f"is_comparison={is_comparison}, "
                 f"compare_to_previous={getattr(dsl, 'compare_to_previous', 'N/A')}")

    # Fallback: if no explicit previous timeseries but we have a previous summary,
    # build a flat reference line at the previous value so charts can show
    # "current vs last period" even without per-day history.
    # NOTE: This is a fallback - real comparison data should come from executor
    if not previous_timeseries and timeseries and result_data.get("previous") is not None:
        prev_value = result_data.get("previous")
        logger.info(f"[VISUAL_BUILDER] Creating flat fallback previous_timeseries "
                    f"(prev_value={prev_value}). For real comparison, ensure "
                    f"compare_to_previous=True in DSL.")
        previous_timeseries = [
            {"date": point.get("date"), "value": prev_value}
            for point in timeseries
        ]

    breakdown = result_data.get("breakdown") or []

    # Debug: Log breakdown data
    if breakdown:
        logger.debug(f"[VISUAL_BUILDER] Breakdown data (first 2): {breakdown[:2]}")

    top_contributor = breakdown[0]["label"] if breakdown else None

    # Build summary card
    payload["cards"].append(
        _build_summary_card(
            metric=metric,
            result_data=result_data,
            timeframe=timeframe,
            sparkline=timeseries,
            top_contributor=top_contributor,
        )
    )

    # ==================================================================
    # ENTITY TIMESERIES (for multi-line charts)
    # When output_format='chart' and we have entity_timeseries, build multi-line chart
    # This is for queries like "graph of top 5 ads"
    # ==================================================================
    entity_timeseries = result_data.get("entity_timeseries")
    breakdown_type = getattr(dsl, 'breakdown', None)

    if entity_timeseries and output_format == "chart":
        # Build multi-line chart showing each entity's timeseries
        logger.info(f"[VISUAL_BUILDER] Building multi-line entity chart (output_format=chart, {len(entity_timeseries)} entities)")
        entity_chart = _build_entity_timeseries_spec(
            metric,
            entity_timeseries,
            breakdown_type=breakdown_type,
            timeframe=timeframe
        )
        if entity_chart:
            payload["viz_specs"].append(entity_chart)
        # Don't build breakdown bar chart or table - the multi-line chart is the visual
    else:
        # Standard behavior: aggregate timeseries + breakdown bar chart + table
        # Build timeseries chart
        if timeseries:
            payload["viz_specs"].append(_build_timeseries_spec(
                metric,
                timeseries,
                timeframe,
                previous_timeseries=previous_timeseries,
                is_comparison=is_comparison  # Pass comparison flag for proper chart type
            ))

        # Build breakdown chart and table
        if breakdown:
            payload["viz_specs"].append(_build_breakdown_spec(metric, breakdown, breakdown_type=breakdown_type))
            payload["tables"].append(_build_breakdown_table(metric, breakdown, breakdown_type=breakdown_type))

    # ==================================================================
    # STEP 3: APPLY STRATEGY FILTER
    # Remove irrelevant visuals based on classified intent
    # ==================================================================
    payload = filter_visuals_by_strategy(payload, strategy)

    # ==================================================================
    # STEP 4: APPLY OUTPUT FORMAT OVERRIDE (NEW v2.2)
    # If user explicitly requested table/chart, enforce it
    # ==================================================================
    payload = _apply_output_format_override(payload, output_format, breakdown, metric, breakdown_type)

    return payload if any(payload.values()) else None
