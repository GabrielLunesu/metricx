"""Shopify OAuth 2.0 flow endpoints.

WHAT:
    Implements OAuth authorization flow for user-initiated Shopify store connections.
    Creates Connection and ShopifyShop records for connected stores.

WHY:
    Allows users to connect their Shopify stores for:
    - Order data (revenue, profit tracking)
    - Product catalog (COGS for profit calculations)
    - Customer data (LTV calculations)

REFERENCES:
    - Shopify OAuth: https://shopify.dev/docs/apps/auth/oauth
    - Implementation plan: docs/living-docs/SHOPIFY_INTEGRATION_PLAN.md
    - Similar pattern: backend/app/routers/meta_oauth.py
"""

import os
import re
import logging
import uuid
import json
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx
from jose import jwt, JWTError

from app.database import get_db
from app.deps import get_current_user
from app.models import User, Connection, ProviderEnum, Workspace, ShopifyShop
from app.services.token_service import store_connection_token
from app.services.pixel_activation_service import activate_pixel_for_connection
from app.telemetry import track_connected_shopify

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/shopify", tags=["Shopify OAuth"])

# =============================================================================
# CONFIGURATION
# =============================================================================
# WHAT: Shopify OAuth app credentials and settings
# WHY: Required for OAuth flow - obtain from Shopify Partners dashboard
# REFERENCES: https://shopify.dev/docs/apps/getting-started/create

# Load env vars at module level (may be None if not configured)
# WHAT: Use os.getenv with None defaults for flexible startup
# WHY: Allow app to start without Shopify configured, validate at endpoint level
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
SHOPIFY_REDIRECT_URI = os.getenv("SHOPIFY_OAUTH_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")


def _validate_shopify_config() -> None:
    """Validate Shopify OAuth configuration.

    WHAT: Check that all required Shopify env vars are set
    WHY: Fail gracefully with clear error when endpoint is called without config

    Raises:
        HTTPException: 503 if any required config is missing
    """
    missing = []
    if not SHOPIFY_API_KEY:
        missing.append("SHOPIFY_API_KEY")
    if not SHOPIFY_API_SECRET:
        missing.append("SHOPIFY_API_SECRET")
    if not SHOPIFY_REDIRECT_URI:
        missing.append("SHOPIFY_OAUTH_REDIRECT_URI")
    if not FRONTEND_URL:
        missing.append("FRONTEND_URL")

    if missing:
        logger.error("[SHOPIFY_OAUTH] Missing required environment variables: %s", missing)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Shopify integration not configured. Missing: {', '.join(missing)}"
        )

# API version - update periodically to use latest stable
# WHAT: Shopify API version string
# WHY: Shopify requires explicit version in all API calls
# REFERENCES: https://shopify.dev/docs/api/usage/versioning
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-01")

