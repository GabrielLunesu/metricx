# Phase 1 Implementation Specification: Fix Critical Bugs & Add Intent Classification

**Goal**: Fix workspace average calculation bug and implement intent-based answer depth to make simple questions get simple answers.

**Timeline**: Week 1 (5 days)

**Success Criteria**:
- ✅ Workspace avg ≠ summary (bug fixed with test coverage)
- ✅ Simple questions get 1-sentence answers
- ✅ Comparative questions get 2-3 sentence answers with context
- ✅ Analytical questions get full rich context
- ✅ 10 test questions all pass quality checks

---

## Task 1: Fix Workspace Average Calculation Bug

### Problem Statement

The `workspace_avg` field in `MetricResult` is showing the same value as `summary`:

```json
{
  "summary": 3.8777280833639898,
  "workspace_avg": 3.8777280833639898  // ← Should be different!
}
```

**Root Cause**: The `_calculate_workspace_avg()` function in `backend/app/dsl/executor.py` is likely applying query filters when it should calculate across ALL workspace data (no filters).

**Expected Behavior**: 
- User queries "what was my ROAS for Google campaigns" → `summary` = Google ROAS only
- `workspace_avg` should be ROAS across ALL platforms (Google, Meta, TikTok, etc.)
- These values should typically be different

### Step 1.1: Add Debug Logging

**File**: `backend/app/dsl/executor.py`

**Location**: Function `_calculate_workspace_avg()` (around line 605)

**Action**: Add comprehensive debug logging to understand what's happening

**Code Changes**:

```python
def _calculate_workspace_avg(
    db: Session,
    workspace_id: str,
    metric: str,
    time_range: TimeRange
) -> Optional[float]:
    """
    WHAT: Calculate workspace-wide average for a metric over time range
    WHY: Provides comparison baseline for "above/below average" context
    WHERE: Called by _execute_metrics_plan() during metrics query execution
    
    CRITICAL: This function must NOT apply any filters from the original query.
    It should calculate the metric across ALL entities in the workspace.
    
    ARGS:
        db: Database session
        workspace_id: Workspace UUID (tenant isolation)
        metric: Metric name (e.g., "roas", "cpc")
        time_range: Time range for calculation (same as query)
    
    RETURNS:
        float: Workspace average for the metric, or None if cannot compute
    
    EXAMPLE:
        Query: "What's ROAS for Google campaigns?" (filter: provider=google)
        Main query summary: 4.2× (Google only)
        workspace_avg: 3.8× (ALL platforms)
        Result: Different values ✅
    """
    MF, E = models.MetricFact, models.Entity
    
    try:
        # Get required base measures for this metric
        dependencies = get_required_bases(metric)
        if not dependencies:
            logger.warning(f"[WORKSPACE_AVG] Unknown metric: {metric}")
            return None
        
        logger.info(f"[WORKSPACE_AVG] Calculating for metric: {metric}")
        logger.info(f"[WORKSPACE_AVG] Dependencies: {dependencies}")
        logger.info(f"[WORKSPACE_AVG] Time range: start={time_range.start}, end={time_range.end}")
        
        # Base query: ALL entities in workspace (NO FILTERS except workspace_id and time)
        # CRITICAL: Do NOT apply provider, level, status, or entity_ids filters
        query = (
            db.query(
                *[func.coalesce(func.sum(getattr(MF, dep)), 0).label(dep) 
                  for dep in dependencies]
            )
            .join(E, E.id == MF.entity_id)
            .filter(E.workspace_id == workspace_id)  # ✅ Only workspace filter
        )
        
        logger.info(f"[WORKSPACE_AVG] Query filters: workspace_id={workspace_id}")
        
        # Apply time range filter (but NO other filters)
        if time_range.start and time_range.end:
            query = query.filter(
                cast(MF.event_date, Date).between(
                    time_range.start, time_range.end
                )
            )
            logger.info(f"[WORKSPACE_AVG] Time filter: {time_range.start} to {time_range.end}")
        elif time_range.last_n_days:
            cutoff = datetime.now() - timedelta(days=time_range.last_n_days)
            query = query.filter(
                cast(MF.event_date, Date) >= cutoff.date()
            )
            logger.info(f"[WORKSPACE_AVG] Time filter: last {time_range.last_n_days} days")
        
        # Execute
        row = query.first()
        if not row:
            logger.warning(f"[WORKSPACE_AVG] No data found for workspace {workspace_id}")
            return None
        
        # Compute metric (with divide-by-zero protection)
        base_measures = {dep: getattr(row, dep) or 0 for dep in dependencies}
        workspace_avg = compute_metric(metric, base_measures)
        
        logger.info(f"[WORKSPACE_AVG] Base measures: {base_measures}")
        logger.info(f"[WORKSPACE_AVG] Calculated workspace avg: {workspace_avg}")
        
        return workspace_avg
    
    except Exception as e:
        logger.error(f"[WORKSPACE_AVG] Failed to calculate workspace avg for {metric}: {e}")
        return None
```

**Key Changes**:
1. Added `[WORKSPACE_AVG]` prefix to all logs for easy filtering
2. Log dependencies, time range, filters applied
3. Log base measures and final result
4. Enhanced docstring with CRITICAL note about not applying filters
5. Added example showing expected different values

### Step 1.2: Create Test to Verify Bug Fix

**File**: `backend/app/tests/test_workspace_avg.py` (NEW FILE)

