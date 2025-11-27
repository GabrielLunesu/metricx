"""
QA Service
==========

High-level orchestrator for question-answering using the DSL v1.1 architecture.

Related files:
- app/nlp/translator.py: Natural language → DSL
- app/dsl/planner.py: DSL → execution plan
- app/dsl/executor.py: Plan → database results
- app/telemetry/logging.py: Structured logging
- app/routers/qa.py: HTTP endpoint

Design:
- Clean pipeline: question → canonicalize → translate → plan → execute → answer
- Comprehensive error handling at each stage
- Telemetry for observability
- Simple answer generation (deterministic, no LLM)

Usage:
    service = QAService(db)
    result = service.answer(question="What's my ROAS?", workspace_id="...")
"""

from __future__ import annotations

import time
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal

from sqlalchemy.orm import Session

from app.nlp.translator import Translator, TranslationError
from app.dsl.planner import build_plan
from app.dsl.executor import execute_plan, get_available_platforms
from app.dsl.validate import DSLValidationError
from app.telemetry.logging import log_qa_run
from app.answer.answer_builder import AnswerBuilder, AnswerBuilderError
from app.answer.formatters import format_metric_value, format_delta_pct, fmt_currency, fmt_count
from app.answer.visual_builder import build_visual_payload
from app import state  # Import shared application state

logger = logging.getLogger(__name__)


