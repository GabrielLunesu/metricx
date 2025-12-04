"""
Semantic QA Service
===================

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Active

High-level orchestrator for question-answering using the Semantic Layer.
This is the REPLACEMENT for QAService (app/services/qa_service.py).

WHY THIS FILE EXISTS
--------------------
The original QAService uses the DSL (Domain-Specific Language) which had
a critical limitation: mutually exclusive fields (breakdown OR comparison).

This service uses the Semantic Layer which allows composable queries:
- breakdown + comparison = per-entity comparison
- breakdown + timeseries = multi-line charts
- All components can combine freely

ARCHITECTURE
------------
```
User Question
    |
    v
LLM Translation → SemanticQuery (app/semantic/prompts.py)
    |
    v
Multi-layer Validation (app/semantic/validator.py)
    |   - Schema validation
    |   - Security validation (allowlists)
    |   - Semantic validation (business rules)
    |
    v
Semantic Compiler (app/semantic/compiler.py)
    |   - Strategy selection
    |   - Data retrieval
    |   - Entity comparison (THE KEY FEATURE)
    |
    v
CompilationResult
    |
    v
Answer Builder → Natural Language
    |
    v
Visual Builder → Charts/Tables
```

TELEMETRY
---------
Every stage is tracked with:
- query.started, query.completed, query.failed events
- Per-stage timing (validation, compilation, answer_building)
- Error classification and logging

RELATED FILES
-------------
- app/semantic/query.py: SemanticQuery structure
- app/semantic/validator.py: Multi-layer validation
- app/semantic/compiler.py: Query compilation
- app/semantic/telemetry.py: Observability
- app/semantic/prompts.py: LLM prompts
- app/services/qa_service.py: OLD service (being replaced)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Dict, Any, Optional, List
from decimal import Decimal

from sqlalchemy.orm import Session

from app.semantic import (
    SemanticQuery,
    TimeRange,
    Breakdown,
    Comparison,
    ComparisonType,
    Filter,
    SemanticValidator,
    SemanticCompiler,
    CompilationResult,
    TelemetryCollector,
    get_telemetry,
    build_semantic_full_prompt,
    SEMANTIC_ANSWER_PROMPT,
)
from app.semantic.errors import QueryError, QueryErrorHandler, ErrorCategory
from app.telemetry.logging import log_qa_run
from app import state

logger = logging.getLogger(__name__)


def convert_decimals_to_floats(obj: Any) -> Any:
    """Recursively convert Decimal values to floats for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_floats(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_floats(item) for item in obj]
    else:
        return obj


