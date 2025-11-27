"""
Context Extractor - Rich Insight Extraction from Query Results

WHAT: Extracts contextual insights (trends, outliers, comparisons) from MetricResult
WHY: Provides GPT with rich material for natural, informative answers instead of just raw numbers
WHERE: Used by AnswerBuilder before GPT call

ARCHITECTURE:
- Pure functions (no side effects, no LLM calls)
- Deterministic (same input = same output)
- Fully testable (no mocking needed)
- Type-safe (Pydantic models)

REFERENCES:
- Called by: app/answer/answer_builder.py::AnswerBuilder.build_answer()
- Uses: app/dsl/schema.py::MetricResult
- Docs: backend/docs/QA_SYSTEM_ARCHITECTURE.md (DSL v2.0.1)
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from app.dsl.schema import MetricResult, MetricQuery
from app.answer.formatters import format_metric_value, format_delta_pct


class TrendDirection(str, Enum):
    """
    WHAT: Enum for timeseries trend direction
    WHY: Type-safe trend classification
    """
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class PerformanceLevel(str, Enum):
    """
    WHAT: Enum for metric performance assessment
    WHY: Standardized performance classification
    """
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    CONCERNING = "concerning"


class RichContext:
    """
    WHAT: Rich contextual insights extracted from query results
    WHY: Provides GPT with structured context for natural answer generation
    
    FIELDS:
    - metric_name: Human-readable metric name
    - metric_value: Primary metric value (formatted)
    - metric_value_raw: Raw numeric value (for GPT calculations)
    - comparison: Optional comparison to previous period
    - workspace_comparison: Optional comparison to workspace average
    - trend: Optional trend analysis from timeseries
    - outliers: Optional list of notable outliers in breakdown
    - top_performer: Optional best performing entity
    - bottom_performer: Optional worst performing entity
    - performance_level: Overall performance assessment
    """
    
    def __init__(self):
        self.metric_name: str = ""
        self.metric_value: str = ""
        self.metric_value_raw: float = 0.0
        self.comparison: Optional[Dict[str, Any]] = None
        self.workspace_comparison: Optional[Dict[str, Any]] = None
        self.trend: Optional[Dict[str, Any]] = None
        self.outliers: List[Dict[str, Any]] = []
        self.top_performer: Optional[Dict[str, Any]] = None
        self.bottom_performer: Optional[Dict[str, Any]] = None
        self.performance_level: Optional[PerformanceLevel] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        WHAT: Convert to dictionary for GPT prompt
        WHY: JSON-serializable format for LLM consumption
        """
        return {
            k: v for k, v in self.__dict__.items() 
            if v is not None and v != [] and v != ""
        }


def extract_rich_context(
    result: MetricResult,
    query: MetricQuery,
    workspace_avg: Optional[float] = None
) -> RichContext:
    """
    WHAT: Main entry point - extracts all available context from query result
    WHY: Single function to get complete rich context for answer generation
    WHERE: Called by AnswerBuilder.build_answer()
    
    ARGS:
        result: Query execution result with summary, timeseries, breakdown
        query: Original query (for metric name, type)
        workspace_avg: Optional workspace average for this metric (computed by executor)
    
    RETURNS:
        RichContext: Structured insights ready for GPT prompt
    
    EXAMPLE:
        >>> result = MetricResult(summary=2.45, previous=2.06, delta_pct=0.189, ...)
        >>> query = MetricQuery(metric="roas", ...)
        >>> context = extract_rich_context(result, query, workspace_avg=2.30)
        >>> context.metric_value
        "2.45×"
        >>> context.comparison
        {"previous": "2.06×", "change": "+18.9%", "direction": "improved"}
    
    REFERENCES:
        - Uses: _extract_comparison(), _extract_trend(), _extract_outliers()
        - Docs: QA_SYSTEM_ARCHITECTURE.md (Rich Context Extraction)
    """
    context = RichContext()
    
    # Basic metric info
    metric = query.metric
    context.metric_name = metric.upper()
    context.metric_value_raw = result.summary
    context.metric_value = format_metric_value(metric, result.summary)
    
    # Comparison to previous period
    if result.previous is not None:
        context.comparison = _extract_comparison(metric, result)
    
    # Comparison to workspace average
    if workspace_avg is not None:
        context.workspace_comparison = _extract_workspace_comparison(
            metric, result.summary, workspace_avg
        )
    
    # Trend analysis from timeseries
    if result.timeseries and len(result.timeseries) > 1:
        context.trend = _extract_trend(metric, result.timeseries)
    
    # Outlier detection in breakdown
    if result.breakdown and len(result.breakdown) > 0:
        context.outliers = _extract_outliers(metric, result.breakdown)
        context.top_performer = _extract_top_performer(metric, result.breakdown)
        context.bottom_performer = _extract_bottom_performer(metric, result.breakdown)
    
    # Performance assessment
    context.performance_level = _assess_performance(
        metric, 
        result.summary, 
        workspace_avg, 
        result.delta_pct
    )
    
    return context


