"""
Query Error Handler and Classification
========================================

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Active

Error classification, user messaging, and error handling for semantic queries.

WHY THIS FILE EXISTS
--------------------
Error handling happens at multiple stages and from multiple sources:

    1. Schema Validation Errors
       - Invalid JSON structure
       - Missing required fields
       - Wrong data types
       - Invalid enum values

    2. Security Validation Errors
       - Unknown metrics/dimensions
       - Invalid operators
       - Dangerous patterns
       - Value constraints violated

    3. Semantic Validation Errors
       - Conflicting filters
       - Invalid composition
       - Business rule violations
       - Out-of-range parameters

    4. Compilation Errors
       - Database access failures
       - Missing data
       - Query execution timeouts
       - Resource constraints

This file provides:
- QueryError: Unified exception class
- QueryErrorHandler: Error classification and messaging
- Mapping between technical errors and user-friendly messages
- Suggestions for how to fix common errors

WHY IT MATTERS FOR USERS
------------------------
When something fails, users need to know:
1. WHAT went wrong (clear, non-technical)
2. WHY it happened (context)
3. HOW to fix it (actionable suggestion)

Example:
    ❌ Old: "INVALID_METRIC"
    ✅ New: "I don't know the metric 'roi'. Did you mean 'roas' (Return on Ad Spend)?"

RELATED FILES
-------------
- app/semantic/validator.py: Produces ValidationResult with errors
- app/semantic/security.py: Produces SecurityValidationResult with errors
- app/semantic/query.py: SemanticQuery being validated
- docs/living-docs/SEMANTIC_LAYER_IMPLEMENTATION_PLAN.md: Full plan
"""

from dataclasses import dataclass, field as dataclass_field
from typing import List, Optional, Dict, Any
from enum import Enum
import logging


# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# ERROR CLASSIFICATION ENUMS
# =============================================================================

class ErrorCategory(Enum):
    """
    Categories of errors for classification and handling.

    WHAT: Classifies errors into broader categories for better handling.

    WHY: Different categories need different responses (e.g., retry logic,
         logging level, user messaging).
    """
    SCHEMA = "schema"              # JSON structure, types, format
    SECURITY = "security"          # Validation, allowlists, injection
    SEMANTIC = "semantic"          # Business logic, composition
    RESOURCE = "resource"          # Database, memory, rate limits
    EXTERNAL = "external"          # Third-party API failures
    UNKNOWN = "unknown"            # Unexpected errors


class ErrorSeverity(Enum):
    """
    Severity levels for errors.

    WHAT: Indicates how serious the error is and who needs to know.

    WHY: Helps with logging, monitoring, and user communication.
    """
    INFO = "info"                  # Informational (success, expected state)
    WARNING = "warning"            # Warning (unexpected but recoverable)
    ERROR = "error"                # Error (operation failed, user needs action)
    CRITICAL = "critical"          # Critical (system damage possible)


class ErrorCode(Enum):
    """
    Standard error codes for common issues.

    WHAT: Machine-readable codes for error categorization and monitoring.

    WHY: Enables tracking, metrics, and automated handling.
    """
    # Schema errors
    MISSING_REQUIRED_FIELD = "ERR_001"
    INVALID_FIELD_TYPE = "ERR_002"
    INVALID_ENUM_VALUE = "ERR_003"
    MALFORMED_JSON = "ERR_004"

    # Security errors
    UNKNOWN_METRIC = "ERR_010"
    UNKNOWN_DIMENSION = "ERR_011"
    UNKNOWN_OPERATOR = "ERR_012"
    INVALID_PROVIDER = "ERR_013"
    DANGEROUS_PATTERN = "ERR_014"
    VALUE_TOO_LONG = "ERR_015"
    OUT_OF_RANGE = "ERR_016"

    # Semantic errors
    CONFLICTING_FILTERS = "ERR_020"
    INVALID_COMPOSITION = "ERR_021"
    CUSTOM_COMPARISON_NOT_SUPPORTED = "ERR_022"
    INCOMPATIBLE_METRICS = "ERR_023"

    # Resource errors
    QUERY_TIMEOUT = "ERR_030"
    DATABASE_ERROR = "ERR_031"
    RATE_LIMIT_EXCEEDED = "ERR_032"
    OUT_OF_MEMORY = "ERR_033"

    # External errors
    EXTERNAL_API_ERROR = "ERR_040"
    EXTERNAL_API_TIMEOUT = "ERR_041"

    # Unknown errors
    INTERNAL_ERROR = "ERR_999"


