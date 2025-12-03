"""
Semantic Layer for QA System
============================

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Active Development

This module provides a **composable query system** that replaces the rigid DSL
(Domain-Specific Language) for handling complex analytics questions.

WHY THIS EXISTS
---------------
The original DSL had mutually exclusive fields - you could have `breakdown` OR
`compare_to_previous`, but not both. This prevented queries like:

    "compare CPC this week vs last week for top 3 ads"

Which requires:
- breakdown: entity/ad, limit 3
- comparison: previous_period
- timeseries: true (for the chart)

The semantic layer makes these components **composable** - they can be combined
freely to express any valid analytics question.

ARCHITECTURE OVERVIEW
---------------------
```
User Question
    |
    v
LLM Translation (nlp/translator.py)
    |
    v
SemanticQuery (semantic/query.py)
    |
    v
Validation Pipeline (semantic/validator.py)
    |   1. Schema validation (Pydantic)
    |   2. Security validation (allowlists)
    |   3. Semantic validation (business rules)
    |
    v
Semantic Compiler (semantic/compiler.py)
    |
    v
UnifiedMetricService (services/unified_metric_service.py)
    |
    v
CompiledResult
    |
    v
Answer + Visuals
```

SECURITY MODEL
--------------
The LLM **never writes SQL**. Instead:
1. LLM outputs JSON matching SemanticQuery schema
2. JSON is validated against allowlists (not blocklists)
3. SQLAlchemy parameterizes all values
4. Every query is workspace-scoped at SQL level

This provides **defense in depth** against injection attacks.

OBSERVABILITY
-------------
Every stage of the pipeline logs structured events:
- query.started: Query received
- stage.completed: Each validation/compilation stage
- query.completed: Success with timing
- query.failed: Error with classification

See `semantic/telemetry.py` for the full telemetry system.

COMPONENTS
----------
- model.py: Metric and dimension definitions (single source of truth)
- query.py: SemanticQuery dataclass (composable query structure)
- security.py: Security validation with allowlists
- validator.py: Multi-layer validation pipeline
- compiler.py: Query to data compilation
- telemetry.py: Pipeline observability
- errors.py: Error classification and user-friendly messages

USAGE
-----
```python
from app.semantic import (
    SemanticQuery,
    SemanticCompiler,
    SemanticValidator,
    TelemetryCollector,
)

# Build a query
query = SemanticQuery(
    metrics=["cpc"],
    time_range=TimeRange(last_n_days=7),
    breakdown=Breakdown(dimension="entity", level="ad", limit=3),
    comparison=Comparison(type=ComparisonType.PREVIOUS_PERIOD),
    include_timeseries=True,
)

# Validate
validator = SemanticValidator()
result = validator.validate(query)
if not result.valid:
    return error_response(result.to_user_message())

# Compile and execute
compiler = SemanticCompiler(service)
data = compiler.compile(query, workspace_id)
```

RELATED FILES
-------------
- app/dsl/schema.py: Original DSL (being replaced)
- app/metrics/registry.py: Metric definitions (reused)
- app/services/unified_metric_service.py: Data fetching (reused)
- app/answer/visual_builder.py: Chart generation (updated)
- docs/living-docs/SEMANTIC_LAYER_IMPLEMENTATION_PLAN.md: Full plan

CHANGELOG
---------
- 2025-12-03: Initial implementation (Phase 1 foundation)
"""

# Re-export main components for clean imports

from app.semantic.query import (
    SemanticQuery,
    TimeRange,
    Breakdown,
    Comparison,
    Filter,
    ComparisonType,
    OutputFormat,
)

from app.semantic.validator import (
    SemanticValidator,
    ValidationResult,
    ValidationError,
)

from app.semantic.security import (
    SecurityValidator,
    SecurityError,
)

from app.semantic.errors import (
    QueryError,
    QueryErrorHandler,
    ErrorCategory,
    ErrorSeverity,
    ErrorCode,
)

from app.semantic.model import (
    get_metric,
    get_dimension,
    get_all_metric_names,
    METRICS,
    DIMENSIONS,
)

from app.semantic.compiler import (
    SemanticCompiler,
    CompilationResult,
    EntityComparisonItem,
    EntityTimeseriesItem,
    compile_query,
)

from app.semantic.telemetry import (
    TelemetryCollector,
    QueryContext,
    QueryMetrics,
    TelemetryEvent,
    EventType,
    get_telemetry,
    set_telemetry,
)

from app.semantic.prompts import (
    build_semantic_system_prompt,
    build_semantic_few_shot_prompt,
    build_semantic_full_prompt,
    get_semantic_json_schema,
    get_semantic_examples,
    SEMANTIC_ANSWER_PROMPT,
)

__all__ = [
    # Query components (query.py)
    "SemanticQuery",
    "TimeRange",
    "Breakdown",
    "Comparison",
    "Filter",
    "ComparisonType",
    "OutputFormat",
    # Validation components (validator.py)
    "SemanticValidator",
    "ValidationResult",
    "ValidationError",
    # Security components (security.py)
    "SecurityValidator",
    "SecurityError",
    # Error handling (errors.py)
    "QueryError",
    "QueryErrorHandler",
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorCode",
    # Model components (model.py)
    "get_metric",
    "get_dimension",
    "get_all_metric_names",
    "METRICS",
    "DIMENSIONS",
    # Compiler components (compiler.py)
    "SemanticCompiler",
    "CompilationResult",
    "EntityComparisonItem",
    "EntityTimeseriesItem",
    "compile_query",
    # Telemetry components (telemetry.py)
    "TelemetryCollector",
    "QueryContext",
    "QueryMetrics",
    "TelemetryEvent",
    "EventType",
    "get_telemetry",
    "set_telemetry",
    # Prompt components (prompts.py)
    "build_semantic_system_prompt",
    "build_semantic_few_shot_prompt",
    "build_semantic_full_prompt",
    "get_semantic_json_schema",
    "get_semantic_examples",
    "SEMANTIC_ANSWER_PROMPT",
]

# Version for tracking compatibility
__version__ = "1.0.0"
