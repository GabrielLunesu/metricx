"""
Semantic Query Compiler
=======================

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Active

Translates validated SemanticQuery objects into actual data retrieval.
This is the "execution engine" of the semantic layer.

WHY THIS FILE EXISTS
--------------------
The SemanticQuery (app/semantic/query.py) defines WHAT to query.
The UnifiedMetricService (app/services/unified_metric_service.py) knows HOW to query.
This compiler bridges them: it translates semantic intent into service calls.

THE KEY FEATURE: ENTITY COMPARISON
----------------------------------
This compiler implements the feature that was impossible with the old DSL:

    breakdown (entity) + comparison = per-entity comparison data

This enables queries like:
    "compare CPC this week vs last week for top 3 ads"

Which requires:
    1. Get top 3 ads by CPC for current period
    2. Get the SAME ads' CPC for previous period
    3. Combine into comparison data structure

Previously, DSL had mutually exclusive fields (breakdown OR compare_to_previous).
Now, these compose freely.

COMPILATION STRATEGIES
----------------------
The compiler uses different strategies based on query composition:

1. Summary: Just metrics → get_summary()
2. Breakdown: Metrics + breakdown → get_breakdown()
3. Comparison: Metrics + comparison → get_summary(compare=True)
4. Entity Comparison: Breakdown + comparison → get_entity_comparison() [KEY!]
5. Timeseries: Metrics + timeseries → get_timeseries()
6. Entity Timeseries: Breakdown + timeseries → get_entity_timeseries()
7. Provider Breakdown: Breakdown by provider → get_breakdown(provider)
8. Time Breakdown: Breakdown by time → get_time_based_breakdown()

RELATED FILES
-------------
- app/semantic/query.py: Input - SemanticQuery structure
- app/semantic/validator.py: Validates queries before compilation
- app/services/unified_metric_service.py: Data retrieval (called by compiler)
- app/dsl/schema.py: OLD - TimeRange used for compatibility
- app/qa/qa_service.py: Uses compiler results for answers
- docs/living-docs/SEMANTIC_LAYER_IMPLEMENTATION_PLAN.md: Full plan
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field as dataclass_field
from datetime import date, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from app.semantic.query import (
    SemanticQuery,
    TimeRange as SemanticTimeRange,
    Comparison,
    ComparisonType,
)
from app.semantic.model import get_metric, is_inverse_metric, METRICS
from app.services.unified_metric_service import (
    UnifiedMetricService,
    MetricFilters,
    MetricValue,
    MetricSummary,
    MetricBreakdownItem,
    MetricTimePoint,
)
from app.dsl.schema import TimeRange as DslTimeRange

logger = logging.getLogger(__name__)


# =============================================================================
# RESULT DATA STRUCTURES
# =============================================================================

@dataclass
class EntityComparisonItem:
    """
    Single entity's comparison data.

    WHAT: Contains both current and previous period values for one entity.

    WHY: This is THE KEY FEATURE that was missing - per-entity comparison.
    E.g., "Ad A: $1.50 CPC this week, $1.80 last week (-17%)"

    PARAMETERS:
        entity_id: UUID of the entity (for further lookups)
        entity_name: Display name of the entity
        current_value: Metric value for current period
        previous_value: Metric value for previous period
        delta_pct: Percentage change ((current - previous) / previous)
        current_bases: Raw base measures for current period (for secondary metrics)
        previous_bases: Raw base measures for previous period

    EXAMPLE:
        EntityComparisonItem(
            entity_id="uuid-123",
            entity_name="Summer Sale Ad",
            current_value=1.50,
            previous_value=1.80,
            delta_pct=-0.1667,  # -16.67%
            current_bases={"spend": 150, "clicks": 100},
            previous_bases={"spend": 180, "clicks": 100}
        )
    """
    entity_id: str
    entity_name: str
    current_value: Optional[float]
    previous_value: Optional[float]
    delta_pct: Optional[float]
    # Raw base measures for calculating secondary metrics
    current_bases: Dict[str, float] = dataclass_field(default_factory=dict)
    previous_bases: Dict[str, float] = dataclass_field(default_factory=dict)


@dataclass
class EntityTimeseriesItem:
    """
    Single entity's timeseries data.

    WHAT: Contains daily values for one entity (for multi-line charts).

    WHY: Enables queries like "graph daily CPC for top 3 campaigns"
    where each entity becomes a separate line.

    PARAMETERS:
        entity_id: UUID of the entity
        entity_name: Display name (used as line label)
        timeseries: List of date/value points

    EXAMPLE:
        EntityTimeseriesItem(
            entity_id="uuid-123",
            entity_name="Summer Sale",
            timeseries=[
                {"date": "2025-11-20", "value": 1.50},
                {"date": "2025-11-21", "value": 1.45},
                ...
            ]
        )
    """
    entity_id: str
    entity_name: str
    timeseries: List[Dict[str, Any]]


@dataclass
class CompilationResult:
    """
    Result of compiling and executing a SemanticQuery.

    WHAT: Contains all data needed to build an answer.

    WHY: Provides a consistent interface for the answer builder,
    regardless of which compilation strategy was used.

    STRUCTURE:
        The result contains different fields based on query type:

        - summary: Aggregate metrics (always present)
        - breakdown: Per-entity/provider metrics (if breakdown requested)
        - comparison: Period-over-period data (if comparison requested)
        - entity_comparison: Per-entity comparison (if breakdown + comparison)
        - timeseries: Daily data (if timeseries requested)
        - entity_timeseries: Per-entity daily data (if breakdown + timeseries)

    METADATA:
        - query: Original SemanticQuery (for reference)
        - compilation_strategy: Which strategy was used
        - time_range_resolved: Actual dates used (after resolving relative ranges)
        - workspace_avg: Workspace average for primary metric (for context)

    EXAMPLE:
        # Simple summary query
        result.summary = {"roas": MetricValue(value=6.5)}
        result.comparison = None
        result.entity_comparison = None

        # Entity comparison query (THE KEY FEATURE)
        result.summary = {"cpc": MetricValue(value=1.50, previous=1.80, delta_pct=-0.17)}
        result.entity_comparison = [
            EntityComparisonItem(name="Ad A", current=1.50, previous=1.80, ...),
            EntityComparisonItem(name="Ad B", current=2.00, previous=1.90, ...),
        ]
    """
    # Core data
    summary: Dict[str, MetricValue] = dataclass_field(default_factory=dict)
    breakdown: List[MetricBreakdownItem] = dataclass_field(default_factory=list)

    # Comparison data
    comparison: Optional[Dict[str, MetricValue]] = None  # Overall comparison
    entity_comparison: Optional[List[EntityComparisonItem]] = None  # Per-entity comparison (KEY!)

    # Timeseries data
    timeseries: Dict[str, List[MetricTimePoint]] = dataclass_field(default_factory=dict)
    entity_timeseries: Optional[List[EntityTimeseriesItem]] = None  # Per-entity timeseries

    # Metadata
    query: Optional[SemanticQuery] = None
    compilation_strategy: str = "unknown"
    time_range_resolved: Optional[Dict[str, str]] = None
    workspace_avg: Optional[float] = None

    def has_breakdown(self) -> bool:
        """Check if result contains breakdown data."""
        return len(self.breakdown) > 0

    def has_entity_comparison(self) -> bool:
        """Check if result contains per-entity comparison data (THE KEY FEATURE)."""
        return self.entity_comparison is not None and len(self.entity_comparison) > 0

    def has_entity_timeseries(self) -> bool:
        """Check if result contains per-entity timeseries data."""
        return self.entity_timeseries is not None and len(self.entity_timeseries) > 0

    def has_timeseries(self) -> bool:
        """Check if result contains any timeseries data."""
        return len(self.timeseries) > 0

    def get_primary_metric_value(self) -> Optional[float]:
        """Get the value of the first metric in summary."""
        if self.summary:
            first_key = next(iter(self.summary))
            return self.summary[first_key].value
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        RETURNS:
            Dict representation suitable for API response
        """
        result = {
            "compilation_strategy": self.compilation_strategy,
            "time_range_resolved": self.time_range_resolved,
            "workspace_avg": self.workspace_avg,
        }

        # Summary
        if self.summary:
            result["summary"] = {
                k: {
                    "value": v.value,
                    "previous": v.previous,
                    "delta_pct": v.delta_pct,
                }
                for k, v in self.summary.items()
            }

        # Breakdown
        if self.breakdown:
            result["breakdown"] = [
                {
                    "label": item.label,
                    "value": item.value,
                    "entity_id": item.entity_id,
                    "spend": item.spend,
                    "revenue": item.revenue,
                    "clicks": item.clicks,
                    "impressions": item.impressions,
                    "conversions": item.conversions,
                }
                for item in self.breakdown
            ]

        # Entity comparison (THE KEY FEATURE)
        if self.entity_comparison:
            result["entity_comparison"] = [
                {
                    "entity_id": item.entity_id,
                    "entity_name": item.entity_name,
                    "current_value": item.current_value,
                    "previous_value": item.previous_value,
                    "delta_pct": item.delta_pct,
                }
                for item in self.entity_comparison
            ]

        # Timeseries
        if self.timeseries:
            result["timeseries"] = {
                k: [{"date": p.date, "value": p.value} for p in v]
                for k, v in self.timeseries.items()
            }

        # Entity timeseries
        if self.entity_timeseries:
            result["entity_timeseries"] = [
                {
                    "entity_id": item.entity_id,
                    "entity_name": item.entity_name,
                    "timeseries": item.timeseries,
                }
                for item in self.entity_timeseries
            ]

        return result


