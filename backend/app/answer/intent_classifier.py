"""
Intent Classifier - Determines Answer Depth Based on Question Type

WHAT: Classifies user questions into intent categories to match answer complexity to user needs
WHY: Simple questions deserve simple answers; complex questions deserve rich context
WHERE: Called by AnswerBuilder before context extraction

Intent Levels:
- SIMPLE: "what was my roas" → Just the number (1 sentence)
- COMPARATIVE: "how does my roas compare" → Include comparison context (2-3 sentences)
- ANALYTICAL: "why is my roas low" → Full rich context (trends, outliers, recommendations)

Design Philosophy:
- Start with simple rules (not ML)
- Based on question keywords and DSL structure
- Easy to understand and debug
- Extensible for future improvements

References:
- Used by: app/answer/answer_builder.py::AnswerBuilder.build_answer()
- Docs: backend/docs/ROADMAP_TO_NATURAL_COPILOT.md (Phase 1, Task 1.2)
"""

from enum import Enum
from typing import Optional
from app.dsl.schema import MetricQuery


class AnswerIntent(str, Enum):
    """
    Answer intent classification.
    
    Determines how much context to include in the answer.
    """
    SIMPLE = "simple"          # Just give me the number
    COMPARATIVE = "comparative" # Compare to something
    ANALYTICAL = "analytical"   # Explain the why/how
    LIST = "list"              # Give me a list of items


def classify_intent(question: str, query: MetricQuery) -> AnswerIntent:
    """
    Classify user intent from question text and generated DSL.
    
    Uses both natural language signals (question keywords) and structured signals
    (DSL fields) to determine what level of detail the user wants.
    
    Args:
        question: User's original question (canonicalized)
        query: Generated DSL query
        
    Returns:
        AnswerIntent: Classification for answer depth control
        
    Examples:
        >>> classify_intent("what was my roas last month", query)
        AnswerIntent.SIMPLE
        
        >>> classify_intent("how does my roas compare to last month", query_with_comparison)
        AnswerIntent.COMPARATIVE
        
        >>> classify_intent("why is my roas so volatile", query)
        AnswerIntent.ANALYTICAL
    
    Classification Logic:
    
    SIMPLE Intent - Give me a quick fact:
    - Question starts with "what/how much/how many/show me"
    - NO comparison requested (compare_to_previous=False)
    - NO breakdown requested
    - Example: "what was my roas", "how much did I spend", "show me cpc"
    
    COMPARATIVE Intent - Show me the difference:
    - Question contains comparison keywords ("compare", "vs", "versus", "better", "worse", "higher", "lower")
    - OR DSL has compare_to_previous=True
    - OR DSL has breakdown (breaking down by dimension is inherently comparative)
    - Example: "compare google vs meta", "how does this week compare", "which campaign had highest roas"
    
    ANALYTICAL Intent - Explain it to me:
    - Question contains analysis keywords ("why", "explain", "analyze", "trend", "pattern", "insight")
    - User explicitly asking for understanding, not just data
    - Example: "why is my roas low", "explain the trend", "analyze campaign performance"
    
    LIST Intent - Give me a list of items:
    - Question contains list keywords ("list", "show me all", "give me", "top", "all")
    - DSL has breakdown AND top_n > 1
    - User wants to see multiple items, not just the top performer
    - Example: "give me a list of top 5 campaigns", "show me all adsets", "list campaigns with high ROAS"
    
    References:
    - Docs: backend/docs/ROADMAP_TO_NATURAL_COPILOT.md
    - Tests: app/tests/test_intent_classifier.py
    """
    question_lower = question.lower().strip()
    
    # ANALYTICAL: Explicitly asking for explanation or analysis
    # These users want to understand WHY/HOW, not just WHAT
    analytical_keywords = [
        "why", "explain", "analyze", "analysis",
        "trend", "trending", "pattern", "patterns",
        "insight", "insights", "understand",
        "what's happening", "what happened",
        "problem", "issue", "volatile", "volatility",
        "fluctuating", "swinging", "unstable", "erratic"  # NEW keywords
    ]
    
    if any(kw in question_lower for kw in analytical_keywords):
        return AnswerIntent.ANALYTICAL
    
    # LIST: Asking for a list of items (check BEFORE comparative)
    # These users want to see multiple items, not just the top performer
    list_keywords = [
        "list", "show me all", "give me", "top", "all",
        "every", "each", "entire", "complete", "show me"
    ]
    
    # Check for list keywords in question
    has_list_keywords = any(kw in question_lower for kw in list_keywords)
    
    # Check DSL for list signals (breakdown with top_n > 1 OR has metric_filters)
    has_list_in_dsl = (
        query.breakdown is not None and 
        query.top_n is not None and 
        query.top_n > 1
    )
    
    # IMPORTANT: Metric filter queries are ALWAYS list queries
    # When user says "show me campaigns with ROAS above 4", they want a list
    has_metric_filters = (
        query.filters and 
        hasattr(query.filters, 'metric_filters') and 
        query.filters.metric_filters is not None and 
        len(query.filters.metric_filters) > 0
    )
    
    if (has_list_keywords and has_list_in_dsl) or has_metric_filters:
        return AnswerIntent.LIST
    
    # COMPARATIVE: Asking to compare things
    # These users want context and comparison, not just a single number
    comparative_keywords = [
        "compare", "comparison", "vs", "versus",
        "better", "worse", "best", "worst",
        "higher", "lower", "more", "less",
        "bottom", "rank", "ranking",
        "which", "who", "what campaign", "what platform"
    ]
    
    # Check for comparative keywords in question
    has_comparative_keywords = any(kw in question_lower for kw in comparative_keywords)
    
    # Check DSL for comparison/breakdown signals
    has_comparison_in_dsl = (
        query.compare_to_previous or 
        query.breakdown is not None or
        query.group_by != "none"
    )
    
    if has_comparative_keywords or has_comparison_in_dsl:
        return AnswerIntent.COMPARATIVE
    
    # SIMPLE: Just asking for a basic fact
    # These users want a quick number, nothing more
    simple_starters = [
        "what", "what's", "what is", "what was",
        "how much", "how many",
        "show me", "give me", "tell me",
        "get me", "fetch"
    ]
    
    # Check if question starts with simple pattern
    if any(question_lower.startswith(starter) for starter in simple_starters):
        # Extra check: make sure it's not actually comparative
        # Example: "what's better, google or meta" should be COMPARATIVE
        if not has_comparative_keywords and not has_comparison_in_dsl:
            return AnswerIntent.SIMPLE
    
    # Default: COMPARATIVE (safe middle ground)
    # If we can't confidently classify, give moderate detail
    return AnswerIntent.COMPARATIVE


