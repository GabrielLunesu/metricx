"""
Connection Resolver
===================

**Version**: 1.0.0
**Created**: 2025-12-17

Safely resolves workspace connections and instantiates authenticated API clients.

WHY THIS FILE EXISTS
--------------------
Live API calls require authenticated clients for Google Ads and Meta Ads.
This module handles:
- Finding connections for a workspace
- Decrypting OAuth tokens securely
- Instantiating API clients with proper credentials
- Enforcing workspace scoping (security)

SECURITY
--------
- Only returns connections belonging to the specified workspace
- Tokens are decrypted only when needed
- Never logs decrypted tokens
- All access is audit-logged

RELATED FILES
-------------
- app/agent/live_api_tools.py: Uses resolved clients
- app/agent/exceptions.py: ProviderNotConnectedError, TokenExpiredError
- app/services/snapshot_sync_service.py: Similar pattern for sync jobs
- app/security.py: decrypt_secret function
"""

import logging
from typing import Optional, List, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Connection, Token, ProviderEnum
from app.security import decrypt_secret
from app.services.google_ads_client import GAdsClient
from app.services.meta_ads_client import MetaAdsClient
from app.agent.exceptions import (
    ProviderNotConnectedError,
    TokenExpiredError,
)

logger = logging.getLogger(__name__)


