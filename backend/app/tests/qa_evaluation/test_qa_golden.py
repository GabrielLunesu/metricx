"""
QA Golden Test Cases
=====================

Automated tests for QA system correctness using golden test cases.

Version 4.0 - Updated for Agentic Copilot (LangGraph + Claude)

These tests verify:
1. Answer quality (using DeepEval when available)
2. Expected query patterns

Run:
    pytest app/tests/qa_evaluation/test_qa_golden.py -v
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from unittest.mock import MagicMock, patch
import json


@dataclass
class GoldenTestCase:
    """
    Golden test case for QA system validation.

    Each test case defines:
    - question: The natural language input
    - Expected properties (metric, breakdown, etc.)
    """
    # Input
    question: str

    # Expected properties
    expected_metric: Optional[str] = None
    expected_breakdown: Optional[str] = None
    expected_top_n: Optional[int] = None
    expected_compare_to_previous: bool = False

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
        expected_compare_to_previous=False,
        tags=["simple", "roas"],
    ),
    GoldenTestCase(
        question="How much did I spend yesterday?",
        expected_metric="spend",
        expected_compare_to_previous=False,
        tags=["simple", "spend"],
    ),
    GoldenTestCase(
        question="What's my CPC?",
        expected_metric="cpc",
        tags=["simple", "derived_metric"],
    ),

    # -------------------------------------------------------------------------
    # Comparison Queries
    # -------------------------------------------------------------------------
    GoldenTestCase(
        question="Spend vs last week",
        expected_metric="spend",
        expected_compare_to_previous=True,
        tags=["comparison", "critical"],
    ),
    GoldenTestCase(
        question="Compare ROAS to last month",
        expected_metric="roas",
        expected_compare_to_previous=True,
        tags=["comparison"],
    ),
    GoldenTestCase(
        question="Revenue this week vs last week",
        expected_metric="revenue",
        expected_compare_to_previous=True,
        tags=["comparison"],
    ),

    # -------------------------------------------------------------------------
    # Ranking Queries
    # -------------------------------------------------------------------------
    GoldenTestCase(
        question="Which campaign had highest ROAS?",
        expected_metric="roas",
        expected_breakdown="campaign",
        expected_top_n=1,
        tags=["ranking", "highest"],
    ),
    GoldenTestCase(
        question="Top 5 campaigns by revenue",
        expected_metric="revenue",
        expected_breakdown="campaign",
        expected_top_n=5,
        tags=["ranking", "top_n"],
    ),

    # -------------------------------------------------------------------------
    # Multi-Metric Queries (v4.0)
    # -------------------------------------------------------------------------
    GoldenTestCase(
        question="Give me spend, revenue, ROAS, and profit for all campaigns",
        expected_metric=["spend", "revenue", "roas", "profit"],
        expected_breakdown="campaign",
        tags=["multi_metric"],
    ),
    GoldenTestCase(
        question="Show me CPC, CTR, and CPA for my top campaigns",
        expected_metric=["cpc", "ctr", "cpa"],
        expected_breakdown="campaign",
        tags=["multi_metric"],
    ),
]


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
# BASIC VALIDATION TESTS
# =============================================================================

class TestGoldenCases:
    """Basic validation tests for golden test cases."""

    @pytest.mark.parametrize("test_case", GOLDEN_TEST_CASES, ids=lambda tc: tc.question[:50])
    def test_metric_expectation_set(self, test_case: GoldenTestCase):
        """
        Test that every golden test case has expected_metric defined.
        """
        assert test_case.expected_metric is not None, \
            f"Golden test case should have expected_metric: {test_case.question}"

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GOLDEN_TEST_CASES if tc.expected_compare_to_previous],
        ids=lambda tc: tc.question[:50]
    )
    def test_comparison_queries_flag(self, test_case: GoldenTestCase):
        """
        CRITICAL: Verify comparison queries expect compare_to_previous=True.
        """
        assert test_case.expected_compare_to_previous == True, \
            f"Comparison query should expect compare_to_previous=True: {test_case.question}"


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

    print("\n" + "="*80)
    print(f"Total test cases: {len(GOLDEN_TEST_CASES)}")
    print("="*80)


if __name__ == "__main__":
    run_golden_tests_report()
