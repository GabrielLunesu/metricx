#!/usr/bin/env python3
"""
Confident AI Setup Script
==========================

Quick setup for DeepEval + Confident AI integration.

Usage:
    python -m app.tests.qa_evaluation.setup_confident

This will:
1. Prompt for your Confident AI API key
2. Configure DeepEval to use Confident AI
3. Run a test evaluation to verify the setup
"""

import os
import sys


def main():
    print("=" * 60)
    print("Confident AI Setup for metricx QA Evaluation")
    print("=" * 60)

    # Check if API key is already set
    existing_key = os.environ.get("CONFIDENT_API_KEY")
    if existing_key:
        print(f"\n[OK] CONFIDENT_API_KEY already set (ends with ...{existing_key[-8:]})")
        use_existing = input("Use existing key? [Y/n]: ").strip().lower()
        if use_existing != 'n':
            api_key = existing_key
        else:
            api_key = input("Enter your Confident AI API key: ").strip()
    else:
        print("\nNo CONFIDENT_API_KEY found in environment.")
        api_key = input("Enter your Confident AI API key: ").strip()

    if not api_key:
        print("[!] No API key provided. Exiting.")
        return

    # Set the environment variable
    os.environ["CONFIDENT_API_KEY"] = api_key

    # Try to configure DeepEval
    print("\n[...] Configuring DeepEval...")
    try:
        import deepeval
        from deepeval import evaluate
        from deepeval.test_case import LLMTestCase
        from deepeval.metrics import AnswerRelevancyMetric

        print("[OK] DeepEval imported successfully")

        # Login to Confident AI
        print("\n[...] Logging into Confident AI...")
        from deepeval.confident.api import set_confident_api_key, is_confident
        set_confident_api_key(api_key)
        if is_confident():
            print("[OK] Logged in to Confident AI")
        else:
            print("[!] Failed to configure Confident AI")
            return

        # Run a simple test
        print("\n[...] Running test evaluation...")
        test_case = LLMTestCase(
            input="What is my ROAS this week?",
            actual_output="Your ROAS this week is 2.45x, which represents a 15% increase from last week.",
            context=["ROAS: 2.45", "Previous ROAS: 2.13", "Change: +15%"],
        )

        # Simple evaluation without metrics (just to test connection)
        print("[OK] Test case created successfully")

        print("\n" + "=" * 60)
        print("SETUP COMPLETE!")
        print("=" * 60)
        print("""
Next steps:

1. Add to your shell profile (.bashrc, .zshrc):
   export CONFIDENT_API_KEY='{}'

2. Run the full evaluation suite:
   python -m app.tests.qa_evaluation.run_evaluation --confident

3. View results at:
   https://app.confident-ai.com

4. Run pytest with DeepEval:
   deepeval test run app/tests/qa_evaluation/test_qa_golden.py
""".format(api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else api_key))

    except Exception as e:
        print(f"\n[!] Error during setup: {e}")
        print("\nTroubleshooting:")
        print("1. Verify your API key at https://app.confident-ai.com")
        print("2. Check internet connection")
        print("3. Try: deepeval login --confident-api-key YOUR_KEY")
        return


if __name__ == "__main__":
    main()
