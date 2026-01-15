"""Admin endpoints for user and workspace management.

WHAT: Protected endpoints for admin operations like user management, billing overrides
WHY: Enables platform-level administration separate from workspace-level roles

SECURITY:
    - UI-based: Protected by is_superuser flag (login required)
    - API-based: Protected by ADMIN_SECRET header (for scripts/automation)
"""

import os
import logging
from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..deps import get_current_user, require_superuser
from ..models import (
    Workspace,
    User,
    WorkspaceMember,
    BillingPlanEnum,
    BillingStatusEnum,
    RoleEnum,
    AuthCredential,
    QaQueryLog,
    QaFeedback,
    PolarCheckoutMapping,
    Connection,
    Entity,
    ComputeRun,
    ManualCost,
)
from ..schemas import (
    AdminUserOut,
    AdminUsersResponse,
    AdminWorkspaceSummary,
    AdminWorkspacesResponse,
    AdminSuperuserUpdate,
    AdminBillingUpdate,
    AdminDeleteUserResponse,
    AdminMeResponse,
    AdminUserWorkspace,
)
from ..services.clerk_admin_service import delete_clerk_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")


def verify_admin_secret(x_admin_secret: str = Header(default=None)):
    """Verify admin secret header for protected endpoints (optional)."""
    if x_admin_secret and ADMIN_SECRET and x_admin_secret == ADMIN_SECRET:
        return True
    return False


async def require_admin_access(
    x_admin_secret: str = Header(default=None),
    current_user: User = Depends(get_current_user),
) -> User:
    """Require either superuser login OR valid admin secret.

    WHAT: Flexible auth that accepts either method
    WHY: UI uses superuser login, scripts use admin secret header
    """
    # Check admin secret first (allows non-authenticated API calls)
    if x_admin_secret and ADMIN_SECRET and x_admin_secret == ADMIN_SECRET:
        return current_user  # Secret valid, allow access

    # Fall back to superuser check
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required (superuser or admin secret)",
        )
    return current_user


# =============================================================================
# ADMIN STATUS ENDPOINT (for frontend to check access)
# =============================================================================


@router.get(
    "/me",
    response_model=AdminMeResponse,
    summary="Check current user's admin status",
    description="Returns whether the current user has superuser access.",
)
async def get_admin_status(
    current_user: User = Depends(get_current_user),
):
    """Check if current user is a superuser."""
    return AdminMeResponse(
        is_superuser=current_user.is_superuser,
        user_id=str(current_user.id),
        email=current_user.email,
    )


# =============================================================================
# USER MANAGEMENT ENDPOINTS
# =============================================================================


@router.get(
    "/users",
    response_model=AdminUsersResponse,
    summary="List all users",
    description="Get all users with their workspace memberships.",
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_access),
):
    """List all users for admin dashboard."""
    query = db.query(User)

    # Optional search by email or name
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_pattern)) | (User.name.ilike(search_pattern))
        )

    total = query.count()
    users = query.offset(skip).limit(limit).all()

    # Build response with workspace info
    user_list = []
    for user in users:
        # Get user's workspaces via memberships
        memberships = (
            db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).all()
        )

        workspaces = []
        for m in memberships:
            ws = db.query(Workspace).filter(Workspace.id == m.workspace_id).first()
            if ws:
                workspaces.append(
                    AdminUserWorkspace(
                        id=str(ws.id),
                        name=ws.name,
                        role=m.role.value if hasattr(m.role, "value") else str(m.role),
                        billing_tier=ws.billing_tier.value
                        if hasattr(ws.billing_tier, "value")
                        else str(ws.billing_tier),
                    )
                )

        user_list.append(
            AdminUserOut(
                id=str(user.id),
                email=user.email,
                name=user.name,
                clerk_id=user.clerk_id,
                is_superuser=user.is_superuser,
                is_verified=user.is_verified,
                avatar_url=user.avatar_url,
                workspaces=workspaces,
            )
        )

    return AdminUsersResponse(users=user_list, total=total)


