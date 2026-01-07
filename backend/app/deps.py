"""Dependency providers and settings management.

WHAT: FastAPI dependencies for auth, database sessions, and configuration
WHY: Centralized dependency injection for consistent auth and settings access
REFERENCES: backend/app/routers/* (all routers use these dependencies)
"""

import logging
from functools import lru_cache
from typing import Optional

import httpx
from fastapi import Cookie, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, Workspace, WorkspaceMember, RoleEnum, BillingStatusEnum
from .security import decode_token

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment or .env."""

    BACKEND_CORS_ORIGINS: str = "https://www.metricx.ai,http://localhost:3000"
    # Cookie domain must NOT include protocol (https://)
    # Set to None for same-origin cookies (works for both localhost and production)
    COOKIE_DOMAIN: Optional[str] = None
    OPENAI_API_KEY: str | None = None

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CONTEXT_MAX_HISTORY: int = 5
    CONTEXT_TTL_SECONDS: int = 3600  # 1 hour

    # Shopify OAuth Configuration
    # WHAT: Shopify Partner app credentials for OAuth flow
    # WHY: Required for shop authentication and API access
    # REFERENCES: https://shopify.dev/docs/apps/auth/oauth
    SHOPIFY_CLIENT_ID: Optional[str] = None
    SHOPIFY_CLIENT_SECRET: Optional[str] = None
    SHOPIFY_SCOPES: str = "read_orders,read_all_orders,read_products,read_customers,read_analytics,read_inventory,read_marketing_events"
    SHOPIFY_REDIRECT_URI: Optional[str] = (
        None  # e.g., https://api.yourapp.com/shopify/callback
    )

    # Clerk Authentication Configuration
    # WHAT: Clerk API keys for JWT validation and webhook verification
    # WHY: Migrated from custom JWT to Clerk for auth (Google OAuth, password reset, etc.)
    # REFERENCES: https://clerk.com/docs
    CLERK_SECRET_KEY: Optional[str] = None
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_WEBHOOK_SECRET: Optional[str] = None

    # Development mode settings
    # WHAT: Auto-provision users when Clerk webhooks can't reach localhost
    # WHY: In local dev, Clerk webhooks don't fire, so users aren't created in DB
    # Set to True in .env for local development
    DEV_AUTO_PROVISION_USERS: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()  # type: ignore[call-arg]


# -----------------------------------------------------------------------------
# Clerk JWKS Cache
# -----------------------------------------------------------------------------
# WHAT: Cache for Clerk's JSON Web Key Set (public keys for JWT verification)
# WHY: Avoids fetching JWKS on every request (performance)
_clerk_jwks_cache: Optional[dict] = None
_clerk_jwks_cache_time: float = 0


async def _fetch_clerk_jwks(issuer: Optional[str] = None) -> dict:
    """Fetch Clerk's JWKS for JWT signature validation.

    WHAT: Retrieves public keys from Clerk's well-known endpoint
    WHY: Required to verify JWT signatures (RS256 algorithm)
    CACHING: Results cached for 1 hour to reduce latency

    Parameters:
        issuer: Optional JWT issuer URL to derive JWKS endpoint from

    Returns:
        dict: JWKS containing public keys

    Raises:
        HTTPException: If JWKS fetch fails
    """
    global _clerk_jwks_cache, _clerk_jwks_cache_time
    import time

    # Return cached JWKS if still valid (1 hour TTL)
    if _clerk_jwks_cache and (time.time() - _clerk_jwks_cache_time) < 3600:
        return _clerk_jwks_cache

    # Determine JWKS URL from issuer (best) or publishable key (fallback)
    jwks_url = None

    if issuer:
        # Use issuer from JWT - most reliable method
        # Issuer is like: https://your-instance.clerk.accounts.dev
        jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
        logger.debug(f"[CLERK] Using issuer-based JWKS URL: {jwks_url}")
    else:
        # Fallback: try to derive from publishable key
        settings = get_settings()
        if not settings.CLERK_PUBLISHABLE_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Clerk not configured",
            )

        try:
            import base64

            key_parts = settings.CLERK_PUBLISHABLE_KEY.split("_")
            if len(key_parts) >= 3:
                encoded_domain = key_parts[-1]
                padding = 4 - len(encoded_domain) % 4
                if padding != 4:
                    encoded_domain += "=" * padding
                frontend_api = (
                    base64.b64decode(encoded_domain).decode("utf-8").rstrip("$")
                )
                jwks_url = f"https://{frontend_api}/.well-known/jwks.json"
        except Exception as e:
            logger.warning(f"[CLERK] Could not decode frontend API from key: {e}")

    if not jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not determine Clerk JWKS URL",
        )

    logger.info(f"[CLERK] Fetching JWKS from {jwks_url}")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_url, timeout=10.0)
            resp.raise_for_status()
            _clerk_jwks_cache = resp.json()
            _clerk_jwks_cache_time = time.time()
            logger.info("[CLERK] JWKS cache refreshed successfully")
            return _clerk_jwks_cache
    except httpx.HTTPError as e:
        logger.error(f"[CLERK] Failed to fetch JWKS from {jwks_url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )


# -----------------------------------------------------------------------------
# Clerk Authentication Dependency
# -----------------------------------------------------------------------------


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Resolve current user from Clerk session token.

    WHAT: Validates Clerk JWT and returns local User record
    WHY: Clerk handles authentication, we handle authorization and data ownership

    Security:
    - Validates JWT signature against Clerk's JWKS (RS256)
    - Checks token expiration
    - Looks up user by clerk_id (not email, which can change)

    Token Sources (in order of preference):
    1. Authorization header: "Bearer <token>"
    2. __session cookie (Clerk's default)

    Parameters:
        request: FastAPI Request object
        db: Database session

    Returns:
        User: Local user record

    Raises:
        HTTPException 401: If not authenticated or token invalid
        HTTPException 404: If user not found in local database
    """
    settings = get_settings()

    # Check if Clerk is configured
    if not settings.CLERK_SECRET_KEY:
        # Fallback to legacy JWT auth for backwards compatibility
        return await _get_current_user_legacy(request, db)

    token = None

    # Try Authorization header first (Bearer token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]

    # Fall back to __session cookie (Clerk's default)
    if not token:
        token = request.cookies.get("__session")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        # First decode without verification to get issuer and key ID
        unverified_header = jwt.get_unverified_header(token)
        unverified_claims = jwt.get_unverified_claims(token)

        kid = unverified_header.get("kid")
        issuer = unverified_claims.get("iss")

        logger.debug(f"[CLERK] Token kid={kid}, issuer={issuer}")

        # Get Clerk's JWKS for signature verification (use issuer for correct URL)
        jwks = await _fetch_clerk_jwks(issuer=issuer)

        # Find matching key in JWKS
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break

        if not rsa_key:
            logger.warning(f"[CLERK] No matching key found for kid={kid} in JWKS")
            # Clear cache and retry once (key might have rotated)
            global _clerk_jwks_cache, _clerk_jwks_cache_time
            _clerk_jwks_cache = None
            _clerk_jwks_cache_time = 0
            jwks = await _fetch_clerk_jwks(issuer=issuer)

            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = key
                    break

            if not rsa_key:
                logger.error(f"[CLERK] Key {kid} not found even after refresh")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                )

        # Decode and validate JWT
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk doesn't require audience
        )

        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

    except JWTError as e:
        logger.warning(f"[CLERK] JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    # Look up user by clerk_id
    user = db.query(User).filter(User.clerk_id == clerk_user_id).first()

    if not user:
        # User exists in Clerk but not in our DB
        settings = get_settings()

        # In development mode, auto-provision the user
        if settings.DEV_AUTO_PROVISION_USERS:
            logger.warning(
                f"[CLERK] Auto-provisioning user for clerk_id={clerk_user_id} (DEV_AUTO_PROVISION_USERS=True)"
            )
            user = await _auto_provision_clerk_user(db, clerk_user_id, settings)
            if user:
                return user

        # If not in dev mode or provisioning failed
        logger.error(f"[CLERK] User not found for clerk_id={clerk_user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please try signing out and back in.",
        )

    return user


async def _auto_provision_clerk_user(
    db: Session,
    clerk_user_id: str,
    settings: Settings,
) -> Optional[User]:
    """Auto-provision a Clerk user in local database (development only).

    WHAT: Fetches user data from Clerk API and creates local User + Workspace
    WHY: In local dev, Clerk webhooks can't reach localhost, so users aren't created

    Args:
        db: Database session
        clerk_user_id: Clerk user ID (e.g., "user_xxx")
        settings: Application settings

    Returns:
        Created User or None if failed
    """
    if not settings.CLERK_SECRET_KEY:
        logger.error("[CLERK] Cannot auto-provision: CLERK_SECRET_KEY not set")
        return None

    try:
        # Fetch user data from Clerk API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.clerk.com/v1/users/{clerk_user_id}",
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
                timeout=10.0,
            )

            if response.status_code != 200:
                logger.error(
                    f"[CLERK] Failed to fetch user from Clerk API: {response.status_code}"
                )
                return None

            clerk_user = response.json()

        # Extract user info
        email_addresses = clerk_user.get("email_addresses", [])
        primary_email_id = clerk_user.get("primary_email_address_id")
        primary_email = None
        for email_obj in email_addresses:
            if email_obj.get("id") == primary_email_id:
                primary_email = email_obj.get("email_address")
                break

        if not primary_email and email_addresses:
            primary_email = email_addresses[0].get("email_address")

        first_name = clerk_user.get("first_name") or ""
        last_name = clerk_user.get("last_name") or ""
        full_name = f"{first_name} {last_name}".strip() or "User"

        # Generate workspace name
        workspace_name = f"{first_name}'s Workspace" if first_name else "My Workspace"

        # Create workspace
        workspace = Workspace(
            name=workspace_name,
            onboarding_completed=False,  # New user needs onboarding
        )
        db.add(workspace)
        db.flush()

        # Create user
        user = User(
            clerk_id=clerk_user_id,
            email=primary_email or f"{clerk_user_id}@placeholder.local",
            name=full_name,
            role=RoleEnum.owner,
            workspace_id=workspace.id,
            is_verified=True,
            avatar_url=clerk_user.get("image_url"),
        )
        db.add(user)
        db.flush()

        # Create workspace membership
        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=RoleEnum.owner,
            status="active",
        )
        db.add(membership)

        db.commit()

        logger.info(
            f"[CLERK] Auto-provisioned user {user.id} with workspace {workspace.id}"
        )
        return user

    except Exception as e:
        logger.exception(f"[CLERK] Failed to auto-provision user: {e}")
        db.rollback()
        return None


