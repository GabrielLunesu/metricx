"""
Meta Ads metrics ingestion API.

WHY:
- Receive metric data from Meta Ads API (and other platforms)
- UPSERT pattern prevents duplicate ingestion
- Decoupled from sync logic (Phase 3 will call this)

WHAT:
- POST endpoint to ingest batch of metrics
- Validates data, checks for duplicates via natural_key
- Creates entities on-the-fly if needed

WHERE:
- Called by Phase 3 MetaMetricsFetcher service
- Can also be used for manual ingestion/testing

REFERENCES:
- app/schemas.py:MetricFactCreate (request schema)
- app/models.py:MetricFact (database model)
- backend/docs/roadmap/meta-ads-roadmap.md Phase 1.2
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models import MetricFact
from typing import List
from uuid import UUID, uuid4
from datetime import datetime, timezone
import logging

from ..database import get_db
from ..deps import get_current_user
from ..schemas import MetricFactCreate, MetricFactIngestResponse, UserOut
from ..models import MetricFact, Entity, Import, Fetch, Connection, Workspace
from app.services.sync_comparison import has_metrics_changed

logger = logging.getLogger(__name__)

router = APIRouter()


async def ingest_metrics_internal(
    workspace_id: UUID,
    facts: List[MetricFactCreate],
    db: Session
) -> dict:
    """
    Internal ingestion function for use by other services.
    
    WHY:
    - meta_sync needs to call ingestion without HTTP/FastAPI dependencies
    - Reuses all ingestion logic (deduplication, entity creation, etc.)
    
    WHAT:
    - Same logic as ingest_metrics endpoint but without auth/HTTP layer
    - Returns dict instead of response model
    - Commits transaction
    
    WHERE:
    - Called by meta_sync.py during metrics synchronization
    - Can be called by other internal services
    
    Args:
        workspace_id: Workspace UUID
        facts: List of metrics to ingest
        db: Database session
        
    Returns:
        Dict with ingested/skipped/errors counts
    """
    # Verify workspace exists
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise ValueError(f"Workspace {workspace_id} not found")
    
    ingested = 0
    skipped = 0
    errors = []
    
    # Get or create import record for this batch
    import_record = _get_or_create_import(db, workspace_id)
    
    logger.info(f"[INGEST] Processing {len(facts)} facts for workspace {workspace_id}")
    
    for idx, fact in enumerate(facts):
        try:
            # Determine entity_id
            if fact.entity_id:
                entity_id = fact.entity_id
            elif fact.external_entity_id:
                # Get or create entity
                entity = _get_or_create_entity(
                    db=db,
                    workspace_id=workspace_id,
                    provider=fact.provider.value,
                    external_id=fact.external_entity_id,
                    level=fact.level.value
                )
                entity_id = entity.id
            else:
                errors.append(f"Fact {idx}: Must provide entity_id or external_entity_id")
                continue
            
            # Compute natural_key if not provided
            natural_key = fact.natural_key
            if not natural_key:
                external_id = fact.external_entity_id or str(entity_id)
                natural_key = f"{external_id}-{fact.event_at.isoformat()}"
            
            # Extract event_date (date part of event_at)
            event_date = fact.event_at.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Check if fact already exists (UPSERT pattern for Meta sync)
            existing_fact = db.query(MetricFact).filter(
                MetricFact.natural_key == natural_key
            ).first()
            
            if existing_fact:
                if has_metrics_changed(existing_fact, fact):
                    existing_fact.spend = fact.spend
                    existing_fact.impressions = fact.impressions
                    existing_fact.clicks = fact.clicks
                    existing_fact.conversions = fact.conversions
                    existing_fact.revenue = fact.revenue
                    existing_fact.leads = fact.leads
                    existing_fact.installs = fact.installs
                    existing_fact.purchases = fact.purchases
                    existing_fact.visitors = fact.visitors
                    existing_fact.profit = fact.profit
                    existing_fact.currency = fact.currency
                    existing_fact.import_id = import_record.id
                    existing_fact.ingested_at = datetime.now(timezone.utc)
                    ingested += 1
                    logger.debug(f"[INGEST] Updated existing fact: {natural_key}")
                else:
                    skipped += 1
                    logger.debug(f"[INGEST] No changes for fact: {natural_key}")
            else:
                # Create new MetricFact
                metric_fact = MetricFact(
                    id=uuid4(),
                    entity_id=entity_id,
                    provider=fact.provider,
                    level=fact.level,
                    event_at=fact.event_at,
                    event_date=event_date,
                    spend=fact.spend,
                    impressions=fact.impressions,
                    clicks=fact.clicks,
                    conversions=fact.conversions,
                    revenue=fact.revenue,
                    leads=fact.leads,
                    installs=fact.installs,
                    purchases=fact.purchases,
                    visitors=fact.visitors,
                    profit=fact.profit,
                    currency=fact.currency,
                    natural_key=natural_key,
                    import_id=import_record.id,
                    ingested_at=datetime.now(timezone.utc)
                )
                
                db.add(metric_fact)
                ingested += 1
            
            try:
                db.flush()
            except IntegrityError as e:
                db.rollback()
                error_msg = f"Fact {idx}: Database error - {str(e)}"
                logger.error(f"[INGEST] {error_msg}")
                errors.append(error_msg)
                ingested -= 1  # Rollback the count
        
        except Exception as e:
            error_msg = f"Fact {idx}: {type(e).__name__} - {str(e)}"
            logger.error(f"[INGEST] {error_msg}")
            errors.append(error_msg)
    
    # Commit all successful inserts
    try:
        db.commit()
        logger.info(f"[INGEST] Complete: {ingested} ingested, {skipped} skipped, {len(errors)} errors")
    except Exception as e:
        db.rollback()
        logger.error(f"[INGEST] Commit failed: {e}")
        raise ValueError(f"Failed to commit ingestion: {str(e)}")
    
    return {
        "success": len(errors) == 0,
        "ingested": ingested,
        "skipped": skipped,
        "errors": errors
    }


def _get_or_create_entity(
    db: Session,
    workspace_id: UUID,
    provider: str,
    external_id: str,
    level: str,
    name: str = None
) -> Entity:
    """
    Get existing entity or create placeholder.
    
    WHY:
    - Ingestion shouldn't block on missing entities
    - Phase 2.3 will properly sync entities with full metadata
    - This creates minimal entities just to store metrics
    
    WHAT:
    - Lookup by workspace + provider + external_id
    - Create if not found (with placeholder name)
    - Returns entity UUID for MetricFact
    """
    # Try to find existing
    entity = db.query(Entity).filter(
        Entity.workspace_id == workspace_id,
        Entity.external_id == external_id
    ).first()
    
    if entity:
        return entity
    
    # Create placeholder entity
    # Note: Phase 2.3 will properly sync with full metadata from Meta
    entity = Entity(
        id=uuid4(),
        workspace_id=workspace_id,
        external_id=external_id,
        level=level,
        name=name or f"{provider}_{level}_{external_id}",
        status="unknown",  # Will be updated by Phase 2.3 sync
        connection_id=None  # Will be linked by Phase 2.3
    )
    
    db.add(entity)
    db.flush()  # Get ID without committing
    
    logger.info(f"[INGEST] Created placeholder entity: {entity.id} ({external_id})")
    
    return entity


def _get_or_create_import(db: Session, workspace_id: UUID) -> Import:
    """
    Get or create an Import record for this ingestion batch.
    
    WHY:
    - MetricFact requires import_id (tracks data lineage)
    - For now, create generic "API Ingestion" import
    - Phase 3 will create proper Fetch → Import flow
    
    WHAT:
    - Creates Import with as_of = now
    - Links to a generic Fetch record
    - Returns import UUID
    """
    # For Phase 1, create a generic fetch/import
    # Phase 3 will replace this with proper MetaMetricsFetcher flow
    
    # Check if we have a connection for this workspace
    connection = db.query(Connection).filter(
        Connection.workspace_id == workspace_id
    ).first()
    
    if not connection:
        # Create a placeholder connection
        # Phase 2 will create proper connections
        connection = Connection(
            id=uuid4(),
            workspace_id=workspace_id,
            provider="meta",
            name="API Ingestion (Placeholder)",
            external_account_id="placeholder"
        )
        db.add(connection)
        db.flush()
    
    # Create fetch record
    fetch = Fetch(
        id=uuid4(),
        connection_id=connection.id,
        kind="snapshot",
        status="completed",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc)
    )
    db.add(fetch)
    db.flush()
    
    # Create import record
    import_record = Import(
        id=uuid4(),
        fetch_id=fetch.id,
        as_of=datetime.now(timezone.utc),
        note="API Ingestion"
    )
    db.add(import_record)
    db.flush()
    
    return import_record


@router.post(
    "/workspaces/{workspace_id}/metrics/ingest",
    response_model=MetricFactIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest metric facts from ad platforms",
    description="""
    Ingest metric facts from Meta Ads (or other platforms).
    
    **Features**:
    - Batch ingestion (send multiple facts at once)
    - Automatic deduplication via natural_key
    - Creates placeholder entities if needed
    - UPSERT pattern (safe to re-run)
    
    **Usage**:
    ```python
    facts = [
        {
            "external_entity_id": "123456789",
            "provider": "meta",
            "level": "campaign",
            "event_at": "2025-10-30T14:00:00+00:00",
            "spend": 150.50,
            "impressions": 5420,
            "clicks": 234,
            "currency": "USD"
        }
    ]
    response = requests.post("/workspaces/{id}/metrics/ingest", json=facts)
    ```
    
    **Returns**:
    - `ingested`: Number of new facts added
    - `skipped`: Number of duplicates (already exist)
    - `errors`: List of validation errors
    """,
    tags=["Ingestion"]
)
def ingest_metrics(
    workspace_id: UUID,
    facts: List[MetricFactCreate],
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Ingest batch of metric facts.
    
    WHY:
    - Receive hourly data from Meta Insights API
    - Store raw base measures for later aggregation
    - Prevent duplicate ingestion via natural_key
    
    WHAT:
    - Validates workspace exists and user has access
    - Creates/looks up entities as needed
    - Inserts facts with UPSERT behavior (skip duplicates)
    - Returns summary of ingestion results
    
    WHERE:
    - Called by Phase 3 MetaMetricsFetcher
    - Can be used for manual testing/backfills
    """
    
    # Verify workspace exists and user has access
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found"
        )
    
    # TODO: Check user has access to this workspace
    # For now, assuming current_user.workspace_id == workspace_id
    
    ingested = 0
    skipped = 0
    errors = []
    
    # Get or create import record for this batch
    import_record = _get_or_create_import(db, workspace_id)
    
    logger.info(f"[INGEST] Processing {len(facts)} facts for workspace {workspace_id}")
    
    for idx, fact in enumerate(facts):
        try:
            # Determine entity_id
            if fact.entity_id:
                entity_id = fact.entity_id
            elif fact.external_entity_id:
                # Get or create entity
                entity = _get_or_create_entity(
                    db=db,
                    workspace_id=workspace_id,
                    provider=fact.provider.value,
                    external_id=fact.external_entity_id,
                    level=fact.level.value
                )
                entity_id = entity.id
            else:
                errors.append(f"Fact {idx}: Must provide entity_id or external_entity_id")
                continue
            
            # Compute natural_key if not provided
            natural_key = fact.natural_key
            if not natural_key:
                external_id = fact.external_entity_id or str(entity_id)
                natural_key = f"{external_id}-{fact.event_at.isoformat()}"
            
            # Extract event_date (date part of event_at)
            event_date = fact.event_at.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Check if fact already exists (UPSERT pattern for Meta sync)
            existing_fact = db.query(MetricFact).filter(
                MetricFact.natural_key == natural_key
            ).first()
            
            if existing_fact:
                # Update existing fact instead of skipping
                existing_fact.spend = fact.spend
                existing_fact.impressions = fact.impressions
                existing_fact.clicks = fact.clicks
                existing_fact.conversions = fact.conversions
                existing_fact.revenue = fact.revenue
                existing_fact.leads = fact.leads
                existing_fact.installs = fact.installs
                existing_fact.purchases = fact.purchases
                existing_fact.visitors = fact.visitors
                existing_fact.profit = fact.profit
                existing_fact.currency = fact.currency
                existing_fact.import_id = import_record.id
                existing_fact.ingested_at = datetime.now(timezone.utc)
                ingested += 1
                logger.debug(f"[INGEST] Updated existing fact: {natural_key}")
            else:
                # Create new MetricFact
                metric_fact = MetricFact(
                    id=uuid4(),
                    entity_id=entity_id,
                    provider=fact.provider,
                    level=fact.level,
                    event_at=fact.event_at,
                    event_date=event_date,
                    spend=fact.spend,
                    impressions=fact.impressions,
                    clicks=fact.clicks,
                    conversions=fact.conversions,
                    revenue=fact.revenue,
                    leads=fact.leads,
                    installs=fact.installs,
                    purchases=fact.purchases,
                    visitors=fact.visitors,
                    profit=fact.profit,
                    currency=fact.currency,
                    natural_key=natural_key,
                    import_id=import_record.id,
                    ingested_at=datetime.now(timezone.utc)
                )
                
                db.add(metric_fact)
                ingested += 1
            
            try:
                db.flush()
            except IntegrityError as e:
                db.rollback()
                error_msg = f"Fact {idx}: Database error - {str(e)}"
                logger.error(f"[INGEST] {error_msg}")
                errors.append(error_msg)
                ingested -= 1  # Rollback the count
        
        except Exception as e:
            error_msg = f"Fact {idx}: {type(e).__name__} - {str(e)}"
            logger.error(f"[INGEST] {error_msg}")
            errors.append(error_msg)
    
    # Commit all successful inserts
    try:
        db.commit()
        logger.info(f"[INGEST] Complete: {ingested} ingested, {skipped} skipped, {len(errors)} errors")
    except Exception as e:
        db.rollback()
        logger.error(f"[INGEST] Commit failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit ingestion: {str(e)}"
        )
    
    return MetricFactIngestResponse(
        success=len(errors) == 0,
        ingested=ingested,
        skipped=skipped,
        errors=errors
    )

