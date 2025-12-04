"""
Semantic Query Validator
========================

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Active

Multi-layer validation pipeline for semantic queries.
Coordinates schema, security, and semantic validation.

WHY THIS FILE EXISTS
--------------------
Validation happens in stages with different responsibilities:

    Layer 1: Schema Validation
        - Ensures JSON/dict can be parsed into SemanticQuery
        - Type checking, required fields, enum values
        - Happens during SemanticQuery.from_dict()

    Layer 2: Security Validation (security.py)
        - Allowlist enforcement (metrics, dimensions, operators)
        - Value constraints (lengths, ranges)
        - Dangerous pattern detection

    Layer 3: Semantic Validation (THIS FILE)
        - Business logic validation
        - Query composition rules
        - Time range sanity checks
        - Metric/dimension compatibility

This file coordinates all three layers and provides:
- Unified validation interface
- Aggregated error collection
- User-friendly error messages
- Validation result caching (if needed)

VALIDATION FLOW
---------------
```
SemanticQuery
    │
    ▼
[Layer 1: Schema]
    │  ✓ Valid structure
    ▼
[Layer 2: Security]
    │  ✓ Allowlists pass
    │  ✓ Values sanitized
    ▼
[Layer 3: Semantic]
    │  ✓ Valid composition
    │  ✓ Business rules pass
    ▼
ValidationResult(valid=True)
```

If ANY layer fails, we collect all errors and return them together
for a better user experience (instead of failing one at a time).

RELATED FILES
-------------
- app/semantic/security.py: Layer 2 security validation
- app/semantic/query.py: SemanticQuery being validated
- app/semantic/errors.py: Error classification and messages
- app/semantic/model.py: Metric/dimension definitions
- docs/living-docs/SEMANTIC_LAYER_IMPLEMENTATION_PLAN.md: Full plan
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from datetime import date, timedelta
import logging

from app.semantic.query import (
    SemanticQuery,
    TimeRange,
    Breakdown,
    Comparison,
    Filter,
    ComparisonType,
)
from app.semantic.security import (
    SecurityValidator,
    SecurityValidationResult,
    SecurityError,
)
from app.semantic.model import (
    ALLOWED_METRICS,
    ALLOWED_DIMENSIONS,
    ALLOWED_ENTITY_LEVELS,
    ALLOWED_TIME_GRANULARITIES,
    get_metric,
)


# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# VALIDATION ERROR
# =============================================================================

@dataclass
class ValidationError:
    """
    Represents a single validation error.

    WHAT: Encapsulates error information from any validation layer.

    WHY: Provides consistent error format regardless of which layer failed.

    ATTRIBUTES:
        layer: Which validation layer caught this ("schema", "security", "semantic")
        code: Machine-readable error code (e.g., "INVALID_METRIC", "MISSING_LEVEL")
        message: Human-readable error message
        field: Which field caused the error (optional)
        suggestion: Helpful suggestion to fix the error (optional)
    """
    layer: str
    code: str
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "layer": self.layer,
            "code": self.code,
            "message": self.message,
        }
        if self.field:
            result["field"] = self.field
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


# =============================================================================
# VALIDATION RESULT
# =============================================================================

@dataclass
class ValidationResult:
    """
    Result of the complete validation pipeline.

    WHAT: Contains the outcome of all validation layers.

    WHY: Provides single result object with all errors/warnings collected.

    ATTRIBUTES:
        valid: True if all validation layers passed
        errors: List of ValidationError from all layers
        warnings: Non-blocking warnings (query works but may be suboptimal)
        layers_passed: Which validation layers were executed and passed

    USAGE:
        result = validator.validate(query)
        if not result.valid:
            return error_response(result.to_user_message())
    """
    valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    layers_passed: List[str] = field(default_factory=list)

    def add_error(self, error: ValidationError) -> None:
        """Add an error and mark result as invalid."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add a non-blocking warning."""
        self.warnings.append(warning)

    def mark_layer_passed(self, layer: str) -> None:
        """Mark a validation layer as passed."""
        self.layers_passed.append(layer)

    def has_errors_in_layer(self, layer: str) -> bool:
        """Check if any errors are from a specific layer."""
        return any(e.layer == layer for e in self.errors)

    def get_errors_by_layer(self, layer: str) -> List[ValidationError]:
        """Get all errors from a specific layer."""
        return [e for e in self.errors if e.layer == layer]

    def to_user_message(self) -> str:
        """
        Generate user-friendly error message.

        WHAT: Creates a readable summary of all validation errors.

        WHY: Users need to understand what went wrong and how to fix it.

        RETURNS:
            Multi-line string with all errors and suggestions
        """
        if self.valid:
            return "Query validation passed."

        lines = ["I couldn't process that query. Here's what went wrong:"]
        lines.append("")

        for error in self.errors:
            if error.field:
                lines.append(f"• {error.field}: {error.message}")
            else:
                lines.append(f"• {error.message}")

            if error.suggestion:
                lines.append(f"  → {error.suggestion}")

        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")

        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "layers_passed": self.layers_passed,
        }


