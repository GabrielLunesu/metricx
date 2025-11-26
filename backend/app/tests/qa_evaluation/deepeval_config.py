"""
DeepEval Configuration for Confident AI
=========================================

Configure DeepEval metrics and Confident AI integration for QA evaluation.

Setup:
    1. Install DeepEval: pip install deepeval
    2. Set CONFIDENT_API_KEY environment variable
    3. Run: deepeval login --confident-api-key YOUR_KEY

Usage:
    from app.tests.qa_evaluation.deepeval_config import (
        evaluate_answer_quality,
        create_test_case,
        run_evaluation_suite
    )
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Check for DeepEval availability
DEEPEVAL_AVAILABLE = False
try:
    import deepeval
    from deepeval import evaluate
    from deepeval.metrics import (
        FaithfulnessMetric,
        AnswerRelevancyMetric,
        ContextualRelevancyMetric,
    )
    from deepeval.test_case import LLMTestCase
    DEEPEVAL_AVAILABLE = True
except ImportError:
    logger.warning("DeepEval not installed. Run: pip install deepeval")


# =============================================================================
# CONFIDENT AI CONFIGURATION
# =============================================================================

def configure_confident_ai(api_key: str = None) -> bool:
    """
    Configure DeepEval to use Confident AI for tracking.

    Args:
        api_key: Confident AI API key. If not provided, reads from
                 CONFIDENT_API_KEY environment variable.

    Returns:
        True if configured successfully, False otherwise.
    """
    if not DEEPEVAL_AVAILABLE:
        logger.error("DeepEval not installed. Cannot configure Confident AI.")
        return False

    api_key = api_key or os.environ.get("CONFIDENT_API_KEY")
    if not api_key:
        logger.error("CONFIDENT_API_KEY not set. Please set the environment variable.")
        return False

    try:
        # Configure DeepEval with Confident AI using the correct API
        from deepeval.confident.api import set_confident_api_key, is_confident
        set_confident_api_key(api_key)

        if is_confident():
            logger.info("Confident AI configured successfully")
            return True
        else:
            logger.error("Confident AI configuration failed - not detected as active")
            return False
    except Exception as e:
        logger.error(f"Failed to configure Confident AI: {e}")
        return False


# =============================================================================
# QA-SPECIFIC METRICS
# =============================================================================

@dataclass
class QAMetricThresholds:
    """Default thresholds for QA evaluation metrics."""
    faithfulness: float = 0.8
    answer_relevancy: float = 0.8
    contextual_relevancy: float = 0.7
    dsl_accuracy: float = 0.9
    visual_accuracy: float = 0.9


DEFAULT_THRESHOLDS = QAMetricThresholds()


def create_test_case(
    question: str,
    answer: str,
    context: List[str],
    expected_output: str = None,
    retrieval_context: List[str] = None,
) -> Optional["LLMTestCase"]:
    """
    Create a DeepEval test case for QA evaluation.

    Args:
        question: User's question
        answer: Generated answer from QA system
        context: Context/data used to generate the answer
        expected_output: Optional expected output for comparison
        retrieval_context: Optional retrieval context for RAG metrics

    Returns:
        LLMTestCase instance or None if DeepEval not available
    """
    if not DEEPEVAL_AVAILABLE:
        return None

    return LLMTestCase(
        input=question,
        actual_output=answer,
        context=context,
        expected_output=expected_output,
        retrieval_context=retrieval_context or context,
    )


def evaluate_answer_quality(
    test_case: "LLMTestCase",
    thresholds: QAMetricThresholds = None,
) -> Dict[str, Any]:
    """
    Evaluate answer quality using multiple metrics.

    Args:
        test_case: LLMTestCase to evaluate
        thresholds: Custom thresholds (optional)

    Returns:
        Dictionary with metric scores and pass/fail status
    """
    if not DEEPEVAL_AVAILABLE:
        return {"error": "DeepEval not available", "passed": False}

    thresholds = thresholds or DEFAULT_THRESHOLDS

    results = {
        "passed": True,
        "metrics": {},
        "details": {},
    }

    # Faithfulness: Does the answer stick to the facts?
    try:
        faithfulness = FaithfulnessMetric(threshold=thresholds.faithfulness)
        faithfulness.measure(test_case)
        results["metrics"]["faithfulness"] = faithfulness.score
        results["details"]["faithfulness"] = faithfulness.reason
        if faithfulness.score < thresholds.faithfulness:
            results["passed"] = False
    except Exception as e:
        results["metrics"]["faithfulness"] = None
        results["details"]["faithfulness"] = f"Error: {str(e)}"

    # Answer Relevancy: Is the answer relevant to the question?
    try:
        relevancy = AnswerRelevancyMetric(threshold=thresholds.answer_relevancy)
        relevancy.measure(test_case)
        results["metrics"]["answer_relevancy"] = relevancy.score
        results["details"]["answer_relevancy"] = relevancy.reason
        if relevancy.score < thresholds.answer_relevancy:
            results["passed"] = False
    except Exception as e:
        results["metrics"]["answer_relevancy"] = None
        results["details"]["answer_relevancy"] = f"Error: {str(e)}"

    return results


# =============================================================================
# QA-SPECIFIC EVALUATION
# =============================================================================

def evaluate_dsl_correctness(
    actual_dsl: Dict[str, Any],
    expected: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate DSL generation correctness.

    Args:
        actual_dsl: Generated DSL from translator
        expected: Expected DSL properties

    Returns:
        Dictionary with correctness scores per field
    """
    results = {
        "passed": True,
        "field_scores": {},
        "overall_score": 0.0,
    }

    fields_to_check = [
        "metric",
        "breakdown",
        "top_n",
        "compare_to_previous",
        "sort_order",
        "query_type",
    ]

    correct = 0
    total = 0

    for field in fields_to_check:
        if field in expected and expected[field] is not None:
            total += 1
            actual_value = actual_dsl.get(field)
            expected_value = expected[field]

            # Handle list comparison
            if isinstance(expected_value, list) and isinstance(actual_value, list):
                match = set(expected_value) == set(actual_value)
            else:
                match = actual_value == expected_value

            results["field_scores"][field] = {
                "expected": expected_value,
                "actual": actual_value,
                "match": match,
            }

            if match:
                correct += 1
            else:
                results["passed"] = False

    results["overall_score"] = correct / total if total > 0 else 1.0
    return results


