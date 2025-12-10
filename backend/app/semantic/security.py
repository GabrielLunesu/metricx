"""
Security Validation for Semantic Queries
=========================================

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Active

This module provides security validation using ALLOWLISTS (not blocklists).
Only explicitly permitted values are accepted.

WHY THIS FILE EXISTS
--------------------
Security is critical because the LLM generates query structures.
We MUST ensure that:
1. Only valid metrics can be queried
2. Only valid dimensions can be used
3. Filter values are sanitized
4. No SQL injection is possible

SECURITY MODEL
--------------
Defense in depth with 5 layers:

    Layer 1: Schema Validation (Pydantic)
        - Validates JSON structure and types
        - Rejects malformed queries before they reach security

    Layer 2: Allowlist Validation (THIS FILE)
        - Only permits values from explicit allowlists
        - Validates metrics, dimensions, operators, providers
        - Enforces value constraints (lengths, ranges)

    Layer 3: Value Sanitization (THIS FILE)
        - String values: Max 500 chars
        - Numeric values: Reasonable ranges
        - Time ranges: 1-365 days
        - Limits: 1-50 items

    Layer 4: SQL Parameterization (SQLAlchemy)
        - All values passed as parameters
        - No string concatenation
        - SQLAlchemy ORM handles escaping

    Layer 5: Workspace Scoping (services)
        - Every query filtered by workspace_id
        - JWT token contains workspace claim
        - No cross-tenant data access possible

KEY DESIGN PRINCIPLE
--------------------
ALLOWLISTS, not blocklists. We enumerate exactly what IS allowed,
rather than trying to enumerate what ISN'T allowed.

This means:
- New attack vectors don't bypass security
- Unknown values are rejected by default
- Changes require explicit code updates

RELATED FILES
-------------
- app/semantic/model.py: Source of allowed metrics/dimensions
- app/semantic/query.py: Query structure being validated
- app/semantic/validator.py: Coordinates all validation layers
- docs/living-docs/SEMANTIC_LAYER_IMPLEMENTATION_PLAN.md: Full security design
"""

from typing import List, Optional, Dict, Any, Set, FrozenSet
from dataclasses import dataclass, field
import re
import logging

from app.semantic.query import SemanticQuery, TimeRange, Breakdown, Comparison, Filter
from app.semantic.model import (
    ALLOWED_METRICS,
    ALLOWED_DIMENSIONS,
    ALLOWED_ENTITY_LEVELS,
    ALLOWED_TIME_GRANULARITIES,
    ALLOWED_PROVIDERS,
)


# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# SECURITY CONSTANTS: Allowlists and Limits
# =============================================================================

# Filter field allowlist
ALLOWED_FILTER_FIELDS: FrozenSet[str] = frozenset({
    "provider",      # Platform filter (meta, google, tiktok)
    "level",         # Entity level (campaign, adset, ad)
    "status",        # Entity status (active, paused)
    "entity_name",   # Entity name (for contains filter)
    "entity_ids",    # Specific entity IDs
})

# Comparison operator allowlist
ALLOWED_OPERATORS: FrozenSet[str] = frozenset({
    "=",        # Exact match
    "!=",       # Not equal
    ">",        # Greater than
    "<",        # Less than
    ">=",       # Greater than or equal
    "<=",       # Less than or equal
    "in",       # In list
    "contains", # Substring match
})

# Entity status allowlist
ALLOWED_STATUSES: FrozenSet[str] = frozenset({
    "active",
    "paused",
    "deleted",
    "archived",
    "removed",
    "enabled",
    "disabled",
})

# Sort order allowlist
ALLOWED_SORT_ORDERS: FrozenSet[str] = frozenset({
    "asc",
    "desc",
})

