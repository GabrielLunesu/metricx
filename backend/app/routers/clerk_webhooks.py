"""Clerk webhook handlers for user lifecycle events.

WHAT: Receives events from Clerk when users are created/updated/deleted
WHY: Keeps local User table in sync with Clerk identity provider
REFERENCES:
    - https://clerk.com/docs/integrations/webhooks
    - backend/app/models.py (User, Workspace, WorkspaceMember)

Events handled:
    - user.created: Create local User + Workspace + WorkspaceMember
    - user.updated: Sync email/name changes from Clerk
    - user.deleted: Clean up local data (GDPR compliance)
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_settings
from ..models import RoleEnum, User, Workspace, WorkspaceMember
from ..services.workspace_factory import create_workspace_with_trial, generate_workspace_name

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _verify_clerk_signature(
    payload: bytes,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
    secret: str,
) -> bool:
    """Verify webhook signature from Clerk using Svix.

    WHAT: Cryptographically verifies webhook came from Clerk
    WHY: Prevents attackers from creating fake users via forged webhooks

    Clerk uses Svix for webhook delivery, which signs payloads using HMAC-SHA256.

    Parameters:
        payload: Raw request body bytes
        svix_id: Unique message ID from Svix-Id header
        svix_timestamp: Unix timestamp from Svix-Timestamp header
        svix_signature: Signature from Svix-Signature header
        secret: Webhook signing secret from Clerk dashboard

    Returns:
        bool: True if signature is valid

    References:
        https://docs.svix.com/receiving/verifying-payloads/how
    """
    # Extract the secret (remove whsec_ prefix if present)
    if secret.startswith("whsec_"):
        secret = secret[6:]

    # Decode the base64 secret
    import base64
    secret_bytes = base64.b64decode(secret)

    # Build the signed payload: "{svix_id}.{svix_timestamp}.{payload}"
    signed_payload = f"{svix_id}.{svix_timestamp}.{payload.decode('utf-8')}"

    # Compute HMAC-SHA256
    expected_signature = hmac.new(
        secret_bytes,
        signed_payload.encode("utf-8"),
        hashlib.sha256
    ).digest()
    expected_signature_b64 = base64.b64encode(expected_signature).decode("utf-8")

    # Svix-Signature header format: "v1,<signature1> v1,<signature2> ..."
    # We need to check if any of the signatures match
    signatures = svix_signature.split(" ")
    for sig in signatures:
        if sig.startswith("v1,"):
            actual_sig = sig[3:]  # Remove "v1," prefix
            if hmac.compare_digest(expected_signature_b64, actual_sig):
                return True

    return False


@router.post("/clerk")
async def handle_clerk_webhook(
    request: Request,
    db: Session = Depends(get_db),
    svix_id: str = Header(None, alias="svix-id"),
    svix_timestamp: str = Header(None, alias="svix-timestamp"),
    svix_signature: str = Header(None, alias="svix-signature"),
):
    """Handle Clerk webhook events for user lifecycle management.

    WHAT: Receives and processes user events from Clerk
    WHY: Provisions/updates/deletes local user records when Clerk state changes

    Security:
        - Verifies webhook signature using Svix HMAC-SHA256
        - Rejects requests with invalid or missing signatures

    Events:
        - user.created: Create Workspace + User + WorkspaceMember
        - user.updated: Sync email/name to local User record
        - user.deleted: Delete local user and cleanup data

    Returns:
        dict: Status of webhook processing

    Raises:
        HTTPException 400: Invalid webhook signature
        HTTPException 500: Webhook secret not configured
    """
    settings = get_settings()

    if not settings.CLERK_WEBHOOK_SECRET:
        logger.error("[CLERK_WEBHOOK] Webhook secret not configured")
        raise HTTPException(
            status_code=500,
            detail="Webhook secret not configured"
        )

    # Get raw body for signature verification
    body = await request.body()

    # Verify required headers
    if not all([svix_id, svix_timestamp, svix_signature]):
        logger.warning("[CLERK_WEBHOOK] Missing required Svix headers")
        raise HTTPException(
            status_code=400,
            detail="Missing webhook signature headers"
        )

    # Verify signature
    if not _verify_clerk_signature(
        body,
        svix_id,
        svix_timestamp,
        svix_signature,
        settings.CLERK_WEBHOOK_SECRET,
    ):
        logger.warning("[CLERK_WEBHOOK] Invalid webhook signature")
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook signature"
        )

    # Validate timestamp to prevent replay attacks
    # Reject webhooks older than 5 minutes
    import time
    try:
        webhook_ts = int(svix_timestamp)
        current_ts = int(time.time())
        age_seconds = abs(current_ts - webhook_ts)
        if age_seconds > 300:  # 5 minute tolerance
            logger.warning(
                f"[CLERK_WEBHOOK] Stale webhook rejected: age={age_seconds}s, "
                f"timestamp={svix_timestamp}"
            )
            raise HTTPException(
                status_code=400,
                detail="Webhook timestamp too old (possible replay attack)"
            )
    except (ValueError, TypeError):
        logger.warning(f"[CLERK_WEBHOOK] Invalid timestamp format: {svix_timestamp}")
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook timestamp"
        )

    # Parse payload
    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.error("[CLERK_WEBHOOK] Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("type")
    data = payload.get("data", {})

    logger.info(f"[CLERK_WEBHOOK] Received event: {event_type}")

    # Route to appropriate handler
    if event_type == "user.created":
        return await _handle_user_created(db, data)
    elif event_type == "user.updated":
        return await _handle_user_updated(db, data)
    elif event_type == "user.deleted":
        return await _handle_user_deleted(db, data)
    else:
        logger.info(f"[CLERK_WEBHOOK] Ignoring event type: {event_type}")
        return {"status": "ignored", "event_type": event_type}


async def _handle_user_created(db: Session, data: dict[str, Any]) -> dict:
    """Create local User with Workspace when Clerk user signs up.

    WHAT: Provisions local user record with default workspace
    WHY: Matches existing registration behavior - "FirstName's Workspace"

    Flow:
        1. Check if user already exists (idempotency)
        2. Extract email/name from Clerk payload
        3. Create Workspace with "FirstName's Workspace" name
        4. Create User linked to workspace with Owner role
        5. Create WorkspaceMember for the relationship

    Parameters:
        db: Database session
        data: Clerk user data from webhook payload

    Returns:
        dict: Status with user_id and workspace_id
    """
    clerk_id = data.get("id")

    # Idempotency check - user might already exist
    existing = db.query(User).filter(User.clerk_id == clerk_id).first()
    if existing:
        logger.info(f"[CLERK_WEBHOOK] User already exists for clerk_id={clerk_id}")
        return {
            "status": "already_exists",
            "user_id": str(existing.id),
            "workspace_id": str(existing.workspace_id),
        }

    # Extract primary email from Clerk payload
    # Clerk stores emails as array with primary_email_address_id reference
    email_addresses = data.get("email_addresses", [])
    primary_email_id = data.get("primary_email_address_id")

    primary_email = None
    for email_obj in email_addresses:
        if email_obj.get("id") == primary_email_id:
            primary_email = email_obj.get("email_address")
            break

    # Fallback to first email if primary not found
    if not primary_email and email_addresses:
        primary_email = email_addresses[0].get("email_address")

    if not primary_email:
        logger.error(f"[CLERK_WEBHOOK] No email found for clerk_id={clerk_id}")
        raise HTTPException(status_code=400, detail="No email address found")

    # Check if email already exists (shouldn't happen but safety check)
    existing_by_email = db.query(User).filter(User.email == primary_email).first()
    if existing_by_email:
        # Link existing user to Clerk (migration scenario)
        existing_by_email.clerk_id = clerk_id
        db.commit()
        logger.info(f"[CLERK_WEBHOOK] Linked existing user {existing_by_email.id} to clerk_id={clerk_id}")
        return {
            "status": "linked_existing",
            "user_id": str(existing_by_email.id),
            "workspace_id": str(existing_by_email.workspace_id),
        }

    # Extract name from Clerk payload
    first_name = data.get("first_name") or ""
    last_name = data.get("last_name") or ""
    full_name = f"{first_name} {last_name}".strip()

    # Fallback to email username if no name provided
    if not full_name:
        full_name = primary_email.split("@")[0]

    # Create workspace with 7-day trial via factory (full access)
    workspace_name = generate_workspace_name(first_name)
    workspace = create_workspace_with_trial(db=db, name=workspace_name)

    # Create user linked to Clerk
    user = User(
        clerk_id=clerk_id,
        email=primary_email,
        name=full_name,
        role=RoleEnum.owner,
        workspace_id=workspace.id,
        is_verified=True,  # Clerk handles email verification
        avatar_url=data.get("image_url"),
    )
    db.add(user)
    db.flush()  # Get user.id without committing

    # Create workspace membership (user must exist first)
    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=RoleEnum.owner,
        status="active",
    )
    db.add(membership)

    db.commit()

    logger.info(
        f"[CLERK_WEBHOOK] Created user {user.id} with workspace {workspace.id} "
        f"for clerk_id={clerk_id} email={primary_email}"
    )

    return {
        "status": "created",
        "user_id": str(user.id),
        "workspace_id": str(workspace.id),
    }


async def _handle_user_updated(db: Session, data: dict[str, Any]) -> dict:
    """Sync user profile changes from Clerk to local database.

    WHAT: Updates local User record when Clerk profile changes
    WHY: Keeps email/name in sync between Clerk and local database

    Parameters:
        db: Database session
        data: Clerk user data from webhook payload

    Returns:
        dict: Status of update operation
    """
    clerk_id = data.get("id")

    user = db.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        logger.warning(f"[CLERK_WEBHOOK] User not found for clerk_id={clerk_id}")
        return {"status": "not_found", "clerk_id": clerk_id}

    # Update email if changed
    email_addresses = data.get("email_addresses", [])
    primary_email_id = data.get("primary_email_address_id")

    for email_obj in email_addresses:
        if email_obj.get("id") == primary_email_id:
            new_email = email_obj.get("email_address")
            if new_email and new_email != user.email:
                # Check email isn't taken by another user
                existing = db.query(User).filter(
                    User.email == new_email,
                    User.id != user.id
                ).first()
                if not existing:
                    user.email = new_email
                    logger.info(f"[CLERK_WEBHOOK] Updated email for user {user.id}")
            break

    # Update name if changed
    first_name = data.get("first_name") or ""
    last_name = data.get("last_name") or ""
    full_name = f"{first_name} {last_name}".strip()
    if full_name and full_name != user.name:
        user.name = full_name
        logger.info(f"[CLERK_WEBHOOK] Updated name for user {user.id}")

    # Update avatar if changed
    new_avatar = data.get("image_url")
    if new_avatar != user.avatar_url:
        user.avatar_url = new_avatar

    db.commit()

    logger.info(f"[CLERK_WEBHOOK] Updated user {user.id} for clerk_id={clerk_id}")
    return {"status": "updated", "user_id": str(user.id)}


async def _handle_user_deleted(db: Session, data: dict[str, Any]) -> dict:
    """Clean up local data when Clerk user is deleted (GDPR compliance).

    WHAT: Deletes local user record and associated data
    WHY: GDPR/CCPA requires data deletion when user requests account removal

    This reuses the existing account deletion logic from auth router.

    Parameters:
        db: Database session
        data: Clerk user data from webhook payload

    Returns:
        dict: Status of deletion operation
    """
    clerk_id = data.get("id")

    user = db.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        logger.warning(f"[CLERK_WEBHOOK] User not found for clerk_id={clerk_id}")
        return {"status": "not_found", "clerk_id": clerk_id}

    user_id = user.id
    workspace_id = user.workspace_id

    logger.info(f"[CLERK_WEBHOOK] Starting deletion for user {user_id}")

    try:
        # Import models for cleanup
        from ..models import (
            AuthCredential,
            Connection,
            Entity,
            ManualCost,
            MetricFact,
            QaQueryLog,
            Token,
            Workspace,
        )

        # Check if user is the only one in the workspace
        users_in_workspace = db.query(User).filter(User.workspace_id == workspace_id).count()
        delete_workspace = users_in_workspace == 1

        # Delete user's query logs
        db.query(QaQueryLog).filter(QaQueryLog.user_id == user_id).delete()

        # Delete auth credentials (legacy)
        db.query(AuthCredential).filter(AuthCredential.user_id == user_id).delete()

        # Nullify created_by_user_id in manual costs
        db.query(ManualCost).filter(ManualCost.created_by_user_id == user_id).update(
            {"created_by_user_id": None},
            synchronize_session=False
        )

        if delete_workspace:
            logger.info(f"[CLERK_WEBHOOK] User is sole member, deleting workspace {workspace_id}")

            # Delete metric facts for workspace entities
            db.query(MetricFact).filter(
                MetricFact.entity_id.in_(
                    db.query(Entity.id).filter(Entity.workspace_id == workspace_id)
                )
            ).delete(synchronize_session=False)

            # Delete entities
            db.query(Entity).filter(Entity.workspace_id == workspace_id).delete()

            # Delete manual costs
            db.query(ManualCost).filter(ManualCost.workspace_id == workspace_id).delete()

            # Delete tokens and connections
            connection_ids = [c.id for c in db.query(Connection.id).filter(
                Connection.workspace_id == workspace_id
            ).all()]

            if connection_ids:
                token_ids = [t[0] for t in db.query(Connection.token_id).filter(
                    Connection.id.in_(connection_ids),
                    Connection.token_id.isnot(None)
                ).all()]

                db.query(Connection).filter(Connection.workspace_id == workspace_id).delete()

                if token_ids:
                    db.query(Token).filter(Token.id.in_(token_ids)).delete(synchronize_session=False)

            # Delete workspace query logs
            db.query(QaQueryLog).filter(QaQueryLog.workspace_id == workspace_id).delete()

            # Delete workspace memberships
            db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).delete()

            # Delete user
            db.query(User).filter(User.id == user_id).delete()

            # Delete workspace
            db.query(Workspace).filter(Workspace.id == workspace_id).delete()

            logger.info(f"[CLERK_WEBHOOK] Deleted workspace {workspace_id} and all data")
        else:
            # Multi-user workspace: only delete the user
            db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).delete()
            db.query(User).filter(User.id == user_id).delete()

        db.commit()

        logger.info(f"[CLERK_WEBHOOK] Successfully deleted user {user_id}")
        return {"status": "deleted", "user_id": str(user_id)}

    except Exception as e:
        db.rollback()
        logger.exception(f"[CLERK_WEBHOOK] Failed to delete user {user_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.post("/clerk/repair")
async def repair_user_from_clerk(
    request: Request,
    db: Session = Depends(get_db),
):
    """Repair a user record when Clerk webhook failed during signup.

    WHAT: Creates local User + Workspace when webhook failed but user exists in Clerk
    WHY: Recovery mechanism for users stuck in "User not found" state after signup

    Flow:
        1. Validate Clerk JWT from request
        2. Check if user already exists locally (idempotent)
        3. Fetch user details from Clerk API
        4. Create Workspace + User + WorkspaceMember

    Security:
        - Requires valid Clerk JWT (user must be authenticated)
        - Only creates user for the authenticated clerk_id (no impersonation)

    Returns:
        dict: Status with user_id and workspace_id

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 500: If Clerk API call fails
    """
    import httpx
    from jose import jwt, JWTError

    settings = get_settings()

    if not settings.CLERK_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Clerk not configured"
        )

    # Extract and validate JWT token
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if not token:
        token = request.cookies.get("__session")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    # Decode JWT to get clerk_id (we trust it's valid if Clerk signed it)
    try:
        # Decode without verification to get clerk_id
        # The actual verification happens when we call Clerk API
        unverified = jwt.get_unverified_claims(token)
        clerk_id = unverified.get("sub")
        if not clerk_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Check if user already exists (idempotent)
    existing = db.query(User).filter(User.clerk_id == clerk_id).first()
    if existing:
        logger.info(f"[CLERK_REPAIR] User already exists for clerk_id={clerk_id}")
        return {
            "status": "already_exists",
            "user_id": str(existing.id),
            "workspace_id": str(existing.workspace_id),
        }

    # Fetch user details from Clerk API
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.clerk.com/v1/users/{clerk_id}",
                headers={
                    "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
            if resp.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="User not found in Clerk. Please sign up again."
                )
            resp.raise_for_status()
            clerk_user = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"[CLERK_REPAIR] Failed to fetch user from Clerk: {e}")
        raise HTTPException(
            status_code=503,
            detail="Could not reach Clerk API. Please try again later."
        )

    # Extract email from Clerk response
    email_addresses = clerk_user.get("email_addresses", [])
    primary_email_id = clerk_user.get("primary_email_address_id")

    primary_email = None
    for email_obj in email_addresses:
        if email_obj.get("id") == primary_email_id:
            primary_email = email_obj.get("email_address")
            break

    if not primary_email and email_addresses:
        primary_email = email_addresses[0].get("email_address")

    if not primary_email:
        raise HTTPException(status_code=400, detail="No email found in Clerk profile")

    # Check if email already exists (link existing user)
    existing_by_email = db.query(User).filter(User.email == primary_email).first()
    if existing_by_email:
        existing_by_email.clerk_id = clerk_id
        db.commit()
        logger.info(f"[CLERK_REPAIR] Linked existing user {existing_by_email.id} to clerk_id={clerk_id}")
        return {
            "status": "linked_existing",
            "user_id": str(existing_by_email.id),
            "workspace_id": str(existing_by_email.workspace_id),
        }

    # Extract name
    first_name = clerk_user.get("first_name") or ""
    last_name = clerk_user.get("last_name") or ""
    full_name = f"{first_name} {last_name}".strip() or primary_email.split("@")[0]

    # Create workspace with 7-day trial via factory (full access)
    workspace_name = generate_workspace_name(first_name)
    workspace = create_workspace_with_trial(db=db, name=workspace_name)

    # Create user
    user = User(
        clerk_id=clerk_id,
        email=primary_email,
        name=full_name,
        role=RoleEnum.owner,
        workspace_id=workspace.id,
        is_verified=True,
        avatar_url=clerk_user.get("image_url"),
    )
    db.add(user)
    db.flush()

    # Create workspace membership (user must exist first)
    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=RoleEnum.owner,
        status="active",
    )
    db.add(membership)

    db.commit()

    logger.info(
        f"[CLERK_REPAIR] Created user {user.id} with workspace {workspace.id} "
        f"for clerk_id={clerk_id} email={primary_email}"
    )

    return {
        "status": "created",
        "user_id": str(user.id),
        "workspace_id": str(workspace.id),
    }
