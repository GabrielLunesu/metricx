"""Workspace management endpoints."""

from datetime import datetime

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from .. import schemas
from ..database import get_db
from ..deps import get_current_user
from ..models import (
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceInvite,
    Fetch,
    ComputeRun,
    MetricFact,
    Entity,
    LevelEnum,
    Connection,
    RoleEnum,
    InviteStatusEnum,
)
from sqlalchemy.orm import joinedload


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


def _require_membership(
    db: Session,
    user: User,
    workspace_id: UUID,
    roles: List[RoleEnum] | None = None,
):
    membership = (
        db.query(WorkspaceMember)
        .options(joinedload(WorkspaceMember.workspace))
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this workspace",
        )
    if roles and membership.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this workspace",
        )
    return membership


@router.get(
    "/active",
    response_model=schemas.ActiveWorkspaceResponse,
    summary="Get active workspace",
    description="""
    Get the current user's active workspace context.

    This endpoint is called immediately after login to hydrate the frontend
    with workspace context. The user's active workspace is stored in users.workspace_id.

    REFERENCES:
        - ui/lib/workspace.js (getActiveWorkspace, currentUser)
        - backend/app/deps.py (get_current_user validates Clerk JWT)
    """
)
async def get_active_workspace(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's active workspace for frontend context.

    WHAT: Returns workspace_id, workspace_name, and user info
    WHY: Frontend needs this to hydrate after Clerk login

    Returns:
        ActiveWorkspaceResponse with workspace and user details
    """
    # Get the workspace details
    workspace = db.query(Workspace).filter(
        Workspace.id == current_user.workspace_id
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active workspace not found. Please contact support."
        )

    return schemas.ActiveWorkspaceResponse(
        workspace_id=str(workspace.id),
        workspace_name=workspace.name,
        user_id=str(current_user.id),
        user_name=current_user.name,
        user_email=current_user.email,
    )


@router.get(
    "",
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
    memberships = (
        db.query(WorkspaceMember)
        .options(joinedload(WorkspaceMember.workspace))
        .filter(
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.status == "active",
        )
        .all()
    )

    items: List[schemas.WorkspaceWithRole] = []
    for m in memberships:
        if not m.workspace:
            continue
        items.append(
            schemas.WorkspaceWithRole(
                id=m.workspace.id,
                name=m.workspace.name,
                created_at=m.workspace.created_at,
                role=m.role,
                status=m.status,
                is_active=(m.workspace.id == current_user.workspace_id),
            )
        )

    return schemas.WorkspaceListResponse(
        workspaces=items,
        total=len(items)
    )


@router.post(
    "",
    response_model=schemas.WorkspaceWithRole,
    status_code=status.HTTP_201_CREATED,
    summary="Create workspace",
    description="Create a new workspace and set it as the active workspace for the current user (owner).",
)
def create_workspace(
    payload: schemas.WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = Workspace(name=payload.name)
    db.add(workspace)
    db.flush()

    # Enforce single owner: creator becomes the sole owner if none exists yet
    existing_owner = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.role == RoleEnum.owner,
            WorkspaceMember.status == "active",
        )
        .first()
    )
    if existing_owner:
        raise HTTPException(status_code=400, detail="Workspace already has an owner")

    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=RoleEnum.owner,
        status="active",
    )
    db.add(membership)

    # Update active workspace context and role for compatibility
    current_user.workspace_id = workspace.id
    current_user.role = RoleEnum.owner

    db.commit()
    db.refresh(workspace)
    db.refresh(current_user)

    return schemas.WorkspaceWithRole(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
        role=membership.role,
        status=membership.status,
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
    _require_membership(db, current_user, workspace_id)

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
    _require_membership(db, current_user, workspace_id, roles=[RoleEnum.owner, RoleEnum.admin])

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
    response_model=List[schemas.WorkspaceMemberOut],
    summary="List workspace members",
    description="List members with roles for a workspace (members only).",
)
def list_workspace_users(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_membership(db, current_user, workspace_id)
    members = (
        db.query(WorkspaceMember)
        .options(joinedload(WorkspaceMember.user), joinedload(WorkspaceMember.workspace))
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.status == "active",
        )
        .all()
    )
    for m in members:
        m.workspace_name = m.workspace.name if m.workspace else None
        m.user_email = m.user.email if m.user else None
        m.user_name = m.user.name if m.user else None
    return members


@router.post(
    "/{workspace_id}/members",
    response_model=schemas.WorkspaceMemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add workspace member",
)
def add_workspace_member(
    workspace_id: UUID,
    payload: schemas.WorkspaceMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_membership(db, current_user, workspace_id, roles=[RoleEnum.owner])

    if payload.role == RoleEnum.owner:
        raise HTTPException(status_code=400, detail="Only one owner per workspace")

    target_user = db.query(User).filter(User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == payload.user_id,
            WorkspaceMember.status == "active",
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User already in workspace")

    membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=payload.user_id,
        role=payload.role,
        status="active",
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    membership.workspace_name = membership.workspace.name if membership.workspace else None
    return membership


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=schemas.WorkspaceMemberOut,
    summary="Update member role",
)
def update_member_role(
    workspace_id: UUID,
    user_id: UUID,
    payload: schemas.WorkspaceMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_membership(db, current_user, workspace_id, roles=[RoleEnum.owner])

    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found")

    if membership.role == RoleEnum.owner:
        raise HTTPException(status_code=400, detail="Cannot change owner role")

    if payload.role == RoleEnum.owner:
        raise HTTPException(status_code=400, detail="Only one owner allowed")

    membership.role = payload.role
    db.commit()
    db.refresh(membership)
    membership.workspace_name = membership.workspace.name if membership.workspace else None
    return membership


@router.delete(
    "/{workspace_id}/members/{user_id}",
    response_model=schemas.SuccessResponse,
    summary="Remove workspace member",
)
def remove_member(
    workspace_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_membership(db, current_user, workspace_id, roles=[RoleEnum.owner])

    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found")

    if membership.role == RoleEnum.owner:
        raise HTTPException(status_code=400, detail="Cannot remove the owner")

    membership.status = "removed"
    db.commit()
    return schemas.SuccessResponse(status="ok")


@router.post(
    "/{workspace_id}/switch",
    response_model=schemas.UserOut,
    summary="Switch active workspace",
    description="Set the active workspace for the current session/user.",
)
def switch_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = _require_membership(db, current_user, workspace_id)

    current_user.workspace_id = workspace_id
    current_user.role = membership.role
    db.commit()
    db.refresh(current_user)

    # Hydrate via auth helper
    from .auth import _hydrate_user_context  # lazy import to avoid circular

    hydrated = _hydrate_user_context(db, current_user)
    return hydrated


@router.post(
    "/{workspace_id}/invites",
    response_model=schemas.WorkspaceInviteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create invite for existing user",
)
def create_invite(
    workspace_id: UUID,
    payload: schemas.WorkspaceInviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_membership(db, current_user, workspace_id, roles=[RoleEnum.owner])

    if payload.role == RoleEnum.owner:
        raise HTTPException(status_code=400, detail="Cannot invite additional owners")

    target_user = db.query(User).filter(User.email == payload.email).first()
    if not target_user:
        raise HTTPException(status_code=400, detail="Invitee must already have an account")

    # Already a member?
    existing_member = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == target_user.id,
            WorkspaceMember.status == "active",
        )
        .first()
    )
    if existing_member:
        raise HTTPException(status_code=400, detail="User is already a member")

    existing_invite = (
        db.query(WorkspaceInvite)
        .filter(
            WorkspaceInvite.workspace_id == workspace_id,
            WorkspaceInvite.email == payload.email,
            WorkspaceInvite.status == InviteStatusEnum.pending,
        )
        .first()
    )
    if existing_invite:
        return existing_invite

    invite = WorkspaceInvite(
        workspace_id=workspace_id,
        invited_by=current_user.id,
        email=payload.email,
        role=payload.role,
        status=InviteStatusEnum.pending,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    invite.workspace_name = invite.workspace.name if invite.workspace else None
    return invite


@router.get(
    "/me/invites",
    response_model=List[schemas.WorkspaceInviteOut],
    summary="List pending invites for current user",
)
def list_my_invites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invites = (
        db.query(WorkspaceInvite)
        .options(joinedload(WorkspaceInvite.workspace))
        .filter(
            WorkspaceInvite.email == current_user.email,
            WorkspaceInvite.status == InviteStatusEnum.pending,
        )
        .all()
    )
    for inv in invites:
        inv.workspace_name = inv.workspace.name if inv.workspace else None
    return invites


@router.post(
    "/invites/{invite_id}/accept",
    response_model=schemas.SuccessResponse,
    summary="Accept workspace invite",
)
def accept_invite(
    invite_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invite = db.query(WorkspaceInvite).filter(WorkspaceInvite.id == invite_id).first()
    if not invite or invite.status != InviteStatusEnum.pending:
        raise HTTPException(status_code=404, detail="Invite not found or already handled")
    if invite.email.lower() != current_user.email.lower():
        raise HTTPException(status_code=403, detail="Invite not addressed to this user")
    if invite.role == RoleEnum.owner:
        raise HTTPException(status_code=400, detail="Cannot assign owner via invite")

    # Avoid duplicate membership
    existing_member = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == invite.workspace_id,
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.status == "active",
        )
        .first()
    )
    if not existing_member:
        membership = WorkspaceMember(
            workspace_id=invite.workspace_id,
            user_id=current_user.id,
            role=invite.role,
            status="active",
        )
        db.add(membership)

    invite.status = InviteStatusEnum.accepted
    invite.responded_at = datetime.utcnow()

    # If user has no active workspace or only default, consider setting active
    current_user.workspace_id = current_user.workspace_id or invite.workspace_id
    db.commit()
    return schemas.SuccessResponse(status="ok", detail=None)


@router.post(
    "/invites/{invite_id}/decline",
    response_model=schemas.SuccessResponse,
    summary="Decline workspace invite",
)
def decline_invite(
    invite_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invite = db.query(WorkspaceInvite).filter(WorkspaceInvite.id == invite_id).first()
    if not invite or invite.status != InviteStatusEnum.pending:
        raise HTTPException(status_code=404, detail="Invite not found or already handled")
    if invite.email.lower() != current_user.email.lower():
        raise HTTPException(status_code=403, detail="Invite not addressed to this user")

    invite.status = InviteStatusEnum.declined
    invite.responded_at = datetime.utcnow()
    db.commit()
    return schemas.SuccessResponse(status="ok", detail=None)


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
    
    Auth not enforced here; consider locking down once multi-workspace access controls are strict.
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
    "/{workspace_id}/status",
    response_model=schemas.WorkspaceStatus,
    summary="Get workspace connection status",
    description="""
    Get connection status flags for conditional UI rendering.

    Returns:
        - has_shopify: Whether Shopify is connected and active
        - has_ad_platform: Whether any ad platform is connected
        - connected_platforms: List of connected platforms
        - attribution_ready: Whether attribution is fully set up

    Use this endpoint to determine which UI components to render:
        - Dashboard attribution widgets (only if has_shopify)
        - Attribution page access (only if has_shopify)
        - Platform source indicators (show connected_platforms)

    REFERENCES:
        - docs/living-docs/FRONTEND_REFACTOR_PLAN.md
    """
)
def get_workspace_status(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get workspace connection status for conditional UI rendering.

    WHAT: Returns flags indicating platform connection states
    WHY: Frontend needs this to show/hide attribution components

    Args:
        workspace_id: The workspace UUID as string
        db: Database session
        current_user: Authenticated user

    Returns:
        WorkspaceStatus with has_shopify, has_ad_platform, connected_platforms, attribution_ready

    Raises:
        HTTPException 400: Invalid workspace ID format
        HTTPException 403: User doesn't have access to workspace

    Example:
        GET /workspaces/123e4567-e89b-12d3-a456-426614174000/status
        -> { "has_shopify": true, "has_ad_platform": true,
             "connected_platforms": ["meta", "google", "shopify"],
             "attribution_ready": true }
    """
    from ..models import PixelEvent
    from datetime import timedelta

    # Convert string ID to UUID
    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )

    # Check user has access to this workspace
    _require_membership(db, current_user, workspace_uuid)

    # Get all active connections for this workspace
    connections = (
        db.query(Connection)
        .filter(
            Connection.workspace_id == workspace_uuid,
            Connection.status == "active"
        )
        .all()
    )

    # Extract provider names
    connected_platforms = [c.provider.value for c in connections if c.provider]

    # Check for Shopify connection
    has_shopify = any(c.provider.value == "shopify" for c in connections if c.provider)

    # Check for any ad platform connection
    ad_platforms = {"meta", "google", "tiktok"}
    has_ad_platform = any(
        c.provider.value in ad_platforms for c in connections if c.provider
    )

    # Check if attribution is ready (Shopify connected + pixel receiving events recently)
    attribution_ready = False
    if has_shopify:
        # Check for recent pixel events (within last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_events = (
            db.query(PixelEvent)
            .filter(
                PixelEvent.workspace_id == workspace_uuid,
                PixelEvent.created_at >= seven_days_ago
            )
            .limit(1)
            .first()
        )
        attribution_ready = recent_events is not None

    return schemas.WorkspaceStatus(
        has_shopify=has_shopify,
        has_ad_platform=has_ad_platform,
        connected_platforms=sorted(connected_platforms),
        attribution_ready=attribution_ready
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

@router.delete(
    "/{workspace_id}",
    response_model=schemas.SuccessResponse,
    summary="Delete workspace",
    description="""
    Permanently delete a workspace and all its data.
    
    Requirements:
    - User must be the Owner of the workspace.
    
    Behavior:
    - Deletes all entities, metrics, connections, and logs associated with the workspace.
    - For all members (including the owner), if this was their active workspace:
        - Switches them to another workspace if available.
        - If no other workspace exists, creates a new default workspace for them.
    """
)
def delete_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Check permissions
    _require_membership(db, current_user, workspace_id, roles=[RoleEnum.owner])
    
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # 2. Handle members (ensure no one is left stranded)
    # Get all members of this workspace
    members = (
        db.query(WorkspaceMember)
        .options(joinedload(WorkspaceMember.user))
        .filter(WorkspaceMember.workspace_id == workspace_id)
        .all()
    )
    
    for member in members:
        user = member.user
        if not user:
            continue
            
        # If this is their active workspace, we must move them
        if user.workspace_id == workspace_id:
            # Find another workspace
            other_membership = (
                db.query(WorkspaceMember)
                .filter(
                    WorkspaceMember.user_id == user.id,
                    WorkspaceMember.workspace_id != workspace_id,
                    WorkspaceMember.status == "active"
                )
                .first()
            )
            
            if other_membership:
                user.workspace_id = other_membership.workspace_id
                user.role = other_membership.role
            else:
                # Create a new default workspace for them
                first_name = ((user.name or "").split(" ")[0] or "My").strip().title()
                new_ws = Workspace(name=f"{first_name}'s Workspace")
                db.add(new_ws)
                db.flush()
                
                new_member = WorkspaceMember(
                    workspace_id=new_ws.id,
                    user_id=user.id,
                    role=RoleEnum.owner,
                    status="active"
                )
                db.add(new_member)
                
                user.workspace_id = new_ws.id
                user.role = RoleEnum.owner
                
                db.add(user)

    # 3. Delete all workspace data (Cascade logic)
    # Import models locally to avoid circular imports if any, though they are available at module level
    from ..models import (
        MetricFact, Entity, ManualCost, Connection, Token, QaQueryLog, ComputeRun, Pnl
    )
    
    # Delete metric facts
    db.query(MetricFact).filter(
        MetricFact.entity_id.in_(
            db.query(Entity.id).filter(Entity.workspace_id == workspace_id)
        )
    ).delete(synchronize_session=False)
    
    # Delete PnLs (via ComputeRuns or Entities)
    # PnLs are linked to ComputeRuns and Entities. 
    # Deleting Entities will cascade to PnLs if configured, but let's be explicit.
    db.query(Pnl).filter(
        Pnl.run_id.in_(
            db.query(ComputeRun.id).filter(ComputeRun.workspace_id == workspace_id)
        )
    ).delete(synchronize_session=False)
    
    # Delete ComputeRuns
    db.query(ComputeRun).filter(ComputeRun.workspace_id == workspace_id).delete(synchronize_session=False)

    # Delete entities
    db.query(Entity).filter(Entity.workspace_id == workspace_id).delete(synchronize_session=False)
    
    # Delete manual costs
    db.query(ManualCost).filter(ManualCost.workspace_id == workspace_id).delete(synchronize_session=False)
    
    # Delete connections and orphaned tokens
    connection_ids = [c.id for c in db.query(Connection.id).filter(
        Connection.workspace_id == workspace_id
    ).all()]
    
    if connection_ids:
        token_ids = [t[0] for t in db.query(Connection.token_id).filter(
            Connection.id.in_(connection_ids),
            Connection.token_id.isnot(None)
        ).all()]
        
        db.query(Connection).filter(Connection.workspace_id == workspace_id).delete(synchronize_session=False)
        
        if token_ids:
            # Only delete tokens if they are not used by other connections (though tokens are usually 1:1)
            # For safety, check if token is used elsewhere? 
            # Our model implies 1:N but usually 1:1. Let's assume safe to delete if we are deleting the connection.
            # Actually, let's check if any other connection uses these tokens
            used_tokens = db.query(Connection.token_id).filter(
                Connection.token_id.in_(token_ids),
                Connection.workspace_id != workspace_id
            ).all()
            used_token_ids = {t[0] for t in used_tokens}
            tokens_to_delete = set(token_ids) - used_token_ids
            
            if tokens_to_delete:
                db.query(Token).filter(Token.id.in_(tokens_to_delete)).delete(synchronize_session=False)

    # Delete query logs
    db.query(QaQueryLog).filter(QaQueryLog.workspace_id == workspace_id).delete(synchronize_session=False)
    
    # Delete invites
    db.query(WorkspaceInvite).filter(WorkspaceInvite.workspace_id == workspace_id).delete(synchronize_session=False)
    
    # Delete members
    db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).delete(synchronize_session=False)

    # Delete workspace
    db.delete(workspace)
    
    db.commit()
    
    return schemas.SuccessResponse(detail="Workspace deleted successfully")