**Purpose**: Prove the bug exists, then prove it's fixed

**Code**:

```python
"""
Tests for Workspace Average Calculation

WHAT: Verify workspace_avg is calculated correctly (without query filters)
WHY: Ensure workspace comparison context is accurate
WHERE: Tests app/dsl/executor.py::_calculate_workspace_avg()

Critical test: workspace_avg should be different from summary when filters are applied
"""

import pytest
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.dsl.schema import MetricQuery, MetricResult, TimeRange, Filters
from app.dsl.planner import build_plan
from app.dsl.executor import execute_plan, _calculate_workspace_avg
from app import models


@pytest.fixture
def workspace_with_multi_provider_data(db: Session):
    """
    Create test data with multiple providers to test workspace avg.
    
    Setup:
    - 2 campaigns on Google (high ROAS)
    - 2 campaigns on Meta (low ROAS)
    - Overall workspace ROAS should be ~3.0
    - Google-only ROAS should be ~4.5
    - Meta-only ROAS should be ~1.5
    """
    workspace = models.Workspace(name="Test Workspace Avg")
    db.add(workspace)
    db.flush()
    
    # Google campaigns (high performers)
    google_campaign_1 = models.Entity(
        workspace_id=workspace.id,
        provider="google",
        level="campaign",
        name="Google Campaign 1",
        status="active"
    )
    google_campaign_2 = models.Entity(
        workspace_id=workspace.id,
        provider="google",
        level="campaign",
        name="Google Campaign 2",
        status="active"
    )
    
    # Meta campaigns (low performers)
    meta_campaign_1 = models.Entity(
        workspace_id=workspace.id,
        provider="meta",
        level="campaign",
        name="Meta Campaign 1",
        status="active"
    )
    meta_campaign_2 = models.Entity(
        workspace_id=workspace.id,
        provider="meta",
        level="campaign",
        name="Meta Campaign 2",
        status="active"
    )
    
    db.add_all([google_campaign_1, google_campaign_2, meta_campaign_1, meta_campaign_2])
    db.flush()
    
    # Add metrics data
    today = date.today()
    
    # Google: High ROAS (4.5× average)
    # Campaign 1: $1000 spend, $4500 revenue (4.5×)
    db.add(models.MetricFact(
        workspace_id=workspace.id,
        entity_id=google_campaign_1.id,
        provider="google",
        level="campaign",
        event_date=today - timedelta(days=15),
        spend=1000,
        revenue=4500,
        clicks=500,
        impressions=10000,
        conversions=50
    ))
    
    # Campaign 2: $1000 spend, $4500 revenue (4.5×)
    db.add(models.MetricFact(
        workspace_id=workspace.id,
        entity_id=google_campaign_2.id,
        provider="google",
        level="campaign",
        event_date=today - timedelta(days=15),
        spend=1000,
        revenue=4500,
        clicks=500,
        impressions=10000,
        conversions=50
    ))
    
    # Meta: Low ROAS (1.5× average)
    # Campaign 1: $1000 spend, $1500 revenue (1.5×)
    db.add(models.MetricFact(
        workspace_id=workspace.id,
        entity_id=meta_campaign_1.id,
        provider="meta",
        level="campaign",
        event_date=today - timedelta(days=15),
        spend=1000,
        revenue=1500,
        clicks=300,
        impressions=8000,
        conversions=30
    ))
    
    # Campaign 2: $1000 spend, $1500 revenue (1.5×)
    db.add(models.MetricFact(
        workspace_id=workspace.id,
        entity_id=meta_campaign_2.id,
        provider="meta",
        level="campaign",
        event_date=today - timedelta(days=15),
        spend=1000,
        revenue=1500,
        clicks=300,
        impressions=8000,
        conversions=30
    ))
    
    db.commit()
    
    return workspace


class TestWorkspaceAverageCalculation:
    """Tests for workspace average calculation."""
    
    def test_workspace_avg_ignores_provider_filter(self, db, workspace_with_multi_provider_data):
        """
        CRITICAL TEST: Workspace avg should be calculated across ALL providers,
        even when the main query filters to a specific provider.
        
        Setup:
        - Google ROAS: 4.5×
        - Meta ROAS: 1.5×
        - Overall workspace ROAS: 3.0×
        
        Test:
        - Query "What's my ROAS for Google campaigns?"
        - Summary should be 4.5× (Google only)
        - workspace_avg should be 3.0× (ALL providers)
        - Values should be DIFFERENT ✅
        """
        workspace = workspace_with_multi_provider_data
        
        # Query with Google filter
        query = MetricQuery(
            query_type="metrics",
            metric="roas",
            time_range=TimeRange(last_n_days=30),
            filters=Filters(provider="google")
        )
        
        plan = build_plan(query)
        result = execute_plan(db, str(workspace.id), plan, query)
        
        # Verify summary is Google-only ROAS (4.5×)
        assert result.summary == pytest.approx(4.5, rel=0.01), \
            f"Expected Google ROAS ~4.5×, got {result.summary}"
        
        # Verify workspace_avg is ALL providers (3.0×)
        assert result.workspace_avg is not None, "workspace_avg should not be None"
        assert result.workspace_avg == pytest.approx(3.0, rel=0.01), \
            f"Expected workspace avg ~3.0×, got {result.workspace_avg}"
        
        # CRITICAL: They should be DIFFERENT
        assert result.summary != result.workspace_avg, \
            "BUG: workspace_avg should differ from summary when filters are applied!"
        
        print(f"✅ Test passed: summary={result.summary:.2f}, workspace_avg={result.workspace_avg:.2f}")
    
    def test_workspace_avg_ignores_status_filter(self, db, workspace_with_multi_provider_data):
        """
        Test that workspace avg ignores status filter.
        
        Even if we query only active campaigns, workspace_avg should include
        both active and paused campaigns.
        """
        workspace = workspace_with_multi_provider_data
        
        # Pause one Meta campaign
        meta_campaign = db.query(models.Entity).filter(
            models.Entity.workspace_id == workspace.id,
            models.Entity.provider == "meta"
        ).first()
        meta_campaign.status = "paused"
        db.commit()
        
        # Query with active filter
        query = MetricQuery(
            query_type="metrics",
            metric="roas",
            time_range=TimeRange(last_n_days=30),
            filters=Filters(status="active")
        )
        
        plan = build_plan(query)
        result = execute_plan(db, str(workspace.id), plan, query)
        
        # workspace_avg should still include the paused campaign
        assert result.workspace_avg is not None
        # Should be close to 3.0 (includes all 4 campaigns, even paused one)
        assert result.workspace_avg == pytest.approx(3.0, rel=0.1)
    
    def test_workspace_avg_with_no_filters(self, db, workspace_with_multi_provider_data):
        """
        Test that workspace avg equals summary when no filters are applied.
        
        When querying the entire workspace, summary and workspace_avg should match.
        """
        workspace = workspace_with_multi_provider_data
        
        # Query with NO filters
        query = MetricQuery(
            query_type="metrics",
            metric="roas",
            time_range=TimeRange(last_n_days=30)
        )
        
        plan = build_plan(query)
        result = execute_plan(db, str(workspace.id), plan, query)
        
        # Both should be ~3.0× (entire workspace)
        assert result.summary == pytest.approx(3.0, rel=0.01)
        assert result.workspace_avg == pytest.approx(3.0, rel=0.01)
        
        # They should be equal (or very close) in this case
        assert abs(result.summary - result.workspace_avg) < 0.01, \
            "When no filters applied, summary and workspace_avg should match"
    
    def test_workspace_avg_helper_function_directly(self, db, workspace_with_multi_provider_data):
        """
        Test _calculate_workspace_avg() function directly.
        
        Verifies the helper function works correctly in isolation.
        """
        workspace = workspace_with_multi_provider_data
        
        time_range = TimeRange(last_n_days=30)
        
        # Calculate workspace average for ROAS
        workspace_avg = _calculate_workspace_avg(
            db=db,
            workspace_id=str(workspace.id),
            metric="roas",
            time_range=time_range
        )
        
        # Should be ~3.0× (average of all 4 campaigns)
        assert workspace_avg is not None
        assert workspace_avg == pytest.approx(3.0, rel=0.01), \
            f"Expected workspace avg ~3.0×, got {workspace_avg}"


class TestWorkspaceAvgEdgeCases:
    """Test edge cases for workspace average calculation."""
    
    def test_workspace_avg_with_zero_denominator(self, db, workspace_with_multi_provider_data):
        """
        Test that workspace avg handles divide-by-zero gracefully.
        
        If a metric can't be calculated (e.g., ROAS with $0 spend),
        should return None without crashing.
        """
        workspace = workspace_with_multi_provider_data
        
        # Delete all metric facts to create zero-spend scenario
        db.query(models.MetricFact).filter(
            models.MetricFact.workspace_id == workspace.id
        ).delete()
        db.commit()
        
        time_range = TimeRange(last_n_days=30)
        
        workspace_avg = _calculate_workspace_avg(
            db=db,
            workspace_id=str(workspace.id),
            metric="roas",
            time_range=time_range
        )
        
        # Should handle gracefully (return None)
        assert workspace_avg is None, "Should return None when no data available"
    
    def test_workspace_avg_with_unknown_metric(self, db, workspace_with_multi_provider_data):
        """
        Test that workspace avg handles unknown metrics gracefully.
        """
        workspace = workspace_with_multi_provider_data
        
        time_range = TimeRange(last_n_days=30)
        
        workspace_avg = _calculate_workspace_avg(
            db=db,
            workspace_id=str(workspace.id),
            metric="invalid_metric_xyz",
            time_range=time_range
        )
        
        # Should return None for unknown metric
        assert workspace_avg is None
```

