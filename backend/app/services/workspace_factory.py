"""Workspace Factory Service - Centralized workspace creation logic.

WHAT: Provides factory functions for creating workspaces with consistent billing setup.
WHY: Consolidates 5 duplicate workspace creation patterns across the codebase:
    - clerk_webhooks.py (2 places)
    - workspaces.py (2 places)
    - auth.py (1 place)

This ensures all new workspaces get proper trial billing setup.

REFERENCES:
    - backend/app/models.py (Workspace, WorkspaceMember models)
    - docs-arch/living-docs/BILLING.md (billing flow documentation)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..models import (
    Workspace,
    WorkspaceMember,
    BillingStatusEnum,
    BillingPlanEnum,
    RoleEnum,
)

# Trial configuration constants
TRIAL_DURATION_DAYS = 7


def create_workspace_with_trial(
    db: Session,
    name: str,
    owner_user_id: Optional[UUID] = None,
    flush_only: bool = True,
) -> Workspace:
    """Create a new workspace with 7-day trial billing setup.

    WHAT: Creates a workspace with trialing status and starter tier.
    WHY: All new workspaces should start with a 7-day trial to let users
         experience full features before requiring payment.

    Parameters:
        db: Database session
        name: Workspace name (e.g., "John's Workspace")
        owner_user_id: If provided, creates WorkspaceMember with owner role
        flush_only: If True, only flush (don't commit). Default True for
                   callers that manage their own transaction.

    Returns:
        Workspace: The created workspace with trial setup

    Example:
        # In webhook handler
        workspace = create_workspace_with_trial(
            db=db,
            name=f"{first_name}'s Workspace",
            owner_user_id=user.id,
        )
        db.commit()
    """
    trial_start = datetime.now(timezone.utc)
    trial_end = trial_start + timedelta(days=TRIAL_DURATION_DAYS)

    workspace = Workspace(
        name=name,
        billing_status=BillingStatusEnum.trialing,
        billing_tier=BillingPlanEnum.starter,  # Full access during trial
        trial_started_at=trial_start,
        trial_end=trial_end,
    )
    db.add(workspace)
    db.flush()  # Get workspace.id without committing

    # Create owner membership if user_id provided
    if owner_user_id:
        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner_user_id,
            role=RoleEnum.owner,
            status="active",
        )
        db.add(membership)

    if not flush_only:
        db.commit()
        db.refresh(workspace)

    return workspace


def generate_workspace_name(first_name: Optional[str]) -> str:
    """Generate a workspace name from user's first name.

    WHAT: Creates a consistent "FirstName's Workspace" pattern.
    WHY: Users expect a personalized workspace name on signup.

    Parameters:
        first_name: User's first name (can be None or empty)

    Returns:
        str: Workspace name like "John's Workspace" or "My Workspace" if no name

    Example:
        name = generate_workspace_name("John")  # "John's Workspace"
        name = generate_workspace_name("")      # "My Workspace"
    """
    clean_name = (first_name or "").strip().title()
    if not clean_name:
        clean_name = "My"
    return f"{clean_name}'s Workspace"


def create_workspace_for_user(
    db: Session,
    owner_user_id: UUID,
    first_name: Optional[str] = None,
    custom_name: Optional[str] = None,
    flush_only: bool = True,
) -> Workspace:
    """Create a workspace for a user with auto-generated or custom name.

    WHAT: Convenience function combining name generation with workspace creation.
    WHY: Common pattern across signup flows - create workspace with proper name.

    Parameters:
        db: Database session
        owner_user_id: User who will own the workspace
        first_name: User's first name for auto-generated name
        custom_name: Custom workspace name (overrides first_name)
        flush_only: If True, only flush (don't commit)

    Returns:
        Workspace: The created workspace

    Example:
        # Auto-generated name from first name
        workspace = create_workspace_for_user(db, user.id, first_name="John")

        # Custom name
        workspace = create_workspace_for_user(db, user.id, custom_name="Acme Inc")
    """
    name = custom_name if custom_name else generate_workspace_name(first_name)
    return create_workspace_with_trial(
        db=db,
        name=name,
        owner_user_id=owner_user_id,
        flush_only=flush_only,
    )
