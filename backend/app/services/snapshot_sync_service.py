"""Snapshot Sync Service - 15-min granularity metric syncing.

WHAT:
    Provides services for syncing ad metrics to the metric_snapshots table
    with 15-minute granularity. Replaces the daily MetricFact approach.

WHY:
    - 15-min sync matches Meta/Google's data refresh rate
    - Enables real-time rules engine (stop-losses, alerts)
    - Supports intraday analytics and dashboards
    - Daily attribution re-fetch catches delayed conversions

SYNC SCHEDULE:
    - Every 15 min: Sync today's data (captures current state)
    - Daily 3am: Re-fetch last 7 days with hourly granularity (attribution)
    - Daily 1am: Compact day-2 from 15-min to hourly (storage efficiency)

REFERENCES:
    - Migration: alembic/versions/20251207_000001_add_metric_snapshots.py
    - Model: app/models.py:MetricSnapshot
    - Design: docs/architecture/unified-metrics.md
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, date, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert

from app.models import (
    Connection,
    Entity,
    MetricSnapshot,
    Workspace,
    LevelEnum,
    ProviderEnum,
)
from app.security import decrypt_secret
from app.services.meta_ads_client import MetaAdsClient, MetaAdsClientError
from app.services.google_ads_client import GAdsClient, QuotaExhaustedError
from app.telemetry import capture_exception

logger = logging.getLogger(__name__)

# Rate limit configuration
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = [30, 60, 120]  # Exponential backoff

# Parallel sync configuration
MAX_PARALLEL_SYNCS = 5  # Max concurrent connection syncs


# =============================================================================
# DATA CLASSES
# =============================================================================

class SnapshotSyncResult:
    """Result of a snapshot sync operation."""

    def __init__(self):
        self.inserted = 0
        self.updated = 0
        self.skipped = 0
        self.errors: List[str] = []
        self.synced_at: Optional[datetime] = None

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def __repr__(self):
        return f"SnapshotSyncResult(inserted={self.inserted}, updated={self.updated}, skipped={self.skipped}, errors={len(self.errors)})"


# =============================================================================
# ENTITY SYNC (Status Updates)
# =============================================================================

def _sync_entities_for_connection(db: Session, connection: Connection) -> None:
    """Sync entity hierarchy and status for a connection.

    WHAT:
        Updates campaign/adset/ad status (active, paused, etc.) from the ad platform.

    WHY:
        Captures real-time status changes so rules engine knows when
        something is paused/killed mid-day.

    Args:
        db: Database session
        connection: Connection to sync entities for
    """
    logger.info("[ENTITY_SYNC] Syncing entities for connection %s", connection.id)

    if connection.provider == ProviderEnum.meta:
        from app.services.meta_sync_service import sync_meta_entities
        sync_meta_entities(db, connection.workspace_id, connection.id)

    elif connection.provider == ProviderEnum.google:
        from app.services.google_sync_service import sync_google_entities
        sync_google_entities(db, connection.workspace_id, connection.id)

    logger.info("[ENTITY_SYNC] Entity sync complete for connection %s", connection.id)


# =============================================================================
# MAIN SYNC FUNCTIONS
# =============================================================================

def sync_snapshots_for_connection(
    db: Session,
    connection_id: UUID,
    mode: str = "realtime",
    sync_entities: bool = True
) -> SnapshotSyncResult:
    """Sync metric snapshots for a specific connection.

    WHAT:
        1. Syncs entity hierarchy and status (campaigns, adsets, ads)
        2. Fetches current metrics from ad platform and stores as snapshots

    WHY:
        Central entry point for all snapshot syncing, called by scheduler
        or manual trigger. Entity sync ensures we capture status changes
        (active/paused) in real-time.

    Args:
        db: Database session
        connection_id: Connection UUID to sync
        mode: Sync mode - "realtime" (today only) or "attribution" (last 7 days)
        sync_entities: Whether to sync entity status (default True)

    Returns:
        SnapshotSyncResult with counts and any errors
    """
    result = SnapshotSyncResult()

    # Get connection with status check
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.status == "active"  # Only sync active connections
    ).first()

    if not connection:
        result.errors.append(f"Connection {connection_id} not found or not active")
        return result

    logger.info(
        "[SNAPSHOT_SYNC] Starting sync: connection=%s, provider=%s, mode=%s, sync_entities=%s",
        connection_id, connection.provider.value, mode, sync_entities
    )

    # STEP 1: Sync entity hierarchy and status (captures paused/active changes)
    if sync_entities:
        try:
            _sync_entities_for_connection(db, connection)
        except Exception as e:
            logger.warning("[SNAPSHOT_SYNC] Entity sync failed, continuing with metrics: %s", e)
            capture_exception(e, extra={
                "operation": "entity_sync",
                "connection_id": str(connection_id),
                "provider": connection.provider.value,
            })
            # CRITICAL: Rollback the failed session to allow subsequent operations
            # Without this, the session remains in PendingRollback state and all
            # subsequent queries/commits will fail
            db.rollback()
            # Re-query connection since it was detached by rollback
            connection = db.query(Connection).filter(Connection.id == connection_id).first()
            if not connection:
                result.errors.append(f"Connection {connection_id} not found after rollback")
                return result
            # Don't fail the whole sync if entity sync fails

    # STEP 2: Sync metrics
    if connection.provider == ProviderEnum.meta:
        result = _sync_meta_snapshots(db, connection, mode)
    elif connection.provider == ProviderEnum.google:
        result = _sync_google_snapshots(db, connection, mode)
    else:
        result.errors.append(f"Unsupported provider: {connection.provider}")
        return result

    # Update connection sync tracking fields
    if result.success:
        result.synced_at = datetime.now(timezone.utc)
        connection.last_sync_completed_at = result.synced_at
        connection.last_sync_attempted_at = result.synced_at
        connection.last_sync_error = None
        connection.total_syncs_attempted = (connection.total_syncs_attempted or 0) + 1

        # Track data changes: if any rows were inserted or updated with new values
        # (inserted > 0 indicates new data, updated > 0 with changes indicates changed data)
        if result.inserted > 0 or result.updated > 0:
            connection.total_syncs_with_changes = (connection.total_syncs_with_changes or 0) + 1
            connection.last_metrics_changed_at = result.synced_at
            logger.info(
                "[SNAPSHOT_SYNC] Data changed: connection=%s, inserted=%d, updated=%d",
                connection_id, result.inserted, result.updated
            )

        db.commit()
    else:
        connection.last_sync_attempted_at = datetime.now(timezone.utc)
        connection.total_syncs_attempted = (connection.total_syncs_attempted or 0) + 1
        connection.last_sync_error = "; ".join(result.errors[:3])  # Store first 3 errors
        db.commit()

    return result


def sync_all_snapshots(
    db: Session,
    mode: str = "realtime",
    parallel: bool = True
) -> Dict[str, SnapshotSyncResult]:
    """Sync snapshots for all active connections.

    WHAT:
        Syncs all ACTIVE connections, optionally in parallel.

    WHY:
        Called by scheduler for the 15-min sync job.
        Parallel mode (default) maximizes throughput by syncing multiple
        connections simultaneously.

    Args:
        db: Database session
        mode: Sync mode - "realtime" or "attribution"
        parallel: If True, sync connections in parallel (default True)

    Returns:
        Dictionary mapping connection_id to SnapshotSyncResult
    """
    results = {}

    # Get all ACTIVE connections (Meta and Google only)
    connections = db.query(Connection).filter(
        Connection.provider.in_([ProviderEnum.meta, ProviderEnum.google]),
        Connection.status == "active"  # CRITICAL: Only sync active connections
    ).all()

    logger.info(
        "[SNAPSHOT_SYNC] Syncing %d active connections in %s mode (parallel=%s)",
        len(connections), mode, parallel
    )

    if parallel and len(connections) > 1:
        results = _sync_connections_parallel(connections, mode)
    else:
        results = _sync_connections_sequential(db, connections, mode)

    # Update workspace-level last_synced_at
    _update_workspace_sync_timestamps(db, connections)

    return results


def _sync_connections_sequential(
    db: Session,
    connections: List[Connection],
    mode: str
) -> Dict[str, SnapshotSyncResult]:
    """Sync connections sequentially.

    WHAT:
        Syncs each connection one at a time.

    WHY:
        Fallback for single connections or when parallel is disabled.
        Simpler error handling and debugging.

    Args:
        db: Database session
        connections: List of connections to sync
        mode: Sync mode

    Returns:
        Dictionary of results
    """
    results = {}

    for connection in connections:
        try:
            result = sync_snapshots_for_connection(db, connection.id, mode)
            results[str(connection.id)] = result
        except Exception as e:
            logger.error("[SNAPSHOT_SYNC] Failed to sync connection %s: %s", connection.id, e)
            capture_exception(e, extra={
                "operation": "sync_connection",
                "connection_id": str(connection.id),
                "provider": connection.provider.value,
                "workspace_id": str(connection.workspace_id),
                "mode": mode,
            })
            error_result = SnapshotSyncResult()
            error_result.errors.append(str(e))
            results[str(connection.id)] = error_result

    return results


def _sync_connections_parallel(
    connections: List[Connection],
    mode: str
) -> Dict[str, SnapshotSyncResult]:
    """Sync connections in parallel using ThreadPoolExecutor.

    WHAT:
        Syncs multiple connections concurrently using a thread pool.
        Each thread gets its own database session.

    WHY:
        - API calls to Meta/Google are I/O-bound and benefit from parallelism
        - Reduces total sync time from O(n) to O(n/workers)
        - Each connection gets isolated session to prevent conflicts

    Args:
        connections: List of connections to sync
        mode: Sync mode

    Returns:
        Dictionary of results
    """
    from app.database import SessionLocal

    results = {}
    connection_ids = [(str(c.id), c.provider.value, str(c.workspace_id)) for c in connections]

    def sync_single_connection(conn_info: Tuple[str, str, str]) -> Tuple[str, SnapshotSyncResult]:
        """Sync a single connection with its own session."""
        conn_id, provider, workspace_id = conn_info
        local_db = SessionLocal()
        try:
            result = sync_snapshots_for_connection(local_db, UUID(conn_id), mode)
            return (conn_id, result)
        except Exception as e:
            logger.error("[SNAPSHOT_SYNC] Parallel sync failed for %s: %s", conn_id, e)
            capture_exception(e, extra={
                "operation": "parallel_sync_connection",
                "connection_id": conn_id,
                "provider": provider,
                "workspace_id": workspace_id,
                "mode": mode,
            })
            error_result = SnapshotSyncResult()
            error_result.errors.append(str(e))
            return (conn_id, error_result)
        finally:
            local_db.close()

    # Use ThreadPoolExecutor for parallel I/O-bound work
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_SYNCS) as executor:
        futures = {
            executor.submit(sync_single_connection, info): info[0]
            for info in connection_ids
        }

        for future in as_completed(futures):
            conn_id = futures[future]
            try:
                result_conn_id, result = future.result()
                results[result_conn_id] = result
            except Exception as e:
                logger.error("[SNAPSHOT_SYNC] Future failed for %s: %s", conn_id, e)
                error_result = SnapshotSyncResult()
                error_result.errors.append(str(e))
                results[conn_id] = error_result

    logger.info(
        "[SNAPSHOT_SYNC] Parallel sync complete: %d connections, %d success, %d errors",
        len(results),
        sum(1 for r in results.values() if r.success),
        sum(1 for r in results.values() if not r.success)
    )

    return results


def _update_workspace_sync_timestamps(db: Session, connections: List[Connection]) -> None:
    """Update last_synced_at for all affected workspaces."""
    workspace_ids = set(c.workspace_id for c in connections)
    now = datetime.now(timezone.utc)

    for ws_id in workspace_ids:
        try:
            workspace = db.query(Workspace).filter(Workspace.id == ws_id).first()
            if workspace:
                workspace.last_synced_at = now
        except Exception as e:
            logger.warning("[SNAPSHOT_SYNC] Failed to update workspace %s timestamp: %s", ws_id, e)

    db.commit()


# =============================================================================
# META SYNC - ACCOUNT LEVEL (BATCHED)
# =============================================================================

def _sync_meta_snapshots(
    db: Session,
    connection: Connection,
    mode: str
) -> SnapshotSyncResult:
    """Sync Meta Ads metrics to snapshots using ACCOUNT-LEVEL insights.

    WHAT:
        Fetches metrics at two levels:
        1. Campaign-level (SOURCE OF TRUTH for dashboard KPIs)
        2. Ad-level (for drill-down analytics)

    WHY:
        Campaign-level is authoritative - ensures totals match Meta Ads dashboard.
        Ad-level is kept for drill-down into individual creative performance.

    CRITICAL: Uses account-level insights with breakdown, NOT per-entity calls.
    This reduces API calls from N (one per entity) to ~2 (campaign + ad breakdown).

    Args:
        db: Database session
        connection: Meta connection to sync
        mode: "realtime" (today) or "attribution" (last 7 days)

    Returns:
        SnapshotSyncResult
    """
    result = SnapshotSyncResult()

    try:
        # Get access token
        access_token = _get_meta_access_token(connection)
        client = MetaAdsClient(access_token=access_token)

        # Determine date range based on mode
        today = date.today()
        if mode == "realtime":
            start_date = today
            end_date = today
        elif mode == "backfill":
            # 90-day historical backfill for new connections
            start_date = today - timedelta(days=89)
            end_date = today
        else:  # attribution
            start_date = today - timedelta(days=7)
            end_date = today

        # Get ad account ID from connection
        ad_account_id = connection.external_account_id

        logger.info(
            "[SNAPSHOT_SYNC] Fetching Meta ACCOUNT-LEVEL insights for %s, %s to %s",
            ad_account_id, start_date, end_date
        )

        # Timestamp for this sync batch (rounded to 15 min)
        captured_at = datetime.now(timezone.utc)
        captured_at = captured_at.replace(
            minute=(captured_at.minute // 15) * 15,
            second=0,
            microsecond=0
        )

        # ===================================================================
        # PART 0: Sync campaign-level metrics (SOURCE OF TRUTH for KPI totals)
        # ===================================================================
        # WHY: Campaign-level metrics are the authoritative source for dashboard KPIs.
        # Meta campaigns may have discrepancies between campaign totals and the sum
        # of child entities (ads). Using campaign-level ensures our totals match
        # Meta Ads dashboard exactly.
        campaign_entities = db.query(Entity).filter(
            Entity.connection_id == connection.id,
            Entity.level == LevelEnum.campaign
        ).all()
        campaign_map = {str(e.external_id): e for e in campaign_entities}

        if campaign_map:
            logger.info(
                "[SNAPSHOT_SYNC] Fetching Meta CAMPAIGN-level insights for %d campaigns, %s to %s",
                len(campaign_map), start_date, end_date
            )

            campaign_insights = _fetch_meta_campaign_insights_with_retry(
                client=client,
                ad_account_id=ad_account_id,
                start_date=start_date,
                end_date=end_date
            )

            for insight in campaign_insights:
                campaign_id = insight.get("campaign_id")
                if not campaign_id:
                    result.skipped += 1
                    continue

                entity = campaign_map.get(str(campaign_id))
                if not entity:
                    result.skipped += 1
                    continue

                # Determine timestamp
                if mode == "realtime":
                    snap_time = captured_at
                else:
                    date_str = insight.get("date_stop")
                    if date_str:
                        snap_time = datetime.combine(
                            date.fromisoformat(date_str), datetime.max.time()
                        ).replace(tzinfo=timezone.utc)
                    else:
                        snap_time = captured_at

                snapshot_result = _upsert_meta_snapshot(
                    db=db,
                    entity=entity,
                    insight=insight,
                    captured_at=snap_time
                )

                if snapshot_result == "inserted":
                    result.inserted += 1
                else:
                    result.updated += 1

            logger.info(
                "[SNAPSHOT_SYNC] Meta campaign-level sync: %d entities processed",
                result.inserted + result.updated
            )

        # ===================================================================
        # PART 1: Sync ad-level metrics (for drill-down analytics)
        # ===================================================================
        # Build entity map for quick lookup
        ad_entities = db.query(Entity).filter(
            Entity.connection_id == connection.id,
            Entity.level == LevelEnum.ad
        ).all()
        entity_map = {str(e.external_id): e for e in ad_entities}

        if not entity_map:
            logger.info("[SNAPSHOT_SYNC] No ad entities for connection %s, skipping ad-level sync", connection.id)
            # Don't return early - we may have campaign data already
            if not campaign_map:
                return result
            db.commit()
            result.synced_at = datetime.now(timezone.utc)
            return result

        # Get insights at ACCOUNT level with ad breakdown
        # This returns all ads' metrics in one call
        insights = _fetch_meta_account_insights_with_retry(
            client=client,
            ad_account_id=ad_account_id,
            start_date=start_date,
            end_date=end_date
        )

        if not insights:
            logger.info("[SNAPSHOT_SYNC] No insights returned for account %s", ad_account_id)
            return result

        # Process each insight (one per ad per day)
        for insight in insights:
            ad_id = insight.get("ad_id")
            if not ad_id:
                result.skipped += 1
                continue

            entity = entity_map.get(str(ad_id))
            if not entity:
                result.skipped += 1
                continue

            # Determine timestamp
            # For backfill/attribution: use 23:59:59 so it's the "final" snapshot for that day
            # This ensures DISTINCT ON ... ORDER BY captured_at DESC picks the backfill data
            # over any partial realtime snapshots from earlier in the day
            if mode == "realtime":
                snap_time = captured_at
            else:
                date_str = insight.get("date_stop")
                if date_str:
                    snap_time = datetime.combine(
                        date.fromisoformat(date_str), datetime.max.time()
                    ).replace(tzinfo=timezone.utc)
                else:
                    snap_time = captured_at

            snapshot_result = _upsert_meta_snapshot(
                db=db,
                entity=entity,
                insight=insight,
                captured_at=snap_time
            )

            if snapshot_result == "inserted":
                result.inserted += 1
            else:
                result.updated += 1

        db.commit()
        result.synced_at = datetime.now(timezone.utc)

        logger.info(
            "[SNAPSHOT_SYNC] Meta sync complete: inserted=%d, updated=%d, skipped=%d",
            result.inserted, result.updated, result.skipped
        )

    except Exception as e:
        logger.error("[SNAPSHOT_SYNC] Meta sync failed: %s", e)
        capture_exception(e, extra={
            "operation": "meta_sync",
            "connection_id": str(connection.id),
            "workspace_id": str(connection.workspace_id),
            "mode": mode,
            "ad_account_id": connection.external_account_id,
        })
        db.rollback()
        result.errors.append(str(e))

    return result


def _fetch_meta_account_insights_with_retry(
    client: MetaAdsClient,
    ad_account_id: str,
    start_date: date,
    end_date: date
) -> List[Dict[str, Any]]:
    """Fetch Meta insights with retry and backoff for rate limits.

    Args:
        client: Meta Ads client
        ad_account_id: Ad account ID
        start_date: Start date
        end_date: End date

    Returns:
        List of insight dictionaries
    """
    for attempt in range(MAX_RETRIES):
        try:
            # Use account-level insights with ad breakdown
            insights = client.get_account_insights(
                ad_account_id=ad_account_id,
                level="ad",  # Breakdown by ad
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                time_increment=1,  # Daily
                fields=[
                    "ad_id", "ad_name", "spend", "impressions", "clicks",
                    "actions", "action_values", "account_currency"
                ]
            )
            return insights or []

        except MetaAdsClientError as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "too many" in error_msg:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF_SECONDS[attempt]
                    logger.warning(
                        "[SNAPSHOT_SYNC] Rate limited, waiting %d seconds (attempt %d/%d)",
                        wait_time, attempt + 1, MAX_RETRIES
                    )
                    time.sleep(wait_time)
                    continue
            raise

    return []


def _fetch_meta_campaign_insights_with_retry(
    client: MetaAdsClient,
    ad_account_id: str,
    start_date: date,
    end_date: date
) -> List[Dict[str, Any]]:
    """Fetch Meta CAMPAIGN-level insights with retry and backoff.

    WHAT:
        Fetches metrics at campaign level (SOURCE OF TRUTH for dashboard KPIs).

    WHY:
        Campaign-level ensures totals match Meta Ads dashboard exactly.
        Ad-level metrics may not sum to campaign totals in all cases.

    Args:
        client: Meta Ads client
        ad_account_id: Ad account ID
        start_date: Start date
        end_date: End date

    Returns:
        List of insight dictionaries with campaign_id field
    """
    for attempt in range(MAX_RETRIES):
        try:
            # Use account-level insights with CAMPAIGN breakdown
            insights = client.get_account_insights(
                ad_account_id=ad_account_id,
                level="campaign",  # Campaign-level for accurate totals
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                time_increment=1,  # Daily
                fields=[
                    "campaign_id", "campaign_name", "spend", "impressions", "clicks",
                    "actions", "action_values", "account_currency"
                ]
            )
            return insights or []

        except MetaAdsClientError as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "too many" in error_msg:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF_SECONDS[attempt]
                    logger.warning(
                        "[SNAPSHOT_SYNC] Rate limited on campaign insights, waiting %d seconds (attempt %d/%d)",
                        wait_time, attempt + 1, MAX_RETRIES
                    )
                    time.sleep(wait_time)
                    continue
            raise

    return []


def _upsert_meta_snapshot(
    db: Session,
    entity: Entity,
    insight: Dict[str, Any],
    captured_at: datetime
) -> str:
    """Upsert a single Meta snapshot.

    Returns:
        "inserted" or "updated"
    """
    # Parse actions to get conversions/revenue
    actions = insight.get("actions", []) or []
    action_values = insight.get("action_values", []) or []

    purchases = 0
    leads = 0
    revenue = Decimal("0")

    for action in actions:
        action_type = action.get("action_type", "")
        value = int(float(action.get("value", 0)))
        if action_type == "omni_purchase":
            purchases = value
        elif action_type == "lead":
            leads = value

    for av in action_values:
        if av.get("action_type") == "omni_purchase":
            revenue = Decimal(str(av.get("value", 0)))

    # Build snapshot data
    snapshot_data = {
        "entity_id": entity.id,
        "provider": "meta",
        "captured_at": captured_at,
        "spend": Decimal(str(insight.get("spend", 0) or 0)),
        "impressions": int(insight.get("impressions", 0) or 0),
        "clicks": int(insight.get("clicks", 0) or 0),
        "conversions": Decimal(str(purchases)),
        "revenue": revenue,
        "leads": Decimal(str(leads)),
        "purchases": purchases,
        "currency": insight.get("account_currency", "USD"),
    }

    # Use PostgreSQL UPSERT (INSERT ... ON CONFLICT)
    stmt = insert(MetricSnapshot).values(**snapshot_data)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_metric_snapshots_entity_provider_time",
        set_={
            "spend": stmt.excluded.spend,
            "impressions": stmt.excluded.impressions,
            "clicks": stmt.excluded.clicks,
            "conversions": stmt.excluded.conversions,
            "revenue": stmt.excluded.revenue,
            "leads": stmt.excluded.leads,
            "purchases": stmt.excluded.purchases,
            "currency": stmt.excluded.currency,
        }
    )

    db.execute(stmt)
    return "updated"


# =============================================================================
# GOOGLE SYNC - ACCOUNT LEVEL (BATCHED)
# =============================================================================

def _sync_google_snapshots(
    db: Session,
    connection: Connection,
    mode: str
) -> SnapshotSyncResult:
    """Sync Google Ads metrics to snapshots.

    WHAT:
        Fetches metrics at three levels:
        1. Campaign-level (SOURCE OF TRUTH for dashboard KPIs)
        2. Ad-level (for drill-down into traditional campaigns)
        3. Asset_group-level (for drill-down into PMax campaigns)

    WHY:
        Campaign-level is authoritative because:
        - PMax campaigns don't attribute all spend to asset_groups
        - Shopping campaigns may have spend not fully attributed to ads
        - Campaign-level ensures totals match Google Ads dashboard exactly

        Child-level (ad, asset_group) is kept for drill-down analytics.

    Args:
        db: Database session
        connection: Google connection to sync
        mode: "realtime" (today), "attribution" (last 7 days), or "backfill" (last 90 days)

    Returns:
        SnapshotSyncResult
    """
    result = SnapshotSyncResult()

    try:
        # Get Google Ads client
        client = _get_google_ads_client(connection)
        customer_id = _normalize_customer_id(connection.external_account_id)

        # Determine date range based on mode
        today = date.today()
        if mode == "realtime":
            start_date = today
            end_date = today
        elif mode == "backfill":
            # 90-day historical backfill for new connections
            start_date = today - timedelta(days=89)
            end_date = today
        else:  # attribution
            start_date = today - timedelta(days=7)
            end_date = today

        # Timestamp for this sync batch
        captured_at = datetime.now(timezone.utc)
        captured_at = captured_at.replace(
            minute=(captured_at.minute // 15) * 15,
            second=0,
            microsecond=0
        )

        # ===================================================================
        # PART 0: Sync campaign-level metrics (SOURCE OF TRUTH for KPI totals)
        # ===================================================================
        # WHY: Campaign-level metrics are the authoritative source for dashboard KPIs.
        # PMax campaigns don't attribute all spend to asset_groups - some spend exists
        # only at campaign level. Similarly, Shopping campaigns may have spend not
        # fully attributed to ads. Using campaign-level ensures our totals match
        # Google Ads dashboard exactly.
        campaign_entities = db.query(Entity).filter(
            Entity.connection_id == connection.id,
            Entity.level == LevelEnum.campaign
        ).all()
        campaign_map = {str(e.external_id): e for e in campaign_entities}

        if campaign_map:
            logger.info(
                "[SNAPSHOT_SYNC] Fetching Google CAMPAIGN-level metrics for %d campaigns, %s to %s",
                len(campaign_map), start_date, end_date
            )

            rows = _fetch_google_metrics_with_retry(client, customer_id, start_date, end_date, level="campaign")

            for row in rows:
                try:
                    raw = row.get("_raw")
                    if not raw:
                        result.skipped += 1
                        continue

                    ext_id = str(raw.campaign.id)
                    entity = campaign_map.get(ext_id)

                    if not entity:
                        result.skipped += 1
                        continue

                    # For backfill/attribution: use 23:59:59 so it's the "final" snapshot for that day
                    snap_time = captured_at if mode == "realtime" else datetime.combine(
                        date.fromisoformat(row["date"]), datetime.max.time()
                    ).replace(tzinfo=timezone.utc)

                    _upsert_google_snapshot(
                        db=db,
                        entity=entity,
                        row=row,
                        captured_at=snap_time,
                        currency=connection.currency_code or "USD"
                    )
                    result.updated += 1

                except Exception as e:
                    logger.error("[SNAPSHOT_SYNC] Error processing campaign row: %s", e)
                    result.errors.append(str(e))

        # ===================================================================
        # PART 1: Sync ad-level metrics (for drill-down into traditional campaigns)
        # ===================================================================
        ad_entities = db.query(Entity).filter(
            Entity.connection_id == connection.id,
            Entity.level == LevelEnum.ad
        ).all()
        ad_entity_map = {str(e.external_id): e for e in ad_entities}

        if ad_entity_map:
            logger.info(
                "[SNAPSHOT_SYNC] Fetching Google AD metrics for %d ads, %s to %s",
                len(ad_entity_map), start_date, end_date
            )

            rows = _fetch_google_metrics_with_retry(client, customer_id, start_date, end_date, level="ad")

            for row in rows:
                try:
                    raw = row.get("_raw")
                    if not raw:
                        result.skipped += 1
                        continue

                    ext_id = str(raw.ad_group_ad.ad.id)
                    entity = ad_entity_map.get(ext_id)

                    if not entity:
                        result.skipped += 1
                        continue

                    # For backfill/attribution: use 23:59:59 so it's the "final" snapshot for that day
                    # This ensures DISTINCT ON ... ORDER BY captured_at DESC picks the backfill data
                    # over any partial realtime snapshots from earlier in the day
                    snap_time = captured_at if mode == "realtime" else datetime.combine(
                        date.fromisoformat(row["date"]), datetime.max.time()
                    ).replace(tzinfo=timezone.utc)

                    _upsert_google_snapshot(
                        db=db,
                        entity=entity,
                        row=row,
                        captured_at=snap_time,
                        currency=connection.currency_code or "USD"
                    )
                    result.updated += 1

                except Exception as e:
                    logger.error("[SNAPSHOT_SYNC] Error processing ad row: %s", e)
                    result.errors.append(str(e))

        # ===================================================================
        # PART 2: Sync asset_group-level metrics (for drill-down into PMax campaigns)
        # ===================================================================
        asset_group_entities = db.query(Entity).filter(
            Entity.connection_id == connection.id,
            Entity.level == LevelEnum.asset_group
        ).all()
        asset_group_map = {str(e.external_id): e for e in asset_group_entities}

        if asset_group_map:
            logger.info(
                "[SNAPSHOT_SYNC] Fetching Google ASSET_GROUP metrics for %d groups, %s to %s",
                len(asset_group_map), start_date, end_date
            )

            rows = _fetch_google_metrics_with_retry(client, customer_id, start_date, end_date, level="asset_group")

            for row in rows:
                try:
                    raw = row.get("_raw")
                    if not raw:
                        result.skipped += 1
                        continue

                    ext_id = str(raw.asset_group.id)
                    entity = asset_group_map.get(ext_id)

                    if not entity:
                        result.skipped += 1
                        continue

                    # For backfill/attribution: use 23:59:59 so it's the "final" snapshot for that day
                    snap_time = captured_at if mode == "realtime" else datetime.combine(
                        date.fromisoformat(row["date"]), datetime.max.time()
                    ).replace(tzinfo=timezone.utc)

                    _upsert_google_snapshot(
                        db=db,
                        entity=entity,
                        row=row,
                        captured_at=snap_time,
                        currency=connection.currency_code or "USD"
                    )
                    result.updated += 1

                except Exception as e:
                    logger.error("[SNAPSHOT_SYNC] Error processing asset_group row: %s", e)
                    result.errors.append(str(e))

        if not campaign_map and not ad_entity_map and not asset_group_map:
            logger.warning("[SNAPSHOT_SYNC] No campaign, ad, or asset_group entities for Google connection %s", connection.id)

        db.commit()
        result.synced_at = datetime.now(timezone.utc)

        logger.info(
            "[SNAPSHOT_SYNC] Google sync complete: inserted=%d, updated=%d, skipped=%d",
            result.inserted, result.updated, result.skipped
        )

    except QuotaExhaustedError as e:
        # Circuit breaker: Set rate_limited_until to skip this connection
        logger.warning(
            "[SNAPSHOT_SYNC] Google quota exhausted for connection %s, setting cooldown for %ds",
            connection.id, e.retry_seconds
        )
        connection.rate_limited_until = datetime.now(timezone.utc) + timedelta(seconds=e.retry_seconds)
        connection.sync_status = "rate_limited"
        connection.last_sync_error = f"Quota exhausted. Cooldown until {connection.rate_limited_until.isoformat()}"
        db.commit()
        result.errors.append(str(e))
        capture_exception(e, extra={
            "operation": "google_sync_quota_exhausted",
            "connection_id": str(connection.id),
            "workspace_id": str(connection.workspace_id),
            "retry_seconds": e.retry_seconds,
        })

    except Exception as e:
        logger.error("[SNAPSHOT_SYNC] Google sync failed: %s", e)
        capture_exception(e, extra={
            "operation": "google_sync",
            "connection_id": str(connection.id),
            "workspace_id": str(connection.workspace_id),
            "mode": mode,
            "customer_id": _normalize_customer_id(connection.external_account_id),
        })
        db.rollback()
        result.errors.append(str(e))

    return result


def _fetch_google_metrics_with_retry(
    client: GAdsClient,
    customer_id: str,
    start_date: date,
    end_date: date,
    level: str = "ad"
) -> List[Dict[str, Any]]:
    """Fetch Google metrics with retry and backoff.

    Args:
        client: Google Ads client
        customer_id: Customer ID
        start_date: Start date
        end_date: End date
        level: Entity level - "ad" for traditional campaigns, "asset_group" for PMax

    Returns:
        List of metric rows
    """
    for attempt in range(MAX_RETRIES):
        try:
            return client.fetch_daily_metrics(customer_id, start_date, end_date, level=level)
        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg or "quota" in error_msg or "resource_exhausted" in error_msg:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF_SECONDS[attempt]
                    logger.warning(
                        "[SNAPSHOT_SYNC] Rate limited, waiting %d seconds (attempt %d/%d)",
                        wait_time, attempt + 1, MAX_RETRIES
                    )
                    time.sleep(wait_time)
                    continue
            raise

    return []


def _upsert_google_snapshot(
    db: Session,
    entity: Entity,
    row: Dict[str, Any],
    captured_at: datetime,
    currency: str = "USD"
) -> str:
    """Upsert a single Google snapshot.

    Args:
        db: Database session
        entity: The entity to attach the snapshot to
        row: Metric data from Google Ads API
        captured_at: Timestamp for the snapshot
        currency: Currency code from the connection (e.g., "EUR", "USD")
    """

    snapshot_data = {
        "entity_id": entity.id,
        "provider": "google",
        "captured_at": captured_at,
        "spend": Decimal(str(row.get("spend", 0) or 0)),
        "impressions": int(row.get("impressions", 0) or 0),
        "clicks": int(row.get("clicks", 0) or 0),
        "conversions": Decimal(str(row.get("conversions", 0) or 0)),
        "revenue": Decimal(str(row.get("revenue", 0) or 0)),
        "currency": currency,
    }

    stmt = insert(MetricSnapshot).values(**snapshot_data)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_metric_snapshots_entity_provider_time",
        set_={
            "spend": stmt.excluded.spend,
            "impressions": stmt.excluded.impressions,
            "clicks": stmt.excluded.clicks,
            "conversions": stmt.excluded.conversions,
            "revenue": stmt.excluded.revenue,
            "currency": stmt.excluded.currency,
        }
    )

    db.execute(stmt)
    return "updated"


# =============================================================================
# COMPACTION (ATOMIC)
# =============================================================================

def compact_snapshots_to_hourly(db: Session, target_date: date) -> int:
    """Compact 15-min snapshots to hourly for a specific date.

    WHAT:
        Aggregates 15-min snapshots into hourly buckets and removes the
        original 15-min rows in a SINGLE ATOMIC transaction.

    WHY:
        - Storage efficiency: 24 rows/day instead of 96 rows/day
        - Historical data doesn't need 15-min granularity

    WHEN:
        - Called daily at 1am for day-2 (e.g., on Dec 9, compact Dec 7)

    Args:
        db: Database session
        target_date: Date to compact

    Returns:
        Number of hourly snapshots created
    """
    logger.info("[COMPACTION] Starting compaction for date %s", target_date)

    # Start and end of target date
    start_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(target_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)

    # ATOMIC: Use a single CTE-based operation to avoid race conditions
    # This creates hourly aggregates and deletes 15-min rows in one statement
    compact_sql = text("""
        WITH hourly_aggregates AS (
            SELECT
                entity_id,
                provider,
                date_trunc('hour', captured_at) as hour_bucket,
                MAX(spend) as spend,
                MAX(impressions) as impressions,
                MAX(clicks) as clicks,
                MAX(conversions) as conversions,
                MAX(revenue) as revenue,
                MAX(leads) as leads,
                MAX(purchases) as purchases,
                MAX(installs) as installs,
                MAX(visitors) as visitors,
                MAX(profit) as profit,
                MAX(currency) as currency
            FROM metric_snapshots
            WHERE captured_at >= :start_dt
              AND captured_at < :end_dt
              AND captured_at != date_trunc('hour', captured_at)
            GROUP BY entity_id, provider, date_trunc('hour', captured_at)
        ),
        inserted AS (
            INSERT INTO metric_snapshots (
                id, entity_id, provider, captured_at,
                spend, impressions, clicks, conversions, revenue,
                leads, purchases, installs, visitors, profit, currency, created_at
            )
            SELECT
                gen_random_uuid(),
                entity_id,
                provider,
                hour_bucket,
                spend, impressions, clicks, conversions, revenue,
                leads, purchases, installs, visitors, profit, currency,
                NOW()
            FROM hourly_aggregates
            ON CONFLICT (entity_id, provider, captured_at)
            DO UPDATE SET
                spend = EXCLUDED.spend,
                impressions = EXCLUDED.impressions,
                clicks = EXCLUDED.clicks,
                conversions = EXCLUDED.conversions,
                revenue = EXCLUDED.revenue,
                leads = EXCLUDED.leads,
                purchases = EXCLUDED.purchases,
                installs = EXCLUDED.installs,
                visitors = EXCLUDED.visitors,
                profit = EXCLUDED.profit
            RETURNING 1
        ),
        deleted AS (
            DELETE FROM metric_snapshots
            WHERE captured_at >= :start_dt
              AND captured_at < :end_dt
              AND captured_at != date_trunc('hour', captured_at)
            RETURNING 1
        )
        SELECT
            (SELECT COUNT(*) FROM inserted) as inserted_count,
            (SELECT COUNT(*) FROM deleted) as deleted_count
    """)

    result = db.execute(compact_sql, {"start_dt": start_dt, "end_dt": end_dt})
    row = result.fetchone()

    hourly_count = row[0] if row else 0
    deleted_count = row[1] if row else 0

    db.commit()

    logger.info(
        "[COMPACTION] Compacted date %s: created %d hourly, deleted %d 15-min rows",
        target_date, hourly_count, deleted_count
    )

    return hourly_count


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_meta_access_token(connection: Connection) -> str:
    """Get decrypted Meta access token."""
    if connection.token and connection.token.access_token_enc:
        return decrypt_secret(
            connection.token.access_token_enc,
            context=f"meta:{connection.id}:access"
        )
    raise ValueError(f"No access token for connection {connection.id}")


def _get_google_ads_client(connection: Connection) -> GAdsClient:
    """Get Google Ads client for connection.

    WHAT:
        Builds GAdsClient using connection's stored refresh token.

    WHY:
        Each connection has its own OAuth tokens stored in the database.
        We decrypt them and build a client for that specific account.
    """
    if connection.token and connection.token.refresh_token_enc:
        refresh_token = decrypt_secret(
            connection.token.refresh_token_enc,
            context=f"google:{connection.id}:refresh"
        )

        # Get parent MCC ID if this is a client account
        parent_mcc_id = getattr(connection, 'parent_mcc_id', None)

        # Build SDK client from tokens
        sdk_client = GAdsClient._build_client_from_tokens(
            refresh_token,
            login_customer_id=parent_mcc_id
        )
        return GAdsClient(client=sdk_client)

    # Fallback: Use env vars (for backward compatibility)
    logger.warning("[SNAPSHOT_SYNC] No refresh token for connection %s, using env vars", connection.id)
    return GAdsClient()


def _normalize_customer_id(customer_id: str) -> str:
    """Remove dashes from customer ID."""
    return customer_id.replace("-", "") if customer_id else ""


def _date_to_hourly_timestamp(date_str: str) -> datetime:
    """Convert date string to midnight timestamp for hourly attribution data."""
    if not date_str:
        return datetime.now(timezone.utc)
    d = date.fromisoformat(date_str)
    return datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc)


def get_last_sync_time(db: Session, workspace_id: UUID) -> Optional[datetime]:
    """Get the last sync time for a workspace.

    Used by UI to display "Last updated X minutes ago".

    Args:
        db: Database session
        workspace_id: Workspace UUID

    Returns:
        Last sync timestamp or None if never synced
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if workspace:
        return getattr(workspace, 'last_synced_at', None)
    return None
