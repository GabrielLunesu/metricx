"""Ad platform connection management endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from .. import schemas
from ..database import get_db
from ..deps import get_current_user
from ..models import User, Connection, Workspace, ProviderEnum, WorkspaceMember, RoleEnum
from ..services.token_service import store_connection_token
from ..services.google_ads_client import GAdsClient
from redis import Redis
from rq import Queue
import os
from datetime import datetime


router = APIRouter(
    prefix="/connections",
    tags=["Connections"],
    responses={
        401: {"model": schemas.ErrorResponse, "description": "Unauthorized"},
        403: {"model": schemas.ErrorResponse, "description": "Forbidden"},
        404: {"model": schemas.ErrorResponse, "description": "Not Found"},
        500: {"model": schemas.ErrorResponse, "description": "Internal Server Error"},
    }
)


def _require_connection_permission(
    db: Session,
    user: User,
    workspace_id,
    roles=(RoleEnum.owner, RoleEnum.admin),
):
    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this workspace")
    if membership.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for this action")
    return membership


@router.get(
    "",
    response_model=schemas.ConnectionListResponse,
    summary="List ad platform connections",
    description="""
    Get all ad platform connections for the current user's workspace.
    
    Connections represent links to advertising platforms like Google Ads,
    Meta Ads, TikTok Ads, etc.
    """
)
def list_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """List connections for the current workspace."""
    _require_connection_permission(db, current_user, current_user.workspace_id, roles=(RoleEnum.owner, RoleEnum.admin, RoleEnum.viewer))
    query = db.query(Connection).filter(
        Connection.workspace_id == current_user.workspace_id
    )
    
    # Apply filters
    if provider:
        query = query.filter(Connection.provider == provider)
    if status:
        query = query.filter(Connection.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    connections = query.offset(offset).limit(limit).all()
    
    return schemas.ConnectionListResponse(
        connections=connections,
        total=total
    )


@router.post(
    "/google/from-env",
    response_model=schemas.ConnectionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create/ensure Google Ads connection from environment",
    description="""
    Creates a Google Ads connection for the current workspace using env vars:
    - GOOGLE_CUSTOMER_ID (required)
    - GOOGLE_REFRESH_TOKEN (required)
    - GOOGLE_LOGIN_CUSTOMER_ID (optional)
    - GOOGLE_DEVELOPER_TOKEN / GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET (required by SDK)

    Stores the refresh token encrypted. If a connection already exists, updates
    its token. Fetches timezone/currency when possible.
    """
)
def ensure_google_connection_from_env(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_connection_permission(db, current_user, current_user.workspace_id)

    customer_id = os.getenv("GOOGLE_CUSTOMER_ID")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    developer_token = os.getenv("GOOGLE_DEVELOPER_TOKEN")
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    # Basic validation and clear error messaging
    missing = []
    if not customer_id:
        missing.append("GOOGLE_CUSTOMER_ID")
    if not refresh_token:
        missing.append("GOOGLE_REFRESH_TOKEN")
    for k, v in {"GOOGLE_DEVELOPER_TOKEN": developer_token, "GOOGLE_CLIENT_ID": client_id, "GOOGLE_CLIENT_SECRET": client_secret}.items():
        if not v:
            missing.append(k)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing env vars: {', '.join(sorted(set(missing)))}")

    # Normalize ID to digits only for storage; UI can format with dashes
    norm_id = "".join(ch for ch in customer_id if ch.isdigit())

    # Upsert connection
    connection = db.query(Connection).filter(
        Connection.workspace_id == current_user.workspace_id,
        Connection.provider == ProviderEnum.google,
        Connection.external_account_id == norm_id,
    ).first()

    if connection is None:
        connection = Connection(
            provider=ProviderEnum.google,
            external_account_id=norm_id,
            name=f"Google Ads - {norm_id}",
            status="active",
            connected_at=datetime.utcnow(),
            workspace_id=current_user.workspace_id,
        )
        db.add(connection)
        db.flush()

    # Store encrypted refresh token; access token remains nullable
    store_connection_token(
        db,
        connection,
        access_token=None,
        refresh_token=refresh_token,
        expires_at=None,
        scope="google-refresh-token",
        ad_account_ids=[norm_id],
    )

    # Attempt to fetch timezone/currency for nicer display (best-effort)
    try:
        meta = GAdsClient().get_customer_metadata(norm_id)
        tz = meta.get("time_zone")
        cur = meta.get("currency_code")
        if tz:
            connection.timezone = tz
        if cur:
            connection.currency_code = cur
        db.flush()
    except Exception:
        # Non-fatal; leave as None
        pass

    db.commit()
    db.refresh(connection)
    return connection


@router.post(
    "/meta/from-env",
    response_model=schemas.ConnectionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create/ensure Meta Ads connection from environment",
    description="""
    Creates a Meta Ads connection for the current workspace using env vars:
    - META_ACCESS_TOKEN (required)
    - META_AD_ACCOUNT_ID (required)

    Stores the access token encrypted. If a connection already exists, updates
    its token.
    """
)
def ensure_meta_connection_from_env(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_connection_permission(db, current_user, current_user.workspace_id)

    access_token = os.getenv("META_ACCESS_TOKEN")
    ad_account_id = os.getenv("META_AD_ACCOUNT_ID")
    
    if not access_token:
        raise HTTPException(status_code=400, detail="Missing env var: META_ACCESS_TOKEN")
    if not ad_account_id:
        raise HTTPException(status_code=400, detail="Missing env var: META_AD_ACCOUNT_ID")
    
    # Upsert connection
    connection = db.query(Connection).filter(
        Connection.workspace_id == current_user.workspace_id,
        Connection.provider == ProviderEnum.meta,
        Connection.external_account_id == ad_account_id,
    ).first()
    
    if connection is None:
        connection = Connection(
            provider=ProviderEnum.meta,
            external_account_id=ad_account_id,
            name=f"Meta Ads - {ad_account_id}",
            status="active",
            connected_at=datetime.utcnow(),
            workspace_id=current_user.workspace_id,
        )
        db.add(connection)
        db.flush()
    
    # Store encrypted access token
    store_connection_token(
        db,
        connection,
        access_token=access_token,
        refresh_token=None,
        expires_at=None,
        scope="system-user",
        ad_account_ids=[ad_account_id],
    )
    
    db.commit()
    db.refresh(connection)
    return connection


def _get_connection_for_workspace(
    db: Session,
    workspace_id: UUID,
    connection_id: UUID,
) -> Connection:
    connection = (
        db.query(Connection)
        .filter(
            Connection.id == connection_id,
            Connection.workspace_id == workspace_id,
        )
        .first()
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connection


@router.post(
    "/{connection_id}/sync-now",
    response_model=schemas.SyncJobResponse,
    summary="Enqueue an immediate sync job for this connection",
)
def enqueue_sync_job(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_connection_permission(db, current_user, current_user.workspace_id)
    connection = _get_connection_for_workspace(
        db=db,
        workspace_id=current_user.workspace_id,
        connection_id=connection_id,
    )

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    queue = Queue("sync_jobs", connection=Redis.from_url(redis_url))
    job = queue.enqueue(
        "app.workers.sync_worker.process_sync_job",
        str(connection.id),
        str(connection.workspace_id),
    )

    connection.sync_status = "queued"
    connection.last_sync_error = None
    db.commit()

    return schemas.SyncJobResponse(job_id=job.id, status="queued")


VALID_SYNC_FREQUENCIES = {
    "manual",
    "5min",
    "10min",
    "30min",
    "hourly",
    "daily",
    # "realtime",  # 30s interval reserved for power users (see docs/REALTIME_SYNC_IMPLEMENTATION_SUMMARY.md)
}


@router.patch(
    "/{connection_id}/sync-frequency",
    response_model=schemas.ConnectionSyncStatus,
    summary="Update automated sync frequency",
)
def update_sync_frequency(
    connection_id: UUID,
    payload: schemas.SyncFrequencyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_connection_permission(db, current_user, current_user.workspace_id)
    if payload.sync_frequency not in VALID_SYNC_FREQUENCIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sync_frequency. Allowed: {', '.join(sorted(VALID_SYNC_FREQUENCIES))}",
        )

    connection = _get_connection_for_workspace(
        db=db,
        workspace_id=current_user.workspace_id,
        connection_id=connection_id,
    )

    connection.sync_frequency = payload.sync_frequency
    db.commit()
    db.refresh(connection)

    return schemas.ConnectionSyncStatus.model_validate(connection)


@router.get(
    "/{connection_id}/sync-status",
    response_model=schemas.ConnectionSyncStatus,
    summary="Get sync status for a connection",
)
def get_sync_status(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connection = _get_connection_for_workspace(
        db=db,
        workspace_id=current_user.workspace_id,
        connection_id=connection_id,
    )
    return schemas.ConnectionSyncStatus.model_validate(connection)


@router.post(
    "",
    response_model=schemas.ConnectionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create new connection",
    description="""
    Create a new connection to an advertising platform.
    
    This establishes a link between your workspace and an external
    ad platform account (Google Ads, Meta, TikTok, etc.).
    """
)
def create_connection(
    payload: schemas.ConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new ad platform connection."""
    _require_connection_permission(db, current_user, current_user.workspace_id)
    
    # Check if connection with same external_account_id already exists
    existing = db.query(Connection).filter(
        Connection.workspace_id == current_user.workspace_id,
        Connection.provider == payload.provider,
        Connection.external_account_id == payload.external_account_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection to {payload.provider} account {payload.external_account_id} already exists"
        )
    
    connection = Connection(
        **payload.model_dump(),
        workspace_id=current_user.workspace_id
    )
    
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