**Test Execution**:

```bash
cd backend
pytest app/tests/test_workspace_avg.py -v
```

**Expected Outcome**:
- **If bug exists**: Test `test_workspace_avg_ignores_provider_filter` will FAIL
- **After fix**: All tests PASS ✅

### Step 1.3: Run Tests and Verify Bug

**Action**: Run the test to confirm the bug exists

```bash
cd backend
pytest app/tests/test_workspace_avg.py::TestWorkspaceAverageCalculation::test_workspace_avg_ignores_provider_filter -v -s
```

**Look for**:
- `[WORKSPACE_AVG]` logs showing what's being calculated
- Test assertion failure showing `summary == workspace_avg` (the bug)

### Step 1.4: Fix the Bug (If Confirmed)

**Based on logs, identify the issue**:

**Possible causes**:
1. ❌ Filters from main query leaking into workspace avg calculation
2. ❌ Using wrong workspace_id
3. ❌ Time range calculation incorrect

**Most likely fix**: Ensure NO filters except `workspace_id` and `time_range` are applied

The code in Step 1.1 already has the fix - verify that's what's in the file. If filters are being applied elsewhere, remove them.

### Step 1.5: Verify Fix with Tests

```bash
cd backend
pytest app/tests/test_workspace_avg.py -v
```

