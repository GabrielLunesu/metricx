"""Workspace management endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from .. import schemas
from ..database import get_db
from ..deps import get_current_user
from ..models import User, Workspace, Fetch, ComputeRun, MetricFact, Entity, LevelEnum, Connection


router = APIRouter(
    prefix="/workspaces",
    tags=["Workspaces"],
    responses={
        401: {"model": schemas.ErrorResponse, "description": "Unauthorized"},
        403: {"model": schemas.ErrorResponse, "description": "Forbidden"},
        404: {"model": schemas.ErrorResponse, "description": "Not Found"},
        500: {"model": schemas.ErrorResponse, "description": "Internal Server Error"},
    }
)


@router.get(
    "/",
    response_model=schemas.WorkspaceListResponse,
    summary="List workspaces",
    description="""
    Get a list of all workspaces accessible to the current user.
    
    Currently, users can only access their own workspace, but this will be
    extended in the future to support multi-workspace access.
    """
)
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all workspaces accessible to the current user."""
    # For now, users only have access to their own workspace
    # TODO: Implement multi-workspace access with proper permissions
    workspace = db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return schemas.WorkspaceListResponse(
        workspaces=[workspace],
        total=1
    )


@router.get(
    "/{workspace_id}",
    response_model=schemas.WorkspaceOut,
    summary="Get workspace details",
    description="""
    Get detailed information about a specific workspace.
    
    Users can only access workspaces they belong to.
    """
)
def get_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get workspace by ID."""
    # Check if user has access to this workspace
    if current_user.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this workspace"
        )
    
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return workspace


@router.put(
    "/{workspace_id}",
    response_model=schemas.WorkspaceOut,
    summary="Update workspace",
    description="""
    Update workspace information.
    
    Only workspace owners and admins can update workspace details.
    """
)
def update_workspace(
    workspace_id: UUID,
    payload: schemas.WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update workspace."""
    # Check if user has access to this workspace
    if current_user.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this workspace"
        )
    
    # Check if user has admin rights
    if current_user.role.value not in ["Owner", "Admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace owners and admins can update workspace details"
        )
    
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Update fields
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workspace, field, value)
    
    db.commit()
    db.refresh(workspace)
    return workspace


@router.get(
    "/{workspace_id}/users",
    response_model=List[schemas.UserOut],
    summary="List workspace users",
    description="""
    Get all users in a workspace.
    
    Only workspace members can view the user list.
    """
)
def list_workspace_users(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all users in a workspace."""
    # Check if user has access to this workspace
    if current_user.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this workspace"
        )
    
    # Get all users in the workspace
    users = db.query(User).filter(User.workspace_id == workspace_id).all()
    return users


@router.get(
    "/{workspace_id}/info",
    response_model=schemas.WorkspaceInfo,
    summary="Get workspace info for sidebar",
    description="""
    Get workspace summary for sidebar.
    
    Returns workspace name and last sync timestamp.
    Last sync is determined by:
    - First priority: latest successful Fetch (raw data import)
    - Fallback: latest successful ComputeRun (aggregated snapshot)
    
    No authentication required since this is public info for the sidebar.
    """
)
def get_workspace_info(
    workspace_id: str,
    db: Session = Depends(get_db)
):
    """
    Get workspace summary for sidebar.
    Logic for last_sync:
    - First try latest successful Fetch (freshest import timestamp).
    - If no Fetch exists, fallback to latest successful ComputeRun (aggregated snapshot).
    """
    # Convert string ID to UUID for query
    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )
    
    # Get workspace
    ws = db.query(Workspace).filter(Workspace.id == workspace_uuid).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    # Latest Fetch (status=success)
    # Note: Fetch connects to Connection which has workspace_id
    last_fetch = (
        db.query(Fetch)
        .join(Fetch.connection)
        .filter(Fetch.connection.has(workspace_id=workspace_uuid))
        .filter(Fetch.status == "success")
        .order_by(desc(Fetch.finished_at))
        .first()
    )

    # Fallback: latest ComputeRun
    last_compute = (
        db.query(ComputeRun)
        .filter(ComputeRun.workspace_id == workspace_uuid)
        .filter(ComputeRun.status == "success")
        .order_by(desc(ComputeRun.computed_at))
        .first()
    )

    # Determine last sync time
    last_sync = None
    if last_fetch and last_fetch.finished_at:
        last_sync = last_fetch.finished_at
    elif last_compute and last_compute.computed_at:
        last_sync = last_compute.computed_at

    return schemas.WorkspaceInfo(
        id=str(ws.id),
        name=ws.name,
        last_sync=last_sync
    )


@router.get(
    "/{workspace_id}/providers",
    summary="Get available providers",
    description="""
    Get distinct ad platforms that have metric data in this workspace.
    
    Returns a list of providers (google, meta, tiktok, other) that have
    at least one MetricFact record in the workspace.
    
    Used for dynamic provider filter buttons in Analytics page.
    """
)
def get_workspace_providers(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get distinct providers with data in this workspace."""
    # Convert string ID to UUID
    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )
    
    # Check user has access to this workspace
    if current_user.workspace_id != workspace_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this workspace"
        )
    
    # Providers from metric facts
    providers_fact = (
        db.query(MetricFact.provider)
        .join(Entity, Entity.id == MetricFact.entity_id)
        .filter(Entity.workspace_id == workspace_uuid)
        .distinct()
        .all()
    )
    fact_list = [p[0].value for p in providers_fact if p[0]]

    # Providers from connections (include those without facts yet)
    providers_conn = (
        db.query(Connection.provider)
        .filter(Connection.workspace_id == workspace_uuid)
        .distinct()
        .all()
    )
    conn_list = [p[0].value for p in providers_conn if p[0]]

    merged = sorted(list(set(fact_list) | set(conn_list)))
    return {"providers": merged}


@router.get(
    "/{workspace_id}/campaigns",
    summary="Get workspace campaigns",
    description="""
    Get campaigns in this workspace for dropdown filtering.
    
    Query params:
    - provider: Filter campaigns by provider (optional)
    - entity_status: Filter by status (default: active)
    
    Used for campaign dropdown in Analytics page chart section.
    """
)
def get_workspace_campaigns(
    workspace_id: str,
    provider: str = None,
    entity_status: str = "active",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get campaigns for dropdown filtering."""
    # Convert string ID to UUID
    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )
    
    # Check user has access to this workspace
    if current_user.workspace_id != workspace_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this workspace"
        )
    
    # Build query for campaigns
    query = (
        db.query(Entity)
        .options(joinedload(Entity.connection))
        .filter(Entity.workspace_id == workspace_uuid)
        .filter(Entity.level == LevelEnum.campaign)
    )
    
    # Filter by entity status if provided
    if entity_status:
        query = query.filter(Entity.status == entity_status)
    
    # Filter by provider if provided
    if provider and provider != "all":
        query = query.join(MetricFact, MetricFact.entity_id == Entity.id)
        query = query.filter(MetricFact.provider == provider)
    
    # Execute query and get distinct campaigns
    campaigns = query.distinct().all()
    
    return {
        "campaigns": [
            {
                "id": str(c.id),
                "name": c.name,
                "status": c.status,  # Already a string, not an enum
                "platform": c.connection.provider.value if c.connection and c.connection.provider else None
            }
            for c in campaigns
        ]
    }
