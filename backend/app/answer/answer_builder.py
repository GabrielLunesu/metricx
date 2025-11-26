"""
Answer Builder (Hybrid)
========================

Generates human-readable answers from DSL + execution results.

WHY Hybrid Approach:
- **Deterministic facts**: Extract numbers/data from results (no hallucinations)
- **LLM rephrasing**: Make answers sound natural and conversational (not robotic)
- **Safety**: LLM cannot invent numbers, only rephrase provided facts

CHANGES IN v2.0.1:
- Use extract_rich_context() instead of basic fact extraction
- Enhanced GPT prompt with structured context
- Better system instructions for using rich context

Design Principles:
- Separation of concerns: This module handles ONLY answer generation
- QAService orchestrates the pipeline (translate → plan → execute → answer)
- Executor computes numbers, this class handles presentation

Related files:
- app/dsl/schema.py: Defines MetricQuery + MetricResult (facts source)
- app/services/qa_service.py: Calls this builder to generate answers
- app/nlp/translator.py: Similar LLM usage pattern for DSL translation
- app/answer/context_extractor.py: Rich context extraction (NEW in v2.0.1)
"""

from __future__ import annotations

import time
import json
import logging
from typing import Dict, Any, Union, Optional
from datetime import date
from openai import OpenAI
from sqlalchemy.orm import Session

from app.dsl.schema import MetricQuery, MetricResult
from app.deps import get_settings
from app.answer.formatters import format_metric_value, format_delta_pct, fmt_currency, fmt_count
from app.answer.context_extractor import extract_rich_context  # NEW in v2.0.1
from app.answer.intent_classifier import (
    classify_intent, AnswerIntent, explain_intent, 
    VerbTense, detect_tense,
    PerformerIntent, detect_performer_intent  # NEW in Phase 4
)
from app.nlp.prompts import (
    ANSWER_GENERATION_PROMPT,  # Existing (fallback for analytical)
    SIMPLE_ANSWER_PROMPT,      # NEW in Phase 1
    COMPARATIVE_ANSWER_PROMPT, # NEW in Phase 1
    ANALYTICAL_ANSWER_PROMPT   # NEW in Phase 1
)

logger = logging.getLogger(__name__)

# Timeout for LLM calls in answer generation (seconds)
# Shorter than translator (30s) since answers should be quick
LLM_ANSWER_TIMEOUT_SECONDS = 15


def _format_date_range(start: date, end: date) -> str:
    """
    Format a date range as human-readable string.
    
    WHY this exists:
    - Provides trust and transparency in answers
    - Users want to know exactly what time window the data covers
    - Compact format saves tokens in LLM prompts
    
    Args:
        start: Start date (inclusive)
        end: End date (inclusive)
        
    Returns:
        Formatted date range string
        
    Examples:
        >>> _format_date_range(date(2025, 9, 29), date(2025, 10, 5))
        "Sep 29–Oct 05, 2025"
        
        >>> _format_date_range(date(2025, 10, 1), date(2025, 10, 1))
        "Oct 01, 2025"
    
    Format decisions:
    - Use abbreviated month names (Sep, Oct) for compactness
    - Use en-dash (–) between dates (not hyphen)
    - Include year at end only (avoid repetition)
    - Single day: Show just one date
    
    Related:
    - Used by: build_answer() to include date window in answers
    - Alternative: ISO format (YYYY-MM-DD) is more precise but less friendly
    """
    # Single day: don't show range
    if start == end:
        return start.strftime("%b %d, %Y")
    
    # Same month: "Sep 29–30, 2025"
    if start.year == end.year and start.month == end.month:
        return f"{start.strftime('%b %d')}–{end.strftime('%d, %Y')}"
    
    # Different months, same year: "Sep 29–Oct 05, 2025"
    if start.year == end.year:
        return f"{start.strftime('%b %d')}–{end.strftime('%b %d, %Y')}"
    
    # Different years: "Dec 29, 2024–Jan 05, 2025"
    return f"{start.strftime('%b %d, %Y')}–{end.strftime('%b %d, %Y')}"


def _format_timeframe_display(timeframe_desc: str, window: Optional[Dict[str, date]]) -> str:
    """
    Build human-friendly timeframe display for answers.
    
    WHY this exists:
    - Users want clear timeframe context in answers
    - Combines user's original phrase with actual date range
    - Provides transparency about what time period data covers
    
    Args:
        timeframe_desc: User's original timeframe phrase (e.g., "this month", "last week")
        window: Actual date range {"start": date, "end": date}
        
    Returns:
        Human-friendly timeframe string for answers
        
    Examples:
        >>> _format_timeframe_display("last month", {"start": date(2025, 9, 1), "end": date(2025, 9, 30)})
        "in the last 30 days"
        
        >>> _format_timeframe_display("this month", {"start": date(2025, 10, 1), "end": date(2025, 10, 13)})
        "from October 1 to October 13"
        
        >>> _format_timeframe_display("last week", {"start": date(2025, 10, 6), "end": date(2025, 10, 12)})
        "in the last 7 days"
        
        >>> _format_timeframe_display("yesterday", {"start": date(2025, 10, 12), "end": date(2025, 10, 12)})
        "yesterday"
        
        >>> _format_timeframe_display("this week", {"start": date(2025, 10, 6), "end": date(2025, 10, 12)})
        "this week"
    
    Logic:
    - Use user's phrase for common relative timeframes (yesterday, this week, last week)
    - Convert "this month" to actual date range for transparency
    - Convert "last month" to "in the last X days" for clarity
    - Fallback to date range format if no specific mapping
    """
    if not timeframe_desc:
        return ""
    
    # Handle specific relative timeframes that users expect to see as-is
    if timeframe_desc.lower() in ["yesterday", "today", "this week", "last week"]:
        return timeframe_desc.lower()
    
    # Handle "this month" -> show actual date range for transparency
    if timeframe_desc.lower() == "this month" and window:
        start_date = window.get("start")
        end_date = window.get("end")
        if start_date and end_date:
            # Format as "from October 1 to October 13"
            start_str = start_date.strftime("%B %d")
            end_str = end_date.strftime("%B %d")
            if start_date.month == end_date.month:
                # Same month: "from October 1 to 13"
                end_str = end_date.strftime("%d")
            return f"from {start_str} to {end_str}"
    
    # Handle "last month" -> show as "in the last X days"
    if timeframe_desc.lower() == "last month" and window:
        start_date = window.get("start")
        end_date = window.get("end")
        if start_date and end_date:
            days = (end_date - start_date).days + 1
            return f"in the last {days} days"
    
    # Handle other "last X" patterns
    if timeframe_desc.lower().startswith("last ") and window:
        start_date = window.get("start")
        end_date = window.get("end")
        if start_date and end_date:
            days = (end_date - start_date).days + 1
            if days == 1:
                return "yesterday"
            elif days == 7:
                return "in the last 7 days"
            elif days == 30:
                return "in the last 30 days"
            else:
                return f"in the last {days} days"
    
    # Fallback: use user's original phrase
    return timeframe_desc.lower()


class AnswerBuilderError(Exception):
    """
    Raised when answer generation fails.
    
    This signals to QAService to use the fallback template-based builder.
    """
    def __init__(self, message: str, original_error: Exception = None):
        self.message = message
        self.original_error = original_error
        super().__init__(message)


