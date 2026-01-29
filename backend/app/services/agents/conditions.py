"""
Condition System for Agent Evaluation.

WHAT:
    Defines condition classes that evaluate metrics against thresholds,
    detect changes over time, and combine with logical operators.

WHY:
    Agents need flexible condition evaluation:
    - Simple: "ROAS > 2"
    - Change-based: "Spend increased 50% vs yesterday"
    - Composite: "ROAS > 2 AND spend > $100"
    - Negation: "ROAS is NOT > 2"

DESIGN:
    - Abstract Condition base class with evaluate() and explain()
    - Concrete implementations for each condition type
    - Factory function to deserialize from dict
    - ConditionResult captures both result and explanation

REFERENCES:
    - Agent System Implementation Plan (Phase 2: Core Engine)
    - backend/app/schemas.py (ThresholdCondition, ChangeCondition, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, Union
import logging

logger = logging.getLogger(__name__)


@dataclass
class EvalContext:
    """
    Context for condition evaluation.

    WHAT: Contains all data needed to evaluate a condition
    WHY: Decouples condition logic from data fetching

    Attributes:
        observations: Current metric values (e.g., {"roas": 2.5, "spend": 150.0})
        historical: Historical metric values by date (for change detection)
        entity_id: UUID of the entity being evaluated
        entity_name: Name for logging/display
        evaluated_at: Timestamp of evaluation
    """

    observations: Dict[str, float]
    historical: Optional[Dict[str, Dict[str, float]]] = None  # date -> metrics
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    evaluated_at: Optional[datetime] = None


@dataclass
class ConditionResult:
    """
    Result of condition evaluation.

    WHAT: Captures whether condition is met and explanation
    WHY: UI and Copilot need to explain why condition triggered or not

    Attributes:
        met: Whether condition evaluated to True
        explanation: Human-readable explanation
        inputs: What values were used for evaluation
        details: Additional details for debugging
    """

    met: bool
    explanation: str
    inputs: Dict[str, Any]
    details: Optional[Dict[str, Any]] = None


class Condition(ABC):
    """
    Abstract base class for conditions.

    WHAT: Defines interface for all condition types
    WHY: Enables polymorphic evaluation in the engine

    Methods:
        evaluate(): Evaluate condition against context, return ConditionResult
        explain(): Generate human-readable description of condition
        to_dict(): Serialize to dictionary for storage
        from_dict(): Deserialize from dictionary (class method)
    """

    @abstractmethod
    def evaluate(self, context: EvalContext) -> ConditionResult:
        """
        Evaluate the condition against the given context.

        Parameters:
            context: EvalContext with current and historical metrics

        Returns:
            ConditionResult with met status and explanation
        """
        pass

    @abstractmethod
    def explain(self) -> str:
        """
        Generate human-readable description of this condition.

        Returns:
            String description like "ROAS greater than 2.0"
        """
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize condition to dictionary.

        Returns:
            Dictionary representation for JSON storage
        """
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Condition":
        """
        Deserialize condition from dictionary.

        Parameters:
            data: Dictionary from to_dict() or API request

        Returns:
            Condition instance
        """
        pass