**All tests should PASS** ✅

---

## Task 2: Implement Intent Classification

### Goal

Detect if user wants:
- **SIMPLE**: Just the number ("What was my ROAS?")
- **COMPARATIVE**: Comparison/context ("How does my ROAS compare?")
- **ANALYTICAL**: Full analysis ("Why is my ROAS low?")

### Step 2.1: Create Intent Classifier Module

**File**: `backend/app/answer/intent_classifier.py` (NEW FILE)

**Code**:

```python
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
        "problem", "issue", "volatile", "volatility"
    ]
    
    if any(kw in question_lower for kw in analytical_keywords):
        return AnswerIntent.ANALYTICAL
    
    # COMPARATIVE: Asking to compare things
    # These users want context and comparison, not just a single number
    comparative_keywords = [
        "compare", "comparison", "vs", "versus",
        "better", "worse", "best", "worst",
        "higher", "lower", "more", "less",
        "top", "bottom", "rank", "ranking",
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
```

### Step 2.2: Create Tests for Intent Classifier

**File**: `backend/app/tests/test_intent_classifier.py` (NEW FILE)

**Code**:

```python
"""
Tests for Intent Classifier

WHAT: Verify intent classification works correctly
WHY: Ensures questions are routed to appropriate answer depth
WHERE: Tests app/answer/intent_classifier.py
"""

import pytest
from app.answer.intent_classifier import classify_intent, AnswerIntent, explain_intent
from app.dsl.schema import MetricQuery, TimeRange, Filters


class TestSimpleIntent:
    """Test SIMPLE intent classification."""
    
    def test_what_was_my_metric(self):
        """Simple fact questions should be classified as SIMPLE."""
        questions = [
            "what was my roas last month",
            "what's my cpc today",
            "what is my conversion rate",
        ]
        
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=30),
            compare_to_previous=False,
            breakdown=None
        )
        
        for question in questions:
            intent = classify_intent(question, query)
            assert intent == AnswerIntent.SIMPLE, \
                f"'{question}' should be SIMPLE, got {intent}"
    
    def test_how_much_did_i(self):
        """'How much' questions should be SIMPLE."""
        questions = [
            "how much did I spend yesterday",
            "how much revenue did I make",
            "how many clicks did I get"
        ]
        
        query = MetricQuery(
            metric="spend",
            time_range=TimeRange(last_n_days=1),
            compare_to_previous=False,
            breakdown=None
        )
        
        for question in questions:
            intent = classify_intent(question, query)
            assert intent == AnswerIntent.SIMPLE
    
    def test_show_me_queries(self):
        """'Show me' should be SIMPLE if no breakdown."""
        question = "show me my roas"
        
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=7),
            compare_to_previous=False,
            breakdown=None
        )
        
        intent = classify_intent(question, query)
        assert intent == AnswerIntent.SIMPLE


class TestComparativeIntent:
    """Test COMPARATIVE intent classification."""
    
    def test_explicit_comparison_keywords(self):
        """Questions with 'compare', 'vs', etc. should be COMPARATIVE."""
        questions = [
            "compare google vs meta",
            "how does this week compare to last week",
            "is google better than meta",
            "which platform is worse"
        ]
        
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=7)
        )
        
        for question in questions:
            intent = classify_intent(question, query)
            assert intent == AnswerIntent.COMPARATIVE, \
                f"'{question}' should be COMPARATIVE, got {intent}"
    
    def test_which_questions(self):
        """'Which X' questions are typically comparative."""
        questions = [
            "which campaign had highest roas",
            "which platform performed best",
            "what campaign spent the most"
        ]
        
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=7),
            breakdown="campaign",
            top_n=1
        )
        
        for question in questions:
            intent = classify_intent(question, query)
            assert intent == AnswerIntent.COMPARATIVE
    
    def test_dsl_has_comparison(self):
        """If DSL has compare_to_previous, should be COMPARATIVE."""
        question = "what was my roas"  # Looks simple
        
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=7),
            compare_to_previous=True  # But DSL has comparison
        )
        
        intent = classify_intent(question, query)
        assert intent == AnswerIntent.COMPARATIVE
    
    def test_dsl_has_breakdown(self):
        """If DSL has breakdown, should be COMPARATIVE."""
        question = "show me roas"  # Looks simple
        
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=7),
            breakdown="campaign"  # But DSL has breakdown
        )
        
        intent = classify_intent(question, query)
        assert intent == AnswerIntent.COMPARATIVE


class TestAnalyticalIntent:
    """Test ANALYTICAL intent classification."""
    
    def test_why_questions(self):
        """'Why' questions should always be ANALYTICAL."""
        questions = [
            "why is my roas low",
            "why did my cpc increase",
            "why is performance bad"
        ]
        
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=7)
        )
        
        for question in questions:
            intent = classify_intent(question, query)
            assert intent == AnswerIntent.ANALYTICAL, \
                f"'{question}' should be ANALYTICAL, got {intent}"
    
    def test_explain_questions(self):
        """'Explain' questions should be ANALYTICAL."""
        questions = [
            "explain the trend in my roas",
            "explain why performance dropped",
            "can you explain this pattern"
        ]
        
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=30)
        )
        
        for question in questions:
            intent = classify_intent(question, query)
            assert intent == AnswerIntent.ANALYTICAL
    
    def test_analyze_questions(self):
        """'Analyze' questions should be ANALYTICAL."""
        questions = [
            "analyze my campaign performance",
            "give me an analysis of roas",
            "what's the analysis"
        ]
        
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=30)
        )
        
        for question in questions:
            intent = classify_intent(question, query)
            assert intent == AnswerIntent.ANALYTICAL
    
    def test_trend_questions(self):
        """Questions about trends should be ANALYTICAL."""
        questions = [
            "what's the trend in my roas",
            "show me the pattern",
            "is there a trend here"
        ]
        
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=30)
        )
        
        for question in questions:
            intent = classify_intent(question, query)
            assert intent == AnswerIntent.ANALYTICAL


class TestEdgeCases:
    """Test edge cases and ambiguous questions."""
    
    def test_empty_question(self):
        """Empty question should default to COMPARATIVE."""
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=7)
        )
        
        intent = classify_intent("", query)
        assert intent == AnswerIntent.COMPARATIVE  # Safe default
    
    def test_ambiguous_question(self):
        """Ambiguous questions default to COMPARATIVE."""
        question = "roas"  # Just a metric name
        
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=7)
        )
        
        intent = classify_intent(question, query)
        assert intent == AnswerIntent.COMPARATIVE
    
    def test_what_is_better_google_or_meta(self):
        """'What's better' should be COMPARATIVE, not SIMPLE."""
        question = "what's better, google or meta"
        
        query = MetricQuery(
            metric="roas",
            time_range=TimeRange(last_n_days=7),
            breakdown="provider"
        )
        
        intent = classify_intent(question, query)
        assert intent == AnswerIntent.COMPARATIVE  # Not SIMPLE!


class TestExplainIntent:
    """Test explain_intent helper function."""
    
    def test_explain_all_intents(self):
        """Verify all intents have explanations."""
        for intent in AnswerIntent:
            explanation = explain_intent(intent)
            assert explanation is not None
            assert len(explanation) > 0
            assert isinstance(explanation, str)
    
    def test_simple_explanation(self):
        """Verify SIMPLE intent explanation."""
        explanation = explain_intent(AnswerIntent.SIMPLE)
        assert "1 sentence" in explanation
        assert "no extra context" in explanation
    
    def test_comparative_explanation(self):
        """Verify COMPARATIVE intent explanation."""
        explanation = explain_intent(AnswerIntent.COMPARATIVE)
        assert "comparison" in explanation
        assert "moderate context" in explanation
    
    def test_analytical_explanation(self):
        """Verify ANALYTICAL intent explanation."""
        explanation = explain_intent(AnswerIntent.ANALYTICAL)
        assert "full rich context" in explanation
        assert "insights" in explanation
```