def _extract_comparison(metric: str, result: MetricResult) -> Dict[str, Any]:
    """
    WHAT: Extract comparison to previous period
    WHY: Provides context on how metric changed over time
    WHERE: Called by extract_rich_context() when result.previous exists
    
    RETURNS:
        {
            "previous": "2.06×",           # Formatted previous value
            "previous_raw": 2.06,          # Raw numeric value
            "change": "+18.9%",            # Formatted delta with sign
            "change_raw": 0.189,           # Raw delta (0.189 = +18.9%)
            "direction": "improved"        # Human-readable direction
        }
    
    LOGIC:
        - For "higher is better" metrics (ROAS, revenue, clicks):
            - Increase = "improved", Decrease = "declined"
        - For "lower is better" metrics (CPC, CPA, CPL):
            - Decrease = "improved", Increase = "worsened"
    
    REFERENCES:
        - Uses: app/answer/formatters.py::format_metric_value()
        - Uses: app/answer/formatters.py::format_delta_pct()
    """
    # Higher is better metrics
    higher_is_better = [
        "roas", "poas", "revenue", "profit", "clicks",
        "impressions", "conversions", "leads", "installs",
        "purchases", "visitors", "ctr", "cvr", "aov", "arpv"
    ]

    # Lower is better metrics
    lower_is_better = ["cpc", "cpm", "cpa", "cpl", "cpi", "cpp"]

    # Handle None delta_pct (e.g., 0 to 0 comparison)
    if result.delta_pct is None:
        return {
            "previous": format_metric_value(metric, result.previous),
            "previous_raw": result.previous,
            "change": "N/A",
            "change_raw": None,
            "direction": "unchanged"
        }

    # Determine direction
    if result.delta_pct > 0:
        if metric in higher_is_better:
            direction = "improved"
        elif metric in lower_is_better:
            direction = "worsened"
        else:
            direction = "increased"
    elif result.delta_pct < 0:
        if metric in higher_is_better:
            direction = "declined"
        elif metric in lower_is_better:
            direction = "improved"
        else:
            direction = "decreased"
    else:
        direction = "remained stable"
    
    return {
        "previous": format_metric_value(metric, result.previous),
        "previous_raw": result.previous,
        "change": format_delta_pct(result.delta_pct),
        "change_raw": result.delta_pct,
        "direction": direction
    }


def _extract_workspace_comparison(
    metric: str, 
    value: float, 
    workspace_avg: float
) -> Dict[str, Any]:
    """
    WHAT: Compare metric value to workspace average
    WHY: Provides context on how this query's value relates to overall performance
    WHERE: Called by extract_rich_context() when workspace_avg is provided
    
    RETURNS:
        {
            "workspace_avg": "2.30×",        # Formatted workspace average
            "workspace_avg_raw": 2.30,       # Raw numeric value
            "deviation_pct": 0.065,          # (2.45 - 2.30) / 2.30 = 6.5%
            "comparison": "above average"    # Human-readable comparison
        }
    
    LOGIC:
        - Within ±10% = "average"
        - >10% higher = "above average"
        - <10% lower = "below average"
    
    REFERENCES:
        - Uses: app/answer/formatters.py::format_metric_value()
    """
    # Guard against division by zero
    if workspace_avg == 0:
        # If workspace avg is 0, we can't compute deviation percentage
        # Return None to indicate no comparison is possible
        return None
    
    deviation_pct = (value - workspace_avg) / workspace_avg
    
    if abs(deviation_pct) < 0.10:
        comparison = "average"
    elif deviation_pct > 0:
        comparison = "above average"
    else:
        comparison = "below average"
    
    return {
        "workspace_avg": format_metric_value(metric, workspace_avg),
        "workspace_avg_raw": workspace_avg,
        "deviation_pct": deviation_pct,
        "comparison": comparison
    }


