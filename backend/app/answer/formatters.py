"""
Metric Formatters
=================

Single source of truth for display formatting of metrics.

WHY:
- Avoid each caller formatting differently (AnswerBuilder vs QAService fallback)
- Prevent rounding bugs (e.g., CPC showing "0" due to integer formatting)
- Keep formatting rules explicit & easy to extend
- Ensure GPT receives correctly formatted values (no invention of formatting)

Used by:
- app/answer/answer_builder.py (hybrid LLM phrasing)
- app/services/qa_service.py (fallback deterministic phrasing)

Design principles:
- Pure functions: no side effects
- Type hints: clear contracts
- Defaults: sensible for None values
- Explicit sets: easy to see which metrics use which format

Related:
- app/metrics/registry.py: Defines which metrics are base vs derived
- app/dsl/executor.py: Computes metric values (raw numbers)
"""

from typing import Optional


# =====================================================================
# METRIC CATEGORIZATION BY DISPLAY FORMAT
# =====================================================================

# Currency metrics: dollar amounts with 2 decimals
# Examples: $1,234.56, $0.48, $25.30
CURRENCY = {
    # Base measures
    "spend",
    "revenue", 
    "profit",
    # Derived cost metrics
    "cpa",
    "cpl",
    "cpi",
    "cpp",
    "cpc",
    "cpm",
    # Derived value metrics
    "aov",
    "arpv",
}

# Ratio metrics: multipliers with × symbol
# Examples: 2.45×, 0.85×, 10.50×
RATIOS_X = {
    "roas",
    "poas",
}

# Percentage metrics: displayed as percentages with 1 decimal
# Examples: 4.2%, 15.7%, 0.5%
# NOTE: These are stored as decimals (0.042 = 4.2%)
PERCENT = {
    "ctr",
    "cvr",
}

# Count metrics: whole numbers with thousands separators
# Examples: 12,345, 1,000,000, 500
COUNTS = {
    "clicks",
    "impressions",
    "conversions",
    "leads",
    "installs",
    "purchases",
    "visitors",
}


# =====================================================================
# FORMATTING FUNCTIONS
# =====================================================================

def fmt_currency(v: Optional[float], symbol: str = "$") -> str:
    """
    Format numeric as currency with 2 decimals and thousands separators.
    
    Args:
        v: Numeric value (can be None)
        symbol: Currency symbol (default: "$")
        
    Returns:
        Formatted string like "$1,234.56" or "N/A" if None
        
    Examples:
        >>> fmt_currency(1234.56)
        "$1,234.56"
        
        >>> fmt_currency(0.4794)
        "$0.48"  # Rounded to 2 decimals
        
        >>> fmt_currency(None)
        "N/A"
        
        >>> fmt_currency(1234.56, "€")
        "€1,234.56"
    
    Design notes:
    - Always 2 decimals (even for whole numbers: $100.00)
    - Thousands separators for readability ($1,234,567.89)
    - Returns "N/A" for None (not "None" or "$0.00")
    """
    if v is None:
        return "N/A"
    return f"{symbol}{v:,.2f}"


def fmt_ratio_x(v: Optional[float]) -> str:
    """
    Format numeric ratio as multiplier with × symbol.
    
    Args:
        v: Numeric ratio (can be None)
        
    Returns:
        Formatted string like "2.45×" or "N/A" if None
        
    Examples:
        >>> fmt_ratio_x(2.456)
        "2.46×"
        
        >>> fmt_ratio_x(0.85)
        "0.85×"  # Below 1 = losing money
        
        >>> fmt_ratio_x(None)
        "N/A"
    
    Design notes:
    - 2 decimals for precision (2.45× vs 2.5×)
    - × symbol makes it clear it's a multiplier (not a currency)
    - Used for ROAS/POAS (return/profit on ad spend)
    """
    if v is None:
        return "N/A"
    return f"{v:.2f}×"


def fmt_percent(v: Optional[float]) -> str:
    """
    Format numeric fraction as percentage with 1 decimal.
    
    Args:
        v: Numeric fraction (0.042 = 4.2%, can be None)
        
    Returns:
        Formatted string like "4.2%" or "N/A" if None
        
    Examples:
        >>> fmt_percent(0.042)
        "4.2%"
        
        >>> fmt_percent(0.157)
        "15.7%"
        
        >>> fmt_percent(None)
        "N/A"
    
    Design notes:
    - Input is decimal fraction (0.042), output is percentage (4.2%)
    - 1 decimal for readability (4.2% vs 4.23%)
    - Used for CTR/CVR (engagement metrics)
    - No thousands separator needed (rates rarely > 100%)
    """
    if v is None:
        return "N/A"
    return f"{(v * 100):.1f}%"


