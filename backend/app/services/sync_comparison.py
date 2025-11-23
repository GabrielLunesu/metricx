"""Metric comparison helpers for sync ingestion.

WHAT:
    Provides utilities to detect whether new metric values actually differ
    from existing values before writing to the database.

WHY:
    - Allows aggressive polling without rewriting identical rows.
    - Reduces unnecessary writes and helps compute data freshness.

REFERENCES:
    - docs/living-docs/REALTIME_SYNC_STATUS.md
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Iterable

from app.models import MetricFact
from app.schemas import MetricFactCreate


DECIMAL_FIELDS: Iterable[str] = (
    "spend",
    "conversions",
    "revenue",
    "leads",
    "installs",
    "purchases",
    "visitors",
    "profit",
)

INT_FIELDS: Iterable[str] = ("impressions", "clicks")

OTHER_FIELDS: Iterable[str] = ("currency",)


def _to_decimal(value) -> Decimal:
    """Safe Decimal conversion (None -> 0)."""
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal("0")


def _to_int(value) -> int:
    if value is None:
        return 0
    return int(value)


def has_metrics_changed(existing: MetricFact, new_fact: MetricFactCreate) -> bool:
    """Return True if ANY metric field has changed."""
    for field in DECIMAL_FIELDS:
        if _to_decimal(getattr(existing, field)) != _to_decimal(getattr(new_fact, field)):
            return True

    for field in INT_FIELDS:
        if _to_int(getattr(existing, field)) != _to_int(getattr(new_fact, field)):
            return True

    for field in OTHER_FIELDS:
        if getattr(existing, field) != getattr(new_fact, field):
            return True

    return False


