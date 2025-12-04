"""
Answer Module - Formatters Only
================================

This module contains metric formatting utilities used by the semantic layer.

The original answer generation logic (answer_builder, intent_classifier, etc.)
has been replaced by the Agentic Copilot (app/agent/) using LangGraph + Claude.

Related files:
- app/answer/formatters.py: Metric value formatting utilities
- app/semantic/visual_builder.py: Uses formatters for visual output
- app/agent/nodes.py: New agentic answer generation
"""

from app.answer.formatters import (
    format_metric_value,
    format_delta_pct,
    fmt_currency,
    fmt_count,
    fmt_percent,
    fmt_ratio_x,
)

__all__ = [
    "format_metric_value",
    "format_delta_pct",
    "fmt_currency",
    "fmt_count",
    "fmt_percent",
    "fmt_ratio_x",
]
