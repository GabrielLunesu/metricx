"""Meta sync service functions.

WHAT:
    Provides reusable functions for syncing Meta entities and metrics.

WHY:
    - Enables both HTTP endpoints and background workers to share the same logic.
    - Keeps routers thin (auth, request parsing) while services handle business logic.

REFERENCES:
    - docs/living-docs/REALTIME_SYNC_STATUS.md
    - backend/app/routers/meta_sync.py (calls these functions)
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, date
from typing import List, Tuple, Dict, Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import (
    Connection,
    Entity,
    MetricFact,
    LevelEnum,
    GoalEnum,
    ProviderEnum,
    MediaTypeEnum,
)
from app.schemas import (
    EntitySyncResponse,
    EntitySyncStats,
    MetricsSyncRequest,
    MetricsSyncResponse,
    MetricsSyncStats,
    DateRange,
    MetricFactCreate,
)
from app.security import decrypt_secret
from app.services.meta_ads_client import (
    MetaAdsClient,
    MetaAdsClientError,
    MetaAdsAuthenticationError,
    MetaAdsPermissionError,
)

logger = logging.getLogger(__name__)

# Objective to Goal Mapping
OBJECTIVE_TO_GOAL = {
    "OUTCOME_AWARENESS": GoalEnum.awareness,
    "OUTCOME_TRAFFIC": GoalEnum.traffic,
    "OUTCOME_ENGAGEMENT": GoalEnum.traffic,
    "OUTCOME_LEADS": GoalEnum.leads,
    "OUTCOME_APP_PROMOTION": GoalEnum.app_installs,
    "OUTCOME_SALES": GoalEnum.purchases,
    "CONVERSIONS": GoalEnum.conversions,
}


def sync_meta_entities(
    db: Session,
    workspace_id: UUID,
    connection_id: UUID,
) -> EntitySyncResponse:
    """Sync entity hierarchy from Meta to metricx."""

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

    logger.info(
        "[META_SYNC] Starting entity sync: workspace=%s, connection=%s",
        workspace_id,
        connection_id,
    )

    try:
        connection = (
            db.query(Connection)
            .filter(
                Connection.id == connection_id,
                Connection.workspace_id == workspace_id,
            )
            .first()
        )

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found or does not belong to workspace",
            )

        if connection.provider != ProviderEnum.meta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection is not a Meta connection (provider={connection.provider})",
            )

        access_token = _get_access_token(connection)

        client = MetaAdsClient(access_token=access_token)

        account_id = connection.external_account_id
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"

        logger.info(
            "[META_SYNC] Fetching campaigns for account: %s", account_id
        )
        campaigns = client.get_campaigns(account_id)
        logger.info(
            "[META_SYNC] Found %s campaigns for %s", len(campaigns), account_id
        )

        for campaign_data in campaigns:
            try:
                campaign_entity, campaign_created = _upsert_entity(
                    db=db,
                    connection=connection,
                    external_id=campaign_data["id"],
                    level=LevelEnum.campaign,
                    name=campaign_data.get("name", "Unnamed Campaign"),
                    status=campaign_data.get("status", "unknown"),
                    goal=_map_objective_to_goal(
                        campaign_data.get("objective")
                    ),
                )

                if campaign_created:
                    stats.campaigns_created += 1
                else:
                    stats.campaigns_updated += 1

                adsets = client.get_adsets(campaign_data["id"])
                logger.debug(
                    "[META_SYNC] Campaign %s has %s adsets",
                    campaign_data["id"],
                    len(adsets),
                )

                for adset_data in adsets:
                    adset_entity, adset_created = _upsert_entity(
                        db=db,
                        connection=connection,
                        external_id=adset_data["id"],
                        level=LevelEnum.adset,
                        name=adset_data.get("name", "Unnamed Ad Set"),
                        status=adset_data.get("status", "unknown"),
                        parent_id=campaign_entity.id,
                    )

                    if adset_created:
                        stats.adsets_created += 1
                    else:
                        stats.adsets_updated += 1

                ads = client.get_ads(adset_data["id"])
                logger.debug(
                    "[META_SYNC] Adset %s has %s ads",
                    adset_data["id"],
                    len(ads),
                )

                for ad_data in ads:
                    # Extract creative details if available (Meta only)
                    thumbnail_url = None
                    image_url = None
                    media_type = None

                    creative_ref = ad_data.get("creative")
                    if creative_ref and isinstance(creative_ref, dict):
                        creative_id = creative_ref.get("id")
                        if creative_id:
                            creative_details = client.get_creative_details(creative_id)
                            if creative_details:
                                thumbnail_url = creative_details.get("thumbnail_url")
                                image_url = creative_details.get("image_url")
                                media_type_str = creative_details.get("media_type")
                                if media_type_str:
                                    try:
                                        media_type = MediaTypeEnum(media_type_str)
                                    except ValueError:
                                        media_type = MediaTypeEnum.unknown

                    _, ad_created = _upsert_entity(
                        db=db,
                        connection=connection,
                        external_id=ad_data["id"],
                        level=LevelEnum.ad,
                        name=ad_data.get("name", "Unnamed Ad"),
                        status=ad_data.get("status", "unknown"),
                        parent_id=adset_entity.id,
                        thumbnail_url=thumbnail_url,
                        image_url=image_url,
                        media_type=media_type,
                    )

                    if ad_created:
                        stats.ads_created += 1
                    else:
                        stats.ads_updated += 1

            except MetaAdsPermissionError as e:
                logger.error(
                    "[META_SYNC] Permission error for campaign %s: %s",
                    campaign_data.get("id"),
                    e,
                )
                errors.append(
                    f"Permission error for campaign {campaign_data.get('id')}: {e}"
                )
            except MetaAdsClientError as e:
                logger.error(
                    "[META_SYNC] Error syncing campaign %s: %s",
                    campaign_data.get("id"),
                    e,
                )
                errors.append(
                    f"Error syncing campaign {campaign_data.get('id')}: {e}"
                )

        db.commit()

        stats.duration_seconds = (
            datetime.utcnow() - start_time
        ).total_seconds()

        success = len(errors) == 0

        logger.info(
            "[META_SYNC] Entity sync completed: workspace=%s, connection=%s, success=%s",
            workspace_id,
            connection_id,
            success,
        )

        return EntitySyncResponse(success=success, synced=stats, errors=errors)

    except MetaAdsAuthenticationError as e:
        logger.error("[META_SYNC] Authentication error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Meta authentication failed. Refresh access token.",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[META_SYNC] Unexpected error during entity sync: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {e}",
        ) from e


def _determine_date_range(
    connection: Connection,
    db: Session,
    request: MetricsSyncRequest
) -> Tuple[date, date]:
    """Determine date range for metrics sync.
    
    WHAT:
        Calculates start/end dates based on request and sync history.
        Implements 90-day policy and incremental sync logic.
    
    WHY:
        - 90-day historical backfill on first sync
        - Incremental sync on subsequent runs (only new dates)
        - Force refresh allows manual override
    """
    if request.start_date and request.end_date:
        return request.start_date, request.end_date
    
    end_date = datetime.utcnow().date() - timedelta(days=1)
    
    if request.force_refresh:
        start_date = end_date - timedelta(days=90)
    else:
        last_fact = db.query(MetricFact).join(Entity).filter(
            Entity.connection_id == connection.id,
            MetricFact.provider == ProviderEnum.meta
        ).order_by(desc(MetricFact.event_date)).first()
        
        if last_fact:
            last_date = last_fact.event_date.date()
            start_date = last_date + timedelta(days=1)
        else:
            days_back = 90
            if connection.connected_at.date() >= end_date:
                days_back = 30
            start_date = end_date - timedelta(days=days_back)
    
    if start_date > end_date:
        start_date = end_date - timedelta(days=30)
    
    return start_date, end_date


def _chunk_date_range(start: date, end: date, chunk_days: int = 7) -> List[Tuple[date, date]]:
    """Split date range into chunks for rate limit safety."""
    chunks = []
    current = start
    
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    
    return chunks


def _parse_actions(insight: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Meta actions array into metricx metrics."""
    actions = insight.get("actions", [])
    action_values = insight.get("action_values", [])
    
    result = {
        "purchases": 0,
        "leads": 0,
        "installs": 0,
        "conversions": 0,
        "revenue": 0.0
    }
    
    for action in actions:
        action_type = action.get("action_type", "")
        value = int(float(action.get("value", 0)))
        
        if action_type == "omni_purchase":
            result["purchases"] = value
        elif action_type == "lead":
            result["leads"] = value
        elif action_type == "app_install":
            result["installs"] = value
        elif action_type in ["offsite_conversion", "onsite_conversion"]:
            result["conversions"] += value
    
    for action_value in action_values:
        action_type = action_value.get("action_type", "")
        if action_type == "omni_purchase":
            result["revenue"] = float(action_value.get("value", 0))
    
    return result