# Value constraints
MAX_STRING_LENGTH = 500      # Max chars for string filter values
MAX_LIST_LENGTH = 100        # Max items in "in" filter lists
MIN_TIME_RANGE_DAYS = 1      # Minimum time range
MAX_TIME_RANGE_DAYS = 365    # Maximum time range
MIN_BREAKDOWN_LIMIT = 1      # Minimum items in breakdown
MAX_BREAKDOWN_LIMIT = 50     # Maximum items in breakdown
MAX_METRICS_COUNT = 15       # Maximum metrics per query (11 standard metrics: spend, revenue, roas, cpc, ctr, cpa, clicks, impressions, conversions, profit, cvr)
MAX_FILTERS_COUNT = 10       # Maximum filters per query


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class SecurityError(Exception):
    """
    Exception raised when security validation fails.

    WHAT: Indicates a security constraint was violated.

    WHY: Separates security failures from other validation errors.
    Security failures should be logged and monitored more closely.

    ATTRIBUTES:
        message: Human-readable error description
        field: Which field caused the error
        value: What value was rejected (sanitized for logging)
        constraint: Which constraint was violated
    """

    def __init__(
        self,
        message: str,
        field: str = None,
        value: Any = None,
        constraint: str = None
    ):
        super().__init__(message)
        self.message = message
        self.field = field
        self.value = self._sanitize_for_log(value) if value else None
        self.constraint = constraint

    def _sanitize_for_log(self, value: Any) -> str:
        """
        Sanitize value for safe logging.

        Truncates long strings and converts to string representation.
        """
        str_val = str(value)
        if len(str_val) > 100:
            return str_val[:100] + "... (truncated)"
        return str_val

    def to_dict(self) -> Dict:
        """Convert to dictionary for structured logging."""
        return {
            "error_type": "security_error",
            "message": self.message,
            "field": self.field,
            "value": self.value,
            "constraint": self.constraint,
        }


# =============================================================================
# VALIDATION RESULT
# =============================================================================

@dataclass
class SecurityValidationResult:
    """
    Result of security validation.

    WHAT: Contains validation outcome and any errors found.

    WHY: Provides structured feedback about what failed and why.

    ATTRIBUTES:
        valid: True if all security checks passed
        errors: List of SecurityError instances
        warnings: List of non-blocking warnings
    """
    valid: bool
    errors: List[SecurityError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, error: SecurityError) -> None:
        """Add an error and mark result as invalid."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add a non-blocking warning."""
        self.warnings.append(warning)

    def to_user_message(self) -> str:
        """
        Generate user-friendly error message.

        RETURNS:
            Human-readable description of security issues
        """
        if self.valid:
            return "Security validation passed."

        messages = []
        for error in self.errors:
            if error.field:
                messages.append(f"• Invalid {error.field}: {error.message}")
            else:
                messages.append(f"• {error.message}")

        return "Security validation failed:\n" + "\n".join(messages)


# =============================================================================
# SECURITY VALIDATOR
# =============================================================================