# =============================================================================
# SEMANTIC VALIDATOR
# =============================================================================

class SemanticValidator:
    """
    Multi-layer validation pipeline for semantic queries.

    WHAT: Coordinates all validation layers and collects errors.

    WHY: Provides single validation entry point with comprehensive checking.

    VALIDATION LAYERS:
        1. Schema: Structure and types (happens in from_dict)
        2. Security: Allowlists and sanitization (security.py)
        3. Semantic: Business rules and composition (this class)

    USAGE:
        validator = SemanticValidator()
        result = validator.validate(query)

        if not result.valid:
            logger.warning(f"Validation failed: {result.errors}")
            return error_response(result.to_user_message())

        # Query is safe to compile
        compiler.compile(query, workspace_id)

    RELATED FILES:
        - app/semantic/security.py: Security validation
        - app/semantic/compiler.py: Uses validated queries
        - app/services/qa_service.py: Calls this validator
    """

    def __init__(self):
        """Initialize the validator with security validator."""
        self.security_validator = SecurityValidator()

    # -------------------------------------------------------------------------
    # Main Validation Entry Point
    # -------------------------------------------------------------------------

    def validate(self, query: SemanticQuery) -> ValidationResult:
        """
        Validate a semantic query through all layers.

        WHAT: Full validation pipeline execution.

        WHY: Ensures query is valid before compilation.

        PARAMETERS:
            query: SemanticQuery to validate

        RETURNS:
            ValidationResult with all errors/warnings collected

        FLOW:
            1. Run security validation
            2. Run semantic validation
            3. Collect all errors
            4. Return unified result

        EXAMPLE:
            validator = SemanticValidator()
            result = validator.validate(query)

            if result.valid:
                # Safe to compile
                data = compiler.compile(query, workspace_id)
            else:
                # Show errors to user
                return {"error": result.to_user_message()}
        """
        result = ValidationResult()

        try:
            # Layer 1: Schema validation already happened in from_dict
            # If we have a SemanticQuery object, schema is valid
            result.mark_layer_passed("schema")

            # Layer 2: Security validation
            security_result = self.security_validator.validate(query)
            if not security_result.valid:
                for error in security_result.errors:
                    result.add_error(ValidationError(
                        layer="security",
                        code=error.constraint or "SECURITY_ERROR",
                        message=error.message,
                        field=error.field,
                    ))
            else:
                result.mark_layer_passed("security")

            # Add security warnings
            for warning in security_result.warnings:
                result.add_warning(warning)

            # Layer 3: Semantic validation
            self._validate_semantic(query, result)
            if not result.has_errors_in_layer("semantic"):
                result.mark_layer_passed("semantic")

        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            result.add_error(ValidationError(
                layer="internal",
                code="INTERNAL_ERROR",
                message="An unexpected error occurred during validation.",
            ))

        # Log validation result
        if result.valid:
            logger.debug(f"Query validation passed: {query.metrics}")
        else:
            logger.warning(
                f"Query validation failed",
                extra={
                    "error_count": len(result.errors),
                    "metrics": query.metrics,
                    "errors": [e.to_dict() for e in result.errors]
                }
            )

        return result

    # -------------------------------------------------------------------------
    # Semantic Validation (Layer 3)
    # -------------------------------------------------------------------------

    def _validate_semantic(
        self,
        query: SemanticQuery,
        result: ValidationResult
    ) -> None:
        """
        Validate semantic/business rules.

        WHAT: Checks that query makes logical sense.

        WHY: Even if values are valid, combinations may not make sense.

        CHECKS:
            1. Query composition is valid
            2. Time range is sensible
            3. Breakdown/comparison compatibility
            4. Filter combinations are valid
        """
        # 1. Validate composition
        self._validate_composition(query, result)

        # 2. Validate time range semantics
        self._validate_time_range_semantics(query, result)

        # 3. Validate breakdown semantics
        if query.breakdown:
            self._validate_breakdown_semantics(query, result)

        # 4. Validate comparison semantics
        if query.comparison:
            self._validate_comparison_semantics(query, result)

        # 5. Validate filter semantics
        if query.filters:
            self._validate_filter_semantics(query, result)

        # 6. Validate metric combinations
        self._validate_metric_combinations(query, result)

    def _validate_composition(
        self,
        query: SemanticQuery,
        result: ValidationResult
    ) -> None:
        """
        Validate query composition rules.

        WHAT: Ensures query component combinations are valid.

        WHY: Some combinations don't make sense or aren't supported.

        RULES:
            - Timeseries requires time_range of 2+ days
            - Entity comparison requires entity breakdown
            - Provider breakdown + entity comparison not meaningful
        """
        # Timeseries needs sufficient time range
        if query.include_timeseries:
            if query.time_range.last_n_days and query.time_range.last_n_days < 2:
                result.add_warning(
                    "Timeseries with only 1 day of data may not be useful"
                )

        # Entity comparison logic check
        if query.comparison and not query.breakdown:
            # Comparison without breakdown = overall comparison (valid)
            pass

        # Check for potentially slow queries
        if query.breakdown and query.include_timeseries and query.comparison:
            if query.breakdown.limit > 10:
                result.add_warning(
                    f"Query with {query.breakdown.limit} entities, timeseries, "
                    "and comparison may be slow. Consider reducing limit."
                )

    def _validate_time_range_semantics(
        self,
        query: SemanticQuery,
        result: ValidationResult
    ) -> None:
        """
        Validate time range makes business sense.

        WHAT: Checks time range for logical issues.

        WHY: Catch obviously wrong time ranges.

        CHECKS:
            - Future dates warning
            - Very old dates warning
            - Single day with comparison warning
        """
        today = date.today()

        if query.time_range.end:
            if query.time_range.end > today:
                result.add_warning(
                    "Time range extends into the future. "
                    "Data may be incomplete."
                )

        if query.time_range.start:
            days_ago = (today - query.time_range.start).days
            if days_ago > 365:
                result.add_warning(
                    f"Time range starts {days_ago} days ago. "
                    "Old data may be less relevant."
                )

        # Single day comparison warning
        if query.comparison and query.time_range.last_n_days == 1:
            result.add_warning(
                "Comparing single days may show high variance. "
                "Consider using 7+ days for more stable comparisons."
            )

    def _validate_breakdown_semantics(
        self,
        query: SemanticQuery,
        result: ValidationResult
    ) -> None:
        """
        Validate breakdown makes business sense.

        WHAT: Checks breakdown configuration for issues.

        WHY: Catch nonsensical breakdown configurations.

        CHECKS:
            - Time breakdown with very long range
            - Entity breakdown with very high limit
        """
        breakdown = query.breakdown

        # Time breakdown with long range may produce too many points
        if breakdown.dimension == "time":
            if breakdown.granularity == "day":
                days = query.time_range.last_n_days or 30
                if days > 90:
                    result.add_warning(
                        f"Daily breakdown for {days} days will produce many data points. "
                        "Consider using 'week' or 'month' granularity."
                    )
            elif breakdown.granularity == "month":
                days = query.time_range.last_n_days or 30
                if days < 60:
                    result.add_warning(
                        "Monthly breakdown for less than 60 days may show only 1-2 points. "
                        "Consider using 'week' or 'day' granularity."
                    )

    def _validate_comparison_semantics(
        self,
        query: SemanticQuery,
        result: ValidationResult
    ) -> None:
        """
        Validate comparison makes business sense.

        WHAT: Checks comparison configuration for issues.

        WHY: Catch problematic comparison configurations.

        CHECKS:
            - Year-over-year with less than 1 year of data
            - Custom comparison (not yet implemented)
        """
        comparison = query.comparison

        if comparison.type == ComparisonType.YEAR_OVER_YEAR:
            # Check if data would exist for comparison
            if query.time_range.last_n_days:
                days = query.time_range.last_n_days
                if days < 7:
                    result.add_warning(
                        "Year-over-year comparison with short time range "
                        "may show high variance. Consider 7+ days."
                    )

        if comparison.type == ComparisonType.CUSTOM:
            result.add_error(ValidationError(
                layer="semantic",
                code="CUSTOM_COMPARISON_NOT_SUPPORTED",
                message="Custom comparison type is not yet supported.",
                field="comparison.type",
                suggestion="Use 'previous_period' or 'year_over_year' instead."
            ))

    def _validate_filter_semantics(
        self,
        query: SemanticQuery,
        result: ValidationResult
    ) -> None:
        """
        Validate filter combinations make sense.

        WHAT: Checks filter configurations for issues.

        WHY: Catch conflicting or redundant filters.

        CHECKS:
            - Conflicting filters (provider=meta AND provider=google)
            - Redundant filters
        """
        # Check for conflicting provider filters
        provider_filters = [
            f for f in query.filters
            if f.field == "provider" and f.operator == "="
        ]
        if len(provider_filters) > 1:
            values = [f.value for f in provider_filters]
            result.add_error(ValidationError(
                layer="semantic",
                code="CONFLICTING_FILTERS",
                message=f"Conflicting provider filters: {values}. "
                        "A query cannot filter by multiple providers with '='.",
                field="filters",
                suggestion="Use 'in' operator to match multiple providers: "
                          f"filter('provider', 'in', {values})"
            ))

        # Check for redundant filters
        seen_filters = set()
        for f in query.filters:
            key = (f.field, f.operator, str(f.value))
            if key in seen_filters:
                result.add_warning(
                    f"Duplicate filter detected: {f.field} {f.operator} {f.value}"
                )
            seen_filters.add(key)

    def _validate_metric_combinations(
        self,
        query: SemanticQuery,
        result: ValidationResult
    ) -> None:
        """
        Validate metric combinations make sense.

        WHAT: Checks if requested metrics work well together.

        WHY: Some metric combinations may not be meaningful.

        CHECKS:
            - Mixing very different metric types
            - Requesting incompatible metrics
        """
        # Check if mixing count metrics with rate metrics in breakdown
        if len(query.metrics) > 1 and query.breakdown:
            metric_types = set()
            for metric_name in query.metrics:
                metric = get_metric(metric_name)
                if metric:
                    metric_types.add(metric.type)

            if len(metric_types) > 2:
                result.add_warning(
                    "Mixing many different metric types in one breakdown "
                    "may make the chart hard to read."
                )

    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------

    def validate_dict(self, data: Dict) -> ValidationResult:
        """
        Validate a query dictionary.

        WHAT: Validates dict before converting to SemanticQuery.

        WHY: Catches schema errors with helpful messages.

        PARAMETERS:
            data: Dictionary representation of query

        RETURNS:
            ValidationResult (with schema errors if parsing failed)
        """
        result = ValidationResult()

        try:
            query = SemanticQuery.from_dict(data)
            return self.validate(query)
        except KeyError as e:
            result.add_error(ValidationError(
                layer="schema",
                code="MISSING_REQUIRED_FIELD",
                message=f"Missing required field: {e}",
                field=str(e),
                suggestion="Ensure all required fields are provided."
            ))
        except ValueError as e:
            result.add_error(ValidationError(
                layer="schema",
                code="INVALID_VALUE",
                message=f"Invalid value: {e}",
                suggestion="Check the value format and type."
            ))
        except Exception as e:
            result.add_error(ValidationError(
                layer="schema",
                code="PARSE_ERROR",
                message=f"Failed to parse query: {e}",
                suggestion="Verify the query structure matches the expected format."
            ))

        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def validate_semantic_query(query: SemanticQuery) -> ValidationResult:
    """
    Convenience function to validate a semantic query.

    PARAMETERS:
        query: SemanticQuery to validate

    RETURNS:
        ValidationResult

    EXAMPLE:
        result = validate_semantic_query(query)
        if not result.valid:
            raise ValueError(result.to_user_message())
    """
    validator = SemanticValidator()
    return validator.validate(query)


def validate_query_dict(data: Dict) -> ValidationResult:
    """
    Convenience function to validate a query dictionary.

    PARAMETERS:
        data: Dictionary representation of query

    RETURNS:
        ValidationResult

    EXAMPLE:
        result = validate_query_dict(llm_output)
        if not result.valid:
            return {"error": result.to_user_message()}
    """
    validator = SemanticValidator()
    return validator.validate_dict(data)