def sync_meta_metrics(
    db: Session,
    workspace_id: UUID,
    connection_id: UUID,
    request: MetricsSyncRequest,
) -> MetricsSyncResponse:
    """Sync metrics from Meta to metricx (shared service function)."""

    from app.routers.ingest import ingest_metrics_internal

    start_time = datetime.utcnow()
    total_ingested = 0
    total_skipped = 0
    errors: List[str] = []

    logger.info(
        "[META_SYNC] Starting metrics sync: workspace=%s, connection=%s",
        workspace_id,
        connection_id,
    )

    try:
        connection = (
            db.query(Connection)
            .filter(
                Connection.id == connection_id,
                Connection.workspace_id == workspace_id,
            )
            .first()
        )

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found or does not belong to workspace",
            )

        if connection.provider != ProviderEnum.meta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection is not a Meta connection (provider={connection.provider})",
            )

        start_date, end_date = _determine_date_range(connection, db, request)

        if start_date > end_date or (end_date - start_date).days < 1:
            logger.warning(
                "[META_SYNC] Date range invalid or too small (%s to %s), forcing 30-day range",
                start_date,
                end_date,
            )
            end_date = datetime.utcnow().date() - timedelta(days=1)
            start_date = end_date - timedelta(days=29)

        logger.info(
            "[META_SYNC] Using date range: %s to %s (%s days)",
            start_date,
            end_date,
            (end_date - start_date).days + 1,
        )

        ad_entities = (
            db.query(Entity)
            .filter(
                Entity.connection_id == connection.id,
                Entity.level == LevelEnum.ad,
            )
            .all()
        )

        if not ad_entities:
            logger.warning(
                "[META_SYNC] No ad-level entities found for connection %s",
                connection_id,
            )
            return MetricsSyncResponse(
                success=True,
                synced=MetricsSyncStats(
                    ads_processed=0,
                    facts_ingested=0,
                    facts_skipped=0,
                    duration_seconds=0.0,
                    date_range=DateRange(
                        start=start_date,
                        end=end_date,
                    ),
                ),
                errors=["No ad-level entities found. Run entity sync first."],
            )

        access_token = _get_access_token(connection)
        client = MetaAdsClient(access_token=access_token)

        date_chunks = _chunk_date_range(start_date, end_date, chunk_size_days=7)

        logger.info(
            "[META_SYNC] Processing %s ad entities across %s date chunks",
            len(ad_entities),
            len(date_chunks),
        )

        for ad_entity in ad_entities:
            for chunk_start, chunk_end in date_chunks:
                try:
                    insights = client.get_insights(
                        entity_id=ad_entity.external_id,
                        level="ad",
                        start_date=chunk_start.isoformat(),
                        end_date=chunk_end.isoformat(),
                        time_increment=1  # Daily
                    )

                    if not insights:
                        total_skipped += 1
                        continue

                    facts: List[MetricFactCreate] = []

                    for insight in insights:
                        parsed_actions = _parse_actions(insight)
                        fact = MetricFactCreate(
                            entity_id=ad_entity.id,
                            external_entity_id=ad_entity.external_id,
                            provider=ProviderEnum.meta,
                            level=LevelEnum.ad,
                            event_at=datetime.fromisoformat(
                                insight["date_stop"] + "T00:00:00"
                            ),
                            spend=float(insight.get("spend", 0.0)),
                            impressions=int(insight.get("impressions", 0)),
                            clicks=int(insight.get("clicks", 0)),
                            conversions=parsed_actions.get("purchases"),
                            revenue=parsed_actions.get("purchase_value"),
                            leads=parsed_actions.get("leads"),
                            installs=parsed_actions.get("installs"),
                            purchases=parsed_actions.get("purchases"),
                            visitors=None,
                            profit=None,
                            currency=insight.get("account_currency", "USD"),
                        )
                        facts.append(fact)

                    if facts:
                        ingest_result = ingest_metrics_internal(
                            workspace_id=workspace_id,
                            facts=facts,
                            db=db,
                        )

                        total_ingested += ingest_result["ingested"]
                        total_skipped += ingest_result["skipped"]

                except MetaAdsClientError as e:
                    logger.error(
                        "[META_SYNC] Error fetching insights for ad %s: %s",
                        ad_entity.external_id,
                        e,
                    )
                    errors.append(
                        f"Error fetching insights for ad {ad_entity.external_id}: {e}"
                    )

        stats = MetricsSyncStats(
            ads_processed=len(ad_entities),
            facts_ingested=total_ingested,
            facts_skipped=total_skipped,
            duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            date_range=DateRange(start=start_date, end=end_date),
        )

        success = len(errors) == 0

        logger.info(
            "[META_SYNC] Metrics sync completed: workspace=%s, connection=%s, success=%s",
            workspace_id,
            connection_id,
            success,
        )

        return MetricsSyncResponse(success=success, synced=stats, errors=errors)

    except MetaAdsAuthenticationError as e:
        logger.error(
            "[META_SYNC] Authentication error during metrics sync: %s", e
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Meta authentication failed. Refresh access token.",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[META_SYNC] Unexpected error during metrics sync: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {e}",
        ) from e