**Run tests**:

```bash
cd backend
pytest app/tests/test_intent_classifier.py -v
```

All tests should PASS ✅

---

## Task 3: Create Intent-Specific Answer Prompts

### Step 3.1: Add New Prompts to prompts.py

**File**: `backend/app/nlp/prompts.py`

**Location**: After existing `ANSWER_GENERATION_PROMPT` (around line 660)

**Add**:

```python
# =====================================================================
# Intent-Specific Answer Generation Prompts (Phase 1)
# =====================================================================
# WHY: Different question intents deserve different answer depths
# WHAT: Three prompts for SIMPLE, COMPARATIVE, and ANALYTICAL intents
# USAGE: app/answer/answer_builder.py selects prompt based on intent
# =====================================================================

SIMPLE_ANSWER_PROMPT = """You are a helpful marketing analytics assistant.

The user asked a SIMPLE factual question. They want a quick answer, not analysis.

YOUR TASK: Give them a direct, concise answer in ONE sentence.

CRITICAL RULES:
1. Answer in EXACTLY ONE sentence
2. State the metric value clearly
3. NO comparisons unless explicitly in the context
4. NO analysis, NO trends, NO recommendations
5. NO workspace average mentions
6. Be conversational but BRIEF
7. Use the formatted values (not raw numbers)

GOOD Examples (SIMPLE intent):
- "Your ROAS last month was 3.88×"
- "You spent $1,234 yesterday"
- "Your CPC this week is $0.48"
- "You got 1,250 clicks today"
- "Your conversion rate is 4.2%"

BAD Examples (too verbose):
- "Your ROAS last month was 3.88×, which is performing well compared to..."  ❌ Too much!
- "You spent $1,234 yesterday. This represents a..."  ❌ Extra sentence!
- "Your CPC this week is $0.48. That's better than..."  ❌ Unwanted comparison!

Remember: They asked for a fact. Give them JUST that fact. Nothing more."""

COMPARATIVE_ANSWER_PROMPT = """You are a helpful marketing analytics colleague.

The user wants to COMPARE metrics or see context. Give them a clear comparison.

YOUR TASK: Provide a natural answer with comparison context in 2-3 sentences.

TONE: Conversational, like explaining to a friend over coffee
STYLE: Use contractions (it's, you're, that's), avoid formal business speak
LENGTH: 2-3 sentences maximum

WHAT TO INCLUDE:
- Main metric value (always)
- Comparison context if available (previous period, workspace avg, top performer)
- Brief interpretation ("that's good", "up from", "better than")

WHAT TO SKIP:
- Long explanations
- Detailed trend analysis
- Recommendations
- Multiple comparisons (pick the most relevant one)

GOOD Examples (COMPARATIVE intent):
- "Your ROAS is 2.45× this week, up 19% from last week's 2.06×—nice improvement"
- "Google's crushing it at $0.32 CPC while Meta's at $0.51. Overall you're at $0.42"
- "Summer Sale is your top performer at 3.20× ROAS, pulling your overall average up to 2.88×"
- "You spent $5,234 this month, which is 15% less than last month. Looks like you're scaling back"

BAD Examples (too formal):
- "Your ROAS for the selected period is 2.45×. That represents a +19.0% change vs the previous period."  ❌ Too robotic!
- "The Google platform demonstrates superior performance relative to Meta."  ❌ Too formal!

BAD Examples (too verbose):
- "Your ROAS jumped to 2.45× this week—that's 19% better than last week. Over time, it has shown some volatility, peaking at..."  ❌ Too long!

Remember: Be helpful and clear, but keep it concise. Sound like a human."""

ANALYTICAL_ANSWER_PROMPT = """You are a knowledgeable marketing analytics advisor.

The user wants to UNDERSTAND something. They asked "why" or want analysis. Give them insights.

YOUR TASK: Provide a thorough, insightful answer with full context in 3-4 sentences.

TONE: Professional but approachable, like a consultant explaining findings
DEPTH: Include trends, comparisons, outliers, and interpretation
LENGTH: 3-4 sentences (don't exceed 4)

WHAT TO INCLUDE:
- Main metric value with context
- Relevant trends (if available)
- Notable outliers or patterns
- Workspace comparison (if available)
- Constructive interpretation or observation

STRUCTURE:
1. Lead with the current state + direction
2. Explain what's driving it (trends, top performers, outliers)
3. Provide context (workspace avg, comparison to previous)
4. End with observation or gentle suggestion (if performance is poor)

GOOD Examples (ANALYTICAL intent):
- "Your ROAS has been quite volatile this month, swinging from a low of 1.38× to a high of 5.80×. Most of the volatility seems to be coming from your Meta campaigns, which are showing inconsistent daily performance. Your overall average of 3.88× is right in line with your workspace norm, but the wide swings suggest you might want to review your bidding strategy or creative rotation"

- "Your CPC jumped to $0.85 last week, which is 45% higher than the previous week and well above your workspace average of $0.52. The spike came primarily from your 'New Product Launch' campaign on Google, which is driving up costs across the board. You might want to review that campaign's targeting or pause it temporarily"

- "Your ROAS improved nicely to 4.2× this month, up from 3.1× last month—that's a solid 35% increase. The improvement was driven by your 'Summer Sale' campaign, which delivered an impressive 5.8× return and pulled up your overall performance. This is well above your workspace average of 3.2×, so whatever you're doing with that campaign, keep it up"

BAD Examples (too brief):
- "Your ROAS is 3.88×"  ❌ Not enough analysis!
- "Your ROAS is 3.88× this month, up from last month"  ❌ Too simple for analytical intent!

BAD Examples (too long):
- "Your ROAS has been volatile... [5+ sentences of analysis]"  ❌ Too long, overwhelming!

Remember: They want to understand, not just know the number. Provide insights, but stay concise."""
```