def _extract_trend(metric: str, timeseries: List[Dict]) -> Dict[str, Any]:
    """
    WHAT: Analyze trend from timeseries data
    WHY: Describes how metric evolved over time (not just start vs end)
    WHERE: Called by extract_rich_context() when timeseries has >1 data point
    
    RETURNS:
        {
            "direction": "increasing",     # TrendDirection enum value
            "start_value": "2.10×",       # First value in series
            "end_value": "2.80×",         # Last value in series
            "peak_value": "2.90×",        # Highest value
            "peak_date": "2025-10-03",    # Date of peak
            "low_value": "2.05×",         # Lowest value
            "low_date": "2025-09-29",     # Date of low
            "volatility": 0.15            # Coefficient of variation
        }
    
    LOGIC:
        - Increasing: End > Start by >10%
        - Decreasing: End < Start by >10%
        - Stable: Within ±10%
        - Volatile: Std dev / mean > 0.20
    
    REFERENCES:
        - Uses: app/answer/formatters.py::format_metric_value()
        - Docs: QA_SYSTEM_ARCHITECTURE.md (Trend Detection)
    """
    values = [point["value"] for point in timeseries]
    dates = [point["date"] for point in timeseries]
    
    start = values[0]
    end = values[-1]
    mean = sum(values) / len(values)
    
    # Standard deviation (population)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std_dev = variance ** 0.5
    volatility = std_dev / mean if mean != 0 else 0
    
    # Determine direction
    change_pct = (end - start) / start if start != 0 else 0
    
    if abs(change_pct) < 0.10:
        direction = TrendDirection.STABLE
    elif change_pct > 0.10:
        direction = TrendDirection.INCREASING
    elif change_pct < -0.10:
        direction = TrendDirection.DECREASING
    else:
        direction = TrendDirection.STABLE
    
    # Check volatility
    if volatility > 0.20:
        direction = TrendDirection.VOLATILE
    
    # Find peak and low
    peak_idx = values.index(max(values))
    low_idx = values.index(min(values))
    
    return {
        "direction": direction,
        "start_value": format_metric_value(metric, start),
        "start_value_raw": start,
        "end_value": format_metric_value(metric, end),
        "end_value_raw": end,
        "peak_value": format_metric_value(metric, values[peak_idx]),
        "peak_value_raw": values[peak_idx],
        "peak_date": dates[peak_idx],
        "low_value": format_metric_value(metric, values[low_idx]),
        "low_value_raw": values[low_idx],
        "low_date": dates[low_idx],
        "volatility": round(volatility, 3)
    }


def _extract_outliers(
    metric: str, 
    breakdown: List[Dict],
    threshold: float = 2.0
) -> List[Dict[str, Any]]:
    """
    WHAT: Detect statistical outliers in breakdown data
    WHY: Identifies entities that performed significantly differently from the rest
    WHERE: Called by extract_rich_context() when breakdown exists
    
    ARGS:
        metric: Metric name for formatting
        breakdown: List of entities with values
        threshold: Number of standard deviations to consider outlier (default: 2.0)
    
    RETURNS:
        [
            {
                "label": "Summer Sale",
                "value": "5.80×",
                "value_raw": 5.80,
                "z_score": 2.3,
                "type": "high"  # or "low"
            }
        ]
    
    LOGIC:
        - Calculate mean and std dev of breakdown values
        - Outlier if |z-score| > threshold
        - z-score = (value - mean) / std_dev
    
    REFERENCES:
        - Uses: app/answer/formatters.py::format_metric_value()
        - Docs: QA_SYSTEM_ARCHITECTURE.md (Outlier Detection)
    """
    if len(breakdown) < 3:
        return []  # Need at least 3 data points for meaningful outlier detection
    
    values = [item["value"] for item in breakdown]
    mean = sum(values) / len(values)
    
    # Standard deviation
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std_dev = variance ** 0.5
    
    if std_dev == 0:
        return []  # All values are the same, no outliers
    
    outliers = []
    for item in breakdown:
        z_score = (item["value"] - mean) / std_dev
        
        if abs(z_score) > threshold:
            outliers.append({
                "label": item["label"],
                "value": format_metric_value(metric, item["value"]),
                "value_raw": item["value"],
                "z_score": round(z_score, 2),
                "type": "high" if z_score > 0 else "low"
            })
    
    return outliers