# =============================================================================
# QUERY ERROR EXCEPTION
# =============================================================================

@dataclass
class QueryError(Exception):
    """
    Exception class for query-related errors.

    WHAT: Encapsulates all error information for semantic query failures.

    WHY: Provides unified error handling with rich metadata.

    ATTRIBUTES:
        code: StandardErrorCode (machine-readable)
        message: User-friendly error message
        field_name: Which field caused the error (optional)
        suggestion: How to fix the error (optional)
        category: Error category for classification
        severity: How serious this error is
        details: Additional debug information
        original_exception: Original exception if wrapping (optional)

    USAGE:
        try:
            result = validator.validate(query)
            if not result.valid:
                raise QueryError(
                    code=ErrorCode.UNKNOWN_METRIC,
                    message="I don't know the metric 'roi'",
                    field_name="metrics",
                    suggestion="Did you mean 'roas' (Return on Ad Spend)?",
                    category=ErrorCategory.SECURITY,
                    severity=ErrorSeverity.ERROR,
                )
        except QueryError as e:
            logger.error(f"Query error: {e.message}", extra=e.to_dict())
            return {"error": e.user_message()}
    """
    code: ErrorCode
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    field_name: Optional[str] = None
    suggestion: Optional[str] = None
    details: Dict[str, Any] = dataclass_field(default_factory=dict)
    original_exception: Optional[Exception] = None

    def __str__(self) -> str:
        """String representation of the error."""
        if self.field_name:
            return f"[{self.code.value}] {self.field_name}: {self.message}"
        return f"[{self.code.value}] {self.message}"

    def user_message(self) -> str:
        """
        Generate user-friendly error message.

        WHAT: Creates a readable message for end users.

        WHY: Users shouldn't see technical error codes or implementation details.

        RETURNS:
            Friendly message with suggestion if available

        EXAMPLE:
            "I don't know the metric 'roi'. Did you mean 'roas' (Return on Ad Spend)?"
        """
        lines = []

        # Main message
        if self.field_name:
            lines.append(f"**{self.field_name}**: {self.message}")
        else:
            lines.append(self.message)

        # Add suggestion if available
        if self.suggestion:
            lines.append(f"\n💡 {self.suggestion}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for logging/JSON serialization.

        WHAT: Structured representation for logs and APIs.

        RETURNS:
            Dictionary with all error information
        """
        result = {
            "code": self.code.value,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
        }

        if self.field_name:
            result["field"] = self.field_name

        if self.suggestion:
            result["suggestion"] = self.suggestion

        if self.details:
            result["details"] = self.details

        return result


# =============================================================================
# ERROR HANDLER
# =============================================================================

class QueryErrorHandler:
    """
    Handles error classification, messaging, and suggestions.

    WHAT: Converts validation errors to user-friendly messages with suggestions.

    WHY: Users need clear, actionable error messages. Technical errors from
         validators are not directly user-friendly.

    USAGE:
        handler = QueryErrorHandler()

        # Create error from validation failure
        error = handler.create_error_from_validation(
            error_dict=validation_error.to_dict(),
            context={"query": query}
        )

        # Get user message
        user_msg = error.user_message()

        # Log error
        logger.error(str(error), extra=error.to_dict())

    EXAMPLES:

        1. Unknown Metric:
            Input:  {"code": "UNKNOWN_METRIC", "field": "metrics", "value": "roi"}
            Output: QueryError with message:
                    "I don't know the metric 'roi'. Did you mean 'roas'?"

        2. Dangerous Pattern:
            Input:  {"code": "SQL_INJECTION", "value": "'; DROP--"}
            Output: QueryError with message:
                    "That looks like it might contain SQL code. For safety, I can't process it."

        3. Invalid Composition:
            Input:  {"code": "CUSTOM_COMPARISON_NOT_SUPPORTED"}
            Output: QueryError with message:
                    "Custom comparisons aren't supported yet. Try 'previous_period' or 'year_over_year'."
    """

    # Predefined error mappings
    ERROR_MESSAGES = {
        # Schema errors
        "MISSING_REQUIRED_FIELD": {
            "message": "Missing required information",
            "suggestion": "Please provide all required fields",
        },
        "INVALID_FIELD_TYPE": {
            "message": "Invalid data type",
            "suggestion": "Check that the value matches the expected type",
        },
        "MALFORMED_JSON": {
            "message": "I couldn't parse that request",
            "suggestion": "Check the format of your query",
        },

        # Security errors
        "UNKNOWN_METRIC": {
            "message": "I don't know that metric",
            "suggestion_template": "Did you mean '{suggestion}'?",
        },
        "UNKNOWN_DIMENSION": {
            "message": "I don't know that dimension",
            "suggestion_template": "Valid options are: {suggestion}",
        },
        "UNKNOWN_OPERATOR": {
            "message": "I don't understand that operator",
            "suggestion_template": "Valid operators are: {suggestion}",
        },
        "INVALID_PROVIDER": {
            "message": "I don't recognize that platform",
            "suggestion_template": "Valid platforms are: {suggestion}",
        },
        "DANGEROUS_PATTERN": {
            "message": "That looks like it might contain SQL code",
            "suggestion": "For safety, I can't process it. Please rephrase your question",
        },
        "VALUE_TOO_LONG": {
            "message": "That value is too long",
            "suggestion": "Use a shorter value (max 500 characters)",
        },
        "OUT_OF_RANGE": {
            "message": "That value is outside the allowed range",
            "suggestion_template": "Valid range is: {suggestion}",
        },

        # Semantic errors
        "CONFLICTING_FILTERS": {
            "message": "You have conflicting filters",
            "suggestion": "A query can't have multiple exact filters on the same field",
        },
        "INVALID_COMPOSITION": {
            "message": "That combination of features isn't supported",
            "suggestion": "Try a simpler query",
        },
        "CUSTOM_COMPARISON_NOT_SUPPORTED": {
            "message": "Custom comparisons aren't supported yet",
            "suggestion": "Use 'previous_period' or 'year_over_year' instead",
        },
        "INCOMPATIBLE_METRICS": {
            "message": "Those metrics don't work well together",
            "suggestion": "Try querying one metric at a time, or ask them separately",
        },

        # Resource errors
        "QUERY_TIMEOUT": {
            "message": "That query is taking too long",
            "suggestion": "Try a shorter time period or fewer entities",
        },
        "DATABASE_ERROR": {
            "message": "I couldn't access the database",
            "suggestion": "Please try again in a moment",
        },
        "RATE_LIMIT_EXCEEDED": {
            "message": "Too many requests",
            "suggestion": "Please wait a moment before trying again",
        },

        # External errors
        "EXTERNAL_API_ERROR": {
            "message": "I couldn't reach the data source",
            "suggestion": "Please try again in a moment",
        },

        # Generic
        "INTERNAL_ERROR": {
            "message": "Something went wrong",
            "suggestion": "Please try again, or contact support if this keeps happening",
        },
    }

    # Metric suggestions for common typos
    METRIC_SUGGESTIONS = {
        "roi": "roas",  # Common mistake
        "cpi": "cpi",
        "cpp": "cpp",
        "roas": "roas",
        "aov": "aov",
        "arpv": "arpv",
    }

    def __init__(self):
        """Initialize error handler."""
        pass

    # -------------------------------------------------------------------------
    # Error Creation Methods
    # -------------------------------------------------------------------------

    def create_error_from_validation(
        self,
        error_dict: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> QueryError:
        """
        Create QueryError from validation error dictionary.

        WHAT: Converts validation errors to QueryError with suggestions.

        PARAMETERS:
            error_dict: Error dictionary from validator
            context: Additional context for error handling

        RETURNS:
            QueryError with user-friendly message
        """
        code_str = error_dict.get("code", "INTERNAL_ERROR")
        field_name = error_dict.get("field")
        message = error_dict.get("message", "Unknown error")
        layer = error_dict.get("layer", "unknown")

        # Determine category based on layer
        category_map = {
            "schema": ErrorCategory.SCHEMA,
            "security": ErrorCategory.SECURITY,
            "semantic": ErrorCategory.SEMANTIC,
            "internal": ErrorCategory.UNKNOWN,
        }
        category = category_map.get(layer, ErrorCategory.UNKNOWN)

        # Get template message
        template = self.ERROR_MESSAGES.get(code_str, {})
        user_message = template.get("message", message)

        # Generate suggestion
        suggestion = self._generate_suggestion(
            code_str,
            error_dict,
            context or {}
        )

        # Create and return error
        return QueryError(
            code=self._string_to_error_code(code_str),
            message=user_message,
            field_name=field_name,
            suggestion=suggestion,
            category=category,
            severity=self._get_severity(code_str),
            details={"original": error_dict},
        )

    def create_error(
        self,
        code: ErrorCode,
        message: str,
        field_name: Optional[str] = None,
        suggestion: Optional[str] = None,
        severity: Optional[ErrorSeverity] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> QueryError:
        """
        Create a QueryError with specified parameters.

        WHAT: Factory method for creating QueryError instances.

        PARAMETERS:
            code: ErrorCode enum value
            message: User-friendly message
            field_name: Field that caused the error (optional)
            suggestion: Suggestion to fix (optional)
            severity: How serious this is (optional, defaults based on code)
            details: Debug details (optional)

        RETURNS:
            QueryError instance
        """
        if severity is None:
            severity = self._get_severity_from_code(code)

        return QueryError(
            code=code,
            message=message,
            field_name=field_name,
            suggestion=suggestion,
            category=self._get_category_from_code(code),
            severity=severity,
            details=details or {},
        )

    # -------------------------------------------------------------------------
    # Suggestion Generation
    # -------------------------------------------------------------------------

    def _generate_suggestion(
        self,
        code: str,
        error_dict: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate helpful suggestion for error.

        WHAT: Creates context-aware suggestions to help users fix errors.

        PARAMETERS:
            code: Error code
            error_dict: Error details
            context: Query context

        RETURNS:
            Suggestion string if available
        """
        # Use suggestion from error if provided
        if "suggestion" in error_dict:
            return error_dict["suggestion"]

        # Generate template-based suggestions
        template = self.ERROR_MESSAGES.get(code, {})
        suggestion_template = template.get("suggestion_template")

        if not suggestion_template:
            return template.get("suggestion")

        # Fill in template with context
        suggestion_data = self._get_suggestion_data(code, context)
        if suggestion_data:
            return suggestion_template.format(suggestion=suggestion_data)

        return template.get("suggestion")

    def _get_suggestion_data(
        self,
        code: str,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Get data to fill in suggestion template.

        WHAT: Provides specific values for suggestion templates.

        PARAMETERS:
            code: Error code
            context: Query context

        RETURNS:
            Data string for template, or None
        """
        if code == "UNKNOWN_METRIC":
            # Find similar metric
            value = context.get("value", "")
            return self.METRIC_SUGGESTIONS.get(value.lower())

        if code == "UNKNOWN_DIMENSION":
            return "entity, provider, time"

        if code == "UNKNOWN_OPERATOR":
            return "=, !=, >, <, >=, <=, in, contains"

        if code == "INVALID_PROVIDER":
            return "google, meta, tiktok, other"

        if code == "OUT_OF_RANGE":
            field = context.get("field", "")
            if "limit" in field.lower():
                return "1-50"
            elif "days" in field.lower():
                return "1-365"

        return None

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _get_severity(self, code_str: str) -> ErrorSeverity:
        """Get severity level for error code."""
        return self._get_severity_from_code(
            self._string_to_error_code(code_str)
        )

    def _get_severity_from_code(self, code: ErrorCode) -> ErrorSeverity:
        """
        Determine severity from error code.

        WHAT: Maps error codes to severity levels.

        RETURNS:
            ErrorSeverity enum value
        """
        critical_codes = {
            ErrorCode.INTERNAL_ERROR,
            ErrorCode.DATABASE_ERROR,
            ErrorCode.OUT_OF_MEMORY,
        }

        if code in critical_codes:
            return ErrorSeverity.CRITICAL

        warning_codes = {
            ErrorCode.INVALID_COMPOSITION,
            ErrorCode.INCOMPATIBLE_METRICS,
            ErrorCode.OUT_OF_RANGE,
        }

        if code in warning_codes:
            return ErrorSeverity.WARNING

        return ErrorSeverity.ERROR

    def _get_category_from_code(self, code: ErrorCode) -> ErrorCategory:
        """
        Determine category from error code.

        WHAT: Maps error codes to categories.

        RETURNS:
            ErrorCategory enum value
        """
        if code.value.startswith("ERR_001") or code.value.startswith("ERR_004"):
            return ErrorCategory.SCHEMA

        if code.value.startswith("ERR_01"):
            return ErrorCategory.SECURITY

        if code.value.startswith("ERR_02"):
            return ErrorCategory.SEMANTIC

        if code.value.startswith("ERR_03"):
            return ErrorCategory.RESOURCE

        if code.value.startswith("ERR_04"):
            return ErrorCategory.EXTERNAL

        return ErrorCategory.UNKNOWN

    def _string_to_error_code(self, code_str: str) -> ErrorCode:
        """
        Convert string to ErrorCode enum.

        WHAT: Maps string codes to ErrorCode enum values.

        PARAMETERS:
            code_str: String error code (e.g., "UNKNOWN_METRIC")

        RETURNS:
            ErrorCode enum value
        """
        try:
            return ErrorCode[code_str]
        except KeyError:
            return ErrorCode.INTERNAL_ERROR

    # -------------------------------------------------------------------------
    # Error Classification
    # -------------------------------------------------------------------------

    def is_retryable(self, error: QueryError) -> bool:
        """
        Determine if error is retryable.

        WHAT: Identifies errors that can be safely retried.

        PARAMETERS:
            error: QueryError to check

        RETURNS:
            True if the error is likely transient and retryable
        """
        retryable_codes = {
            ErrorCode.QUERY_TIMEOUT,
            ErrorCode.RATE_LIMIT_EXCEEDED,
            ErrorCode.EXTERNAL_API_TIMEOUT,
        }

        return error.code in retryable_codes

    def should_log_user_visible(self, error: QueryError) -> bool:
        """
        Determine if error should be shown to user.

        WHAT: Identifies errors that are safe to show to users.

        PARAMETERS:
            error: QueryError to check

        RETURNS:
            True if error should be shown to user
        """
        # All schema, security, semantic errors are user-visible
        visible_categories = {
            ErrorCategory.SCHEMA,
            ErrorCategory.SECURITY,
            ErrorCategory.SEMANTIC,
        }

        return error.category in visible_categories


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_query_error(
    code: ErrorCode,
    message: str,
    field_name: Optional[str] = None,
    suggestion: Optional[str] = None,
) -> QueryError:
    """
    Convenience function to create a QueryError.

    PARAMETERS:
        code: ErrorCode enum
        message: User message
        field_name: Field that caused error
        suggestion: How to fix it

    RETURNS:
        QueryError instance

    EXAMPLE:
        error = create_query_error(
            code=ErrorCode.UNKNOWN_METRIC,
            message="I don't know that metric",
            field_name="metrics",
            suggestion="Did you mean 'roas'?",
        )
        raise error
    """
    handler = QueryErrorHandler()
    return handler.create_error(
        code=code,
        message=message,
        field_name=field_name,
        suggestion=suggestion,
    )