---

## Task 4: Integrate Intent Classification into AnswerBuilder

### Step 4.1: Modify answer_builder.py

**File**: `backend/app/answer/answer_builder.py`

**Changes**:

1. **Import intent classifier** (top of file):
```python
from app.answer.intent_classifier import classify_intent, AnswerIntent, explain_intent
from app.nlp.prompts import (
    ANSWER_GENERATION_PROMPT,  # Existing (now only for fallback)
    SIMPLE_ANSWER_PROMPT,      # NEW
    COMPARATIVE_ANSWER_PROMPT, # NEW
    ANALYTICAL_ANSWER_PROMPT   # NEW
)
```

2. **Modify `build_answer()` method** (around line 169):

```python
def build_answer(
    self, 
    dsl: MetricQuery, 
    result: Union[MetricResult, Dict[str, Any]],
    window: Optional[Dict[str, date]] = None,
    log_latency: bool = False
) -> tuple[str, Optional[int]]:
    """
    Build a natural language answer from query + results.
    
    CHANGES IN Phase 1:
    - Classify question intent (simple/comparative/analytical)
    - Adjust context depth based on intent
    - Use intent-specific GPT prompts
    
    Args:
        dsl: The MetricQuery that was executed (user intent)
        result: Execution results (MetricResult for metrics, dict for providers/entities)
        window: Optional date window {"start": date, "end": date}
        log_latency: Whether to return latency in ms
        
    Returns:
        tuple: (answer_text, latency_ms) if log_latency=True, else (answer_text, None)
    """
    start_time = time.time() if log_latency else None
    
    try:
        # Step 1: Classify intent (NEW in Phase 1)
        question = getattr(dsl, 'question', None) or f"What is my {dsl.metric}?"
        intent = classify_intent(question, dsl)
        
        logger.info(
            f"[INTENT] Classified as {intent.value}: {explain_intent(intent)}",
            extra={"question": question, "intent": intent.value}
        )
        
        # Step 2: Extract context and build prompt based on intent
        if dsl.query_type == "metrics":
            # Extract rich context
            context = extract_rich_context(
                result=result,
                query=dsl,
                workspace_avg=result.workspace_avg if isinstance(result, MetricResult) else None
            )
            
            # Filter context based on intent (NEW)
            if intent == AnswerIntent.SIMPLE:
                # SIMPLE: Only basic value, no extra context
                filtered_context = {
                    "metric_name": context.metric_name,
                    "metric_value": context.metric_value,
                    "metric_value_raw": context.metric_value_raw
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
                    "performance_level": context.performance_level
                }
                system_prompt = COMPARATIVE_ANSWER_PROMPT
                user_prompt = self._build_comparative_prompt(filtered_context, question)
                
            else:  # ANALYTICAL
                # ANALYTICAL: Include everything (full rich context)
                system_prompt = ANALYTICAL_ANSWER_PROMPT
                user_prompt = self._build_rich_context_prompt(context, dsl)
            
            logger.info(
                f"[INTENT] Using {intent.value} prompt with filtered context",
                extra={
                    "has_comparison": "comparison" in filtered_context if intent != AnswerIntent.ANALYTICAL else True,
                    "has_trend": "trend" in (context.to_dict() if intent == AnswerIntent.ANALYTICAL else {}),
                    "has_workspace_comparison": "workspace_comparison" in (filtered_context if intent != AnswerIntent.ANALYTICAL else context.to_dict())
                }
            )
            
        elif dsl.query_type == "providers":
            facts = self._extract_providers_facts(result)
            system_prompt = self._build_system_prompt()  # Use legacy prompt for non-metrics
            user_prompt = self._build_user_prompt(dsl, facts)
            
        else:  # entities
            facts = self._extract_entities_facts(dsl, result)
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(dsl, facts)
        
        # Step 3: Call GPT with intent-specific prompt
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=200  # Enough for analytical, plenty for simple
        )
        
        answer_text = response.choices[0].message.content.strip()
        
        # Step 4: Calculate latency
        latency_ms = None
        if log_latency and start_time:
            latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"[ANSWER] Generated {intent.value} answer ({len(answer_text)} chars) in {latency_ms}ms"
        )
        
        return answer_text, latency_ms
        
    except Exception as e:
        logger.error(f"Answer generation failed: {e}", exc_info=True)
        raise AnswerBuilderError(
            message=f"Answer generation failed: {str(e)}",
            original_error=e
        )
```