@router.get(
    "/{connection_id}",
    response_model=schemas.ConnectionOut,
    summary="Get connection details",
    description="""
    Get detailed information about a specific ad platform connection.
    """
)
def get_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get connection by ID."""
    _require_connection_permission(db, current_user, current_user.workspace_id, roles=(RoleEnum.owner, RoleEnum.admin, RoleEnum.viewer))
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.workspace_id == current_user.workspace_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    return connection


@router.put(
    "/{connection_id}",
    response_model=schemas.ConnectionOut,
    summary="Update connection",
    description="""
    Update connection information such as name or status.
    
    Only workspace owners and admins can update connections.
    """
)
def update_connection(
    connection_id: UUID,
    payload: schemas.ConnectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update connection."""
    _require_connection_permission(db, current_user, current_user.workspace_id)
    
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.workspace_id == current_user.workspace_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Update fields
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(connection, field, value)
    
    db.commit()
    db.refresh(connection)
    return connection


@router.delete(
    "/{connection_id}",
    response_model=schemas.SuccessResponse,
    summary="Delete connection",
    description="""
    Delete an ad platform connection.
    
    **Warning**: This will also delete all associated entities, metrics,
    and other data linked to this connection. This action cannot be undone.
    
    Only workspace owners can delete connections.
    """
)
def delete_connection(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete connection and all associated data."""
    import logging
    from app.models import (
        Entity, MetricFact, Token, Fetch, Import, Pnl,
        ShopifyShop, ShopifyProduct, ShopifyCustomer, ShopifyOrder, ShopifyOrderLineItem,
        PixelEvent, CustomerJourney, JourneyTouchpoint, Attribution,
    )

    logger = logging.getLogger(__name__)
    
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.workspace_id == current_user.workspace_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )

    _require_connection_permission(db, current_user, connection.workspace_id)
    
    logger.info(f"[DELETE_CONNECTION] Starting deletion of connection {connection_id} ({connection.name})")
    
    try:
        # Get all entity IDs and fetch IDs for this connection
        entity_ids = [e.id for e in db.query(Entity.id).filter(
            Entity.connection_id == connection_id
        ).all()]
        
        fetch_ids = [f.id for f in db.query(Fetch.id).filter(
            Fetch.connection_id == connection_id
        ).all()]
        
        import_ids = []
        if fetch_ids:
            import_ids = [imp.id for imp in db.query(Import.id).filter(
                Import.fetch_id.in_(fetch_ids)
            ).all()]
        
        # 1. Delete P&L snapshots that reference these entities
        if entity_ids:
            pnl_count = db.query(Pnl).filter(
                Pnl.entity_id.in_(entity_ids)
            ).delete(synchronize_session=False)
            logger.info(f"[DELETE_CONNECTION] Deleted {pnl_count} P&L snapshots")
            db.flush()

        # 1b. Delete Shopify-related data if this is a Shopify connection
        shopify_shop = db.query(ShopifyShop).filter(
            ShopifyShop.connection_id == connection_id
        ).first()

        if shopify_shop:
            shop_id = shopify_shop.id
            logger.info(f"[DELETE_CONNECTION] Deleting Shopify data for shop {shop_id}")

            # Get order IDs for this shop
            order_ids = [o.id for o in db.query(ShopifyOrder.id).filter(
                ShopifyOrder.shop_id == shop_id
            ).all()]

            # Delete attributions referencing these orders
            if order_ids:
                attr_count = db.query(Attribution).filter(
                    Attribution.shopify_order_id.in_(order_ids)
                ).delete(synchronize_session=False)
                logger.info(f"[DELETE_CONNECTION] Deleted {attr_count} attributions")
                db.flush()

            # Delete order line items
            if order_ids:
                line_count = db.query(ShopifyOrderLineItem).filter(
                    ShopifyOrderLineItem.order_id.in_(order_ids)
                ).delete(synchronize_session=False)
                logger.info(f"[DELETE_CONNECTION] Deleted {line_count} order line items")
                db.flush()

            # Delete orders
            order_count = db.query(ShopifyOrder).filter(
                ShopifyOrder.shop_id == shop_id
            ).delete(synchronize_session=False)
            logger.info(f"[DELETE_CONNECTION] Deleted {order_count} orders")
            db.flush()

            # Delete customers
            customer_count = db.query(ShopifyCustomer).filter(
                ShopifyCustomer.shop_id == shop_id
            ).delete(synchronize_session=False)
            logger.info(f"[DELETE_CONNECTION] Deleted {customer_count} customers")
            db.flush()

            # Delete products
            product_count = db.query(ShopifyProduct).filter(
                ShopifyProduct.shop_id == shop_id
            ).delete(synchronize_session=False)
            logger.info(f"[DELETE_CONNECTION] Deleted {product_count} products")
            db.flush()

            # Delete shop
            db.delete(shopify_shop)
            logger.info(f"[DELETE_CONNECTION] Deleted ShopifyShop")
            db.flush()

        # 1c. Delete attribution-related data for this workspace
        # (PixelEvents and Journeys are workspace-level, not connection-level,
        # so we only delete them if this was the only Shopify connection)
        # For now, leave pixel_events and journeys - they're workspace-level data

        # 2. Delete metric facts that reference these entities OR imports
        # MetricFact has FK to both Entity and Import, so delete all facts related to this connection
        fact_count = 0
        if entity_ids:
            # Delete facts by entity_id
            fact_count += db.query(MetricFact).filter(
                MetricFact.entity_id.in_(entity_ids)
            ).delete(synchronize_session=False)
        if import_ids:
            # Delete facts by import_id (in case some facts don't have entity_id)
            fact_count += db.query(MetricFact).filter(
                MetricFact.import_id.in_(import_ids)
            ).delete(synchronize_session=False)
        if fact_count > 0:
            logger.info(f"[DELETE_CONNECTION] Deleted {fact_count} metric facts")
            db.flush()
        
        # 3. Delete entities (no longer referenced by metric facts or P&L)
        entity_count = db.query(Entity).filter(
            Entity.connection_id == connection_id
        ).delete(synchronize_session=False)
        logger.info(f"[DELETE_CONNECTION] Deleted {entity_count} entities")
        db.flush()
        
        # 4. Delete imports (no longer referenced by metric facts)
        if import_ids:
            import_count = db.query(Import).filter(
                Import.id.in_(import_ids)
            ).delete(synchronize_session=False)
            logger.info(f"[DELETE_CONNECTION] Deleted {import_count} imports")
            db.flush()
        
        # 5. Delete fetches (no longer referenced by imports)
        if fetch_ids:
            fetch_count = db.query(Fetch).filter(
                Fetch.id.in_(fetch_ids)
            ).delete(synchronize_session=False)
            logger.info(f"[DELETE_CONNECTION] Deleted {fetch_count} fetches")
            db.flush()
        
        # 6. Store token_id before deleting connection (need to nullify FK first)
        token_id_to_delete = connection.token_id
        
        # 7. Delete the connection first (this removes the FK reference)
        db.delete(connection)
        db.flush()
        
        # 8. Now delete the token if it exists (FK reference is gone)
        if token_id_to_delete:
            token_count = db.query(Token).filter(
                Token.id == token_id_to_delete
            ).delete(synchronize_session=False)
            logger.info(f"[DELETE_CONNECTION] Deleted {token_count} token(s)")
            db.flush()
        
        db.commit()
        
        logger.info(f"[DELETE_CONNECTION] Successfully deleted connection {connection_id} and all associated data")
        
        return schemas.SuccessResponse(detail="Connection deleted successfully")
        
    except Exception as e:
        db.rollback()
        logger.exception(f"[DELETE_CONNECTION] Failed to delete connection {connection_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete connection: {str(e)}"
        )


# =============================================================================
# META PIXEL SETTINGS (for CAPI)
# =============================================================================

from pydantic import BaseModel

class MetaPixelUpdate(BaseModel):
    """Request body for updating Meta Pixel ID."""
    pixel_id: str


@router.patch(
    "/{connection_id}/meta-pixel",
    response_model=schemas.SuccessResponse,
    summary="Set Meta Pixel ID for CAPI",
    description="""
    Set the Meta Pixel ID for a Meta connection to enable server-side
    conversion tracking via Conversions API (CAPI).

    The Pixel ID can be found in Meta Events Manager.
    """
)
async def update_meta_pixel_id(
    connection_id: UUID,
    payload: MetaPixelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update Meta Pixel ID for CAPI integration.

    WHAT: Sets the meta_pixel_id on a Meta connection
    WHY: Required for sending purchase events via CAPI

    Args:
        connection_id: The Meta connection UUID
        payload: Contains the pixel_id to set

    Returns:
        Success message

    Raises:
        404: Connection not found
        400: Connection is not a Meta connection
        403: User doesn't have permission
    """
    # Find the connection
    connection = db.query(Connection).filter(Connection.id == connection_id).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )

    # Check permission
    _require_connection_permission(db, current_user, connection.workspace_id)

    # Verify it's a Meta connection
    if connection.provider != ProviderEnum.meta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for Meta connections"
        )

    # Update pixel ID
    connection.meta_pixel_id = payload.pixel_id
    db.commit()

    logger.info(
        f"[META_PIXEL] Updated pixel_id for connection {connection_id}",
        extra={"pixel_id": payload.pixel_id}
    )

    return schemas.SuccessResponse(detail=f"Meta Pixel ID set to {payload.pixel_id}")


