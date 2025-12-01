"""Google Click ID (gclid) Resolution Service.

WHAT:
    Resolves gclid to actual Google Ads campaign/ad group/ad data.
    Uses Google Ads API ClickView resource for high-confidence attribution.

WHY:
    - gclid contains the most accurate attribution data (directly from Google)
    - Higher confidence than UTM matching (gclid is cryptographically tied to the click)
    - Enables exact campaign/ad group/ad attribution

HOW:
    1. Query click_view resource with gclid + click date
    2. Returns campaign, ad group, and ad information
    3. Results are cached in Redis to avoid repeated API calls

CONSTRAINTS:
    - click_view requires ONE day filter (can't query date ranges)
    - Only last 90 days of click data available
    - Requires active Google Ads connection with valid refresh token

REFERENCES:
    - https://developers.google.com/google-ads/api/fields/v21/click_view
    - docs/living-docs/ATTRIBUTION_ENGINE.md
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class GclidResolutionResult:
    """Result of gclid resolution.

    WHAT: Contains campaign/ad group/ad data from resolved gclid
    WHY: Structured return type for attribution service consumption
    """
    campaign_id: str
    campaign_name: str
    ad_group_id: Optional[str] = None
    ad_group_name: Optional[str] = None
    ad_id: Optional[str] = None
    click_date: Optional[str] = None
    customer_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for caching/serialization."""
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "ad_group_id": self.ad_group_id,
            "ad_group_name": self.ad_group_name,
            "ad_id": self.ad_id,
            "click_date": self.click_date,
            "customer_id": self.customer_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GclidResolutionResult":
        """Create from dictionary (e.g., from cache)."""
        return cls(
            campaign_id=data["campaign_id"],
            campaign_name=data["campaign_name"],
            ad_group_id=data.get("ad_group_id"),
            ad_group_name=data.get("ad_group_name"),
            ad_id=data.get("ad_id"),
            click_date=data.get("click_date"),
            customer_id=data.get("customer_id"),
        )


