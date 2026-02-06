"""Unit tests for snapshot entity-sync strategy resolution."""

from datetime import datetime, timezone

from app.services.snapshot_sync_service import _resolve_entity_sync_strategy


def test_realtime_strategy_runs_every_30_minutes():
    should_sync, mode = _resolve_entity_sync_strategy(
        "realtime", now_utc=datetime(2026, 2, 6, 10, 0, tzinfo=timezone.utc)
    )
    assert should_sync is True
    assert mode == "active_only"

    should_sync, mode = _resolve_entity_sync_strategy(
        "realtime", now_utc=datetime(2026, 2, 6, 10, 15, tzinfo=timezone.utc)
    )
    assert should_sync is False
    assert mode == "active_only"

    should_sync, mode = _resolve_entity_sync_strategy(
        "realtime", now_utc=datetime(2026, 2, 6, 10, 30, tzinfo=timezone.utc)
    )
    assert should_sync is True
    assert mode == "active_only"


def test_non_realtime_strategy_runs_full_reconcile():
    should_sync, mode = _resolve_entity_sync_strategy("attribution")
    assert should_sync is True
    assert mode == "full"

    should_sync, mode = _resolve_entity_sync_strategy("backfill")
    assert should_sync is True
    assert mode == "full"
