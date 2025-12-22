"""Admin endpoints for workspace management.

WHAT: Protected endpoints for admin operations like bulk upgrades
WHY: Enables giveaways, promotions, and manual user management at scale

SECURITY: Protected by ADMIN_SECRET environment variable
"""

import os
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Workspace, User, WorkspaceMember, BillingPlanEnum

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")


def verify_admin_secret(x_admin_secret: str = Header(...)):
    """Verify admin secret header for protected endpoints."""
    if not ADMIN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints not configured"
        )
    if x_admin_secret != ADMIN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin secret"
        )
    return True


class UpgradeRequest(BaseModel):
    """Request to upgrade workspaces to starter tier."""
    # Can specify by workspace IDs, user emails, or both
    workspace_ids: List[str] = []
    user_emails: List[EmailStr] = []
    tier: str = "starter"  # "free" or "starter"


class UpgradeResponse(BaseModel):
    """Response from upgrade operation."""
    upgraded: int
    failed: int
    details: List[dict]


@router.post(
    "/upgrade-workspaces",
    response_model=UpgradeResponse,
    summary="Bulk upgrade workspaces to paid tier",
    description="""
    Upgrade multiple workspaces to starter tier for giveaways/promotions.

    Can specify workspaces by:
    - workspace_ids: Direct workspace UUIDs
    - user_emails: Will upgrade the primary workspace of each user

    Requires X-Admin-Secret header.
    """
)
async def bulk_upgrade_workspaces(
    payload: UpgradeRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Bulk upgrade workspaces to starter tier."""

    tier = BillingPlanEnum.starter if payload.tier == "starter" else BillingPlanEnum.free
    upgraded = 0
    failed = 0
    details = []

    # Upgrade by workspace IDs
    for ws_id in payload.workspace_ids:
        try:
            workspace = db.query(Workspace).filter(Workspace.id == UUID(ws_id)).first()
            if workspace:
                workspace.billing_tier = tier
                upgraded += 1
                details.append({"workspace_id": ws_id, "name": workspace.name, "status": "upgraded"})
            else:
                failed += 1
                details.append({"workspace_id": ws_id, "status": "not_found"})
        except Exception as e:
            failed += 1
            details.append({"workspace_id": ws_id, "status": "error", "error": str(e)})

    # Upgrade by user emails (find their primary workspace)
    for email in payload.user_emails:
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                failed += 1
                details.append({"email": email, "status": "user_not_found"})
                continue

            # Find user's primary workspace (where they are Owner)
            membership = db.query(WorkspaceMember).filter(
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.role == "Owner"
            ).first()

            if not membership:
                # Fallback: any workspace they're a member of
                membership = db.query(WorkspaceMember).filter(
                    WorkspaceMember.user_id == user.id
                ).first()

            if membership:
                workspace = db.query(Workspace).filter(Workspace.id == membership.workspace_id).first()
                if workspace:
                    workspace.billing_tier = tier
                    upgraded += 1
                    details.append({"email": email, "workspace": workspace.name, "status": "upgraded"})
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

    logger.info(f"Bulk upgrade: {upgraded} upgraded, {failed} failed")

    return UpgradeResponse(upgraded=upgraded, failed=failed, details=details)


@router.get(
    "/workspace/{workspace_id}",
    summary="Get workspace details",
    description="Get billing and membership details for a workspace."
)
async def get_workspace_details(
    workspace_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_secret),
):
    """Get workspace details for admin."""
    workspace = db.query(Workspace).filter(Workspace.id == UUID(workspace_id)).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace.id).all()

    return {
        "id": str(workspace.id),
        "name": workspace.name,
        "billing_status": workspace.billing_status.value,
        "billing_tier": workspace.billing_tier.value,
        "billing_plan": workspace.billing_plan,
        "members": [
            {"user_id": str(m.user_id), "role": m.role.value, "status": m.status}
            for m in members
        ]
    }