def convert_decimals_to_floats(obj: Any) -> Any:
    """
    Recursively convert Decimal values to floats for JSON serialization.
    
    Args:
        obj: Any Python object (dict, list, Decimal, etc.)
    
    Returns:
        Object with all Decimal values converted to float
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_floats(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_floats(item) for item in obj]
    else:
        return obj


class QAService:
    """
    High-level QA orchestrator using the DSL v1.2 pipeline with conversation context.
    
    This service:
    1. Retrieves conversation history for context
    2. Translates questions to DSL via LLM (context-aware)
    3. Plans the query execution
    4. Executes against the database
    5. Builds human-readable answers
    6. Stores conversation history for follow-ups
    7. Logs everything for telemetry
    
    Related:
    - Uses: Translator, build_plan, execute_plan, ContextManager
    - Called by: app/routers/qa.py
    """
    
    def __init__(self, db: Session):
        """
        Initialize QA service.
        
        Args:
            db: SQLAlchemy database session
        
        Components:
        - translator: Converts natural language → DSL (app/nlp/translator.py)
        - answer_builder: Converts results → natural language (app/answer/answer_builder.py)
        - context_manager: SHARED singleton for conversation history (app/state.py)
        
        WHY separation:
        - Translator: Question → structured query
        - Executor: Structured query → numbers
        - AnswerBuilder: Numbers → natural answer
        - ContextManager: Multi-turn conversation support (shared across requests)
        
        WHY shared context_manager:
        - Each HTTP request creates a new QAService instance
        - If each instance had its own ContextManager, context would be lost between requests
        - Using shared singleton from app.state ensures context persists
        """
        self.db = db
        self.translator = Translator()
        self.answer_builder = AnswerBuilder(db=self.db)
        # Use SHARED context manager from application state (not a new instance)
        # WHY: Context must persist across HTTP requests
        self.context_manager = state.context_manager
    
    def answer(
        self, 
        question: str, 
        workspace_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer a natural language question about metrics.
        
        Args:
            question: User's natural language question
            workspace_id: Workspace UUID for scoping
            user_id: User UUID for logging (optional)
            
        Returns:
            Dict with:
                - answer: Human-readable answer text
                - executed_dsl: Validated MetricQuery that was executed
                - data: MetricResult with summary/timeseries/breakdown
                
        Raises:
            TranslationError: If LLM translation fails
            DSLValidationError: If DSL validation fails
            Exception: If execution fails
            
        Examples:
            >>> service = QAService(db)
            >>> result = service.answer(
            ...     question="What's my ROAS this week?",
            ...     workspace_id="123e4567..."
            ... )
            >>> print(result["answer"])
            "Your ROAS for the selected period is 2.45."
        
        Pipeline:
        1. Retrieve conversation history (context)
        2. Translate question → DSL (via LLM, with context)
        3. Build execution plan
        4. Execute plan → results
        5. Format human-readable answer
        6. Store in conversation history
        7. Log run for telemetry
        """
        start_time = time.time()
        error_message = None
        dsl = None
        answer_text = None
        
        logger.info(f"[QA_PIPELINE] ===== Starting QA pipeline =====")
        logger.info(f"[QA_PIPELINE] Question: '{question}'")
        logger.info(f"[QA_PIPELINE] Workspace ID: {workspace_id}")
        logger.info(f"[QA_PIPELINE] User ID: {user_id or 'anon'}")
        
        try:
            # Step 1: Fetch prior context (last N Q&A for this user+workspace)
            # WHY: Enables follow-up questions like "Which one performed best?"
            logger.info(f"[QA_PIPELINE] Step 1: Fetching conversation context")
            if self.context_manager:
                context = self.context_manager.get_context(
                    user_id or "anon", 
                    workspace_id
                )
                logger.info(f"[QA_PIPELINE] Context retrieved: {len(context)} previous queries")
            else:
                context = []
                logger.warning("[QA_PIPELINE] Context manager unavailable - no conversation history")
            
            # Step 1.5: Build entity catalog for LLM to choose from
            # WHY: Let LLM handle entity recognition without hardcoded patterns
            entity_catalog = self._build_entity_catalog(workspace_id, limit=50)
            logger.info(f"[ENTITY_CATALOG] Built catalog with {len(entity_catalog)} entities")
            
            # Step 2: Translate to DSL with context awareness and entity catalog (with retry logic)
            # WHY context: LLM can resolve pronouns ("that", "this", "which one")
            # WHY catalog: LLM can choose appropriate entities without hardcoded patterns
            # WHY retry: LLM sometimes returns empty DSL or fails - retry improves success rate
            logger.info(f"[QA_PIPELINE] Step 2: Translating question to DSL")
            translation_attempts = 0
            max_retries = 2
            dsl = None
            translation_latency = None
            
            while translation_attempts <= max_retries:
                try:
                    dsl, translation_latency = self.translator.to_dsl(
                        question, 
                        log_latency=True,
                        context=context,  # NEW: Pass conversation history
                        entity_catalog=entity_catalog  # NEW: Pass entity catalog for entity recognition
                    )
                    
                    # Check if DSL is valid (not empty) - validate_dsl already checks this, but verify here too
                    if dsl and dsl.model_dump() != {}:
                        logger.info(f"[QA_PIPELINE] Translation complete: {dsl.model_dump()}")
                        logger.info(f"[QA_PIPELINE] Translation latency: {translation_latency}ms")
                        break  # Success, exit retry loop
                    else:
                        raise TranslationError(
                            message="Translation returned empty DSL",
                            question=question,
                            raw_response=""
                        )
                        
                except (TranslationError, DSLValidationError) as e:
                    translation_attempts += 1
                    logger.warning(f"[QA_PIPELINE] Translation attempt {translation_attempts} failed: {e.message}")
                    
                    if translation_attempts > max_retries:
                        # All retries exhausted
                        logger.error(f"[QA_PIPELINE] Translation failed after {max_retries + 1} attempts")
                        # Raise with helpful message - will be caught by error handler below
                        raise TranslationError(
                            message=f"Translation failed after {max_retries + 1} attempts. Please try rephrasing your question.",
                            question=question,
                            raw_response=str(e)
                        ) from e
                    
                    # Wait briefly before retry (exponential backoff)
                    wait_time = 0.5 * translation_attempts
                    logger.info(f"[QA_PIPELINE] Retrying translation in {wait_time}s...")
                    time.sleep(wait_time)
            
            # Add workspace_id to DSL for context-aware answer generation
            dsl.workspace_id = workspace_id
            
            # Step 3: Plan execution (may return None for non-metrics queries)
            logger.info(f"[QA_PIPELINE] Step 3: Building execution plan")
            plan = build_plan(dsl)
            logger.info(f"[QA_PIPELINE] Plan built: {plan}")
            
            # Phase 3: Pre-execution validation for missing data
            # Check if platform filter exists before executing query
            try:
                if dsl.filters and dsl.filters.provider:
                    available_platforms = get_available_platforms(self.db, workspace_id)
                    requested_platform = dsl.filters.provider.lower() if hasattr(dsl.filters.provider, 'lower') else str(dsl.filters.provider).lower()
                    
                    logger.info(f"[VALIDATION] Checking platform '{requested_platform}'. Available: {available_platforms}")
                    
                    if requested_platform not in available_platforms:
                        # Platform doesn't exist - provide helpful answer immediately
                        logger.info(
                            f"[VALIDATION] Platform '{requested_platform}' not found in {available_platforms}"
                        )
                        
                        # Build helpful answer
                        if available_platforms:
                            platform_list = ", ".join([p.capitalize() for p in available_platforms])
                            if len(available_platforms) == 1:
                                helpful_answer = f"You don't have any {requested_platform.capitalize()} campaigns connected. You're currently only running ads on {platform_list}."
                            else:
                                helpful_answer = f"You don't have any {requested_platform.capitalize()} campaigns connected. You're currently running ads on {platform_list}."
                        else:
                            helpful_answer = f"You don't have any {requested_platform.capitalize()} campaigns connected yet."
                        
                        # Log this as a successful query (we provided a helpful answer)
                        log_qa_run(
                            db=self.db,
                            workspace_id=workspace_id,
                            question=question,
                            dsl=dsl.model_dump(),
                            success=True,
                            latency_ms=int((time.time() - start_time) * 1000),
                            user_id=user_id,
                            error_message=None
                        )
                        
                        # Return early with helpful explanation
                        return {
                            "answer": helpful_answer,
                            "executed_dsl": dsl.model_dump(),
                            "data": {},  # Fixed: schema requires dict, not None
                            "context_used": self._build_context_summary_for_response(context),
                            "visuals": None
                        }
            except Exception as e:
                # If validation fails, log but continue with normal execution
                logger.warning(f"[VALIDATION] Platform check failed: {e}. Continuing with normal execution.")
            
            # Step 4: Execute plan (pass both plan and query for DSL v1.2)
            logger.info(f"[QA_PIPELINE] Step 4: Executing plan")
            result = execute_plan(
                db=self.db,
                workspace_id=workspace_id,
                plan=plan,
                query=dsl
            )
            logger.info(f"[QA_PIPELINE] Execution complete: {result}")
            
            # Step 5: Build human-readable answer (hybrid approach)
            logger.info(f"[QA_PIPELINE] Step 5: Building answer")
            # WHY hybrid: LLM rephrases deterministic facts → natural + safe
            # WHY fallback: If LLM fails, use template-based answer
            # NEW v2.0: Pass date window for transparency in answers
            answer_generation_ms = None
            
            # Extract date window from plan (for metrics queries)
            # WHY: Enables answers like "Summer Sale had highest ROAS from Sep 29–Oct 05, 2025"
            window = None
            if plan:
                window = {"start": plan.start, "end": plan.end}
            
            try:
                # Try hybrid answer builder (LLM-based rephrasing)
                answer_text, answer_generation_ms = self.answer_builder.build_answer(
                    dsl=dsl,
                    result=result,
                    window=window,  # NEW: Pass date window
                    log_latency=True
                )
                logger.info(f"[QA_PIPELINE] Answer generated successfully")
                logger.info(f"[QA_PIPELINE] Answer: '{answer_text}'")
                # Ensure latency is always numeric (never None)
                answer_generation_ms = answer_generation_ms if answer_generation_ms is not None else 0
                logger.info(f"[QA_PIPELINE] Answer generation latency: {answer_generation_ms}ms")
            except AnswerBuilderError as e:
                # Fallback to template-based answer if LLM fails
                # WHY fallback: Ensures we always return something, even if LLM is down
                logger.warning(f"[QA_PIPELINE] Answer builder failed, using template fallback: {e.message}")
                answer_text = self._build_answer_template(dsl, result, window)
                answer_generation_ms = 0  # Template fallback (always 0ms for consistency)
                logger.info(f"[QA_PIPELINE] Template answer: '{answer_text}'")
                logger.info(f"[QA_PIPELINE] Answer generation latency: {answer_generation_ms}ms")
            
            # Step 6: Save to conversation context for follow-ups
            # WHY: Enables next question to reference this query
            # Example: User asks "Which one performed best?" → needs this result
            # Serialize result based on type
            if hasattr(result, 'model_dump'):
                result_data = result.model_dump(mode='json')  # Changed: added mode='json'
            else:
                result_data = result  # Already a dict
            
            # Convert Decimal values to floats for JSON serialization
            result_data = convert_decimals_to_floats(result_data)

            # Debug: Log result_data before building visuals
            logger.debug(f"[QA_SERVICE] Building visuals with result_data keys: {list(result_data.keys()) if isinstance(result_data, dict) else 'not a dict'}")
            if isinstance(result_data, dict):
                ts_prev = result_data.get('timeseries_previous')
                logger.debug(f"[QA_SERVICE] timeseries_previous in result_data: {len(ts_prev) if ts_prev else 'None/empty'} points")

            visuals = build_visual_payload(dsl, result_data, window)

            # Debug: Log what visuals were built
            if visuals:
                logger.debug(f"[QA_SERVICE] Visuals built - viz_specs count: {len(visuals.get('viz_specs', []))}")
                for i, spec in enumerate(visuals.get('viz_specs', [])):
                    logger.debug(f"[QA_SERVICE] viz_spec[{i}]: type={spec.get('type')}, series_count={len(spec.get('series', []))}")
            
            # Store context for future follow-up questions (if Redis is available)
            if self.context_manager:
                self.context_manager.add_entry(
                    user_id=user_id or "anon",
                    workspace_id=workspace_id,
                    question=question,
                    dsl=dsl.model_dump(mode='json'),  # Changed: added mode='json' to serialize dates
                    result=result_data
                )
            else:
                logger.debug("[QA_PIPELINE] Context manager unavailable - skipping context storage")
            
            # Step 7: Build context summary for response (for debugging in Swagger)
            # WHY: Makes it visible what context was used for this query
            # Useful for testing follow-up questions in Swagger UI
            context_summary = self._build_context_summary_for_response(context)
            
            # Step 8: Log success (including answer generation latency)
            total_latency_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[QA_PIPELINE] Step 6: Saving to conversation context")
            logger.info(f"[QA_PIPELINE] Step 7: Logging telemetry")
            log_qa_run(
                db=self.db,
                workspace_id=workspace_id,
                question=question,
                dsl=dsl.model_dump(mode='json'),  # Changed: added mode='json' to serialize dates
                success=True,
                latency_ms=total_latency_ms,
                user_id=user_id,
                answer_text=answer_text
            )
            
            logger.info(f"[QA_PIPELINE] ===== Pipeline complete =====")
            logger.info(f"[QA_PIPELINE] Total latency: {total_latency_ms}ms")
            logger.info(f"[QA_PIPELINE] Final answer: '{answer_text}'")
            
            return {
                "answer": answer_text,
                "executed_dsl": dsl.model_dump(),  # Convert Pydantic model to dict
                "data": result_data,
                "context_used": context_summary,  # NEW: Show what context was available
                "visuals": visuals
            }
            
        except TranslationError as e:
            error_message = f"Translation failed: {e.message}"
            total_latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[QA_PIPELINE] Translation error: {e.message}")
            
            # Log failure
            log_qa_run(
                db=self.db,
                workspace_id=workspace_id,
                question=question,
                dsl=None,
                success=False,
                latency_ms=total_latency_ms,
                user_id=user_id,
                error_message=error_message
            )
            
            # Return helpful error response instead of raising (better UX)
            return {
                "answer": "I couldn't understand your question. Please try rephrasing it. For example:\n- 'What's my ROAS this week?'\n- 'Compare Google vs Meta campaigns'\n- 'Show me campaigns with ROAS above 4'\n- 'What's my spend and revenue last month?'",
                "executed_dsl": {},
                "data": None,
                "error": error_message,
                "visuals": None
            }
            
        except DSLValidationError as e:
            error_message = f"Validation failed: {e.message}"
            total_latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[QA_PIPELINE] DSL validation error: {e.message}")
            
            # Log failure
            log_qa_run(
                db=self.db,
                workspace_id=workspace_id,
                question=question,
                dsl=None,
                success=False,
                latency_ms=total_latency_ms,
                user_id=user_id,
                error_message=error_message
            )
            
            # Return helpful error response instead of raising (better UX)
            return {
                "answer": "I couldn't understand your question. Please try rephrasing it. For example:\n- 'What's my ROAS this week?'\n- 'Compare Google vs Meta campaigns'\n- 'Show me campaigns with ROAS above 4'\n- 'What's my spend and revenue last month?'",
                "executed_dsl": {},
                "data": None,
                "error": error_message,
                "visuals": None
            }
            
        except Exception as e:
            error_message = f"Execution failed: {str(e)}"
            total_latency_ms = int((time.time() - start_time) * 1000)
            
            # Log failure
            log_qa_run(
                db=self.db,
                workspace_id=workspace_id,
                question=question,
                dsl=dsl.model_dump() if dsl else None,
                success=False,
                latency_ms=total_latency_ms,
                user_id=user_id,
                error_message=error_message
            )
            
            raise
    
    def _build_answer_template(self, dsl, result, window=None) -> str:
        """
        Build a template-based answer (FALLBACK ONLY).
        
        WHY this exists:
        - Fallback when AnswerBuilder (LLM) fails
        - Ensures we always return an answer
        - Deterministic, safe, but less natural than LLM version
        
        NEW v2.0: window parameter
        - Accepts optional date window for including date range in fallback answers
        
        NEW Phase 1.1: Natural fallback templates
        - Uses timeframe_description and tense detection
        - More natural language ("You spent" vs "Your SPEND")
        - Correct verb tenses based on timeframe
        
        DSL v1.2 changes:
        - Handles providers queries: "You are running ads on Google, Meta, TikTok."
        - Handles entities queries: "Here are your campaigns: Summer Sale, Winter Promo, ..."
        - Handles metrics queries: existing logic (ROAS, CPA, etc.)
        
        Args:
            dsl: MetricQuery that was executed
            result: MetricResult (metrics) or dict (providers/entities) from execution
            
        Returns:
            Human-readable answer text (template-based, more natural)
            
        Design:
        - Deterministic (no LLM, no randomness)
        - Template-based (predictable format)
        - Includes comparison delta if available (metrics only)
        - Mentions breakdown if present (metrics only)
        
        Related:
        - Primary: app/answer/answer_builder.py (LLM-based, preferred)
        - Used when: AnswerBuilder raises AnswerBuilderError
        """
        # Import tense detection
        from app.answer.intent_classifier import detect_tense, VerbTense
        # DSL v1.2: Handle providers queries
        # Example: "Which platforms am I advertising on?"
        # Result: {"providers": ["google", "meta", "tiktok"]}
        if dsl.query_type == "providers":
            providers = result.get("providers", [])
            if not providers:
                return "No active ad platforms found for this workspace."
            
            # Format provider names nicely (capitalize first letter)
            formatted = [p.capitalize() for p in providers]
            
            if len(formatted) == 1:
                return f"You are running ads on {formatted[0]}."
            elif len(formatted) == 2:
                return f"You are running ads on {formatted[0]} and {formatted[1]}."
            else:
                # Oxford comma for 3+
                all_but_last = ", ".join(formatted[:-1])
                return f"You are running ads on {all_but_last}, and {formatted[-1]}."
        
        # DSL v1.2: Handle entities queries
        # Example: "List my active campaigns"
        # Result: {"entities": [{"name": "...", "status": "...", "level": "..."}, ...]}
        if dsl.query_type == "entities":
            entities = result.get("entities", [])
            if not entities:
                return "No entities matched your filters."
            
            # Determine what we're listing (campaigns, adsets, ads)
            level = dsl.filters.level if dsl.filters and dsl.filters.level else "entities"
            level_plural = level if level.endswith("s") else f"{level}s"
            
            # List entity names
            names = [e["name"] for e in entities]
            
            if len(names) <= 3:
                # Short list: enumerate all
                names_str = ", ".join(names)
                return f"Here are your {level_plural}: {names_str}."
            else:
                # Long list: show first 3 and count
                first_three = ", ".join(names[:3])
                remaining = len(names) - 3
                return f"Here are your {level_plural}: {first_three}, and {remaining} more."
        
        # METRICS: Original logic (DSL v1.1), now with formatters (Derived Metrics v1)
        # NEW v2.0: Intent-first answers for top_n=1 queries
        if isinstance(dsl.metric, list):
            metric_display = ", ".join(dsl.metric).upper()
        else:
            metric_display = dsl.metric.upper() if dsl.metric else "METRIC"
        
        # For metrics, result is a MetricResult or dict with .summary
        if isinstance(result, dict):
            value = result.get("summary")
            previous = result.get("previous")
            delta_pct = result.get("delta_pct")
            breakdown = result.get("breakdown")
        else:
            value = result.summary
            previous = result.previous
            delta_pct = result.delta_pct
            breakdown = result.breakdown
        
        # Format value using shared formatters
        # WHY: Single source of truth for formatting (same as AnswerBuilder)
        # This prevents bugs like CPC showing as "$0" when it's actually "$0.48"
        value_str = format_metric_value(dsl.metric, value)
        
        # NEW v2.0: Intent-first answer for "Which X had highest Y?" queries
        # WHY: Answer the question directly, not with workspace average
        if breakdown and len(breakdown) > 0 and dsl.top_n == 1 and dsl.breakdown:
            top_item = breakdown[0]
            top_value_formatted = format_metric_value(dsl.metric, top_item.get("value"))
            
            # Build date range string if available
            date_str = ""
            if window:
                from app.answer.answer_builder import _format_date_range
                date_str = f" from {_format_date_range(window['start'], window['end'])}"
            
            # Lead with the top performer
            answer = f"{top_item['label']} had the highest {metric_display} at {top_value_formatted}{date_str}."
            
            # Add denominators if available (for context)
            denominators = []
            if "spend" in top_item and top_item.get("spend"):
                denominators.append(f"Spend {fmt_currency(top_item['spend'])}")
            if "revenue" in top_item and top_item.get("revenue"):
                denominators.append(f"Revenue {fmt_currency(top_item['revenue'])}")
            if "clicks" in top_item and top_item.get("clicks"):
                denominators.append(f"{fmt_count(top_item['clicks'])} clicks")
            if "conversions" in top_item and top_item.get("conversions"):
                denominators.append(f"{fmt_count(top_item['conversions'])} conversions")
            
            if denominators:
                answer += f" ({', '.join(denominators)})."
            
            # Optionally add overall context
            if value is not None and value != top_item.get("value"):
                answer += f" Overall {metric_display} was {value_str}."
            
            return answer
        
        # Get timeframe and tense
        timeframe_desc = getattr(dsl, 'timeframe_description', '')
        question = getattr(dsl, 'question', '')
        tense = detect_tense(question, timeframe_desc)
        
        # Build human-friendly timeframe display
        from app.answer.answer_builder import _format_timeframe_display
        timeframe_display = _format_timeframe_display(timeframe_desc, window)
        
        # Natural metric names
        natural_names = {
            "ROAS": "ROAS",
            "CPC": "cost per click", 
            "CPA": "cost per acquisition",
            "CTR": "click-through rate",
            "SPEND": "ad spend",
            "REVENUE": "revenue",
            "CLICKS": "clicks",
            "IMPRESSIONS": "impressions",
            "CONVERSIONS": "conversions",
            "CVR": "conversion rate",
            "CPM": "cost per thousand impressions",
            "CPL": "cost per lead",
            "CPI": "cost per install",
            "CPP": "cost per purchase",
            "POAS": "profit on ad spend",
            "AOV": "average order value",
            "ARPV": "average revenue per visitor"
        }
        
        metric_natural = natural_names.get(metric_display, metric_display.lower())
        
        # Phase 3: Check for missing data and provide helpful explanation
        is_null_or_zero = value is None or (isinstance(value, (int, float)) and value == 0)
        
        if is_null_or_zero:
            # Data is missing - provide helpful context
            if timeframe_desc in ['today', 'yesterday']:
                # Suggest checking broader timeframe
                return f"No data available for {timeframe_display} yet. Your {metric_natural} last week was available - try asking about a longer timeframe."
            elif value is None:
                # Truly no data (N/A)
                return f"No {metric_natural} data available for {timeframe_display if timeframe_display else 'the selected period'}."
            # If value is exactly 0, continue with normal answer (it might genuinely be zero)
        
        # Build natural sentence based on tense and metric type
        if tense == VerbTense.PAST:
            if metric_display == "SPEND":
                answer = f"You spent {value_str}{' ' + timeframe_display if timeframe_display else ''}."
            elif metric_display == "REVENUE":
                answer = f"You generated {value_str} in revenue{' ' + timeframe_display if timeframe_display else ''}."
            elif metric_display == "CLICKS":
                answer = f"You got {value_str} clicks{' ' + timeframe_display if timeframe_display else ''}."
            elif metric_display == "IMPRESSIONS":
                answer = f"Your ads received {value_str} impressions{' ' + timeframe_display if timeframe_display else ''}."
            elif metric_display == "CONVERSIONS":
                answer = f"You had {value_str} conversions{' ' + timeframe_display if timeframe_display else ''}."
            else:
                # For ratio/rate metrics
                answer = f"Your {metric_natural} was {value_str}{' ' + timeframe_display if timeframe_display else ''}."
        else:  # PRESENT or FUTURE
            verb = "is" if tense == VerbTense.PRESENT else "will be"
            answer = f"Your {metric_natural} {verb} {value_str}{' ' + timeframe_display if timeframe_display else ''}."
        
        # Add comparison if available (using shared formatters)
        # WHY format_delta_pct: Consistent with AnswerBuilder, includes sign (+/-)
        if delta_pct is not None:
            delta_display = format_delta_pct(delta_pct)
            if tense == VerbTense.PAST:
                answer += f" That was a {delta_display} change from the previous period."
            else:
                answer += f" That's a {delta_display} change from the previous period."
        
        # Mention breakdown if available
        if breakdown and len(breakdown) > 0:
            top_item = breakdown[0]
            # Format the top performer's value using the same metric formatter
            top_value_formatted = format_metric_value(dsl.metric, top_item.get("value"))
            answer += f" Top performer: {top_item['label']} ({top_value_formatted})."
        
        return answer
    
    def _build_context_summary_for_response(self, context: list) -> list:
        """
        Build a simplified context summary for API response.
        
        WHY this exists:
        - Makes context visible in Swagger UI responses
        - Helps users debug follow-up question behavior
        - Shows what information was available when translating the query
        
        Args:
            context: Full context list from context_manager.get_context()
                     Each entry: {"question": str, "dsl": dict, "result": dict}
        
        Returns:
            Simplified list of dicts with only key info for debugging
            Empty list if no context available
        
        Examples:
            >>> context = [{"question": "how much revenue?", "dsl": {"metric": "revenue"}, "result": {...}}]
            >>> summary = self._build_context_summary_for_response(context)
            >>> summary
            [{"question": "how much revenue?", "metric": "revenue"}]
        
        Design decisions:
        - Only include question + key DSL fields (metric, query_type)
        - Omit full result data to keep response size small
        - Empty list (not null) when no context for consistent typing
        
        Related:
        - Used in: answer() method to populate response
        - Visible in: Swagger UI /qa endpoint responses
        - Helps debug: Follow-up questions ("and the week before?")
        """
        if not context or len(context) == 0:
            return []
        
        summary = []
        for entry in context:
            question = entry.get("question", "")
            dsl = entry.get("dsl", {})
            
            # Extract only the most relevant DSL fields for debugging
            context_item = {
                "question": question,
                "query_type": dsl.get("query_type", "metrics"),
            }
            
            # Add metric if present (helps debug metric inheritance)
            if "metric" in dsl and dsl["metric"]:
                context_item["metric"] = dsl["metric"]
            
            # Add time range if present (helps debug time period changes)
            if "time_range" in dsl and dsl["time_range"]:
                time_range = dsl["time_range"]
                if isinstance(time_range, dict) and "last_n_days" in time_range:
                    context_item["time_period"] = f"last_{time_range['last_n_days']}_days"
            
            summary.append(context_item)
        
        return summary
    
    def _build_entity_catalog(self, workspace_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Build a compact catalog of entities for the LLM to choose from.
        
        Args:
            workspace_id: Workspace UUID for scoping
            limit: Maximum number of entities to include
            
        Returns:
            List of entity dictionaries with name, level, provider, goal
        """
        from app.services.unified_metric_service import UnifiedMetricService, MetricFilters
        
        service = UnifiedMetricService(self.db)
        filters = MetricFilters()  # Empty filters to get all entities
        entities = service.get_entity_list(workspace_id, filters=filters, limit=limit)
        
        catalog = []
        for entity in entities:
            catalog.append({
                "name": entity.get("name", ""),
                "level": entity.get("level", ""),
                "provider": entity.get("provider"),
                "goal": entity.get("goal"),
            })
        
        return catalog
    
    def _extract_entity_names(self, question: str, workspace_id: str) -> List[str]:
        """
        Skip entity extraction - let LLM handle entity recognition using catalog.
        
        This approach:
        - Removes hardcoded patterns
        - Works with any naming convention
        - Lets LLM handle entity recognition
        - No database calls for entity extraction
        """
        # Don't extract entity names at all
        # Let the translator/LLM figure out entity names from context
        # The LLM will put entity names in dsl.filters.entity_name
        return []