def fmt_count(v: Optional[float]) -> str:
    """
    Format integer-like metrics as whole numbers with thousands separators.
    
    Args:
        v: Numeric count (can be None)
        
    Returns:
        Formatted string like "12,345" or "N/A" if None
        
    Examples:
        >>> fmt_count(1234)
        "1,234"
        
        >>> fmt_count(1234.9)
        "1,235"  # Rounds to nearest whole number
        
        >>> fmt_count(None)
        "N/A"
    
    Design notes:
    - No decimals (counts are whole numbers)
    - Thousands separators for readability (1,000,000)
    - Used for clicks, impressions, conversions, etc.
    - Rounds if given a float (defensive)
    """
    if v is None:
        return "N/A"
    return f"{v:,.0f}"


# =====================================================================
# MAIN ROUTING FUNCTION
# =====================================================================

def format_metric_value(
    metric: str,
    value: Optional[float],
    symbol: str = "$"
) -> str:
    """
    Route metric to appropriate formatter based on its type.
    
    This is the MAIN entry point for all metric formatting.
    
    Args:
        metric: Metric name (e.g., "cpc", "roas", "ctr")
        value: Numeric value to format (can be None)
        symbol: Currency symbol for currency metrics (default: "$")
        
    Returns:
        Formatted string appropriate for the metric type
        
    Examples:
        >>> format_metric_value("cpc", 0.4794)
        "$0.48"
        
        >>> format_metric_value("roas", 2.456)
        "2.46×"
        
        >>> format_metric_value("ctr", 0.042)
        "4.2%"
        
        >>> format_metric_value("clicks", 1234)
        "1,234"
        
        >>> format_metric_value("unknown_metric", 123.45)
        "123.45"  # Fallback: 2 decimals
    
    Design notes:
    - Case-insensitive metric matching
    - Fallback to 2-decimal float for unknown metrics
    - No business logic here (DISPLAY ONLY)
    - Pure function: same input → same output
    
    Related:
    - app/metrics/registry.py: get_metric_format() provides format hints
    - app/answer/answer_builder.py: Uses this to format facts for GPT
    - app/services/qa_service.py: Uses this for fallback answers
    """
    # Normalize metric name (case-insensitive)
    if isinstance(metric, list):
        # For multi-metric queries, use the first metric for formatting rules
        # (This is a simplified assumption, but better than crashing)
        m = (metric[0] if metric else "").lower()
    else:
        m = (metric or "").lower()
    
    # Route to appropriate formatter
    if m in CURRENCY:
        return fmt_currency(value, symbol)
    
    if m in RATIOS_X:
        return fmt_ratio_x(value)
    
    if m in PERCENT:
        return fmt_percent(value)
    
    if m in COUNTS:
        return fmt_count(value)
    
    # Fallback: 2-decimal float (for unknown/new metrics)
    if value is None:
        return "N/A"
    return f"{value:.2f}"


# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================

def format_delta_pct(delta_pct: Optional[float]) -> str:
    """
    Format percentage change with sign and 1 decimal.
    
    Args:
        delta_pct: Decimal change (0.19 = +19%, -0.05 = -5%)
        
    Returns:
        Formatted string like "+19.0%" or "-5.0%" or "N/A"
        
    Examples:
        >>> format_delta_pct(0.19)
        "+19.0%"
        
        >>> format_delta_pct(-0.05)
        "-5.0%"
        
        >>> format_delta_pct(None)
        "N/A"
    
    Design notes:
    - Always includes sign (+ or -) for clarity
    - 1 decimal for readability
    - Used for period-over-period comparisons
    """
    if delta_pct is None:
        return "N/A"
    
    sign = "+" if delta_pct >= 0 else ""
    return f"{sign}{(delta_pct * 100):.1f}%"


def get_metric_format_type(metric: str) -> str:
    """
    Get the format type for a metric (for debugging/introspection).
    
    Args:
        metric: Metric name
        
    Returns:
        Format type: "currency", "ratio", "percentage", "count", or "float"
        
    Examples:
        >>> get_metric_format_type("cpc")
        "currency"
        
        >>> get_metric_format_type("roas")
        "ratio"
        
        >>> get_metric_format_type("ctr")
        "percentage"
    """
    m = (metric or "").lower()
    
    if m in CURRENCY:
        return "currency"
    if m in RATIOS_X:
        return "ratio"
    if m in PERCENT:
        return "percentage"
    if m in COUNTS:
        return "count"
    
    return "float"