# OAuth scopes for full analytics access
# WHAT: Permissions requested during OAuth
# WHY: Need orders, products, customers, analytics, inventory, marketing for full integration
# REFERENCES: https://shopify.dev/docs/api/usage/access-scopes
SHOPIFY_SCOPES = [
    "read_orders",           # Order data for revenue/profit
    "read_all_orders",       # Historical orders (>60 days)
    "read_products",         # Product catalog with pricing
    # "read_customers",      # Requires protected customer data approval - skipped
    "read_analytics",        # Shop analytics
    "read_inventory",        # Inventory levels and cost
    "read_marketing_events", # Marketing attribution data
    # Attribution engine scopes (Web Pixel Extension)
    "write_pixels",          # Create and configure web pixels
    "read_customer_events",  # Read customer browsing behavior from pixel
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def normalize_shop_domain(shop_input: str) -> str:
    """Normalize shop domain to myshopify.com format.

    WHAT: Convert various shop input formats to canonical domain
    WHY: Users may enter 'myshop', 'myshop.myshopify.com', or full URL

    Examples:
        'myshop' -> 'myshop.myshopify.com'
        'myshop.myshopify.com' -> 'myshop.myshopify.com'
        'https://myshop.myshopify.com/admin' -> 'myshop.myshopify.com'
    """
    # Remove whitespace
    shop = shop_input.strip().lower()

    # If it's a full URL, extract the hostname
    if shop.startswith('http://') or shop.startswith('https://'):
        parsed = urlparse(shop)
        shop = parsed.netloc or parsed.path.split('/')[0]

    # Remove any path components
    shop = shop.split('/')[0]

    # If it doesn't end with .myshopify.com, append it
    if not shop.endswith('.myshopify.com'):
        # Remove any other domain suffix if present
        shop = shop.replace('.myshopify.com', '')
        shop = f"{shop}.myshopify.com"

    return shop


def validate_shop_domain(shop_domain: str) -> bool:
    """Validate that shop domain is a valid Shopify store domain.

    WHAT: Check domain format matches Shopify pattern
    WHY: Prevent OAuth attempts with invalid domains
    """
    # Must be format: {store-name}.myshopify.com
    # Store name: alphanumeric and hyphens, 3-100 chars
    pattern = r'^[a-z0-9][a-z0-9\-]{1,98}[a-z0-9]\.myshopify\.com$'
    return bool(re.match(pattern, shop_domain.lower()))


def extract_utms(landing_site: Optional[str]) -> dict:
    """Extract UTM parameters from landing site URL.

    WHAT: Parse UTM tags from URL query string
    WHY: Enable basic attribution without full attribution engine
    REFERENCES: Order.landingSite contains full URL with query params
    """
    if not landing_site:
        return {}

    try:
        parsed = urlparse(landing_site)
        params = parse_qs(parsed.query)
        return {
            'utm_source': params.get('utm_source', [None])[0],
            'utm_medium': params.get('utm_medium', [None])[0],
            'utm_campaign': params.get('utm_campaign', [None])[0],
            'utm_content': params.get('utm_content', [None])[0],
            'utm_term': params.get('utm_term', [None])[0],
        }
    except Exception:
        return {}


def append_query_params(url: str, extra_params: dict[str, str]) -> str:
    """Append or replace query params on a relative or absolute URL."""
    parsed = urlparse(url)
    existing = parse_qs(parsed.query, keep_blank_values=True)

    for key, value in extra_params.items():
        existing[key] = [value]

    return urlunparse(parsed._replace(query=urlencode(existing, doseq=True)))


def verify_shopify_session_token(token: str) -> dict:
    """Decode and verify a Shopify session token from App Bridge."""
    _validate_shopify_config()

    try:
        claims = jwt.decode(
            token,
            SHOPIFY_API_SECRET,
            algorithms=["HS256"],
            audience=SHOPIFY_API_KEY,
        )
    except JWTError as exc:
        logger.warning("[SHOPIFY_SESSION] Invalid session token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Shopify session token",
        ) from exc

    issuer_host = urlparse(claims.get("iss", "")).hostname
    dest_host = urlparse(claims.get("dest", "")).hostname

    if not issuer_host or not dest_host or issuer_host != dest_host:
        logger.warning(
            "[SHOPIFY_SESSION] Token issuer/destination mismatch: iss=%s dest=%s",
            claims.get("iss"),
            claims.get("dest"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Shopify session token",
        )

    return claims


def build_shopify_frontend_redirect(
    redirect_path: Optional[str],
    *,
    status_value: str,
    message: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """Build a safe frontend redirect URL for Shopify OAuth completion."""
    safe_redirect = "/settings"
    if redirect_path and redirect_path.startswith("/") and not redirect_path.startswith("//"):
        safe_redirect = redirect_path

    params = {"shopify_oauth": status_value}
    if message:
        params["message"] = message
    if session_id:
        params["session_id"] = session_id

    return append_query_params(f"{FRONTEND_URL}{safe_redirect}", params)


def extract_redirect_path_from_state(state: Optional[str]) -> str:
    """Best-effort redirect path extraction for Shopify OAuth callbacks."""
    if not state:
        return "/settings"

    try:
        state_data = json.loads(state)
    except (json.JSONDecodeError, TypeError):
        return "/settings"

    redirect_path = state_data.get("redirect_path")
    if isinstance(redirect_path, str) and redirect_path.startswith("/") and not redirect_path.startswith("//"):
        return redirect_path

    return "/settings"


def build_shopify_authorize_url(
    *,
    shop: str,
    redirect_path: Optional[str],
    current_user: User,
) -> str:
    """Build a Shopify OAuth consent URL for the current user."""
    _validate_shopify_config()

    shop_domain = normalize_shop_domain(shop)
    if not validate_shop_domain(shop_domain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Shopify store domain: {shop_domain}. Expected format: mystore.myshopify.com"
        )

    logger.info(f"[SHOPIFY_OAUTH] Normalized shop domain: {shop} -> {shop_domain}")

    safe_redirect = "/settings"
    if redirect_path and redirect_path.startswith("/") and not redirect_path.startswith("//"):
        safe_redirect = redirect_path

    state_data = {
        "workspace_id": str(current_user.workspace_id),
        "shop_domain": shop_domain,
        "redirect_path": safe_redirect,
    }
    state = json.dumps(state_data)

    params = {
        "client_id": SHOPIFY_API_KEY,
        "scope": ",".join(SHOPIFY_SCOPES),
        "redirect_uri": SHOPIFY_REDIRECT_URI,
        "state": state,
        "grant_options[]": "per-user",
    }

    return f"https://{shop_domain}/admin/oauth/authorize?{urlencode(params)}"


# =============================================================================
# OAUTH ENDPOINTS
# =============================================================================

def get_shopify_session_claims(request: Request) -> tuple[dict, str]:
    """Return verified Shopify session claims and the normalized shop domain."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Shopify session token",
        )

    claims = verify_shopify_session_token(auth_header[7:])
    shop_domain = urlparse(claims.get("dest", "")).hostname
    if not shop_domain:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Shopify session token",
        )

    return claims, shop_domain


@router.get("/session")
async def verify_embedded_session(request: Request):
    """Verify an embedded-app Shopify session token.

    WHAT: Validates the session token generated by Shopify App Bridge
    WHY: Embedded apps must authenticate backend requests with session tokens
    """
    claims, shop_domain = get_shopify_session_claims(request)

    return {
        "authenticated": True,
        "shop": shop_domain,
        "user_id": claims.get("sub"),
        "session_id": claims.get("sid"),
        "expires_at": claims.get("exp"),
    }


@router.get("/embedded-status")
async def get_embedded_shop_status(
    request: Request,
    db: Session = Depends(get_db),
):
    """Return Shopify-session-authenticated link status for the embedded app."""
    claims, shop_domain = get_shopify_session_claims(request)

    linked_shop = (
        db.query(ShopifyShop, Connection, Workspace)
        .join(Connection, ShopifyShop.connection_id == Connection.id)
        .join(Workspace, ShopifyShop.workspace_id == Workspace.id)
        .filter(
            ShopifyShop.shop_domain == shop_domain,
            Connection.provider == ProviderEnum.shopify,
        )
        .order_by(Connection.connected_at.desc())
        .first()
    )

    response = {
        "authenticated": True,
        "shop": shop_domain,
        "user_id": claims.get("sub"),
        "session_id": claims.get("sid"),
        "expires_at": claims.get("exp"),
        "linked": bool(linked_shop),
    }

    if linked_shop:
        shop, connection, workspace = linked_shop
        response.update(
            {
                "connection_id": str(connection.id),
                "connection_name": connection.name,
                "workspace_id": str(workspace.id),
                "workspace_name": workspace.name,
                "shop_name": shop.shop_name,
            }
        )

    return response


@router.get("/authorize")
async def shopify_authorize(
    shop: str = Query(..., description="Shopify store domain (e.g., 'mystore' or 'mystore.myshopify.com')"),
    redirect_path: Optional[str] = Query(None, description="Frontend path to redirect after OAuth (e.g., '/shopify')"),
    current_user: User = Depends(get_current_user),
):
    """Redirect user to Shopify OAuth consent screen.

    WHAT:
        Builds authorization URL with required parameters and redirects user.
    WHY:
        Initiates OAuth flow for connecting Shopify stores.
    REFERENCES:
        https://shopify.dev/docs/apps/auth/oauth/getting-started
    """
    auth_url = build_shopify_authorize_url(
        shop=shop,
        redirect_path=redirect_path,
        current_user=current_user,
    )

    logger.info(f"[SHOPIFY_OAUTH] Redirecting user {current_user.id} to Shopify consent")
    logger.debug(f"[SHOPIFY_OAUTH] Auth URL: {auth_url}")

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def shopify_callback(
    code: Optional[str] = Query(None),
    shop: Optional[str] = Query(None),  # Shopify returns shop in callback
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Handle OAuth callback from Shopify.

    WHAT:
        Exchanges authorization code for access token.
        Fetches shop info and stores in Redis for confirmation.
    WHY:
        Completes OAuth flow - shows shop confirmation before creating connection.
    REFERENCES:
        https://shopify.dev/docs/apps/auth/oauth/getting-started#step-5-get-an-access-token
    """
    # Validate configuration at runtime
    _validate_shopify_config()
    redirect_path = extract_redirect_path_from_state(state)

    # Handle errors from Shopify
    if error:
        logger.error(f"[SHOPIFY_OAUTH] OAuth error: {error} - {error_description}")
        return RedirectResponse(url=build_shopify_frontend_redirect(
            redirect_path,
            status_value="error",
            message=error,
        ))

    if not code:
        logger.error("[SHOPIFY_OAUTH] Missing authorization code")
        return RedirectResponse(url=build_shopify_frontend_redirect(
            redirect_path,
            status_value="error",
            message="missing_code",
        ))

    if not shop:
        logger.error("[SHOPIFY_OAUTH] Missing shop parameter")
        return RedirectResponse(url=build_shopify_frontend_redirect(
            redirect_path,
            status_value="error",
            message="missing_shop",
        ))

    if not state:
        logger.error("[SHOPIFY_OAUTH] Missing state parameter")
        return RedirectResponse(url=build_shopify_frontend_redirect(
            redirect_path,
            status_value="error",
            message="missing_state",
        ))

    # Parse and validate state
    try:
        state_data = json.loads(state)
        workspace_id = state_data.get("workspace_id")
        expected_shop = state_data.get("shop_domain")
        redirect_path = state_data.get("redirect_path", "/settings")
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"[SHOPIFY_OAUTH] Invalid state parameter: {e}")
        return RedirectResponse(url=build_shopify_frontend_redirect(
            redirect_path,
            status_value="error",
            message="invalid_state",
        ))

    # Normalize shop from callback
    shop_domain = normalize_shop_domain(shop)

    # Verify shop matches what we expected (CSRF protection)
    if shop_domain != expected_shop:
        logger.error(f"[SHOPIFY_OAUTH] Shop mismatch: expected {expected_shop}, got {shop_domain}")
        return RedirectResponse(url=build_shopify_frontend_redirect(
            redirect_path,
            status_value="error",
            message="shop_mismatch",
        ))

    # Verify workspace exists
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        logger.error(f"[SHOPIFY_OAUTH] Invalid workspace ID: {workspace_id}")
        return RedirectResponse(url=build_shopify_frontend_redirect(
            redirect_path,
            status_value="error",
            message="invalid_workspace",
        ))

    # Exchange code for access token
    # WHAT: POST request to Shopify token endpoint
    # WHY: Shopify uses POST (unlike Meta which uses GET)
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                f"https://{shop_domain}/admin/oauth/access_token",
                json={
                    "client_id": SHOPIFY_API_KEY,
                    "client_secret": SHOPIFY_API_SECRET,
                    "code": code,
                }
            )
            token_response.raise_for_status()
            token_data = token_response.json()
    except httpx.HTTPStatusError as e:
        logger.exception(f"[SHOPIFY_OAUTH] Token exchange failed: {e.response.text}")
        return RedirectResponse(url=build_shopify_frontend_redirect(
            redirect_path,
            status_value="error",
            message="token_exchange_failed",
        ))
    except Exception as e:
        logger.exception(f"[SHOPIFY_OAUTH] Token exchange failed: {e}")
        return RedirectResponse(url=build_shopify_frontend_redirect(
            redirect_path,
            status_value="error",
            message="token_exchange_failed",
        ))

    access_token = token_data.get("access_token")
    scope = token_data.get("scope", "")  # Granted scopes

    if not access_token:
        logger.error("[SHOPIFY_OAUTH] Missing access token in response")
        return RedirectResponse(url=build_shopify_frontend_redirect(
            redirect_path,
            status_value="error",
            message="missing_token",
        ))

    logger.info(f"[SHOPIFY_OAUTH] Token exchange successful for {shop_domain}")
    logger.info(f"[SHOPIFY_OAUTH] Granted scopes: {scope}")

    # Fetch shop info using the access token
    # WHAT: Get shop details for display and storage
    # WHY: Need shop name, currency, timezone for connection
    try:
        async with httpx.AsyncClient() as client:
            shop_response = await client.get(
                f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/shop.json",
                headers={
                    "X-Shopify-Access-Token": access_token,
                    "Content-Type": "application/json",
                }
            )
            shop_response.raise_for_status()
            shop_data = shop_response.json().get("shop", {})
    except Exception as e:
        logger.exception(f"[SHOPIFY_OAUTH] Failed to fetch shop info: {e}")
        return RedirectResponse(url=build_shopify_frontend_redirect(
            redirect_path,
            status_value="error",
            message="shop_fetch_failed",
        ))

    shop_info = {
        "id": str(shop_data.get("id")),
        "name": shop_data.get("name", shop_domain),
        "domain": shop_domain,
        "primary_domain": shop_data.get("domain", shop_domain),
        "currency": shop_data.get("currency", "USD"),
        "timezone": shop_data.get("iana_timezone", "UTC"),
        "country_code": shop_data.get("country_code"),
        "plan_name": shop_data.get("plan_name"),
        "email": shop_data.get("email"),
    }

    logger.info(f"[SHOPIFY_OAUTH] Fetched shop info: {shop_info['name']} ({shop_info['currency']})")

    # Store data in Redis for confirmation step
    # WHAT: Temporary storage during OAuth flow
    # WHY: User needs to confirm before we create connection
    from app import state as app_state

    if not app_state.context_manager:
        logger.error("[SHOPIFY_OAUTH] Redis not available")
        return RedirectResponse(url=build_shopify_frontend_redirect(
            redirect_path,
            status_value="error",
            message="redis_unavailable",
        ))

    session_id = str(uuid.uuid4())

    selection_data = {
        "shop": shop_info,
        "workspace_id": workspace_id,
        "access_token": access_token,
        "scope": scope,
    }

    # Store with 10 minute TTL
    app_state.context_manager.redis_client.setex(
        f"shopify_oauth_selection:{session_id}",
        600,  # TTL in seconds
        json.dumps(selection_data)
    )

    logger.info(f"[SHOPIFY_OAUTH] Stored OAuth session: {session_id}")

    # Redirect to frontend for confirmation
    return RedirectResponse(url=build_shopify_frontend_redirect(
        redirect_path,
        status_value="confirm",
        session_id=session_id,
    ))


@router.get("/shop")
async def get_oauth_shop(
    session_id: str = Query(..., description="OAuth session ID from callback"),
    current_user: User = Depends(get_current_user),
):
    """Get shop info available for connection from OAuth flow.

    WHAT: Retrieve shop data from Redis session
    WHY: Frontend needs shop info to display confirmation modal
    """
    from app import state as app_state

    if not app_state.context_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is required for OAuth flow but is currently unavailable."
        )

    # Retrieve selection data from Redis
    selection_data_json = app_state.context_manager.redis_client.get(
        f"shopify_oauth_selection:{session_id}"
    )

    if not selection_data_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session expired or invalid. Please restart OAuth flow."
        )

    selection_data = json.loads(selection_data_json)

    # Verify workspace matches current user
    if selection_data["workspace_id"] != str(current_user.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session does not belong to your workspace"
        )

    return {
        "shop": selection_data["shop"],
        "session_id": session_id,
    }