def explain_intent(intent: AnswerIntent) -> str:
    """
    Get human-readable explanation of an intent classification.
    
    Useful for debugging and logging.
    
    Args:
        intent: Classified intent
        
    Returns:
        str: Explanation of what this intent means for answer generation
    """
    explanations = {
        AnswerIntent.SIMPLE: "Simple fact query - answer with 1 sentence, no extra context",
        AnswerIntent.COMPARATIVE: "Comparative query - include comparisons and moderate context",
        AnswerIntent.ANALYTICAL: "Analytical query - provide full rich context and insights"
    }
    return explanations.get(intent, "Unknown intent")


class VerbTense(str, Enum):
    """Verb tense for answer generation."""
    PAST = "past"
    PRESENT = "present"
    FUTURE = "future"


class PerformerIntent(str, Enum):
    """
    Performer query intent for breakdown queries.
    
    Used to determine correct language when user asks for "lowest" or "highest".
    
    Examples:
        - "Which campaign had the lowest CPC?" → BEST_PERFORMER (CPC is inverse, lower is better)
        - "Which campaign had the highest CPC?" → WORST_PERFORMER (CPC is inverse, higher is worse)
        - "Which campaign had the lowest CTR?" → WORST_PERFORMER (CTR is normal, lower is worse)
        - "Which campaign had the highest ROAS?" → BEST_PERFORMER (ROAS is normal, higher is better)
    """
    BEST_PERFORMER = "best_performer"    # User wants to see the best performing entity
    WORST_PERFORMER = "worst_performer"  # User wants to see the worst performing entity
    NEUTRAL = "neutral"                  # User just wants data, no performance judgment


def detect_tense(question: str, timeframe_desc: Optional[str] = None) -> VerbTense:
    """
    Detect appropriate verb tense for the answer.
    
    Rules:
    - "was", "did", "had" + past timeframes → PAST
    - "is", "are", "do" + "today", "now" → PRESENT
    - "will", "going to" → FUTURE
    - Default based on timeframe
    """
    question_lower = question.lower()
    
    # Past tense indicators
    past_indicators = ["was", "were", "did", "had", "spent", "made", "got", "generated"]
    past_timeframes = ["yesterday", "last week", "last month", "last year", "ago"]
    
    # Check question for past tense
    if any(word in question_lower for word in past_indicators):
        return VerbTense.PAST
    
    # Check timeframe for past
    if timeframe_desc:
        if any(tf in timeframe_desc.lower() for tf in past_timeframes):
            return VerbTense.PAST
    
    # Present tense indicators
    present_indicators = ["is", "are", "am", "do", "does", "have", "has"]
    present_timeframes = ["today", "now", "current", "this hour"]
    
    if any(word in question_lower for word in present_indicators):
        if timeframe_desc and any(tf in timeframe_desc.lower() for tf in present_timeframes):
            return VerbTense.PRESENT
        # "is" with past timeframe should be PAST
        elif timeframe_desc and any(tf in timeframe_desc.lower() for tf in past_timeframes):
            return VerbTense.PAST
    
    # Future tense indicators
    future_indicators = ["will", "going to", "gonna", "shall"]
    if any(word in question_lower for word in future_indicators):
        return VerbTense.FUTURE
    
    # Default based on timeframe
    if timeframe_desc:
        if "last" in timeframe_desc or "ago" in timeframe_desc or "yesterday" in timeframe_desc:
            return VerbTense.PAST
        elif "next" in timeframe_desc or "tomorrow" in timeframe_desc:
            return VerbTense.FUTURE
    
    # Default to present
    return VerbTense.PRESENT


