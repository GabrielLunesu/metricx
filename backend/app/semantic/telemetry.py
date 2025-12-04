"""
Semantic Layer Telemetry
========================

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Active

Full observability for the semantic query pipeline.
Tracks every stage from query receipt to response delivery.

WHY THIS FILE EXISTS
--------------------
As stated in CLAUDE.md: "We must know when something is failing."
This telemetry system provides:
- Structured logging for every pipeline stage
- Timing metrics for performance monitoring
- Error classification for debugging
- Query patterns for optimization insights

TELEMETRY EVENTS
----------------
The pipeline emits these events:

1. query.started - Query received
   - query_id: Unique identifier for tracing
   - query_summary: Human-readable query description
   - workspace_id: For multi-tenant isolation

2. validation.started / validation.completed
   - layer: Which validation layer (schema, security, semantic)
   - result: passed/failed
   - errors: List of validation errors if any
   - warnings: List of validation warnings

3. compilation.started / compilation.completed
   - strategy: Which compilation strategy was used
   - duration_ms: How long compilation took
   - result_summary: What data was retrieved

4. query.completed
   - total_duration_ms: End-to-end latency
   - strategy: Final compilation strategy
   - success: boolean

5. query.failed
   - error_category: schema/security/semantic/execution
   - error_code: Specific error code
   - error_message: User-friendly message
   - duration_ms: How long before failure

USAGE
-----
```python
from app.semantic.telemetry import TelemetryCollector, QueryContext

# Create telemetry collector
telemetry = TelemetryCollector()

# Start tracking a query
with telemetry.track_query("workspace-123", query) as ctx:
    # Validation stage
    with ctx.track_stage("validation"):
        result = validator.validate(query)
        if not result.valid:
            ctx.fail("validation_failed", result.errors)
            raise ValidationError(result)

    # Compilation stage
    with ctx.track_stage("compilation"):
        data = compiler.compile(query)

    # Success - context manager handles completion
```

INTEGRATION
-----------
The telemetry collector integrates with:
- Python logging (structured JSON)
- Future: DataDog, NewRelic, OpenTelemetry
- Future: Custom metrics dashboards

RELATED FILES
-------------
- app/semantic/compiler.py: Uses telemetry during compilation
- app/semantic/validator.py: Uses telemetry during validation
- app/qa/qa_service.py: Orchestrates the full pipeline
- CLAUDE.md: Observability requirements
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Generator

from app.semantic.query import SemanticQuery

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class EventType(Enum):
    """Types of telemetry events."""
    QUERY_STARTED = "query.started"
    QUERY_COMPLETED = "query.completed"
    QUERY_FAILED = "query.failed"
    VALIDATION_STARTED = "validation.started"
    VALIDATION_COMPLETED = "validation.completed"
    COMPILATION_STARTED = "compilation.started"
    COMPILATION_COMPLETED = "compilation.completed"
    STAGE_STARTED = "stage.started"
    STAGE_COMPLETED = "stage.completed"


class Stage(Enum):
    """Pipeline stages for tracking."""
    VALIDATION = "validation"
    SECURITY = "security"
    COMPILATION = "compilation"
    DATA_FETCH = "data_fetch"
    ANSWER_BUILD = "answer_build"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TelemetryEvent:
    """
    Single telemetry event.

    WHAT: Structured record of something that happened in the pipeline.

    WHY: Enables:
    - Debugging: What happened and when?
    - Monitoring: Are queries failing? Which ones?
    - Optimization: Where is time being spent?

    PARAMETERS:
        event_type: Category of event (query/validation/compilation)
        timestamp: When it happened (ISO format)
        query_id: Unique query identifier for tracing
        workspace_id: Multi-tenant isolation
        stage: Which pipeline stage
        duration_ms: How long the operation took
        success: Whether operation succeeded
        data: Additional structured data

    LOGGING FORMAT:
        [INFO] [2025-12-03T10:30:00] [SEMANTIC] query.started | query_id=abc123 workspace=ws-456
    """
    event_type: EventType
    timestamp: str
    query_id: str
    workspace_id: Optional[str] = None
    stage: Optional[str] = None
    duration_ms: Optional[float] = None
    success: bool = True
    data: Dict[str, Any] = dataclass_field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "query_id": self.query_id,
            "workspace_id": self.workspace_id,
            "stage": self.stage,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "data": self.data,
        }

    def to_log_line(self) -> str:
        """Format as structured log line."""
        parts = [
            f"event={self.event_type.value}",
            f"query_id={self.query_id}",
        ]

        if self.workspace_id:
            parts.append(f"workspace={self.workspace_id[:8]}...")

        if self.stage:
            parts.append(f"stage={self.stage}")

        if self.duration_ms is not None:
            parts.append(f"duration_ms={self.duration_ms:.2f}")

        if not self.success:
            parts.append("success=false")

        # Add select data fields
        for key in ["strategy", "error_code", "error_category"]:
            if key in self.data:
                parts.append(f"{key}={self.data[key]}")

        return " | ".join(parts)


@dataclass
class QueryMetrics:
    """
    Aggregated metrics for a single query.

    WHAT: Summary statistics collected during query execution.

    WHY: Enables performance analysis and SLA monitoring.

    PARAMETERS:
        query_id: Unique identifier
        start_time: When query started
        end_time: When query ended (if finished)
        stages: Timing for each pipeline stage
        validation_errors: Number of validation errors
        validation_warnings: Number of validation warnings
        compilation_strategy: Which strategy was used
        row_count: Number of data rows returned
        success: Whether query succeeded
    """
    query_id: str
    start_time: float
    end_time: Optional[float] = None
    stages: Dict[str, float] = dataclass_field(default_factory=dict)
    validation_errors: int = 0
    validation_warnings: int = 0
    compilation_strategy: Optional[str] = None
    row_count: int = 0
    success: bool = True

    @property
    def total_duration_ms(self) -> Optional[float]:
        """Total query duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query_id": self.query_id,
            "total_duration_ms": self.total_duration_ms,
            "stages": self.stages,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings,
            "compilation_strategy": self.compilation_strategy,
            "row_count": self.row_count,
            "success": self.success,
        }


