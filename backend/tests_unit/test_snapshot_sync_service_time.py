"""
Snapshot Sync Time Semantics Tests (Unit)
========================================

WHAT: Unit tests for snapshot timestamp selection logic.
WHY: Prevent regressions where backfill writes future `captured_at` values, breaking intraday charts.

NOTE:
These tests live outside `backend/app/tests/` to avoid loading the integration-test
`conftest.py`, which configures a database and environment variables not required here.

REFERENCES:
- backend/app/services/snapshot_sync_service.py:_get_snapshot_captured_at
"""

import os
from datetime import date, datetime, timezone

# Ensure app.security can import in test environments without a configured .env.
# This key decodes to 32 bytes and is only used to satisfy import-time validation.
os.environ["TOKEN_ENCRYPTION_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="

from app.services.snapshot_sync_service import _get_snapshot_captured_at, _get_end_of_day_in_utc


def test_get_snapshot_captured_at_backfill_today_uses_real_captured_at() -> None:
    """Backfill rows for account-today must not write future timestamps."""
    captured_at = datetime(2025, 12, 15, 11, 15, tzinfo=timezone.utc)
    account_today = date(2025, 12, 15)

    result = _get_snapshot_captured_at(
        mode="backfill",
        metrics_date_str="2025-12-15",
        captured_at=captured_at,
        account_timezone="Europe/Amsterdam",
        account_today=account_today,
    )

    assert result == captured_at


def test_get_snapshot_captured_at_backfill_historical_anchors_to_end_of_day() -> None:
    """Historical backfill rows stay anchored to end-of-day in account timezone."""
    captured_at = datetime(2025, 12, 15, 11, 15, tzinfo=timezone.utc)
    account_today = date(2025, 12, 15)

    result = _get_snapshot_captured_at(
        mode="backfill",
        metrics_date_str="2025-12-14",
        captured_at=captured_at,
        account_timezone="Europe/Amsterdam",
        account_today=account_today,
    )

    assert result == _get_end_of_day_in_utc("2025-12-14", "Europe/Amsterdam")
    assert result.tzinfo is timezone.utc


def test_get_snapshot_captured_at_realtime_always_uses_real_captured_at() -> None:
    captured_at = datetime(2025, 12, 15, 11, 15, tzinfo=timezone.utc)
    account_today = date(2025, 12, 15)

    result = _get_snapshot_captured_at(
        mode="realtime",
        metrics_date_str="2025-12-15",
        captured_at=captured_at,
        account_timezone="Europe/Amsterdam",
        account_today=account_today,
    )

    assert result == captured_at
