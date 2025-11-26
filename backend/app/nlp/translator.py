"""
NLP Translator
==============

Converts natural language questions into validated DSL queries using LLMs.

Related files:
- app/nlp/prompts.py: System prompts and few-shot examples
- app/dsl/canonicalize.py: Pre-processing (synonym mapping)
- app/dsl/validate.py: Post-processing (validation)
- app/dsl/schema.py: Target DSL structure
- app/services/qa_service.py: High-level orchestrator

Design:
- Temperature=0 for deterministic outputs
- JSON mode for structured responses
- Canonicalization before LLM call
- Validation after LLM response
- Clear error handling and logging
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional, List, Dict, Any
import os

from openai import OpenAI

logger = logging.getLogger(__name__)

from app.dsl.schema import MetricQuery
from app.dsl.canonicalize import canonicalize_question
from app.dsl.validate import validate_dsl, DSLValidationError
from app.nlp.prompts import build_system_prompt, build_few_shot_prompt
from app.deps import get_settings
from app.dsl.date_parser import DateRangeParser


class TranslationError(Exception):
    """
    Raised when translation fails (LLM error, JSON parse error, etc.).
    
    Attributes:
        message: Human-readable error description
        question: Original user question
        raw_response: Raw LLM response (if available)
    """
    def __init__(self, message: str, question: str = "", raw_response: str = ""):
        super().__init__(message)
        self.message = message
        self.question = question
        self.raw_response = raw_response


class Translator:
    """
    Translates natural language questions into validated MetricQuery DSL.
    
    Usage:
        translator = Translator()
        dsl = translator.to_dsl("What's my ROAS this week?")
        # Returns: MetricQuery(metric="roas", time_range={"last_n_days": 7}, ...)
    
    Design:
    - Uses OpenAI GPT-4o-mini for JSON mode
    - Temperature=0 for consistency
    - JSON mode for structured outputs with Pydantic validation
    - Canonicalization reduces LLM variance
    - Validation ensures safety
    
    Related:
    - app/dsl/schema.py: Output type (MetricQuery)
    - app/dsl/canonicalize.py: Pre-processing
    - app/dsl/validate.py: Post-processing
    """
    
    def __init__(self, client: Optional[OpenAI] = None):
        """
        Initialize translator with OpenAI client.
        
        Args:
            client: Optional OpenAI client (for testing/mocking)
                    If None, creates client from settings
        """
        if client is None:
            settings = get_settings()
            if not settings.OPENAI_API_KEY:
                raise ValueError(
                    "OPENAI_API_KEY not configured. "
                    "Set it in your .env file or environment."
                )
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            # Allow swapping models via env; default stays on GPT-4o but uses streaming by default for SSE clients.
            self.model = getattr(settings, "OPENAI_MODEL", None) or os.getenv("OPENAI_MODEL") or "gpt-4o"
        else:
            self.client = client
            self.model = "gpt-4o"
        # Streaming can be toggled via env OPENAI_STREAMING=true|false; defaults to True.
        self.use_streaming = os.getenv("OPENAI_STREAMING", "true").lower() == "true"
        
        self.date_parser = DateRangeParser()

    def to_dsl(
        self,
        question: str,
        log_latency: bool = False,
        context: Optional[List[Dict[str, Any]]] = None,
        entity_catalog: Optional[List[Dict[str, Any]]] = None
    ) -> tuple[MetricQuery, Optional[int]]:
        """
        Translate a natural language question into a validated DSL query.
        
        Args:
            question: User's natural language question
            log_latency: Whether to track translation latency
            context: Optional conversation history for follow-up resolution
                     List of {"question": str, "dsl": dict, "result": dict}
            entity_goals: Optional mapping of entity names to their goals
                          Dict of {"entity_name": "goal"} for goal-aware metric selection
            
        Returns:
            Tuple of (MetricQuery, latency_ms)
            - MetricQuery: Validated DSL query
            - latency_ms: Translation time in milliseconds (None if not logged)
            
        Raises:
            TranslationError: If LLM call fails or returns invalid JSON
            DSLValidationError: If LLM output doesn't match DSL schema
            
        Examples:
            >>> translator = Translator()
            >>> # Simple query (no context)
            >>> dsl, latency = translator.to_dsl("What's my spend today?")
            >>> print(dsl.metric, dsl.time_range)
            spend TimeRange(last_n_days=1)
            
            >>> # Follow-up query (with context)
            >>> context = [{"question": "Show me ROAS by campaign", "dsl": {...}, "result": {...}}]
            >>> dsl, latency = translator.to_dsl("Which one performed best?", context=context)
            >>> print(dsl.breakdown)
            campaign
        
        Process:
        1. Canonicalize question (map synonyms, normalize time phrases)
        2. Build context summary if history provided (for follow-ups)
        3. Build prompt with system instructions + context + few-shots + question
        4. Call OpenAI with JSON mode
        5. Parse JSON response
        6. Validate via Pydantic
        7. Return validated MetricQuery
        """
        start_time = time.time() if log_latency else None
        
        # Step 1: Pre-process the question
        canon_question = canonicalize_question(question)

        # Step 2: Parse date range early to guide the LLM
        parsed_date_range = self.date_parser.parse(question)

        # Step 3: Build context for follow-up questions
        context_summary = self._build_context_summary(context) if context else ""

        # Step 4: Build the full prompt
        system_prompt = build_system_prompt()
        few_shot_prompt = build_few_shot_prompt(include_followups=bool(context))
        
        # Add date parsing results to the prompt for the LLM
        date_instruction = ""
        if parsed_date_range:
            date_instruction = f"IMPORTANT: A date range has been pre-parsed for this question. You MUST use the following time_range object in your response:\n"
            date_instruction += f"```json\n{json.dumps(parsed_date_range, default=str)}\n```\n"
        
        # Add entity catalog for entity recognition and goal-aware metric selection
        entity_catalog_instruction = ""
        if entity_catalog:
            entity_catalog_instruction = "ENTITY CATALOG:\n"
            for entry in entity_catalog:
                entry_line = f"- {entry['level']}: {entry['name']}"
                if entry.get("provider"):
                    entry_line += f" (provider: {entry['provider']})"
                if entry.get("goal"):
                    entry_line += f" (goal: {entry['goal']})"
                entity_catalog_instruction += entry_line + "\n"
            entity_catalog_instruction += "\nWhen matching entity names, choose the closest entry from this catalog.\n"
            entity_catalog_instruction += "IMPORTANT: If the user explicitly mentions a specific metric, use that metric.\n"
            entity_catalog_instruction += "Only use goal-aware metric selection when no specific metric is mentioned.\n\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": few_shot_prompt},
        ]
        if context_summary:
            messages.append({"role": "system", "content": context_summary})
        
        final_question = f"{entity_catalog_instruction}{date_instruction}Question: {canon_question}"
        messages.append({"role": "user", "content": final_question})
        
        # Step 5: Call OpenAI API with JSON mode (streaming preferred, fallback to non-stream)
        # Timeout: 30 seconds to prevent hanging on slow LLM responses
        LLM_TIMEOUT_SECONDS = 30
        raw_response = ""
        if self.use_streaming:
            try:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0,
                    response_format={"type": "json_object"},
                    stream=True,
                    timeout=LLM_TIMEOUT_SECONDS,
                )
                raw_chunks: List[str] = []
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else None
                    if delta:
                        raw_chunks.append(delta)
                raw_response = "".join(raw_chunks).strip()
            except Exception as e:
                # Fallback to non-streaming if streaming fails
                logger.warning(f"[TRANSLATOR] Streaming failed, falling back to non-streaming: {e}")
                raw_response = ""
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0,
                        response_format={"type": "json_object"},
                        timeout=LLM_TIMEOUT_SECONDS,
                    )
                    raw_response = response.choices[0].message.content
                except Exception as inner:
                    raise TranslationError(
                        f"OpenAI API call failed (stream + fallback): {inner}",
                        question=question
                    ) from inner
        else:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0,
                    response_format={"type": "json_object"},
                    timeout=LLM_TIMEOUT_SECONDS,
                )
                raw_response = response.choices[0].message.content
            except Exception as e:
                raise TranslationError(
                    f"OpenAI API call failed: {e}",
                    question=question
                ) from e

        if not raw_response:
            raise TranslationError(
                "LLM returned empty response",
                question=question,
                raw_response=""
            )
        try:
            dsl_dict = json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise TranslationError(
                f"LLM returned invalid JSON: {e}",
                question=question,
                raw_response=raw_response
            ) from e

        # Add original question for context in answer generation
        dsl_dict['question'] = question

        # POST-PROCESSING FIX (v2.5.1): Ensure comparison queries have compare_to_previous=True
        # WHY: LLM sometimes misses setting this flag for "vs" queries
        # This is a safety net to ensure comparison charts work correctly
        question_lower = question.lower()
        comparison_keywords = ['vs', 'versus', 'compared to', 'compare to', 'vs.', 'against last', 'vs last']
        if any(kw in question_lower for kw in comparison_keywords):
            if not dsl_dict.get('compare_to_previous'):
                logger.info(f"[TRANSLATOR] Forcing compare_to_previous=True for comparison query: {question}")
                dsl_dict['compare_to_previous'] = True

        # Log the DSL for debugging
        logger.debug(f"[TRANSLATOR] DSL: compare_to_previous={dsl_dict.get('compare_to_previous')}, breakdown={dsl_dict.get('breakdown')}, metric_filters={dsl_dict.get('filters', {}).get('metric_filters')}")

        try:
            validated_dsl = validate_dsl(dsl_dict)

            # Log the DSL for debugging
            logger.info(f"[TRANSLATOR] Generated DSL: metric={validated_dsl.metric}, "
                       f"compare_to_previous={validated_dsl.compare_to_previous}, "
                       f"time_range={validated_dsl.time_range}")

            latency = int((time.time() - start_time) * 1000) if start_time else None
            return validated_dsl, latency
        except DSLValidationError as e:
            # Re-raise with more context for logging
            raise DSLValidationError(
                message=f"DSL validation failed: {e}",
                raw_dict=dsl_dict,
                pydantic_errors=e.pydantic_errors
            ) from e

    def _build_context_summary(self, context: List[Dict[str, Any]]) -> str:
        """
        Build a concise summary of conversation history for the LLM.
        
        WHY this exists:
        - Help LLM resolve follow-up questions with pronouns ("which one", "that", "this")
        - Keep prompt size manageable (only last 1-2 queries)
        - Provide enough context without overwhelming the LLM
        
        Args:
            context: List of conversation entries from ContextManager
                     Each entry: {"question": str, "dsl": dict, "result": dict}
        
        Returns:
            Formatted context string for prompt inclusion
            Empty string if context is empty or None
        
        Examples:
            >>> context = [{
            ...     "question": "What's my ROAS this week?",
            ...     "dsl": {"metric": "roas", "time_range": {"last_n_days": 7}},
            ...     "result": {"summary": 2.45, "delta_pct": 0.19}
            ... }]
            >>> summary = self._build_context_summary(context)
            >>> print(summary)
            Previous Question: What's my ROAS this week?
            Previous Metric: roas
            Previous Result: 2.45
        
        Design decisions:
        - Only include last 1-2 entries (most recent context)
        - Summarize key facts (question, metric, main result)
        - Omit full DSL and detailed results to save tokens
        - Format for easy LLM parsing
        
        Related:
        - Called by: to_dsl() when context is provided
        - Context from: app/context/redis_context_manager.py (RedisContextManager)
        """
        if not context or len(context) == 0:
            return ""
        
        # Only include the last 1-2 entries for brevity
        # WHY: Recent context is most relevant for follow-ups
        # More than 2 can clutter the prompt and increase token usage
        recent = context[-2:] if len(context) >= 2 else context[-1:]
        
        summary_parts = []
        
        for idx, entry in enumerate(recent, 1):
            question = entry.get("question", "")
            dsl = entry.get("dsl", {})
            result = entry.get("result", {})
            
            # Extract key facts from DSL
            query_type = dsl.get("query_type", "metrics")
            metric = dsl.get("metric", "N/A")
            
            # Extract key facts from result
            if query_type == "metrics":
                main_value = result.get("summary", "N/A")
                # Include breakdown if present (helpful for "which one" questions)
                breakdown = result.get("breakdown", [])
                top_items = ", ".join([item.get("label", "") for item in breakdown[:3]]) if breakdown else ""
            elif query_type == "providers":
                providers = result.get("providers", [])
                main_value = ", ".join([p.capitalize() for p in providers])
                top_items = ""
            elif query_type == "entities":
                entities = result.get("entities", [])
                entity_names = [e.get("name", "") for e in entities[:3]]
                main_value = ", ".join(entity_names)
                top_items = ""
            else:
                main_value = "N/A"
                top_items = ""
            
            # Build summary for this entry with EXPLICIT instructions
            entry_summary = f"Previous Question #{idx}: {question}\n"
            
            if query_type == "metrics":
                entry_summary += f"  Query Type: METRICS\n"
                entry_summary += f"  Metric Used: {metric} ← Reference this if the user's question is a follow-up about a different time period but doesn't specify a new metric.\n"
                entry_summary += f"  Time Range: {dsl.get('time_range', 'N/A')}\n"
                entry_summary += f"  Result: {main_value}\n"
                if top_items:
                    entry_summary += f"  Top Items: {top_items} ← REFERENCE THESE if user asks 'which one?'\n"
            elif query_type == "providers":
                entry_summary += f"  Query Type: PROVIDERS\n"
                entry_summary += f"  Platforms: {main_value}\n"
            elif query_type == "entities":
                entry_summary += f"  Query Type: ENTITIES\n"
                entry_summary += f"  Entity Names: {main_value} ← REFERENCE THESE if user asks about 'that', 'it', 'them'\n"
                # Get first entity name for easy reference
                if entities and len(entities) > 0:
                    first_entity = entities[0].get("name", "")
                    if first_entity:
                        entry_summary += f"  First Entity: '{first_entity}' ← USE THIS if user says 'that campaign', 'it', 'that one'\n"
            
            summary_parts.append(entry_summary)
        
        return "\n".join(summary_parts)
    
    def to_dsl_simple(self, question: str) -> MetricQuery:
        """
        Simplified interface that returns just the DSL (no latency).
        
        Args:
            question: User's natural language question
            
        Returns:
            Validated MetricQuery
            
        Raises:
            TranslationError: If translation fails
            DSLValidationError: If validation fails
        """
        dsl, _ = self.to_dsl(question, log_latency=False)
        return dsl