class SemanticQAService:
    """
    High-level QA orchestrator using the Semantic Layer.

    WHAT: Answers natural language questions about marketing metrics.

    WHY: Replaces QAService with composable queries and better observability.

    USAGE:
        service = SemanticQAService(db)
        result = service.answer(
            question="Compare CPC this week vs last week for top 3 ads",
            workspace_id="..."
        )

    THE KEY FEATURE:
        This service can handle queries that were IMPOSSIBLE before:
        - "Compare CPC for top 3 ads this week vs last week"
        - "Graph daily spend for top 5 campaigns vs last week"

    RELATED:
        - app/services/qa_service.py: OLD service (DSL-based)
        - app/routers/qa.py: HTTP endpoint
    """

    def __init__(self, db: Session):
        """
        Initialize Semantic QA service.

        PARAMETERS:
            db: SQLAlchemy database session

        COMPONENTS:
            - validator: Multi-layer query validation
            - compiler: Query to data compilation
            - telemetry: Pipeline observability
            - error_handler: Error classification
        """
        self.db = db
        self.validator = SemanticValidator()
        self.compiler = SemanticCompiler(db)
        self.telemetry = get_telemetry()
        self.error_handler = QueryErrorHandler()
        # Use shared context manager for conversation history
        self.context_manager = state.context_manager

    def answer(
        self,
        question: str,
        workspace_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Answer a natural language question about metrics.

        WHAT: Main entry point - orchestrates the full pipeline.

        WHY: Single method for complete question answering.

        PARAMETERS:
            question: User's natural language question
            workspace_id: UUID of the workspace (security scope)
            user_id: Optional user UUID for context/logging

        RETURNS:
            Dict with:
                - answer: Natural language answer
                - data: CompilationResult data
                - query: SemanticQuery that was executed
                - visuals: Visual payload (charts/tables)
                - telemetry: Performance metrics

        PIPELINE:
            1. Get conversation context (for follow-ups)
            2. Translate question → SemanticQuery (LLM)
            3. Validate query (security, semantic)
            4. Compile query → data (THE KEY)
            5. Build answer (natural language)
            6. Build visuals (charts/tables)
            7. Store context for follow-ups
            8. Log telemetry

        EXAMPLE:
            result = service.answer(
                question="Compare CPC for top 3 ads this week vs last week",
                workspace_id="123e4567..."
            )
            # Result includes entity_comparison data!
        """
        start_time = time.time()

        # Start telemetry tracking
        with self.telemetry.track_query(workspace_id) as ctx:
            try:
                logger.info(f"[SEMANTIC_QA] ===== Starting Semantic QA pipeline =====")
                logger.info(f"[SEMANTIC_QA] Question: '{question}'")
                logger.info(f"[SEMANTIC_QA] Workspace ID: {workspace_id}")

                # Step 1: Get conversation context
                context = self._get_context(user_id, workspace_id)
                logger.info(f"[SEMANTIC_QA] Context: {len(context)} previous queries")

                # Step 2: Translate question to SemanticQuery
                with ctx.track_stage("translation"):
                    query = self._translate_question(question, context)
                    logger.info(f"[SEMANTIC_QA] Query: {query.describe()}")

                # Step 3: Validate query
                with ctx.track_stage("validation"):
                    validation_result = self.validator.validate(query)
                    ctx.set_validation_result(
                        valid=validation_result.valid,
                        errors=len(validation_result.errors),
                        warnings=len(validation_result.warnings),
                    )

                    if not validation_result.valid:
                        error_msg = validation_result.to_user_message()
                        logger.warning(f"[SEMANTIC_QA] Validation failed: {error_msg}")
                        ctx.fail("VALIDATION_FAILED", error_msg, "semantic")

                        return {
                            "answer": error_msg,
                            "data": None,
                            "query": query.to_dict(),
                            "visuals": None,
                            "error": "validation_failed",
                        }

                # Step 4: Compile and execute query (THE KEY)
                with ctx.track_stage("compilation"):
                    result = self.compiler.compile(workspace_id, query)
                    ctx.set_compilation_result(
                        strategy=result.compilation_strategy,
                        row_count=len(result.breakdown) if result.breakdown else 0,
                    )
                    logger.info(f"[SEMANTIC_QA] Compilation: {result.compilation_strategy}")

                # Step 5: Build answer
                with ctx.track_stage("answer_building"):
                    answer_text = self._build_answer(query, result)
                    logger.info(f"[SEMANTIC_QA] Answer: '{answer_text[:50]}...'")

                # Step 6: Build visuals
                with ctx.track_stage("visual_building"):
                    visuals = self._build_visuals(query, result)

                # Step 7: Store context for follow-ups
                self._store_context(user_id, workspace_id, question, query, result)

                # Step 8: Log telemetry
                total_latency_ms = int((time.time() - start_time) * 1000)
                log_qa_run(
                    db=self.db,
                    workspace_id=workspace_id,
                    question=question,
                    dsl=query.to_dict(),
                    success=True,
                    latency_ms=total_latency_ms,
                    user_id=user_id,
                    answer_text=answer_text,
                )

                logger.info(f"[SEMANTIC_QA] ===== Pipeline complete ({total_latency_ms}ms) =====")

                return {
                    "answer": answer_text,
                    "data": convert_decimals_to_floats(result.to_dict()),
                    "query": query.to_dict(),
                    "visuals": convert_decimals_to_floats(visuals),  # Convert Decimals for JSON
                    "telemetry": {
                        "latency_ms": total_latency_ms,
                        "strategy": result.compilation_strategy,
                        "has_entity_comparison": result.has_entity_comparison(),
                    },
                }

            except Exception as e:
                # Handle and classify error
                total_latency_ms = int((time.time() - start_time) * 1000)
                ctx.fail(
                    error_code=type(e).__name__,
                    error_message=str(e),
                    error_category="execution",
                )

                logger.error(f"[SEMANTIC_QA] Pipeline failed: {e}")

                # Log failure
                log_qa_run(
                    db=self.db,
                    workspace_id=workspace_id,
                    question=question,
                    dsl=None,
                    success=False,
                    latency_ms=total_latency_ms,
                    user_id=user_id,
                    error_message=str(e),
                )

                # Return user-friendly error
                return {
                    "answer": self._get_error_message(e),
                    "data": None,
                    "query": None,
                    "visuals": None,
                    "error": str(e),
                }

    # -------------------------------------------------------------------------
    # Pipeline Steps
    # -------------------------------------------------------------------------

    def _get_context(self, user_id: Optional[str], workspace_id: str) -> List[Dict]:
        """Get conversation context for follow-up questions."""
        if self.context_manager:
            return self.context_manager.get_context(user_id or "anon", workspace_id)
        return []

    def _translate_question(
        self,
        question: str,
        context: List[Dict],
    ) -> SemanticQuery:
        """
        Translate natural language to SemanticQuery.

        WHAT: Uses LLM to convert question to structured query.

        WHY: Enables natural language interface.

        NOTE: For now, this is a simplified implementation.
        Full LLM integration will be added in Phase 5 completion.
        """
        logger.info(f"[SEMANTIC_QA] _translate_question: '{question}'")
        logger.info(f"[SEMANTIC_QA] Context entries: {len(context)}")

        # Build context string for LLM
        context_str = None
        if context:
            context_parts = []
            for entry in context[-3:]:  # Last 3 entries
                q = entry.get("question", "")
                dsl = entry.get("dsl", {})
                context_parts.append(f"Q: {q}\nA: {json.dumps(dsl)}")
            context_str = "\n\n".join(context_parts)
            logger.info(f"[SEMANTIC_QA] Context string built: {context_str[:200]}...")

        # Build full prompt
        prompt = build_semantic_full_prompt(question, context_str)

        # Check if this is a follow-up question that modifies a previous query
        follow_up_query = self._handle_follow_up(question, context)
        if follow_up_query:
            logger.info(f"[SEMANTIC_QA] Follow-up detected! Query: {follow_up_query.describe()}")
            logger.info(f"[SEMANTIC_QA] Follow-up include_timeseries: {follow_up_query.include_timeseries}")
            return follow_up_query

        # For now, use pattern matching as a fallback
        # TODO: Integrate with actual LLM (OpenAI/Anthropic)
        logger.info(f"[SEMANTIC_QA] No follow-up detected, using fallback parser")
        query = self._parse_question_fallback(question)
        logger.info(f"[SEMANTIC_QA] Fallback query: {query.describe()}")
        logger.info(f"[SEMANTIC_QA] Fallback include_timeseries: {query.include_timeseries}")

        return query

    def _handle_follow_up(
        self,
        question: str,
        context: List[Dict],
    ) -> Optional[SemanticQuery]:
        """
        Handle follow-up questions that modify previous queries.

        WHAT: Detects phrases like "make a graph", "show daily", "compare to last week"
              and modifies the previous query accordingly.

        WHY: Enables conversational flow without re-specifying the entire query.

        IMPORTANT: If the new question mentions a specific metric, use that metric
        instead of inheriting from the previous query.
        """
        if not context:
            return None

        q = question.lower().strip()

        # Get the previous query
        prev_entry = context[-1] if context else None
        if not prev_entry or "dsl" not in prev_entry:
            return None

        prev_dsl = prev_entry.get("dsl", {})

        # Helper to detect metric in current question
        def detect_metric_in_question(question_text: str) -> Optional[List[str]]:
            """Check if question explicitly mentions a metric."""
            q_lower = question_text.lower()
            if "spend" in q_lower or "cost" in q_lower:
                return ["spend"]
            if "revenue" in q_lower:
                return ["revenue"]
            if "cpc" in q_lower:
                return ["cpc"]
            if "ctr" in q_lower:
                return ["ctr"]
            if "cpa" in q_lower:
                return ["cpa"]
            if "roas" in q_lower:
                return ["roas"]
            if "conversion" in q_lower:
                return ["conversions"]
            return None  # No explicit metric mentioned

        # Graph/chart follow-ups -> add timeseries
        graph_triggers = ["graph", "chart", "trend", "daily", "show me over time", "visualize"]
        if any(trigger in q for trigger in graph_triggers):
            # Check if question mentions a specific metric
            metrics = detect_metric_in_question(q) or prev_dsl.get("metrics", ["roas"])
            logger.info(f"[SEMANTIC_QA] Follow-up: adding timeseries, metrics={metrics}")
            return SemanticQuery(
                metrics=metrics,
                time_range=TimeRange(last_n_days=prev_dsl.get("time_range", {}).get("last_n_days", 7)),
                include_timeseries=True,  # Add timeseries flag
            )

        # Comparison follow-ups -> add comparison
        compare_triggers = ["vs last", "compare to", "compared to", "change from", "vs "]
        if any(trigger in q for trigger in compare_triggers):
            # Check if question mentions a specific metric
            metrics = detect_metric_in_question(q) or prev_dsl.get("metrics", ["roas"])
            logger.info(f"[SEMANTIC_QA] Follow-up: adding comparison, metrics={metrics}")
            return SemanticQuery(
                metrics=metrics,
                time_range=TimeRange(last_n_days=prev_dsl.get("time_range", {}).get("last_n_days", 7)),
                comparison=Comparison(type=ComparisonType.PREVIOUS_PERIOD),
            )

        return None

    def _parse_question_fallback(self, question: str) -> SemanticQuery:
        """
        Fallback question parsing (pattern matching).

        WHAT: Simple heuristic-based parsing when LLM is unavailable.

        WHY: Enables testing without LLM dependency.

        NOTE: This will be replaced with actual LLM translation.
        """
        q = question.lower()
        logger.info(f"[FALLBACK_PARSER] Input: '{q}'")

        # Detect metrics - check most specific first
        metrics = ["roas"]  # Default
        if "spend" in q or "cost" in q:
            metrics = ["spend"]
            logger.info(f"[FALLBACK_PARSER] Detected metric: spend")
        elif "revenue" in q or "sales" in q:
            metrics = ["revenue"]
            logger.info(f"[FALLBACK_PARSER] Detected metric: revenue")
        elif "cpc" in q:
            metrics = ["cpc"]
            logger.info(f"[FALLBACK_PARSER] Detected metric: cpc")
        elif "ctr" in q:
            metrics = ["ctr"]
            logger.info(f"[FALLBACK_PARSER] Detected metric: ctr")
        elif "cpa" in q:
            metrics = ["cpa"]
            logger.info(f"[FALLBACK_PARSER] Detected metric: cpa")
        elif "conversion" in q:
            metrics = ["conversions"]
            logger.info(f"[FALLBACK_PARSER] Detected metric: conversions")
        elif "roas" in q:
            metrics = ["roas"]
            logger.info(f"[FALLBACK_PARSER] Detected metric: roas (explicit)")
        else:
            logger.info(f"[FALLBACK_PARSER] No metric keyword found, using default: roas")

        # Detect time range
        time_range = TimeRange(last_n_days=7)  # Default
        if "today" in q:
            time_range = TimeRange(last_n_days=1)
        elif "yesterday" in q:
            time_range = TimeRange(last_n_days=1)
        elif "month" in q or "30 day" in q:
            time_range = TimeRange(last_n_days=30)
        elif "last week" in q or "this week" in q:
            time_range = TimeRange(last_n_days=7)

        # Detect breakdown
        breakdown = None
        limit = 5  # Default limit
        if "top 3" in q:
            limit = 3
        elif "top 10" in q:
            limit = 10
        elif "all" in q:
            limit = 50

        if "campaign" in q:
            breakdown = Breakdown(
                dimension="entity",
                level="campaign",
                limit=limit,
            )
            logger.info(f"[FALLBACK_PARSER] Detected breakdown: campaign (limit={limit})")
        elif "creative" in q or "ad" in q:
            breakdown = Breakdown(
                dimension="entity",
                level="ad",
                limit=limit,
            )
            logger.info(f"[FALLBACK_PARSER] Detected breakdown: ad/creative (limit={limit})")
        elif "platform" in q or "provider" in q:
            breakdown = Breakdown(dimension="provider")
            logger.info(f"[FALLBACK_PARSER] Detected breakdown: provider")

        # Detect comparison
        comparison = None
        if "vs" in q or "compare" in q or "last week" in q or "vs last" in q:
            comparison = Comparison(type=ComparisonType.PREVIOUS_PERIOD)
            logger.info(f"[FALLBACK_PARSER] Detected comparison: previous_period")

        # Detect timeseries
        include_timeseries = "graph" in q or "chart" in q or "trend" in q or "daily" in q or "over time" in q
        if include_timeseries:
            logger.info(f"[FALLBACK_PARSER] Detected timeseries request")

        # Detect filters
        filters = []
        if "meta" in q or "facebook" in q:
            filters.append(Filter(field="provider", operator="=", value="meta"))
            logger.info(f"[FALLBACK_PARSER] Detected filter: provider=meta")
        elif "google" in q:
            filters.append(Filter(field="provider", operator="=", value="google"))
            logger.info(f"[FALLBACK_PARSER] Detected filter: provider=google")

        # Handle "zero sales" / "no conversions" type queries
        if "zero" in q or "no " in q:
            if "sales" in q or "conversion" in q or "revenue" in q:
                # This is a request for entities with no conversions
                # We'll need to handle this in the compiler
                logger.info(f"[FALLBACK_PARSER] Detected 'zero/no' filter - filtering for no conversions")
                filters.append(Filter(field="conversions", operator="=", value="0"))
                if not breakdown:
                    breakdown = Breakdown(dimension="entity", level="campaign", limit=limit)

        query = SemanticQuery(
            metrics=metrics,
            time_range=time_range,
            breakdown=breakdown,
            comparison=comparison,
            include_timeseries=include_timeseries,
            filters=filters,
        )
        logger.info(f"[FALLBACK_PARSER] Final query: {query.describe()}")
        return query

    def _build_answer(self, query: SemanticQuery, result: CompilationResult) -> str:
        """
        Build natural language answer from compilation result.

        WHAT: Converts structured data to human-readable text.

        WHY: Users want natural language, not JSON.

        NOTE: For now, this is template-based. Full LLM integration later.
        """
        # Get primary metric value
        primary_metric = query.get_primary_metric()
        value = result.get_primary_metric_value()

        # Format value
        if value is None:
            return f"No {primary_metric} data found for the selected period."

        # Format based on metric type
        if primary_metric in ["spend", "revenue", "profit"]:
            value_str = f"${value:,.2f}"
        elif primary_metric in ["roas", "poas"]:
            value_str = f"{value:.2f}×"
        elif primary_metric in ["ctr", "cvr"]:
            value_str = f"{value:.2%}"
        elif primary_metric in ["cpc", "cpa", "cpl", "cpi", "cpp", "cpm", "aov"]:
            value_str = f"${value:.2f}"
        else:
            value_str = f"{value:,.0f}"

        # Build answer based on compilation strategy
        strategy = result.compilation_strategy

        if strategy == "entity_comparison":
            # THE KEY FEATURE - per-entity comparison
            return self._build_entity_comparison_answer(query, result, value_str)

        elif strategy == "entity_breakdown":
            return self._build_breakdown_answer(query, result, value_str)

        elif strategy == "comparison":
            return self._build_comparison_answer(query, result, value_str)

        elif strategy == "timeseries":
            return self._build_timeseries_answer(query, result, value_str)

        else:
            # Simple summary
            return f"Your {primary_metric.upper()} was {value_str} for the selected period."

    def _build_entity_comparison_answer(
        self,
        query: SemanticQuery,
        result: CompilationResult,
        value_str: str,
    ) -> str:
        """Build answer for entity comparison (THE KEY FEATURE)."""
        if not result.entity_comparison:
            return f"Your {query.get_primary_metric().upper()} was {value_str}."

        primary_metric = query.get_primary_metric()
        lines = [f"Here's how your top {len(result.entity_comparison)} {query.breakdown.level}s performed:"]

        for item in result.entity_comparison:
            # Format current value
            if item.current_value is not None:
                if primary_metric in ["spend", "revenue", "cpc", "cpa"]:
                    curr_str = f"${item.current_value:.2f}"
                elif primary_metric in ["roas", "poas"]:
                    curr_str = f"{item.current_value:.2f}×"
                else:
                    curr_str = f"{item.current_value:.2f}"
            else:
                curr_str = "N/A"

            # Format delta
            if item.delta_pct is not None:
                sign = "+" if item.delta_pct > 0 else ""
                delta_str = f" ({sign}{item.delta_pct:.1%})"
            else:
                delta_str = ""

            lines.append(f"• {item.entity_name}: {curr_str}{delta_str}")

        return "\n".join(lines)

    def _build_breakdown_answer(
        self,
        query: SemanticQuery,
        result: CompilationResult,
        value_str: str,
    ) -> str:
        """Build answer for breakdown query."""
        if not result.breakdown:
            return f"Your {query.get_primary_metric().upper()} was {value_str}."

        primary_metric = query.get_primary_metric()
        lines = [f"Top {query.breakdown.level}s by {primary_metric.upper()}:"]

        for item in result.breakdown[:5]:  # Show top 5
            if primary_metric in ["spend", "revenue", "cpc", "cpa"]:
                val_str = f"${item.value:.2f}"
            elif primary_metric in ["roas", "poas"]:
                val_str = f"{item.value:.2f}×"
            else:
                val_str = f"{item.value:.2f}"

            lines.append(f"• {item.label}: {val_str}")

        return "\n".join(lines)

    def _build_comparison_answer(
        self,
        query: SemanticQuery,
        result: CompilationResult,
        value_str: str,
    ) -> str:
        """Build answer for comparison query."""
        primary_metric = query.get_primary_metric()
        metric_value = result.summary.get(primary_metric)

        if metric_value and metric_value.delta_pct is not None:
            sign = "+" if metric_value.delta_pct > 0 else ""
            delta_str = f"{sign}{metric_value.delta_pct:.1%}"
            direction = "up" if metric_value.delta_pct > 0 else "down"
            return f"Your {primary_metric.upper()} was {value_str}, {direction} {abs(metric_value.delta_pct):.1%} from the previous period."

        return f"Your {primary_metric.upper()} was {value_str}."

    def _build_timeseries_answer(
        self,
        query: SemanticQuery,
        result: CompilationResult,
        value_str: str,
    ) -> str:
        """Build answer for timeseries query."""
        primary_metric = query.get_primary_metric()
        return f"Your {primary_metric.upper()} averaged {value_str} over the period. See the chart below for the daily trend."

    def _build_visuals(
        self,
        query: SemanticQuery,
        result: CompilationResult,
    ) -> Optional[Dict[str, Any]]:
        """
        Build visual payload for the result.

        WHAT: Creates chart/table specifications.

        WHY: Visual representation of data.

        NOTE: Simplified implementation for now.
        """
        logger.info(f"[SEMANTIC_QA] _build_visuals: strategy={result.compilation_strategy}")
        logger.info(f"[SEMANTIC_QA] _build_visuals: has_breakdown={result.has_breakdown()}, has_timeseries={result.has_timeseries()}, has_entity_comparison={result.has_entity_comparison()}")

        # Check if any visual-worthy data exists
        if (not result.has_breakdown()
            and not result.has_timeseries()
            and not result.has_entity_comparison()):
            logger.info(f"[SEMANTIC_QA] _build_visuals: No visual-worthy data, returning None")
            return None

        visuals = {"viz_specs": [], "tables": []}

        # Timeseries chart
        if result.has_timeseries():
            for metric, points in result.timeseries.items():
                spec = {
                    "id": f"timeseries-{metric}",
                    "type": "area",
                    "title": f"{metric.upper()} Trend",
                    "valueFormat": metric,
                    "series": [
                        {
                            "name": metric.upper(),
                            "data": [{"x": p.date, "y": p.value} for p in points],
                        }
                    ],
                }
                visuals["viz_specs"].append(spec)
                logger.info(f"[SEMANTIC_QA] Added timeseries chart for {metric} with {len(points)} points")

        # Entity timeseries (multi-line chart)
        if result.has_entity_timeseries():
            spec = {
                "type": "line",
                "title": f"{query.get_primary_metric().upper()} by {query.breakdown.level}",
                "series": [
                    {
                        "name": item.entity_name,
                        "data": item.timeseries,
                    }
                    for item in result.entity_timeseries
                ],
            }
            visuals["viz_specs"].append(spec)

        # Breakdown bar chart
        if result.has_breakdown() and not result.has_entity_timeseries() and not result.has_entity_comparison():
            metric = query.get_primary_metric()
            spec = {
                "id": f"breakdown-{metric}",
                "type": "bar",
                "title": f"{metric.upper()} by {query.breakdown.level}",
                "valueFormat": metric,
                "series": [
                    {
                        "name": metric.upper(),
                        "data": [
                            {"x": item.label, "y": item.value}
                            for item in result.breakdown
                        ],
                    }
                ],
            }
            visuals["viz_specs"].append(spec)
            logger.info(f"[SEMANTIC_QA] Added breakdown bar chart for {metric} with {len(result.breakdown)} items")

        # Entity comparison table (THE KEY FEATURE)
        if result.has_entity_comparison():
            metric = query.get_primary_metric()
            table = {
                "id": f"comparison-{metric}",
                "type": "comparison_table",
                "title": f"{metric.upper()} Comparison by {query.breakdown.level}",
                "columns": [
                    {"key": "entity", "label": "Entity", "format": "text"},
                    {"key": "current", "label": "This Period", "format": metric},
                    {"key": "previous", "label": "Previous Period", "format": metric},
                    {"key": "delta_pct", "label": "Change", "format": "percent"},
                ],
                "rows": [
                    {
                        "entity": item.entity_name,
                        "current": item.current_value,
                        "previous": item.previous_value,
                        "delta_pct": item.delta_pct,
                    }
                    for item in result.entity_comparison
                ],
            }
            visuals["tables"].append(table)

            # Grouped bar chart for visual comparison
            chart = {
                "id": f"comparison-chart-{metric}",
                "type": "grouped_bar",
                "title": f"{metric.upper()} This Week vs Last Week",
                "valueFormat": metric,
                "series": [
                    {
                        "name": "This Period",
                        "data": [
                            {"x": item.entity_name, "y": item.current_value}
                            for item in result.entity_comparison
                        ],
                    },
                    {
                        "name": "Previous Period",
                        "data": [
                            {"x": item.entity_name, "y": item.previous_value}
                            for item in result.entity_comparison
                        ],
                    },
                ],
            }
            visuals["viz_specs"].append(chart)

        return visuals if (visuals["viz_specs"] or visuals["tables"]) else None

    def _store_context(
        self,
        user_id: Optional[str],
        workspace_id: str,
        question: str,
        query: SemanticQuery,
        result: CompilationResult,
    ) -> None:
        """Store conversation context for follow-ups."""
        if self.context_manager:
            self.context_manager.add_entry(
                user_id=user_id or "anon",
                workspace_id=workspace_id,
                question=question,
                dsl=query.to_dict(),
                result=convert_decimals_to_floats(result.to_dict()),  # Convert Decimals for JSON
            )

    def _get_error_message(self, error: Exception) -> str:
        """Get user-friendly error message."""
        if isinstance(error, QueryError):
            return error.message

        return (
            "I couldn't process your question. Please try rephrasing it. "
            "For example:\n"
            "- 'What's my ROAS this week?'\n"
            "- 'Compare CPC for top 3 ads vs last week'\n"
            "- 'Show me daily spend by campaign'"
        )


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def answer_question(
    db: Session,
    question: str,
    workspace_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to answer a question.

    WHAT: One-liner for answering questions.

    WHY: Cleaner API for simple use cases.

    EXAMPLE:
        result = answer_question(db, "What's my ROAS?", workspace_id)
    """
    service = SemanticQAService(db)
    return service.answer(question, workspace_id, user_id)