3. **Add new prompt builder methods** (after `_build_rich_context_prompt`):

```python
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
    import json
    
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
    import json
    
    # Filter out None values
    filtered = {k: v for k, v in context.items() if v is not None}
    
    return f"""The user asked: "{question}"

Provide a natural answer with comparison context (2-3 sentences).

CONTEXT:
{json.dumps(filtered, indent=2)}

Remember: Include comparison, keep it conversational, 2-3 sentences max."""
```

---

## Task 5: End-to-End Testing

### Step 5.1: Create Manual Test Script

**File**: `backend/app/tests/test_phase1_manual.py` (for manual testing during development)

**Code**:

```python
"""
Manual test script for Phase 1 implementation.

Run this to test intent classification and answer generation
with real questions during development.

Usage:
    python -m app.tests.test_phase1_manual
"""

import asyncio
from app.services.qa_service import QAService
from app.database import SessionLocal
from app import models


async def test_phase1():
    """Test Phase 1: Intent classification + different answer depths."""
    
    # Find a workspace
    db = SessionLocal()
    workspace = db.query(models.Workspace).first()
    
    if not workspace:
        print("❌ No workspace found. Run seed_mock.py first")
        return
    
    print(f"✅ Using workspace: {workspace.name} ({workspace.id})")
    print("=" * 80)
    
    qa_service = QAService()
    
    # Test questions grouped by expected intent
    test_cases = [
        # SIMPLE intent
        ("what was my roas last month", "SIMPLE", "1 sentence"),
        ("how much did I spend yesterday", "SIMPLE", "1 sentence"),
        ("what's my cpc this week", "SIMPLE", "1 sentence"),
        
        # COMPARATIVE intent
        ("how does my roas compare to last month", "COMPARATIVE", "2-3 sentences with comparison"),
        ("which campaign had highest roas", "COMPARATIVE", "2-3 sentences with top performer"),
        ("compare google vs meta performance", "COMPARATIVE", "2-3 sentences comparing platforms"),
        
        # ANALYTICAL intent
        ("why is my roas so volatile", "ANALYTICAL", "3-4 sentences with trends and insights"),
        ("explain the trend in my cpc", "ANALYTICAL", "3-4 sentences with analysis"),
        ("analyze my campaign performance", "ANALYTICAL", "3-4 sentences with full context"),
    ]
    
    results = []
    
    for question, expected_intent, expected_answer_style in test_cases:
        print(f"\n📝 Question: {question}")
        print(f"   Expected: {expected_intent} intent → {expected_answer_style}")
        print("-" * 80)
        
        try:
            result = await qa_service.answer(
                question=question,
                workspace_id=str(workspace.id),
                user_id="test_user"
            )
            
            answer = result["answer"]
            executed_dsl = result["executed_dsl"]
            
            # Count sentences (rough approximation)
            sentence_count = answer.count('.') + answer.count('!') + answer.count('?')
            
            print(f"✅ Answer ({sentence_count} sentences): {answer}")
            print(f"   DSL: {executed_dsl.get('metric')} over {executed_dsl.get('time_range', {}).get('last_n_days', '?')} days")
            
            # Quality check
            quality = "✅ PASS"
            if expected_intent == "SIMPLE" and sentence_count > 1:
                quality = "⚠️  WARNING: Too verbose for SIMPLE intent"
            elif expected_intent == "COMPARATIVE" and sentence_count > 3:
                quality = "⚠️  WARNING: Too verbose for COMPARATIVE intent"
            elif expected_intent == "ANALYTICAL" and sentence_count > 4:
                quality = "⚠️  WARNING: Too verbose for ANALYTICAL intent"
            
            print(f"   Quality: {quality}")
            
            results.append({
                "question": question,
                "expected_intent": expected_intent,
                "answer": answer,
                "sentence_count": sentence_count,
                "quality": quality
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                "question": question,
                "expected_intent": expected_intent,
                "error": str(e),
                "quality": "❌ FAIL"
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if "✅" in r.get("quality", ""))
    total = len(results)
    
    print(f"\nResults: {passed}/{total} passed")
    
    for r in results:
        status = "✅" if "✅" in r.get("quality", "") else "⚠️" if "⚠️" in r.get("quality", "") else "❌"
        print(f"{status} {r['question'][:50]}")
    
    db.close()


if __name__ == "__main__":
    asyncio.run(test_phase1())
```