def _get_access_token(connection: Connection) -> str:
    """Retrieve decrypted Meta access token, falling back to env token."""
    if connection.token and connection.token.access_token_enc:
        try:
            access_token = decrypt_secret(
                connection.token.access_token_enc,
                context=f"meta-connection:{connection.id}",
            )
            logger.info(
                "[META_SYNC] Using decrypted token for connection %s",
                connection.id,
            )
            return access_token
        except ValueError as exc:
            logger.exception(
                "[META_SYNC] Stored token for connection %s could not be decrypted",
                connection.id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored Meta token is invalid or corrupted.",
            ) from exc

    token = os.getenv("META_ACCESS_TOKEN")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="META_ACCESS_TOKEN not configured in environment",
        )

    logger.info("[META_SYNC] Using system user token from .env")
    return token


def _upsert_entity(
    db: Session,
    connection: Connection,
    external_id: str,
    level: LevelEnum,
    name: str,
    status: str,
    parent_id: Optional[UUID] = None,
    goal: Optional[GoalEnum] = None,
    thumbnail_url: Optional[str] = None,
    image_url: Optional[str] = None,
    media_type: Optional[MediaTypeEnum] = None,
) -> Tuple[Entity, bool]:
    """UPSERT entity by external_id + connection_id (idempotent).

    Args:
        db: Database session
        connection: Parent connection
        external_id: External platform ID
        level: Entity level (campaign, adset, ad)
        name: Entity name
        status: Entity status
        parent_id: Optional parent entity ID
        goal: Optional campaign goal
        thumbnail_url: Optional creative thumbnail URL (ad-level only, Meta only)
        image_url: Optional creative full-size image URL (ad-level only, Meta only)
        media_type: Optional media type (image, video, carousel)

    Returns:
        Tuple of (entity, was_created)
    """
    entity = (
        db.query(Entity)
        .filter(
            Entity.connection_id == connection.id,
            Entity.external_id == external_id,
        )
        .first()
    )

    was_created = False

    if entity:
        entity.name = name
        entity.status = status
        entity.parent_id = parent_id
        entity.goal = goal
        # Update creative fields if provided (only for ads)
        if thumbnail_url is not None:
            entity.thumbnail_url = thumbnail_url
        if image_url is not None:
            entity.image_url = image_url
        if media_type is not None:
            entity.media_type = media_type
        entity.updated_at = datetime.utcnow()
        logger.debug(
            "[META_SYNC] Updated entity: %s (%s)", external_id, level.value
        )
    else:
        entity = Entity(
            id=uuid.uuid4(),
            workspace_id=connection.workspace_id,
            connection_id=connection.id,
            level=level,
            external_id=external_id,
            name=name,
            status=status,
            parent_id=parent_id,
            goal=goal,
            thumbnail_url=thumbnail_url,
            image_url=image_url,
            media_type=media_type,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(entity)
        was_created = True
        logger.debug(
            "[META_SYNC] Created entity: %s (%s)", external_id, level.value
        )

    db.flush()
    return entity, was_created


def _map_objective_to_goal(objective: Optional[str]) -> Optional[GoalEnum]:
    """Maps Meta objectives to metricx goal enums."""
    if not objective:
        return None

    return OBJECTIVE_TO_GOAL.get(objective.upper())


def _determine_date_range(
    connection: Connection,
    db: Session,
    request: MetricsSyncRequest,
) -> Tuple[date, date]:
    """Determine date range for metrics sync."""
    if request.start_date and request.end_date:
        return request.start_date, request.end_date

    end_date = datetime.utcnow().date() - timedelta(days=1)

    last_fact = (
        db.query(MetricFact)
        .join(Entity)
        .filter(
            Entity.connection_id == connection.id,
            MetricFact.provider == ProviderEnum.meta,
        )
        .order_by(desc(MetricFact.event_date))
        .first()
    )

    if request.force_refresh:
        start_date = end_date - timedelta(days=90)
    elif last_fact:
        last_date = last_fact.event_date.date()
        start_date = last_date + timedelta(days=1)
    else:
        days_back = 90
        if connection.connected_at.date() >= end_date:
            days_back = 30
        start_date = end_date - timedelta(days=days_back)

    if start_date > end_date:
        start_date = end_date - timedelta(days=30)

    return start_date, end_date


def _chunk_date_range(
    start_date: date,
    end_date: date,
    chunk_size_days: int = 7,
) -> List[Tuple[date, date]]:
    """Chunk a date range into smaller windows."""
    chunks: List[Tuple[date, date]] = []
    current_start = start_date

    while current_start <= end_date:
        current_end = min(
            current_start + timedelta(days=chunk_size_days - 1), end_date
        )
        chunks.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)

    return chunks


def _parse_actions(insight: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Meta actions array into flat metrics."""
    result = {
        "purchases": None,
        "purchase_value": None,
        "leads": None,
        "installs": None,
    }

    actions = insight.get("actions") or []
    action_values = insight.get("action_values") or []

    action_map = {a["action_type"]: a.get("value") for a in actions}
    value_map = {a["action_type"]: a.get("value") for a in action_values}

    if "purchase" in action_map:
        result["purchases"] = float(action_map["purchase"])
    if "purchase" in value_map:
        result["purchase_value"] = float(value_map["purchase"])
    if "lead" in action_map:
        result["leads"] = float(action_map["lead"])
    if "install" in action_map:
        result["installs"] = float(action_map["install"])

    return result