def _extract_top_performer(metric: str, breakdown: List[Dict]) -> Dict[str, Any]:
    """
    WHAT: Extract top performing entity from breakdown
    WHY: Highlights the winner for "which campaign had highest X" questions
    WHERE: Called by extract_rich_context() when breakdown exists
    
    RETURNS:
        {
            "label": "Summer Sale",
            "value": "3.20×",
            "value_raw": 3.20,
            "rank": 1
        }
    
    REFERENCES:
        - Uses: app/answer/formatters.py::format_metric_value()
    """
    if not breakdown:
        return None
    
    top = breakdown[0]  # Already sorted by executor
    
    return {
        "label": top["label"],
        "value": format_metric_value(metric, top["value"]),
        "value_raw": top["value"],
        "rank": 1
    }


def _extract_bottom_performer(metric: str, breakdown: List[Dict]) -> Dict[str, Any]:
    """
    WHAT: Extract worst performing entity from breakdown
    WHY: Identifies underperformers for optimization opportunities
    WHERE: Called by extract_rich_context() when breakdown exists
    
    RETURNS:
        {
            "label": "Winter Promo",
            "value": "1.20×",
            "value_raw": 1.20,
            "rank": 5  # Last in breakdown
        }
    
    REFERENCES:
        - Uses: app/answer/formatters.py::format_metric_value()
    """
    if not breakdown or len(breakdown) < 2:
        return None
    
    bottom = breakdown[-1]  # Last item in sorted breakdown
    
    return {
        "label": bottom["label"],
        "value": format_metric_value(metric, bottom["value"]),
        "value_raw": bottom["value"],
        "rank": len(breakdown)
    }


def _assess_performance(
    metric: str,
    value: float,
    workspace_avg: Optional[float],
    delta_pct: Optional[float]
) -> PerformanceLevel:
    """
    WHAT: Assess overall performance level of metric
    WHY: Provides qualitative assessment for tone selection in GPT prompt
    WHERE: Called by extract_rich_context()
    
    RETURNS:
        PerformanceLevel enum: EXCELLENT, GOOD, AVERAGE, POOR, CONCERNING
    
    LOGIC:
        1. If workspace_avg available:
           - EXCELLENT: >150% of workspace avg
           - GOOD: 110-150% of workspace avg
           - AVERAGE: 90-110% of workspace avg
           - POOR: 70-90% of workspace avg
           - CONCERNING: <70% of workspace avg
        
        2. If delta_pct available (no workspace_avg):
           - EXCELLENT: Improved by >50%
           - GOOD: Improved by 10-50%
           - AVERAGE: Changed by <10%
           - POOR: Declined by 10-30%
           - CONCERNING: Declined by >30%
        
        3. Otherwise: AVERAGE (not enough context)
    
    NOTE: For "lower is better" metrics (CPC, CPA), flip the logic
    
    REFERENCES:
        - Docs: QA_SYSTEM_ARCHITECTURE.md (Performance Assessment)
    """
    # Lower is better metrics
    lower_is_better = ["cpc", "cpm", "cpa", "cpl", "cpi", "cpp"]
    flip_logic = metric in lower_is_better
    
    # Strategy 1: Workspace comparison
    if workspace_avg is not None and workspace_avg != 0:
        ratio = value / workspace_avg
        
        if flip_logic:
            ratio = 1 / ratio  # Flip for lower-is-better metrics
        
        if ratio > 1.5:
            return PerformanceLevel.EXCELLENT
        elif ratio > 1.1:
            return PerformanceLevel.GOOD
        elif ratio > 0.9:
            return PerformanceLevel.AVERAGE
        elif ratio > 0.7:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CONCERNING
    
    # Strategy 2: Delta comparison
    elif delta_pct is not None:
        change = delta_pct if not flip_logic else -delta_pct
        
        if change > 0.5:
            return PerformanceLevel.EXCELLENT
        elif change > 0.1:
            return PerformanceLevel.GOOD
        elif abs(change) < 0.1:
            return PerformanceLevel.AVERAGE
        elif change < -0.1 and change > -0.3:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CONCERNING
    
    # Strategy 3: No context
    else:
        return PerformanceLevel.AVERAGE