def evaluate_visual_correctness(
    payload: Dict[str, Any],
    expected: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate visual payload correctness.

    Args:
        payload: Generated visual payload
        expected: Expected visual properties

    Returns:
        Dictionary with correctness assessment
    """
    results = {
        "passed": True,
        "checks": {},
    }

    # Check chart type
    viz_specs = payload.get("viz_specs", [])
    if expected.get("expected_chart_type"):
        actual_types = [v.get("type") for v in viz_specs]
        expected_type = expected["expected_chart_type"]
        results["checks"]["chart_type"] = {
            "expected": expected_type,
            "actual": actual_types,
            "match": expected_type in actual_types,
        }
        if expected_type not in actual_types:
            results["passed"] = False

    # Check has table
    tables = payload.get("tables", [])
    if expected.get("expected_has_table"):
        results["checks"]["has_table"] = {
            "expected": True,
            "actual": len(tables) > 0,
            "match": len(tables) > 0,
        }
        if len(tables) == 0:
            results["passed"] = False

    # Check series count for comparison charts
    if expected.get("expected_series_count") and viz_specs:
        chart = viz_specs[0]
        actual_series = len(chart.get("series", []))
        expected_series = expected["expected_series_count"]
        results["checks"]["series_count"] = {
            "expected": expected_series,
            "actual": actual_series,
            "match": actual_series == expected_series,
        }
        if actual_series != expected_series:
            results["passed"] = False

    # Check is comparison flag
    if expected.get("expected_has_comparison_chart") and viz_specs:
        chart = viz_specs[0]
        is_comparison = chart.get("isComparison", False)
        results["checks"]["is_comparison"] = {
            "expected": True,
            "actual": is_comparison,
            "match": is_comparison,
        }
        if not is_comparison:
            results["passed"] = False

    return results


# =============================================================================
# EVALUATION SUITE RUNNER
# =============================================================================

def run_evaluation_suite(
    test_cases: List[Dict[str, Any]],
    qa_service=None,
    workspace_id: str = None,
    track_to_confident: bool = True,
) -> Dict[str, Any]:
    """
    Run full evaluation suite on test cases.

    Args:
        test_cases: List of test case dictionaries
        qa_service: QA service instance for live testing
        workspace_id: Workspace ID for scoping
        track_to_confident: Whether to track results to Confident AI

    Returns:
        Comprehensive evaluation report
    """
    report = {
        "total": len(test_cases),
        "passed": 0,
        "failed": 0,
        "results": [],
        "summary": {},
    }

    for tc in test_cases:
        result = {
            "question": tc.get("question"),
            "passed": True,
            "dsl_result": None,
            "visual_result": None,
            "answer_result": None,
        }

        if qa_service:
            # Live evaluation against QA service
            try:
                response = qa_service.answer(
                    question=tc["question"],
                    workspace_id=workspace_id,
                    user_id="evaluation-user",
                )

                # Evaluate DSL
                if "expected_metric" in tc:
                    result["dsl_result"] = evaluate_dsl_correctness(
                        response.get("executed_dsl", {}),
                        {
                            "metric": tc.get("expected_metric"),
                            "breakdown": tc.get("expected_breakdown"),
                            "top_n": tc.get("expected_top_n"),
                            "compare_to_previous": tc.get("expected_compare_to_previous"),
                        }
                    )
                    if not result["dsl_result"]["passed"]:
                        result["passed"] = False

                # Evaluate visuals
                if "expected_chart_type" in tc or "expected_has_table" in tc:
                    result["visual_result"] = evaluate_visual_correctness(
                        response.get("visuals", {}),
                        tc
                    )
                    if not result["visual_result"]["passed"]:
                        result["passed"] = False

                # Evaluate answer quality with DeepEval
                if DEEPEVAL_AVAILABLE and response.get("answer"):
                    test_case = create_test_case(
                        question=tc["question"],
                        answer=response["answer"],
                        context=[str(response.get("executed_dsl", {}))],
                    )
                    if test_case:
                        result["answer_result"] = evaluate_answer_quality(test_case)
                        if not result["answer_result"]["passed"]:
                            result["passed"] = False

            except Exception as e:
                result["passed"] = False
                result["error"] = str(e)

        report["results"].append(result)
        if result["passed"]:
            report["passed"] += 1
        else:
            report["failed"] += 1

    # Calculate summary
    report["summary"] = {
        "pass_rate": report["passed"] / report["total"] * 100 if report["total"] > 0 else 0,
        "dsl_accuracy": _calculate_category_accuracy(report["results"], "dsl_result"),
        "visual_accuracy": _calculate_category_accuracy(report["results"], "visual_result"),
        "answer_quality": _calculate_category_accuracy(report["results"], "answer_result"),
    }

    return report


def _calculate_category_accuracy(results: List[Dict], category: str) -> float:
    """Calculate accuracy for a specific evaluation category."""
    valid_results = [r for r in results if r.get(category) is not None]
    if not valid_results:
        return None
    passed = sum(1 for r in valid_results if r[category].get("passed", False))
    return passed / len(valid_results) * 100


# =============================================================================
# CLI HELPER
# =============================================================================

def setup_deepeval_cli():
    """Print CLI setup instructions for DeepEval + Confident AI."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     DeepEval + Confident AI Setup                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

1. Install DeepEval:
   pip install deepeval

2. Login to Confident AI:
   deepeval login --confident-api-key YOUR_API_KEY

3. Set environment variable (alternative to CLI login):
   export CONFIDENT_API_KEY=your_api_key

4. Run evaluation:
   python -m app.tests.qa_evaluation.run_evaluation --live

5. View results:
   Visit https://app.confident-ai.com to see evaluation dashboard

For more info: https://docs.confident-ai.com/docs/getting-started-introduction
""")


if __name__ == "__main__":
    setup_deepeval_cli()