class AnswerBuilder:
    """
    Hybrid Answer Builder
    ---------------------
    
    Responsible ONLY for answer generation.
    
    WHY separation from QAService:
    - QAService orchestrates the pipeline (translate → plan → execute → answer)
    - Executor computes the numbers (deterministic, safe)
    - This class handles presentation (natural language)
    
    Process:
    1. Extract deterministic facts from results (no hallucinations possible)
    2. Build structured fact payload
    3. Call GPT-4o-mini with strict instructions:
       - "Do NOT invent numbers"
       - "Use only provided facts"
       - "Keep it conversational"
    4. Return rephrased natural language
    
    Fallback:
    - If LLM call fails, raise AnswerBuilderError
    - QAService will catch and use template-based fallback
    
    Examples:
        >>> builder = AnswerBuilder()
        >>> # Metrics query
        >>> dsl = MetricQuery(query_type="metrics", metric="roas")
        >>> result = MetricResult(summary=2.45, delta_pct=0.19)
        >>> answer = builder.build_answer(dsl, result)
        >>> print(answer)
        "Your ROAS is currently 2.45, which represents a 19% improvement 
         over the previous period. Great work!"
        
        >>> # Providers query
        >>> dsl = MetricQuery(query_type="providers")
        >>> result = {"providers": ["google", "meta", "tiktok"]}
        >>> answer = builder.build_answer(dsl, result)
        >>> print(answer)
        "You're running ads across three platforms: Google, Meta, and TikTok."
    
    Related:
    - Used by: app/services/qa_service.py
    - Input: app/dsl/schema.py (MetricQuery, MetricResult or dict)
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize Answer Builder with OpenAI client and optional database session.
        
        Args:
            db: Optional database session for enhanced context (e.g., entity counts)
        
        Uses the same API key and client pattern as the Translator
        for consistency.
        
        Related:
        - app/nlp/translator.py: Similar initialization pattern
        - app/deps.py: get_settings() provides OpenAI API key
        """
        settings = get_settings()
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.db = db
    
    def _get_entity_count_for_breakdown(
        self,
        workspace_id: str,
        breakdown_dimension: str,
        status: Optional[str] = None
    ) -> int:
        """
        Get count of entities for a breakdown dimension (without metric filters).
        
        Args:
            workspace_id: Workspace ID
            breakdown_dimension: 'campaign', 'adset', 'ad', or other
            status: Optional status filter ('active', etc.)
        
        Returns:
            Count of entities in workspace
        """
        if not self.db:
            return 0
        
        try:
            from app.services.unified_metric_service import UnifiedMetricService
            from app.dsl.schema import Filters
            service = UnifiedMetricService(self.db)
            
            level = breakdown_dimension if breakdown_dimension in ['campaign', 'adset', 'ad'] else None
            
            # Create minimal filters object
            filters = Filters(
                level=level,
                status=status
            )
            
            entities_result = service.get_entity_list(
                workspace_id=workspace_id,
                filters=filters,
                level=level
            )
            return len(entities_result)
        except Exception as e:
            logger.warning(f"[ANSWER_BUILDER] Failed to get entity count: {e}")
            return 0
    
    def build_answer(
        self, 
        dsl: MetricQuery, 
        result: Union[MetricResult, Dict[str, Any]],
        window: Optional[Dict[str, date]] = None,
        log_latency: bool = False
    ) -> tuple[str, Optional[int]]:
        """
        Build a natural language answer from query + results.
        
        CHANGES IN v2.0.1:
        - Uses extract_rich_context() for metrics queries (instead of basic facts)
        - Enhanced GPT prompt with structured context
        - Workspace average comparison included when available
        
        Args:
            dsl: The MetricQuery that was executed (user intent)
            result: Execution results (MetricResult for metrics, dict for providers/entities)
            window: Optional date window {"start": date, "end": date} for including date range in answer
            log_latency: Whether to return latency in ms (for telemetry)
            
        Returns:
            tuple: (answer_text, latency_ms) if log_latency=True, else (answer_text, None)
            
        Raises:
            AnswerBuilderError: If LLM call fails (QAService will fallback to template)
            
        Examples:
            >>> builder = AnswerBuilder()
            >>> dsl = MetricQuery(query_type="metrics", metric="roas", time_range=TimeRange(last_n_days=7))
            >>> result = MetricResult(summary=2.45, previous=2.06, workspace_avg=2.30)
            >>> answer, latency = builder.build_answer(dsl, result, log_latency=True)
            >>> print(answer)
            "Your ROAS jumped to 2.45× last week—19% higher than before. This is slightly above your workspace average of 2.30×."
            
        Process (v2.0.1):
        1. For metrics queries: Extract rich context (trends, comparisons, outliers)
        2. For other queries: Extract basic facts (providers, entities)
        3. Build GPT prompt with context-aware instructions
        4. Call GPT-4o-mini for natural language generation
        5. Return answer (or raise error for fallback)
        
        Related:
        - Called by: app/services/qa_service.py
        - Context extraction: app/answer/context_extractor.py (NEW in v2.0.1)
        - System prompt: app/nlp/prompts.py::ANSWER_GENERATION_PROMPT
        """
        start_time = time.time() if log_latency else None
        
        try:
            # EARLY GUARD: Check for empty/null data BEFORE any processing
            # This prevents hallucination when database returns no results
            # IMPORTANT: Skip this for multi-metric queries (they have a different structure)
            if dsl.query_type == "metrics":
                # Skip early guard for multi-metric queries (they don't have a single "summary" field)
                is_multi_metric = isinstance(result, dict) and result.get("query_type") == "multi_metrics"
                
                if not is_multi_metric:
                    if isinstance(result, dict):
                        summary = result.get("summary")
                        breakdown = result.get("breakdown")
                    elif isinstance(result, MetricResult):
                        summary = result.summary
                        breakdown = result.breakdown
                    else:
                        summary = None
                        breakdown = None
                    
                    # If we have no summary data AND no breakdown data, return early
                    # CRITICAL: Only check for None, not == 0 (zero is valid data!)
                    if summary is None:
                        if not breakdown or (isinstance(breakdown, list) and len(breakdown) == 0):
                            timeframe_desc = getattr(dsl, 'timeframe_description', None) or ""
                            timeframe_display = _format_timeframe_display(timeframe_desc, window)
                            answer_text = f"I couldn't find any data for {dsl.metric} {timeframe_display}. You may want to try a different time period."
                            latency_ms = int((time.time() - start_time) * 1000) if log_latency and start_time else 0
                            logger.info(f"[ANSWER] No data found (early guard), returning template answer. Latency: {latency_ms}ms")
                            return answer_text, latency_ms
            
            # Step 1: Classify intent (NEW in Phase 1)
            question = getattr(dsl, 'question', None) or f"What is my {dsl.metric}?"
            intent = classify_intent(question, dsl)

            # Step 1.5: Detect tense and get timeframe
            timeframe_desc = getattr(dsl, 'timeframe_description', None) or ""
            tense = detect_tense(question, timeframe_desc)

            # Step 1.7: Build human-friendly timeframe display
            timeframe_display = _format_timeframe_display(timeframe_desc, window)

            # ==================================================================
            # OUTPUT FORMAT HANDLING (NEW v2.2)
            # If user explicitly requested table format, generate a short intro
            # ==================================================================
            output_format = getattr(dsl, 'output_format', 'auto')
            if output_format == "table":
                # User wants table - give a short intro, let the table do the talking
                answer_text = self._build_table_intro_answer(dsl, result, timeframe_display)
                latency_ms = int((time.time() - start_time) * 1000) if log_latency and start_time else 0
                logger.info(f"[ANSWER] Table format requested, returning short intro. Latency: {latency_ms}ms")
                return answer_text, latency_ms

            # ==================================================================
            # CREATIVE QUERY HANDLING (NEW v2.5)
            # For queries asking about "creatives", generate intro with Meta-only acknowledgment
            # ==================================================================
            if self._is_creative_query(dsl, result, question):
                # Check if any creatives have images
                if isinstance(result, dict):
                    breakdown = result.get("breakdown", [])
                else:
                    breakdown = result.breakdown or []
                has_images = any(item.get("thumbnail_url") or item.get("image_url") for item in breakdown)

                answer_text = self._build_creative_intro(dsl, result, timeframe_display, has_images)
                latency_ms = int((time.time() - start_time) * 1000) if log_latency and start_time else 0
                logger.info(f"[ANSWER] Creative query detected, returning intro with Meta acknowledgment. Latency: {latency_ms}ms")
                return answer_text, latency_ms

            # Step 1.6: Detect performer intent for breakdown queries (NEW in Phase 4)
            performer_intent = detect_performer_intent(question, dsl)
            
            logger.info(
                f"[INTENT] Classified as {intent.value} with {tense.value} tense and {performer_intent.value} performer intent: {explain_intent(intent)}",
                extra={
                    "question": question, 
                    "intent": intent.value, 
                    "tense": tense.value, 
                    "timeframe": timeframe_desc,
                    "performer_intent": performer_intent.value,
                    "dsl_breakdown": dsl.breakdown,
                    "dsl_top_n": dsl.top_n
                }
            )
            
            # Step 2: Extract context and build prompt based on query type and intent
            if dsl.query_type == "comparison":
                # Handle comparison queries
                return self._build_comparison_answer(dsl, result, timeframe_display, question, log_latency)
            elif dsl.query_type == "metrics":
                # Phase 7: Handle multi-metric queries
                if isinstance(result, dict) and result.get("query_type") == "multi_metrics":
                    return self._build_multi_metric_answer(dsl, result, timeframe_display, question, log_latency)

                # HALLUCINATION GUARD: If no data, return a template message.
                # CRITICAL: Only check for None, not == 0 (zero is valid data!)
                if isinstance(result, MetricResult) and result.summary is None and not result.breakdown:
                    answer_text = f"I couldn't find any data for {dsl.metric} for {timeframe_display}. You may want to try a different time period."
                    latency_ms = int((time.time() - start_time) * 1000) if log_latency and start_time else 0
                    logger.info(f"[ANSWER] No data found, returning template answer. Latency: {latency_ms}ms")
                    return answer_text, latency_ms

                # HYPOTHETICAL QUESTION GUARD: Detect if a metric_filter is being misused for a hypothetical.
                if dsl.filters and dsl.filters.metric_filters and intent == AnswerIntent.SIMPLE:
                    answer_text = "I'm sorry, but I can't answer hypothetical questions like that. I can only provide data based on your actual performance."
                    latency_ms = int((time.time() - start_time) * 1000) if log_latency and start_time else 0
                    logger.info(f"[ANSWER] Detected a hypothetical question, returning canned response. Latency: {latency_ms}ms")
                    return answer_text, latency_ms
                    
                # Single metric query - extract rich context
                context = extract_rich_context(
                    result=result,
                    query=dsl,
                    workspace_avg=result.workspace_avg if isinstance(result, MetricResult) else None
                )
                
                # Filter context based on intent (NEW in Phase 1)
                if intent == AnswerIntent.SIMPLE:
                    # SIMPLE: Only basic value, no extra context
                    filtered_context = {
                        "metric_name": context.metric_name,
                        "metric_value": context.metric_value,
                        "metric_value_raw": context.metric_value_raw,
                        "timeframe": timeframe_desc,
                        "timeframe_display": timeframe_display,  # NEW: Human-friendly timeframe
                        "tense": tense.value,
                        "performer_intent": performer_intent.value  # NEW in Phase 4
                    }
                    system_prompt = SIMPLE_ANSWER_PROMPT
                    user_prompt = self._build_simple_prompt(filtered_context, question)
                    
                elif intent == AnswerIntent.COMPARATIVE:
                    # COMPARATIVE: Include comparison + top performer, skip trends
                    filtered_context = {
                        "metric_name": context.metric_name,
                        "metric_value": context.metric_value,
                        "metric_value_raw": context.metric_value_raw,
                        "comparison": context.comparison,
                        "workspace_comparison": context.workspace_comparison,
                        "top_performer": context.top_performer,
                        "performance_level": context.performance_level,
                        "timeframe": timeframe_desc,
                        "timeframe_display": timeframe_display,  # NEW: Human-friendly timeframe
                        "tense": tense.value,
                        "performer_intent": performer_intent.value  # NEW in Phase 4
                    }
                    system_prompt = COMPARATIVE_ANSWER_PROMPT
                    user_prompt = self._build_comparative_prompt(filtered_context, question)
                    
                elif intent == AnswerIntent.LIST:
                    # LIST: Include all breakdown items, not just top performer
                    return self._build_list_answer(dsl, result, timeframe_display, question, log_latency)
                    
                else:  # ANALYTICAL
                    # ANALYTICAL: Include everything (full rich context)
                    # Add timeframe_display to rich context
                    context.timeframe_display = timeframe_display
                    system_prompt = ANALYTICAL_ANSWER_PROMPT
                    user_prompt = self._build_rich_context_prompt(context, dsl)
                
                logger.info(
                    f"[INTENT] Using {intent.value} prompt with filtered context"
                )
                
            elif dsl.query_type == "providers":
                facts = self._extract_providers_facts(result)
                system_prompt = self._build_system_prompt()
                user_prompt = self._build_user_prompt(dsl, facts)
                
            else:  # entities
                # Bypass LLM when list is reasonably small → "list means list"
                if isinstance(result, dict):
                    entities = result.get("entities", [])
                else:
                    entities = []

                if entities and len(entities) <= 25:
                    answer_text = self._build_entities_list_template(dsl, entities)
                    latency_ms = int((time.time() - start_time) * 1000) if log_latency and start_time else 0
                    logger.info(f"[ANSWER] Template answer latency: {latency_ms}ms")
                    return answer_text, latency_ms
                
                # Fallback to LLM formatting for large lists
                facts = self._extract_entities_facts(dsl, result)
                system_prompt = self._build_system_prompt()
                user_prompt = self._build_user_prompt(dsl, facts)
            
            # Step 2: Call GPT-4o-mini
            # WHY gpt-4o: Better reasoning and instruction-following
            # WHY temperature=0.3: Some naturalness, but still deterministic
            response = self.client.chat.completions.create(
                model="gpt-4o",
                temperature=0.3,  # Slightly creative for natural flow, but controlled
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=200,  # Increased from 150 to allow for richer answers (2-4 sentences)
                timeout=LLM_ANSWER_TIMEOUT_SECONDS,
            )
            
            answer_text = response.choices[0].message.content.strip()
            
            # Step 3: Calculate latency if requested (always return numeric)
            latency_ms = 0
            if log_latency and start_time:
                latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"[ANSWER] Generated {intent.value if dsl.query_type == 'metrics' else 'default'} answer "
                f"({len(answer_text)} chars) in {latency_ms}ms"
            )
            logger.info(f"[ANSWER] Answer generation latency: {latency_ms}ms")
            
            return answer_text, latency_ms
            
        except Exception as e:
            logger.error(f"Answer generation failed: {e}", exc_info=True)
            # Raise custom error so QAService knows to use fallback
            raise AnswerBuilderError(
                message=f"Answer generation failed: {str(e)}",
                original_error=e
            )
    
    def _extract_metrics_facts(
        self, 
        dsl: MetricQuery, 
        result: Union[MetricResult, Dict],
        window: Optional[Dict[str, date]] = None
    ) -> Dict[str, Any]:
        """
        Extract deterministic facts from metrics query results.
        
        WHY deterministic extraction:
        - Prevents LLM from inventing numbers
        - All facts come from validated execution results
        - Safe to pass to LLM for rephrasing only
        
        FORMATTING STRATEGY:
        - Provide BOTH raw and formatted values
        - Instruct GPT to prefer formatted values
        - This prevents GPT from inventing formatting (e.g., "$0" for CPC)
        
        NEW (v2.0): Date windows and denominators
        - Include date range for transparency ("Sep 29–Oct 05, 2025")
        - Include denominators (spend, clicks, conversions) for context
        
        Args:
            dsl: MetricQuery with query intent
            result: MetricResult or dict with summary, delta_pct, breakdown
            window: Optional date window {"start": date, "end": date}
            
        Returns:
            Dict with extracted facts ready for LLM prompt (includes formatted values, date range, denominators)
            
        Example:
            >>> facts = _extract_metrics_facts(dsl, result)
            >>> facts
            {
                "metric": "cpc",
                "value_raw": 0.4794,
                "value_formatted": "$0.48",
                "previous_value_raw": 0.3912,
                "previous_value_formatted": "$0.39",
                "change_formatted": "+22.5%",
                "top_performer": "Summer Sale"
            }
        
        Related:
        - Input: app/dsl/schema.py (MetricResult)
        - Formatters: app/answer/formatters.py (format_metric_value, format_delta_pct)
        - Used by: build_answer()
        """
        # Handle both MetricResult objects and dicts
        if isinstance(result, dict):
            summary = result.get("summary")
            previous = result.get("previous")
            delta_pct = result.get("delta_pct")
            breakdown = result.get("breakdown")
        else:
            summary = result.summary
            previous = result.previous
            delta_pct = result.delta_pct
            breakdown = result.breakdown
        
        # Format the main value
        # WHY both raw and formatted: GPT gets correct formatting, fallback has raw for math
        formatted_summary = format_metric_value(dsl.metric, summary)
        
        facts = {
            "metric": dsl.metric,
            "value_raw": summary,
            "value_formatted": formatted_summary,  # GPT should use this
        }
        
        # Add date window for transparency (NEW v2.0)
        # WHY: Users trust answers more when they know the exact time period
        # Example: "Summer Sale had highest ROAS at 3.20× from Sep 29–Oct 05, 2025"
        if window and "start" in window and "end" in window:
            date_range_str = _format_date_range(window["start"], window["end"])
            facts["date_range"] = date_range_str
        
        # Add comparison if available (with formatting)
        if previous is not None:
            formatted_previous = format_metric_value(dsl.metric, previous)
            facts["previous_value_raw"] = previous
            facts["previous_value_formatted"] = formatted_previous  # GPT should use this
        
        if delta_pct is not None:
            # Format percentage change with sign
            formatted_delta = format_delta_pct(delta_pct)
            facts["change_raw"] = delta_pct
            facts["change_formatted"] = formatted_delta  # GPT should use this
        
        # Add top performer if breakdown exists
        # WHY: Gives context for "which campaign drove this?"
        if breakdown and len(breakdown) > 0:
            top = breakdown[0]
            facts["top_performer"] = top.get("label")
            # Also format the top performer's value
            if "value" in top:
                facts["top_performer_value_formatted"] = format_metric_value(
                    dsl.metric, 
                    top.get("value")
                )
            
            # NEW v2.0: Include denominators for context
            # WHY: Helps explain results in natural language
            # Example: "Summer Sale had ROAS 3.20× (Spend $1,234, Revenue $3,948)"
            denominators = []
            if "spend" in top and top.get("spend"):
                denominators.append(f"Spend {fmt_currency(top['spend'])}")
            if "revenue" in top and top.get("revenue"):
                denominators.append(f"Revenue {fmt_currency(top['revenue'])}")
            if "clicks" in top and top.get("clicks"):
                denominators.append(f"{fmt_count(top['clicks'])} clicks")
            if "conversions" in top and top.get("conversions"):
                denominators.append(f"{fmt_count(top['conversions'])} conversions")
            
            if denominators:
                facts["top_performer_context"] = ", ".join(denominators)
            
            # Special handling for top_n=1 queries (e.g., "Which campaign had highest ROAS?")
            # This makes the answer focus on the specific entity rather than overall summary
            if dsl.top_n == 1 and dsl.breakdown:
                facts["query_intent"] = "highest_by_metric"
                facts["breakdown_level"] = dsl.breakdown  # e.g., "campaign"
                facts["metric_display"] = dsl.metric.upper()  # e.g., "ROAS"
        
        return facts
    
    def _extract_providers_facts(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract facts from providers query results.
        
        Args:
            result: Dict with "providers" list
            
        Returns:
            Dict with provider facts for LLM
            
        Example:
            >>> facts = _extract_providers_facts({"providers": ["google", "meta"]})
            >>> facts
            {"platforms": ["Google", "Meta"], "count": 2}
        
        Related:
        - Input: app/dsl/executor.py (providers query result)
        - Used by: build_answer()
        """
        providers = result.get("providers", [])
        
        # Capitalize provider names for display
        formatted_providers = [p.capitalize() for p in providers]
        
        return {
            "platforms": formatted_providers,
            "count": len(formatted_providers)
        }
    
    def _extract_entities_facts(
        self, 
        dsl: MetricQuery, 
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract facts from entities query results.
        
        Args:
            dsl: MetricQuery with filters (level, status)
            result: Dict with "entities" list
            
        Returns:
            Dict with entity facts for LLM
            
        Example:
            >>> facts = _extract_entities_facts(dsl, result)
            >>> facts
            {
                "entity_type": "campaigns",
                "status": "active",
                "entity_names": ["Summer Sale", "Winter Promo"],
                "count": 2
            }
        
        Related:
        - Input: app/dsl/executor.py (entities query result)
        - Used by: build_answer()
        """
        entities = result.get("entities", [])
        
        # Determine entity type from filters
        level = dsl.filters.level if dsl.filters and dsl.filters.level else "entities"
        level_plural = level if level.endswith("s") else f"{level}s"
        
        # Extract entity names
        entity_names = [e.get("name") for e in entities if e.get("name")]
        
        facts = {
            "entity_type": level_plural,
            "entity_names": entity_names,
            "count": len(entity_names)
        }
        
        # Add status filter if present
        if dsl.filters and dsl.filters.status:
            facts["status"] = dsl.filters.status
        
        return facts

    def _build_entities_list_template(self, dsl: MetricQuery, entities: list[Dict[str, Any]]) -> str:
        """
        Deterministic, numbered list output for entities queries when N is small.
        """
        level = dsl.filters.level if dsl.filters and dsl.filters.level else "entities"
        level_plural = level if level.endswith("s") else f"{level}s"
        header = f"Here are your {len(entities)} {level_plural}:"
        lines = []
        for idx, e in enumerate(entities, start=1):
            name = e.get("name") or "Unnamed"
            lines.append(f"{idx}. {name}")
        body = "\n".join(lines)
        return f"{header}\n{body}"
    
    def _build_system_prompt(self) -> str:
        """
        Build system prompt with strict safety instructions.
        
        WHY strict instructions:
        - Prevent LLM from inventing numbers
        - Ensure only provided facts are used
        - Keep answers conversational but accurate
        
        FORMATTING INSTRUCTIONS:
        - Always prefer *_formatted fields over *_raw fields
        - This prevents GPT from inventing formatting (e.g., "$0" for CPC = 0.48)
        - Formatted fields come from app/answer/formatters.py (single source of truth)
        
        Returns:
            System prompt string
            
        Instructions prioritized by importance:
        1. No number invention (CRITICAL for trust)
        2. Use formatted values when available (prevents formatting errors)
        3. Use only provided facts (prevents hallucinations)
        4. Natural tone (user experience)
        5. Concise (2-3 sentences)
        
        Related:
        - Pattern inspired by: app/nlp/prompts.py (DSL translation prompt)
        - Used by: build_answer()
        """
        return """You are a helpful marketing analytics assistant.

Your job is to rephrase data facts into natural, conversational answers.

CRITICAL RULES:
1. Do NOT invent numbers or make up facts
2. Use ONLY the facts provided in the user message
3. ALWAYS prefer *_formatted fields over *_raw fields (e.g., use "value_formatted" not "value_raw")
4. If a fact is missing or None, gracefully omit it
5. Keep answers concise (2-3 sentences maximum)
6. Sound like a helpful colleague, not a robot
7. Do NOT apply your own formatting - the formatted values are already correct

WHY formatted fields matter:
- They come from our formatting system (currency, ratios, percentages)
- Using raw values causes errors like "$0" when the value is "$0.48"
- Always trust the formatted values

Examples:
- Given: {"metric": "cpc", "value_formatted": "$0.48", "change_formatted": "+15.5%"}
  Answer: "Your CPC is $0.48, up 15.5% from the previous period."
  
- Given: {"metric": "roas", "value_formatted": "2.45×", "top_performer": "Summer Sale"}
  Answer: "Your ROAS is 2.45×, with Summer Sale as the top performer."
  
- Given: {"platforms": ["Google", "Meta"], "count": 2}
  Answer: "You're running ads on Google and Meta."
  
- Given: {"query_intent": "highest_by_metric", "breakdown_level": "campaign", "metric_display": "ROAS", 
           "top_performer": "Summer Sale", "top_performer_value_formatted": "3.20×", "date_range": "Sep 29–Oct 05, 2025"}
  Answer: "Summer Sale had the highest ROAS at 3.20× from Sep 29–Oct 05, 2025."
  
- Given: {"query_intent": "highest_by_metric", "breakdown_level": "provider", "metric_display": "CPC",
           "top_performer": "Google", "top_performer_value_formatted": "$0.32", "date_range": "Oct 01–07, 2025",
           "top_performer_context": "Spend $1,234.56, 3,850 clicks", "value_formatted": "$0.45"}
  Answer: "Google had the best CPC at $0.32 from Oct 01–07, 2025 (Spend $1,234.56, 3,850 clicks). Overall CPC was $0.45."

INTENT-FIRST RULE for "highest_by_metric":
- When query_intent is "highest_by_metric", LEAD with the top_performer and their value
- Include date_range for transparency
- Optionally mention top_performer_context (spend, clicks, etc.) in parentheses
- Optionally mention overall value_formatted as context at the end

Remember: Be helpful and natural, but never invent data or formatting."""
    
    def _build_rich_context_prompt(self, context, dsl: MetricQuery) -> str:
        """
        Build user prompt with rich context (NEW in v2.0.1).
        
        WHY this exists:
        - Provides GPT with all context in organized format
        - Enables natural language generation from deterministic insights
        - Performance level guides tone selection
        
        Args:
            context: RichContext object from context_extractor
            dsl: MetricQuery (for original question if available)
            
        Returns:
            Structured prompt with JSON context + instructions
            
        Example output:
            Generate a natural language answer for this marketing metric query.
            
            CONTEXT:
            {
              "metric_name": "ROAS",
              "metric_value": "2.45×",
              "comparison": {...},
              "workspace_comparison": {...},
              "performance_level": "good"
            }
            
            USER QUESTION: "What's my ROAS this week?"
            
            INSTRUCTIONS: ...
        
        Related:
        - Uses: context.to_dict() from RichContext
        - Used by: build_answer() for metrics queries
        """
        context_json = json.dumps(context.to_dict(), indent=2)
        
        # Try to extract original question if available
        original_question = getattr(dsl, 'question', None) or f"What is my {context.metric_name}?"
        
        return f"""Generate a natural language answer for this marketing metric query.

CONTEXT:
{context_json}

USER QUESTION: "{original_question}"

INSTRUCTIONS:
- Lead with the main metric value and what it means
- If comparison data exists, describe how the metric changed
- If workspace_comparison exists, mention how this compares to average
- If trend data exists, describe the pattern over time
- If top_performer exists, highlight which entity performed best
- If outliers exist, mention notable anomalies
- Match tone to performance_level: {context.performance_level}
  - EXCELLENT/GOOD: Positive, encouraging tone
  - AVERAGE: Neutral, factual tone
  - POOR/CONCERNING: Constructive, problem-solving tone
- Use formatted values (not raw numbers) from the context
- Keep answer concise: 2-4 sentences maximum
- Be conversational but professional
- DO NOT invent any numbers or data not in the context

EXAMPLE TONE FOR PERFORMANCE LEVELS:
- EXCELLENT: "Your ROAS is performing excellently at..."
- GOOD: "Your ROAS is doing well at..."
- AVERAGE: "Your ROAS is stable at..."
- POOR: "Your ROAS has room for improvement at..."
- CONCERNING: "Your ROAS needs attention—it's currently at..."
"""
    
    def _build_user_prompt(self, dsl: MetricQuery, facts: Dict[str, Any]) -> str:
        """
        Build user prompt with extracted facts (legacy for providers/entities).
        
        NOTE: Metrics queries now use _build_rich_context_prompt() (v2.0.1)
        
        Args:
            dsl: MetricQuery (for context)
            facts: Extracted facts dict
            
        Returns:
            User prompt with facts and request
            
        Format:
        - Clear fact presentation
        - Simple request ("rephrase these facts")
        - No ambiguity
        
        Related:
        - Facts from: _extract_*_facts() methods
        - Used by: build_answer() for providers/entities queries
        """
        return f"""Here are the facts about this query:

Query type: {dsl.query_type}
Facts: {facts}

Please rephrase these facts into a natural, helpful answer for a marketer.
Remember: Use only the provided facts, do not invent any numbers."""
    
    def _build_simple_prompt(self, context: Dict[str, Any], question: str) -> str:
        """
        Build user prompt for SIMPLE intent answers.
        
        WHY: Simple questions need minimal context to avoid verbose answers
        WHAT: Only includes metric name and value, nothing else
        WHERE: Called by build_answer() when intent=SIMPLE
        
        Args:
            context: Filtered context with only basic fields
            question: Original user question
            
        Returns:
            Minimal prompt for GPT
            
        Example:
            context = {
                "metric_name": "ROAS",
                "metric_value": "3.88×",
                "metric_value_raw": 3.88
            }
            
            Output prompt:
            "The user asked: 'what was my roas last month'
             
             Answer with ONE sentence stating the fact:
             Metric: ROAS
             Value: 3.88×"
        """
        return f"""The user asked: "{question}"

Answer with ONE sentence stating the fact.

CONTEXT:
{json.dumps(context, indent=2)}

Remember: Just the fact. One sentence. No analysis."""
    
    def _build_comparative_prompt(self, context: Dict[str, Any], question: str) -> str:
        """
        Build user prompt for COMPARATIVE intent answers.
        
        WHY: Comparative questions need comparison context but not full analysis
        WHAT: Includes metric value, comparison data, and top performer
        WHERE: Called by build_answer() when intent=COMPARATIVE
        
        Args:
            context: Filtered context with comparison fields
            question: Original user question
            
        Returns:
            Moderate prompt for GPT with comparison context
        """
        # Filter out None values
        filtered = {k: v for k, v in context.items() if v is not None}
        
        return f"""The user asked: "{question}"

Provide a natural answer with comparison context (2-3 sentences).

CONTEXT:
{json.dumps(filtered, indent=2)}

Remember: Include comparison, keep it conversational, 2-3 sentences max."""

    def _build_multi_metric_answer(
        self,
        dsl: MetricQuery,
        result: Dict[str, Any],
        timeframe_display: str,
        question: str,
        log_latency: bool = False
    ) -> tuple[str, Optional[int]]:
        """
        Build answer for multi-metric queries (Phase 7).
        
        Args:
            dsl: The MetricQuery that was executed
            result: Multi-metric result dict with structure:
                {
                    "metrics": {
                        "spend": {"summary": 1000.0, "previous": 900.0, "delta_pct": 11.1},
                        "revenue": {"summary": 2000.0, "previous": 1800.0, "delta_pct": 11.1},
                        "roas": {"summary": 2.0, "previous": 2.0, "delta_pct": 0.0}
                    },
                    "query_type": "multi_metrics"
                }
            timeframe_display: Human-friendly timeframe string
            question: Original user question
            log_latency: Whether to return latency in ms
            
        Returns:
            tuple: (answer_text, latency_ms) if log_latency=True, else (answer_text, None)
        """
        start_time = time.time() if log_latency else None
        
        try:
            # Build context for multi-metric answer
            metrics_data = result.get("metrics", {})
            
            # Format each metric value
            formatted_metrics = {}
            for metric_name, metric_data in metrics_data.items():
                summary_value = metric_data.get("summary")
                previous_value = metric_data.get("previous")
                delta_pct = metric_data.get("delta_pct")
                
                if summary_value is not None:
                    formatted_value = format_metric_value(metric_name, summary_value)
                    formatted_metrics[metric_name] = {
                        "value": formatted_value,
                        "raw_value": summary_value,
                        "previous": previous_value,
                        "delta_pct": delta_pct
                    }
            
            # Build context for LLM (include breakdown if available)
            breakdown = result.get("breakdown")

            # Helper to convert Decimal to float for JSON serialization
            def convert_decimals(obj):
                if isinstance(obj, dict):
                    return {k: convert_decimals(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimals(item) for item in obj]
                elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'Decimal':
                    return float(obj)
                else:
                    return obj

            context = {
                "metrics": formatted_metrics,
                "timeframe_display": timeframe_display,
                "question": question,
                "metric_count": len(formatted_metrics)
            }

            # Add breakdown data if available (convert Decimals for JSON serialization)
            if breakdown and len(breakdown) > 0:
                context["breakdown"] = convert_decimals(breakdown)
                context["breakdown_dimension"] = dsl.breakdown if dsl.breakdown else None
            
            # Determine if this is a breakdown-focused query (e.g., "top 5 ads")
            is_breakdown_focused = breakdown and len(breakdown) > 0 and dsl.breakdown
            output_format = getattr(dsl, 'output_format', 'auto')

            # Use analytical prompt for multi-metric answers
            system_prompt = ANALYTICAL_ANSWER_PROMPT

            # Different instructions based on query type
            # Check if metric was auto-inferred (user didn't specify)
            metric_inferred = getattr(dsl, 'metric_inferred', False)
            first_metric = list(metrics_data.keys())[0] if metrics_data else "spend"

            if is_breakdown_focused and output_format in ['chart', 'table']:
                # User wants to see breakdown items (e.g., "graph of top 5 ads")
                # Focus on the breakdown, not workspace totals

                # Build metric clarification instruction
                metric_clarification_instruction = ""
                if metric_inferred:
                    metric_clarification_instruction = f"""
7. IMPORTANT: The metric "{first_metric}" was automatically selected for sorting since the user didn't specify one.
   You MUST clarify this in your answer! Example: "sorted by {first_metric}" or "ranked by {first_metric} (since no specific metric was requested)"
"""

                user_prompt = f"""
Generate a natural, conversational answer for a breakdown query.

QUESTION: {question}

DATA:
{json.dumps(context, indent=2)}

CRITICAL INSTRUCTIONS:
1. The user asked for a breakdown by {context.get('breakdown_dimension', 'items')} - focus on THOSE items
2. List the top {len(breakdown)} items from the breakdown with their values
3. Do NOT prominently show workspace totals (metrics.summary values) - the breakdown IS the answer
4. Use the timeframe_display for timeframe context
5. Be conversational and brief - the visual (chart/table) will show the details
6. Keep metric_inferred in mind: {metric_inferred}
{metric_clarification_instruction}
Example good answer: "Here are your top {len(breakdown)} {context.get('breakdown_dimension', 'items')} by {first_metric} {timeframe_display}."

Answer:"""
            else:
                # Standard multi-metric query
                user_prompt = f"""
Generate a natural, conversational answer for a multi-metric query.

QUESTION: {question}

METRICS DATA:
{json.dumps(context, indent=2)}

INSTRUCTIONS:
1. Include ALL requested metrics in your answer with their values
2. Use the timeframe_display for timeframe context
3. Keep it conversational and natural
4. If there are comparisons available, include them briefly
5. Format numbers appropriately (currency, percentages, etc.)
6. If breakdown data is provided, include the top performing items in your answer
7. Keep the answer concise but comprehensive - ensure ALL metrics are listed with values

Answer:"""
            
            # Call LLM
            client = OpenAI(api_key=get_settings().OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                timeout=LLM_ANSWER_TIMEOUT_SECONDS,
            )

            answer = response.choices[0].message.content.strip()

            # Calculate latency if requested
            latency_ms = 0  # Always return numeric (0 for LLM success)
            if log_latency and start_time:
                latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"[MULTI_METRIC_ANSWER] Generated answer for {len(formatted_metrics)} metrics")
            logger.info(f"[MULTI_METRIC_ANSWER] Answer generation latency: {latency_ms}ms")
            return answer, latency_ms
            
        except Exception as e:
            logger.error(f"[MULTI_METRIC_ANSWER] Failed to generate answer: {e}")
            # Fallback to simple template (always return 0 latency for template)
            template_answer = self._build_multi_metric_template_answer(dsl, result, timeframe_display)
            logger.info(f"[MULTI_METRIC_ANSWER] Using template fallback (latency: 0ms)")
            return template_answer, 0
    
    def _build_list_template_answer(
        self,
        dsl: MetricQuery,
        breakdown: list,
        timeframe_display: str,
        log_latency: bool,
        start_time: Optional[float]
    ) -> tuple[str, Optional[int]]:
        """
        Deterministic template-based answer for large lists (>10 items).

        PERFORMANCE: This is INSTANT (0ms) vs 15-20 seconds for LLM formatting.

        WHY: When users ask "show me all ads with CPC below $1", they want a list, not prose.
        A simple numbered list is clearer and 1000x faster than LLM-generated paragraphs.

        UPDATED v2.4: Include metric clarification when metric was auto-inferred.

        Args:
            dsl: The MetricQuery
            breakdown: List of breakdown items
            timeframe_display: Human-friendly timeframe
            log_latency: Whether to track latency
            start_time: Start time for latency calculation

        Returns:
            tuple: (answer_text, latency_ms)
        """
        metric_name = dsl.metric
        breakdown_dimension = dsl.breakdown
        metric_inferred = getattr(dsl, 'metric_inferred', False)

        # Build header
        has_metric_filter = (dsl.filters and
                            hasattr(dsl.filters, 'metric_filters') and
                            dsl.filters.metric_filters)

        if has_metric_filter:
            filter_desc = dsl.filters.metric_filters[0]
            operator_text = {
                ">": "above",
                ">=": "at least",
                "<": "below",
                "<=": "at most",
                "=": "equal to",
                "!=": "not equal to"
            }.get(filter_desc.get("operator"), "")
            
            filter_metric = filter_desc.get("metric")
            filter_value = filter_desc.get("value")
            
            # Format the filter value
            if filter_metric in ['cpc', 'cpa', 'cpl', 'cpi', 'cpp', 'cpm', 'revenue', 'spend', 'profit']:
                filter_value_str = f"${filter_value:,.2f}" if filter_value else str(filter_value)
            elif filter_metric in ['roas', 'poas']:
                filter_value_str = f"{filter_value}×"
            elif filter_metric in ['ctr', 'cvr']:
                filter_value_str = f"{filter_value}%"
            else:
                filter_value_str = f"{filter_value:,}"
            
            header = f"Here are the {breakdown_dimension}s {timeframe_display} with {filter_metric.upper()} {operator_text} {filter_value_str}:"
        else:
            # Add clarification if metric was inferred
            metric_note = ""
            if metric_inferred:
                metric_note = " (sorted by this metric since no specific metric was requested)"
            header = f"Here are the top {len(breakdown)} {breakdown_dimension}s by {metric_name.upper()} {timeframe_display}{metric_note}:"
        
        # Build numbered list
        lines = [header, ""]
        for idx, item in enumerate(breakdown, start=1):
            label = item.get("label", "Unknown")
            value = item.get("value")
            
            # Format value
            formatted_value = format_metric_value(metric_name, value) if value is not None else "N/A"
            
            lines.append(f"{idx}. {label}: {formatted_value}")
        
        answer_text = "\n".join(lines)
        
        # Calculate latency
        latency_ms = 0
        if log_latency and start_time:
            latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"[LIST_TEMPLATE] Built list with {len(breakdown)} items in {latency_ms}ms")
        return answer_text, latency_ms
    
    def _build_multi_metric_template_answer(
        self,
        dsl: MetricQuery,
        result: Dict[str, Any],
        timeframe_display: str
    ) -> str:
        """
        Fallback template-based answer for multi-metric queries.

        This provides a simple, deterministic answer when LLM fails.

        UPDATED v2.3: For breakdown-focused queries (e.g., "graph of top 5 ads"),
        focus on the breakdown items, not workspace totals.

        UPDATED v2.4: Include metric clarification when metric was auto-inferred.
        """
        metrics_data = result.get("metrics", {})
        breakdown = result.get("breakdown")
        output_format = getattr(dsl, 'output_format', 'auto')
        breakdown_dimension = dsl.breakdown if dsl.breakdown else "items"
        metric_inferred = getattr(dsl, 'metric_inferred', False)

        # Determine if this is a breakdown-focused query
        is_breakdown_focused = breakdown and len(breakdown) > 0 and output_format in ['chart', 'table']

        if is_breakdown_focused:
            # User asked for a chart/table of breakdown items - focus on those
            # Determine which metric to use for display
            first_metric = list(metrics_data.keys())[0] if metrics_data else "value"

            # Build breakdown list
            breakdown_lines = []
            for item in breakdown:
                label = item.get("label", "Unknown")
                value = item.get("value")
                if value is not None:
                    formatted_value = format_metric_value(first_metric, value)
                    breakdown_lines.append(f"  - {label}: {formatted_value}")

            if not breakdown_lines:
                return f"No data available for {timeframe_display if timeframe_display else 'the selected period'}."

            timeframe_text = f" {timeframe_display}" if timeframe_display else ""

            # Add clarification if metric was inferred
            metric_note = ""
            if metric_inferred:
                metric_note = f" (sorted by {first_metric} since no specific metric was requested)"

            header = f"Here are your top {len(breakdown)} {breakdown_dimension}s by {first_metric}{timeframe_text}{metric_note}:"

            return header + "\n" + "\n".join(breakdown_lines)

        # Standard multi-metric answer (show workspace totals + optional breakdown)
        if not metrics_data:
            return f"No data available for {timeframe_display if timeframe_display else 'the selected period'}."

        # Build simple list of metrics with values
        metric_lines = []
        for metric_name, metric_data in metrics_data.items():
            summary_value = metric_data.get("summary")
            if summary_value is not None:
                formatted_value = format_metric_value(metric_name, summary_value)
                previous_value = metric_data.get("previous")
                delta_pct = metric_data.get("delta_pct")

                # Include comparison if available
                if previous_value is not None and delta_pct is not None:
                    change_text = f" ({delta_pct:+.1f}% vs previous period)"
                    metric_lines.append(f"• {metric_name.upper()}: {formatted_value}{change_text}")
                else:
                    metric_lines.append(f"• {metric_name.upper()}: {formatted_value}")

        if not metric_lines:
            return f"No data available for {timeframe_display if timeframe_display else 'the selected period'}."

        # Add breakdown if available (but not as the main focus)
        breakdown_text = ""
        if breakdown and len(breakdown) > 0:
            breakdown_lines = []
            for item in breakdown[:5]:  # Top 5 items
                label = item.get("label", "Unknown")
                value = item.get("value")
                if value is not None:
                    # Format value using first metric if available
                    first_metric = list(metrics_data.keys())[0] if metrics_data else None
                    if first_metric:
                        formatted_value = format_metric_value(first_metric, value)
                    else:
                        formatted_value = f"{value:,.2f}"
                    breakdown_lines.append(f"  - {label}: {formatted_value}")

            if breakdown_lines:
                breakdown_text = f"\n\nTop {breakdown_dimension.upper()}:\n" + "\n".join(breakdown_lines)

        # Combine into answer
        metrics_text = "\n".join(metric_lines)
        timeframe_text = f" {timeframe_display}" if timeframe_display else ""

        return f"Here are your metrics{timeframe_text}:\n\n{metrics_text}{breakdown_text}"

    def _build_comparison_answer(
        self,
        dsl: MetricQuery,
        result: Dict[str, Any],
        timeframe_display: str,
        question: str,
        log_latency: bool = False
    ) -> tuple[str, Optional[int]]:
        """
        Build answer for comparison queries.
        
        Args:
            dsl: The MetricQuery with comparison fields
            result: Comparison results dict
            timeframe_display: Human-friendly timeframe
            question: Original user question
            log_latency: Whether to track latency
            
        Returns:
            Tuple of (answer_text, latency_ms)
        """
        start_time = time.time() if log_latency else None
        
        try:
            comparison_data = result.get("comparison", [])
            comparison_type = result.get("comparison_type", "unknown")
            metrics = result.get("metrics", [])
            
            if not comparison_data:
                latency_ms = 0 if log_latency else 0
                return "It looks like there are currently no entities to compare, as the count is 0. Let me know if you need help with anything else!", latency_ms
            
            # Convert Decimal values to float for JSON serialization
            def convert_decimals(obj):
                if isinstance(obj, dict):
                    return {k: convert_decimals(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimals(item) for item in obj]
                elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'Decimal':
                    return float(obj)
                else:
                    return obj
            
            # Build context for GPT
            context = {
                "comparison_type": comparison_type,
                "metrics": metrics,
                "timeframe": timeframe_display,
                "comparison_data": convert_decimals(comparison_data)
            }
            
            # Build prompt
            prompt = f"""The user asked: "{question}"

Provide a natural comparison answer based on the data below.

COMPARISON DATA:
{json.dumps(context, indent=2)}

INSTRUCTIONS:
1. Compare the entities/providers based on the requested metrics
2. Use the timeframe_display for timeframe context
3. Keep it conversational and natural
4. Highlight which entity/provider performed better for each metric
5. Format numbers appropriately (percentages, ratios, etc.)
6. Keep the answer concise but informative

Answer:"""
            
            # Call GPT
            client = OpenAI(api_key=get_settings().OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful marketing analytics assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300,
                timeout=LLM_ANSWER_TIMEOUT_SECONDS,
            )

            answer = response.choices[0].message.content.strip()

            if log_latency:
                latency_ms = int((time.time() - start_time) * 1000)
                return answer, latency_ms
            else:
                return answer, None
                
        except Exception as e:
            logger.error(f"[COMPARISON_ANSWER] Failed to build comparison answer: {e}")
            raise AnswerBuilderError(f"Failed to build comparison answer: {e}")

    def _build_table_intro_answer(
        self,
        dsl: MetricQuery,
        result: Union[MetricResult, Dict[str, Any]],
        timeframe_display: str
    ) -> str:
        """
        Build a short intro answer when user explicitly requested table format.

        NEW in v2.2: When output_format="table", we generate a brief intro
        and let the table visual do the heavy lifting.

        Args:
            dsl: The MetricQuery with metric and breakdown info
            result: Metric results
            timeframe_display: Human-friendly timeframe

        Returns:
            Short intro text that complements the table

        Examples:
            "Here's a breakdown of your campaigns by ROAS for last week:"
            "Here's your campaign performance in table format:"
        """
        metric = dsl.metric if isinstance(dsl.metric, str) else (dsl.metric[0] if dsl.metric else "metrics")
        breakdown = dsl.breakdown or "campaign"

        # Get count of items - check both breakdown AND comparison data
        # WHY: Regular metrics queries use "breakdown", comparison queries use "comparison"
        if isinstance(result, dict):
            breakdown_data = result.get("breakdown", [])
            # Also check for comparison data (entity_vs_entity queries)
            if not breakdown_data:
                breakdown_data = result.get("comparison", [])
        elif isinstance(result, MetricResult):
            breakdown_data = result.breakdown or []
        else:
            breakdown_data = []

        count = len(breakdown_data)

        # Build metric display name
        metric_names = {
            "roas": "ROAS", "cpa": "CPA", "cpc": "CPC", "cpm": "CPM",
            "cpl": "CPL", "ctr": "CTR", "cvr": "CVR", "spend": "spend",
            "revenue": "revenue", "clicks": "clicks", "conversions": "conversions"
        }
        metric_display = metric_names.get(metric.lower(), metric) if metric else "performance"

        # Build breakdown display name
        breakdown_names = {
            "campaign": "campaigns", "adset": "ad sets", "ad": "ads",
            "provider": "platforms", "day": "days", "week": "weeks", "month": "months"
        }
        breakdown_display = breakdown_names.get(breakdown, f"{breakdown}s")

        # Build the intro
        if count > 0:
            timeframe_part = f" {timeframe_display}" if timeframe_display else ""
            return f"Here's a breakdown of your {count} {breakdown_display} by {metric_display}{timeframe_part}:"
        else:
            return f"I couldn't find any {breakdown_display} to display in a table{' ' + timeframe_display if timeframe_display else ''}."

    def _build_list_answer(
        self,
        dsl: MetricQuery,
        result: Dict[str, Any],
        timeframe_display: str,
        question: str,
        log_latency: bool = False
    ) -> tuple[str, Optional[int]]:
        """
        Build answer for list queries.
        
        PERFORMANCE OPTIMIZATION (2025-10-29):
        - For lists with >10 items, use deterministic template (instant, 0ms)
        - For lists with <=10 items, use LLM for natural formatting
        - This prevents 15-20 second latency when formatting large lists
        
        Args:
            dsl: The MetricQuery with breakdown fields
            result: Metric results with breakdown data
            timeframe_display: Human-friendly timeframe
            question: Original user question
            log_latency: Whether to track latency
            
        Returns:
            Tuple of (answer_text, latency_ms)
        """
        start_time = time.time() if log_latency else None
        
        try:
            # Handle both dict and MetricResult objects
            if isinstance(result, dict):
                breakdown = result.get("breakdown", [])
            else:
                breakdown = result.breakdown or []
            metric_name = dsl.metric
            top_n = dsl.top_n or 5
            
            # PERFORMANCE OPTIMIZATION: Use template for large lists (>10 items)
            # WHY: LLM takes 15-20 seconds to format 30 items, template is instant
            if breakdown and len(breakdown) > 10:
                return self._build_list_template_answer(dsl, breakdown, timeframe_display, log_latency, start_time)
            
            if not breakdown:
                # Check if metric filters were applied
                metric_filters = getattr(dsl.filters, 'metric_filters', None) if dsl.filters else None
                
                if metric_filters and self.db:
                    # Get workspace_id from dsl or result
                    workspace_id = getattr(dsl, 'workspace_id', None)
                    
                    if workspace_id:
                        # Get total entity count (unfiltered)
                        total_count = self._get_entity_count_for_breakdown(
                            workspace_id=workspace_id,
                            breakdown_dimension=dsl.breakdown,
                            status=getattr(dsl.filters, 'status', None) if dsl.filters else None
                        )
                        
                        # Build context for LLM to interpret
                        filter_descriptions = []
                        for f in metric_filters:
                            filter_descriptions.append({
                                "metric": f.get("metric"),
                                "operator": f.get("operator"),
                                "value": f.get("value")
                            })
                        
                        context = {
                            "question": question,
                            "metric": metric_name,
                            "timeframe": timeframe_display,
                            "breakdown_dimension": dsl.breakdown,
                            "filters": filter_descriptions,
                            "total_entities": total_count,
                            "result_count": 0
                        }
                        
                        # Build prompt for LLM to interpret empty result
                        prompt = f"""The user asked: "{question}"

The query returned 0 results after applying filters, but {total_count} total entities exist in the workspace.

CONTEXT:
{json.dumps(context, indent=2)}

TASK: Provide a natural, context-aware explanation for why no results were returned.

Consider:
1. If total_entities > 0 and result_count = 0, determine if this is:
   - POSITIVE: All entities already exceed/meet the threshold (e.g., ">" operator with 0 results = all entities are above threshold)
   - NEGATIVE: No entities meet the criteria (e.g., "<" operator with 0 results = no entities are below threshold)
2. Examine the operator direction to determine positive vs negative
3. Be specific about the filter criteria
4. Keep it conversational and concise (1-2 sentences)

EXAMPLES of good responses:
- "Great news! All 10 of your campaigns already have a conversion rate above 5%."
- "None of your 8 campaigns currently meet the spend threshold of $1,000."
- "You don't have any campaigns with ROAS below 2.0—they're all performing well!"

Answer:"""
                        
                        # Call GPT for intelligent interpretation
                        try:
                            response = self.client.chat.completions.create(
                                model="gpt-4o",
                                messages=[
                                    {"role": "system", "content": "You are a helpful marketing analytics assistant. Interpret empty query results intelligently and provide context-aware explanations."},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=0.3,
                                max_tokens=150,
                                timeout=LLM_ANSWER_TIMEOUT_SECONDS,
                            )
                            
                            answer = response.choices[0].message.content.strip()
                            
                            if log_latency:
                                latency_ms = int((time.time() - start_time) * 1000)
                                return answer, latency_ms
                            else:
                                return answer, None
                                
                        except Exception as e:
                            logger.error(f"[ANSWER_BUILDER] LLM interpretation failed: {e}")
                            # Fallback to generic message if LLM fails
                
                # Default fallback for non-filter cases or when context unavailable
                return f"No data available for {timeframe_display if timeframe_display else 'the selected period'}.", None
            
            # Convert Decimal values to float for JSON serialization
            def convert_decimals(obj):
                if isinstance(obj, dict):
                    return {k: convert_decimals(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimals(item) for item in obj]
                elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'Decimal':
                    return float(obj)
                else:
                    return obj
            
            # Check if metric was auto-inferred
            metric_inferred = getattr(dsl, 'metric_inferred', False)

            # Build context for GPT
            context = {
                "metric_name": metric_name,
                "timeframe": timeframe_display,
                "top_n": top_n,
                "breakdown": convert_decimals(breakdown),
                "total_items": len(breakdown),
                "metric_inferred": metric_inferred
            }

            # Build metric clarification instruction
            metric_clarification_instruction = ""
            if metric_inferred:
                metric_clarification_instruction = f"""
8. IMPORTANT: The metric "{metric_name}" was automatically selected for sorting since the user didn't specify one.
   You MUST clarify this in your answer! Example: "sorted by {metric_name}" or "ranked by {metric_name} (since no specific metric was requested)"
"""

            # Build prompt
            prompt = f"""The user asked: "{question}"

Provide a natural list answer based on the breakdown data below.

BREAKDOWN DATA:
{json.dumps(context, indent=2)}

INSTRUCTIONS:
1. List ALL items in the breakdown (not just the top performer)
2. Use the timeframe_display for timeframe context
3. Keep it conversational and natural
4. Format numbers appropriately (currency, percentages, etc.)
5. Include the metric value for each item
6. Mention the total count if relevant
7. Keep the answer concise but comprehensive - focus on the key metrics, not every detail
{metric_clarification_instruction}
Answer:"""
            
            # Call GPT
            client = OpenAI(api_key=get_settings().OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful marketing analytics assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                timeout=LLM_ANSWER_TIMEOUT_SECONDS,
            )

            answer = response.choices[0].message.content.strip()

            if log_latency:
                latency_ms = int((time.time() - start_time) * 1000)
                return answer, latency_ms
            else:
                return answer, None
                
        except Exception as e:
            logger.error(f"[LIST_ANSWER] Failed to build list answer: {e}")
            raise AnswerBuilderError(f"Failed to build list answer: {e}")

    def _is_creative_query(self, dsl: MetricQuery, result: Union[MetricResult, Dict[str, Any]], question: str) -> bool:
        """
        Detect if this is a creative query (asking for ad creatives).

        Returns True if:
        - Breakdown is at "ad" level, AND
        - Question mentions "creative(s)" or explicitly asks for ad images

        This triggers special handling with Meta-only acknowledgment.
        """
        # Check breakdown type
        breakdown_type = getattr(dsl, 'breakdown', None)
        if breakdown_type != "ad":
            return False

        # Check if question mentions creatives
        question_lower = question.lower()
        creative_keywords = ["creative", "creatives", "ad image", "ad images", "thumbnail", "visual"]
        return any(kw in question_lower for kw in creative_keywords)

    def _build_creative_intro(
        self,
        dsl: MetricQuery,
        result: Union[MetricResult, Dict[str, Any]],
        timeframe_display: str,
        has_images: bool
    ) -> str:
        """
        Build introduction text for creative query answers.

        IMPORTANT: Acknowledges that creative images are only available for Meta ads.

        Args:
            dsl: The MetricQuery
            result: Metric results with breakdown
            timeframe_display: Human-readable timeframe
            has_images: Whether any creatives have image URLs

        Returns:
            Intro text acknowledging Meta-only limitation if relevant
        """
        # Get breakdown data
        if isinstance(result, dict):
            breakdown = result.get("breakdown", [])
        else:
            breakdown = result.breakdown or []

        count = len(breakdown)
        metric = dsl.metric or "spend"
        metric_name = metric.upper() if metric in ["roas", "cpc", "cpm", "ctr", "cpa", "cpl"] else metric.title()

        # Check if metric was inferred
        metric_inferred = getattr(dsl, 'metric_inferred', False)
        metric_clarification = ""
        if metric_inferred:
            metric_clarification = f" (sorted by {metric_name} since no specific metric was requested)"

        # Build intro based on whether we have images
        if has_images:
            # Some creatives have images (Meta ads)
            meta_count = sum(1 for item in breakdown if item.get("thumbnail_url") or item.get("image_url"))
            if meta_count == count:
                intro = f"Here are your top {count} creatives by {metric_name}{metric_clarification} {timeframe_display}."
            else:
                intro = (
                    f"Here are your top {count} creatives by {metric_name}{metric_clarification} {timeframe_display}. "
                    f"{meta_count} have preview images available (Meta ads only)."
                )
        else:
            # No images available
            intro = (
                f"Here are your top {count} ads by {metric_name}{metric_clarification} {timeframe_display}. "
                f"Note: Creative preview images are currently only available for Meta (Facebook/Instagram) ads."
            )

        return intro