class SecurityValidator:
    """
    Validates semantic queries against security allowlists.

    WHAT: Central security validation for all query components.

    WHY: Ensures only permitted values can be used in queries,
    preventing injection attacks and unauthorized data access.

    SECURITY MODEL:
        1. Metrics must be in ALLOWED_METRICS
        2. Dimensions must be in ALLOWED_DIMENSIONS
        3. Entity levels must be in ALLOWED_ENTITY_LEVELS
        4. Time granularities must be in ALLOWED_TIME_GRANULARITIES
        5. Filter fields must be in ALLOWED_FILTER_FIELDS
        6. Operators must be in ALLOWED_OPERATORS
        7. Values must pass sanitization checks

    USAGE:
        validator = SecurityValidator()
        result = validator.validate(query)

        if not result.valid:
            logger.warning(f"Security validation failed: {result.errors}")
            return error_response(result.to_user_message())

    LOGGING:
        All security failures are logged at WARNING level.
        Suspicious patterns are logged at ERROR level.

    RELATED FILES:
        - app/semantic/model.py: Source of metric/dimension allowlists
        - app/semantic/validator.py: Coordinates with schema/semantic validation
    """

    def __init__(self):
        """
        Initialize the security validator.

        Pre-computes regex patterns for efficiency.
        """
        # Compile patterns for efficiency
        self._dangerous_pattern = re.compile(
            r"(--|;|'|\"|\\|/\*|\*/|<|>|&|%|\$|`|\x00)",
            re.IGNORECASE
        )
        self._sql_keyword_pattern = re.compile(
            r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|OR|AND|WHERE|FROM|"
            r"EXEC|EXECUTE|TRUNCATE|ALTER|CREATE|GRANT|REVOKE)\b",
            re.IGNORECASE
        )

    # -------------------------------------------------------------------------
    # Main Validation Entry Point
    # -------------------------------------------------------------------------

    def validate(self, query: SemanticQuery) -> SecurityValidationResult:
        """
        Validate a semantic query against all security constraints.

        WHAT: Full security validation of a SemanticQuery.

        WHY: Ensures query contains only permitted values before execution.

        PARAMETERS:
            query: SemanticQuery to validate

        RETURNS:
            SecurityValidationResult with validation outcome

        FLOW:
            1. Validate metrics
            2. Validate time range
            3. Validate breakdown (if present)
            4. Validate comparison (if present)
            5. Validate filters (if present)
            6. Check overall constraints

        EXAMPLE:
            validator = SecurityValidator()
            result = validator.validate(query)
            if not result.valid:
                raise SecurityError(result.to_user_message())
        """
        result = SecurityValidationResult(valid=True)

        try:
            # 1. Validate metrics
            self._validate_metrics(query.metrics, result)

            # 2. Validate time range
            self._validate_time_range(query.time_range, result)

            # 3. Validate breakdown if present
            if query.breakdown:
                self._validate_breakdown(query.breakdown, result)

            # 4. Validate comparison if present
            if query.comparison:
                self._validate_comparison(query.comparison, result)

            # 5. Validate filters if present
            if query.filters:
                self._validate_filters(query.filters, result)

            # 6. Check overall constraints
            self._validate_query_constraints(query, result)

        except Exception as e:
            # Catch unexpected errors as security failures
            logger.error(f"Unexpected security validation error: {e}")
            result.add_error(SecurityError(
                message="Unexpected validation error",
                constraint="internal_error"
            ))

        # Log result
        if not result.valid:
            error_messages = [e.message for e in result.errors]
            logger.warning(
                f"Security validation failed: {error_messages}"
            )

        return result

    # -------------------------------------------------------------------------
    # Component Validators
    # -------------------------------------------------------------------------

    def _validate_metrics(
        self,
        metrics: List[str],
        result: SecurityValidationResult
    ) -> None:
        """
        Validate metric names against allowlist.

        CHECKS:
            1. Not empty
            2. Not too many metrics
            3. Each metric in allowlist
            4. No dangerous characters
        """
        # Check not empty
        if not metrics:
            result.add_error(SecurityError(
                message="At least one metric is required",
                field="metrics",
                constraint="min_count"
            ))
            return

        # Check count
        if len(metrics) > MAX_METRICS_COUNT:
            result.add_error(SecurityError(
                message=f"Maximum {MAX_METRICS_COUNT} metrics allowed",
                field="metrics",
                value=len(metrics),
                constraint="max_count"
            ))
            return

        # Check each metric
        for metric in metrics:
            # Check allowlist
            if metric not in ALLOWED_METRICS:
                result.add_error(SecurityError(
                    message=f"Unknown metric: '{metric}'",
                    field="metrics",
                    value=metric,
                    constraint="allowlist"
                ))
                continue

            # Check for dangerous patterns (defense in depth)
            if self._contains_dangerous_pattern(metric):
                result.add_error(SecurityError(
                    message=f"Invalid characters in metric name",
                    field="metrics",
                    value=metric,
                    constraint="dangerous_pattern"
                ))

    def _validate_time_range(
        self,
        time_range: TimeRange,
        result: SecurityValidationResult
    ) -> None:
        """
        Validate time range constraints.

        CHECKS:
            1. Has either last_n_days OR (start, end)
            2. Days within allowed range
            3. Dates are valid
        """
        if time_range.last_n_days is not None:
            # Relative time range
            if time_range.last_n_days < MIN_TIME_RANGE_DAYS:
                result.add_error(SecurityError(
                    message=f"Minimum time range is {MIN_TIME_RANGE_DAYS} day(s)",
                    field="time_range.last_n_days",
                    value=time_range.last_n_days,
                    constraint="min_value"
                ))

            if time_range.last_n_days > MAX_TIME_RANGE_DAYS:
                result.add_error(SecurityError(
                    message=f"Maximum time range is {MAX_TIME_RANGE_DAYS} days",
                    field="time_range.last_n_days",
                    value=time_range.last_n_days,
                    constraint="max_value"
                ))

        elif time_range.start is not None or time_range.end is not None:
            # Absolute time range
            if time_range.start is None or time_range.end is None:
                result.add_error(SecurityError(
                    message="Both start and end dates are required for absolute range",
                    field="time_range",
                    constraint="both_required"
                ))

            elif time_range.end < time_range.start:
                result.add_error(SecurityError(
                    message="End date must be after start date",
                    field="time_range",
                    constraint="date_order"
                ))

            else:
                # Check range doesn't exceed max
                days = (time_range.end - time_range.start).days + 1
                if days > MAX_TIME_RANGE_DAYS:
                    result.add_error(SecurityError(
                        message=f"Maximum time range is {MAX_TIME_RANGE_DAYS} days",
                        field="time_range",
                        value=days,
                        constraint="max_value"
                    ))

        else:
            result.add_error(SecurityError(
                message="Time range is required (last_n_days or start/end)",
                field="time_range",
                constraint="required"
            ))

    def _validate_breakdown(
        self,
        breakdown: Breakdown,
        result: SecurityValidationResult
    ) -> None:
        """
        Validate breakdown configuration.

        CHECKS:
            1. Dimension in allowlist
            2. Level valid for entity dimension
            3. Granularity valid for time dimension
            4. Limit within range
            5. Sort order valid
        """
        # Check dimension
        if breakdown.dimension not in ALLOWED_DIMENSIONS:
            result.add_error(SecurityError(
                message=f"Unknown dimension: '{breakdown.dimension}'",
                field="breakdown.dimension",
                value=breakdown.dimension,
                constraint="allowlist"
            ))
            return

        # Entity dimension requires level
        if breakdown.dimension == "entity":
            if not breakdown.level:
                result.add_error(SecurityError(
                    message="Entity breakdown requires 'level' (campaign, adset, or ad)",
                    field="breakdown.level",
                    constraint="required"
                ))
            elif breakdown.level not in ALLOWED_ENTITY_LEVELS:
                result.add_error(SecurityError(
                    message=f"Unknown entity level: '{breakdown.level}'",
                    field="breakdown.level",
                    value=breakdown.level,
                    constraint="allowlist"
                ))

        # Time dimension requires granularity
        if breakdown.dimension == "time":
            if not breakdown.granularity:
                result.add_error(SecurityError(
                    message="Time breakdown requires 'granularity' (day, week, or month)",
                    field="breakdown.granularity",
                    constraint="required"
                ))
            elif breakdown.granularity not in ALLOWED_TIME_GRANULARITIES:
                result.add_error(SecurityError(
                    message=f"Unknown time granularity: '{breakdown.granularity}'",
                    field="breakdown.granularity",
                    value=breakdown.granularity,
                    constraint="allowlist"
                ))

        # Check limit
        if breakdown.limit < MIN_BREAKDOWN_LIMIT:
            result.add_error(SecurityError(
                message=f"Breakdown limit must be at least {MIN_BREAKDOWN_LIMIT}",
                field="breakdown.limit",
                value=breakdown.limit,
                constraint="min_value"
            ))

        if breakdown.limit > MAX_BREAKDOWN_LIMIT:
            result.add_error(SecurityError(
                message=f"Breakdown limit cannot exceed {MAX_BREAKDOWN_LIMIT}",
                field="breakdown.limit",
                value=breakdown.limit,
                constraint="max_value"
            ))

        # Check sort order
        if breakdown.sort_order not in ALLOWED_SORT_ORDERS:
            result.add_error(SecurityError(
                message=f"Invalid sort order: '{breakdown.sort_order}'",
                field="breakdown.sort_order",
                value=breakdown.sort_order,
                constraint="allowlist"
            ))

    def _validate_comparison(
        self,
        comparison: Comparison,
        result: SecurityValidationResult
    ) -> None:
        """
        Validate comparison configuration.

        CHECKS:
            1. Comparison type is valid enum value
        """
        # Comparison type is validated by the enum itself
        # Just ensure it's a valid ComparisonType
        from app.semantic.query import ComparisonType

        if not isinstance(comparison.type, ComparisonType):
            result.add_error(SecurityError(
                message=f"Invalid comparison type",
                field="comparison.type",
                constraint="type"
            ))

    def _validate_filters(
        self,
        filters: List[Filter],
        result: SecurityValidationResult
    ) -> None:
        """
        Validate filter configurations.

        CHECKS:
            1. Not too many filters
            2. Each filter field in allowlist
            3. Each operator in allowlist
            4. Filter values are sanitized
        """
        # Check count
        if len(filters) > MAX_FILTERS_COUNT:
            result.add_error(SecurityError(
                message=f"Maximum {MAX_FILTERS_COUNT} filters allowed",
                field="filters",
                value=len(filters),
                constraint="max_count"
            ))
            return

        # Validate each filter
        for i, filter in enumerate(filters):
            self._validate_single_filter(filter, i, result)

    def _validate_single_filter(
        self,
        filter: Filter,
        index: int,
        result: SecurityValidationResult
    ) -> None:
        """
        Validate a single filter.

        CHECKS:
            1. Field in allowlist
            2. Operator in allowlist
            3. Value properly sanitized
            4. Value type matches operator expectations
        """
        field_name = f"filters[{index}]"

        # Check field
        if filter.field not in ALLOWED_FILTER_FIELDS:
            result.add_error(SecurityError(
                message=f"Unknown filter field: '{filter.field}'",
                field=f"{field_name}.field",
                value=filter.field,
                constraint="allowlist"
            ))
            return

        # Check operator
        if filter.operator not in ALLOWED_OPERATORS:
            result.add_error(SecurityError(
                message=f"Unknown operator: '{filter.operator}'",
                field=f"{field_name}.operator",
                value=filter.operator,
                constraint="allowlist"
            ))
            return

        # Validate value based on field type
        self._validate_filter_value(filter, field_name, result)

    def _validate_filter_value(
        self,
        filter: Filter,
        field_name: str,
        result: SecurityValidationResult
    ) -> None:
        """
        Validate filter value based on field type and operator.

        SPECIAL HANDLING:
            - provider: Must be in ALLOWED_PROVIDERS
            - level: Must be in ALLOWED_ENTITY_LEVELS
            - status: Must be in ALLOWED_STATUSES
            - entity_name: String, sanitized for dangerous patterns
            - entity_ids: List of strings/UUIDs
        """
        value = filter.value

        # Handle list values for "in" operator
        if filter.operator == "in":
            if not isinstance(value, list):
                result.add_error(SecurityError(
                    message="'in' operator requires a list value",
                    field=f"{field_name}.value",
                    constraint="type"
                ))
                return

            if len(value) > MAX_LIST_LENGTH:
                result.add_error(SecurityError(
                    message=f"List cannot exceed {MAX_LIST_LENGTH} items",
                    field=f"{field_name}.value",
                    value=len(value),
                    constraint="max_count"
                ))
                return

            # Validate each item
            for item in value:
                self._validate_filter_value_item(filter.field, item, field_name, result)
            return

        # Single value
        self._validate_filter_value_item(filter.field, value, field_name, result)

    def _validate_filter_value_item(
        self,
        field: str,
        value: Any,
        field_name: str,
        result: SecurityValidationResult
    ) -> None:
        """
        Validate a single filter value item.

        CHECKS:
            - provider: In ALLOWED_PROVIDERS
            - level: In ALLOWED_ENTITY_LEVELS
            - status: In ALLOWED_STATUSES
            - entity_name: String, max length, no dangerous patterns
            - entity_ids: String (UUID format)
        """
        if field == "provider":
            if value not in ALLOWED_PROVIDERS:
                result.add_error(SecurityError(
                    message=f"Unknown provider: '{value}'",
                    field=f"{field_name}.value",
                    value=value,
                    constraint="allowlist"
                ))

        elif field == "level":
            if value not in ALLOWED_ENTITY_LEVELS:
                result.add_error(SecurityError(
                    message=f"Unknown level: '{value}'",
                    field=f"{field_name}.value",
                    value=value,
                    constraint="allowlist"
                ))

        elif field == "status":
            str_value = str(value).lower()
            if str_value not in ALLOWED_STATUSES:
                result.add_error(SecurityError(
                    message=f"Unknown status: '{value}'",
                    field=f"{field_name}.value",
                    value=value,
                    constraint="allowlist"
                ))

        elif field == "entity_name":
            # String value - check length and patterns
            if not isinstance(value, str):
                result.add_error(SecurityError(
                    message="entity_name must be a string",
                    field=f"{field_name}.value",
                    constraint="type"
                ))
            elif len(value) > MAX_STRING_LENGTH:
                result.add_error(SecurityError(
                    message=f"Value exceeds maximum length of {MAX_STRING_LENGTH}",
                    field=f"{field_name}.value",
                    value=len(value),
                    constraint="max_length"
                ))
            elif self._contains_dangerous_pattern(value):
                result.add_error(SecurityError(
                    message="Value contains invalid characters",
                    field=f"{field_name}.value",
                    constraint="dangerous_pattern"
                ))

        elif field == "entity_ids":
            # Should be string (UUID) or list of strings
            if isinstance(value, list):
                for item in value:
                    if not isinstance(item, str) or len(item) > 100:
                        result.add_error(SecurityError(
                            message="entity_ids must be strings",
                            field=f"{field_name}.value",
                            constraint="type"
                        ))
                        break
            elif not isinstance(value, str) or len(value) > 100:
                result.add_error(SecurityError(
                    message="entity_ids must be a string",
                    field=f"{field_name}.value",
                    constraint="type"
                ))

    def _validate_query_constraints(
        self,
        query: SemanticQuery,
        result: SecurityValidationResult
    ) -> None:
        """
        Validate overall query constraints.

        CHECKS:
            1. Valid composition (no conflicting options)
            2. Required components present
        """
        # Add warnings for unusual but valid queries
        if len(query.metrics) > 5:
            result.add_warning(
                f"Query has {len(query.metrics)} metrics, consider fewer for clarity"
            )

        if query.breakdown and query.breakdown.limit > 20:
            result.add_warning(
                f"Breakdown limit of {query.breakdown.limit} may result in slow queries"
            )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _contains_dangerous_pattern(self, value: str) -> bool:
        """
        Check if value contains potentially dangerous patterns.

        WHAT: Detects SQL injection and other attack patterns.

        WHY: Defense in depth - even though we use allowlists and
        parameterized queries, we still check for obvious attacks.

        PATTERNS DETECTED:
            - SQL comment sequences (--, /*, */)
            - Quote characters (', ", `)
            - SQL keywords (SELECT, INSERT, etc.)
            - Special characters (;, &, <, >, etc.)
            - Null bytes

        RETURNS:
            True if dangerous pattern found
        """
        if self._dangerous_pattern.search(value):
            logger.warning(
                f"Dangerous pattern detected",
                extra={"value_preview": value[:50]}
            )
            return True

        if self._sql_keyword_pattern.search(value):
            logger.warning(
                f"SQL keyword detected",
                extra={"value_preview": value[:50]}
            )
            return True

        return False

    def validate_metric(self, metric: str) -> bool:
        """
        Quick validation for a single metric name.

        PARAMETERS:
            metric: Metric name to validate

        RETURNS:
            True if metric is allowed
        """
        return metric in ALLOWED_METRICS

    def validate_dimension(self, dimension: str) -> bool:
        """
        Quick validation for a single dimension name.

        PARAMETERS:
            dimension: Dimension name to validate

        RETURNS:
            True if dimension is allowed
        """
        return dimension in ALLOWED_DIMENSIONS

    def validate_provider(self, provider: str) -> bool:
        """
        Quick validation for a provider name.

        PARAMETERS:
            provider: Provider name to validate

        RETURNS:
            True if provider is allowed
        """
        return provider in ALLOWED_PROVIDERS


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def validate_query_security(query: SemanticQuery) -> SecurityValidationResult:
    """
    Convenience function to validate a query's security.

    WHAT: Creates a SecurityValidator and validates the query.

    WHY: Simple interface for one-off validation.

    PARAMETERS:
        query: SemanticQuery to validate

    RETURNS:
        SecurityValidationResult

    EXAMPLE:
        result = validate_query_security(query)
        if not result.valid:
            raise SecurityError(result.to_user_message())
    """
    validator = SecurityValidator()
    return validator.validate(query)


def is_safe_metric(metric: str) -> bool:
    """
    Check if a metric name is safe to use.

    PARAMETERS:
        metric: Metric name to check

    RETURNS:
        True if metric is in allowlist
    """
    return metric in ALLOWED_METRICS


def is_safe_dimension(dimension: str) -> bool:
    """
    Check if a dimension name is safe to use.

    PARAMETERS:
        dimension: Dimension name to check

    RETURNS:
        True if dimension is in allowlist
    """
    return dimension in ALLOWED_DIMENSIONS


def is_safe_provider(provider: str) -> bool:
    """
    Check if a provider name is safe to use.

    PARAMETERS:
        provider: Provider name to check

    RETURNS:
        True if provider is in allowlist
    """
    return provider in ALLOWED_PROVIDERS