@router.get(
    "/{connection_id}/meta-pixel",
    summary="Get Meta Pixel ID",
    description="Get the currently configured Meta Pixel ID for a connection."
)
async def get_meta_pixel_id(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Meta Pixel ID for a connection.

    Args:
        connection_id: The Meta connection UUID

    Returns:
        Dict with pixel_id (or null if not set)
    """
    connection = db.query(Connection).filter(Connection.id == connection_id).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )

    # Check permission (allow all roles to read)
    _require_connection_permission(
        db, current_user, connection.workspace_id,
        roles=(RoleEnum.owner, RoleEnum.admin, RoleEnum.member)
    )

    return {
        "connection_id": str(connection_id),
        "provider": connection.provider.value,
        "meta_pixel_id": connection.meta_pixel_id,
    }


# =============================================================================
# GOOGLE CONVERSION ACTION SETTINGS
# =============================================================================

class GoogleConversionActionUpdate(BaseModel):
    """Request body for updating Google Conversion Action ID."""
    conversion_action_id: str


@router.patch(
    "/{connection_id}/google-conversion-action",
    response_model=schemas.SuccessResponse,
    summary="Set Google Conversion Action ID",
    description="""
    Set the Google Ads Conversion Action ID for offline conversion uploads.

    The Conversion Action ID can be found in Google Ads under:
    Tools & Settings > Measurement > Conversions > [Your conversion] > Details
    """
)
async def update_google_conversion_action_id(
    connection_id: UUID,
    payload: GoogleConversionActionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update Google Conversion Action ID for offline conversions.

    WHAT: Sets the google_conversion_action_id on a Google connection
    WHY: Required for uploading purchase conversions to Google Ads

    Args:
        connection_id: The Google connection UUID
        payload: Contains the conversion_action_id to set

    Returns:
        Success message

    Raises:
        404: Connection not found
        400: Connection is not a Google connection
        403: User doesn't have permission
    """
    connection = db.query(Connection).filter(Connection.id == connection_id).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )

    _require_connection_permission(db, current_user, connection.workspace_id)

    if connection.provider != ProviderEnum.google:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for Google connections"
        )

    connection.google_conversion_action_id = payload.conversion_action_id
    db.commit()

    logger.info(
        f"[GOOGLE_CONV] Updated conversion_action_id for connection {connection_id}",
        extra={"conversion_action_id": payload.conversion_action_id}
    )

    return schemas.SuccessResponse(
        detail=f"Google Conversion Action ID set to {payload.conversion_action_id}"
    )


@router.get(
    "/{connection_id}/google-conversion-action",
    summary="Get Google Conversion Action ID",
    description="Get the currently configured Google Conversion Action ID for a connection."
)
async def get_google_conversion_action_id(
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Google Conversion Action ID for a connection.

    Args:
        connection_id: The Google connection UUID

    Returns:
        Dict with conversion_action_id (or null if not set)
    """
    connection = db.query(Connection).filter(Connection.id == connection_id).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )

    _require_connection_permission(
        db, current_user, connection.workspace_id,
        roles=(RoleEnum.owner, RoleEnum.admin, RoleEnum.member)
    )

    return {
        "connection_id": str(connection_id),
        "provider": connection.provider.value,
        "google_conversion_action_id": connection.google_conversion_action_id,
    }
