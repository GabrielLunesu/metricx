"""Polar billing integration endpoints.

WHAT: Handles Polar checkout creation and webhook processing
WHY: Per-workspace billing - each workspace needs its own subscription

Key flows:
    1. Checkout: POST /billing/checkout → create Polar checkout, persist mapping
    2. Webhook: POST /webhooks/polar → process checkout.updated, subscription.*
    3. Status: GET /billing/status → return workspace billing state
    4. Portal: GET /billing/portal → redirect to Polar customer portal

REFERENCES:
    - openspec/changes/add-polar-workspace-billing/proposal.md
    - openspec/changes/add-polar-workspace-billing/design.md
    - .codex/polar.md (Polar API reference)
    - https://docs.polar.sh/developers/webhooks

WEBHOOK EVENTS HANDLED:
    - checkout.created: Checkout session created (informational)
    - checkout.updated: Checkout completed/failed - this is the main upgrade event
    - subscription.created: New subscription created (may be pending payment)
    - subscription.updated: Subscription status changed (active, canceled, etc.)
    - subscription.canceled: Subscription canceled
    - subscription.revoked: Subscription revoked (fraud, chargeback)
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from polar_sdk.webhooks import validate_event, WebhookVerificationError
from sqlalchemy import and_
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import get_current_user
from ..models import (
    BillingStatusEnum,
    BillingPlanEnum,
    PolarCheckoutMapping,
    PolarWebhookEvent,
    RoleEnum,
    User,
    Workspace,
    WorkspaceMember,
)

logger = logging.getLogger(__name__)

# Environment configuration
POLAR_API_URL = os.getenv("POLAR_API_URL", "https://api.polar.sh")
POLAR_ACCESS_TOKEN = os.getenv("POLAR_ACCESS_TOKEN", "")
POLAR_WEBHOOK_SECRET = os.getenv("POLAR_WEBHOOK_SECRET", "")
POLAR_ORGANIZATION_ID = os.getenv("POLAR_ORGANIZATION_ID", "")

# Product IDs (set in environment or Polar dashboard)
POLAR_MONTHLY_PRODUCT_ID = os.getenv("POLAR_MONTHLY_PRODUCT_ID", "")
POLAR_ANNUAL_PRODUCT_ID = os.getenv("POLAR_ANNUAL_PRODUCT_ID", "")

# Frontend URLs for redirects
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


router = APIRouter(
    prefix="/billing",
    tags=["Billing"],
    responses={
        401: {"model": schemas.ErrorResponse, "description": "Unauthorized"},
        403: {"model": schemas.ErrorResponse, "description": "Forbidden"},
        500: {"model": schemas.ErrorResponse, "description": "Internal Server Error"},
    },
)

webhook_router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _is_access_allowed(billing_status: BillingStatusEnum) -> bool:
    """Check if billing status allows access to subscription-gated routes.

    WHAT: Returns True for trialing/active, False for everything else
    WHY: Central logic for access gating decisions
    """
    return billing_status in (BillingStatusEnum.trialing, BillingStatusEnum.active)


def _can_manage_billing(user: User, workspace_id: UUID, db: Session) -> bool:
    """Check if user can manage billing for a workspace.

    WHAT: Returns True if user is Owner or Admin of the workspace
    WHY: Only Owner/Admin can create checkouts, access portal
    """
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
        return False
    return membership.role in (RoleEnum.owner, RoleEnum.admin)


def _get_product_id_for_plan(plan: str) -> str:
    """Get Polar product ID for a plan type.

    WHAT: Maps plan name to Polar product ID
    WHY: Different products for monthly vs annual plans
    """
    if plan == "monthly":
        if not POLAR_MONTHLY_PRODUCT_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Monthly product not configured",
            )
        return POLAR_MONTHLY_PRODUCT_ID
    elif plan == "annual":
        if not POLAR_ANNUAL_PRODUCT_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Annual product not configured",
            )
        return POLAR_ANNUAL_PRODUCT_ID
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid plan: {plan}"
        )


async def _create_polar_checkout(
    product_id: str,
    customer_email: str,
    success_url: str,
    metadata: dict = None,
) -> dict:
    """Create a Polar checkout session via API.

    WHAT: Calls Polar API to create checkout
    WHY: User is redirected to Polar to complete payment

    Returns:
        dict with id, client_secret, url, etc.

    REFERENCES:
        - https://polar.sh/docs/features/checkout/session
        - https://docs.polar.sh/api-reference/checkouts/create-session
    """
    if not POLAR_ACCESS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Polar API not configured",
        )

    headers = {
        "Authorization": f"Bearer {POLAR_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    # Polar API uses 'products' array with product IDs
    payload = {
        "products": [product_id],
        "success_url": success_url,
        "customer_email": customer_email,
    }
    if metadata:
        payload["metadata"] = metadata

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{POLAR_API_URL}/v1/checkouts/",
            json=payload,
            headers=headers,
            timeout=30.0,
        )

        if response.status_code not in (200, 201):
            logger.error(
                f"Polar checkout creation failed: {response.status_code} {response.text}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to create checkout: {response.text}",
            )

        data = response.json()

        # Log the full response to debug URL format
        logger.info(f"Polar checkout response: {data}")

        # Polar should return url directly, but build fallback if needed
        if not data.get("url"):
            checkout_id = data.get("id")
            client_secret = data.get("client_secret")
            if checkout_id and client_secret:
                # Try the embed URL format
                data["url"] = f"https://checkout.polar.sh/{client_secret}"

        return data


async def _get_polar_customer_portal_url(customer_id: str) -> str:
    """Get Polar customer portal URL for self-service billing.

    WHAT: Retrieves portal session URL from Polar
    WHY: Users can manage payment methods, cancel, view invoices
    """
    if not POLAR_ACCESS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Polar API not configured",
        )

    headers = {
        "Authorization": f"Bearer {POLAR_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.post(
            f"{POLAR_API_URL}/v1/customer-sessions",
            json={"customer_id": customer_id},
            headers=headers,
            timeout=30.0,
        )

        if response.status_code not in (200, 201):
            logger.error(
                f"Polar portal creation failed: {response.status_code} {response.text}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to get billing portal URL",
            )

        data = response.json()
        return data.get("customer_portal_url", "")


# Note: Signature verification is now handled by polar_sdk.webhooks.validate_event
# which uses standard webhook signatures (Svix-based)


def _compute_event_key(event_type: str, data: dict) -> str:
    """Compute idempotency key for webhook event.

    WHAT: Creates unique identifier for deduplication
    WHY: Polar may retry webhooks; we must process each event only once

    Format: {event_type}:{data.id}:{created_at or now}
    """
    data_id = data.get("id", "unknown")
    created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
    return f"{event_type}:{data_id}:{created_at}"


def _is_event_processed(event_key: str, db: Session) -> bool:
    """Check if webhook event was already processed.

    WHAT: Queries PolarWebhookEvent table for existing key
    WHY: Idempotency - skip duplicate events
    """
    existing = (
        db.query(PolarWebhookEvent)
        .filter(PolarWebhookEvent.event_key == event_key)
        .first()
    )
    return existing is not None


def _record_event(
    event_key: str,
    event_type: str,
    data_id: str,
    payload: dict,
    result: str,
    db: Session,
):
    """Record webhook event for idempotency tracking.

    WHAT: Inserts row into PolarWebhookEvent table
    WHY: Future webhook deliveries with same key will be skipped
    """
    event = PolarWebhookEvent(
        event_key=event_key,
        event_type=event_type,
        polar_data_id=data_id,
        payload_json=payload,
        processing_result=result,
    )
    db.add(event)
    db.commit()


# =============================================================================
# BILLING STATUS ENDPOINT
# =============================================================================


@router.get(
    "/status",
    response_model=schemas.WorkspaceBillingStatusResponse,
    summary="Get billing status",
    description="""
    Get billing status for the current user's active workspace.

    Returns:
        - billing_status: locked, trialing, active, canceled, etc.
        - is_access_allowed: whether user can access /onboarding, /dashboard
        - can_manage_billing: whether user can create checkout, access portal
        - portal_url: Polar customer portal URL (if Owner/Admin and has subscription)

    Frontend uses this to:
        - Gate routes (/onboarding, /dashboard)
        - Show subscription status in Settings
        - Provide "Subscribe" or "Manage" CTAs
    """,
)
async def get_billing_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get billing status for current workspace."""
    workspace = (
        db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )

    # Check trial expiry on each billing status request
    # WHY: Frontend-driven expiry - no scheduled job needed
    # WHAT: If trial has expired, downgrade to free tier
    if workspace.billing_status == BillingStatusEnum.trialing:
        if workspace.trial_end and workspace.trial_end < datetime.now(timezone.utc):
            workspace.billing_status = BillingStatusEnum.active
            workspace.billing_tier = BillingPlanEnum.free
            db.commit()
            logger.info(
                f"[BILLING] Workspace {workspace.id} trial expired, "
                f"downgraded to free tier"
            )

    can_manage = _can_manage_billing(current_user, workspace.id, db)
    is_allowed = _is_access_allowed(workspace.billing_status)

    # Get portal URL if user can manage and has subscription
    portal_url = None
    if can_manage and workspace.polar_customer_id:
        try:
            portal_url = await _get_polar_customer_portal_url(
                workspace.polar_customer_id
            )
        except Exception as e:
            logger.warning(f"Failed to get portal URL: {e}")

    billing_info = schemas.BillingInfo(
        billing_status=workspace.billing_status,
        billing_tier=workspace.billing_tier,
        billing_plan=workspace.billing_plan,
        trial_started_at=workspace.trial_started_at,
        trial_end=workspace.trial_end,
        current_period_start=workspace.current_period_start,
        current_period_end=workspace.current_period_end,
        is_access_allowed=is_allowed,
        can_manage_billing=can_manage,
        portal_url=portal_url,
    )

    return schemas.WorkspaceBillingStatusResponse(
        workspace_id=str(workspace.id),
        workspace_name=workspace.name,
        billing=billing_info,
    )


