"""Google Ads synchronization endpoints.

WHAT:
    REST endpoints for syncing Google entity hierarchy (campaigns/ad groups/ads)
    and daily metrics (GAQL) from Google Ads API into metricx DB.

WHY:
    - User-initiated sync via UI button (manual trigger)
    - Two-step process: entities first, then metrics (idempotent)
    - Mirrors Meta sync architecture for consistency

REFERENCES:
    - app/services/google_ads_client.py (GAdsClient, map_channel_to_goal)
    - app/routers/ingest.py (ingest_metrics_internal)
    - docs/living-docs/GOOGLE_INTEGRATION_STATUS.MD
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Connection, Entity, MetricFact, LevelEnum, GoalEnum, ProviderEnum
from app.schemas import (
    EntitySyncResponse,
    EntitySyncStats,
    MetricsSyncRequest,
    MetricsSyncResponse,
    MetricsSyncStats,
    DateRange,
    MetricFactCreate,
)
from app.routers.ingest import ingest_metrics_internal
from app.services.google_ads_client import GAdsClient, map_channel_to_goal
from app.security import decrypt_secret


logger = logging.getLogger(__name__)


# --- Helpers -------------------------------------------------------------

def _normalize_customer_id(customer_id: str) -> str:
    """Normalize Google customer ID (strip hyphens)."""
    return "".join(ch for ch in str(customer_id) if ch.isdigit())


def _compute_date_chunks(start: date, end: date, chunk_days: int = 7) -> List[Tuple[date, date]]:
    """Split date range into inclusive chunks of size chunk_days."""
    chunks: List[Tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        chunk_end = min(end, cursor + timedelta(days=chunk_days - 1))
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + timedelta(days=1)
    return chunks


def _normalize_status(status_val: Optional[object]) -> str:
    """Map Google enum/string statuses into unified app statuses.

    Google: ENABLED/PAUSED/REMOVED → active/paused/inactive
    """
    if status_val is None:
        return "unknown"
    # Extract enum name if present
    if hasattr(status_val, "name"):
        s = str(status_val.name).upper()
    else:
        s = str(status_val).upper()
    if s == "ENABLED":
        return "active"
    if s == "PAUSED":
        return "paused"
    if s == "REMOVED":
        return "inactive"
    return s.lower()


def _upsert_entity(
    db: Session,
    connection: Connection,
    external_id: str,
    level: LevelEnum,
    name: str,
    status: str,
    parent_id: Optional[UUID] = None,
    goal: Optional[GoalEnum] = None,
    tracking_params: Optional[Dict[str, Any]] = None,
) -> Tuple[Entity, bool]:
    """UPSERT entity by external_id + connection_id.

    WHAT: Creates new Entity or updates existing one.
    WHY: Idempotent synchronization across re-runs.

    Args:
        tracking_params: Optional URL tracking configuration (utm_source, etc.)
    """
    entity = db.query(Entity).filter(
        Entity.connection_id == connection.id,
        Entity.external_id == external_id,
    ).first()

    created = False
    if entity:
        entity.name = name
        entity.status = status
        entity.parent_id = parent_id
        entity.goal = goal
        entity.level = level  # Update level in case it changed (e.g., adset -> asset_group)
        # Update tracking params for UTM detection
        if tracking_params is not None:
            entity.tracking_params = tracking_params
        entity.updated_at = datetime.utcnow()
    else:
        entity = Entity(
            level=level,
            external_id=external_id,
            name=name,
            status=status,
            parent_id=parent_id,
            goal=goal,
            tracking_params=tracking_params,
            workspace_id=connection.workspace_id,
            connection_id=connection.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(entity)
        created = True
    db.flush()
    return entity, created


def _update_connection_metadata(db: Session, connection: Connection, meta: Dict[str, Optional[str]]) -> None:
    """Persist timezone/currency on Connection if available."""
    tz = meta.get("time_zone")
    cur = meta.get("currency_code")
    changed = False
    if tz and tz != connection.timezone:
        connection.timezone = tz
        changed = True
    if cur and cur != connection.currency_code:
        connection.currency_code = cur
        changed = True
    if changed:
        db.flush()


def _get_google_ads_client(connection: Connection) -> GAdsClient:
    """Get Google Ads client from connection tokens or env vars.
    
    WHAT:
        Uses encrypted tokens from connection if available, otherwise falls back to env vars.
        For client accounts (accessed through MCC), sets login_customer_id header.
    WHY:
        Supports OAuth connections where tokens are stored in database.
        Handles MCC hierarchy by setting login-customer-id header.
    """
    # OAuth: Use connection.token
    if connection.token and connection.token.refresh_token_enc:
        try:
            refresh_token = decrypt_secret(
                connection.token.refresh_token_enc,
                context=f"google-connection:{connection.id}",
            )
            logger.info("[GOOGLE_SYNC] Using decrypted refresh token for connection %s", connection.id)
            
            # Check if this is a client account (has parent MCC)
            parent_mcc_id = None
            if connection.token.ad_account_ids:
                # Check if ad_account_ids is a dict with parent_mcc_id
                if isinstance(connection.token.ad_account_ids, dict):
                    parent_mcc_id = connection.token.ad_account_ids.get("parent_mcc_id")
                    logger.info("[GOOGLE_SYNC] Connection %s has parent MCC: %s", connection.id, parent_mcc_id)
            
            # Build client from connection tokens with parent MCC if needed
            sdk_client = GAdsClient._build_client_from_tokens(
                refresh_token,
                login_customer_id=parent_mcc_id  # Set parent MCC as login customer
            )
            return GAdsClient(client=sdk_client)
        except ValueError:
            logger.exception("[GOOGLE_SYNC] Stored token for connection %s could not be decrypted", connection.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored Google Ads token is invalid or corrupted."
            )
    
    # Fallback: Use env vars (for backward compatibility)
    logger.info("[GOOGLE_SYNC] Using refresh token from environment variables")
    return GAdsClient()


# --- Service Functions ----------------------------------------------------

def sync_google_entities(
    db: Session,
    workspace_id: UUID,
    connection_id: UUID,
) -> EntitySyncResponse:
    """Sync Google Ads entity hierarchy (campaigns → ad groups → ads).

    Mirrors Meta sync endpoint; safe to re-run (UPSERT).
    """
    start_time = datetime.utcnow()
    stats = EntitySyncStats(
        campaigns_created=0,
        campaigns_updated=0,
        adsets_created=0,
        adsets_updated=0,
        ads_created=0,
        ads_updated=0,
        duration_seconds=0.0,
    )
    errors: List[str] = []

    # Validate connection
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.workspace_id == workspace_id,
    ).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found or not in workspace")
    if connection.provider != ProviderEnum.google:
        raise HTTPException(status_code=400, detail=f"Connection is not a Google connection (provider={connection.provider})")

    customer_id = _normalize_customer_id(connection.external_account_id)
    client = _get_google_ads_client(connection)

    # Check if this is a manager account (MCC) - MCC accounts don't have campaigns
    try:
        query = f"""
            SELECT customer.manager
            FROM customer
            WHERE customer.id = {customer_id}
        """
        response = client.search(customer_id, query)
        is_manager = False
        for row in response:
            is_manager = getattr(row.customer, 'manager', False)
            break
        
        if is_manager:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection {connection.name} ({customer_id}) is a Manager Account (MCC). "
                       f"MCC accounts don't contain campaigns directly. Please sync individual ad accounts instead."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[GOOGLE_SYNC] Failed to check manager status: %s", e)
        # Continue - assume it's not an MCC if check fails

    # Update connection metadata (timezone/currency)
    try:
        meta = client.get_customer_metadata(customer_id)
        _update_connection_metadata(db, connection, meta)
    except Exception as e:
        logger.warning("[GOOGLE_SYNC] Failed to fetch customer metadata: %s", e)

    # Campaigns
    try:
        logger.info("[GOOGLE_SYNC] Fetching campaigns for customer %s", customer_id)
        campaigns = client.list_campaigns(customer_id)
        for c in campaigns:
            goal = map_channel_to_goal(c.get("advertising_channel_type"))
            camp, created = _upsert_entity(
                db=db,
                connection=connection,
                external_id=str(c["id"]),
                level=LevelEnum.campaign,
                name=c.get("name") or f"Campaign {c['id']}",
                status=_normalize_status(c.get("status")),
                parent_id=None,
                goal=goal,
            )
            if created:
                stats.campaigns_created += 1
            else:
                stats.campaigns_updated += 1

            # Route by channel type: STANDARD (ad groups/ads) vs PMax (asset groups/assets)
            chan = c.get("advertising_channel_type") or ""
            logger.info("[GOOGLE_SYNC] Campaign %s (%s) has channel_type=%s", c.get("id"), c.get("name"), chan)
            if str(chan).upper() == "PERFORMANCE_MAX":
                # Asset Groups for PMax campaigns - these are the leaf entities for metrics
                # Asset Groups are similar to ads in traditional campaigns
                try:
                    agroups = client.list_asset_groups(customer_id, str(c["id"]))
                    logger.info("[GOOGLE_SYNC] PMax campaign %s has %d asset_groups", c.get("id"), len(agroups))
                    for grp in agroups:
                        asset_group_entity, ag_created = _upsert_entity(
                            db=db,
                            connection=connection,
                            external_id=str(grp["id"]),
                            level=LevelEnum.asset_group,  # Use proper asset_group level
                            name=grp.get("name") or f"Asset Group {grp['id']}",
                            status=_normalize_status(grp.get("status")),
                            parent_id=camp.id,
                        )
                        if ag_created:
                            stats.adsets_created += 1  # Count as adsets for UI totals
                        else:
                            stats.adsets_updated += 1

                        # Note: We don't sync individual assets as they don't have metrics
                        # The asset_group level is where metrics are reported for PMax
                except Exception as e:
                    logger.exception("[GOOGLE_SYNC] Asset groups fetch failed for campaign %s: %s", c.get("id"), e)
                    errors.append(f"campaign {c.get('id')}: {e}")
            else:
                # Standard campaigns: Ad groups and ads
                # Note: Shopping campaigns have ad_groups but NO ad_group_ad entities
                chan_upper = str(chan).upper()
                is_shopping = chan_upper == "SHOPPING"

                try:
                    ad_groups = client.list_ad_groups(customer_id, str(c["id"]))
                    logger.info("[GOOGLE_SYNC] Campaign %s has %d ad_groups", c.get("id"), len(ad_groups))
                    for ag in ad_groups:
                        adset, ag_created = _upsert_entity(
                            db=db,
                            connection=connection,
                            external_id=str(ag["id"]),
                            level=LevelEnum.adset,
                            name=ag.get("name") or f"Ad group {ag['id']}",
                            status=_normalize_status(ag.get("status")),
                            parent_id=camp.id,
                        )
                        if ag_created:
                            stats.adsets_created += 1
                        else:
                            stats.adsets_updated += 1

                        # Skip ads for Shopping campaigns - they don't have ad_group_ad
                        # Shopping products are synced separately via shopping_performance_view
                        if is_shopping:
                            logger.debug(
                                "[GOOGLE_SYNC] Skipping ads for Shopping campaign %s ad_group %s (no ad_group_ad)",
                                c.get("id"), ag.get("id")
                            )
                            continue

                        # Ads (only for non-Shopping campaigns)
                        try:
                            ads = client.list_ads(customer_id, str(ag["id"]))
                            for ad in ads:
                                # Extract tracking params for UTM detection
                                # WHY: Enables proactive attribution warnings
                                tracking_params = ad.get("tracking_params")

                                _, ad_created = _upsert_entity(
                                    db=db,
                                    connection=connection,
                                    external_id=str(ad["id"]),
                                    level=LevelEnum.ad,
                                    name=ad.get("name") or f"Ad {ad['id']}",
                                    status=_normalize_status(ad.get("status")),
                                    parent_id=adset.id,
                                    tracking_params=tracking_params,
                                )
                                if ad_created:
                                    stats.ads_created += 1
                                else:
                                    stats.ads_updated += 1
                        except Exception as e:
                            logger.exception("[GOOGLE_SYNC] Ads fetch failed for ad group %s: %s", ag.get("id"), e)
                            errors.append(f"ad_group {ag.get('id')}: {e}")
                except Exception as e:
                    logger.exception("[GOOGLE_SYNC] Ad groups fetch failed for campaign %s: %s", c.get("id"), e)
                    errors.append(f"campaign {c.get('id')}: {e}")
    except Exception as e:
        logger.exception("[GOOGLE_SYNC] Campaigns fetch failed: %s", e)
        errors.append(str(e))

    stats.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
    db.commit()
    return EntitySyncResponse(success=len(errors) == 0, synced=stats, errors=errors)


def sync_google_metrics(
    db: Session,
    workspace_id: UUID,
    connection_id: UUID,
    request: Optional[MetricsSyncRequest],
) -> MetricsSyncResponse:
    """Sync Google Ads daily metrics (ad-level) into MetricFact.

    Default: 90-day backfill, 7-day chunks, incremental by last ingested date.
    """
    started = datetime.utcnow()
    errors: List[str] = []

    # Validate connection/provider
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.workspace_id == workspace_id,
    ).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found or not in workspace")
    if connection.provider != ProviderEnum.google:
        raise HTTPException(status_code=400, detail=f"Connection is not a Google connection (provider={connection.provider})")

    if request is None:
        request = MetricsSyncRequest()

    # Determine date range
    # Note: Include today's data for real-time reflection of Google Ads dashboard
    today = date.today()
    default_end = today
    # Last ingested date for this connection/provider
    last_date = db.query(func.max(MetricFact.event_date)).join(Entity, Entity.id == MetricFact.entity_id).filter(
        Entity.connection_id == connection.id,
        MetricFact.provider == ProviderEnum.google,
    ).scalar()

    if request.start_date and request.end_date:
        start_d, end_d = request.start_date, request.end_date
    else:
        if last_date and not request.force_refresh:
            start_d = (last_date.date() if isinstance(last_date, datetime) else last_date) + timedelta(days=1)
        else:
            start_d = default_end - timedelta(days=89)
        end_d = default_end

    if start_d > end_d:
        # Nothing to sync
        stats = MetricsSyncStats(
            facts_ingested=0,
            facts_skipped=0,
            date_range=DateRange(start=start_d, end=end_d),
            ads_processed=0,
            duration_seconds=(datetime.utcnow() - started).total_seconds(),
        )
        return MetricsSyncResponse(success=True, synced=stats, errors=[])

    chunks = _compute_date_chunks(start_d, end_d, 7)
    customer_id = _normalize_customer_id(connection.external_account_id)
    client = _get_google_ads_client(connection)

    # Check if this is a manager account (MCC) - MCC accounts don't have metrics
    try:
        query = f"""
            SELECT customer.manager
            FROM customer
            WHERE customer.id = {customer_id}
        """
        response = client.search(customer_id, query)
        is_manager = False
        for row in response:
            is_manager = getattr(row.customer, 'manager', False)
            break
        
        if is_manager:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection {connection.name} ({customer_id}) is a Manager Account (MCC). "
                       f"MCC accounts don't contain campaigns or metrics directly. Please sync individual ad accounts instead."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[GOOGLE_SYNC] Failed to check manager status: %s", e)
        # Continue - assume it's not an MCC if check fails

    # Safeguard: ensure hierarchy exists to avoid orphaned placeholders
    # Build maps for known entities in this connection
    ad_rows = (
        db.query(Entity.external_id, Entity.id)
        .filter(Entity.connection_id == connection.id)
        .filter(Entity.level == LevelEnum.ad)
        .all()
    )
    ad_map: Dict[str, UUID] = {str(ext): eid for ext, eid in ad_rows}
    asset_group_rows = (
        db.query(Entity.external_id, Entity.id)
        .filter(Entity.connection_id == connection.id)
        .filter(Entity.level == LevelEnum.adset)
        .all()
    )
    asset_group_map: Dict[str, UUID] = {str(ext): eid for ext, eid in asset_group_rows}
    creative_rows = (
        db.query(Entity.external_id, Entity.id)
        .filter(Entity.connection_id == connection.id)
        .filter(Entity.level == LevelEnum.creative)
        .all()
    )
    creative_map: Dict[str, UUID] = {str(ext): eid for ext, eid in creative_rows}
    # Campaign map for linking products to campaigns (Shopping/PMax)
    campaign_rows = (
        db.query(Entity.external_id, Entity.id)
        .filter(Entity.connection_id == connection.id)
        .filter(Entity.level == LevelEnum.campaign)
        .all()
    )
    campaign_map: Dict[str, UUID] = {str(ext): eid for ext, eid in campaign_rows}
    # Product map for existing product entities
    product_rows = (
        db.query(Entity.external_id, Entity.id)
        .filter(Entity.connection_id == connection.id)
        .filter(Entity.level == LevelEnum.product)
        .all()
    )
    product_map: Dict[str, UUID] = {str(ext): eid for ext, eid in product_rows}

    # Diagnostic logging to understand entity state
    logger.info(
        "[GOOGLE_SYNC] Entity maps: ads=%d, adsets=%d, creatives=%d, campaigns=%d, products=%d",
        len(ad_map), len(asset_group_map), len(creative_map), len(campaign_map), len(product_map)
    )

    if not ad_map and not asset_group_map and not creative_map:
        # Mirror Meta behavior: allow metrics sync to succeed with zero work
        stats = MetricsSyncStats(
            facts_ingested=0,
            facts_skipped=0,
            date_range=DateRange(start=start_d, end=end_d),
            ads_processed=0,
            duration_seconds=(datetime.utcnow() - started).total_seconds(),
        )
        logger.info("[GOOGLE_SYNC] No entities found for connection %s; metrics sync is a no-op.", connection.id)
        return MetricsSyncResponse(success=True, synced=stats, errors=[])

    total_ingested = 0
    total_skipped = 0
    ads_processed: set[str] = set()
    missing_entity_count = 0

    for s, e in chunks:
        logger.info("[GOOGLE_SYNC] Processing chunk %s to %s", s, e)
        try:
            rows = client.fetch_daily_metrics(customer_id, s, e, level="ad")
            logger.info("[GOOGLE_SYNC] Ad-level query returned %d rows", len(rows))
            facts: List[MetricFactCreate] = []
            for row in rows:
                # Identify external entity id depending on level
                raw = row.get("_raw")
                try:
                    ext_id = str(raw.ad_group_ad.ad.id)
                except Exception:
                    # Fallback: cannot parse id → skip
                    continue
                # Resolve to existing entity_id to prevent placeholder creation
                entity_id = ad_map.get(ext_id)
                if not entity_id:
                    missing_entity_count += 1
                    continue  # Skip rows for unknown ads to avoid orphan facts
                ads_processed.add(ext_id)
                ev_date = datetime.combine(date.fromisoformat(row["date"]), datetime.min.time())
                facts.append(MetricFactCreate(
                    entity_id=entity_id,
                    provider=ProviderEnum.google,
                    level=LevelEnum.ad,
                    event_at=ev_date,
                    spend=row.get("spend", 0.0),
                    impressions=row.get("impressions", 0),
                    clicks=row.get("clicks", 0),
                    conversions=row.get("conversions", 0.0),
                    revenue=row.get("revenue", 0.0),
                    currency=connection.currency_code or "USD",
                ))
            if facts:
                res = ingest_metrics_internal(workspace_id=workspace_id, facts=facts, db=db)
                total_ingested += res.get("ingested", 0)
                total_skipped += res.get("skipped", 0)
        except Exception as ex:
            logger.exception("[GOOGLE_SYNC] Metrics fetch failed for %s to %s: %s", s, e, ex)
            errors.append(f"{s}..{e}: {ex}")

        # PMax: asset_group level metrics → adset entities
        try:
            rows_ag = client.fetch_daily_metrics(customer_id, s, e, level="asset_group")
            facts_ag: List[MetricFactCreate] = []
            for row in rows_ag:
                ext_id = str(row.get("resource_id"))
                entity_id = asset_group_map.get(ext_id)
                if not entity_id:
                    missing_entity_count += 1
                    continue
                ev_date = datetime.combine(date.fromisoformat(row["date"]), datetime.min.time())
                facts_ag.append(MetricFactCreate(
                    entity_id=entity_id,
                    provider=ProviderEnum.google,
                    level=LevelEnum.adset,
                    event_at=ev_date,
                    spend=row.get("spend", 0.0),
                    impressions=row.get("impressions", 0),
                    clicks=row.get("clicks", 0),
                    conversions=row.get("conversions", 0.0),
                    revenue=row.get("revenue", 0.0),
                    currency=connection.currency_code or "USD",
                ))
            if facts_ag:
                res = ingest_metrics_internal(workspace_id=workspace_id, facts=facts_ag, db=db)
                total_ingested += res.get("ingested", 0)
                total_skipped += res.get("skipped", 0)
        except Exception as ex:
            logger.exception("[GOOGLE_SYNC] Asset group metrics fetch failed for %s to %s: %s", s, e, ex)
            errors.append(f"asset_group {s}..{e}: {ex}")

        # PMax: asset_group_asset level metrics → creative entities
        try:
            rows_cre = client.fetch_daily_metrics(customer_id, s, e, level="asset_group_asset")
            facts_cre: List[MetricFactCreate] = []
            for row in rows_cre:
                ext_id = str(row.get("resource_id"))
                entity_id = creative_map.get(ext_id)
                if not entity_id:
                    missing_entity_count += 1
                    continue
                ev_date = datetime.combine(date.fromisoformat(row["date"]), datetime.min.time())
                facts_cre.append(MetricFactCreate(
                    entity_id=entity_id,
                    provider=ProviderEnum.google,
                    level=LevelEnum.creative,
                    event_at=ev_date,
                    spend=row.get("spend", 0.0),
                    impressions=row.get("impressions", 0),
                    clicks=row.get("clicks", 0),
                    conversions=row.get("conversions", 0.0),
                    revenue=row.get("revenue", 0.0),
                    currency=connection.currency_code or "USD",
                ))
            if facts_cre:
                res = ingest_metrics_internal(workspace_id=workspace_id, facts=facts_cre, db=db)
                total_ingested += res.get("ingested", 0)
                total_skipped += res.get("skipped", 0)
        except Exception as ex:
            logger.exception("[GOOGLE_SYNC] Asset group asset metrics fetch failed for %s to %s: %s", s, e, ex)
            errors.append(f"asset_group_asset {s}..{e}: {ex}")

        # Shopping: product-level metrics from shopping_performance_view
        # WHY: Shopping campaigns don't have ad_group_ad, they have product data
        try:
            rows_prod = client.fetch_shopping_performance(customer_id, s, e)
            logger.info("[GOOGLE_SYNC] Shopping query returned %d rows for %s to %s", len(rows_prod), s, e)
            facts_prod: List[MetricFactCreate] = []
            products_created = 0
            products_skipped_no_parent = 0
            for row in rows_prod:
                # Build unique product identifier: product_item_id within ad_group
                product_item_id = row.get("product_item_id", "")
                ad_group_id = str(row.get("ad_group_id", ""))
                campaign_id = str(row.get("campaign_id", ""))

                if not product_item_id:
                    continue

                # Unique external_id = product_item_id:ad_group_id (product may appear in multiple ad groups)
                product_ext_id = f"{product_item_id}:{ad_group_id}"

                # Find parent: prefer ad_group, fallback to campaign
                parent_entity_id = asset_group_map.get(ad_group_id) or campaign_map.get(campaign_id)
                if not parent_entity_id:
                    # No parent found - skip to avoid orphaned product
                    products_skipped_no_parent += 1
                    missing_entity_count += 1
                    continue

                # Upsert product entity on-demand
                entity_id = product_map.get(product_ext_id)
                if not entity_id:
                    product_name = row.get("product_title") or product_item_id
                    product_entity, created = _upsert_entity(
                        db=db,
                        connection=connection,
                        external_id=product_ext_id,
                        level=LevelEnum.product,
                        name=product_name,
                        status="active",
                        parent_id=parent_entity_id,
                    )
                    entity_id = product_entity.id
                    product_map[product_ext_id] = entity_id
                    if created:
                        products_created += 1

                ev_date = datetime.combine(date.fromisoformat(row["date"]), datetime.min.time())
                facts_prod.append(MetricFactCreate(
                    entity_id=entity_id,
                    provider=ProviderEnum.google,
                    level=LevelEnum.product,
                    event_at=ev_date,
                    spend=row.get("spend", 0.0),
                    impressions=row.get("impressions", 0),
                    clicks=row.get("clicks", 0),
                    conversions=row.get("conversions", 0.0),
                    revenue=row.get("revenue", 0.0),
                    currency=connection.currency_code or "USD",
                ))
            if facts_prod:
                res = ingest_metrics_internal(workspace_id=workspace_id, facts=facts_prod, db=db)
                total_ingested += res.get("ingested", 0)
                total_skipped += res.get("skipped", 0)
            logger.info(
                "[GOOGLE_SYNC] Shopping products: %d rows, %d facts created, %d entities created, %d skipped (no parent)",
                len(rows_prod), len(facts_prod), products_created, products_skipped_no_parent
            )
        except Exception as ex:
            logger.exception("[GOOGLE_SYNC] Shopping product metrics fetch failed for %s to %s: %s", s, e, ex)
            errors.append(f"shopping_products {s}..{e}: {ex}")

    stats = MetricsSyncStats(
        facts_ingested=total_ingested,
        facts_skipped=total_skipped,
        date_range=DateRange(start=start_d, end=end_d),
        ads_processed=len(ads_processed),
        duration_seconds=(datetime.utcnow() - started).total_seconds(),
    )
    if missing_entity_count:
        errors.append(
            f"Skipped {missing_entity_count} ad rows because entities were missing. "
            "Run entity sync to create hierarchy before metrics."
        )
    return MetricsSyncResponse(success=len(errors) == 0, synced=stats, errors=errors)