@router.delete(
    "/users/{user_id}",
    response_model=AdminDeleteUserResponse,
    summary="Delete a user",
    description="Delete user from database AND Clerk. Cascades to owned workspaces.",
)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_access),
):
    """Delete a user and cascade to their owned workspaces.

    This will:
    1. Delete user from Clerk (so they can't log in)
    2. Delete workspaces where user is Owner
    3. Remove user's WorkspaceMember records
    4. Delete the User record
    """
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    clerk_deleted = False
    workspaces_deleted = 0

    # Step 1: Delete from Clerk
    if user.clerk_id:
        clerk_deleted = await delete_clerk_user(user.clerk_id)
        if not clerk_deleted:
            logger.warning(
                f"[ADMIN] Failed to delete user {user_id} from Clerk, continuing with DB deletion"
            )

    # Step 2: Find and delete owned workspaces
    owned_memberships = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.role == RoleEnum.owner,
        )
        .all()
    )

    for membership in owned_memberships:
        workspace = (
            db.query(Workspace).filter(Workspace.id == membership.workspace_id).first()
        )
        if workspace:
            # Delete all members of this workspace first
            db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == workspace.id
            ).delete()

            # Delete related data (no cascade configured on these)
            db.query(Connection).filter(
                Connection.workspace_id == workspace.id
            ).delete()
            db.query(Entity).filter(
                Entity.workspace_id == workspace.id
            ).delete()
            db.query(ComputeRun).filter(
                ComputeRun.workspace_id == workspace.id
            ).delete()
            db.query(ManualCost).filter(
                ManualCost.workspace_id == workspace.id
            ).delete()
            db.query(QaQueryLog).filter(
                QaQueryLog.workspace_id == workspace.id
            ).delete()

            # Delete the workspace (cascade handles invites)
            db.delete(workspace)
            workspaces_deleted += 1

    # Step 3: Remove any remaining memberships (where user is member, not owner)
    db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).delete()

    # Step 4: Delete all user-related records from other tables
    # QA Feedback (references QaQueryLog which references user)
    db.query(QaFeedback).filter(QaFeedback.user_id == user.id).delete()

    # QA Query Logs
    db.query(QaQueryLog).filter(QaQueryLog.user_id == user.id).delete()

    # Polar checkout mappings
    db.query(PolarCheckoutMapping).filter(
        PolarCheckoutMapping.created_by_user_id == user.id
    ).delete()

    # Auth credentials (legacy password auth)
    db.query(AuthCredential).filter(AuthCredential.user_id == user.id).delete()

    # Step 5: Delete the user
    db.delete(user)
    db.commit()

    logger.info(
        f"[ADMIN] Deleted user {user_id} (clerk_deleted={clerk_deleted}, "
        f"workspaces_deleted={workspaces_deleted})"
    )

    return AdminDeleteUserResponse(
        success=True,
        user_id=user_id,
        clerk_deleted=clerk_deleted,
        workspaces_deleted=workspaces_deleted,
        message=f"User deleted successfully. Clerk: {'yes' if clerk_deleted else 'no'}, Workspaces: {workspaces_deleted}",
    )


@router.patch(
    "/users/{user_id}/superuser",
    response_model=AdminUserOut,
    summary="Toggle user superuser status",
    description="Grant or revoke superuser access for a user.",
)
async def update_superuser_status(
    user_id: str,
    payload: AdminSuperuserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_access),
):
    """Toggle superuser status for a user."""
    # Prevent removing your own superuser status
    if str(current_user.id) == user_id and not payload.is_superuser:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove your own superuser status",
        )

    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_superuser = payload.is_superuser
    db.commit()
    db.refresh(user)

    logger.info(f"[ADMIN] Set is_superuser={payload.is_superuser} for user {user_id}")

    # Get workspaces for response
    memberships = (
        db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).all()
    )
    workspaces = []
    for m in memberships:
        ws = db.query(Workspace).filter(Workspace.id == m.workspace_id).first()
        if ws:
            workspaces.append(
                AdminUserWorkspace(
                    id=str(ws.id),
                    name=ws.name,
                    role=m.role.value if hasattr(m.role, "value") else str(m.role),
                    billing_tier=ws.billing_tier.value
                    if hasattr(ws.billing_tier, "value")
                    else str(ws.billing_tier),
                )
            )

    return AdminUserOut(
        id=str(user.id),
        email=user.email,
        name=user.name,
        clerk_id=user.clerk_id,
        is_superuser=user.is_superuser,
        is_verified=user.is_verified,
        avatar_url=user.avatar_url,
        workspaces=workspaces,
    )


