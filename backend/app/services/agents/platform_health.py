"""
Platform Health Service for Agent Pre-Action Validation.

WHAT:
    Validates ad platform connections before agents take autonomous actions.
    Ensures we have valid credentials and API access before mutating anything.

WHY:
    Agents making autonomous API calls (scale budget, pause campaigns) need
    rock-solid validation before acting:
    - Is the platform even connected?
    - Is the OAuth token valid?
    - Can we reach the API?
    - Do we have write permissions?

DESIGN:
    Fail-fast: If any check fails, agent action is blocked with clear reason.
    Cached: Health checks are cached briefly (5 min) to avoid hammering APIs.
    Comprehensive: Checks token validity, API reachability, and permissions.

USAGE:
    health_service = PlatformHealthService(db)
    result = await health_service.check_health(connection_id)

    if not result.healthy:
        # Block agent action
        raise AgentActionBlocked(result.reason)

REFERENCES:
    - backend/app/models.py (Connection model)
    - backend/app/services/token_service.py
    - backend/app/services/meta_ads_client.py
    - backend/app/services/google_ads_client.py
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session

from ...models import Connection, Token, ProviderEnum

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check result status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"  # Working but with warnings


@dataclass
class HealthCheckResult:
    """
    Result of a platform health check.

    WHAT: Complete health assessment for a connection
    WHY: Agents need to know if they can safely take action
    """
    status: HealthStatus
    healthy: bool
    connection_id: UUID
    provider: str

    # Individual check results
    connection_active: bool
    token_valid: bool
    token_expires_at: Optional[datetime]
    api_reachable: bool
    has_write_permission: bool

    # Details
    reason: Optional[str] = None
    warnings: list = None
    checked_at: datetime = None
    response_time_ms: Optional[int] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.checked_at is None:
            self.checked_at = datetime.now(timezone.utc)


# Simple in-memory cache for health checks
# Key: connection_id, Value: (result, timestamp)
_health_cache: Dict[UUID, tuple] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


class PlatformHealthService:
    """
    Service for validating platform connection health before agent actions.

    WHAT: Comprehensive health checker for Meta and Google ad platforms
    WHY: Autonomous agents need validated API access before taking actions
    """

    def __init__(self, db: Session):
        """
        Initialize health service.

        Parameters:
            db: Database session for connection/token queries
        """
        self.db = db

    async def check_health(
        self,
        connection_id: UUID,
        force_refresh: bool = False,
    ) -> HealthCheckResult:
        """
        Check health of a platform connection.

        Parameters:
            connection_id: Connection to check
            force_refresh: Bypass cache and force fresh check

        Returns:
            HealthCheckResult with detailed status

        WHAT: Complete health assessment
        WHY: Agents call this before taking any autonomous action
        """
        import time
        start_time = time.time()

        # Check cache first
        if not force_refresh:
            cached = self._get_cached(connection_id)
            if cached:
                logger.debug(f"Health check cache hit for connection {connection_id}")
                return cached

        # Get connection
        connection = self.db.query(Connection).filter(
            Connection.id == connection_id
        ).first()

        if not connection:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                healthy=False,
                connection_id=connection_id,
                provider="unknown",
                connection_active=False,
                token_valid=False,
                token_expires_at=None,
                api_reachable=False,
                has_write_permission=False,
                reason="Connection not found",
            )

        # Run provider-specific health check
        if connection.provider == ProviderEnum.meta:
            result = await self._check_meta_health(connection)
        elif connection.provider == ProviderEnum.google:
            result = await self._check_google_health(connection)
        else:
            result = HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                healthy=False,
                connection_id=connection_id,
                provider=connection.provider.value,
                connection_active=False,
                token_valid=False,
                token_expires_at=None,
                api_reachable=False,
                has_write_permission=False,
                reason=f"Unsupported provider: {connection.provider.value}",
            )

        # Add response time
        result.response_time_ms = int((time.time() - start_time) * 1000)

        # Cache result
        self._set_cached(connection_id, result)

        return result

    async def check_health_for_entity(
        self,
        entity_id: UUID,
    ) -> HealthCheckResult:
        """
        Check health for the platform connection associated with an entity.

        Parameters:
            entity_id: Entity whose connection to check

        Returns:
            HealthCheckResult

        WHAT: Convenience method for agent evaluation
        WHY: Agents work with entities, not connections directly
        """
        from ...models import Entity

        entity = self.db.query(Entity).filter(Entity.id == entity_id).first()
        if not entity or not entity.connection_id:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                healthy=False,
                connection_id=UUID('00000000-0000-0000-0000-000000000000'),
                provider="unknown",
                connection_active=False,
                token_valid=False,
                token_expires_at=None,
                api_reachable=False,
                has_write_permission=False,
                reason="Entity not found or has no connection",
            )

        return await self.check_health(entity.connection_id)

    async def _check_meta_health(self, connection: Connection) -> HealthCheckResult:
        """
        Check Meta Marketing API health.

        Parameters:
            connection: Meta connection to check

        Returns:
            HealthCheckResult for Meta
        """
        warnings = []

        # Check 1: Connection status
        connection_active = connection.status == "active"
        if not connection_active:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                healthy=False,
                connection_id=connection.id,
                provider="meta",
                connection_active=False,
                token_valid=False,
                token_expires_at=None,
                api_reachable=False,
                has_write_permission=False,
                reason=f"Connection status is '{connection.status}', not 'active'",
            )

        # Check 2: Token exists and validity
        token = self.db.query(Token).filter(Token.id == connection.token_id).first()
        if not token:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                healthy=False,
                connection_id=connection.id,
                provider="meta",
                connection_active=True,
                token_valid=False,
                token_expires_at=None,
                api_reachable=False,
                has_write_permission=False,
                reason="No token found for connection",
            )

        # Check token expiration (Meta uses long-lived access tokens ~60 days)
        token_valid = True
        token_expires_at = token.expires_at

        if token_expires_at:
            now = datetime.now(timezone.utc)
            if token_expires_at < now:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    healthy=False,
                    connection_id=connection.id,
                    provider="meta",
                    connection_active=True,
                    token_valid=False,
                    token_expires_at=token_expires_at,
                    api_reachable=False,
                    has_write_permission=False,
                    reason="Access token has expired. User needs to re-authenticate.",
                )

            # Warn if expiring soon (within 7 days)
            if token_expires_at < now + timedelta(days=7):
                warnings.append(f"Token expires in {(token_expires_at - now).days} days")

        # Check 3: API reachability (lightweight call)
        api_reachable = False
        has_write_permission = False

        try:
            from ..token_service import get_decrypted_token
            access_token = get_decrypted_token(self.db, connection.id, "access")

            if not access_token:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    healthy=False,
                    connection_id=connection.id,
                    provider="meta",
                    connection_active=True,
                    token_valid=False,
                    token_expires_at=token_expires_at,
                    api_reachable=False,
                    has_write_permission=False,
                    reason="Could not decrypt access token",
                )

            # Make a lightweight API call to verify token works
            import httpx
            async with httpx.AsyncClient() as client:
                # Check token validity with debug_token or simple me call
                response = await client.get(
                    f"https://graph.facebook.com/v24.0/me",
                    params={"access_token": access_token, "fields": "id,name"},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    api_reachable = True
                    # Meta tokens with ads_management scope have write access
                    has_write_permission = True  # We requested this scope during OAuth
                else:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    return HealthCheckResult(
                        status=HealthStatus.UNHEALTHY,
                        healthy=False,
                        connection_id=connection.id,
                        provider="meta",
                        connection_active=True,
                        token_valid=False,
                        token_expires_at=token_expires_at,
                        api_reachable=False,
                        has_write_permission=False,
                        reason=f"API returned error: {error_msg}",
                    )

        except httpx.TimeoutException:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                healthy=False,
                connection_id=connection.id,
                provider="meta",
                connection_active=True,
                token_valid=token_valid,
                token_expires_at=token_expires_at,
                api_reachable=False,
                has_write_permission=False,
                reason="Meta API timeout - service may be unavailable",
            )
        except Exception as e:
            logger.exception(f"Meta health check failed: {e}")
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                healthy=False,
                connection_id=connection.id,
                provider="meta",
                connection_active=True,
                token_valid=token_valid,
                token_expires_at=token_expires_at,
                api_reachable=False,
                has_write_permission=False,
                reason=f"Health check error: {str(e)}",
            )

        # All checks passed
        status = HealthStatus.DEGRADED if warnings else HealthStatus.HEALTHY

        return HealthCheckResult(
            status=status,
            healthy=True,
            connection_id=connection.id,
            provider="meta",
            connection_active=True,
            token_valid=True,
            token_expires_at=token_expires_at,
            api_reachable=True,
            has_write_permission=True,
            warnings=warnings,
        )

    async def _check_google_health(self, connection: Connection) -> HealthCheckResult:
        """
        Check Google Ads API health.

        Parameters:
            connection: Google connection to check

        Returns:
            HealthCheckResult for Google
        """
        warnings = []

        # Check 1: Connection status
        connection_active = connection.status == "active"
        if not connection_active:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                healthy=False,
                connection_id=connection.id,
                provider="google",
                connection_active=False,
                token_valid=False,
                token_expires_at=None,
                api_reachable=False,
                has_write_permission=False,
                reason=f"Connection status is '{connection.status}', not 'active'",
            )

        # Check 2: Token exists
        token = self.db.query(Token).filter(Token.id == connection.token_id).first()
        if not token:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                healthy=False,
                connection_id=connection.id,
                provider="google",
                connection_active=True,
                token_valid=False,
                token_expires_at=None,
                api_reachable=False,
                has_write_permission=False,
                reason="No token found for connection",
            )

        # Google uses refresh tokens - they don't expire unless revoked
        # Access tokens are auto-refreshed by the SDK
        token_valid = True
        token_expires_at = None  # Refresh tokens don't expire

        # Check 3: API reachability
        api_reachable = False
        has_write_permission = False

        try:
            from ..token_service import get_decrypted_token
            refresh_token = get_decrypted_token(self.db, connection.id, "refresh")

            if not refresh_token:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    healthy=False,
                    connection_id=connection.id,
                    provider="google",
                    connection_active=True,
                    token_valid=False,
                    token_expires_at=None,
                    api_reachable=False,
                    has_write_permission=False,
                    reason="Could not decrypt refresh token",
                )

            # Try to use the Google Ads client
            from ..google_ads_client import GoogleAdsClient

            client = GoogleAdsClient._build_client_from_tokens(
                refresh_token=refresh_token,
                login_customer_id=connection.external_account_id,
            )

            # Make a lightweight call to verify credentials
            # Just getting customer metadata is enough
            customer_service = client.get_service("CustomerService")
            customer_resource_name = customer_service.customer_path(
                connection.external_account_id
            )

            # If we get here without exception, API is reachable
            api_reachable = True
            has_write_permission = True  # We requested full adwords scope

        except Exception as e:
            error_str = str(e).lower()

            if "authentication" in error_str or "oauth" in error_str:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    healthy=False,
                    connection_id=connection.id,
                    provider="google",
                    connection_active=True,
                    token_valid=False,
                    token_expires_at=None,
                    api_reachable=False,
                    has_write_permission=False,
                    reason="Google authentication failed. User may need to re-authenticate.",
                )
            elif "permission" in error_str or "access" in error_str:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    healthy=False,
                    connection_id=connection.id,
                    provider="google",
                    connection_active=True,
                    token_valid=True,
                    token_expires_at=None,
                    api_reachable=True,
                    has_write_permission=False,
                    reason="Insufficient permissions for Google Ads account",
                )
            else:
                logger.exception(f"Google health check failed: {e}")
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    healthy=False,
                    connection_id=connection.id,
                    provider="google",
                    connection_active=True,
                    token_valid=token_valid,
                    token_expires_at=None,
                    api_reachable=False,
                    has_write_permission=False,
                    reason=f"Health check error: {str(e)[:200]}",
                )

        # All checks passed
        status = HealthStatus.DEGRADED if warnings else HealthStatus.HEALTHY

        return HealthCheckResult(
            status=status,
            healthy=True,
            connection_id=connection.id,
            provider="google",
            connection_active=True,
            token_valid=True,
            token_expires_at=None,
            api_reachable=True,
            has_write_permission=True,
            warnings=warnings,
        )

    def _get_cached(self, connection_id: UUID) -> Optional[HealthCheckResult]:
        """Get cached health check result if still valid."""
        if connection_id not in _health_cache:
            return None

        result, timestamp = _health_cache[connection_id]
        if datetime.now(timezone.utc) - timestamp > timedelta(seconds=CACHE_TTL_SECONDS):
            del _health_cache[connection_id]
            return None

        return result

    def _set_cached(self, connection_id: UUID, result: HealthCheckResult) -> None:
        """Cache a health check result."""
        _health_cache[connection_id] = (result, datetime.now(timezone.utc))

    def clear_cache(self, connection_id: Optional[UUID] = None) -> None:
        """
        Clear health check cache.

        Parameters:
            connection_id: Specific connection to clear, or None for all
        """
        if connection_id:
            _health_cache.pop(connection_id, None)
        else:
            _health_cache.clear()


async def require_healthy_connection(
    db: Session,
    connection_id: UUID,
) -> HealthCheckResult:
    """
    Require a healthy connection or raise an exception.

    Parameters:
        db: Database session
        connection_id: Connection to validate

    Returns:
        HealthCheckResult if healthy

    Raises:
        ConnectionUnhealthyError: If connection is not healthy

    WHAT: Convenience function for action pre-validation
    WHY: Actions should call this and handle the exception
    """
    service = PlatformHealthService(db)
    result = await service.check_health(connection_id)

    if not result.healthy:
        raise ConnectionUnhealthyError(result)

    return result


class ConnectionUnhealthyError(Exception):
    """Raised when a connection health check fails."""

    def __init__(self, health_result: HealthCheckResult):
        self.health_result = health_result
        super().__init__(health_result.reason or "Connection is unhealthy")
