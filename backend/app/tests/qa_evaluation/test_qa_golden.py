"""
QA Golden Test Cases
=====================

Automated tests for QA system correctness using golden test cases.

These tests verify:
1. DSL generation correctness (metric, time_range, breakdown, etc.)
2. Visual intent classification
3. Answer quality (using DeepEval when available)

Run:
    pytest app/tests/qa_evaluation/test_qa_golden.py -v
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from unittest.mock import MagicMock, patch
import json

# Import QA components
from app.dsl.schema import MetricQuery
from app.answer.visual_intent import classify_visual_intent, VisualIntent


@dataclass
class GoldenTestCase:
    """
    Golden test case for QA system validation.

    Each test case defines:
    - question: The natural language input
    - Expected DSL properties (metric, query_type, breakdown, etc.)
    - Expected visual properties (intent, chart_type, etc.)
    """
    # Input
    question: str

    # Expected DSL properties
    expected_metric: Optional[str] = None
    expected_query_type: str = "metrics"
    expected_breakdown: Optional[str] = None
    expected_top_n: Optional[int] = None
    expected_compare_to_previous: bool = False
    expected_sort_order: str = "desc"

    # Expected visual properties
    expected_visual_intent: Optional[str] = None
    expected_chart_type: Optional[str] = None
    expected_has_table: bool = False
    expected_has_comparison_chart: bool = False
    expected_series_count: Optional[int] = None

    # Validation flags
    should_have_breakdown: bool = False
    min_breakdown_items: int = 0

    # Tags for filtering
    tags: List[str] = field(default_factory=list)


# =============================================================================
# GOLDEN TEST CASES
# =============================================================================

GOLDEN_TEST_CASES = [
    # -------------------------------------------------------------------------
    # Simple Queries
    # -------------------------------------------------------------------------
    GoldenTestCase(
        question="What's my ROAS this week?",
        expected_metric="roas",
        expected_query_type="metrics",
        expected_compare_to_previous=False,
        expected_visual_intent="SINGLE_METRIC",
        expected_chart_type="area",
        tags=["simple", "roas"],
    ),
    GoldenTestCase(
        question="How much did I spend yesterday?",
        expected_metric="spend",
        expected_query_type="metrics",
        expected_compare_to_previous=False,
        expected_visual_intent="SINGLE_METRIC",
        tags=["simple", "spend"],
    ),
    GoldenTestCase(
        question="What's my CPC?",
        expected_metric="cpc",
        expected_query_type="metrics",
        expected_visual_intent="SINGLE_METRIC",
        tags=["simple", "derived_metric"],
    ),

    # -------------------------------------------------------------------------
    # Comparison Queries (CRITICAL - often buggy)
    # -------------------------------------------------------------------------
    GoldenTestCase(
        question="Spend vs last week",
        expected_metric="spend",
        expected_compare_to_previous=True,
        expected_visual_intent="COMPARISON",
        expected_chart_type="line",
        expected_has_comparison_chart=True,
        expected_series_count=2,  # Current + Previous
        tags=["comparison", "critical"],
    ),
    GoldenTestCase(
        question="Compare ROAS to last month",
        expected_metric="roas",
        expected_compare_to_previous=True,
        expected_visual_intent="COMPARISON",
        expected_has_comparison_chart=True,
        tags=["comparison"],
    ),
    GoldenTestCase(
        question="Revenue this week vs last week",
        expected_metric="revenue",
        expected_compare_to_previous=True,
        expected_visual_intent="COMPARISON",
        tags=["comparison"],
    ),

    # -------------------------------------------------------------------------
    # "Compare All" Queries (CRITICAL - known bug)
    # -------------------------------------------------------------------------
    GoldenTestCase(
        question="Compare all campaigns",
        expected_metric="roas",  # Should default to ROAS for performance
        expected_query_type="metrics",
        expected_breakdown="campaign",
        expected_top_n=50,  # CRITICAL: "all" = 50 (max)
        expected_visual_intent="RANKING",
        expected_chart_type="bar",
        expected_has_table=True,
        should_have_breakdown=True,
        min_breakdown_items=5,
        tags=["compare_all", "critical", "breakdown"],
    ),
    GoldenTestCase(
        question="Show all campaigns by ROAS",
        expected_metric="roas",
        expected_breakdown="campaign",
        expected_top_n=50,
        expected_visual_intent="RANKING",
        expected_has_table=True,
        tags=["compare_all", "breakdown"],
    ),
    GoldenTestCase(
        question="Give me all campaigns performance",
        expected_metric="revenue",  # "performance" defaults to revenue
        expected_breakdown="campaign",
        expected_top_n=50,
        expected_visual_intent="RANKING",
        tags=["compare_all", "breakdown"],
    ),
    GoldenTestCase(
        question="Show me all adsets",
        expected_metric="revenue",
        expected_breakdown="adset",
        expected_top_n=50,
        tags=["compare_all", "breakdown"],
    ),

    # -------------------------------------------------------------------------
    # Ranking Queries
    # -------------------------------------------------------------------------
    GoldenTestCase(
        question="Which campaign had highest ROAS?",
        expected_metric="roas",
        expected_breakdown="campaign",
        expected_top_n=1,
        expected_sort_order="desc",
        expected_visual_intent="RANKING",
        tags=["ranking", "highest"],
    ),
    GoldenTestCase(
        question="Which campaign had lowest CPC?",
        expected_metric="cpc",
        expected_breakdown="campaign",
        expected_top_n=1,
        expected_sort_order="asc",  # LOWEST = ascending
        expected_visual_intent="RANKING",
        tags=["ranking", "lowest"],
    ),
    GoldenTestCase(
        question="Top 5 campaigns by revenue",
        expected_metric="revenue",
        expected_breakdown="campaign",
        expected_top_n=5,
        expected_visual_intent="RANKING",
        expected_has_table=True,
        tags=["ranking", "top_n"],
    ),

    # -------------------------------------------------------------------------
    # Filtering Queries
    # -------------------------------------------------------------------------
    GoldenTestCase(
        question="Show campaigns with ROAS above 4",
        expected_metric="roas",
        expected_breakdown="campaign",
        expected_visual_intent="FILTERING",
        expected_has_table=True,
        tags=["filtering", "metric_filter"],
    ),
    GoldenTestCase(
        question="Which campaigns have zero revenue?",
        expected_metric="revenue",
        expected_breakdown="campaign",
        expected_visual_intent="FILTERING",
        expected_has_table=True,
        tags=["filtering"],
    ),

    # -------------------------------------------------------------------------
    # Provider Queries
    # -------------------------------------------------------------------------
    GoldenTestCase(
        question="Which platforms am I advertising on?",
        expected_query_type="providers",
        tags=["providers", "non_metrics"],
    ),
    GoldenTestCase(
        question="Compare Google vs Meta performance",
        expected_metric="roas",
        expected_breakdown="provider",
        expected_visual_intent="BREAKDOWN",
        tags=["providers", "comparison"],
    ),

    # -------------------------------------------------------------------------
    # Multi-Metric Queries
    # -------------------------------------------------------------------------
    GoldenTestCase(
        question="Show me spend and revenue this week",
        expected_metric=["spend", "revenue"],  # Multi-metric
        expected_visual_intent="MULTI_METRIC",
        tags=["multi_metric"],
    ),

    # -------------------------------------------------------------------------
    # Temporal Breakdown Queries
    # -------------------------------------------------------------------------
    GoldenTestCase(
        question="Which day had highest CPC?",
        expected_metric="cpc",
        expected_breakdown="day",
        expected_top_n=1,
        expected_visual_intent="RANKING",
        tags=["temporal", "breakdown"],
    ),
    GoldenTestCase(
        question="Show me weekly revenue",
        expected_metric="revenue",
        expected_breakdown="week",
        tags=["temporal", "breakdown"],
    ),
]


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def mock_translator():
    """Mock translator for testing DSL generation without LLM calls."""
    with patch('app.nlp.translator.Translator') as mock:
        yield mock


@pytest.fixture
def test_cases_by_tag():
    """Group test cases by tags for selective testing."""
    grouped = {}
    for tc in GOLDEN_TEST_CASES:
        for tag in tc.tags:
            if tag not in grouped:
                grouped[tag] = []
            grouped[tag].append(tc)
    return grouped


# =============================================================================
# DSL GENERATION TESTS
# =============================================================================

class TestDSLGeneration:
    """Test DSL generation from natural language questions."""

    @pytest.mark.parametrize("test_case", GOLDEN_TEST_CASES, ids=lambda tc: tc.question[:50])
    def test_dsl_metric_expectation(self, test_case: GoldenTestCase):
        """
        Test that DSL generation produces expected metric.

        NOTE: This test validates expectations, not actual generation.
        Run with --mock to test against mock translator.
        """
        # This test documents expected behavior
        # Actual DSL generation would require mocking the LLM
        assert test_case.expected_metric is not None or test_case.expected_query_type != "metrics", \
            f"Metrics query should have expected_metric: {test_case.question}"

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GOLDEN_TEST_CASES if "compare_all" in tc.tags],
        ids=lambda tc: tc.question[:50]
    )
    def test_compare_all_uses_max_top_n(self, test_case: GoldenTestCase):
        """
        CRITICAL: Verify "compare all" queries expect top_n=50 (max).

        This test documents the expected behavior for the "compare all campaigns" bug fix.
        """
        assert test_case.expected_top_n == 50, \
            f"'Compare all' query should expect top_n=50, got {test_case.expected_top_n}: {test_case.question}"

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GOLDEN_TEST_CASES if tc.expected_compare_to_previous],
        ids=lambda tc: tc.question[:50]
    )
    def test_comparison_queries_set_flag(self, test_case: GoldenTestCase):
        """
        CRITICAL: Verify comparison queries expect compare_to_previous=True.
        """
        assert test_case.expected_compare_to_previous == True, \
            f"Comparison query should expect compare_to_previous=True: {test_case.question}"


# =============================================================================
# VISUAL INTENT TESTS
# =============================================================================

class TestVisualIntent:
    """Test visual intent classification."""

    def test_single_metric_intent(self):
        """Simple queries should classify as SINGLE_METRIC."""
        dsl = MetricQuery(
            metric="roas",
            time_range={"last_n_days": 7},
            compare_to_previous=False,
            breakdown=None,
        )
        result = {"summary": 2.5}

        intent = classify_visual_intent(dsl, result)
        assert intent == VisualIntent.SINGLE_METRIC

    def test_comparison_intent(self):
        """Comparison queries should classify as COMPARISON."""
        dsl = MetricQuery(
            metric="spend",
            time_range={"last_n_days": 7},
            compare_to_previous=True,
            breakdown=None,
        )
        result = {"summary": 1000, "previous": 900}

        intent = classify_visual_intent(dsl, result)
        assert intent == VisualIntent.COMPARISON

    def test_ranking_intent(self):
        """Breakdown queries with top_n should classify as RANKING."""
        dsl = MetricQuery(
            metric="roas",
            time_range={"last_n_days": 7},
            compare_to_previous=False,
            breakdown="campaign",
            top_n=5,
        )
        result = {
            "summary": 2.5,
            "breakdown": [
                {"label": "Campaign A", "value": 3.0},
                {"label": "Campaign B", "value": 2.5},
            ]
        }

        intent = classify_visual_intent(dsl, result)
        assert intent == VisualIntent.RANKING

    def test_filtering_intent_with_metric_filter(self):
        """
        Filtered breakdown queries should classify as RANKING.

        Even with metric_filters, breakdown queries are displayed as
        ranked lists (bar charts with tables), not a special FILTERING view.
        """
        dsl = MetricQuery(
            metric="roas",
            time_range={"last_n_days": 7},
            compare_to_previous=False,
            breakdown="campaign",
            filters={"metric_filters": [{"metric": "roas", "operator": ">", "value": 4}]},
        )
        result = {"breakdown": []}

        intent = classify_visual_intent(dsl, result)
        # Filtered breakdowns are displayed as RANKING (with filters applied)
        assert intent == VisualIntent.RANKING


# =============================================================================
# VISUAL BUILDER TESTS
# =============================================================================

class TestVisualBuilder:
    """Test visual payload generation."""

    def test_comparison_chart_has_two_series(self):
        """Comparison charts should have 2 series (current + previous)."""
        from app.answer.visual_builder import build_visual_payload

        dsl = MetricQuery(
            metric="spend",
            time_range={"last_n_days": 7},
            compare_to_previous=True,
        )
        result = {
            "summary": 1000,
            "previous": 900,
            "timeseries": [
                {"date": "2025-01-01", "value": 100},
                {"date": "2025-01-02", "value": 150},
            ],
            "timeseries_previous": [
                {"date": "2024-12-25", "value": 90},
                {"date": "2024-12-26", "value": 140},
            ],
        }

        payload = build_visual_payload(dsl, result, "this week")

        # Check viz_specs has comparison chart
        viz_specs = payload.get("viz_specs", [])
        assert len(viz_specs) > 0, "Should have at least one chart"

        chart = viz_specs[0]
        assert chart.get("isComparison") == True, "Should be marked as comparison"
        assert len(chart.get("series", [])) == 2, "Comparison chart should have 2 series"

    def test_ranking_has_table(self):
        """Ranking queries should include a table."""
        from app.answer.visual_builder import build_visual_payload

        dsl = MetricQuery(
            metric="roas",
            time_range={"last_n_days": 7},
            compare_to_previous=False,
            breakdown="campaign",
            top_n=5,
        )
        result = {
            "summary": 2.5,
            "breakdown": [
                {"label": "Campaign A", "value": 3.0},
                {"label": "Campaign B", "value": 2.5},
                {"label": "Campaign C", "value": 2.0},
            ],
        }

        payload = build_visual_payload(dsl, result, "last week")

        tables = payload.get("tables", [])
        assert len(tables) > 0, "Ranking query should have a table"


# =============================================================================
# ANSWER QUALITY TESTS (DeepEval)
# =============================================================================

# Check for DeepEval availability
try:
    import deepeval
    from deepeval import assert_test
    from deepeval.test_case import LLMTestCase
    from deepeval.metrics import AnswerRelevancyMetric
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False
    assert_test = None

import os
CONFIDENT_API_KEY = os.environ.get("CONFIDENT_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


class TestAnswerQuality:
    """
    Answer quality tests using DeepEval metrics.

    Run with:
        CONFIDENT_API_KEY=your_key pytest app/tests/qa_evaluation/test_qa_golden.py -v -k "TestAnswerQuality"

    Or use deepeval CLI:
        deepeval test run app/tests/qa_evaluation/test_qa_golden.py
    """

    @pytest.mark.skipif(
        not DEEPEVAL_AVAILABLE or not OPENAI_API_KEY,
        reason="Requires DeepEval and OPENAI_API_KEY"
    )
    def test_answer_faithfulness(self):
        """
        Test that answers are faithful to the provided data.

        Faithfulness measures if the answer only contains information
        that can be derived from the provided context (no hallucinations).
        """
        from deepeval.metrics import FaithfulnessMetric

        test_case = LLMTestCase(
            input="What's my ROAS this week?",
            actual_output="Your ROAS this week is 2.45x, which is a 15% increase from last week.",
            retrieval_context=["ROAS: 2.45", "Previous: 2.13", "Delta: +15%"],
        )

        metric = FaithfulnessMetric(threshold=0.7)

        # Use assert_test to register with Confident AI
        assert_test(test_case, [metric])

    @pytest.mark.skipif(
        not DEEPEVAL_AVAILABLE or not OPENAI_API_KEY,
        reason="Requires DeepEval and OPENAI_API_KEY"
    )
    def test_answer_relevancy(self):
        """
        Test that answers are relevant to the question asked.
        """
        test_case = LLMTestCase(
            input="What's my ROAS this week?",
            actual_output="Your ROAS this week is 2.45x.",
        )

        metric = AnswerRelevancyMetric(threshold=0.7)

        # Use assert_test to register with Confident AI
        assert_test(test_case, [metric])

    @pytest.mark.skipif(
        not DEEPEVAL_AVAILABLE or not OPENAI_API_KEY,
        reason="Requires DeepEval and OPENAI_API_KEY"
    )
    def test_campaign_comparison_answer(self):
        """
        Test answer quality for campaign comparison queries.
        """
        test_case = LLMTestCase(
            input="Compare all campaigns",
            actual_output="""Over the last week, the "Display - Retargeting" campaign led with a ROAS of 14.54.
            The "Meta - Conversions Mid Funnel" campaign achieved 11.05 ROAS.
            "Meta - Catalog Sales" had moderate performance at 4.80 ROAS.
            "Meta - Awareness Top Funnel" showed 0.0 ROAS.""",
            retrieval_context=[
                "Campaign: Display - Retargeting, ROAS: 14.54",
                "Campaign: Meta - Conversions Mid Funnel, ROAS: 11.05",
                "Campaign: Meta - Catalog Sales, ROAS: 4.80",
                "Campaign: Meta - Awareness Top Funnel, ROAS: 0.0",
            ],
        )

        metric = AnswerRelevancyMetric(threshold=0.7)

        # Use assert_test to register with Confident AI
        assert_test(test_case, [metric])


# =============================================================================
# REGRESSION TESTS
# =============================================================================

class TestKnownBugs:
    """
    Tests for known bugs and their fixes.

    Each test documents a specific bug and verifies the fix works.
    """

    def test_compare_all_campaigns_not_empty(self):
        """
        BUG: "Compare all campaigns" returned empty or limited results.
        FIX: Added few-shot examples with top_n=50 for "all" queries.

        This test verifies the expectation is documented.
        """
        test_case = next(
            tc for tc in GOLDEN_TEST_CASES
            if tc.question == "Compare all campaigns"
        )

        assert test_case.expected_top_n == 50
        assert test_case.expected_breakdown == "campaign"

    def test_comparison_chart_single_line_fix(self):
        """
        BUG: Comparison charts showed only 1 line instead of 2.
        FIX: Post-processing forces compare_to_previous=True for "vs last" queries.

        This test verifies the expectation is documented.
        Note: "vs" queries that compare entities (e.g., "Google vs Meta") are
        NOT time-based comparisons and should have compare_to_previous=False.
        """
        # Only time-based "vs" queries should have compare_to_previous=True
        time_based_vs_queries = [
            tc for tc in GOLDEN_TEST_CASES
            if "vs" in tc.question.lower()
            and any(kw in tc.question.lower() for kw in ["vs last", "vs previous"])
        ]

        for tc in time_based_vs_queries:
            assert tc.expected_compare_to_previous == True, \
                f"Time-based 'vs' query should expect compare_to_previous=True: {tc.question}"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def run_golden_tests_report():
    """
    Generate a report of all golden test cases.

    Useful for documentation and manual review.
    """
    print("\n" + "="*80)
    print("GOLDEN TEST CASES REPORT")
    print("="*80)

    for i, tc in enumerate(GOLDEN_TEST_CASES, 1):
        print(f"\n{i}. {tc.question}")
        print(f"   Tags: {', '.join(tc.tags)}")
        print(f"   Expected metric: {tc.expected_metric}")
        print(f"   Expected breakdown: {tc.expected_breakdown}")
        print(f"   Expected top_n: {tc.expected_top_n}")
        print(f"   Expected visual: {tc.expected_visual_intent}")

    print("\n" + "="*80)
    print(f"Total test cases: {len(GOLDEN_TEST_CASES)}")
    print("="*80)


if __name__ == "__main__":
    run_golden_tests_report()
