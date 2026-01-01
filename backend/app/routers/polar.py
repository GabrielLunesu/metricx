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
"""

import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
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

    async with httpx.AsyncClient() as client:
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


def _verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Polar webhook signature.

    WHAT: Validates the webhook came from Polar
    WHY: Security - prevent forged webhook attacks

    Args:
        payload: Raw request body bytes
        signature: Value from Polar-Signature header

    Returns:
        True if signature is valid
    """
    if not POLAR_WEBHOOK_SECRET:
        logger.warning("POLAR_WEBHOOK_SECRET not set, skipping signature verification")
        return True  # Allow in dev mode

    # Polar uses SHA256 HMAC
    expected = hmac.new(
        POLAR_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


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

    # Check if already subscribed
    if workspace.billing_status in (
        BillingStatusEnum.trialing,
        BillingStatusEnum.active,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace already has an active subscription",
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

    # Update workspace to incomplete state
    workspace.billing_status = BillingStatusEnum.incomplete
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
        - checkout.updated: Link subscription to workspace
        - subscription.active: Mark workspace as active
        - subscription.canceled: Mark workspace as canceled
        - subscription.revoked: Mark workspace as revoked

    Security:
        - Verifies Polar-Signature header
        - Idempotent: skips duplicate events

    Testing:
        - Create actual checkout to generate events
        - Use Polar webhook delivery history "Replay" to resend
    """,
)
async def handle_polar_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Process Polar webhook events."""
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    signature = request.headers.get("Polar-Signature", "")
    if not _verify_webhook_signature(body, signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature"
        )

    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        )

    event_type = payload.get("type", "unknown")
    data = payload.get("data", {})

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
    try:
        action = await _process_webhook_event(event_type, data, db)
        _record_event(event_key, event_type, data.get("id"), payload, "success", db)
        return schemas.WebhookResponse(event_type=event_type, action=action)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        _record_event(
            event_key, event_type, data.get("id"), payload, f"error: {str(e)}", db
        )
        # Still return 200 to prevent Polar from retrying
        return schemas.WebhookResponse(event_type=event_type, action="error")


async def _process_webhook_event(event_type: str, data: dict, db: Session) -> str:
    """Process a specific webhook event type.

    WHAT: Routes event to appropriate handler
    WHY: Different events update workspace billing in different ways
    """
    if event_type == "checkout.updated":
        return await _handle_checkout_updated(data, db)
    elif event_type == "subscription.active":
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
        3. Set billing_status based on checkout status
    """
    checkout_id = data.get("id")
    checkout_status = data.get("status")
    subscription_id = data.get("subscription_id")
    customer_id = data.get("customer_id")

    logger.info(f"Checkout {checkout_id} updated: status={checkout_status}")

    # Find checkout mapping
    mapping = (
        db.query(PolarCheckoutMapping)
        .filter(PolarCheckoutMapping.polar_checkout_id == checkout_id)
        .first()
    )

    if not mapping:
        logger.warning(f"No checkout mapping found for {checkout_id}")
        return "no_mapping"

    # Update mapping
    mapping.status = checkout_status
    mapping.polar_subscription_id = subscription_id

    # Get workspace
    workspace = db.query(Workspace).filter(Workspace.id == mapping.workspace_id).first()

    if not workspace:
        logger.error(f"Workspace not found for mapping: {mapping.workspace_id}")
        return "workspace_not_found"

    # Update workspace based on checkout status
    if checkout_status == "succeeded":
        workspace.polar_subscription_id = subscription_id
        workspace.polar_customer_id = customer_id
        workspace.billing_status = BillingStatusEnum.active
        workspace.billing_tier = BillingPlanEnum.starter  # Upgrade to paid tier
        workspace.billing_plan = mapping.requested_plan
        workspace.pending_since = None  # Clear pending state
        logger.info(
            f"Workspace {workspace.id} upgraded to starter tier with subscription {subscription_id}"
        )
    elif checkout_status == "failed":
        workspace.billing_status = BillingStatusEnum.locked
        logger.info(f"Checkout failed for workspace {workspace.id}")
    elif checkout_status == "expired":
        workspace.billing_status = BillingStatusEnum.locked
        mapping.status = "expired"
        logger.info(f"Checkout expired for workspace {workspace.id}")

    db.commit()
    return "processed"


async def _handle_subscription_active(data: dict, db: Session) -> str:
    """Handle subscription.active webhook.

    WHAT: Updates workspace when subscription becomes active
    WHY: May occur after trial period ends or payment succeeds
    """
    subscription_id = data.get("id")
    customer_id = data.get("customer_id")
    current_period_start = data.get("current_period_start")
    current_period_end = data.get("current_period_end")
    trial_end = data.get("trial_end")

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
        logger.warning(f"No workspace found for subscription {subscription_id}")
        return "workspace_not_found"

    # Update billing state
    workspace.billing_status = BillingStatusEnum.active
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

    logger.info(f"Workspace {workspace.id} subscription active")
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
    WHY: Plan change, period renewal, etc.
    """
    subscription_id = data.get("id")
    status_str = data.get("status")
    current_period_start = data.get("current_period_start")
    current_period_end = data.get("current_period_end")
    trial_end = data.get("trial_end")

    workspace = (
        db.query(Workspace)
        .filter(Workspace.polar_subscription_id == subscription_id)
        .first()
    )

    if not workspace:
        logger.warning(f"No workspace found for subscription {subscription_id}")
        return "workspace_not_found"

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