class ThresholdCondition(Condition):
    """
    Threshold-based condition.

    WHAT: Compare a metric value to a threshold
    WHY: Most common condition type - "ROAS > 2", "CPC < $3"

    Operators:
        gt: greater than
        gte: greater than or equal
        lt: less than
        lte: less than or equal
        eq: equal
        neq: not equal

    Example:
        ThresholdCondition(metric="roas", operator="gt", value=2.0)
        → "ROAS > 2.0" → True if current ROAS exceeds 2.0
    """

    OPERATORS = {
        "gt": lambda a, b: a > b,
        "gte": lambda a, b: a >= b,
        "lt": lambda a, b: a < b,
        "lte": lambda a, b: a <= b,
        "eq": lambda a, b: abs(a - b) < 0.0001,  # Float comparison
        "neq": lambda a, b: abs(a - b) >= 0.0001,
    }

    OPERATOR_NAMES = {
        "gt": "greater than",
        "gte": "greater than or equal to",
        "lt": "less than",
        "lte": "less than or equal to",
        "eq": "equal to",
        "neq": "not equal to",
    }

    def __init__(
        self,
        metric: str,
        operator: Literal["gt", "gte", "lt", "lte", "eq", "neq"],
        value: float,
    ):
        """
        Initialize threshold condition.

        Parameters:
            metric: Metric name to evaluate (e.g., "roas", "cpc", "spend")
            operator: Comparison operator
            value: Threshold value to compare against
        """
        if operator not in self.OPERATORS:
            raise ValueError(f"Invalid operator: {operator}")

        self.metric = metric
        self.operator = operator
        self.value = value

    def evaluate(self, context: EvalContext) -> ConditionResult:
        """
        Evaluate threshold against current metric value.

        Parameters:
            context: EvalContext with observations

        Returns:
            ConditionResult with comparison result
        """
        current_value = context.observations.get(self.metric)

        if current_value is None:
            return ConditionResult(
                met=False,
                explanation=f"Metric '{self.metric}' not available",
                inputs={"metric": self.metric, "value": None},
                details={"error": "metric_not_found"},
            )

        comparator = self.OPERATORS[self.operator]
        met = comparator(current_value, self.value)

        operator_name = self.OPERATOR_NAMES[self.operator]
        if met:
            explanation = (
                f"{self.metric.upper()} ({current_value:.2f}) is {operator_name} "
                f"{self.value:.2f}"
            )
        else:
            explanation = (
                f"{self.metric.upper()} ({current_value:.2f}) is NOT {operator_name} "
                f"{self.value:.2f}"
            )

        return ConditionResult(
            met=met,
            explanation=explanation,
            inputs={
                "metric": self.metric,
                "operator": self.operator,
                "threshold": self.value,
                "current_value": current_value,
            },
        )

    def explain(self) -> str:
        """Generate human-readable description."""
        operator_name = self.OPERATOR_NAMES[self.operator]
        return f"{self.metric.upper()} {operator_name} {self.value}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": "threshold",
            "metric": self.metric,
            "operator": self.operator,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThresholdCondition":
        """
        Deserialize from dictionary.

        Handles both named operators (gt, lt) and symbolic operators (<, >)
        for backwards compatibility with agents created before the fix.
        """
        # Map symbolic operators to named operators
        operator_map = {
            "<": "lt",
            "<=": "lte",
            ">": "gt",
            ">=": "gte",
            "=": "eq",
            "==": "eq",
            "!=": "neq",
        }
        raw_operator = data["operator"]
        operator = operator_map.get(raw_operator, raw_operator)

        return cls(
            metric=data["metric"],
            operator=operator,
            value=float(data["value"]),
        )


