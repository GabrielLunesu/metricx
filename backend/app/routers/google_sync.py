"""Google Ads synchronization endpoints.

WHAT:
    Thin HTTP wrappers for Google sync services (entities + metrics).

WHY:
    - Routers focus on auth and request parsing.
    - Business logic is centralized in service layer for reuse by workers.

REFERENCES:
    - backend/app/services/google_sync_service.py
    - docs/living-docs/GOOGLE_INTEGRATION_STATUS.MD
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
from app.services.google_sync_service import (
    sync_google_entities,
    sync_google_metrics,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/connections/{connection_id}",
    tags=["Google Sync"],
)


@router.post("/sync-google-entities", response_model=EntitySyncResponse)
async def sync_entities(
    workspace_id: UUID,
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntitySyncResponse:
    """Sync Google Ads hierarchy (delegates to service layer)."""
    logger.info(
        "[GOOGLE_SYNC] HTTP entity sync requested: workspace=%s connection=%s",
        workspace_id,
        connection_id,
    )
    return sync_google_entities(
        db=db,
        workspace_id=workspace_id,
        connection_id=connection_id,
    )


@router.post("/sync-google-metrics", response_model=MetricsSyncResponse)
async def sync_metrics(
    workspace_id: UUID,
    connection_id: UUID,
    request: MetricsSyncRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetricsSyncResponse:
    """Sync Google Ads metrics (delegates to service layer)."""
    logger.info(
        "[GOOGLE_SYNC] HTTP metrics sync requested: workspace=%s connection=%s",
        workspace_id,
        connection_id,
    )
    return sync_google_metrics(
        db=db,
        workspace_id=workspace_id,
        connection_id=connection_id,
        request=request,
    )