# =============================================================================
# QUERY CONTEXT
# =============================================================================

class QueryContext:
    """
    Context manager for tracking a single query.

    WHAT: Tracks timing and events for one query through the pipeline.

    WHY: Provides a clean API for instrumenting code:
    - Automatic timing
    - Proper cleanup on error
    - Structured event emission

    USAGE:
        with telemetry.track_query(workspace_id, query) as ctx:
            with ctx.track_stage("validation"):
                validate(query)
            with ctx.track_stage("compilation"):
                compile(query)

    PARAMETERS:
        collector: Parent TelemetryCollector
        query_id: Unique identifier for this query
        workspace_id: Workspace being queried
        query: The SemanticQuery being executed
    """

    def __init__(
        self,
        collector: 'TelemetryCollector',
        query_id: str,
        workspace_id: str,
        query: Optional[SemanticQuery] = None,
    ):
        self.collector = collector
        self.query_id = query_id
        self.workspace_id = workspace_id
        self.query = query
        self.metrics = QueryMetrics(query_id=query_id, start_time=time.time())
        self._current_stage: Optional[str] = None
        self._stage_start: Optional[float] = None
        self._failed = False
        self._failure_data: Dict[str, Any] = {}

    def emit(self, event_type: EventType, **kwargs) -> None:
        """
        Emit a telemetry event.

        PARAMETERS:
            event_type: Type of event
            **kwargs: Additional event data
        """
        event = TelemetryEvent(
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            query_id=self.query_id,
            workspace_id=self.workspace_id,
            **kwargs,
        )
        self.collector.record(event)

    @contextmanager
    def track_stage(self, stage: str) -> Generator[None, None, None]:
        """
        Context manager for tracking a pipeline stage.

        PARAMETERS:
            stage: Name of the stage (validation, compilation, etc.)

        USAGE:
            with ctx.track_stage("validation"):
                validator.validate(query)
        """
        self._current_stage = stage
        self._stage_start = time.time()

        self.emit(EventType.STAGE_STARTED, stage=stage)

        try:
            yield
            # Stage completed successfully
            duration_ms = (time.time() - self._stage_start) * 1000
            self.metrics.stages[stage] = duration_ms

            self.emit(
                EventType.STAGE_COMPLETED,
                stage=stage,
                duration_ms=duration_ms,
                success=True,
            )

        except Exception as e:
            # Stage failed
            duration_ms = (time.time() - self._stage_start) * 1000
            self.metrics.stages[stage] = duration_ms

            self.emit(
                EventType.STAGE_COMPLETED,
                stage=stage,
                duration_ms=duration_ms,
                success=False,
                data={"error": str(e)},
            )
            raise

        finally:
            self._current_stage = None
            self._stage_start = None

    def set_validation_result(
        self,
        valid: bool,
        errors: int = 0,
        warnings: int = 0,
    ) -> None:
        """
        Record validation result.

        PARAMETERS:
            valid: Whether validation passed
            errors: Number of errors found
            warnings: Number of warnings found
        """
        self.metrics.validation_errors = errors
        self.metrics.validation_warnings = warnings

        self.emit(
            EventType.VALIDATION_COMPLETED,
            stage="validation",
            success=valid,
            data={"errors": errors, "warnings": warnings},
        )

    def set_compilation_result(
        self,
        strategy: str,
        row_count: int = 0,
    ) -> None:
        """
        Record compilation result.

        PARAMETERS:
            strategy: Which compilation strategy was used
            row_count: Number of data rows returned
        """
        self.metrics.compilation_strategy = strategy
        self.metrics.row_count = row_count

    def fail(
        self,
        error_code: str,
        error_message: str,
        error_category: str = "execution",
    ) -> None:
        """
        Mark query as failed.

        PARAMETERS:
            error_code: Specific error identifier
            error_message: User-friendly message
            error_category: Category (schema/security/semantic/execution)
        """
        self._failed = True
        self.metrics.success = False
        self._failure_data = {
            "error_code": error_code,
            "error_message": error_message,
            "error_category": error_category,
        }

    def __enter__(self) -> 'QueryContext':
        """Start tracking the query."""
        # Emit query started event
        query_data = {}
        if self.query:
            query_data["query_summary"] = self.query.describe()
            query_data["metrics"] = self.query.metrics
            query_data["has_breakdown"] = self.query.has_breakdown()
            query_data["has_comparison"] = self.query.has_comparison()
            query_data["has_timeseries"] = self.query.include_timeseries

        self.emit(EventType.QUERY_STARTED, data=query_data)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Finish tracking the query."""
        self.metrics.end_time = time.time()
        duration_ms = self.metrics.total_duration_ms

        if exc_type is not None:
            # Exception occurred
            self._failed = True
            self.metrics.success = False
            self._failure_data = {
                "error_type": exc_type.__name__,
                "error_message": str(exc_val),
            }

        if self._failed:
            self.emit(
                EventType.QUERY_FAILED,
                duration_ms=duration_ms,
                success=False,
                data=self._failure_data,
            )
        else:
            self.emit(
                EventType.QUERY_COMPLETED,
                duration_ms=duration_ms,
                success=True,
                data={
                    "strategy": self.metrics.compilation_strategy,
                    "row_count": self.metrics.row_count,
                },
            )

        # Record final metrics
        self.collector.record_metrics(self.metrics)

        # Don't suppress exceptions
        return False


# =============================================================================
# TELEMETRY COLLECTOR
# =============================================================================

class TelemetryCollector:
    """
    Central telemetry collection for the semantic layer.

    WHAT: Collects, logs, and stores telemetry events.

    WHY: Single point of observability for:
    - Debugging production issues
    - Performance monitoring
    - Usage analytics
    - Alerting on failures

    USAGE:
        telemetry = TelemetryCollector()

        # Track a query
        with telemetry.track_query(workspace_id, query) as ctx:
            # ... execute query ...

        # Get recent metrics
        metrics = telemetry.get_recent_metrics(limit=100)

    CONFIGURATION:
        The collector can be configured via environment variables:
        - SEMANTIC_TELEMETRY_ENABLED: true/false
        - SEMANTIC_TELEMETRY_LOG_LEVEL: DEBUG/INFO/WARNING
        - SEMANTIC_TELEMETRY_BUFFER_SIZE: Number of events to keep

    FUTURE INTEGRATIONS:
        - DataDog: metrics.timing(), metrics.count()
        - OpenTelemetry: Distributed tracing
        - Custom webhooks: Real-time alerting
    """

    def __init__(
        self,
        enabled: bool = True,
        log_level: str = "INFO",
        buffer_size: int = 1000,
    ):
        """
        Initialize telemetry collector.

        PARAMETERS:
            enabled: Whether to collect telemetry
            log_level: Minimum log level to emit
            buffer_size: Number of events/metrics to keep in memory
        """
        self.enabled = enabled
        self.log_level = log_level
        self.buffer_size = buffer_size

        # In-memory buffers (could be replaced with Redis/external store)
        self._events: List[TelemetryEvent] = []
        self._metrics: List[QueryMetrics] = []

        # Counters for quick stats
        self._query_count = 0
        self._error_count = 0
        self._total_duration_ms = 0.0

    def track_query(
        self,
        workspace_id: str,
        query: Optional[SemanticQuery] = None,
    ) -> QueryContext:
        """
        Create a tracking context for a query.

        WHAT: Creates a QueryContext for tracking a single query.

        WHY: Clean API for instrumenting query execution.

        PARAMETERS:
            workspace_id: UUID of the workspace
            query: Optional SemanticQuery for metadata

        RETURNS:
            QueryContext to use as context manager

        EXAMPLE:
            with telemetry.track_query(workspace_id, query) as ctx:
                data = compiler.compile(query)
                ctx.set_compilation_result("entity_comparison", len(data))
        """
        query_id = self._generate_query_id()
        return QueryContext(
            collector=self,
            query_id=query_id,
            workspace_id=workspace_id,
            query=query,
        )

    def record(self, event: TelemetryEvent) -> None:
        """
        Record a telemetry event.

        PARAMETERS:
            event: The event to record
        """
        if not self.enabled:
            return

        # Log the event
        log_line = f"[SEMANTIC] {event.to_log_line()}"
        if event.success:
            logger.info(log_line)
        else:
            logger.warning(log_line)

        # Buffer the event
        self._events.append(event)
        if len(self._events) > self.buffer_size:
            self._events.pop(0)

        # Update counters
        if event.event_type == EventType.QUERY_COMPLETED:
            self._query_count += 1
            if event.duration_ms:
                self._total_duration_ms += event.duration_ms

        if event.event_type == EventType.QUERY_FAILED:
            self._query_count += 1
            self._error_count += 1

    def record_metrics(self, metrics: QueryMetrics) -> None:
        """
        Record query metrics.

        PARAMETERS:
            metrics: Aggregated metrics for a query
        """
        if not self.enabled:
            return

        self._metrics.append(metrics)
        if len(self._metrics) > self.buffer_size:
            self._metrics.pop(0)

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent telemetry events.

        PARAMETERS:
            limit: Maximum number of events to return

        RETURNS:
            List of event dictionaries (most recent first)
        """
        return [e.to_dict() for e in self._events[-limit:][::-1]]

    def get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent query metrics.

        PARAMETERS:
            limit: Maximum number of metrics to return

        RETURNS:
            List of metrics dictionaries (most recent first)
        """
        return [m.to_dict() for m in self._metrics[-limit:][::-1]]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get aggregated statistics.

        RETURNS:
            Dict with query count, error rate, avg duration
        """
        avg_duration = 0.0
        if self._query_count > 0:
            avg_duration = self._total_duration_ms / self._query_count

        error_rate = 0.0
        if self._query_count > 0:
            error_rate = self._error_count / self._query_count

        # Calculate strategy distribution
        strategy_counts: Dict[str, int] = {}
        for m in self._metrics:
            if m.compilation_strategy:
                strategy_counts[m.compilation_strategy] = (
                    strategy_counts.get(m.compilation_strategy, 0) + 1
                )

        return {
            "query_count": self._query_count,
            "error_count": self._error_count,
            "error_rate": error_rate,
            "avg_duration_ms": avg_duration,
            "strategy_distribution": strategy_counts,
        }

    def reset(self) -> None:
        """Reset all telemetry data (for testing)."""
        self._events.clear()
        self._metrics.clear()
        self._query_count = 0
        self._error_count = 0
        self._total_duration_ms = 0.0

    def _generate_query_id(self) -> str:
        """Generate unique query ID."""
        return f"sq_{uuid.uuid4().hex[:12]}"


# =============================================================================
# CONVENIENCE INSTANCES
# =============================================================================

# Default collector instance (can be replaced in tests)
_default_collector: Optional[TelemetryCollector] = None


def get_telemetry() -> TelemetryCollector:
    """
    Get the default telemetry collector.

    WHAT: Returns the singleton telemetry collector.

    WHY: Provides easy access without passing collector everywhere.

    RETURNS:
        TelemetryCollector instance

    EXAMPLE:
        from app.semantic.telemetry import get_telemetry
        telemetry = get_telemetry()
        with telemetry.track_query(workspace_id) as ctx:
            ...
    """
    global _default_collector
    if _default_collector is None:
        _default_collector = TelemetryCollector()
    return _default_collector


def set_telemetry(collector: TelemetryCollector) -> None:
    """
    Set the default telemetry collector.

    WHAT: Replaces the default collector.

    WHY: For testing or custom configurations.

    PARAMETERS:
        collector: New TelemetryCollector to use
    """
    global _default_collector
    _default_collector = collector