# =============================================================================
# CHECKOUT CREATION ENDPOINT
# =============================================================================


@router.post(
    "/checkout",
    response_model=schemas.CheckoutCreateResponse,
    summary="Create checkout session",
    description="""
    Create a Polar checkout session for a workspace subscription.

    Requirements:
        - User must be Owner or Admin of the workspace
        - Workspace must not already have an active subscription

    Flow:
        1. Validate user can manage billing for workspace
        2. Create Polar checkout via API
        3. Persist checkout → workspace mapping
        4. Return checkout URL for redirect
    """,
)
async def create_checkout(
    payload: schemas.CheckoutCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create Polar checkout session."""
    workspace_id = UUID(payload.workspace_id)

    # Verify workspace exists
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )

    # Check user can manage billing
    if not _can_manage_billing(current_user, workspace_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace Owner or Admin can manage billing",
        )

    # Only block ACTUALLY PAID users (active status + starter tier + has subscription ID)
    # Allow: trialing users (want to upgrade early)
    # Allow: free tier users (trial expired, want to subscribe)
    if (workspace.billing_status == BillingStatusEnum.active
        and workspace.billing_tier == BillingPlanEnum.starter
        and workspace.polar_subscription_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace already has a paid subscription",
        )

    # Get product ID for plan
    product_id = _get_product_id_for_plan(payload.plan)

    # Build redirect URLs
    success_url = payload.success_url or f"{FRONTEND_URL}/dashboard?checkout=success"
    # cancel_url is not used in Polar checkout API

    # Create Polar checkout
    checkout_data = await _create_polar_checkout(
        product_id=product_id,
        customer_email=current_user.email,
        success_url=success_url,
        metadata={"workspace_id": str(workspace_id), "plan": payload.plan},
    )

    checkout_id = checkout_data.get("id")
    checkout_url = checkout_data.get("url")

    if not checkout_id or not checkout_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid checkout response from Polar",
        )

    # Persist checkout mapping
    mapping = PolarCheckoutMapping(
        workspace_id=workspace_id,
        polar_checkout_id=checkout_id,
        requested_plan=payload.plan,
        created_by_user_id=current_user.id,
        status="pending",
    )
    db.add(mapping)

    # Note: Don't change billing_status here - free tier users should keep 'active' status
    # The webhook will update status when checkout completes/fails
    # Only store the pending plan for reference
    workspace.billing_plan = payload.plan

    db.commit()

    logger.info(f"Created checkout {checkout_id} for workspace {workspace_id}")

    return schemas.CheckoutCreateResponse(
        checkout_url=checkout_url,
        checkout_id=checkout_id,
    )


# =============================================================================
# BILLING PORTAL ENDPOINT
# =============================================================================


@router.get(
    "/portal",
    response_model=schemas.BillingPortalResponse,
    summary="Get billing portal URL",
    description="""
    Get Polar customer portal URL for self-service billing management.

    Requirements:
        - User must be Owner or Admin of the workspace
        - Workspace must have a Polar customer ID (from completed checkout)

    Portal allows users to:
        - Update payment method
        - View invoices
        - Cancel subscription
    """,
)
async def get_billing_portal(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Polar customer portal URL."""
    ws_uuid = UUID(workspace_id)

    workspace = db.query(Workspace).filter(Workspace.id == ws_uuid).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )

    if not _can_manage_billing(current_user, ws_uuid, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace Owner or Admin can access billing portal",
        )

    if not workspace.polar_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace does not have an active subscription",
        )

    portal_url = await _get_polar_customer_portal_url(workspace.polar_customer_id)

    return schemas.BillingPortalResponse(portal_url=portal_url)


