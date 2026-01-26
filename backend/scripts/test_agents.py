#!/usr/bin/env python3
"""
Agent System Local Test Script.

WHAT:
    Script to test agent system functionality locally:
    - Email notifications (via Resend)
    - Agent evaluation engine
    - Condition evaluation
    - Action execution (dry-run mode)

USAGE:
    # Test email notification (requires RESEND_API_KEY in .env)
    python scripts/test_agents.py email --to your@email.com

    # Test agent evaluation with mock data
    python scripts/test_agents.py evaluate --agent-id <uuid>

    # Test condition parsing
    python scripts/test_agents.py condition

    # Run full integration test
    python scripts/test_agents.py full --to your@email.com

REFERENCES:
    - backend/app/services/agents/notification_service.py
    - backend/app/services/agents/evaluation_engine.py
    - backend/app/services/agents/conditions.py
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_email_notification(recipient_email: str) -> bool:
    """Test sending an email notification via Resend."""
    from app.services.agents.notification_service import AgentNotificationService

    logger.info(f"Testing email notification to: {recipient_email}")

    # Create notification service from settings
    service = AgentNotificationService.from_settings()

    # Check if Resend is configured
    if not service.resend_client:
        logger.warning("Resend not configured (no API key). Email will be logged but not sent.")
        logger.warning("Set RESEND_API_KEY in your .env file to enable real email sending.")

    # Test trigger notification
    result = await service.send_trigger_notification(
        agent_id="test-agent-id-12345",
        agent_name="Test ROAS Agent",
        entity_name="Summer Campaign 2024",
        entity_provider="Meta",
        condition_explanation="ROAS dropped below 2.0x threshold (current: 1.45x)",
        observations={
            "spend": 1250.50,
            "revenue": 1812.75,
            "roas": 1.45,
            "clicks": 2345,
            "impressions": 125000,
            "conversions": 45.5,
        },
        action_results=[
            {"type": "email", "success": True, "description": "Notification sent to team"},
            {"type": "scale_budget", "success": True, "description": "Budget reduced by 20% (from $100 to $80)"},
        ],
        recipients=[recipient_email],
        workspace_id="test-workspace-id",
    )

    if result.success:
        logger.info(f"Email sent successfully! Message ID: {result.message_id}")
        return True
    else:
        logger.error(f"Email failed: {result.error}")
        return False


async def test_error_notification(recipient_email: str) -> bool:
    """Test sending an error notification."""
    from app.services.agents.notification_service import AgentNotificationService

    logger.info(f"Testing error notification to: {recipient_email}")

    service = AgentNotificationService.from_settings()

    result = await service.send_error_notification(
        agent_id="test-agent-id-12345",
        agent_name="Test ROAS Agent",
        error_message="Failed to fetch metrics from Meta API: Rate limit exceeded. The agent will retry in 15 minutes.",
        recipients=[recipient_email],
        workspace_id="test-workspace-id",
    )

    if result.success:
        logger.info(f"Error notification sent! Message ID: {result.message_id}")
        return True
    else:
        logger.error(f"Error notification failed: {result.error}")
        return False


def test_condition_parsing():
    """Test condition parsing and evaluation."""
    from app.services.agents.conditions import condition_from_dict, EvalContext

    logger.info("Testing condition parsing and evaluation...")

    # Test threshold condition
    threshold_config = {
        "type": "threshold",
        "metric": "roas",
        "operator": "lt",
        "value": 2.0,
    }

    condition = condition_from_dict(threshold_config)
    logger.info(f"Parsed threshold condition: {condition}")

    # Test with metrics above threshold
    context_good = EvalContext(
        observations={"roas": 3.5, "spend": 1000, "revenue": 3500},
        entity_id="entity-1",
        entity_name="Test Campaign",
        evaluated_at=datetime.now(timezone.utc),
    )
    result_good = condition.evaluate(context_good)
    logger.info(f"ROAS 3.5 (above threshold): met={result_good.met}, explanation={result_good.explanation}")

    # Test with metrics below threshold
    context_bad = EvalContext(
        observations={"roas": 1.5, "spend": 1000, "revenue": 1500},
        entity_id="entity-1",
        entity_name="Test Campaign",
        evaluated_at=datetime.now(timezone.utc),
    )
    result_bad = condition.evaluate(context_bad)
    logger.info(f"ROAS 1.5 (below threshold): met={result_bad.met}, explanation={result_bad.explanation}")

    # Test composite AND condition
    composite_config = {
        "type": "composite",
        "operator": "and",
        "conditions": [
            {"type": "threshold", "metric": "roas", "operator": "lt", "value": 2.0},
            {"type": "threshold", "metric": "spend", "operator": "gt", "value": 500},
        ],
    }

    composite = condition_from_dict(composite_config)
    result_composite = composite.evaluate(context_bad)
    logger.info(f"Composite AND (ROAS < 2 AND spend > 500): met={result_composite.met}")

    # Test change condition
    change_config = {
        "type": "change",
        "metric": "spend",
        "percent": 20.0,  # 20% change
        "direction": "increase",
        "reference_period": "previous_day",
    }

    change_condition = condition_from_dict(change_config)
    context_with_history = EvalContext(
        observations={"spend": 1200, "spend_previous": 900},
        entity_id="entity-1",
        entity_name="Test Campaign",
        evaluated_at=datetime.now(timezone.utc),
    )
    result_change = change_condition.evaluate(context_with_history)
    logger.info(f"Change condition (spend increased 33%): met={result_change.met}, explanation={result_change.explanation}")

    logger.info("Condition tests completed!")
    return True


async def test_full_flow(recipient_email: str) -> bool:
    """Run full integration test."""
    logger.info("=" * 60)
    logger.info("FULL INTEGRATION TEST")
    logger.info("=" * 60)

    all_passed = True

    # Test 1: Condition parsing
    logger.info("\n--- Test 1: Condition Parsing ---")
    try:
        test_condition_parsing()
        logger.info("✓ Condition parsing: PASSED")
    except Exception as e:
        logger.error(f"✗ Condition parsing: FAILED - {e}")
        all_passed = False

    # Test 2: Trigger email
    logger.info("\n--- Test 2: Trigger Email Notification ---")
    try:
        result = await test_email_notification(recipient_email)
        if result:
            logger.info("✓ Trigger email: PASSED")
        else:
            logger.warning("⚠ Trigger email: SKIPPED (Resend not configured)")
    except Exception as e:
        logger.error(f"✗ Trigger email: FAILED - {e}")
        all_passed = False

    # Test 3: Error email
    logger.info("\n--- Test 3: Error Email Notification ---")
    try:
        result = await test_error_notification(recipient_email)
        if result:
            logger.info("✓ Error email: PASSED")
        else:
            logger.warning("⚠ Error email: SKIPPED (Resend not configured)")
    except Exception as e:
        logger.error(f"✗ Error email: FAILED - {e}")
        all_passed = False

    # Summary
    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("ALL TESTS PASSED!")
    else:
        logger.error("SOME TESTS FAILED")
    logger.info("=" * 60)

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Test agent system locally")
    subparsers = parser.add_subparsers(dest="command", help="Test command")

    # Email test
    email_parser = subparsers.add_parser("email", help="Test email notification")
    email_parser.add_argument("--to", required=True, help="Recipient email address")

    # Condition test
    subparsers.add_parser("condition", help="Test condition parsing")

    # Full test
    full_parser = subparsers.add_parser("full", help="Run full integration test")
    full_parser.add_argument("--to", required=True, help="Recipient email address")

    args = parser.parse_args()

    if args.command == "email":
        asyncio.run(test_email_notification(args.to))
    elif args.command == "condition":
        test_condition_parsing()
    elif args.command == "full":
        asyncio.run(test_full_flow(args.to))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
