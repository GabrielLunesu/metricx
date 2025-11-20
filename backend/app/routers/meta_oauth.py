"""Meta Ads OAuth 2.0 flow endpoints.

WHAT:
    Implements OAuth authorization flow for user-initiated Meta Ads connections.
    
WHY:
    Allows users to connect their own Meta ad accounts without manual token setup.
    
REFERENCES:
    - docs/META_OAUTH_IMPLEMENTATION.md
    - backend/app/routers/google_oauth.py (similar pattern)
    - https://developers.facebook.com/docs/marketing-api/get-started/authentication
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
from app.utils.env import require_env  # utility to fetch env vars with mandatory check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/meta", tags=["Meta OAuth"])

# OAuth configuration from environment
META_APP_ID = require_env("META_APP_ID")
META_APP_SECRET = require_env("META_APP_SECRET")
META_REDIRECT_URI = require_env("META_OAUTH_REDIRECT_URI")
FRONTEND_URL = require_env("FRONTEND_URL")

# Optional configuration for flexibility
# Default scopes if not specified in env
DEFAULT_SCOPES = ["ads_management", "ads_read", "business_management", "read_insights", "email"]
env_scopes = os.getenv("META_OAUTH_SCOPES")
META_SCOPES = env_scopes.split(",") if env_scopes else DEFAULT_SCOPES

META_CONFIG_ID = os.getenv("META_OAUTH_CONFIG_ID")

META_AUTH_URL = "https://www.facebook.com/v24.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v24.0/oauth/access_token"
META_EXCHANGE_TOKEN_URL = "https://graph.facebook.com/v24.0/oauth/access_token"


@router.get("/authorize")
async def meta_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Redirect user to Meta OAuth consent screen.
    
    WHAT:
        Builds authorization URL with required parameters and redirects user.
    WHY:
        Initiates OAuth flow for connecting Meta ad accounts.
    """
    if not META_APP_ID or not META_APP_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Meta OAuth not configured. Missing APP_ID or APP_SECRET."
        )
    
    # Build authorization URL
    params = {
        "client_id": META_APP_ID,
        "redirect_uri": META_REDIRECT_URI,
        "response_type": "code",
        "state": str(current_user.workspace_id),  # Pass workspace ID for callback
    }

    # Use config_id if available (Facebook Login for Business), otherwise use scopes
    if META_CONFIG_ID:
        params["config_id"] = META_CONFIG_ID
        params["override_default_response_type"] = "true"
        logger.info(f"[META_OAUTH] Using config_id: {META_CONFIG_ID}")
    else:
        params["scope"] = ",".join(META_SCOPES)  # Meta uses comma-separated scopes
        logger.info(f"[META_OAUTH] Using scopes: {params['scope']}")
    
    
    auth_url = f"{META_AUTH_URL}?{urlencode(params)}"
    logger.info(f"[META_OAUTH] Generated Auth URL: {auth_url}")
    logger.info(f"[META_OAUTH] Redirecting user {current_user.id} to Meta consent screen")
    
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def meta_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_reason: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    state: Optional[str] = Query(None),  # workspace_id
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Meta.
    
    WHAT:
        Exchanges authorization code for access token.
        Fetches ad account IDs and creates connection.
    WHY:
        Completes OAuth flow and stores encrypted tokens.
    """
    # Validate configuration
    if not META_APP_ID or not META_APP_SECRET:
        logger.error("[META_OAUTH] OAuth not configured - missing credentials")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?meta_oauth=error&message=oauth_not_configured"
        )
    
    # Handle errors from Meta
    if error:
        logger.error(f"[META_OAUTH] OAuth error: {error} - {error_reason} - {error_description}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?meta_oauth=error&message={error}"
        )
    
    if not code:
        logger.error("[META_OAUTH] Missing authorization code")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?meta_oauth=error&message=missing_code"
        )
    
    # Validate state parameter (workspace_id)
    if not state:
        logger.error("[META_OAUTH] Missing state parameter")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?meta_oauth=error&message=missing_state"
        )
    
    # Verify workspace exists
    from app.models import Workspace
    workspace = db.query(Workspace).filter(Workspace.id == state).first()
    if not workspace:
        logger.error(f"[META_OAUTH] Invalid workspace ID: {state}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?meta_oauth=error&message=invalid_workspace"
        )
    
    # Exchange code for tokens
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.get(
                META_TOKEN_URL,
                params={
                    "client_id": META_APP_ID,
                    "client_secret": META_APP_SECRET,
                    "redirect_uri": META_REDIRECT_URI,
                    "code": code,
                }
            )
            token_response.raise_for_status()
            token_data = token_response.json()
    except Exception as e:
        logger.exception("[META_OAUTH] Failed to exchange code for tokens")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?meta_oauth=error&message=token_exchange_failed"
        )
    
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in")  # seconds
    
    if not access_token:
        logger.error("[META_OAUTH] Missing access token in response")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?meta_oauth=error&message=missing_tokens"
        )
    
    # Check if token is short-lived (expires_in < 5184000 = 60 days)
    # If short-lived, exchange for long-lived token
    if expires_in and expires_in < 5184000:
        logger.info(f"[META_OAUTH] Token is short-lived ({expires_in}s), exchanging for long-lived token")
        try:
            async with httpx.AsyncClient() as client:
                exchange_response = await client.get(
                    META_EXCHANGE_TOKEN_URL,
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": META_APP_ID,
                        "client_secret": META_APP_SECRET,
                        "fb_exchange_token": access_token,
                    }
                )
                exchange_response.raise_for_status()
                exchange_data = exchange_response.json()
                access_token = exchange_data.get("access_token")
                expires_in = exchange_data.get("expires_in", expires_in)
                logger.info(f"[META_OAUTH] Exchanged for long-lived token (expires in {expires_in}s)")
        except Exception as e:
            logger.warning(f"[META_OAUTH] Failed to exchange for long-lived token: {e}, using short-lived token")
    
    # Fetch accessible ad accounts using the access token
    try:
        async with httpx.AsyncClient() as client:
            # First, get user's ad accounts
            accounts_response = await client.get(
                "https://graph.facebook.com/v24.0/me/adaccounts",
                params={
                    "fields": "id,name,account_id,currency,timezone_name",
                    "access_token": access_token,
                }
            )
            accounts_response.raise_for_status()
            accounts_data = accounts_response.json()
            
            ad_accounts = accounts_data.get("data", [])
            
            if not ad_accounts:
                logger.error("[META_OAUTH] No accessible ad accounts found")
                return RedirectResponse(
                    url=f"{FRONTEND_URL}/settings?meta_oauth=error&message=no_ad_accounts"
                )
            
            logger.info(f"[META_OAUTH] Found {len(ad_accounts)} accessible ad account(s)")
            
            # Deduplicate accounts by account_id (numeric ID)
            # Meta returns the same account multiple times if accessed through different paths
            # (e.g., direct ownership + Business portfolio access)
            accounts_by_id = {}
            for account in ad_accounts:
                account_id = account.get("id", "").replace("act_", "")  # Remove 'act_' prefix for storage
                full_id = account.get("id")  # Keep full 'act_123456789' format
                
                # Use account_id as key for deduplication
                if account_id not in accounts_by_id:
                    accounts_by_id[account_id] = {
                        "id": full_id,  # Keep full 'act_123456789' format for API calls
                        "account_id": account_id,  # Numeric ID for storage
                        "name": account.get("name", f"Meta Ads {account_id}"),
                        "currency": account.get("currency", "USD"),
                        "timezone": account.get("timezone_name", "UTC"),
                        "sources": [],  # Track how user accesses this account
                    }
                
                # Track this access path (for future use - showing portfolio context)
                account_name = account.get("name", f"Meta Ads {account_id}")
                if account_name not in accounts_by_id[account_id]["sources"]:
                    accounts_by_id[account_id]["sources"].append(account_name)
            
            # Convert to list for selection
            accounts_for_selection = list(accounts_by_id.values())
            
            # Log deduplication results
            if len(ad_accounts) > len(accounts_for_selection):
                logger.info(f"[META_OAUTH] Deduplicated {len(ad_accounts)} accounts to {len(accounts_for_selection)} unique accounts")
            
            for acc in accounts_for_selection:
                logger.info(f"[META_OAUTH] Found ad account: {acc['name']} ({acc['id']})")
            
    except Exception as e:
        logger.exception(f"[META_OAUTH] Failed to fetch ad accounts: {str(e)}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?meta_oauth=error&message=account_fetch_failed"
        )
    
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
    
    # Calculate expiration time
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None
    
    # Store in Redis with 10 minute TTL (600 seconds)
    selection_data_json = json.dumps({
        "accounts": accounts_for_selection,
        "workspace_id": workspace_id,
        "access_token": access_token,
        "expires_in": expires_in,
        "expires_at": expires_at.isoformat() if expires_at else None,
    })
    
    app_state.context_manager.redis_client.setex(
        f"meta_oauth_selection:{session_id}",
        600,  # TTL in seconds
        selection_data_json
    )
    
    logger.info(f"[META_OAUTH] Stored selection data with session_id: {session_id}")
    
    return RedirectResponse(
        url=f"{FRONTEND_URL}/settings?meta_oauth=select&session_id={session_id}"
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
    selection_data_json = app_state.context_manager.redis_client.get(f"meta_oauth_selection:{session_id}")
    
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
        "session_id": session_id,
    }


class ConnectSelectedRequest(BaseModel):
    account_ids: List[str]  # List of account IDs (with 'act_' prefix)
    session_id: str


@router.post("/connect-selected")
async def connect_selected_accounts(
    request: ConnectSelectedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create connections for selected Meta ad accounts."""
    from app import state as app_state
    
    if not app_state.context_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is required for OAuth flow but is currently unavailable. Please configure REDIS_URL."
        )
    
    # Retrieve selection data from Redis
    selection_data_json = app_state.context_manager.redis_client.get(f"meta_oauth_selection:{request.session_id}")
    
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
    expires_in = selection_data.get("expires_in")
    expires_at_str = selection_data.get("expires_at")
    expires_at = datetime.fromisoformat(expires_at_str) if expires_at_str else None
    
    created_connections = []
    updated_connections = []
    
    try:
        for account_data in selected_accounts:
            # Use account_id (numeric) for external_account_id storage
            account_id = account_data["account_id"]
            
            connection = db.query(Connection).filter(
                Connection.workspace_id == workspace_id,
                Connection.provider == ProviderEnum.meta,
                Connection.external_account_id == account_id,
            ).first()
            
            if not connection:
                connection = Connection(
                    provider=ProviderEnum.meta,
                    external_account_id=account_id,
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
                logger.info(f"[META_OAUTH] Created new connection for account {account_id}")
            else:
                connection.name = account_data["name"]
                connection.timezone = account_data["timezone"]
                connection.currency_code = account_data["currency"]
                connection.status = "active"
                updated_connections.append(connection)
                logger.info(f"[META_OAUTH] Updating existing connection for account {account_id}")
            
            # Store encrypted tokens for each connection
            # Meta uses access_token only (no refresh token)
            store_connection_token(
                db,
                connection,
                access_token=access_token,
                refresh_token=None,  # Meta doesn't use refresh tokens
                expires_at=expires_at,
                scope=",".join(META_SCOPES),
                ad_account_ids=[account_data["id"]],  # Store full 'act_123456789' format
            )
        
        db.commit()
        
        # Clean up session data (if Redis is available)
        if app_state.context_manager:
            app_state.context_manager.redis_client.delete(f"meta_oauth_selection:{request.session_id}")
        
        total_connections = len(created_connections) + len(updated_connections)
        logger.info(
            f"[META_OAUTH] Successfully connected {total_connections} Meta ad account(s) "
            f"({len(created_connections)} new, {len(updated_connections)} updated) to workspace {workspace_id}"
        )
        
        return {
            "success": True,
            "connections_created": len(created_connections),
            "connections_updated": len(updated_connections),
            "total": total_connections,
            "connection_ids": [str(c.id) for c in created_connections + updated_connections],
        }
        
    except Exception as e:
        db.rollback()
        logger.exception(f"[META_OAUTH] Failed to create/update connections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connections: {str(e)}"
        )