class ConnectShopRequest(BaseModel):
    """Request body for connecting a Shopify shop."""
    session_id: str


@router.post("/connect")
async def connect_shop(
    request: ConnectShopRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create connection for the Shopify shop.

    WHAT: Creates Connection and ShopifyShop records
    WHY: Completes OAuth flow by persisting the connection
    """
    from app import state as app_state

    if not app_state.context_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is required for OAuth flow but is currently unavailable."
        )

    # Retrieve selection data from Redis
    selection_data_json = app_state.context_manager.redis_client.get(
        f"shopify_oauth_selection:{request.session_id}"
    )

    if not selection_data_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session expired or invalid. Please restart OAuth flow."
        )

    selection_data = json.loads(selection_data_json)

    # Verify workspace matches current user
    workspace_id = selection_data["workspace_id"]
    if workspace_id != str(current_user.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session does not belong to your workspace"
        )

    shop_info = selection_data["shop"]
    access_token = selection_data["access_token"]
    scope = selection_data["scope"]

    # Debug: Log granted scopes to verify pixel scopes were included
    logger.info(f"[SHOPIFY_OAUTH] Granted scopes: {scope}")

    shop_domain = shop_info["domain"]
    shop_id = shop_info["id"]

    try:
        existing_shop_link = db.query(ShopifyShop).filter(
            ShopifyShop.shop_domain == shop_domain
        ).first()
        if existing_shop_link and str(existing_shop_link.workspace_id) != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This Shopify store is already linked to another workspace.",
            )

        # Check if connection already exists for this shop
        existing_connection = db.query(Connection).filter(
            Connection.workspace_id == workspace_id,
            Connection.provider == ProviderEnum.shopify,
            Connection.external_account_id == shop_domain,
        ).first()

        if existing_connection:
            # Update existing connection
            existing_connection.name = shop_info["name"]
            existing_connection.status = "active"
            existing_connection.timezone = shop_info["timezone"]
            existing_connection.currency_code = shop_info["currency"]
            connection = existing_connection
            is_new = False
            logger.info(f"[SHOPIFY_OAUTH] Updating existing connection for {shop_domain}")
        else:
            # Create new connection
            connection = Connection(
                provider=ProviderEnum.shopify,
                external_account_id=shop_domain,
                name=shop_info["name"],
                status="active",
                timezone=shop_info["timezone"],
                currency_code=shop_info["currency"],
                workspace_id=workspace_id,
                connected_at=datetime.utcnow(),
            )
            db.add(connection)
            db.flush()  # Get connection.id
            is_new = True
            logger.info(f"[SHOPIFY_OAUTH] Created new connection for {shop_domain}")

        # Store encrypted token
        # WHAT: Persist access token with encryption
        # WHY: Shopify tokens don't expire but should still be encrypted
        store_connection_token(
            db,
            connection,
            access_token=access_token,
            refresh_token=None,  # Shopify offline tokens don't need refresh
            expires_at=None,  # Shopify offline tokens don't expire
            scope=scope,
            ad_account_ids=[shop_domain],  # Store shop domain for reference
        )

        # Create or update ShopifyShop record
        existing_shop = db.query(ShopifyShop).filter(
            ShopifyShop.connection_id == connection.id
        ).first()

        if existing_shop:
            # Update existing shop
            existing_shop.shop_name = shop_info["name"]
            existing_shop.currency = shop_info["currency"]
            existing_shop.timezone = shop_info["timezone"]
            existing_shop.country_code = shop_info.get("country_code")
            existing_shop.plan_name = shop_info.get("plan_name")
            existing_shop.email = shop_info.get("email")
            existing_shop.updated_at = datetime.utcnow()
            shopify_shop = existing_shop
            logger.info(f"[SHOPIFY_OAUTH] Updated ShopifyShop record for {shop_domain}")
        else:
            # Create new ShopifyShop
            shopify_shop = ShopifyShop(
                workspace_id=workspace_id,
                connection_id=connection.id,
                external_shop_id=f"gid://shopify/Shop/{shop_id}",
                shop_domain=shop_domain,
                shop_name=shop_info["name"],
                currency=shop_info["currency"],
                timezone=shop_info["timezone"],
                country_code=shop_info.get("country_code"),
                plan_name=shop_info.get("plan_name"),
                email=shop_info.get("email"),
            )
            db.add(shopify_shop)
            logger.info(f"[SHOPIFY_OAUTH] Created ShopifyShop record for {shop_domain}")

        db.commit()

        # =====================================================================
        # PIXEL ACTIVATION (Attribution Engine)
        # =====================================================================
        # WHAT: Activate the web pixel for this shop after successful OAuth
        # WHY: Pixel must be activated via GraphQL before it can capture events
        # REFERENCES: docs/living-docs/ATTRIBUTION_ENGINE.md
        pixel_id = None
        pixel_error = None

        # Check if write_pixels scope was granted before attempting activation
        # WHY: Stores connected before this scope was added won't have permission
        granted_scopes = scope.split(",") if scope else []
        if "write_pixels" not in granted_scopes:
            pixel_error = (
                "write_pixels scope not granted — store must re-authorize. "
                f"Granted scopes: {scope}"
            )
            logger.warning(
                f"[SHOPIFY_OAUTH] {pixel_error} for {shop_domain}"
            )
        else:
            try:
                pixel_id, pixel_error = await activate_pixel_for_connection(
                    connection=connection,
                    access_token=access_token,
                    workspace_id=workspace_id,
                )
                if pixel_id:
                    # Store pixel ID on connection
                    connection.web_pixel_id = pixel_id
                    db.commit()
                    logger.info(
                        f"[SHOPIFY_OAUTH] Activated pixel for {shop_domain}",
                        extra={"pixel_id": pixel_id}
                    )
                else:
                    logger.warning(
                        f"[SHOPIFY_OAUTH] Pixel activation failed for {shop_domain}: {pixel_error}"
                    )
            except Exception as e:
                # Don't fail the connection if pixel activation fails
                # The pixel can be activated later
                pixel_error = f"Unexpected error: {str(e)}"
                logger.warning(
                    f"[SHOPIFY_OAUTH] Pixel activation error for {shop_domain}: {e}"
                )

        # =====================================================================
        # WEBHOOK SUBSCRIPTION (Attribution Engine)
        # =====================================================================
        # WHAT: Subscribe to orders/paid webhook for attribution triggers
        # WHY: Attribution runs when orders are paid, not on checkout_completed
        # REFERENCES: docs/living-docs/ATTRIBUTION_ENGINE.md
        webhook_results = None
        webhook_error = None
        try:
            from app.services.webhook_subscription_service import subscribe_to_webhooks
            webhook_results = await subscribe_to_webhooks(
                shop_domain=shop_domain,
                access_token=access_token,
            )
            logger.info(
                f"[SHOPIFY_OAUTH] Webhook subscription results for {shop_domain}",
                extra={"results": webhook_results}
            )
        except Exception as e:
            # Don't fail the connection if webhook subscription fails
            webhook_error = str(e)
            logger.warning(
                f"[SHOPIFY_OAUTH] Webhook subscription error for {shop_domain}: {e}"
            )

        # Clean up Redis session
        app_state.context_manager.redis_client.delete(
            f"shopify_oauth_selection:{request.session_id}"
        )

        action = "created" if is_new else "updated"
        logger.info(
            f"[SHOPIFY_OAUTH] Successfully {action} Shopify connection for {shop_domain} "
            f"in workspace {workspace_id}"
        )

        # Track connection event for new connections (flows to Google Analytics)
        if is_new:
            track_connected_shopify(
                user_id=str(current_user.id),
                workspace_id=workspace_id,
                shop_domain=shop_domain,
            )

        return {
            "success": True,
            "connection_id": str(connection.id),
            "shop_id": str(shopify_shop.id),
            "shop_name": shop_info["name"],
            "shop_domain": shop_domain,
            "is_new": is_new,
            "pixel_id": pixel_id,
            "pixel_error": pixel_error,
            "webhook_results": webhook_results,
            "webhook_error": webhook_error,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"[SHOPIFY_OAUTH] Failed to create connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connection: {str(e)}"
        )
