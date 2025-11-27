from __future__ import annotations
from typing import Dict, Any, Optional, Tuple
from datetime import date, timedelta
from calendar import monthrange
import re

# Month name to number mapping
MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def _get_month_range(month: int, year: int) -> Tuple[date, date]:
    """Get the first and last day of a given month."""
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    return first_day, last_day


def _infer_year_for_month(month: int, reference_date: date = None) -> int:
    """
    Infer the most likely year for a given month based on context.

    Rules:
    - If the month is <= current month, assume current year
    - If the month is > current month, assume previous year
      (e.g., asking about "December" in January means last December)

    This ensures we always look at recent data, not future months.
    """
    if reference_date is None:
        reference_date = date.today()

    current_month = reference_date.month
    current_year = reference_date.year

    # If the month is in the future relative to current month, use previous year
    if month > current_month:
        return current_year - 1
    else:
        return current_year


class DateRangeParser:
    """
    Parses date-related phrases from natural language questions into structured date ranges.
    Enhanced to support:
    - All month names with year inference
    - "Month vs Month" comparison patterns
    - Explicit year specifications (e.g., "September 2024")
    """

    def __init__(self):
        # Build month pattern dynamically from MONTH_MAP
        month_names = "|".join(MONTH_MAP.keys())

        # Patterns ordered by specificity (more specific first)
        self.patterns = {
            # Month vs Month pattern (e.g., "september vs october", "sep vs oct")
            "month_vs_month": rf"({month_names})\s+(?:vs\.?|versus|compared?\s+to)\s+({month_names})",
            # Month with explicit year (e.g., "september 2024", "oct 2023")
            "month_with_year": rf"(?:in\s+)?({month_names})\s+(\d{{4}})",
            # Single month (e.g., "in september", "september")
            "single_month": rf"(?:in\s+)?({month_names})(?:\s|$|,|\?|!)",
            # Relative time patterns
            "last_week": r"last week",
            "this_week": r"this week",
            "last_month": r"last month",
            "this_month": r"this month",
            "yesterday": r"yesterday",
            "today": r"today",
        }

    def parse(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Parses a question to find a date range.
        Returns a dictionary with 'start', 'end' or 'last_n_days'.

        For "month vs month" patterns, returns a special structure with both ranges.
        """
        question_lower = question.lower()
        today = date.today()

        # Check for month vs month pattern first (highest priority)
        match = re.search(self.patterns["month_vs_month"], question_lower)
        if match:
            month1_name = match.group(1)
            month2_name = match.group(2)
            month1 = MONTH_MAP.get(month1_name)
            month2 = MONTH_MAP.get(month2_name)

            if month1 and month2:
                year1 = _infer_year_for_month(month1, today)
                year2 = _infer_year_for_month(month2, today)

                start1, end1 = _get_month_range(month1, year1)
                start2, end2 = _get_month_range(month2, year2)

                return {
                    "comparison_ranges": [
                        {"start": start1, "end": end1, "label": month1_name.capitalize()},
                        {"start": start2, "end": end2, "label": month2_name.capitalize()},
                    ]
                }

        # Check for month with explicit year
        match = re.search(self.patterns["month_with_year"], question_lower)
        if match:
            month_name = match.group(1)
            year = int(match.group(2))
            month = MONTH_MAP.get(month_name)

            if month:
                start, end = _get_month_range(month, year)
                return {"start": start, "end": end}

        # Check for single month
        match = re.search(self.patterns["single_month"], question_lower)
        if match:
            month_name = match.group(1)
            month = MONTH_MAP.get(month_name)

            if month:
                year = _infer_year_for_month(month, today)
                start, end = _get_month_range(month, year)
                return {"start": start, "end": end}

        # Check relative time patterns
        for key in ["last_week", "this_week", "last_month", "this_month", "yesterday", "today"]:
            if re.search(self.patterns[key], question_lower):
                return self._get_date_range_for_key(key, today)

        return None

    def _get_date_range_for_key(self, key: str, today: date) -> Dict[str, Any]:
        """
        Returns the corresponding date range for a matched relative time key.
        """
        if key == "last_week":
            return {"last_n_days": 7}
        elif key == "this_week":
            start_of_week = today - timedelta(days=today.weekday())
            return {"start": start_of_week, "end": today}
        elif key == "last_month":
            return {"last_n_days": 30}
        elif key == "this_month":
            first_day_of_month = today.replace(day=1)
            return {"start": first_day_of_month, "end": today}
        elif key == "yesterday":
            return {"last_n_days": 1}
        elif key == "today":
            return {"last_n_days": 1}

        return {}