# =============================================================================
# WEBHOOK ENDPOINT
# =============================================================================


@webhook_router.post(
    "/polar",
    response_model=schemas.WebhookResponse,
    summary="Polar webhook handler",
    description="""
    Receives and processes Polar webhook events.

    Handled events:
        - checkout.updated: Link subscription to workspace, upgrade to starter tier
        - subscription.created: New subscription created (may be pending payment)
        - subscription.updated: Subscription status changed
        - subscription.canceled: Mark workspace as canceled
        - subscription.revoked: Mark workspace as revoked (immediate access cut)

    Security:
        - Uses polar_sdk.webhooks.validate_event for signature verification
        - Idempotent: skips duplicate events via event_key

    Testing:
        - Create actual checkout to generate events
        - Use Polar webhook delivery history "Replay" to resend
    """,
)
async def handle_polar_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Process Polar webhook events using Polar SDK validation."""
    # Get raw body for signature verification
    body = await request.body()

    # Validate webhook using Polar SDK (handles signature verification)
    # IMPORTANT: Always use raw JSON for storage to avoid datetime serialization issues
    import json

    raw_payload = json.loads(body)

    try:
        if not POLAR_WEBHOOK_SECRET:
            logger.warning(
                "POLAR_WEBHOOK_SECRET not set - webhook verification disabled (dev mode)"
            )
            # In dev mode, use raw payload directly
            event_type = raw_payload.get("type", "unknown")
            data = raw_payload.get("data", {})
            payload = raw_payload  # Store raw JSON (strings, not datetime objects)
        else:
            # Use Polar SDK for signature verification only
            # We still use the raw JSON for data to avoid datetime serialization issues
            event = validate_event(
                body=body,
                headers=dict(request.headers),
                secret=POLAR_WEBHOOK_SECRET,
            )

            # Polar SDK v0.28+ uses TYPE (uppercase) as the discriminator field
            if hasattr(event, "TYPE"):
                event_type = event.TYPE
            elif hasattr(event, "type"):
                event_type = event.type
            else:
                event_type = raw_payload.get("type", "unknown")

            # CRITICAL: Use raw JSON data, NOT the Pydantic model
            # Pydantic converts datetime strings to datetime objects which can't be JSON serialized
            data = raw_payload.get("data", {})
            payload = raw_payload  # Store raw JSON (strings, not datetime objects)

            logger.info(
                f"Parsed webhook: type={event_type}, data_keys={list(data.keys()) if isinstance(data, dict) else 'N/A'}"
            )

    except WebhookVerificationError as e:
        logger.warning(f"Webhook signature verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
        )
    except Exception as e:
        logger.error(f"Failed to parse/validate webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid webhook payload: {str(e)}",
        )

    logger.info(f"Received Polar webhook: {event_type}")

    # Compute idempotency key
    event_key = _compute_event_key(event_type, data)

    # Check if already processed
    if _is_event_processed(event_key, db):
        logger.info(f"Skipping duplicate event: {event_key}")
        return schemas.WebhookResponse(
            event_type=event_type,
            action="skipped",
        )

    # Process event
    data_id = data.get("id", "unknown")
    try:
        action = await _process_webhook_event(event_type, data, db)
        _record_event(event_key, event_type, data_id, payload, "success", db)
        return schemas.WebhookResponse(event_type=event_type, action=action)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        _record_event(event_key, event_type, data_id, payload, f"error: {str(e)}", db)
        # Still return 200 to prevent Polar from retrying
        return schemas.WebhookResponse(event_type=event_type, action="error")


async def _process_webhook_event(event_type: str, data: dict, db: Session) -> str:
    """Process a specific webhook event type.

    WHAT: Routes event to appropriate handler
    WHY: Different events update workspace billing in different ways

    Event types from Polar:
        - checkout.created: Checkout session started (informational)
        - checkout.updated: Checkout completed/failed - MAIN UPGRADE PATH
        - subscription.created: New subscription created (may be pending)
        - subscription.updated: Status change (active, canceled, past_due, etc.)
        - subscription.canceled: Subscription canceled
        - subscription.revoked: Subscription revoked (fraud, chargeback)
    """
    if event_type == "checkout.created":
        logger.info(f"Checkout created: {data.get('id')}")
        return "acknowledged"
    elif event_type == "checkout.updated":
        return await _handle_checkout_updated(data, db)
    elif event_type == "subscription.created":
        return await _handle_subscription_created(data, db)
    elif event_type == "subscription.active":
        # subscription.active is sent when subscription becomes active
        return await _handle_subscription_active(data, db)
    elif event_type == "subscription.canceled":
        return await _handle_subscription_canceled(data, db)
    elif event_type == "subscription.revoked":
        return await _handle_subscription_revoked(data, db)
    elif event_type == "subscription.updated":
        return await _handle_subscription_updated(data, db)
    else:
        logger.info(f"Unhandled event type: {event_type}")
        return "ignored"


async def _handle_checkout_updated(data: dict, db: Session) -> str:
    """Handle checkout.updated webhook.

    WHAT: Links Polar subscription to workspace when checkout completes
    WHY: This is how we know checkout was successful and can activate subscription

    Flow:
        1. Lookup checkout mapping by checkout_id
        2. If found, update workspace with subscription_id, customer_id
        3. Set billing_status based on checkout state/status

    IMPORTANT: Polar uses 'status' field with values like 'succeeded', 'confirmed', 'open',
    'expired', 'failed'. Check for success states to upgrade.
    """
    checkout_id = data.get("id")
    # Polar SDK uses 'status' field - check for various success indicators
    checkout_status = data.get("status", "")
    subscription_id = data.get("subscription_id")
    customer_id = data.get("customer_id")
    metadata = data.get("metadata", {})

    logger.info(
        f"Checkout {checkout_id} updated: status={checkout_status}, metadata={metadata}, data keys={list(data.keys())}"
    )

    # Find checkout mapping
    mapping = (
        db.query(PolarCheckoutMapping)
        .filter(PolarCheckoutMapping.polar_checkout_id == checkout_id)
        .first()
    )

    # Fallback: If no mapping found, try to find workspace directly via metadata
    workspace = None
    if not mapping:
        workspace_id_str = metadata.get("workspace_id")
        if workspace_id_str:
            logger.info(
                f"No checkout mapping for {checkout_id}, trying metadata workspace_id={workspace_id_str}"
            )
            try:
                workspace = (
                    db.query(Workspace)
                    .filter(Workspace.id == UUID(workspace_id_str))
                    .first()
                )
            except (ValueError, TypeError):
                logger.warning(f"Invalid workspace_id in metadata: {workspace_id_str}")

        if not workspace:
            logger.warning(
                f"No checkout mapping found for {checkout_id} and no valid workspace in metadata"
            )
            return "no_mapping"
    else:
        # We have a mapping - update it and get workspace from it
        mapping.status = checkout_status
        mapping.polar_subscription_id = subscription_id
        workspace = (
            db.query(Workspace).filter(Workspace.id == mapping.workspace_id).first()
        )

    if not workspace:
        logger.error(f"Workspace not found for checkout {checkout_id}")
        return "workspace_not_found"

    # Update workspace based on checkout status
    # Polar checkout status values: 'open', 'expired', 'confirmed', 'succeeded', 'failed'
    # Success states: 'succeeded', 'confirmed' (payment completed)
    success_states = ("succeeded", "confirmed")
    failure_states = ("failed",)
    expired_states = ("expired",)

    # Get plan from mapping if available, otherwise from metadata
    requested_plan = (
        mapping.requested_plan if mapping else metadata.get("plan", "monthly")
    )

    if checkout_status in success_states:
        workspace.polar_subscription_id = subscription_id
        workspace.polar_customer_id = customer_id
        workspace.billing_status = BillingStatusEnum.active
        workspace.billing_tier = BillingPlanEnum.starter  # Upgrade to paid tier
        workspace.billing_plan = requested_plan
        workspace.pending_since = None  # Clear pending state
        logger.info(
            f"Workspace {workspace.id} upgraded to starter tier with subscription {subscription_id}"
        )
    elif checkout_status in failure_states:
        # Don't lock the workspace on checkout failure - they can try again
        logger.info(f"Checkout failed for workspace {workspace.id}")
    elif checkout_status in expired_states:
        if mapping:
            mapping.status = "expired"
        logger.info(f"Checkout expired for workspace {workspace.id}")
    elif checkout_status == "open":
        # Checkout is still open, user hasn't completed payment yet
        logger.info(f"Checkout {checkout_id} still open for workspace {workspace.id}")
    else:
        logger.warning(
            f"Unknown checkout status: {checkout_status} for checkout {checkout_id}"
        )

    db.commit()
    return "processed"


async def _handle_subscription_created(data: dict, db: Session) -> str:
    """Handle subscription.created webhook.

    WHAT: Updates workspace when a new subscription is created
    WHY: Subscription may be created before or after checkout.updated - ensures upgrade

    IMPORTANT: This sets billing_tier = starter to grant full features.
    Even if checkout.updated already ran, this is idempotent.
    """
    subscription_id = data.get("id")
    customer_id = data.get("customer_id")
    subscription_status = data.get("status", "active")  # Polar subscription status
    current_period_start = data.get("current_period_start")
    current_period_end = data.get("current_period_end")
    trial_end = data.get("trial_end")
    metadata = data.get("metadata", {})

    logger.info(
        f"Subscription created: {subscription_id} status={subscription_status}, metadata={metadata}"
    )

    # Try to find workspace by subscription ID first
    workspace = (
        db.query(Workspace)
        .filter(Workspace.polar_subscription_id == subscription_id)
        .first()
    )

    if not workspace:
        # Try to find by checkout mapping
        mapping = (
            db.query(PolarCheckoutMapping)
            .filter(PolarCheckoutMapping.polar_subscription_id == subscription_id)
            .first()
        )
        if mapping:
            workspace = (
                db.query(Workspace).filter(Workspace.id == mapping.workspace_id).first()
            )

    if not workspace:
        # Try to find by customer_id (fallback)
        if customer_id:
            workspace = (
                db.query(Workspace)
                .filter(Workspace.polar_customer_id == customer_id)
                .first()
            )

    if not workspace:
        # Final fallback: try metadata.workspace_id
        workspace_id_str = metadata.get("workspace_id")
        if workspace_id_str:
            logger.info(
                f"Trying metadata workspace_id={workspace_id_str} for subscription {subscription_id}"
            )
            try:
                workspace = (
                    db.query(Workspace)
                    .filter(Workspace.id == UUID(workspace_id_str))
                    .first()
                )
            except (ValueError, TypeError):
                logger.warning(f"Invalid workspace_id in metadata: {workspace_id_str}")

    if not workspace:
        logger.warning(f"No workspace found for subscription {subscription_id}")
        return "workspace_not_found"

    # Update billing state - ALWAYS upgrade to starter tier when subscription is created
    workspace.billing_status = BillingStatusEnum.active
    workspace.billing_tier = BillingPlanEnum.starter  # CRITICAL: Upgrade to paid tier
    workspace.polar_subscription_id = subscription_id
    if customer_id:
        workspace.polar_customer_id = customer_id

    # Update period timestamps
    if current_period_start:
        workspace.current_period_start = datetime.fromisoformat(
            current_period_start.replace("Z", "+00:00")
        )
    if current_period_end:
        workspace.current_period_end = datetime.fromisoformat(
            current_period_end.replace("Z", "+00:00")
        )
    if trial_end:
        workspace.trial_end = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))

    workspace.pending_since = None
    db.commit()

    logger.info(
        f"Workspace {workspace.id} upgraded to starter tier with subscription {subscription_id}"
    )
    return "processed"


async def _handle_subscription_active(data: dict, db: Session) -> str:
    """Handle subscription.active webhook.

    WHAT: Updates workspace when subscription becomes active
    WHY: This is sent when trial converts to paid, or payment succeeds

    IMPORTANT: This sets billing_tier = starter to grant full features.
    """
    subscription_id = data.get("id")
    customer_id = data.get("customer_id")
    current_period_start = data.get("current_period_start")
    current_period_end = data.get("current_period_end")
    metadata = data.get("metadata", {})

    logger.info(f"Subscription active: {subscription_id}, metadata={metadata}")

    # Try to find workspace by subscription ID
    workspace = (
        db.query(Workspace)
        .filter(Workspace.polar_subscription_id == subscription_id)
        .first()
    )

    if not workspace:
        # Try to find by checkout mapping
        mapping = (
            db.query(PolarCheckoutMapping)
            .filter(PolarCheckoutMapping.polar_subscription_id == subscription_id)
            .first()
        )
        if mapping:
            workspace = (
                db.query(Workspace).filter(Workspace.id == mapping.workspace_id).first()
            )

    if not workspace and customer_id:
        # Try to find by customer_id (fallback)
        workspace = (
            db.query(Workspace)
            .filter(Workspace.polar_customer_id == customer_id)
            .first()
        )

    if not workspace:
        # Final fallback: try metadata.workspace_id
        workspace_id_str = metadata.get("workspace_id")
        if workspace_id_str:
            logger.info(
                f"Trying metadata workspace_id={workspace_id_str} for subscription {subscription_id}"
            )
            try:
                workspace = (
                    db.query(Workspace)
                    .filter(Workspace.id == UUID(workspace_id_str))
                    .first()
                )
            except (ValueError, TypeError):
                logger.warning(f"Invalid workspace_id in metadata: {workspace_id_str}")

    if not workspace:
        logger.warning(f"No workspace found for subscription {subscription_id}")
        return "workspace_not_found"

    # Update billing state - subscription is now active
    workspace.billing_status = BillingStatusEnum.active
    workspace.billing_tier = BillingPlanEnum.starter  # CRITICAL: Upgrade to paid tier
    workspace.polar_subscription_id = subscription_id
    if customer_id:
        workspace.polar_customer_id = customer_id

    # Update period timestamps
    if current_period_start:
        workspace.current_period_start = datetime.fromisoformat(
            current_period_start.replace("Z", "+00:00")
        )
    if current_period_end:
        workspace.current_period_end = datetime.fromisoformat(
            current_period_end.replace("Z", "+00:00")
        )

    workspace.pending_since = None
    db.commit()

    logger.info(
        f"Workspace {workspace.id} subscription active - upgraded to starter tier"
    )
    return "processed"


async def _handle_subscription_canceled(data: dict, db: Session) -> str:
    """Handle subscription.canceled webhook.

    WHAT: Updates workspace when subscription is canceled
    WHY: User may still have access until period end; after that, blocked
    """
    subscription_id = data.get("id")
    cancel_at_period_end = data.get("cancel_at_period_end", True)
    current_period_end = data.get("current_period_end")

    workspace = (
        db.query(Workspace)
        .filter(Workspace.polar_subscription_id == subscription_id)
        .first()
    )

    if not workspace:
        logger.warning(f"No workspace found for subscription {subscription_id}")
        return "workspace_not_found"

    # Mark as canceled
    workspace.billing_status = BillingStatusEnum.canceled

    # Update period end if provided
    if current_period_end:
        workspace.current_period_end = datetime.fromisoformat(
            current_period_end.replace("Z", "+00:00")
        )

    db.commit()

    logger.info(
        f"Workspace {workspace.id} subscription canceled (cancel_at_period_end={cancel_at_period_end})"
    )
    return "processed"


async def _handle_subscription_revoked(data: dict, db: Session) -> str:
    """Handle subscription.revoked webhook.

    WHAT: Updates workspace when subscription is revoked (immediate cutoff)
    WHY: Fraud, chargeback, manual revocation - access blocked immediately
    """
    subscription_id = data.get("id")

    workspace = (
        db.query(Workspace)
        .filter(Workspace.polar_subscription_id == subscription_id)
        .first()
    )

    if not workspace:
        logger.warning(f"No workspace found for subscription {subscription_id}")
        return "workspace_not_found"

    workspace.billing_status = BillingStatusEnum.revoked
    db.commit()

    logger.info(f"Workspace {workspace.id} subscription revoked")
    return "processed"


async def _handle_subscription_updated(data: dict, db: Session) -> str:
    """Handle subscription.updated webhook.

    WHAT: Updates workspace when subscription details change
    WHY: Plan change, period renewal, status changes (active, trialing, canceled, etc.)

    IMPORTANT: When status is 'active' or 'trialing', ensure billing_tier = starter
    to grant full features. This handles cases where subscription becomes active
    after payment processing completes.
    """
    subscription_id = data.get("id")
    status_str = data.get("status")
    current_period_start = data.get("current_period_start")
    current_period_end = data.get("current_period_end")
    trial_end = data.get("trial_end")
    customer_id = data.get("customer_id")
    metadata = data.get("metadata", {})

    logger.info(
        f"Subscription updated: {subscription_id} status={status_str}, metadata={metadata}"
    )

    # Try to find workspace by subscription ID first
    workspace = (
        db.query(Workspace)
        .filter(Workspace.polar_subscription_id == subscription_id)
        .first()
    )

    if not workspace:
        # Try to find by checkout mapping (subscription_id may be set there first)
        mapping = (
            db.query(PolarCheckoutMapping)
            .filter(PolarCheckoutMapping.polar_subscription_id == subscription_id)
            .first()
        )
        if mapping:
            workspace = (
                db.query(Workspace).filter(Workspace.id == mapping.workspace_id).first()
            )

    if not workspace and customer_id:
        # Try to find by customer_id (fallback)
        workspace = (
            db.query(Workspace)
            .filter(Workspace.polar_customer_id == customer_id)
            .first()
        )

    if not workspace:
        # Final fallback: try metadata.workspace_id
        workspace_id_str = metadata.get("workspace_id")
        if workspace_id_str:
            logger.info(
                f"Trying metadata workspace_id={workspace_id_str} for subscription {subscription_id}"
            )
            try:
                workspace = (
                    db.query(Workspace)
                    .filter(Workspace.id == UUID(workspace_id_str))
                    .first()
                )
            except (ValueError, TypeError):
                logger.warning(f"Invalid workspace_id in metadata: {workspace_id_str}")

    if not workspace:
        logger.warning(f"No workspace found for subscription {subscription_id}")
        return "workspace_not_found"

    # Update workspace with subscription_id if not set
    if not workspace.polar_subscription_id:
        workspace.polar_subscription_id = subscription_id
    if customer_id and not workspace.polar_customer_id:
        workspace.polar_customer_id = customer_id

    # Map Polar status to our billing status
    status_map = {
        "active": BillingStatusEnum.active,
        "trialing": BillingStatusEnum.trialing,
        "canceled": BillingStatusEnum.canceled,
        "past_due": BillingStatusEnum.past_due,
        "incomplete": BillingStatusEnum.incomplete,
    }
    if status_str in status_map:
        workspace.billing_status = status_map[status_str]

        # CRITICAL: When subscription is active or trialing, ensure starter tier
        # This handles: trial start, trial-to-active conversion, payment success
        if status_str in ("active", "trialing"):
            workspace.billing_tier = BillingPlanEnum.starter
            logger.info(
                f"Workspace {workspace.id} upgraded to starter tier (status: {status_str})"
            )

    # Update timestamps
    if current_period_start:
        workspace.current_period_start = datetime.fromisoformat(
            current_period_start.replace("Z", "+00:00")
        )
    if current_period_end:
        workspace.current_period_end = datetime.fromisoformat(
            current_period_end.replace("Z", "+00:00")
        )
    if trial_end:
        workspace.trial_end = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))

    db.commit()

    logger.info(f"Workspace {workspace.id} subscription updated: status={status_str}")
    return "processed"
