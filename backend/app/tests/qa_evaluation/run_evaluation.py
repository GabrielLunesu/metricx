#!/usr/bin/env python3
"""
QA Evaluation Runner
=====================

Run comprehensive QA evaluation tests and generate reports.
Integrates with Confident AI for tracking and monitoring.

Usage:
    python -m app.tests.qa_evaluation.run_evaluation [options]

Options:
    --report PATH      Generate JSON report to file
    --live             Run against live QA service (requires auth)
    --quick            Run only critical tests
    --confident        Track results to Confident AI
    --setup            Show DeepEval/Confident AI setup instructions

Environment Variables:
    CONFIDENT_API_KEY  API key for Confident AI dashboard
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

# Import test cases
from app.tests.qa_evaluation.test_qa_golden import GOLDEN_TEST_CASES, GoldenTestCase

# Import DeepEval config
from app.tests.qa_evaluation.deepeval_config import (
    DEEPEVAL_AVAILABLE,
    configure_confident_ai,
    evaluate_dsl_correctness,
    evaluate_visual_correctness,
    setup_deepeval_cli,
)


@dataclass
class EvaluationResult:
    """Result of a single test case evaluation."""
    question: str
    passed: bool
    dsl_correct: bool
    visual_correct: bool
    answer_quality: float
    latency_ms: int
    error: str = ""
    details: Dict[str, Any] = None


def evaluate_test_case(
    test_case: GoldenTestCase,
    qa_service=None,
    workspace_id: str = None,
) -> EvaluationResult:
    """
    Evaluate a single test case against the QA system.

    Args:
        test_case: Golden test case to evaluate
        qa_service: QA service instance (optional, for live testing)
        workspace_id: Workspace ID for scoping

    Returns:
        EvaluationResult with pass/fail status and details
    """
    import time

    result = EvaluationResult(
        question=test_case.question,
        passed=False,
        dsl_correct=False,
        visual_correct=False,
        answer_quality=0.0,
        latency_ms=0,
        details={},
    )

    if qa_service is None:
        # Dry run - just validate expectations
        result.passed = True
        result.dsl_correct = True
        result.details = {
            "mode": "dry_run",
            "expected_metric": test_case.expected_metric,
            "expected_breakdown": test_case.expected_breakdown,
            "expected_top_n": test_case.expected_top_n,
        }
        return result

    # Live evaluation
    try:
        start = time.time()
        response = qa_service.answer(
            question=test_case.question,
            workspace_id=workspace_id,
            user_id="evaluation-user",
        )
        result.latency_ms = int((time.time() - start) * 1000)

        # Validate DSL
        executed_dsl = response.get("executed_dsl", {})
        if test_case.expected_metric:
            actual_metric = executed_dsl.get("metric")
            if isinstance(test_case.expected_metric, list):
                result.dsl_correct = actual_metric == test_case.expected_metric
            else:
                result.dsl_correct = actual_metric == test_case.expected_metric

        if test_case.expected_breakdown:
            result.dsl_correct = result.dsl_correct and \
                executed_dsl.get("breakdown") == test_case.expected_breakdown

        if test_case.expected_top_n:
            result.dsl_correct = result.dsl_correct and \
                executed_dsl.get("top_n") == test_case.expected_top_n

        # Validate visuals
        visuals = response.get("visuals", {})
        viz_specs = visuals.get("viz_specs", [])
        tables = visuals.get("tables", [])

        if test_case.expected_has_table:
            result.visual_correct = len(tables) > 0
        elif test_case.expected_has_comparison_chart:
            result.visual_correct = any(
                spec.get("isComparison") for spec in viz_specs
            )
        else:
            result.visual_correct = True  # No specific expectation

        # Overall pass
        result.passed = result.dsl_correct and result.visual_correct

        result.details = {
            "executed_dsl": executed_dsl,
            "answer": response.get("answer", ""),
            "viz_specs_count": len(viz_specs),
            "tables_count": len(tables),
        }

    except Exception as e:
        result.error = str(e)
        result.details = {"error": str(e)}

    return result


def run_evaluation(
    test_cases: List[GoldenTestCase] = None,
    live: bool = False,
    quick: bool = False,
) -> List[EvaluationResult]:
    """
    Run evaluation on all or selected test cases.

    Args:
        test_cases: Test cases to run (default: all)
        live: Run against live QA service
        quick: Run only critical tests

    Returns:
        List of evaluation results
    """
    if test_cases is None:
        test_cases = GOLDEN_TEST_CASES

    if quick:
        test_cases = [tc for tc in test_cases if "critical" in tc.tags]

    qa_service = None
    workspace_id = None

    if live:
        # Initialize live QA service
        from app.services.qa_service import QAService
        from app.database import SessionLocal

        db = SessionLocal()
        qa_service = QAService(db)
        workspace_id = "YOUR_WORKSPACE_ID"  # TODO: Get from env

    results = []
    for tc in test_cases:
        result = evaluate_test_case(tc, qa_service, workspace_id)
        results.append(result)
        status = "" if result.passed else ""
        print(f"{status} {tc.question[:60]}")

    return results


def generate_report(results: List[EvaluationResult], output_path: str = None):
    """Generate evaluation report."""
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    pass_rate = passed / total * 100 if total > 0 else 0

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{pass_rate:.1f}%",
        },
        "results": [asdict(r) for r in results],
    }

    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Pass rate: {pass_rate:.1f}%")
    print("="*60)

    if output_path:
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="QA Evaluation Runner")
    parser.add_argument("--report", help="Output report path", default=None)
    parser.add_argument("--live", action="store_true", help="Run against live QA service")
    parser.add_argument("--quick", action="store_true", help="Run only critical tests")
    parser.add_argument("--confident", action="store_true", help="Track results to Confident AI")
    parser.add_argument("--setup", action="store_true", help="Show setup instructions")
    args = parser.parse_args()

    # Show setup instructions
    if args.setup:
        setup_deepeval_cli()
        return

    print("QA Evaluation Runner")
    print("="*60)

    # Configure Confident AI if requested
    if args.confident:
        api_key = os.environ.get("CONFIDENT_API_KEY")
        if not api_key:
            print("\n[!] CONFIDENT_API_KEY not set")
            print("    Set it with: export CONFIDENT_API_KEY=your_key")
            print("    Or run: python -m app.tests.qa_evaluation.run_evaluation --setup")
            return
        if not DEEPEVAL_AVAILABLE:
            print("\n[!] DeepEval not installed")
            print("    Install with: pip install deepeval")
            return
        if configure_confident_ai(api_key):
            print("[OK] Confident AI configured - results will be tracked")

    results = run_evaluation(live=args.live, quick=args.quick)
    report = generate_report(results, args.report)

    # Track to Confident AI if DeepEval available and configured
    if args.confident and DEEPEVAL_AVAILABLE:
        try:
            from deepeval import evaluate as deepeval_evaluate
            from deepeval.test_case import LLMTestCase

            # Convert results to DeepEval test cases for tracking
            test_cases = []
            for r in results:
                if r.details.get("answer"):
                    tc = LLMTestCase(
                        input=r.question,
                        actual_output=r.details.get("answer", ""),
                        context=[str(r.details.get("executed_dsl", {}))],
                    )
                    test_cases.append(tc)

            if test_cases:
                print(f"\n[...] Tracking {len(test_cases)} results to Confident AI...")
                # Note: evaluate() automatically tracks to Confident AI when logged in
                deepeval_evaluate(test_cases)
                print("[OK] Results tracked to Confident AI dashboard")
        except Exception as e:
            print(f"\n[!] Failed to track to Confident AI: {e}")


if __name__ == "__main__":
    main()