class ConnectionResolver:
    """
    Resolves workspace connections and instantiates authenticated API clients.

    WHAT:
        Given a workspace_id, provides methods to get authenticated Google/Meta
        API clients for making live queries.

    WHY:
        Centralizes credential handling for the copilot.
        Enforces workspace scoping for security.
        Handles token decryption and client instantiation.

    SECURITY:
        - All queries filtered by workspace_id
        - Tokens decrypted only when client is requested
        - Access logged for audit trail

    USAGE:
        resolver = ConnectionResolver(db, workspace_id)

        # Get available providers
        providers = resolver.get_available_providers()

        # Get authenticated client
        google_client = resolver.get_google_client()
        meta_client = resolver.get_meta_client()
    """

    def __init__(
        self,
        db: Session,
        workspace_id: str,
    ):
        """
        Initialize resolver for a workspace.

        PARAMETERS:
            db: SQLAlchemy session
            workspace_id: UUID of the workspace to resolve connections for
        """
        self.db = db
        self.workspace_id = str(workspace_id)

        # Cache connections on first access
        self._connections_cache: Optional[List[Connection]] = None

    def _get_workspace_connections(self) -> List[Connection]:
        """
        Get all active connections for the workspace.

        WHAT:
            Queries Connection table filtered by workspace_id and status.

        WHY:
            Needed to find available providers and get credentials.

        RETURNS:
            List of Connection objects

        SECURITY:
            Only returns connections where workspace_id matches.
        """
        if self._connections_cache is not None:
            return self._connections_cache

        self._connections_cache = (
            self.db.query(Connection)
            .filter(
                Connection.workspace_id == self.workspace_id,
                Connection.status == "active",
            )
            .all()
        )

        logger.debug(
            f"[CONNECTION_RESOLVER] Found {len(self._connections_cache)} active connections "
            f"for workspace {self.workspace_id}"
        )

        return self._connections_cache

    def get_available_providers(self) -> List[str]:
        """
        Get list of providers with active connections.

        WHAT:
            Returns unique provider names that have active connections.

        WHY:
            Tells the agent which providers can be queried live.

        RETURNS:
            List of provider strings (e.g., ["google", "meta"])
        """
        connections = self._get_workspace_connections()
        providers = set()

        for conn in connections:
            if conn.provider in (ProviderEnum.google, ProviderEnum.meta):
                providers.add(conn.provider.value)

        return sorted(list(providers))

    def get_connection(
        self,
        provider: Literal["google", "meta"],
        connection_id: Optional[str] = None,
    ) -> Connection:
        """
        Get a specific connection for the provider.

        WHAT:
            Returns a Connection object for the specified provider.

        WHY:
            Needed to get credentials and account info.

        PARAMETERS:
            provider: "google" or "meta"
            connection_id: Optional specific connection UUID (if multiple exist)

        RETURNS:
            Connection object

        RAISES:
            ProviderNotConnectedError: If no connection exists for provider
        """
        connections = self._get_workspace_connections()

        # Filter by provider
        provider_enum = ProviderEnum.google if provider == "google" else ProviderEnum.meta
        provider_connections = [
            c for c in connections if c.provider == provider_enum
        ]

        if not provider_connections:
            logger.warning(
                f"[CONNECTION_RESOLVER] No {provider} connection found for workspace {self.workspace_id}"
            )
            raise ProviderNotConnectedError(provider=provider)

        # If connection_id specified, find that specific one
        if connection_id:
            for conn in provider_connections:
                if str(conn.id) == connection_id:
                    return conn

            logger.warning(
                f"[CONNECTION_RESOLVER] Connection {connection_id} not found for "
                f"{provider} in workspace {self.workspace_id}"
            )
            raise ProviderNotConnectedError(
                provider=provider,
                message=f"Connection {connection_id} not found for {provider}",
            )

        # Return first (usually only) connection for this provider
        return provider_connections[0]

    def get_google_client(
        self,
        connection_id: Optional[str] = None,
    ) -> GAdsClient:
        """
        Get authenticated Google Ads client for workspace.

        WHAT:
            Returns a GAdsClient instance authenticated with workspace credentials.

        WHY:
            Needed to make live Google Ads API calls.

        PARAMETERS:
            connection_id: Optional specific connection UUID

        RETURNS:
            Authenticated GAdsClient

        RAISES:
            ProviderNotConnectedError: If no Google connection exists
            TokenExpiredError: If token is expired/invalid
        """
        connection = self.get_connection("google", connection_id)

        logger.info(
            f"[CONNECTION_RESOLVER] Getting Google client for connection {connection.id} "
            f"(account: {connection.external_account_id})"
        )

        # Check if token exists
        if not connection.token or not connection.token.refresh_token_enc:
            raise TokenExpiredError(
                provider="google",
                connection_id=str(connection.id),
                message="Google Ads connection has no credentials. Please reconnect.",
            )

        try:
            # Decrypt refresh token
            refresh_token = decrypt_secret(
                connection.token.refresh_token_enc,
                context=f"google:{connection.id}:refresh:live_api",
            )

            # Get parent MCC ID if this is a client account
            parent_mcc_id = getattr(connection.token, 'parent_mcc_id', None)

            # Build SDK client from tokens
            sdk_client = GAdsClient._build_client_from_tokens(
                refresh_token,
                login_customer_id=parent_mcc_id,
            )

            return GAdsClient(client=sdk_client)

        except Exception as e:
            logger.error(
                f"[CONNECTION_RESOLVER] Failed to create Google client for {connection.id}: {e}"
            )
            raise TokenExpiredError(
                provider="google",
                connection_id=str(connection.id),
                message=f"Failed to authenticate with Google Ads: {str(e)}",
            )

    def get_meta_client(
        self,
        connection_id: Optional[str] = None,
    ) -> MetaAdsClient:
        """
        Get authenticated Meta Ads client for workspace.

        WHAT:
            Returns a MetaAdsClient instance authenticated with workspace credentials.

        WHY:
            Needed to make live Meta Ads API calls.

        PARAMETERS:
            connection_id: Optional specific connection UUID

        RETURNS:
            Authenticated MetaAdsClient

        RAISES:
            ProviderNotConnectedError: If no Meta connection exists
            TokenExpiredError: If token is expired/invalid
        """
        connection = self.get_connection("meta", connection_id)

        logger.info(
            f"[CONNECTION_RESOLVER] Getting Meta client for connection {connection.id} "
            f"(account: {connection.external_account_id})"
        )

        # Check if token exists
        if not connection.token or not connection.token.access_token_enc:
            raise TokenExpiredError(
                provider="meta",
                connection_id=str(connection.id),
                message="Meta Ads connection has no credentials. Please reconnect.",
            )

        try:
            # Decrypt access token
            access_token = decrypt_secret(
                connection.token.access_token_enc,
                context=f"meta:{connection.id}:access:live_api",
            )

            return MetaAdsClient(access_token=access_token)

        except Exception as e:
            logger.error(
                f"[CONNECTION_RESOLVER] Failed to create Meta client for {connection.id}: {e}"
            )
            raise TokenExpiredError(
                provider="meta",
                connection_id=str(connection.id),
                message=f"Failed to authenticate with Meta Ads: {str(e)}",
            )

    def get_account_id(
        self,
        provider: Literal["google", "meta"],
        connection_id: Optional[str] = None,
    ) -> str:
        """
        Get the external account ID for a provider connection.

        WHAT:
            Returns the account ID used for API calls.

        WHY:
            Some API calls need the account ID as a parameter.

        PARAMETERS:
            provider: "google" or "meta"
            connection_id: Optional specific connection UUID

        RETURNS:
            Account ID string (e.g., "123-456-7890" for Google, "act_123" for Meta)
        """
        connection = self.get_connection(provider, connection_id)
        return connection.external_account_id

    def get_connection_info(
        self,
        provider: Literal["google", "meta"],
        connection_id: Optional[str] = None,
    ) -> dict:
        """
        Get connection metadata without decrypting tokens.

        WHAT:
            Returns connection info for logging/debugging.

        WHY:
            Useful for error messages and audit logs.

        RETURNS:
            Dict with connection metadata (no sensitive data)
        """
        connection = self.get_connection(provider, connection_id)

        return {
            "connection_id": str(connection.id),
            "provider": connection.provider.value,
            "external_account_id": connection.external_account_id,
            "name": connection.name,
            "status": connection.status,
            "timezone": connection.timezone,
            "currency_code": connection.currency_code,
            "connected_at": connection.connected_at.isoformat() if connection.connected_at else None,
        }