class ChangeCondition(Condition):
    """
    Change-based condition.

    WHAT: Detect metric changes over time
    WHY: "Alert when spend increases 50% vs yesterday"

    Reference periods:
        previous_day: Compare to previous day
        previous_week: Compare to same day last week
        previous_period: Compare to equivalent previous period

    Example:
        ChangeCondition(metric="spend", direction="increase", percent=50,
                       reference_period="previous_day")
        → True if spend increased 50%+ vs yesterday
    """

    def __init__(
        self,
        metric: str,
        direction: Literal["increase", "decrease", "any"],
        percent: float,
        reference_period: Literal["previous_day", "previous_week", "previous_period"],
    ):
        """
        Initialize change condition.

        Parameters:
            metric: Metric name to evaluate
            direction: Direction of change to detect
            percent: Percentage threshold (e.g., 50 for 50%)
            reference_period: What to compare against
        """
        if percent <= 0:
            raise ValueError("Percent must be positive")

        self.metric = metric
        self.direction = direction
        self.percent = percent
        self.reference_period = reference_period

    def evaluate(self, context: EvalContext) -> ConditionResult:
        """
        Evaluate change in metric vs reference period.

        Parameters:
            context: EvalContext with current and historical observations

        Returns:
            ConditionResult with change detection result
        """
        current_value = context.observations.get(self.metric)

        if current_value is None:
            return ConditionResult(
                met=False,
                explanation=f"Metric '{self.metric}' not available",
                inputs={"metric": self.metric, "current_value": None},
                details={"error": "metric_not_found"},
            )

        # Get reference value from historical data
        reference_value = self._get_reference_value(context)

        if reference_value is None:
            return ConditionResult(
                met=False,
                explanation=f"No historical data for {self.reference_period}",
                inputs={
                    "metric": self.metric,
                    "current_value": current_value,
                    "reference_value": None,
                },
                details={"error": "no_historical_data"},
            )

        # Calculate percentage change
        if reference_value == 0:
            if current_value > 0:
                change_pct = float("inf")
            elif current_value < 0:
                change_pct = float("-inf")
            else:
                change_pct = 0.0
        else:
            change_pct = ((current_value - reference_value) / abs(reference_value)) * 100

        # Check if change matches direction
        met = False
        if self.direction == "increase":
            met = change_pct >= self.percent
        elif self.direction == "decrease":
            met = change_pct <= -self.percent
        elif self.direction == "any":
            met = abs(change_pct) >= self.percent

        # Generate explanation
        change_str = f"{abs(change_pct):.1f}%"
        if change_pct >= 0:
            direction_str = "increased"
        else:
            direction_str = "decreased"

        if met:
            explanation = (
                f"{self.metric.upper()} {direction_str} {change_str} "
                f"(from {reference_value:.2f} to {current_value:.2f})"
            )
        else:
            explanation = (
                f"{self.metric.upper()} {direction_str} {change_str}, "
                f"threshold is {self.percent}% {self.direction}"
            )

        return ConditionResult(
            met=met,
            explanation=explanation,
            inputs={
                "metric": self.metric,
                "current_value": current_value,
                "reference_value": reference_value,
                "change_percent": change_pct,
                "threshold_percent": self.percent,
                "direction": self.direction,
            },
        )

    def _get_reference_value(self, context: EvalContext) -> Optional[float]:
        """
        Get the reference value from historical data.

        Parameters:
            context: EvalContext with historical observations

        Returns:
            Reference value or None if not available
        """
        if not context.historical:
            return None

        # Sort dates and find reference date
        dates = sorted(context.historical.keys())
        if not dates:
            return None

        if self.reference_period == "previous_day":
            # Get most recent historical date
            if dates:
                ref_date = dates[-1]
                return context.historical[ref_date].get(self.metric)

        elif self.reference_period == "previous_week":
            # Get date from ~7 days ago
            if len(dates) >= 7:
                ref_date = dates[-7]
                return context.historical[ref_date].get(self.metric)

        elif self.reference_period == "previous_period":
            # Get first date in historical data (start of previous period)
            if dates:
                ref_date = dates[0]
                return context.historical[ref_date].get(self.metric)

        return None

    def explain(self) -> str:
        """Generate human-readable description."""
        return (
            f"{self.metric.upper()} {self.direction}s {self.percent}% "
            f"vs {self.reference_period.replace('_', ' ')}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": "change",
            "metric": self.metric,
            "direction": self.direction,
            "percent": self.percent,
            "reference_period": self.reference_period,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChangeCondition":
        """Deserialize from dictionary."""
        return cls(
            metric=data["metric"],
            direction=data["direction"],
            percent=float(data["percent"]),
            reference_period=data["reference_period"],
        )


class CompositeCondition(Condition):
    """
    Composite condition combining multiple conditions.

    WHAT: AND/OR logic for multiple conditions
    WHY: Complex rules like "ROAS > 2 AND spend > $100"

    Operators:
        and: All conditions must be true
        or: At least one condition must be true

    Example:
        CompositeCondition(
            operator="and",
            conditions=[
                ThresholdCondition("roas", "gt", 2.0),
                ThresholdCondition("spend", "gt", 100),
            ]
        )
    """

    def __init__(
        self,
        operator: Literal["and", "or"],
        conditions: List[Condition],
    ):
        """
        Initialize composite condition.

        Parameters:
            operator: Logical operator ("and" or "or")
            conditions: List of conditions to combine
        """
        if len(conditions) < 2:
            raise ValueError("Composite condition requires at least 2 conditions")

        self.operator = operator
        self.conditions = conditions

    def evaluate(self, context: EvalContext) -> ConditionResult:
        """
        Evaluate all conditions with logical operator.

        Parameters:
            context: EvalContext for evaluation

        Returns:
            ConditionResult with combined result
        """
        results = [c.evaluate(context) for c in self.conditions]

        if self.operator == "and":
            met = all(r.met for r in results)
            if met:
                explanation = f"All conditions met: {'; '.join(r.explanation for r in results)}"
            else:
                failed = [r for r in results if not r.met]
                explanation = f"Not all conditions met. Failed: {'; '.join(r.explanation for r in failed)}"
        else:  # or
            met = any(r.met for r in results)
            if met:
                passed = [r for r in results if r.met]
                explanation = f"At least one condition met: {'; '.join(r.explanation for r in passed)}"
            else:
                explanation = f"No conditions met: {'; '.join(r.explanation for r in results)}"

        return ConditionResult(
            met=met,
            explanation=explanation,
            inputs={
                "operator": self.operator,
                "conditions": [r.inputs for r in results],
            },
            details={
                "results": [{"met": r.met, "explanation": r.explanation} for r in results]
            },
        )

    def explain(self) -> str:
        """Generate human-readable description."""
        operator_str = " AND " if self.operator == "and" else " OR "
        return f"({operator_str.join(c.explain() for c in self.conditions)})"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": "composite",
            "operator": self.operator,
            "conditions": [c.to_dict() for c in self.conditions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompositeCondition":
        """Deserialize from dictionary."""
        conditions = [condition_from_dict(c) for c in data["conditions"]]
        return cls(
            operator=data["operator"],
            conditions=conditions,
        )


class NotCondition(Condition):
    """
    Negation condition.

    WHAT: Negate another condition
    WHY: "Alert when ROAS is NOT > 2"

    Example:
        NotCondition(ThresholdCondition("roas", "gt", 2.0))
        → True when ROAS <= 2.0
    """

    def __init__(self, condition: Condition):
        """
        Initialize negation condition.

        Parameters:
            condition: Condition to negate
        """
        self.condition = condition

    def evaluate(self, context: EvalContext) -> ConditionResult:
        """
        Evaluate negated condition.

        Parameters:
            context: EvalContext for evaluation

        Returns:
            ConditionResult with negated result
        """
        result = self.condition.evaluate(context)

        return ConditionResult(
            met=not result.met,
            explanation=f"NOT ({result.explanation}) → {not result.met}",
            inputs={
                "negated": True,
                "inner_condition": result.inputs,
            },
            details={
                "inner_result": {
                    "met": result.met,
                    "explanation": result.explanation,
                }
            },
        )

    def explain(self) -> str:
        """Generate human-readable description."""
        return f"NOT ({self.condition.explain()})"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": "not",
            "condition": self.condition.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotCondition":
        """Deserialize from dictionary."""
        condition = condition_from_dict(data["condition"])
        return cls(condition=condition)


def condition_from_dict(data: Dict[str, Any]) -> Condition:
    """
    Factory function to deserialize condition from dictionary.

    WHAT: Create appropriate Condition subclass from dict
    WHY: Unified deserialization for all condition types

    Parameters:
        data: Dictionary with "type" field and condition-specific fields

    Returns:
        Appropriate Condition subclass instance

    Raises:
        ValueError: If condition type is unknown
    """
    condition_type = data.get("type")

    if condition_type == "threshold":
        return ThresholdCondition.from_dict(data)
    elif condition_type == "change":
        return ChangeCondition.from_dict(data)
    elif condition_type == "composite":
        return CompositeCondition.from_dict(data)
    elif condition_type == "not":
        return NotCondition.from_dict(data)
    else:
        raise ValueError(f"Unknown condition type: {condition_type}")