# =============================================================================
# WORKSPACE MANAGEMENT ENDPOINTS
# =============================================================================


@router.get(
    "/workspaces",
    response_model=AdminWorkspacesResponse,
    summary="List all workspaces",
    description="Get all workspaces with billing info and member count.",
)
async def list_workspaces(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_access),
):
    """List all workspaces for admin dashboard."""
    query = db.query(Workspace)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(Workspace.name.ilike(search_pattern))

    total = query.count()
    workspaces = query.offset(skip).limit(limit).all()

    workspace_list = []
    for ws in workspaces:
        # Count members
        member_count = (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.workspace_id == ws.id)
            .count()
        )

        # Find owner
        owner_membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.role == RoleEnum.owner,
            )
            .first()
        )
        owner_email = None
        if owner_membership:
            owner = db.query(User).filter(User.id == owner_membership.user_id).first()
            if owner:
                owner_email = owner.email

        workspace_list.append(
            AdminWorkspaceSummary(
                id=str(ws.id),
                name=ws.name,
                billing_status=ws.billing_status.value
                if hasattr(ws.billing_status, "value")
                else str(ws.billing_status),
                billing_tier=ws.billing_tier.value
                if hasattr(ws.billing_tier, "value")
                else str(ws.billing_tier),
                member_count=member_count,
                owner_email=owner_email,
                created_at=ws.created_at,
            )
        )

    return AdminWorkspacesResponse(workspaces=workspace_list, total=total)


@router.patch(
    "/workspaces/{workspace_id}/billing",
    response_model=AdminWorkspaceSummary,
    summary="Update workspace billing tier",
    description="Set workspace billing tier to free or starter.",
)
async def update_workspace_billing(
    workspace_id: str,
    payload: AdminBillingUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_access),
):
    """Update workspace billing tier."""
    workspace = db.query(Workspace).filter(Workspace.id == UUID(workspace_id)).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Update tier
    new_tier = (
        BillingPlanEnum.starter
        if payload.billing_tier == "starter"
        else BillingPlanEnum.free
    )
    workspace.billing_tier = new_tier

    # Also set status to active if upgrading to starter
    # Clear trial fields so trial expiry check doesn't affect gifted users
    if payload.billing_tier == "starter":
        workspace.billing_status = BillingStatusEnum.active
        workspace.trial_started_at = None
        workspace.trial_end = None

    db.commit()
    db.refresh(workspace)

    logger.info(
        f"[ADMIN] Set billing_tier={payload.billing_tier} for workspace {workspace_id}"
    )

    # Count members for response
    member_count = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace.id)
        .count()
    )

    # Find owner
    owner_membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.role == RoleEnum.owner,
        )
        .first()
    )
    owner_email = None
    if owner_membership:
        owner = db.query(User).filter(User.id == owner_membership.user_id).first()
        if owner:
            owner_email = owner.email

    return AdminWorkspaceSummary(
        id=str(workspace.id),
        name=workspace.name,
        billing_status=workspace.billing_status.value
        if hasattr(workspace.billing_status, "value")
        else str(workspace.billing_status),
        billing_tier=workspace.billing_tier.value
        if hasattr(workspace.billing_tier, "value")
        else str(workspace.billing_tier),
        member_count=member_count,
        owner_email=owner_email,
        created_at=workspace.created_at,
    )


# =============================================================================
# LEGACY ENDPOINTS (kept for backwards compatibility)
# =============================================================================


class DeleteClerkUserRequest(BaseModel):
    """Request to delete a user directly from Clerk (for orphaned users)."""

    clerk_id: str


@router.delete(
    "/clerk-user/{clerk_id}",
    summary="Delete orphaned Clerk user",
    description="Delete a user directly from Clerk who doesn't exist in local DB.",
)
async def delete_clerk_user_direct(
    clerk_id: str,
    _: User = Depends(require_admin_access),
):
    """Delete a user directly from Clerk.

    Use this for orphaned Clerk users who aren't in the local database
    but are blocking email signups.
    """
    success = await delete_clerk_user(clerk_id)

    if success:
        return {"success": True, "message": f"Deleted Clerk user {clerk_id}"}
    else:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete Clerk user {clerk_id}"
        )