def detect_performer_intent(question: str, query: MetricQuery) -> PerformerIntent:
    """
    Detect whether user is asking for best or worst performer.
    
    WHY this exists:
    - "Lowest CPC" means best performer (since CPC is inverse - lower is better)
    - "Lowest CTR" means worst performer (since CTR is normal - higher is better)
    - Need to adjust language accordingly to avoid confusion
    
    WHAT it does:
    - Detects "lowest/minimum/worst" vs "highest/maximum/best" keywords
    - Checks if metric is inverse (lower=better) or normal (higher=better)
    - Returns appropriate intent for answer language
    
    Args:
        question: User's original question
        query: MetricQuery with metric name
        
    Returns:
        PerformerIntent: Whether to use "best" or "worst" language
        
    Examples:
        >>> query = MetricQuery(metric="cpc", breakdown="campaign")
        >>> detect_performer_intent("Which campaign had the lowest CPC?", query)
        PerformerIntent.BEST_PERFORMER  # Lower CPC is better
        
        >>> query = MetricQuery(metric="cpc", breakdown="campaign")
        >>> detect_performer_intent("Which campaign had the highest CPC?", query)
        PerformerIntent.WORST_PERFORMER  # Higher CPC is worse
        
        >>> query = MetricQuery(metric="ctr", breakdown="campaign")
        >>> detect_performer_intent("Which campaign had the lowest CTR?", query)
        PerformerIntent.WORST_PERFORMER  # Lower CTR is worse
        
        >>> query = MetricQuery(metric="roas", breakdown="campaign")
        >>> detect_performer_intent("Which campaign had the highest ROAS?", query)
        PerformerIntent.BEST_PERFORMER  # Higher ROAS is better
    
    Logic:
        1. Check if question contains "lowest/minimum/worst" or "highest/maximum/best"
        2. Import metric directionality from registry
        3. Combine to determine if user wants best or worst
        
        Truth table:
        | Keyword  | Metric Type | Intent           |
        |----------|-------------|------------------|
        | Lowest   | Inverse     | BEST_PERFORMER   |
        | Lowest   | Normal      | WORST_PERFORMER  |
        | Highest  | Inverse     | WORST_PERFORMER  |
        | Highest  | Normal      | BEST_PERFORMER   |
    
    References:
        - app/metrics/registry.py: INVERSE_METRICS, NORMAL_METRICS
        - Used by: app/answer/answer_builder.py
    """
    from app.metrics.registry import is_inverse_metric
    
    question_lower = question.lower()
    
    # Check if it's a breakdown query (only relevant for breakdowns)
    if not query.breakdown:
        return PerformerIntent.NEUTRAL
    
    # Detect if user is asking for lowest/minimum
    asking_for_lowest = any(kw in question_lower for kw in [
        "lowest", "minimum", "min", "smallest", "least", "worse", "worst"
    ])
    
    # Detect if user is asking for highest/maximum
    asking_for_highest = any(kw in question_lower for kw in [
        "highest", "maximum", "max", "largest", "most", "best", "top"
    ])
    
    # If neither, return neutral
    if not asking_for_lowest and not asking_for_highest:
        return PerformerIntent.NEUTRAL
    
    # Check if metric is inverse (lower is better)
    metric_name = query.metric
    if isinstance(metric_name, list):
        # For multi-metric queries, use the first metric to determine intent
        metric_name = metric_name[0] if metric_name else "value"
        
    metric_is_inverse = is_inverse_metric(metric_name)
    
    # Apply truth table logic
    if asking_for_lowest:
        # Lowest CPC (inverse) = BEST, Lowest CTR (normal) = WORST
        return PerformerIntent.BEST_PERFORMER if metric_is_inverse else PerformerIntent.WORST_PERFORMER
    else:  # asking_for_highest
        # Highest CPC (inverse) = WORST, Highest ROAS (normal) = BEST
        return PerformerIntent.WORST_PERFORMER if metric_is_inverse else PerformerIntent.BEST_PERFORMER