class GclidResolutionService:
    """Service for resolving Google Click IDs to campaign/ad data.

    WHAT: Looks up gclid via Google Ads API to get exact click attribution
    WHY: Provides highest-confidence attribution for Google Ads clicks

    Usage:
        ```python
        service = GclidResolutionService(db)
        result = await service.resolve_gclid(
            gclid="CjwKCAjw...",
            workspace_id=workspace_uuid,
            click_date=date(2025, 11, 30)
        )
        if result:
            print(f"Click from campaign: {result.campaign_name}")
        ```
    """

    # Cache TTL in seconds (7 days - gclid data doesn't change)
    CACHE_TTL = 7 * 24 * 60 * 60

    def __init__(self, db: Session):
        self.db = db

    async def resolve_gclid(
        self,
        gclid: str,
        workspace_id: UUID,
        click_date: Optional[date] = None,
    ) -> Optional[GclidResolutionResult]:
        """Resolve a gclid to campaign/ad data.

        WHAT: Looks up gclid in Google Ads API to get exact attribution data
        WHY: gclid resolution provides highest-confidence attribution

        Args:
            gclid: Google Click ID from URL parameter
            workspace_id: Workspace UUID (to find Google connection)
            click_date: Date of the click (required for click_view query).
                       If not provided, will try today and yesterday.

        Returns:
            GclidResolutionResult with campaign/ad data, or None if not found

        Notes:
            - Results are cached in Redis for 7 days
            - Only clicks from last 90 days can be resolved
            - Requires active Google Ads connection for workspace
        """
        if not gclid:
            return None

        # Check cache first
        cached = await self._get_from_cache(gclid)
        if cached:
            logger.debug(f"[GCLID] Cache hit for {gclid[:20]}...")
            return cached

        # Find Google Ads connection for workspace
        connection = self._get_google_connection(workspace_id)
        if not connection:
            logger.debug(f"[GCLID] No active Google connection for workspace {workspace_id}")
            return None

        # Get refresh token for API calls
        from app.services.token_service import get_decrypted_token
        refresh_token = get_decrypted_token(self.db, connection.id, "refresh")
        if not refresh_token:
            logger.warning(f"[GCLID] No refresh token for connection {connection.id}")
            return None

        # Get customer ID (external_account_id)
        customer_id = connection.external_account_id
        if not customer_id:
            logger.warning(f"[GCLID] No customer ID for connection {connection.id}")
            return None

        # Normalize customer ID (remove dashes)
        customer_id = "".join(ch for ch in customer_id if ch.isdigit())

        # Determine dates to query
        dates_to_try = self._get_dates_to_query(click_date)

        # Query Google Ads API
        result = await self._query_gclid(
            gclid=gclid,
            customer_id=customer_id,
            refresh_token=refresh_token,
            dates=dates_to_try,
        )

        if result:
            # Cache the result
            await self._save_to_cache(gclid, result)
            logger.info(
                f"[GCLID] Resolved {gclid[:20]}... to campaign {result.campaign_name}",
                extra={"campaign_id": result.campaign_id, "customer_id": customer_id}
            )

        return result

    def _get_google_connection(self, workspace_id: UUID):
        """Get active Google Ads connection for workspace.

        WHAT: Queries database for Google connection
        WHY: Need connection credentials to call Google Ads API
        """
        from app.models import Connection, ProviderEnum

        return self.db.query(Connection).filter(
            Connection.workspace_id == workspace_id,
            Connection.provider == ProviderEnum.google,
            Connection.status == "active",
        ).first()

    def _get_dates_to_query(self, click_date: Optional[date]) -> list[date]:
        """Get list of dates to query for gclid.

        WHAT: Returns dates to try when looking up gclid
        WHY: click_view requires exact date filter

        Args:
            click_date: Known click date, if available

        Returns:
            List of dates to try (up to 3 days if date unknown)
        """
        today = date.today()

        if click_date:
            # If we know the date, just use it
            # But also try adjacent days in case of timezone differences
            return [
                click_date,
                click_date - timedelta(days=1),
                click_date + timedelta(days=1),
            ]

        # If no date known, try last few days
        return [
            today,
            today - timedelta(days=1),
            today - timedelta(days=2),
        ]

    async def _query_gclid(
        self,
        gclid: str,
        customer_id: str,
        refresh_token: str,
        dates: list[date],
    ) -> Optional[GclidResolutionResult]:
        """Query Google Ads API for gclid data.

        WHAT: Makes GAQL query to click_view resource
        WHY: Retrieves campaign/ad data for the gclid

        Args:
            gclid: Google Click ID
            customer_id: Google Ads customer ID (10 digits)
            refresh_token: OAuth refresh token
            dates: List of dates to try (click_view requires single day filter)

        Returns:
            GclidResolutionResult if found, None otherwise
        """
        try:
            from app.services.google_ads_client import GAdsClient

            # Build client with connection's refresh token
            client = GAdsClient(
                client=GAdsClient._build_client_from_tokens(
                    refresh_token=refresh_token,
                    login_customer_id=customer_id,
                )
            )

            # Try each date until we find the gclid
            for query_date in dates:
                # Check if date is within 90-day limit
                if (date.today() - query_date).days > 90:
                    continue

                result = self._query_single_date(client, customer_id, gclid, query_date)
                if result:
                    return result

            logger.debug(f"[GCLID] No results found for {gclid[:20]}... in dates {dates}")
            return None

        except Exception as e:
            logger.error(f"[GCLID] API error resolving {gclid[:20]}...: {e}")
            return None

    def _query_single_date(
        self,
        client,
        customer_id: str,
        gclid: str,
        query_date: date,
    ) -> Optional[GclidResolutionResult]:
        """Query click_view for a single date.

        WHAT: Executes GAQL query for gclid on specific date
        WHY: click_view requires one-day filter constraint
        """
        # GAQL query for click_view
        # Note: gclid is returned but we filter by it in WHERE
        query = f"""
            SELECT
                click_view.gclid,
                click_view.ad_group_ad,
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                segments.date
            FROM click_view
            WHERE segments.date = '{query_date.isoformat()}'
            AND click_view.gclid = '{gclid}'
        """

        try:
            rows = list(client.search(customer_id, query))

            if not rows:
                return None

            # Take first result
            row = rows[0]

            # Extract ad_group_ad resource name to get ad ID
            ad_group_ad = getattr(row.click_view, "ad_group_ad", None)
            ad_id = None
            if ad_group_ad:
                # Resource name format: customers/{cid}/adGroupAds/{ag_id}~{ad_id}
                parts = str(ad_group_ad).split("~")
                if len(parts) == 2:
                    ad_id = parts[1]

            return GclidResolutionResult(
                campaign_id=str(row.campaign.id),
                campaign_name=row.campaign.name,
                ad_group_id=str(row.ad_group.id) if row.ad_group.id else None,
                ad_group_name=row.ad_group.name if row.ad_group.name else None,
                ad_id=ad_id,
                click_date=str(row.segments.date),
                customer_id=customer_id,
            )

        except Exception as e:
            # Log but don't raise - might be normal (no click on this date)
            logger.debug(f"[GCLID] Query for {query_date} failed: {e}")
            return None

    async def _get_from_cache(self, gclid: str) -> Optional[GclidResolutionResult]:
        """Get cached gclid resolution result.

        WHAT: Checks Redis cache for previously resolved gclid
        WHY: Avoid repeated API calls for same gclid
        """
        try:
            from app import state as app_state
            import json

            if not app_state.context_manager:
                return None

            cache_key = f"gclid:{gclid}"
            cached_json = app_state.context_manager.redis_client.get(cache_key)

            if cached_json:
                data = json.loads(cached_json)
                return GclidResolutionResult.from_dict(data)

            return None

        except Exception as e:
            logger.debug(f"[GCLID] Cache read error: {e}")
            return None

    async def _save_to_cache(self, gclid: str, result: GclidResolutionResult) -> None:
        """Save gclid resolution result to cache.

        WHAT: Stores result in Redis with TTL
        WHY: Avoid repeated API calls for same gclid
        """
        try:
            from app import state as app_state
            import json

            if not app_state.context_manager:
                return

            cache_key = f"gclid:{gclid}"
            app_state.context_manager.redis_client.setex(
                cache_key,
                self.CACHE_TTL,
                json.dumps(result.to_dict()),
            )

        except Exception as e:
            logger.debug(f"[GCLID] Cache write error: {e}")


async def resolve_gclid_for_attribution(
    gclid: str,
    workspace_id: UUID,
    landed_at: Optional[datetime],
    db: Session,
) -> Optional[GclidResolutionResult]:
    """Convenience function for attribution service.

    WHAT: Resolves gclid and returns structured result
    WHY: Simple interface for attribution flow

    Args:
        gclid: Google Click ID
        workspace_id: Workspace UUID
        landed_at: Landing timestamp (used to determine click date)
        db: Database session

    Returns:
        GclidResolutionResult or None

    Usage:
        ```python
        result = await resolve_gclid_for_attribution(
            gclid="CjwKCAjw...",
            workspace_id=workspace_id,
            landed_at=touchpoint.touched_at,
            db=db,
        )
        if result:
            # Use result.campaign_id, result.campaign_name, etc.
        ```
    """
    # Convert datetime to date for click lookup
    click_date = landed_at.date() if landed_at else None

    service = GclidResolutionService(db)
    return await service.resolve_gclid(
        gclid=gclid,
        workspace_id=workspace_id,
        click_date=click_date,
    )
