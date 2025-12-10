"""Google Ads OAuth 2.0 flow endpoints.

WHAT:
    Implements OAuth authorization flow for user-initiated Google Ads connections.
    
WHY:
    Allows users to connect their own Google Ads accounts without manual token setup.
    
REFERENCES:
    - docs/living-docs/GOOGLE_INTEGRATION_STATUS.MD (Phase 7)
    - https://developers.google.com/google-ads/api/docs/oauth/overview
"""

import os
import logging
from typing import Optional
from urllib.parse import urlencode
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import httpx
import json

from app.database import get_db
from app.deps import get_current_user
from app.models import User, Connection, ProviderEnum
from app.services.token_service import store_connection_token
from app.telemetry import track_connected_google_ads

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])

# OAuth configuration from environment
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/adwords"]


@router.get("/authorize")
async def google_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Redirect user to Google OAuth consent screen.
    
    WHAT:
        Builds authorization URL with required parameters and redirects user.
    WHY:
        Initiates OAuth flow for connecting Google Ads account.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured. Missing CLIENT_ID or CLIENT_SECRET."
        )
    
    # Build authorization URL
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Force consent screen to ensure refresh token
        "state": str(current_user.workspace_id),  # Pass workspace ID for callback
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    logger.info(f"[GOOGLE_OAUTH] Redirecting user {current_user.id} to Google consent screen")
    
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def google_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    state: Optional[str] = Query(None),  # workspace_id
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Google.
    
    WHAT:
        Exchanges authorization code for access/refresh tokens.
        Fetches customer IDs and creates connection.
    WHY:
        Completes OAuth flow and stores encrypted tokens.
    """
    # Validate configuration
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error("[GOOGLE_OAUTH] OAuth not configured - missing credentials")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?google_oauth=error&message=oauth_not_configured"
        )
    
    # Handle errors from Google
    if error:
        logger.error(f"[GOOGLE_OAUTH] OAuth error: {error}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?google_oauth=error&message={error}"
        )
    
    if not code:
        logger.error("[GOOGLE_OAUTH] Missing authorization code")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?google_oauth=error&message=missing_code"
        )
    
    # Validate state parameter (workspace_id)
    if not state:
        logger.error("[GOOGLE_OAUTH] Missing state parameter")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?google_oauth=error&message=missing_state"
        )
    
    # Verify workspace exists
    from app.models import Workspace
    workspace = db.query(Workspace).filter(Workspace.id == state).first()
    if not workspace:
        logger.error(f"[GOOGLE_OAUTH] Invalid workspace ID: {state}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?google_oauth=error&message=invalid_workspace"
        )
    
    # Exchange code for tokens
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                }
            )
            token_response.raise_for_status()
            token_data = token_response.json()
    except Exception as e:
        logger.exception("[GOOGLE_OAUTH] Failed to exchange code for tokens")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?google_oauth=error&message=token_exchange_failed"
        )
    
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")  # seconds
    
    if not access_token or not refresh_token:
        logger.error("[GOOGLE_OAUTH] Missing tokens in response")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?google_oauth=error&message=missing_tokens"
        )
    
    # Fetch accessible customer IDs using the new access token
    try:
        # Validate developer token is configured
        developer_token = os.getenv("GOOGLE_DEVELOPER_TOKEN")
        if not developer_token:
            logger.error("[GOOGLE_OAUTH] GOOGLE_DEVELOPER_TOKEN not configured")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/settings?google_oauth=error&message=developer_token_missing"
            )
        
        # Build temporary client with OAuth tokens
        from google.ads.googleads.client import GoogleAdsClient as _SdkClient
        
        oauth_config = {
            "developer_token": developer_token,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "use_proto_plus": True,
        }
        
        temp_client = _SdkClient.load_from_dict(oauth_config)
        customer_service = temp_client.get_service("CustomerService")
        
        # List accessible customers
        accessible_customers = customer_service.list_accessible_customers()
        customer_ids = accessible_customers.resource_names
        
        if not customer_ids:
            logger.error("[GOOGLE_OAUTH] No accessible customers found")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/settings?google_oauth=error&message=no_customers"
            )
        
        logger.info(f"[GOOGLE_OAUTH] Found {len(customer_ids)} accessible customer(s)")
        
        # Fetch details for all accessible customers and detect MCC accounts
        ga_service = temp_client.get_service("GoogleAdsService")
        all_customers_data = []
        
        # First pass: Get basic info for all accessible customers
        customer_info_map = {}
        for customer_resource_name in customer_ids:
            customer_id = customer_resource_name.split("/")[-1]
            
            try:
                # Fetch customer details including manager status
                query = f"""
                    SELECT
                        customer.id,
                        customer.descriptive_name,
                        customer.currency_code,
                        customer.time_zone,
                        customer.manager
                    FROM customer
                    WHERE customer.id = {customer_id}
                """
                
                response = ga_service.search(customer_id=customer_id, query=query)
                
                for row in response:
                    is_manager = getattr(row.customer, 'manager', False)
                    customer_info_map[customer_id] = {
                        "id": str(row.customer.id),
                        "name": row.customer.descriptive_name or f"Google Ads {row.customer.id}",
                        "currency": row.customer.currency_code,
                        "timezone": row.customer.time_zone,
                        "is_manager": bool(is_manager),
                        "parent_id": None,
                        "child_accounts": []
                    }
                    logger.info(f"[GOOGLE_OAUTH] Fetched customer: {customer_info_map[customer_id]['name']} ({customer_id}) - {'MCC' if is_manager else 'Ad Account'}")
                    break
            except Exception as e:
                logger.warning(f"[GOOGLE_OAUTH] Failed to fetch details for customer {customer_id}: {e}")
                continue
        
        # Second pass: For MCC accounts, fetch their child accounts using customer_client_link
        for customer_id, customer_data in customer_info_map.items():
            if not customer_data["is_manager"]:
                continue
                
            try:
                logger.info(f"[GOOGLE_OAUTH] Fetching child accounts for MCC {customer_data['name']} ({customer_id})")
            
                # Use customer_client_link to get direct children
                link_query = f"""
                    SELECT
                        customer_client_link.client_customer,
                        customer_client_link.manager_link_id,
                        customer_client_link.status
                    FROM customer_client_link
                    WHERE customer_client_link.status = 'ACTIVE'
                """
                
                link_response = ga_service.search(customer_id=customer_id, query=link_query)
                
                child_ids_found = []
                for link_row in link_response:
                    child_resource = link_row.customer_client_link.client_customer
                    child_id = child_resource.split("/")[-1]
                    
                    # Skip self
                    if child_id == customer_id:
                        continue
                    
                    child_ids_found.append(child_id)
                    logger.info(f"[GOOGLE_OAUTH] Found linked child {child_id} under MCC {customer_id}")
                
                # Now fetch details for each child
                # IMPORTANT: When accessing client customers through a manager account,
                # we MUST set login-customer-id header to the manager's customer ID
                for child_id in child_ids_found:
                    try:
                        # Create a client with login_customer_id set to the parent MCC
                        # This is required by Google Ads API when accessing client accounts
                        child_client_config = {
                            "developer_token": developer_token,
                            "client_id": GOOGLE_CLIENT_ID,
                            "client_secret": GOOGLE_CLIENT_SECRET,
                            "refresh_token": refresh_token,
                            "login_customer_id": customer_id,  # Set MCC as login customer
                            "use_proto_plus": True,
                        }
                        child_client = _SdkClient.load_from_dict(child_client_config)
                        child_ga_service = child_client.get_service("GoogleAdsService")
                        
                        # Fetch child details directly using the child client
                        child_query = f"""
                            SELECT
                                customer.id,
                                customer.descriptive_name,
                                customer.currency_code,
                                customer.time_zone,
                                customer.manager
                            FROM customer
                            WHERE customer.id = {child_id}
                        """
                        
                        child_response = child_ga_service.search(customer_id=child_id, query=child_query)
                        
                        for child_row in child_response:
                            child_is_manager = getattr(child_row.customer, 'manager', False)
                            
                            child_info = {
                                "id": str(child_row.customer.id),
                                "name": child_row.customer.descriptive_name or f"Google Ads {child_id}",
                                "currency": child_row.customer.currency_code,
                                "timezone": child_row.customer.time_zone,
                                "is_manager": bool(child_is_manager),
                                "parent_id": customer_id,
                            }
                            
                            customer_data["child_accounts"].append(child_info)
                            logger.info(f"[GOOGLE_OAUTH] Added child {child_info['name']} ({child_id}) under MCC {customer_data['name']}")
                            break
                            
                    except Exception as child_e:
                        logger.warning(f"[GOOGLE_OAUTH] Failed to fetch details for child {child_id}: {child_e}")
                        continue
                
                logger.info(f"[GOOGLE_OAUTH] MCC {customer_data['name']} ({customer_id}): Found {len(customer_data['child_accounts'])} child account(s)")
            
            except Exception as e:
                logger.error(f"[GOOGLE_OAUTH] Failed to fetch children for MCC {customer_id}: {e}")
                logger.exception(e)
        
        all_customers_data = list(customer_info_map.values())
        
        if not all_customers_data:
            raise Exception("Could not fetch any customer details")
        
    except ImportError as e:
        logger.exception("[GOOGLE_OAUTH] Google Ads SDK not installed")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?google_oauth=error&message=sdk_not_installed"
        )
    except Exception as e:
        logger.exception(f"[GOOGLE_OAUTH] Failed to fetch customer details: {str(e)}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?google_oauth=error&message=customer_fetch_failed"
        )
    
    # Store accounts temporarily and redirect to selection page
    
    # Prepare account data for frontend (flatten hierarchy)
    # Include ALL MCCs (even without children) and their child accounts
    accounts_for_selection = []
    mcc_info = []  # Store MCC info separately for frontend
    
    for customer_data in all_customers_data:
        # If this is a manager account, add its child accounts (not the MCC itself)
        if customer_data.get("is_manager"):
            child_count = len(customer_data.get("child_accounts", []))
            logger.info(f"[GOOGLE_OAUTH] Processing MCC {customer_data['name']} ({customer_data['id']}) with {child_count} children")
            
            # Store MCC info for frontend (even if no children)
            mcc_info.append({
                "id": customer_data["id"],
                "name": customer_data["name"],
                "child_count": child_count,
            })
            
            # Add child accounts if any
            if customer_data.get("child_accounts"):
                for child in customer_data["child_accounts"]:
                    # Skip the MCC itself if it lists itself as a child
                    if child["id"] == customer_data["id"]:
                        continue
                        
                    accounts_for_selection.append({
                        "id": child["id"],
                        "name": child["name"],
                        "currency": child["currency"],
                        "timezone": child["timezone"],
                        "is_manager": child.get("is_manager", False),
                        "parent_id": customer_data["id"],  # Parent MCC ID
                        "parent_name": customer_data["name"],  # Parent MCC name
                    })
                    logger.info(f"[GOOGLE_OAUTH] Added child account: {child['name']} ({child['id']}) under {customer_data['name']}")
            else:
                logger.info(f"[GOOGLE_OAUTH] MCC {customer_data['name']} has no enabled child accounts")
        # If this is NOT a manager account, add it directly
        elif not customer_data.get("is_manager"):
            accounts_for_selection.append({
                "id": customer_data["id"],
                "name": customer_data["name"],
                "currency": customer_data["currency"],
                "timezone": customer_data["timezone"],
                "is_manager": False,
                "parent_id": None,
                "parent_name": None,
            })
            logger.info(f"[GOOGLE_OAUTH] Added standalone account: {customer_data['name']} ({customer_data['id']})")
    
    # Log what accounts we found
    logger.info(f"[GOOGLE_OAUTH] Found {len(accounts_for_selection)} ad account(s) for selection:")
    for acc in accounts_for_selection:
        logger.info(f"  - {acc['name']} ({acc['id']}) - Parent: {acc.get('parent_name', 'None')}")
    
    # If no accounts found, show error
    if len(accounts_for_selection) == 0:
        logger.warning("[GOOGLE_OAUTH] No ad accounts available (only MCCs with no children)")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?google_oauth=error&message=no_ad_accounts"
        )
    
    # Always show selection modal (even for single account) to allow user to review before connecting
    # Removed auto-connect logic - always show modal for user control
    
    # Store tokens temporarily and redirect to selection page
    # Store selection data temporarily using Redis
    import uuid
    from app import state as app_state
    
    if not app_state.context_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is required for OAuth flow but is currently unavailable. Please configure REDIS_URL."
        )
    
    session_id = str(uuid.uuid4())
    workspace_id = state  # workspace_id from OAuth state parameter
    
    # Store in Redis with 10 minute TTL (600 seconds)
    # Include MCC info so frontend can display all MCCs even if they have no children
    selection_data_json = json.dumps({
        "accounts": accounts_for_selection,
        "mccs": mcc_info,  # Include all MCCs for display
        "workspace_id": workspace_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
    })
    
    app_state.context_manager.redis_client.setex(
        f"google_oauth_selection:{session_id}",
        600,  # TTL in seconds
        selection_data_json
    )
    
    logger.info(f"[GOOGLE_OAUTH] Stored selection data with session_id: {session_id}")
    
    return RedirectResponse(
        url=f"{FRONTEND_URL}/settings?google_oauth=select&session_id={session_id}"
    )


@router.get("/accounts")
async def get_oauth_accounts(
    session_id: str = Query(..., description="OAuth session ID from callback"),
    current_user: User = Depends(get_current_user),
):
    """Get accounts available for selection from OAuth flow."""
    from app import state as app_state
    
    if not app_state.context_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is required for OAuth flow but is currently unavailable. Please configure REDIS_URL."
        )
    
    # Retrieve selection data from Redis
    selection_data_json = app_state.context_manager.redis_client.get(f"google_oauth_selection:{session_id}")
    
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
        "accounts": selection_data.get("accounts", []),
        "mccs": selection_data.get("mccs", []),  # Return MCC info for frontend
        "session_id": session_id,
    }


class ConnectSelectedRequest(BaseModel):
    account_ids: List[str]
    session_id: str


@router.post("/connect-selected")
async def connect_selected_accounts(
    request: ConnectSelectedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create connections for selected Google Ads accounts."""
    from app import state as app_state
    
    if not app_state.context_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is required for OAuth flow but is currently unavailable. Please configure REDIS_URL."
        )
    
    # Retrieve selection data from Redis
    selection_data_json = app_state.context_manager.redis_client.get(f"google_oauth_selection:{request.session_id}")
    
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
    
    # Filter accounts to only selected ones
    selected_accounts = [
        acc for acc in selection_data["accounts"]
        if acc["id"] in request.account_ids
    ]
    
    if not selected_accounts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid accounts selected"
        )
    
    workspace_id = selection_data["workspace_id"]
    access_token = selection_data["access_token"]
    refresh_token = selection_data["refresh_token"]
    expires_in = selection_data["expires_in"]
    
    created_connections = []
    updated_connections = []
    
    try:
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None
        
        for account_data in selected_accounts:
            connection = db.query(Connection).filter(
                Connection.workspace_id == workspace_id,
                Connection.provider == ProviderEnum.google,
                Connection.external_account_id == account_data["id"],
            ).first()
            
            if not connection:
                connection = Connection(
                    provider=ProviderEnum.google,
                    external_account_id=account_data["id"],
                    name=account_data["name"],
                    status="active",
                    timezone=account_data["timezone"],
                    currency_code=account_data["currency"],
                    workspace_id=workspace_id,
                    connected_at=datetime.utcnow(),
                )
                db.add(connection)
                db.flush()
                created_connections.append(connection)
                logger.info(f"[GOOGLE_OAUTH] Created new connection for customer {account_data['id']}")
            else:
                connection.name = account_data["name"]
                connection.timezone = account_data["timezone"]
                connection.currency_code = account_data["currency"]
                connection.status = "active"
                updated_connections.append(connection)
                logger.info(f"[GOOGLE_OAUTH] Updating existing connection for customer {account_data['id']}")
            
            # Store encrypted tokens for each connection
            # Include parent_mcc_id if this is a client account
            parent_mcc_id = account_data.get("parent_id")
            store_connection_token(
                db,
                connection,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                scope=" ".join(GOOGLE_SCOPES),
                ad_account_ids=[account_data["id"]],
                parent_mcc_id=parent_mcc_id,  # Store parent MCC ID for sync operations
            )
        
        db.commit()
        
        # Clean up session data (if Redis is available)
        if app_state.context_manager:
            app_state.context_manager.redis_client.delete(f"google_oauth_selection:{request.session_id}")
        
        total_connections = len(created_connections) + len(updated_connections)
        logger.info(
            f"[GOOGLE_OAUTH] Successfully connected {total_connections} Google Ads account(s) "
            f"({len(created_connections)} new, {len(updated_connections)} updated) to workspace {workspace_id}"
        )

        # Track connection events for each new account (flows to Google Analytics)
        for conn in created_connections:
            track_connected_google_ads(
                user_id=str(current_user.id),
                workspace_id=workspace_id,
                account_id=conn.external_account_id,
                account_name=conn.name,
            )

        # Trigger initial sync with 90-day backfill for all new/updated connections (non-blocking)
        # If Redis available: enqueues to background worker with backfill=True
        # If Redis unavailable: skips (connection will be picked up on next 15-min train)
        try:
            from app.workers.arq_enqueue import enqueue_sync_job
            for conn in created_connections + updated_connections:
                # Use backfill=True to fetch 90 days of historical data
                await enqueue_sync_job(str(conn.id), workspace_id, force_refresh=False, backfill=True)
                logger.info(f"[GOOGLE_OAUTH] Enqueued 90-day backfill sync for connection {conn.id}")
        except Exception as e:
            # Don't fail the connection if sync enqueue fails
            logger.warning(f"[GOOGLE_OAUTH] Could not enqueue initial sync: {e}")

        return {
            "success": True,
            "connections_created": len(created_connections),
            "connections_updated": len(updated_connections),
            "total": total_connections,
            "connection_ids": [str(c.id) for c in created_connections + updated_connections],
        }
        
    except Exception as e:
        db.rollback()
        logger.exception(f"[GOOGLE_OAUTH] Failed to create/update connections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connections: {str(e)}"
    )

