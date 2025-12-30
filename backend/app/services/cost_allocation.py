"""Manual cost allocation logic.

WHAT: Pro-rates manual costs across date ranges for P&L inclusion
WHY: Monthly P&L must include only the portion of costs overlapping the period
REFERENCES:
  - app/routers/finance.py: Uses these functions
  - app/models.py:ManualCost: Data model
  - app/tests/test_cost_allocation.py: Unit tests

Allocation rules:
  - one_off: Include if date falls within [period_start, period_end)
  - range: Pro-rate daily across [start, end), include overlapping days only
"""

from datetime import date, timedelta
from typing import List, Dict
from app.models import ManualCost


def calculate_allocated_amount(
    cost: ManualCost,
    period_start: date,
    period_end: date,  # Exclusive
) -> float:
    """Calculate the portion of a manual cost that falls within a period.

    WHAT: Pro-rates cost based on overlapping days
    WHY: Monthly view must include only relevant portion of multi-month costs

    Args:
        cost: ManualCost with allocation info
        period_start: Inclusive start of target period
        period_end: Exclusive end of target period

    Returns:
        Allocated amount in USD for this period

    Examples:
        # One-off inside period → full amount
        one_off(date=2025-10-15), period=[2025-10-01, 2025-11-01) → full amount

        # One-off outside period → 0
        one_off(date=2025-09-15), period=[2025-10-01, 2025-11-01) → 0

        # Range fully inside → full amount
        range(start=2025-10-05, end=2025-10-15), period=[2025-10-01, 2025-11-01) → full

        # Range partially overlapping → pro-rated
        range(start=2025-09-20, end=2025-10-10), period=[2025-10-01, 2025-11-01)
          → 10 days / 20 days = 50% of amount
    """
    if cost.allocation_type == "one_off":
        # Include if date falls within period
        cost_date = (
            cost.allocation_date.date()
            if hasattr(cost.allocation_date, "date")
            else cost.allocation_date
        )
        if cost_date is None:
            # If no date specified, skip this cost (user needs to set a date)
            return 0.0
        if period_start <= cost_date < period_end:
            return float(cost.amount_dollar)
        return 0.0

    elif cost.allocation_type == "range":
        # Pro-rate based on overlapping days
        cost_start = (
            cost.allocation_start.date()
            if hasattr(cost.allocation_start, "date")
            else cost.allocation_start
        )
        cost_end = (
            cost.allocation_end.date()
            if hasattr(cost.allocation_end, "date")
            else cost.allocation_end
        )

        # Skip if dates are missing
        if cost_start is None or cost_end is None:
            return 0.0

        # Calculate overlap
        overlap_start = max(cost_start, period_start)
        overlap_end = min(cost_end, period_end)

        if overlap_start >= overlap_end:
            return 0.0  # No overlap

        # Count overlapping days
        overlap_days = (overlap_end - overlap_start).days
        total_days = (cost_end - cost_start).days

        if total_days == 0:
            return 0.0

        # Pro-rate
        return float(cost.amount_dollar) * (overlap_days / total_days)

    return 0.0


def get_allocated_costs(
    costs: List[ManualCost], period_start: date, period_end: date
) -> Dict[str, float]:
    """Get all costs allocated to a period, grouped by category.

    WHAT: Aggregates manual costs by category for P&L table
    WHY: P&L needs one row per category with total

    Returns:
        Dict mapping category → total allocated amount
    """
    category_totals = {}

    for cost in costs:
        allocated = calculate_allocated_amount(cost, period_start, period_end)
        if allocated > 0:
            category = cost.category
            category_totals[category] = category_totals.get(category, 0) + allocated

    return category_totals
