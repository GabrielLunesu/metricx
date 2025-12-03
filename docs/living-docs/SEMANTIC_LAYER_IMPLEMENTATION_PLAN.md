# Semantic Layer Implementation Plan

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Planning
**Author**: Architecture Review

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [Architecture Design](#architecture-design)
5. [Implementation Phases](#implementation-phases)
6. [File-by-File Changes](#file-by-file-changes)
7. [Security Design](#security-design)
8. [Observability Design](#observability-design)
9. [Testing Strategy](#testing-strategy)
10. [Migration Plan](#migration-plan)
11. [Risk Assessment](#risk-assessment)
12. [Success Criteria](#success-criteria)
13. [Timeline](#timeline)
14. [Appendix](#appendix)

---

## Executive Summary

### What We're Building

A **Semantic Layer** that replaces the current rigid DSL (Domain-Specific Language) with a composable query system. This enables the QA system to handle complex queries like "compare CPC this week vs last week for top 3 ads" that the current architecture cannot express.

### Why We're Building It

The current DSL has **mutually exclusive fields**:
- You can have `breakdown` OR `compare_to_previous`, not both
- You can have `entity_timeseries` OR `comparison`, not both

Users expect these to compose freely. The semantic layer makes this possible.

### Key Benefits

| Benefit | Current State | After Semantic Layer |
|---------|--------------|---------------------|
| Query flexibility | Rigid, predefined patterns | Composable, any valid combination |
| Prompt complexity | 2000+ lines, 100+ examples | ~200 lines, composability rules |
| Code maintainability | Every new feature = new code paths | New features = model additions |
| Error messages | Generic validation errors | Contextual, helpful suggestions |
| Observability | Basic logging | Full pipeline telemetry |

### Estimated Effort

**2-3 weeks** for full implementation, testing, and cleanup.

---

## Problem Statement

### Current Architecture Limitations

```
User: "compare CPC this week vs last week for top 3 ads"

Current DSL can express:
├── breakdown: "ad", top_n: 3          ✓ (gets top 3 ads)
├── compare_to_previous: true          ✓ (gets comparison)
└── BOTH together                      ✗ (not supported!)

Result: System shows top 3 ads but only THIS week's data.
        Previous week comparison is missing.
```

### Root Cause

The DSL schema treats features as **mutually exclusive modes** rather than **composable components**:

```python
# Current: Rigid modes
class MetricQuery:
    breakdown: Optional[str]           # Mode A: Entity breakdown
    compare_to_previous: bool          # Mode B: Time comparison
    # These don't compose - executor picks ONE path

# Needed: Composable components
class SemanticQuery:
    breakdown: Optional[Breakdown]     # Component A
    comparison: Optional[Comparison]   # Component B
    # These compose freely - compiler handles all combinations
```

### Evidence from User Testing

| Query | Expected | Actual | Root Cause |
|-------|----------|--------|------------|
| "compare CPC this week vs last week for top 3 ads" | 6 chart lines (3 ads × 2 periods) | 3 lines (current period only) | Breakdown + comparison don't compose |
| "give a comparison with this week vs last week for this" | Context-aware comparison | "Failed to fetch" | Follow-up context not resolving |
| "compare CPC for Meta - Awareness Top Funnel" | Specific entity data | Wrong entities shown | Entity name filtering fails |

---

## Solution Overview

### Semantic Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SEMANTIC LAYER ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │   User      │────▶│    LLM      │────▶│  Semantic   │           │
│  │  Question   │     │ Translator  │     │   Query     │           │
│  └─────────────┘     └─────────────┘     └──────┬──────┘           │
│                                                 │                   │
│                                                 ▼                   │
│                      ┌──────────────────────────────────┐           │
│                      │         VALIDATION LAYERS        │           │
│                      ├──────────────────────────────────┤           │
│                      │ 1. Schema (Pydantic)             │           │
│                      │ 2. Security (Allowlists)         │           │
│                      │ 3. Semantic (Business Rules)     │           │
│                      └──────────────┬───────────────────┘           │
│                                     │                               │
│                                     ▼                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    SEMANTIC COMPILER                         │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │  Analyzes query composition:                                 │   │
│  │  - Has breakdown? → Fetch breakdown data                     │   │
│  │  - Has comparison? → Fetch previous period                   │   │
│  │  - Has both? → Fetch per-entity comparison (NEW!)            │   │
│  │  - Has timeseries? → Fetch daily data                        │   │
│  └─────────────────────────────────┬───────────────────────────┘   │
│                                    │                                │
│                                    ▼                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              UNIFIED METRIC SERVICE                          │   │
│  │              (Existing - Enhanced)                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Query format | JSON (not SQL) | Safety - LLM never writes SQL |
| Validation | Multi-layer | Defense in depth |
| Compilation | Lazy | Only fetch data that's requested |
| Execution | SQLAlchemy ORM | Parameterized queries, no injection |
| Telemetry | Per-stage | Granular debugging |

---

## Architecture Design

### Component Overview

```
backend/app/
├── semantic/                    # NEW: Semantic Layer
│   ├── __init__.py
│   ├── model.py                 # Metric/dimension definitions
│   ├── query.py                 # SemanticQuery dataclass
│   ├── compiler.py              # Query → Data compilation
│   ├── validator.py             # Multi-layer validation
│   ├── security.py              # Security checks
│   ├── telemetry.py             # Pipeline observability
│   └── errors.py                # Error handling
│
├── dsl/                         # MODIFIED: Simplified
│   ├── schema.py                # Keep for backwards compat
│   ├── executor.py              # Delegate to semantic compiler
│   └── planner.py               # Simplified
│
├── nlp/                         # MODIFIED: Simpler prompts
│   ├── prompts.py               # Reduced from 2000 to ~300 lines
│   └── translator.py            # Output SemanticQuery
│
├── services/                    # MODIFIED: Enhanced
│   ├── qa_service.py            # Use semantic pipeline
│   └── unified_metric_service.py # Add entity comparison
│
└── answer/                      # MODIFIED: New data structures
    └── visual_builder.py        # Handle composed data
```

### Data Flow

```
1. User Question
   │
   ▼
2. LLM Translation (prompts.py → translator.py)
   │  Output: SemanticQuery JSON
   ▼
3. Schema Validation (Pydantic)
   │  Check: Valid JSON, correct types
   ▼
4. Security Validation (security.py)
   │  Check: Metrics/dimensions in allowlist
   ▼
5. Semantic Validation (validator.py)
   │  Check: Valid composition, business rules
   ▼
6. Compilation (compiler.py)
   │  Analyze: What data is needed?
   │  Execute: Call UnifiedMetricService methods
   │  Output: CompiledResult
   ▼
7. Answer Generation (answer_builder.py)
   │  Input: Question + SemanticQuery + CompiledResult
   │  Output: Natural language answer
   ▼
8. Visual Building (visual_builder.py)
   │  Input: CompiledResult
   │  Output: Charts, tables, cards
   ▼
9. Response
```

---

## Implementation Phases

### Phase 1: Foundation (Days 1-3)

**Goal**: Create semantic layer structure without breaking existing functionality.

```
Tasks:
├── Create backend/app/semantic/ folder
├── Implement model.py (metric/dimension definitions)
├── Implement query.py (SemanticQuery dataclass)
├── Implement security.py (allowlists, validation)
├── Write unit tests for all new code
└── No changes to existing code yet
```

**Deliverables**:
- [ ] `semantic/model.py` with all 24 metrics defined
- [ ] `semantic/query.py` with SemanticQuery dataclass
- [ ] `semantic/security.py` with SecurityValidator
- [ ] 50+ unit tests for semantic layer

### Phase 2: Validation Pipeline (Days 4-5)

**Goal**: Build multi-layer validation with helpful error messages.

```
Tasks:
├── Implement validator.py (schema + security + semantic)
├── Implement errors.py (error classification, user messages)
├── Write validation tests
└── Test error message quality
```

**Deliverables**:
- [ ] `semantic/validator.py` with SemanticValidator
- [ ] `semantic/errors.py` with QueryErrorHandler
- [ ] Error message quality review

### Phase 3: Compiler Core (Days 6-9)

**Goal**: Build the compiler that translates semantic queries to data.

```
Tasks:
├── Implement compiler.py basic structure
├── Add summary compilation
├── Add breakdown compilation
├── Add comparison compilation
├── Add entity_comparison compilation (THE KEY FEATURE)
├── Add entity_timeseries compilation
├── Integration with UnifiedMetricService
└── Comprehensive compiler tests
```

**Deliverables**:
- [ ] `semantic/compiler.py` with SemanticCompiler
- [ ] `CompiledResult` dataclass with all data types
- [ ] Integration tests with real database

### Phase 4: Telemetry (Day 10)

**Goal**: Add full pipeline observability.

```
Tasks:
├── Implement telemetry.py
├── Add stage timing
├── Add error classification
├── Add query analytics hooks
└── Test telemetry output
```

**Deliverables**:
- [ ] `semantic/telemetry.py` with TelemetryCollector
- [ ] Structured logging at every stage
- [ ] Query timing metrics

### Phase 5: Integration (Days 11-13)

**Goal**: Connect semantic layer to existing system.

```
Tasks:
├── Update prompts.py (simplified semantic format)
├── Update translator.py (output SemanticQuery)
├── Update qa_service.py (use semantic pipeline)
├── Update executor.py (delegate to compiler)
├── Update visual_builder.py (handle new data)
├── Update answer_builder.py (use CompiledResult)
└── Integration tests
```

**Deliverables**:
- [ ] All existing tests still pass
- [ ] New semantic path working end-to-end
- [ ] Complex queries working (breakdown + comparison)

### Phase 6: Testing & Polish (Days 14-15)

**Goal**: Comprehensive testing and documentation.

```
Tasks:
├── End-to-end test suite
├── Performance benchmarks
├── Error scenario testing
├── Documentation updates
├── Code review and cleanup
└── QA_SYSTEM_ARCHITECTURE.md update
```

**Deliverables**:
- [ ] 100+ new tests
- [ ] Performance baseline established
- [ ] Documentation updated
- [ ] Code review complete

---

## File-by-File Changes

### New Files

#### `backend/app/semantic/__init__.py`

```python
"""
Semantic Layer for QA System
============================

Composable query system replacing the rigid DSL.

Components:
- model.py: Metric and dimension definitions
- query.py: SemanticQuery dataclass
- compiler.py: Query → Data compilation
- validator.py: Multi-layer validation
- security.py: Security checks
- telemetry.py: Pipeline observability
- errors.py: Error handling

Usage:
    from app.semantic import SemanticQuery, SemanticCompiler, SemanticValidator

    query = SemanticQuery(metrics=["roas"], ...)
    validator = SemanticValidator()
    result = validator.validate(query)

    if result.valid:
        compiler = SemanticCompiler(service)
        data = compiler.compile(query, workspace_id)
"""

from app.semantic.query import SemanticQuery, TimeRange, Breakdown, Comparison, Filter
from app.semantic.compiler import SemanticCompiler, CompiledResult
from app.semantic.validator import SemanticValidator, ValidationResult
from app.semantic.security import SecurityValidator, SecurityError
from app.semantic.telemetry import TelemetryCollector, QueryStage
from app.semantic.errors import QueryErrorHandler

__all__ = [
    "SemanticQuery",
    "TimeRange",
    "Breakdown",
    "Comparison",
    "Filter",
    "SemanticCompiler",
    "CompiledResult",
    "SemanticValidator",
    "ValidationResult",
    "SecurityValidator",
    "SecurityError",
    "TelemetryCollector",
    "QueryStage",
    "QueryErrorHandler",
]
```

#### `backend/app/semantic/model.py`

```python
"""
Semantic Model Definition
=========================

Single source of truth for metrics and dimensions in metricx.
This model defines WHAT can be queried, not HOW.

Related files:
- app/metrics/registry.py: Formula implementations (reused)
- app/metrics/formulas.py: Calculation functions (reused)

Design:
- Metrics define what can be measured and how to display
- Dimensions define what can be grouped/filtered by
- Composability rules define valid query combinations
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict
from enum import Enum


class MetricType(Enum):
    """Display format for metric values."""
    CURRENCY = "currency"      # $1,234.56
    RATIO = "ratio"            # 2.45×
    PERCENTAGE = "percentage"  # 4.2%
    COUNT = "count"            # 1,234


class DimensionType(Enum):
    """Type of dimension for query building."""
    ENTITY = "entity"          # campaign, adset, ad
    CATEGORICAL = "categorical" # provider, status
    TEMPORAL = "temporal"       # day, week, month


@dataclass
class Metric:
    """
    Definition of a single metric.

    Attributes:
        name: Internal metric name (e.g., "roas")
        display_name: Human-readable name (e.g., "Return on Ad Spend")
        type: How to format the value
        formula_deps: Base measures needed for calculation
        inverse: True if lower is better (CPC, CPA)
        supports_timeseries: Can show over time
        supports_comparison: Can compare to previous period
        supports_breakdown: Can break down by dimension
    """
    name: str
    display_name: str
    type: MetricType
    formula_deps: List[str]
    inverse: bool = False
    supports_timeseries: bool = True
    supports_comparison: bool = True
    supports_breakdown: bool = True


@dataclass
class Dimension:
    """
    Definition of a dimension for grouping/filtering.

    Attributes:
        name: Internal dimension name
        display_name: Human-readable name
        type: Entity, categorical, or temporal
        levels: For entity dimensions, the hierarchy levels
        granularities: For temporal dimensions, the time buckets
    """
    name: str
    display_name: str
    type: DimensionType
    levels: Optional[List[str]] = None
    granularities: Optional[List[str]] = None


# =============================================================================
# METRIC DEFINITIONS
# =============================================================================

METRICS: Dict[str, Metric] = {
    # Base Measures
    "spend": Metric(
        name="spend",
        display_name="Spend",
        type=MetricType.CURRENCY,
        formula_deps=["spend"],
    ),
    "revenue": Metric(
        name="revenue",
        display_name="Revenue",
        type=MetricType.CURRENCY,
        formula_deps=["revenue"],
    ),
    "profit": Metric(
        name="profit",
        display_name="Profit",
        type=MetricType.CURRENCY,
        formula_deps=["profit"],
    ),
    "clicks": Metric(
        name="clicks",
        display_name="Clicks",
        type=MetricType.COUNT,
        formula_deps=["clicks"],
    ),
    "impressions": Metric(
        name="impressions",
        display_name="Impressions",
        type=MetricType.COUNT,
        formula_deps=["impressions"],
    ),
    "conversions": Metric(
        name="conversions",
        display_name="Conversions",
        type=MetricType.COUNT,
        formula_deps=["conversions"],
    ),
    "leads": Metric(
        name="leads",
        display_name="Leads",
        type=MetricType.COUNT,
        formula_deps=["leads"],
    ),
    "installs": Metric(
        name="installs",
        display_name="Installs",
        type=MetricType.COUNT,
        formula_deps=["installs"],
    ),
    "purchases": Metric(
        name="purchases",
        display_name="Purchases",
        type=MetricType.COUNT,
        formula_deps=["purchases"],
    ),
    "visitors": Metric(
        name="visitors",
        display_name="Visitors",
        type=MetricType.COUNT,
        formula_deps=["visitors"],
    ),

    # Derived Metrics - Efficiency (inverse: lower is better)
    "cpc": Metric(
        name="cpc",
        display_name="Cost per Click",
        type=MetricType.CURRENCY,
        formula_deps=["spend", "clicks"],
        inverse=True,
    ),
    "cpm": Metric(
        name="cpm",
        display_name="Cost per 1K Impressions",
        type=MetricType.CURRENCY,
        formula_deps=["spend", "impressions"],
        inverse=True,
    ),
    "cpa": Metric(
        name="cpa",
        display_name="Cost per Acquisition",
        type=MetricType.CURRENCY,
        formula_deps=["spend", "conversions"],
        inverse=True,
    ),
    "cpl": Metric(
        name="cpl",
        display_name="Cost per Lead",
        type=MetricType.CURRENCY,
        formula_deps=["spend", "leads"],
        inverse=True,
    ),
    "cpi": Metric(
        name="cpi",
        display_name="Cost per Install",
        type=MetricType.CURRENCY,
        formula_deps=["spend", "installs"],
        inverse=True,
    ),
    "cpp": Metric(
        name="cpp",
        display_name="Cost per Purchase",
        type=MetricType.CURRENCY,
        formula_deps=["spend", "purchases"],
        inverse=True,
    ),

    # Derived Metrics - Value (higher is better)
    "roas": Metric(
        name="roas",
        display_name="Return on Ad Spend",
        type=MetricType.RATIO,
        formula_deps=["revenue", "spend"],
    ),
    "poas": Metric(
        name="poas",
        display_name="Profit on Ad Spend",
        type=MetricType.RATIO,
        formula_deps=["profit", "spend"],
    ),
    "aov": Metric(
        name="aov",
        display_name="Average Order Value",
        type=MetricType.CURRENCY,
        formula_deps=["revenue", "purchases"],
    ),
    "arpv": Metric(
        name="arpv",
        display_name="Average Revenue per Visitor",
        type=MetricType.CURRENCY,
        formula_deps=["revenue", "visitors"],
    ),

    # Derived Metrics - Engagement (higher is better)
    "ctr": Metric(
        name="ctr",
        display_name="Click-through Rate",
        type=MetricType.PERCENTAGE,
        formula_deps=["clicks", "impressions"],
    ),
    "cvr": Metric(
        name="cvr",
        display_name="Conversion Rate",
        type=MetricType.PERCENTAGE,
        formula_deps=["conversions", "clicks"],
    ),
}


# =============================================================================
# DIMENSION DEFINITIONS
# =============================================================================

DIMENSIONS: Dict[str, Dimension] = {
    "entity": Dimension(
        name="entity",
        display_name="Entity",
        type=DimensionType.ENTITY,
        levels=["campaign", "adset", "ad"],
    ),
    "provider": Dimension(
        name="provider",
        display_name="Platform",
        type=DimensionType.CATEGORICAL,
    ),
    "time": Dimension(
        name="time",
        display_name="Time",
        type=DimensionType.TEMPORAL,
        granularities=["day", "week", "month"],
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_metric(name: str) -> Optional[Metric]:
    """Get metric definition by name."""
    return METRICS.get(name)


def get_dimension(name: str) -> Optional[Dimension]:
    """Get dimension definition by name."""
    return DIMENSIONS.get(name)


def get_all_metric_names() -> Set[str]:
    """Get set of all valid metric names."""
    return set(METRICS.keys())


def get_all_dimension_names() -> Set[str]:
    """Get set of all valid dimension names."""
    return set(DIMENSIONS.keys())


def is_inverse_metric(name: str) -> bool:
    """Check if metric is inverse (lower is better)."""
    metric = get_metric(name)
    return metric.inverse if metric else False
```

#### `backend/app/semantic/query.py`

```python
"""
Semantic Query Model
====================

Composable query structure that replaces the rigid DSL.
This is what the LLM outputs and what the compiler consumes.

Key insight: Components COMPOSE freely.
- breakdown + comparison = per-entity comparison data
- breakdown + timeseries = per-entity timeseries (multi-line chart)
- All three = full flexibility

Related files:
- app/semantic/compiler.py: Compiles these queries
- app/semantic/validator.py: Validates these queries
- app/nlp/translator.py: LLM outputs these
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from datetime import date
from enum import Enum


class ComparisonType(Enum):
    """Type of time comparison."""
    PREVIOUS_PERIOD = "previous_period"
    YEAR_OVER_YEAR = "year_over_year"
    CUSTOM = "custom"


class OutputFormat(Enum):
    """Preferred output format."""
    AUTO = "auto"
    CHART = "chart"
    TABLE = "table"
    TEXT = "text"


@dataclass
class TimeRange:
    """
    Time range specification.

    Either last_n_days OR (start, end), not both.
    """
    start: Optional[date] = None
    end: Optional[date] = None
    last_n_days: Optional[int] = None

    def to_dict(self) -> Dict:
        if self.last_n_days:
            return {"last_n_days": self.last_n_days}
        return {
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
        }


@dataclass
class Breakdown:
    """
    Breakdown specification.

    Attributes:
        dimension: What to group by ("entity", "provider", "time")
        level: For entity dimension ("campaign", "adset", "ad")
        granularity: For time dimension ("day", "week", "month")
        limit: Max items to return (1-50)
        sort_order: "asc" or "desc"
    """
    dimension: str
    level: Optional[str] = None
    granularity: Optional[str] = None
    limit: int = 5
    sort_order: str = "desc"

    def to_dict(self) -> Dict:
        return {
            "dimension": self.dimension,
            "level": self.level,
            "granularity": self.granularity,
            "limit": self.limit,
            "sort_order": self.sort_order,
        }


@dataclass
class Comparison:
    """
    Time comparison specification.

    Attributes:
        type: Type of comparison (previous_period, year_over_year)
        include_timeseries: Fetch timeseries for both periods
    """
    type: ComparisonType = ComparisonType.PREVIOUS_PERIOD
    include_timeseries: bool = False

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "include_timeseries": self.include_timeseries,
        }


@dataclass
class Filter:
    """
    Filter specification.

    Attributes:
        field: Field to filter on (provider, level, status, entity_name)
        operator: Comparison operator (=, !=, >, <, in, contains)
        value: Value to compare against
    """
    field: str
    operator: str
    value: Any

    def to_dict(self) -> Dict:
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
        }


@dataclass
class SemanticQuery:
    """
    Composable query that can express any valid metric question.

    CRITICAL: Unlike DSL, these components COMPOSE freely.
    You can have breakdown + comparison + timeseries all at once.

    Attributes:
        metrics: One or more metrics to calculate
        time_range: Time period for the query
        breakdown: Optional grouping by dimension
        comparison: Optional comparison to previous period
        include_timeseries: Include daily/hourly data
        filters: Optional filters to apply
        output_format: Preferred output format
        metric_inferred: True if metric was auto-selected (not specified by user)

    Examples:
        Simple:
            SemanticQuery(metrics=["roas"], time_range=TimeRange(last_n_days=7))

        Breakdown:
            SemanticQuery(
                metrics=["cpc"],
                time_range=TimeRange(last_n_days=7),
                breakdown=Breakdown(dimension="entity", level="ad", limit=3)
            )

        Full (THE MISSING QUERY):
            SemanticQuery(
                metrics=["cpc"],
                time_range=TimeRange(last_n_days=7),
                breakdown=Breakdown(dimension="entity", level="ad", limit=3),
                comparison=Comparison(type=ComparisonType.PREVIOUS_PERIOD),
                include_timeseries=True
            )
    """
    # Required
    metrics: List[str]
    time_range: TimeRange

    # Optional - these COMPOSE
    breakdown: Optional[Breakdown] = None
    comparison: Optional[Comparison] = None
    include_timeseries: bool = False

    # Filters
    filters: List[Filter] = field(default_factory=list)

    # Output preferences
    output_format: OutputFormat = OutputFormat.AUTO

    # Metadata
    metric_inferred: bool = False

    def has_breakdown(self) -> bool:
        """Check if query has a breakdown component."""
        return self.breakdown is not None

    def has_comparison(self) -> bool:
        """Check if query has a comparison component."""
        return self.comparison is not None

    def needs_entity_comparison(self) -> bool:
        """
        Check if query needs per-entity comparison data.

        This is the KEY composition that was missing:
        breakdown (entity) + comparison = per-entity previous period data
        """
        return (
            self.has_breakdown()
            and self.breakdown.dimension == "entity"
            and self.has_comparison()
        )

    def needs_entity_timeseries(self) -> bool:
        """
        Check if query needs per-entity timeseries data.

        This enables multi-line charts where each line is an entity.
        """
        return (
            self.has_breakdown()
            and self.breakdown.dimension == "entity"
            and self.include_timeseries
        )

    def get_primary_metric(self) -> str:
        """Get the first/primary metric."""
        return self.metrics[0] if self.metrics else "spend"

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        result = {
            "metrics": self.metrics,
            "time_range": self.time_range.to_dict(),
            "include_timeseries": self.include_timeseries,
            "output_format": self.output_format.value,
            "metric_inferred": self.metric_inferred,
        }

        if self.breakdown:
            result["breakdown"] = self.breakdown.to_dict()

        if self.comparison:
            result["comparison"] = self.comparison.to_dict()

        if self.filters:
            result["filters"] = [f.to_dict() for f in self.filters]

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> 'SemanticQuery':
        """Create SemanticQuery from dictionary."""
        time_range_data = data.get("time_range", {})
        time_range = TimeRange(
            start=date.fromisoformat(time_range_data["start"]) if time_range_data.get("start") else None,
            end=date.fromisoformat(time_range_data["end"]) if time_range_data.get("end") else None,
            last_n_days=time_range_data.get("last_n_days"),
        )

        breakdown = None
        if data.get("breakdown"):
            bd = data["breakdown"]
            breakdown = Breakdown(
                dimension=bd["dimension"],
                level=bd.get("level"),
                granularity=bd.get("granularity"),
                limit=bd.get("limit", 5),
                sort_order=bd.get("sort_order", "desc"),
            )

        comparison = None
        if data.get("comparison"):
            comp = data["comparison"]
            comparison = Comparison(
                type=ComparisonType(comp.get("type", "previous_period")),
                include_timeseries=comp.get("include_timeseries", False),
            )

        filters = []
        for f in data.get("filters", []):
            filters.append(Filter(
                field=f["field"],
                operator=f["operator"],
                value=f["value"],
            ))

        return cls(
            metrics=data.get("metrics", []),
            time_range=time_range,
            breakdown=breakdown,
            comparison=comparison,
            include_timeseries=data.get("include_timeseries", False),
            filters=filters,
            output_format=OutputFormat(data.get("output_format", "auto")),
            metric_inferred=data.get("metric_inferred", False),
        )
```

### Modified Files

#### `backend/app/nlp/prompts.py` (Simplified)

**Changes**:
- Remove 1800+ lines of few-shot examples
- Add semantic query format documentation
- Add composability rules
- Keep ~300 lines total

```python
# Key changes - replace FEW_SHOT_EXAMPLES with:

SEMANTIC_FEW_SHOT_EXAMPLES = [
    # Simple metric query
    {
        "question": "What's my ROAS this week?",
        "query": {
            "metrics": ["roas"],
            "time_range": {"last_n_days": 7}
        }
    },

    # Breakdown query
    {
        "question": "Show me spend by campaign",
        "query": {
            "metrics": ["spend"],
            "time_range": {"last_n_days": 7},
            "breakdown": {"dimension": "entity", "level": "campaign", "limit": 10}
        }
    },

    # Comparison query
    {
        "question": "How does my CPC compare to last week?",
        "query": {
            "metrics": ["cpc"],
            "time_range": {"last_n_days": 7},
            "comparison": {"type": "previous_period"}
        }
    },

    # THE KEY EXAMPLE: Breakdown + Comparison (what was missing!)
    {
        "question": "Compare CPC this week vs last week for top 3 ads",
        "query": {
            "metrics": ["cpc"],
            "time_range": {"last_n_days": 7},
            "breakdown": {"dimension": "entity", "level": "ad", "limit": 3},
            "comparison": {"type": "previous_period", "include_timeseries": True},
            "include_timeseries": True
        }
    },

    # Multi-metric query
    {
        "question": "Show me spend, revenue, and ROAS",
        "query": {
            "metrics": ["spend", "revenue", "roas"],
            "time_range": {"last_n_days": 7}
        }
    },

    # Filter query
    {
        "question": "What's my Google Ads CPA?",
        "query": {
            "metrics": ["cpa"],
            "time_range": {"last_n_days": 7},
            "filters": [{"field": "provider", "operator": "=", "value": "google"}]
        }
    },
]
```

#### `backend/app/services/unified_metric_service.py` (Enhanced)

**Changes**:
- Add `get_entity_comparison()` method
- Add `get_entity_timeseries_with_previous()` method
- Enhance logging

```python
# Add these methods:

def get_entity_comparison(
    self,
    workspace_id: str,
    metric: str,
    time_range: TimeRange,
    entity_ids: List[str],
    entity_labels: Dict[str, str],
) -> Dict[str, Dict[str, Any]]:
    """
    Get comparison data for multiple entities.

    THIS IS THE KEY NEW METHOD that enables:
    "compare CPC this week vs last week for top 3 ads"

    Args:
        workspace_id: Workspace UUID
        metric: Metric to calculate
        time_range: Current time range
        entity_ids: List of entity UUIDs to compare
        entity_labels: Mapping of entity_id -> display name

    Returns:
        Dict mapping entity_id to comparison data:
        {
            "entity-uuid-1": {
                "entity_name": "Summer Sale Ad",
                "this_period": 0.45,
                "previous_period": 0.38,
                "delta_pct": 0.18
            },
            ...
        }
    """
    logger.info(f"[UNIFIED_METRICS] Getting entity comparison for {len(entity_ids)} entities")

    # Calculate previous period
    start_date, end_date = self._resolve_time_range(time_range)
    prev_start, prev_end = self._get_previous_period(start_date, end_date)

    prev_time_range = TimeRange(start=prev_start, end=prev_end)

    result = {}

    for entity_id in entity_ids:
        # Current period
        current_filters = MetricFilters(entity_ids=[entity_id])
        current = self.get_summary(
            workspace_id=workspace_id,
            metrics=[metric],
            time_range=time_range,
            filters=current_filters,
        )

        # Previous period
        previous = self.get_summary(
            workspace_id=workspace_id,
            metrics=[metric],
            time_range=prev_time_range,
            filters=current_filters,
        )

        current_val = current.metrics.get(metric).value if current.metrics.get(metric) else None
        previous_val = previous.metrics.get(metric).value if previous.metrics.get(metric) else None

        delta_pct = None
        if previous_val and previous_val != 0 and current_val is not None:
            delta_pct = (current_val - previous_val) / previous_val

        result[entity_id] = {
            "entity_name": entity_labels.get(entity_id, "Unknown"),
            "this_period": current_val,
            "previous_period": previous_val,
            "delta_pct": delta_pct,
        }

    logger.info(f"[UNIFIED_METRICS] Entity comparison complete: {len(result)} entities")
    return result
```

#### `backend/app/answer/visual_builder.py` (Updated)

**Changes**:
- Handle `entity_comparison` data for dual-period charts
- Add `_build_comparison_entity_chart()` method

---

## Security Design

### Threat Model

| Threat | Mitigation | Layer |
|--------|-----------|-------|
| SQL Injection | LLM outputs JSON, not SQL. SQLAlchemy parameterizes. | Compiler |
| Invalid Metrics | Allowlist validation | Security |
| Cross-tenant Data | Workspace scoping at SQL level | Execution |
| DoS via Complex Query | Query complexity limits | Validation |
| LLM Manipulation | Schema validation rejects unexpected fields | Schema |

### Security Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                       SECURITY LAYERS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: LLM Output Restriction                                │
│  ─────────────────────────────────                              │
│  • LLM outputs JSON only (not SQL)                              │
│  • JSON must match SemanticQuery schema                         │
│  • Pydantic rejects malformed JSON                              │
│                                                                 │
│  Layer 2: Allowlist Validation                                  │
│  ─────────────────────────────────                              │
│  • ALLOWED_METRICS: 24 valid metrics                            │
│  • ALLOWED_DIMENSIONS: 3 valid dimensions                       │
│  • ALLOWED_FILTER_FIELDS: 5 valid filter fields                 │
│  • ALLOWED_OPERATORS: 8 valid operators                         │
│  • Anything not in allowlist = reject                           │
│                                                                 │
│  Layer 3: Value Validation                                      │
│  ─────────────────────────────                                  │
│  • String values: Max 500 chars                                 │
│  • Numeric values: Reasonable ranges                            │
│  • Time ranges: 1-365 days                                      │
│  • Limits: 1-50 items                                           │
│                                                                 │
│  Layer 4: SQL Parameterization                                  │
│  ─────────────────────────────────                              │
│  • All values passed as parameters                              │
│  • No string concatenation                                      │
│  • SQLAlchemy ORM handles escaping                              │
│                                                                 │
│  Layer 5: Workspace Scoping                                     │
│  ──────────────────────────────                                 │
│  • Every query filtered by workspace_id                         │
│  • JWT token contains workspace claim                           │
│  • No cross-tenant data access possible                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Allowlists (Not Blocklists)

```python
# security.py

ALLOWED_METRICS = frozenset({
    "spend", "revenue", "profit", "clicks", "impressions",
    "conversions", "leads", "installs", "purchases", "visitors",
    "cpc", "cpm", "cpa", "cpl", "cpi", "cpp",
    "roas", "poas", "aov", "arpv", "ctr", "cvr"
})

ALLOWED_DIMENSIONS = frozenset({
    "entity", "provider", "time"
})

ALLOWED_ENTITY_LEVELS = frozenset({
    "campaign", "adset", "ad"
})

ALLOWED_TIME_GRANULARITIES = frozenset({
    "day", "week", "month"
})

ALLOWED_FILTER_FIELDS = frozenset({
    "provider", "level", "status", "entity_name", "entity_ids"
})

ALLOWED_OPERATORS = frozenset({
    "=", "!=", ">", "<", ">=", "<=", "in", "contains"
})

ALLOWED_PROVIDERS = frozenset({
    "google", "meta", "tiktok", "other", "mock"
})
```

---

## Observability Design

### Telemetry Events

| Event | When | Data Captured |
|-------|------|---------------|
| `query.started` | Query received | query_id, workspace_id, question_length |
| `stage.started` | Stage begins | stage_name, timestamp |
| `stage.completed` | Stage ends | duration_ms, success, error |
| `query.completed` | Query done | total_duration_ms, success |
| `query.failed` | Query error | error_type, error_message |

### Structured Logging Format

```json
{
  "timestamp": "2025-12-03T14:30:00.000Z",
  "level": "INFO",
  "service": "qa",
  "query_id": "q_abc123",
  "workspace_id": "ws_xyz789",
  "stage": "compilation",
  "duration_ms": 45.2,
  "message": "Stage completed successfully",
  "metadata": {
    "has_breakdown": true,
    "has_comparison": true,
    "entity_count": 3
  }
}
```

### Key Metrics to Track

```python
# Metrics for monitoring dashboard

METRICS = {
    # Latency
    "qa_query_duration_ms": "Histogram of total query duration",
    "qa_stage_duration_ms": "Histogram of per-stage duration",

    # Success rates
    "qa_query_success_total": "Counter of successful queries",
    "qa_query_failure_total": "Counter of failed queries",
    "qa_validation_failure_total": "Counter of validation failures",

    # Usage patterns
    "qa_metric_usage": "Counter by metric name",
    "qa_dimension_usage": "Counter by dimension",
    "qa_composition_usage": "Counter by query composition type",
}
```

---

## Testing Strategy

### Test Categories

| Category | Count | Purpose |
|----------|-------|---------|
| Unit Tests | ~100 | Individual function correctness |
| Integration Tests | ~30 | Component interaction |
| End-to-End Tests | ~20 | Full pipeline validation |
| Security Tests | ~15 | Injection and bypass attempts |
| Performance Tests | ~10 | Latency benchmarks |

### Test File Structure

```
backend/app/tests/
├── semantic/
│   ├── test_model.py           # Metric/dimension definitions
│   ├── test_query.py           # SemanticQuery dataclass
│   ├── test_validator.py       # Validation layers
│   ├── test_security.py        # Security checks
│   ├── test_compiler.py        # Query compilation
│   └── test_telemetry.py       # Telemetry collection
│
├── test_semantic_integration.py # Full pipeline tests
└── test_semantic_security.py    # Security/injection tests
```

### Critical Test Cases

```python
# test_semantic_integration.py

class TestSemanticPipeline:
    """End-to-end tests for semantic query pipeline."""

    def test_simple_metric_query(self):
        """Basic metric query works."""
        query = SemanticQuery(
            metrics=["roas"],
            time_range=TimeRange(last_n_days=7)
        )
        result = execute_query(query, workspace_id)
        assert result.summary["roas"]["value"] is not None

    def test_breakdown_with_comparison(self):
        """THE KEY TEST: Breakdown + comparison compose correctly."""
        query = SemanticQuery(
            metrics=["cpc"],
            time_range=TimeRange(last_n_days=7),
            breakdown=Breakdown(dimension="entity", level="ad", limit=3),
            comparison=Comparison(type=ComparisonType.PREVIOUS_PERIOD),
        )
        result = execute_query(query, workspace_id)

        # Should have breakdown data
        assert len(result.breakdown) == 3

        # Should have per-entity comparison (THE FIX)
        assert result.entity_comparison is not None
        assert len(result.entity_comparison) == 3

        for entity_id, comparison in result.entity_comparison.items():
            assert "this_period" in comparison
            assert "previous_period" in comparison
            assert "delta_pct" in comparison

    def test_entity_timeseries_chart(self):
        """Multi-line chart with entity breakdown."""
        query = SemanticQuery(
            metrics=["spend"],
            time_range=TimeRange(last_n_days=7),
            breakdown=Breakdown(dimension="entity", level="campaign", limit=5),
            include_timeseries=True,
        )
        result = execute_query(query, workspace_id)

        # Should have per-entity timeseries
        assert result.entity_timeseries is not None
        assert len(result.entity_timeseries) == 5

        for entity_data in result.entity_timeseries:
            assert "entity_name" in entity_data
            assert "timeseries" in entity_data
            assert len(entity_data["timeseries"]) == 7  # 7 days


class TestSecurityValidation:
    """Security-focused tests."""

    def test_invalid_metric_rejected(self):
        """Unknown metrics are rejected."""
        query = SemanticQuery(
            metrics=["fake_metric"],
            time_range=TimeRange(last_n_days=7)
        )
        result = validator.validate(query)
        assert not result.valid
        assert "metric" in result.errors[0].field

    def test_sql_injection_in_filter_value(self):
        """SQL injection attempts are safely handled."""
        query = SemanticQuery(
            metrics=["spend"],
            time_range=TimeRange(last_n_days=7),
            filters=[Filter(
                field="entity_name",
                operator="=",
                value="'; DROP TABLE metric_fact; --"
            )]
        )
        # Should not raise, should execute safely
        result = execute_query(query, workspace_id)
        # No data found, but no SQL injection
        assert result is not None

    def test_cross_workspace_isolation(self):
        """Cannot access another workspace's data."""
        query = SemanticQuery(
            metrics=["spend"],
            time_range=TimeRange(last_n_days=7)
        )
        result_ws1 = execute_query(query, "workspace_1")
        result_ws2 = execute_query(query, "workspace_2")

        # Results should be different (different workspaces)
        # More importantly, no overlap in data
```

---

## Migration Plan

### Strategy: Parallel Implementation

```
Week 1: Build semantic layer (parallel to existing DSL)
Week 2: Integrate semantic layer (route complex queries)
Week 3: Test, polish, remove DSL
```

### Detailed Steps

#### Step 1: Create Parallel Path

```python
# qa_service.py

async def process_question(self, question: str, ...):
    # Existing path (keep working)
    if not settings.USE_SEMANTIC_LAYER:
        return await self._process_dsl_path(question, ...)

    # New path (gradual rollout)
    return await self._process_semantic_path(question, ...)
```

#### Step 2: Feature Flag Rollout

```python
# deps.py

class Settings:
    USE_SEMANTIC_LAYER: bool = False  # Start disabled
    SEMANTIC_LAYER_PERCENTAGE: int = 0  # Gradual rollout
```

```python
# qa_service.py

def should_use_semantic_layer(self, workspace_id: str) -> bool:
    """Determine if this request should use semantic layer."""
    if not settings.USE_SEMANTIC_LAYER:
        return False

    # Gradual rollout by workspace hash
    workspace_hash = hash(workspace_id) % 100
    return workspace_hash < settings.SEMANTIC_LAYER_PERCENTAGE
```

#### Step 3: A/B Testing (Optional)

```python
# Compare DSL vs Semantic results for same queries
# Log any discrepancies for analysis

async def _process_with_comparison(self, question, workspace_id):
    dsl_result = await self._process_dsl_path(question, workspace_id)
    semantic_result = await self._process_semantic_path(question, workspace_id)

    if dsl_result.answer != semantic_result.answer:
        logger.warning(
            "[MIGRATION] Result mismatch",
            extra={
                "question": question,
                "dsl_answer": dsl_result.answer,
                "semantic_answer": semantic_result.answer,
            }
        )

    return semantic_result  # Use new path
```

#### Step 4: Full Cutover

```python
# After validation, remove DSL path

# 1. Set USE_SEMANTIC_LAYER = True permanently
# 2. Remove _process_dsl_path method
# 3. Remove old DSL executor code
# 4. Update documentation
```

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance regression | Medium | High | Benchmark before/after, optimize hot paths |
| LLM translation errors | Medium | Medium | Keep few-shot examples, add retry logic |
| Missing edge cases | Medium | Medium | Comprehensive test suite, gradual rollout |
| Integration bugs | Low | High | Parallel implementation, A/B testing |

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Extended development time | Medium | Medium | Clear phases, daily progress checks |
| Scope creep | Medium | Medium | Strict phase boundaries, defer enhancements |
| Breaking existing tests | Low | Medium | Run tests continuously during development |

### Rollback Plan

```
If critical issues discovered:
1. Set USE_SEMANTIC_LAYER = False (instant rollback)
2. Old DSL path takes over immediately
3. Debug issues in semantic layer
4. Fix and re-enable gradually
```

---

## Success Criteria

### Functional Requirements

- [ ] Simple queries work (metric + time_range)
- [ ] Breakdown queries work (metric + breakdown)
- [ ] Comparison queries work (metric + comparison)
- [ ] **Composed queries work (breakdown + comparison)** ← KEY
- [ ] Multi-metric queries work
- [ ] Filter queries work
- [ ] Entity name filtering works
- [ ] Follow-up queries work (context resolution)

### Non-Functional Requirements

- [ ] P95 latency < 3 seconds
- [ ] All existing tests pass
- [ ] 100+ new tests added
- [ ] Zero security vulnerabilities
- [ ] Full telemetry coverage
- [ ] Documentation updated

### User Experience

- [ ] "compare CPC this week vs last week for top 3 ads" produces correct chart
- [ ] Error messages are helpful (not technical)
- [ ] No regressions in existing query types

---

## Timeline

### Week 1: Foundation + Validation + Compiler Core

| Day | Tasks | Deliverables |
|-----|-------|-------------|
| 1 | Create semantic/ folder, model.py | Metric/dimension definitions |
| 2 | Implement query.py | SemanticQuery dataclass |
| 3 | Implement security.py | SecurityValidator |
| 4 | Implement validator.py | SemanticValidator |
| 5 | Start compiler.py | Basic structure |

### Week 2: Compiler + Integration

| Day | Tasks | Deliverables |
|-----|-------|-------------|
| 6 | Compiler: summary + breakdown | Basic compilation |
| 7 | Compiler: comparison + entity_comparison | **KEY FEATURE** |
| 8 | Compiler: timeseries + entity_timeseries | Multi-line charts |
| 9 | Telemetry implementation | Full observability |
| 10 | Update prompts.py + translator.py | Semantic format |

### Week 3: Integration + Testing + Polish

| Day | Tasks | Deliverables |
|-----|-------|-------------|
| 11 | Update qa_service.py + executor.py | Integration |
| 12 | Update visual_builder.py + answer_builder.py | New data structures |
| 13 | Comprehensive testing | 100+ tests |
| 14 | Performance benchmarks | Latency baseline |
| 15 | Documentation + cleanup | Ready for review |

---

## Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| Semantic Layer | Abstraction between natural language and database queries |
| DSL | Domain-Specific Language (current rigid query format) |
| Composition | Combining multiple query components (breakdown + comparison) |
| Compilation | Translating semantic query to database operations |

### B. Related Documentation

- [QA System Architecture](./QA_SYSTEM_ARCHITECTURE.md)
- [Metrics Registry](../../backend/app/metrics/README.md)
- [CLAUDE.md Project Guidelines](../../.claude/CLAUDE.md)

### C. External References

- [Cube.js Semantic Layer](https://cube.dev/docs/product/data-modeling/concepts)
- [dbt Semantic Layer](https://docs.getdbt.com/docs/build/about-metricflow)
- [LangChain SQL Agent](https://python.langchain.com/docs/tutorials/sql_qa/)

### D. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-03 | Choose Semantic Layer over Text-to-SQL | Safety (no raw SQL from LLM) + Maintainability |
| 2025-12-03 | Keep SQLAlchemy ORM | Parameterized queries, existing codebase |
| 2025-12-03 | Parallel implementation strategy | Zero downtime, easy rollback |

---

## Approval

- [ ] Technical Lead Review
- [ ] Security Review
- [ ] Product Owner Sign-off

---

*Last Updated: 2025-12-03*