async def _get_current_user_legacy(
    request: Request,
    db: Session,
) -> User:
    """Legacy JWT authentication (fallback when Clerk not configured).

    WHAT: Original JWT cookie-based auth
    WHY: Backwards compatibility during migration
    DEPRECATED: Will be removed after Clerk migration is complete
    """
    access_token = request.cookies.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    # Remove optional "Bearer " prefix
    if access_token.startswith("Bearer "):
        token = access_token[len("Bearer ") :]
    else:
        token = access_token

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    user = db.query(User).filter(User.email == subject).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user


# =============================================================================
# SUPERUSER DEPENDENCY
# =============================================================================
# WHAT: Require platform-level superuser access for admin endpoints
# WHY: Admin endpoints need elevated privileges beyond workspace roles


async def require_superuser(
    user: User = Depends(get_current_user),
) -> User:
    """Require superuser status for admin endpoints.

    WHAT: FastAPI dependency that enforces superuser access
    WHY: Admin dashboard needs platform-level access (distinct from workspace roles)

    Parameters:
        user: Authenticated user from get_current_user

    Returns:
        User: Same user, if superuser check passes

    Raises:
        HTTPException 403: If user is not a superuser
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required"
        )
    return user


# =============================================================================
# SUBSCRIPTION GATING DEPENDENCY
# =============================================================================
# WHAT: Enforce subscription status before accessing gated routes
# WHY: Per-workspace billing - only trialing/active workspaces can access
# REFERENCES: openspec/changes/add-polar-workspace-billing/design.md


def _is_billing_allowed(billing_status: BillingStatusEnum) -> bool:
    """Check if billing status allows access to subscription-gated routes.

    WHAT: Returns True for trialing/active, False for everything else
    WHY: Central logic for access gating decisions
    """
    return billing_status in (BillingStatusEnum.trialing, BillingStatusEnum.active)


async def require_active_subscription(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """Require active subscription for the user's current workspace.

    WHAT: FastAPI dependency that enforces subscription gating
    WHY: /onboarding, /dashboard, and other routes require paid access

    Behavior:
        - If workspace billing_status is trialing or active: allow access
        - If blocked: raise HTTPException with appropriate status code

    Status codes:
        - 402 Payment Required: Workspace needs subscription
        - 403 Forbidden: User cannot manage billing (not owner/admin)

    Parameters:
        request: FastAPI Request (for logging)
        db: Database session
        current_user: Authenticated user from get_current_user

    Returns:
        User: Same user, if subscription check passes

    Raises:
        HTTPException 402: Workspace needs subscription
        HTTPException 403: User is member but cannot manage billing
    """
    # Get user's active workspace
    workspace = (
        db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    )

    if not workspace:
        logger.error(f"[BILLING] Workspace not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )

    # Check if billing status allows access
    if _is_billing_allowed(workspace.billing_status):
        return current_user

    # Check if user can manage billing (owner or admin)
    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.status == "active",
        )
        .first()
    )

    can_manage_billing = membership and membership.role in (
        RoleEnum.owner,
        RoleEnum.admin,
    )

    # Build response based on user role
    if can_manage_billing:
        # Owner/Admin should be redirected to subscribe
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "subscription_required",
                "message": "This workspace requires an active subscription",
                "workspace_id": str(workspace.id),
                "billing_status": workspace.billing_status.value,
                "can_manage_billing": True,
                "redirect_url": f"/subscribe?workspaceId={workspace.id}",
            },
        )
    else:
        # Viewer/Member cannot manage billing
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "subscription_required_not_admin",
                "message": "This workspace requires an active subscription. Please ask your workspace owner or admin to subscribe.",
                "workspace_id": str(workspace.id),
                "billing_status": workspace.billing_status.value,
                "can_manage_billing": False,
            },
        )