**Run it**:

```bash
cd backend
python -m app.tests.test_phase1_manual
```

---

## Implementation Order

Follow this exact order:

### Day 1: Workspace Avg Bug
1. ✅ Add debug logging to `_calculate_workspace_avg()`
2. ✅ Create `test_workspace_avg.py`
3. ✅ Run tests to confirm bug
4. ✅ Fix bug (ensure no filters except workspace_id + time)
5. ✅ Verify all tests pass

### Day 2: Intent Classifier
1. ✅ Create `intent_classifier.py`
2. ✅ Create `test_intent_classifier.py`
3. ✅ Run tests, verify all pass
4. ✅ Manually test with various questions

### Day 3: Intent-Specific Prompts
1. ✅ Add 3 new prompts to `prompts.py`
2. ✅ Add helper methods to `answer_builder.py`
3. ✅ Test prompts manually with GPT

### Day 4: Integration
1. ✅ Modify `build_answer()` in `answer_builder.py`
2. ✅ Wire intent classification → prompt selection
3. ✅ Add logging for observability
4. ✅ Create `test_phase1_manual.py`

### Day 5: Testing & Polish
1. ✅ Run manual test script
2. ✅ Test 10 questions from `100-realistic-questions.md`
3. ✅ Iterate on prompts based on results
4. ✅ Document any issues found
5. ✅ Update `metricx_BUILD_LOG.md` with Phase 1 completion

---

## Success Criteria Checklist

Before marking Phase 1 complete, verify:

### Workspace Avg Bug
- [ ] Test `test_workspace_avg_ignores_provider_filter` PASSES
- [ ] workspace_avg ≠ summary when filters applied
- [ ] workspace_avg == summary when no filters (sanity check)
- [ ] Logs show `[WORKSPACE_AVG]` calculating correctly

### Intent Classification
- [ ] All tests in `test_intent_classifier.py` PASS
- [ ] "what was my roas" → SIMPLE ✅
- [ ] "compare google vs meta" → COMPARATIVE ✅
- [ ] "why is my roas low" → ANALYTICAL ✅

### Answer Generation
- [ ] SIMPLE intent → 1 sentence answers
- [ ] COMPARATIVE intent → 2-3 sentence answers with comparison
- [ ] ANALYTICAL intent → 3-4 sentence answers with insights
- [ ] No robotic "Your X for the selected period is..." phrases

### Manual Testing
- [ ] Tested 10 questions from `100-realistic-questions.md`
- [ ] 8+ questions get expected intent classification
- [ ] 8+ questions get appropriate answer length
- [ ] Answers sound natural, not robotic

---

## Documentation Updates

After Phase 1 completion:

1. **Update `QA_SYSTEM_ARCHITECTURE.md`**:
   - Add Intent Classification section
   - Update Answer Generation flow
   - Add Phase 1 completion to changelog

2. **Update `metricx_BUILD_LOG.md`**:
   - Add changelog entry for Phase 1
   - Include before/after examples
   - Note workspace avg bug fix

3. **Update `ROADMAP_TO_NATURAL_COPILOT.md`**:
   - Mark Phase 1 as complete ✅
   - Update status for Phase 2

---

## Troubleshooting

### If workspace_avg still equals summary after fix:

1. Check logs for `[WORKSPACE_AVG]` entries
2. Verify query has ONLY `workspace_id` and time filters
3. Check if time_range is being calculated correctly
4. Add breakpoint in `_calculate_workspace_avg()` to inspect

### If intent classification is wrong:

1. Add logging to show why intent was classified
2. Check if keywords are too broad/narrow
3. Review DSL fields (compare_to_previous, breakdown)
4. Adjust keyword lists in `classify_intent()`

### If answers are still too verbose:

1. Check if correct prompt is being used
2. Review GPT temperature (should be 0.3)
3. Try adjusting max_tokens
4. Strengthen prompt language ("EXACTLY ONE sentence")

---

_This specification is complete and ready for implementation by an AI IDE._