# =============================================================================
# COMPILER IMPLEMENTATION
# =============================================================================

class SemanticCompiler:
    """
    Compiles SemanticQuery to actual data.

    WHAT: The execution engine for semantic queries.

    WHY: Separates query intent (SemanticQuery) from execution (UnifiedMetricService).
    This enables:
    - Clear responsibility boundaries
    - Easy testing (mock the service)
    - Future optimizations (batching, caching)

    USAGE:
        compiler = SemanticCompiler(db)
        result = compiler.compile(workspace_id, validated_query)

    COMPOSITION DETECTION:
        The compiler automatically detects query composition and chooses
        the appropriate strategy:

        - needs_entity_comparison() → compile_entity_comparison()
        - needs_entity_timeseries() → compile_entity_timeseries()
        - needs_provider_breakdown() → compile_provider_breakdown()
        - needs_time_breakdown() → compile_time_breakdown()
        - has_breakdown() → compile_breakdown()
        - has_comparison() → compile_comparison()
        - has_timeseries() → compile_timeseries()
        - else → compile_summary()

    RELATED:
        - app/semantic/query.py: SemanticQuery.needs_entity_comparison()
        - app/services/unified_metric_service.py: Actual data fetching
    """

    def __init__(self, db: Session):
        """
        Initialize compiler with database session.

        PARAMETERS:
            db: SQLAlchemy session for data access

        EXAMPLE:
            from sqlalchemy.orm import Session
            compiler = SemanticCompiler(db)
        """
        self.db = db
        self.service = UnifiedMetricService(db)

    def compile(self, workspace_id: str, query: SemanticQuery) -> CompilationResult:
        """
        Compile and execute a SemanticQuery.

        WHAT: Main entry point - detects query type and routes to appropriate strategy.

        WHY: Single method interface simplifies usage while handling all query variants.

        PARAMETERS:
            workspace_id: UUID of the workspace (security scope)
            query: Validated SemanticQuery object

        RETURNS:
            CompilationResult with all requested data

        RAISES:
            ValueError: If query is malformed
            RuntimeError: If database operation fails

        EXAMPLE:
            result = compiler.compile(workspace_id, SemanticQuery(
                metrics=["cpc"],
                time_range=TimeRange(last_n_days=7),
                breakdown=Breakdown(dimension="entity", level="ad", limit=3),
                comparison=Comparison(type=ComparisonType.PREVIOUS_PERIOD)
            ))
            # Result includes entity_comparison data

        STRATEGY SELECTION:
            1. Entity comparison: breakdown.entity + comparison → per-entity comparison
            2. Entity timeseries: breakdown.entity + timeseries → multi-line chart
            3. Provider breakdown: breakdown.provider → by platform
            4. Time breakdown: breakdown.time → by day/week/month
            5. Entity breakdown: breakdown.entity → top N entities
            6. Comparison only: comparison → period-over-period
            7. Timeseries only: timeseries → daily trend
            8. Summary: none of above → simple aggregates
        """
        logger.info(f"[COMPILER] Compiling query: {query.describe()}")

        # Resolve time range for metadata
        time_range_resolved = self._resolve_time_range_dict(query.time_range)

        # Initialize result
        result = CompilationResult(
            query=query,
            time_range_resolved=time_range_resolved,
        )

        # Convert semantic filters to MetricFilters
        filters = self._build_filters(query)

        # Choose compilation strategy based on query composition
        # Order matters: most specific first

        if query.needs_entity_comparison():
            # THE KEY FEATURE: breakdown + comparison
            logger.info("[COMPILER] Strategy: entity_comparison (breakdown + comparison)")
            result.compilation_strategy = "entity_comparison"
            self._compile_entity_comparison(workspace_id, query, filters, result)

        elif query.needs_entity_timeseries():
            # breakdown + timeseries = multi-line chart
            logger.info("[COMPILER] Strategy: entity_timeseries (breakdown + timeseries)")
            result.compilation_strategy = "entity_timeseries"
            self._compile_entity_timeseries(workspace_id, query, filters, result)

        elif query.needs_provider_breakdown():
            # breakdown by provider
            logger.info("[COMPILER] Strategy: provider_breakdown")
            result.compilation_strategy = "provider_breakdown"
            self._compile_provider_breakdown(workspace_id, query, filters, result)

        elif query.needs_time_breakdown():
            # breakdown by time (day/week/month)
            logger.info("[COMPILER] Strategy: time_breakdown")
            result.compilation_strategy = "time_breakdown"
            self._compile_time_breakdown(workspace_id, query, filters, result)

        elif query.has_breakdown():
            # Entity breakdown without comparison/timeseries
            logger.info("[COMPILER] Strategy: entity_breakdown")
            result.compilation_strategy = "entity_breakdown"
            self._compile_entity_breakdown(workspace_id, query, filters, result)

        elif query.has_comparison():
            # Comparison without breakdown
            logger.info("[COMPILER] Strategy: comparison")
            result.compilation_strategy = "comparison"
            self._compile_comparison(workspace_id, query, filters, result)

        elif query.include_timeseries:
            # Timeseries without breakdown
            logger.info("[COMPILER] Strategy: timeseries")
            result.compilation_strategy = "timeseries"
            self._compile_timeseries(workspace_id, query, filters, result)

        else:
            # Simple summary
            logger.info("[COMPILER] Strategy: summary")
            result.compilation_strategy = "summary"
            self._compile_summary(workspace_id, query, filters, result)

        # Get workspace average for context (always useful)
        if query.metrics:
            result.workspace_avg = self.service.get_workspace_average(
                workspace_id=workspace_id,
                metric=query.get_primary_metric(),
                time_range=self._to_dsl_time_range(query.time_range),
            )

        logger.info(f"[COMPILER] Compilation complete: strategy={result.compilation_strategy}")
        return result

    # -------------------------------------------------------------------------
    # Compilation Strategies
    # -------------------------------------------------------------------------

    def _compile_summary(
        self,
        workspace_id: str,
        query: SemanticQuery,
        filters: MetricFilters,
        result: CompilationResult,
    ) -> None:
        """
        Compile simple summary query.

        WHAT: Get aggregate values for metrics without grouping.

        WHY: Answers questions like "What's my ROAS?" or "Total spend?"

        EXAMPLE:
            Query: metrics=["roas", "spend"], last_7_days
            Result: {roas: 6.5, spend: 10000}
        """
        logger.info(f"[COMPILER] Compiling summary for metrics: {query.metrics}")

        summary = self.service.get_summary(
            workspace_id=workspace_id,
            metrics=query.metrics,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            compare_to_previous=False,
        )

        result.summary = summary.metrics

    def _compile_comparison(
        self,
        workspace_id: str,
        query: SemanticQuery,
        filters: MetricFilters,
        result: CompilationResult,
    ) -> None:
        """
        Compile comparison query (period-over-period).

        WHAT: Get metrics for current AND previous period.

        WHY: Answers questions like "How does this week compare to last week?"

        EXAMPLE:
            Query: metrics=["roas"], last_7_days, comparison=previous_period
            Result: {roas: {value: 6.5, previous: 5.8, delta_pct: 0.12}}
        """
        logger.info(f"[COMPILER] Compiling comparison for metrics: {query.metrics}")

        summary = self.service.get_summary(
            workspace_id=workspace_id,
            metrics=query.metrics,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            compare_to_previous=True,
        )

        result.summary = summary.metrics
        result.comparison = summary.metrics  # Same data, explicit comparison field

    def _compile_entity_breakdown(
        self,
        workspace_id: str,
        query: SemanticQuery,
        filters: MetricFilters,
        result: CompilationResult,
    ) -> None:
        """
        Compile entity breakdown query.

        WHAT: Get metrics grouped by campaign/adset/ad.

        WHY: Answers questions like "Top 5 campaigns by ROAS"

        EXAMPLE:
            Query: metrics=["roas"], breakdown={entity, campaign, limit=5}
            Result: breakdown=[
                {label: "Summer Sale", value: 8.5},
                {label: "Winter Promo", value: 7.2},
                ...
            ]
        """
        logger.info(f"[COMPILER] Compiling entity breakdown: level={query.breakdown.level}")

        # First get summary
        summary = self.service.get_summary(
            workspace_id=workspace_id,
            metrics=query.metrics,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            compare_to_previous=query.has_comparison(),
        )
        result.summary = summary.metrics

        # Then get breakdown
        primary_metric = query.get_primary_metric()
        breakdown = self.service.get_breakdown(
            workspace_id=workspace_id,
            metric=primary_metric,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            breakdown_dimension=query.breakdown.level,
            top_n=query.breakdown.limit,
            sort_order=query.breakdown.sort_order,
        )

        result.breakdown = breakdown

    def _compile_entity_comparison(
        self,
        workspace_id: str,
        query: SemanticQuery,
        filters: MetricFilters,
        result: CompilationResult,
    ) -> None:
        """
        Compile entity comparison query - THE KEY FEATURE.

        WHAT: Get per-entity comparison data (breakdown + comparison combined).

        WHY: This is what was IMPOSSIBLE with the old DSL!
        Answers questions like "Compare CPC for top 3 ads this week vs last week"

        ALGORITHM:
            1. Get top N entities for CURRENT period (ranked by metric)
            2. Get the SAME entities' data for PREVIOUS period
            3. Combine into EntityComparisonItem objects with delta calculation

        EXAMPLE:
            Query: metrics=["cpc"], breakdown={entity, ad, limit=3}, comparison=previous_period
            Result: entity_comparison=[
                {name: "Ad A", current: 1.50, previous: 1.80, delta: -17%},
                {name: "Ad B", current: 2.00, previous: 1.90, delta: +5%},
                {name: "Ad C", current: 1.20, previous: 1.30, delta: -8%},
            ]
        """
        logger.info("[COMPILER] Compiling ENTITY COMPARISON (THE KEY FEATURE)")
        logger.info(f"[COMPILER] Breakdown: {query.breakdown.level}, limit={query.breakdown.limit}")

        primary_metric = query.get_primary_metric()

        # Step 1: Get overall summary with comparison
        summary = self.service.get_summary(
            workspace_id=workspace_id,
            metrics=query.metrics,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            compare_to_previous=True,
        )
        result.summary = summary.metrics
        result.comparison = summary.metrics

        # Step 2: Get top N entities for CURRENT period
        current_breakdown = self.service.get_breakdown(
            workspace_id=workspace_id,
            metric=primary_metric,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            breakdown_dimension=query.breakdown.level,
            top_n=query.breakdown.limit,
            sort_order=query.breakdown.sort_order,
        )
        result.breakdown = current_breakdown

        if not current_breakdown:
            logger.warning("[COMPILER] No entities found for current period")
            result.entity_comparison = []
            return

        # Step 3: Calculate previous period dates
        current_start, current_end = self._resolve_time_range(query.time_range)
        period_days = (current_end - current_start).days + 1
        prev_end = current_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days - 1)

        logger.info(f"[COMPILER] Current period: {current_start} to {current_end}")
        logger.info(f"[COMPILER] Previous period: {prev_start} to {prev_end}")

        # Step 4: Get the SAME entities' data for previous period
        entity_ids = [item.entity_id for item in current_breakdown if item.entity_id]
        entity_labels = {item.entity_id: item.label for item in current_breakdown if item.entity_id}

        if not entity_ids:
            logger.warning("[COMPILER] No entity IDs in breakdown, cannot get previous period")
            result.entity_comparison = []
            return

        # Create filters for specific entities
        prev_filters = MetricFilters(
            provider=filters.provider,
            status=filters.status,
            entity_ids=entity_ids,  # Only these specific entities
        )

        prev_time_range = DslTimeRange(start=prev_start, end=prev_end)

        # Get previous period breakdown for the same entities
        prev_breakdown = self.service.get_breakdown(
            workspace_id=workspace_id,
            metric=primary_metric,
            time_range=prev_time_range,
            filters=prev_filters,
            breakdown_dimension=query.breakdown.level,
            top_n=len(entity_ids),  # Get all of them
            sort_order=query.breakdown.sort_order,
        )

        # Step 5: Build lookup for previous values
        prev_by_id = {item.entity_id: item for item in prev_breakdown if item.entity_id}

        # Step 6: Combine into EntityComparisonItem objects
        entity_comparison = []
        for current_item in current_breakdown:
            entity_id = current_item.entity_id
            if not entity_id:
                continue

            prev_item = prev_by_id.get(entity_id)
            current_value = current_item.value
            previous_value = prev_item.value if prev_item else None

            # Calculate delta percentage
            delta_pct = None
            if previous_value is not None and previous_value != 0 and current_value is not None:
                delta_pct = (current_value - previous_value) / previous_value

            entity_comparison.append(EntityComparisonItem(
                entity_id=entity_id,
                entity_name=current_item.label,
                current_value=current_value,
                previous_value=previous_value,
                delta_pct=delta_pct,
                current_bases={
                    "spend": current_item.spend,
                    "revenue": current_item.revenue,
                    "clicks": current_item.clicks,
                    "impressions": current_item.impressions,
                    "conversions": current_item.conversions,
                },
                previous_bases={
                    "spend": prev_item.spend if prev_item else None,
                    "revenue": prev_item.revenue if prev_item else None,
                    "clicks": prev_item.clicks if prev_item else None,
                    "impressions": prev_item.impressions if prev_item else None,
                    "conversions": prev_item.conversions if prev_item else None,
                } if prev_item else {},
            ))

        result.entity_comparison = entity_comparison
        logger.info(f"[COMPILER] Built {len(entity_comparison)} entity comparison items")

    def _compile_entity_timeseries(
        self,
        workspace_id: str,
        query: SemanticQuery,
        filters: MetricFilters,
        result: CompilationResult,
    ) -> None:
        """
        Compile entity timeseries query.

        WHAT: Get daily data for each entity (for multi-line charts).

        WHY: Answers questions like "Show daily CPC for top 3 campaigns"
        where each entity becomes a separate line on the chart.

        ALGORITHM:
            1. Get top N entities (ranked by metric)
            2. Get daily timeseries for EACH entity separately
            3. Return as list of EntityTimeseriesItem

        EXAMPLE:
            Query: metrics=["cpc"], breakdown={entity, campaign, limit=3}, timeseries=true
            Result: entity_timeseries=[
                {name: "Campaign A", timeseries: [{date: "2025-11-20", value: 1.50}, ...]},
                {name: "Campaign B", timeseries: [{date: "2025-11-20", value: 2.00}, ...]},
                {name: "Campaign C", timeseries: [{date: "2025-11-20", value: 1.20}, ...]},
            ]
        """
        logger.info("[COMPILER] Compiling entity timeseries (multi-line chart)")

        primary_metric = query.get_primary_metric()

        # Step 1: Get summary
        summary = self.service.get_summary(
            workspace_id=workspace_id,
            metrics=query.metrics,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            compare_to_previous=query.has_comparison(),
        )
        result.summary = summary.metrics

        # Step 2: Get top N entities
        breakdown = self.service.get_breakdown(
            workspace_id=workspace_id,
            metric=primary_metric,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            breakdown_dimension=query.breakdown.level,
            top_n=query.breakdown.limit,
            sort_order=query.breakdown.sort_order,
        )
        result.breakdown = breakdown

        if not breakdown:
            logger.warning("[COMPILER] No entities found for timeseries")
            result.entity_timeseries = []
            return

        # Step 3: Get timeseries for each entity
        entity_ids = [item.entity_id for item in breakdown if item.entity_id]
        entity_labels = {item.entity_id: item.label for item in breakdown if item.entity_id}

        if not entity_ids:
            logger.warning("[COMPILER] No entity IDs in breakdown")
            result.entity_timeseries = []
            return

        # Use service method for entity timeseries
        timeseries_data = self.service.get_entity_timeseries(
            workspace_id=workspace_id,
            metric=primary_metric,
            time_range=self._to_dsl_time_range(query.time_range),
            entity_ids=entity_ids,
            entity_labels=entity_labels,
            granularity="day",
        )

        # Convert to EntityTimeseriesItem
        entity_timeseries = []
        for item in timeseries_data:
            entity_timeseries.append(EntityTimeseriesItem(
                entity_id=item["entity_id"],
                entity_name=item["entity_name"],
                timeseries=item["timeseries"],
            ))

        result.entity_timeseries = entity_timeseries
        logger.info(f"[COMPILER] Built {len(entity_timeseries)} entity timeseries")

    def _compile_provider_breakdown(
        self,
        workspace_id: str,
        query: SemanticQuery,
        filters: MetricFilters,
        result: CompilationResult,
    ) -> None:
        """
        Compile provider breakdown query.

        WHAT: Get metrics grouped by platform (google, meta, tiktok).

        WHY: Answers questions like "How much did I spend on each platform?"

        EXAMPLE:
            Query: metrics=["spend"], breakdown={provider}
            Result: breakdown=[
                {label: "meta", value: 5000},
                {label: "google", value: 3000},
                {label: "tiktok", value: 2000},
            ]
        """
        logger.info("[COMPILER] Compiling provider breakdown")

        # Get summary
        summary = self.service.get_summary(
            workspace_id=workspace_id,
            metrics=query.metrics,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            compare_to_previous=query.has_comparison(),
        )
        result.summary = summary.metrics

        # Get provider breakdown
        primary_metric = query.get_primary_metric()
        breakdown = self.service.get_breakdown(
            workspace_id=workspace_id,
            metric=primary_metric,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            breakdown_dimension="provider",
            top_n=10,  # There are only a few providers
            sort_order=query.breakdown.sort_order if query.breakdown else "desc",
        )

        result.breakdown = breakdown

    def _compile_time_breakdown(
        self,
        workspace_id: str,
        query: SemanticQuery,
        filters: MetricFilters,
        result: CompilationResult,
    ) -> None:
        """
        Compile time breakdown query.

        WHAT: Get metrics grouped by time (day, week, month).

        WHY: Answers questions like "Show me weekly spend"

        EXAMPLE:
            Query: metrics=["spend"], breakdown={time, granularity=week}
            Result: breakdown=[
                {label: "2025-11-04", value: 3000},  # Week 1
                {label: "2025-11-11", value: 3500},  # Week 2
                ...
            ]
        """
        logger.info(f"[COMPILER] Compiling time breakdown: granularity={query.breakdown.granularity}")

        # Get summary
        summary = self.service.get_summary(
            workspace_id=workspace_id,
            metrics=query.metrics,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            compare_to_previous=query.has_comparison(),
        )
        result.summary = summary.metrics

        # Get time-based breakdown
        primary_metric = query.get_primary_metric()
        granularity = query.breakdown.granularity or "day"

        breakdown = self.service.get_time_based_breakdown(
            workspace_id=workspace_id,
            metric=primary_metric,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            breakdown_dimension=granularity,
            top_n=100,  # Get all time buckets
            sort_order="asc",  # Time should be chronological
        )

        result.breakdown = breakdown

    def _compile_timeseries(
        self,
        workspace_id: str,
        query: SemanticQuery,
        filters: MetricFilters,
        result: CompilationResult,
    ) -> None:
        """
        Compile timeseries query (no breakdown).

        WHAT: Get daily values for metrics.

        WHY: Answers questions like "Show me daily ROAS trend"

        EXAMPLE:
            Query: metrics=["roas"], last_7_days, timeseries=true
            Result: timeseries={
                "roas": [
                    {date: "2025-11-20", value: 6.2},
                    {date: "2025-11-21", value: 6.5},
                    ...
                ]
            }
        """
        logger.info("[COMPILER] Compiling timeseries")
        logger.info(f"[COMPILER] Metrics: {query.metrics}, time_range: {query.time_range.to_dict()}")

        # Get summary with comparison if requested
        summary = self.service.get_summary(
            workspace_id=workspace_id,
            metrics=query.metrics,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            compare_to_previous=query.has_comparison(),
        )
        result.summary = summary.metrics
        logger.info(f"[COMPILER] Summary retrieved: {list(summary.metrics.keys())}")

        # Get timeseries data
        include_previous = (
            query.has_comparison()
            and query.comparison.include_timeseries
        )

        timeseries = self.service.get_timeseries(
            workspace_id=workspace_id,
            metrics=query.metrics,
            time_range=self._to_dsl_time_range(query.time_range),
            filters=filters,
            granularity="day",
            include_previous=include_previous,
        )

        result.timeseries = timeseries
        logger.info(f"[COMPILER] Timeseries retrieved: {list(timeseries.keys())}")
        for metric, points in timeseries.items():
            logger.info(f"[COMPILER] Timeseries {metric}: {len(points)} data points")

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _build_filters(self, query: SemanticQuery) -> MetricFilters:
        """
        Convert SemanticQuery filters to MetricFilters.

        WHAT: Translates semantic filters to the service contract.

        WHY: SemanticQuery uses a composable Filter structure,
        while UnifiedMetricService uses MetricFilters dataclass.

        PARAMETERS:
            query: SemanticQuery with optional filters

        RETURNS:
            MetricFilters object for service calls
        """
        filters = MetricFilters()

        for f in query.filters:
            if f.field == "provider":
                filters.provider = f.value
            elif f.field == "level":
                filters.level = f.value
            elif f.field == "status":
                filters.status = f.value
            elif f.field == "entity_name":
                filters.entity_name = f.value
            elif f.field == "entity_id":
                if isinstance(f.value, list):
                    filters.entity_ids = f.value
                else:
                    filters.entity_ids = [f.value]

        return filters

    def _to_dsl_time_range(self, time_range: SemanticTimeRange) -> DslTimeRange:
        """
        Convert SemanticTimeRange to DslTimeRange.

        WHAT: Bridge between semantic and existing DSL time range types.

        WHY: UnifiedMetricService uses DslTimeRange (from app/dsl/schema.py).
        We keep using it for compatibility until full migration.

        PARAMETERS:
            time_range: SemanticTimeRange from query

        RETURNS:
            DslTimeRange for service calls
        """
        if time_range.last_n_days:
            return DslTimeRange(last_n_days=time_range.last_n_days)
        else:
            return DslTimeRange(start=time_range.start, end=time_range.end)

    def _resolve_time_range(self, time_range: SemanticTimeRange) -> tuple[date, date]:
        """
        Resolve semantic time range to actual dates.

        RETURNS:
            Tuple of (start_date, end_date)
        """
        if time_range.start and time_range.end:
            return (time_range.start, time_range.end)

        n = time_range.last_n_days or 7
        end_date = date.today()
        start_date = end_date - timedelta(days=n - 1)
        return (start_date, end_date)

    def _resolve_time_range_dict(self, time_range: SemanticTimeRange) -> Dict[str, str]:
        """
        Resolve time range to dictionary for metadata.

        RETURNS:
            Dict with start and end ISO date strings
        """
        start, end = self._resolve_time_range(time_range)
        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
        }


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def compile_query(
    db: Session,
    workspace_id: str,
    query: SemanticQuery,
) -> CompilationResult:
    """
    Convenience function to compile a SemanticQuery.

    WHAT: One-liner for compiling queries without instantiating compiler.

    WHY: Cleaner API for callers who don't need to reuse the compiler.

    PARAMETERS:
        db: SQLAlchemy database session
        workspace_id: UUID of the workspace
        query: Validated SemanticQuery

    RETURNS:
        CompilationResult with all data

    EXAMPLE:
        from app.semantic.compiler import compile_query

        result = compile_query(db, workspace_id, query)
        print(result.summary["roas"].value)
    """
    compiler = SemanticCompiler(db)
    return compiler.compile(workspace_id, query)