class UpgradeRequest(BaseModel):
    """Request to upgrade workspaces to starter tier."""

    workspace_ids: List[str] = []
    user_emails: List[EmailStr] = []
    tier: str = "starter"


class UpgradeResponse(BaseModel):
    """Response from upgrade operation."""

    upgraded: int
    failed: int
    details: List[dict]


@router.post(
    "/upgrade-workspaces",
    response_model=UpgradeResponse,
    summary="Bulk upgrade workspaces to paid tier",
    description="Legacy endpoint for bulk upgrades. Requires X-Admin-Secret header.",
)
async def bulk_upgrade_workspaces(
    payload: UpgradeRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_access),
):
    """Bulk upgrade workspaces to starter tier."""
    tier = (
        BillingPlanEnum.starter if payload.tier == "starter" else BillingPlanEnum.free
    )
    upgraded = 0
    failed = 0
    details = []

    # Upgrade by workspace IDs
    for ws_id in payload.workspace_ids:
        try:
            workspace = db.query(Workspace).filter(Workspace.id == UUID(ws_id)).first()
            if workspace:
                workspace.billing_tier = tier
                workspace.billing_status = BillingStatusEnum.active
                # Clear trial fields for gifted upgrades
                if tier == BillingPlanEnum.starter:
                    workspace.trial_started_at = None
                    workspace.trial_end = None
                upgraded += 1
                details.append(
                    {
                        "workspace_id": ws_id,
                        "name": workspace.name,
                        "status": "upgraded",
                    }
                )
            else:
                failed += 1
                details.append({"workspace_id": ws_id, "status": "not_found"})
        except Exception as e:
            failed += 1
            details.append({"workspace_id": ws_id, "status": "error", "error": str(e)})

    # Upgrade by user emails
    for email in payload.user_emails:
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                failed += 1
                details.append({"email": email, "status": "user_not_found"})
                continue

            membership = (
                db.query(WorkspaceMember)
                .filter(
                    WorkspaceMember.user_id == user.id,
                    WorkspaceMember.role == RoleEnum.owner,
                )
                .first()
            )
            if not membership:
                membership = (
                    db.query(WorkspaceMember)
                    .filter(WorkspaceMember.user_id == user.id)
                    .first()
                )

            if membership:
                workspace = (
                    db.query(Workspace)
                    .filter(Workspace.id == membership.workspace_id)
                    .first()
                )
                if workspace:
                    workspace.billing_tier = tier
                    workspace.billing_status = BillingStatusEnum.active
                    # Clear trial fields for gifted upgrades
                    if tier == BillingPlanEnum.starter:
                        workspace.trial_started_at = None
                        workspace.trial_end = None
                    upgraded += 1
                    details.append(
                        {
                            "email": email,
                            "workspace": workspace.name,
                            "status": "upgraded",
                        }
                    )
                else:
                    failed += 1
                    details.append({"email": email, "status": "workspace_not_found"})
            else:
                failed += 1
                details.append({"email": email, "status": "no_membership"})
        except Exception as e:
            failed += 1
            details.append({"email": email, "status": "error", "error": str(e)})

    db.commit()
    logger.info(f"[ADMIN] Bulk upgrade: {upgraded} upgraded, {failed} failed")

    return UpgradeResponse(upgraded=upgraded, failed=failed, details=details)


@router.get(
    "/workspace/{workspace_id}",
    summary="Get workspace details",
    description="Get billing and membership details for a workspace.",
)
async def get_workspace_details(
    workspace_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_access),
):
    """Get workspace details for admin."""
    workspace = db.query(Workspace).filter(Workspace.id == UUID(workspace_id)).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    members = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace.id)
        .all()
    )

    return {
        "id": str(workspace.id),
        "name": workspace.name,
        "billing_status": workspace.billing_status.value
        if hasattr(workspace.billing_status, "value")
        else str(workspace.billing_status),
        "billing_tier": workspace.billing_tier.value
        if hasattr(workspace.billing_tier, "value")
        else str(workspace.billing_tier),
        "billing_plan": workspace.billing_plan,
        "members": [
            {
                "user_id": str(m.user_id),
                "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                "status": m.status,
            }
            for m in members
        ],
    }
