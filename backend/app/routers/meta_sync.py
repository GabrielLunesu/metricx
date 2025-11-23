"""Meta Ads synchronization endpoints.

WHAT:
    Thin HTTP wrappers for Meta sync services.

WHY:
    - Routers handle auth + request parsing only.
    - Business logic reused by both HTTP calls and background workers.

REFERENCES:
    - backend/app/services/meta_sync_service.py
    - docs/living-docs/REALTIME_SYNC_STATUS.md
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import (
    EntitySyncResponse,
    MetricsSyncRequest,
    MetricsSyncResponse,
)
from app.services.meta_sync_service import (
    sync_meta_entities,
    sync_meta_metrics,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/connections/{connection_id}",
    tags=["Meta Sync"],
)


@router.post("/sync-entities", response_model=EntitySyncResponse)
async def sync_entities(
    workspace_id: UUID,
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntitySyncResponse:
    """Sync Meta campaigns/adsets/ads (delegates to service layer)."""
    logger.info(
        "[META_SYNC] HTTP entity sync requested: workspace=%s connection=%s",
        workspace_id,
        connection_id,
    )
    return sync_meta_entities(
                    db=db,
        workspace_id=workspace_id,
        connection_id=connection_id,
    )


@router.post("/sync-metrics", response_model=MetricsSyncResponse)
async def sync_metrics(
    workspace_id: UUID,
    connection_id: UUID,
    request: MetricsSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetricsSyncResponse:
    """Sync Meta insights (delegates to service layer)."""
    logger.info(
        "[META_SYNC] HTTP metrics sync requested: workspace=%s connection=%s",
        workspace_id,
        connection_id,
    )
    return sync_meta_metrics(
        db=db,
                                workspace_id=workspace_id,
        connection_id=connection_id,
        request=request,
        )

