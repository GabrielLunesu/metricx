"""
Visual Intent Classifier
=========================

WHAT:
- Analyzes DSL query and result data to determine appropriate visualizations
- Prevents visual noise by selecting only relevant charts/tables
- Makes the system "smarter" about what to show

WHY:
- "campaigns with no revenue" shouldn't show revenue charts
- "vs last week" should prioritize comparison charts
- Single metric queries don't need 5 different visualizations

HOW:
- Classify query intent based on DSL structure
- Map intent to visualization strategy
- Filter/prioritize visuals accordingly

DATA FLOW:
┌─────────────────┐
│ DSL + Result    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Intent         │
│  Classifier     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ VisualIntent    │────►│ Visual Strategy │
│ (enum)          │     │ (what to show)  │
└─────────────────┘     └─────────────────┘

REFERENCES:
- app/answer/visual_builder.py: Consumes intent to build appropriate visuals
- app/dsl/schema.py: DSL structure we analyze
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class VisualIntent(str, Enum):
    """
    Classification of what kind of visualization the query needs.

    Each intent maps to a different visual strategy:
    - SINGLE_METRIC: Simple card + small sparkline (e.g., "What's my ROAS?")
    - COMPARISON: Dual-line chart showing current vs previous (e.g., "spend vs last week")
    - RANKING: Bar chart + table for top performers (e.g., "top 5 campaigns by ROAS")
    - ALL_ENTITIES: Table ONLY for "compare all X" queries (e.g., "compare all campaigns")
    - FILTERING: Table ONLY for filtered results (e.g., "campaigns with no revenue")
    - TREND: Area chart emphasizing trend direction (e.g., "how is spend trending?")
    - BREAKDOWN: Pie/bar chart for distribution (e.g., "spend by platform")
    - MULTI_METRIC: Multiple cards, shared timeseries (e.g., "show spend and revenue")
    """
    SINGLE_METRIC = "single_metric"
    COMPARISON = "comparison"
    RANKING = "ranking"
    ALL_ENTITIES = "all_entities"  # NEW: Table-only for "compare all X" queries
    FILTERING = "filtering"
    TREND = "trend"
    BREAKDOWN = "breakdown"
    MULTI_METRIC = "multi_metric"


@dataclass
class VisualStrategy:
    """
    Strategy for which visuals to include based on intent.

    Attributes:
        intent: The classified intent
        show_card: Whether to show metric summary card(s)
        show_timeseries: Whether to show line/area chart
        show_comparison_overlay: Whether to overlay previous period on chart
        show_breakdown_chart: Whether to show bar chart for breakdown
        show_table: Whether to show data table
        max_charts: Maximum number of chart visualizations to include
        rationale: Human-readable explanation of the strategy
    """
    intent: VisualIntent
    show_card: bool
    show_timeseries: bool
    show_comparison_overlay: bool
    show_breakdown_chart: bool
    show_table: bool
    max_charts: int
    rationale: str


def classify_visual_intent(dsl: Any, result_data: Dict[str, Any]) -> VisualIntent:
    """
    Analyze DSL and result to determine the appropriate visualization intent.

    WHAT: Classifies query into one of the VisualIntent categories

    WHY: Different queries need different visualizations:
    - "campaigns with no revenue" → just table, no charts
    - "vs last week" → comparison chart
    - "top campaigns" → ranking chart

    HOW:
    1. Check for filtering queries (metric value filters)
    2. Check for comparison queries (vs previous, vs other)
    3. Check for ranking queries (top_n with breakdown)
    4. Check for multi-metric queries
    5. Default to single metric with optional breakdown

    Args:
        dsl: MetricQuery DSL object
        result_data: Execution result dictionary

    Returns:
        VisualIntent classification

    Examples:
        >>> # Filtering query: "campaigns with no revenue"
        >>> dsl.filters.metric_filters = [{"metric": "revenue", "operator": "=", "value": 0}]
        >>> classify_visual_intent(dsl, result_data)
        VisualIntent.FILTERING

        >>> # Comparison query: "spend vs last week"
        >>> dsl.compare_to_previous = True
        >>> classify_visual_intent(dsl, result_data)
        VisualIntent.COMPARISON
    """
    logger.debug(f"[VISUAL_INTENT] Classifying intent for query_type={getattr(dsl, 'query_type', 'unknown')}")

    # 1. FILTERING: Queries with metric value filters (e.g., revenue = 0, ROAS < 1)
    # WHY: These queries are looking for specific entities, not trends
    # WHAT TO SHOW: Table only - the list of matching entities
    filters = getattr(dsl, 'filters', None)
    if filters and getattr(filters, 'metric_filters', None):
        metric_filters = filters.metric_filters
        for mf in metric_filters:
            operator = mf.get('operator', '')
            value = mf.get('value', 0)

            # Zero-value filters: "campaigns with no revenue", "zero spend"
            if operator in ('=', '<=') and value == 0:
                logger.info(f"[VISUAL_INTENT] Classified as FILTERING (zero-value filter)")
                return VisualIntent.FILTERING

            # Low threshold filters: "ROAS below 1", "CTR under 0.5%"
            if operator in ('<', '<=') and isinstance(value, (int, float)):
                logger.info(f"[VISUAL_INTENT] Classified as FILTERING (threshold filter)")
                return VisualIntent.FILTERING

    # EARLY ENTITY CHECK: "Compare ALL X" or "Show ALL X" with breakdown
    # WHY: Must check BEFORE generic comparison check, because "compare all campaigns"
    #      needs a TABLE, not a comparison chart or ranking bar chart
    breakdown = getattr(dsl, 'breakdown', None)
    question = getattr(dsl, 'question', '') or ''
    question_lower = question.lower()

    if breakdown and breakdown in ['campaign', 'adset', 'ad', 'provider']:
        # "all" keywords → TABLE ONLY (no charts, cleaner output)
        all_keywords = ['all', 'compare all', 'show all', 'list all', 'give me all']

        if any(kw in question_lower for kw in all_keywords):
            logger.info(f"[VISUAL_INTENT] Classified as ALL_ENTITIES (breakdown + 'all' keywords, breakdown={breakdown})")
            return VisualIntent.ALL_ENTITIES

        # Ranking keywords → bar chart + table
        ranking_keywords = ['top', 'best', 'worst', 'highest', 'lowest', 'most', 'least']
        if any(kw in question_lower for kw in ranking_keywords):
            logger.info(f"[VISUAL_INTENT] Classified as RANKING (breakdown + ranking keywords)")
            return VisualIntent.RANKING

        # "compare" without "all" → could be entity comparison, check for specific patterns
        compare_keywords = ['compare', 'show me', 'give me', 'list']
        if any(kw in question_lower for kw in compare_keywords):
            logger.info(f"[VISUAL_INTENT] Classified as RANKING (breakdown + compare keywords, breakdown={breakdown})")
            return VisualIntent.RANKING

    # 2. COMPARISON: Time-based comparison queries
    # WHY: "vs last week", "compared to last month" need overlay charts
    # WHAT TO SHOW: Dual-line chart with current + previous periods
    compare_to_previous = getattr(dsl, 'compare_to_previous', False)
    query_type = getattr(dsl, 'query_type', 'metrics')
    comparison_type = getattr(dsl, 'comparison_type', None)
    timeframe_desc = getattr(dsl, 'timeframe_description', '') or ''

    # Check for explicit time-based comparison (not entity comparison)
    # IMPORTANT: query_type='comparison' without time indicators should fall through
    # to RANKING if there's a breakdown (handled above)
    if comparison_type == 'time_vs_time':
        logger.info(f"[VISUAL_INTENT] Classified as COMPARISON (comparison_type=time_vs_time)")
        return VisualIntent.COMPARISON

    # Check for implicit comparison via timeframe
    if compare_to_previous:
        logger.info(f"[VISUAL_INTENT] Classified as COMPARISON (compare_to_previous=True)")
        return VisualIntent.COMPARISON

    # Check for "vs" language in timeframe (time comparisons, not entity comparisons)
    if 'vs' in timeframe_desc.lower() or 'compared' in timeframe_desc.lower():
        logger.info(f"[VISUAL_INTENT] Classified as COMPARISON (timeframe contains 'vs')")
        return VisualIntent.COMPARISON

    # Entity vs entity comparison without breakdown goes to COMPARISON
    # (e.g., "compare Campaign A vs Campaign B" - specific entities, not "all")
    if query_type == 'comparison' and not breakdown:
        logger.info(f"[VISUAL_INTENT] Classified as COMPARISON (query_type=comparison, no breakdown)")
        return VisualIntent.COMPARISON

    # 3. MULTI-METRIC: Queries for multiple metrics at once
    # WHY: "show spend and revenue" needs multiple cards
    # WHAT TO SHOW: Multiple cards + optional shared timeseries
    metric = getattr(dsl, 'metric', None)
    if isinstance(metric, list) and len(metric) > 1:
        logger.info(f"[VISUAL_INTENT] Classified as MULTI_METRIC ({len(metric)} metrics)")
        return VisualIntent.MULTI_METRIC

    # Also check result data for multi-metric structure
    if 'metrics' in result_data and isinstance(result_data.get('metrics'), dict):
        if len(result_data['metrics']) > 1:
            logger.info(f"[VISUAL_INTENT] Classified as MULTI_METRIC (result has multiple metrics)")
            return VisualIntent.MULTI_METRIC

    # 4. RANKING: Top-N queries with breakdown (fallback)
    # NOTE: Most ranking queries are caught by the EARLY RANKING CHECK above
    # This is a fallback for breakdown queries that didn't match keywords
    # WHY: Breakdown with reasonable top_n is almost always a ranking query
    # WHAT TO SHOW: Bar chart + table with rankings
    top_n = getattr(dsl, 'top_n', 5)

    if breakdown and top_n and top_n > 0 and top_n <= 50:
        logger.info(f"[VISUAL_INTENT] Classified as RANKING (breakdown with top_n={top_n}, fallback)")
        return VisualIntent.RANKING

    # 5. BREAKDOWN: Distribution queries (provider breakdown, etc.)
    # WHY: "spend by platform", "revenue breakdown" need distribution chart
    # WHAT TO SHOW: Bar/pie chart for distribution
    if breakdown:
        logger.info(f"[VISUAL_INTENT] Classified as BREAKDOWN (breakdown={breakdown})")
        return VisualIntent.BREAKDOWN

    # 6. TREND: Trend-focused queries
    # WHY: "how is spend trending?", "what's the trend?" need area chart
    # WHAT TO SHOW: Area chart emphasizing direction
    if 'trend' in (getattr(dsl, 'question', '') or '').lower():
        logger.info(f"[VISUAL_INTENT] Classified as TREND (question contains 'trend')")
        return VisualIntent.TREND

    # 7. SINGLE_METRIC: Default for simple metric queries
    # WHY: "What's my ROAS?" just needs a card + sparkline
    # WHAT TO SHOW: Card with sparkline, minimal extras
    logger.info(f"[VISUAL_INTENT] Classified as SINGLE_METRIC (default)")
    return VisualIntent.SINGLE_METRIC


def get_visual_strategy(intent: VisualIntent) -> VisualStrategy:
    """
    Map visual intent to a concrete display strategy.

    WHAT: Converts intent classification into actionable display rules

    WHY: Standardized mapping ensures consistent behavior

    Args:
        intent: Classified VisualIntent

    Returns:
        VisualStrategy with display flags

    Examples:
        >>> strategy = get_visual_strategy(VisualIntent.FILTERING)
        >>> strategy.show_table
        True
        >>> strategy.show_timeseries
        False
    """
    strategies = {
        VisualIntent.SINGLE_METRIC: VisualStrategy(
            intent=VisualIntent.SINGLE_METRIC,
            show_card=True,
            show_timeseries=True,  # Small sparkline in card, full chart optional
            show_comparison_overlay=False,
            show_breakdown_chart=False,
            show_table=False,
            max_charts=1,
            rationale="Simple metric query: card with sparkline is sufficient"
        ),

        VisualIntent.COMPARISON: VisualStrategy(
            intent=VisualIntent.COMPARISON,
            show_card=True,
            show_timeseries=True,
            show_comparison_overlay=True,  # KEY: Enable dual-line chart
            show_breakdown_chart=False,
            show_table=False,
            max_charts=1,
            rationale="Comparison query: dual-line chart shows current vs previous"
        ),

        VisualIntent.RANKING: VisualStrategy(
            intent=VisualIntent.RANKING,
            show_card=True,  # Summary card
            show_timeseries=False,  # Not needed for rankings
            show_comparison_overlay=False,
            show_breakdown_chart=True,  # Bar chart for rankings
            show_table=True,  # Detailed table
            max_charts=1,
            rationale="Ranking query: bar chart + table shows top performers"
        ),

        VisualIntent.ALL_ENTITIES: VisualStrategy(
            intent=VisualIntent.ALL_ENTITIES,
            show_card=False,  # No summary card for "all" queries
            show_timeseries=False,  # No charts
            show_comparison_overlay=False,
            show_breakdown_chart=False,  # No bar chart
            show_table=True,  # TABLE ONLY - clean list of all entities
            max_charts=0,
            rationale="All entities query: clean table showing all campaigns/adsets/ads"
        ),

        VisualIntent.FILTERING: VisualStrategy(
            intent=VisualIntent.FILTERING,
            show_card=False,  # Don't show summary for filtered results
            show_timeseries=False,  # Charts are misleading for zero-value filters
            show_comparison_overlay=False,
            show_breakdown_chart=False,  # No bar charts
            show_table=True,  # TABLE ONLY - this is the key insight
            max_charts=0,
            rationale="Filtering query: only show table of matching entities"
        ),

        VisualIntent.TREND: VisualStrategy(
            intent=VisualIntent.TREND,
            show_card=True,
            show_timeseries=True,  # Area chart for trend
            show_comparison_overlay=False,
            show_breakdown_chart=False,
            show_table=False,
            max_charts=1,
            rationale="Trend query: area chart emphasizes direction over time"
        ),

        VisualIntent.BREAKDOWN: VisualStrategy(
            intent=VisualIntent.BREAKDOWN,
            show_card=True,
            show_timeseries=False,
            show_comparison_overlay=False,
            show_breakdown_chart=True,
            show_table=True,  # Both chart and table for breakdown
            max_charts=1,
            rationale="Breakdown query: distribution chart + table"
        ),

        VisualIntent.MULTI_METRIC: VisualStrategy(
            intent=VisualIntent.MULTI_METRIC,
            show_card=True,  # Multiple cards
            show_timeseries=True,  # Shared timeseries
            show_comparison_overlay=False,
            show_breakdown_chart=False,
            show_table=False,
            max_charts=1,
            rationale="Multi-metric query: multiple cards with shared chart"
        ),
    }

    return strategies.get(intent, strategies[VisualIntent.SINGLE_METRIC])


def filter_visuals_by_strategy(
    payload: Dict[str, List[Dict[str, Any]]],
    strategy: VisualStrategy
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Apply visual strategy to filter/limit the visualization payload.

    WHAT: Removes visuals that don't match the strategy

    WHY: Prevents visual noise and information overload

    HOW:
    1. Remove cards if strategy.show_card=False
    2. Remove charts if strategy.show_timeseries/breakdown_chart=False
    3. Limit charts to strategy.max_charts
    4. Remove tables if strategy.show_table=False

    Args:
        payload: Raw visual payload from visual_builder
        strategy: Visual strategy to apply

    Returns:
        Filtered payload with only relevant visuals

    Examples:
        >>> # Filtering intent: remove all charts, keep only table
        >>> strategy = get_visual_strategy(VisualIntent.FILTERING)
        >>> filtered = filter_visuals_by_strategy(payload, strategy)
        >>> len(filtered['viz_specs'])
        0
        >>> len(filtered['tables'])  # Kept
        1
    """
    logger.info(f"[VISUAL_FILTER] Applying strategy: {strategy.intent.value} (rationale: {strategy.rationale})")

    filtered = {
        'cards': [],
        'viz_specs': [],
        'tables': [],
        'creative_cards': []  # NEW v2.5: Creative cards for ad creative queries
    }

    # Filter cards
    if strategy.show_card:
        filtered['cards'] = payload.get('cards', [])
        logger.debug(f"[VISUAL_FILTER] Keeping {len(filtered['cards'])} cards")
    else:
        logger.debug(f"[VISUAL_FILTER] Removing all cards")

    # Creative cards: Always pass through if present (they replace cards for creative queries)
    creative_cards = payload.get('creative_cards', [])
    if creative_cards:
        filtered['creative_cards'] = creative_cards
        logger.debug(f"[VISUAL_FILTER] Keeping {len(creative_cards)} creative cards")

    # Filter charts (viz_specs)
    if strategy.show_timeseries or strategy.show_breakdown_chart:
        all_charts = payload.get('viz_specs', [])

        # Prioritize charts based on strategy
        prioritized = []
        for chart in all_charts:
            chart_type = chart.get('type', '')

            # Comparison overlay: prioritize line charts
            if strategy.show_comparison_overlay and chart_type == 'line':
                prioritized.insert(0, chart)
            # Breakdown: prioritize bar charts
            elif strategy.show_breakdown_chart and chart_type in ('bar', 'grouped_bar'):
                prioritized.insert(0, chart)
            # Timeseries: keep area/line charts
            elif strategy.show_timeseries and chart_type in ('line', 'area'):
                prioritized.append(chart)
            else:
                prioritized.append(chart)

        # Limit to max_charts
        filtered['viz_specs'] = prioritized[:strategy.max_charts]
        logger.debug(f"[VISUAL_FILTER] Keeping {len(filtered['viz_specs'])} of {len(all_charts)} charts")
    else:
        logger.debug(f"[VISUAL_FILTER] Removing all charts")

    # Filter tables
    if strategy.show_table:
        filtered['tables'] = payload.get('tables', [])
        logger.debug(f"[VISUAL_FILTER] Keeping {len(filtered['tables'])} tables")
    else:
        logger.debug(f"[VISUAL_FILTER] Removing all tables")

    return filtered


def should_show_comparison_chart(dsl: Any, result_data: Dict[str, Any]) -> bool:
    """
    Quick check if this query should have a comparison (dual-line) chart.

    Used by visual_builder to decide whether to generate comparison overlay.

    Args:
        dsl: MetricQuery DSL object
        result_data: Execution result dictionary

    Returns:
        True if comparison chart is appropriate
    """
    intent = classify_visual_intent(dsl, result_data)
    return intent == VisualIntent.COMPARISON
