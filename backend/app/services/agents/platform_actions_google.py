"""
Google Ads API Actions Client for Agents.

WHAT:
    Provides mutating API operations for Google Ads campaigns.
    Campaign-level only (no ad group/ad mutations per design decision).

WHY:
    Agents need to:
    - Scale campaign budgets
    - Pause/resume campaigns
    - Make autonomous decisions based on performance

SUPPORTED OPERATIONS:
    Campaign Level ONLY:
        - Update status (ENABLED, PAUSED)
        - Update budget (via CampaignBudget)

SAFETY:
    All operations:
    - Fetch live state before action
    - Validate preconditions
    - Store state_before / state_after
    - Support rollback

REFERENCES:
    - Google Ads API docs: https://developers.google.com/google-ads/api
    - backend/app/services/google_ads_client.py (read operations)
    - backend/app/services/agents/platform_health.py
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ...models import Connection, ProviderEnum

logger = logging.getLogger(__name__)


class GoogleCampaignStatus(str, Enum):
    """Valid Google campaign statuses."""
    ENABLED = "ENABLED"
    PAUSED = "PAUSED"
    REMOVED = "REMOVED"


@dataclass
class GoogleLiveState:
    """
    Live state fetched from Google Ads API before action.

    WHAT: Current state of campaign directly from Google
    WHY: We need actual current values, not cached data
    """
    campaign_id: str
    customer_id: str
    status: str
    budget_micros: Optional[int] = None  # Budget in micros (1/1,000,000 of currency)
    budget_id: Optional[str] = None  # Resource name of the budget
    name: Optional[str] = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GoogleActionResult:
    """
    Result of a Google Ads API mutation.

    WHAT: Complete record of what happened
    WHY: Audit trail, rollback capability, verification
    """
    success: bool
    campaign_id: str
    customer_id: str
    action_type: str  # scale_budget, pause, resume

    state_before: Dict[str, Any]
    state_after: Dict[str, Any]

    description: str
    error: Optional[str] = None
    duration_ms: int = 0

    # For rollback
    rollback_possible: bool = True
    rollback_data: Optional[Dict[str, Any]] = None


class GooglePlatformActions:
    """
    Google Ads API mutation client for agents.

    WHAT: Executes campaign-level mutations with safety
    WHY: Agents need controlled, auditable API access

    NOTE: Google Ads uses 'micros' for monetary values.
          $10.00 = 10,000,000 micros
    """

    def __init__(
        self,
        db: Session,
        connection_id: UUID,
    ):
        """
        Initialize Google actions client.

        Parameters:
            db: Database session
            connection_id: Google connection ID
        """
        self.db = db
        self.connection_id = connection_id
        self._connection: Optional[Connection] = None
        self._client = None

    @property
    def connection(self) -> Connection:
        """Get connection record."""
        if self._connection:
            return self._connection

        self._connection = self.db.query(Connection).filter(
            Connection.id == self.connection_id
        ).first()
        if not self._connection:
            raise ValueError(f"Connection {self.connection_id} not found")
        return self._connection

    @property
    def customer_id(self) -> str:
        """Get Google customer ID from connection."""
        return self.connection.external_account_id

    def _get_client(self):
        """Get or create Google Ads client."""
        if self._client:
            return self._client

        from ..token_service import get_decrypted_token
        from ..google_ads_client import GoogleAdsClient

        refresh_token = get_decrypted_token(self.db, self.connection_id, "refresh")
        if not refresh_token:
            raise ValueError("Could not get refresh token for connection")

        self._client = GoogleAdsClient._build_client_from_tokens(
            refresh_token=refresh_token,
            login_customer_id=self.customer_id,
        )
        return self._client

    # =========================================================================
    # Live State Fetching
    # =========================================================================

    async def get_live_state(self, campaign_id: str) -> GoogleLiveState:
        """
        Fetch current campaign state directly from Google Ads API.

        Parameters:
            campaign_id: Google campaign ID (numeric string)

        Returns:
            GoogleLiveState with current values

        WHAT: Get real-time state before any mutation
        WHY: Cached data may be stale, need actual values
        """
        client = self._get_client()
        ga_service = client.get_service("GoogleAdsService")

        # Query campaign with budget
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.campaign_budget,
                campaign_budget.amount_micros
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """

        try:
            response = ga_service.search(
                customer_id=self.customer_id,
                query=query,
            )

            for row in response:
                return GoogleLiveState(
                    campaign_id=str(row.campaign.id),
                    customer_id=self.customer_id,
                    status=row.campaign.status.name,
                    budget_micros=row.campaign_budget.amount_micros if row.campaign_budget else None,
                    budget_id=row.campaign.campaign_budget if row.campaign.campaign_budget else None,
                    name=row.campaign.name,
                )

            raise GoogleApiError(f"Campaign {campaign_id} not found")

        except Exception as e:
            logger.exception(f"Failed to fetch Google campaign state: {e}")
            raise GoogleApiError(f"Failed to fetch state: {str(e)}")

    # =========================================================================
    # Campaign Status Actions
    # =========================================================================

    async def update_campaign_status(
        self,
        campaign_id: str,
        new_status: GoogleCampaignStatus,
    ) -> GoogleActionResult:
        """
        Update campaign status (pause/resume).

        Parameters:
            campaign_id: Google campaign ID
            new_status: ENABLED or PAUSED

        Returns:
            GoogleActionResult with before/after state
        """
        import time
        start = time.time()

        try:
            # Fetch live state
            live_state = await self.get_live_state(campaign_id)

            state_before = {
                "status": live_state.status,
                "budget_micros": live_state.budget_micros,
            }

            # Build mutation
            client = self._get_client()
            campaign_service = client.get_service("CampaignService")

            # Create campaign operation
            campaign_operation = client.get_type("CampaignOperation")
            campaign = campaign_operation.update

            # Set resource name
            campaign.resource_name = campaign_service.campaign_path(
                self.customer_id, campaign_id
            )

            # Set new status
            campaign.status = client.enums.CampaignStatusEnum.CampaignStatus[new_status.value]

            # Create field mask for update
            client.copy_from(
                campaign_operation.update_mask,
                client.get_type("FieldMask")(paths=["status"])
            )

            # Execute mutation
            response = campaign_service.mutate_campaigns(
                customer_id=self.customer_id,
                operations=[campaign_operation],
            )

            # Verify change
            new_state = await self.get_live_state(campaign_id)

            state_after = {
                "status": new_state.status,
                "budget_micros": new_state.budget_micros,
            }

            return GoogleActionResult(
                success=True,
                campaign_id=campaign_id,
                customer_id=self.customer_id,
                action_type="update_status",
                state_before=state_before,
                state_after=state_after,
                description=f"Campaign status changed from {live_state.status} to {new_status.value}",
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=True,
                rollback_data={"old_status": live_state.status},
            )

        except GoogleApiError:
            raise
        except Exception as e:
            logger.exception(f"Campaign status update failed: {e}")
            return GoogleActionResult(
                success=False,
                campaign_id=campaign_id,
                customer_id=self.customer_id,
                action_type="update_status",
                state_before=state_before if 'state_before' in locals() else {},
                state_after=state_before if 'state_before' in locals() else {},
                description="Campaign status update failed",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=False,
            )

    # =========================================================================
    # Campaign Budget Actions
    # =========================================================================

    async def update_campaign_budget(
        self,
        campaign_id: str,
        new_budget_micros: int,
    ) -> GoogleActionResult:
        """
        Update campaign budget.

        Parameters:
            campaign_id: Google campaign ID
            new_budget_micros: New budget in micros ($10 = 10,000,000 micros)

        Returns:
            GoogleActionResult with before/after state

        NOTE: Google budgets are shared resources. This updates the budget
              associated with the campaign.
        """
        import time
        start = time.time()

        try:
            # Fetch live state
            live_state = await self.get_live_state(campaign_id)

            if not live_state.budget_id:
                return GoogleActionResult(
                    success=False,
                    campaign_id=campaign_id,
                    customer_id=self.customer_id,
                    action_type="update_budget",
                    state_before={},
                    state_after={},
                    description="Campaign has no budget to update",
                    error="No budget resource found for campaign",
                    duration_ms=int((time.time() - start) * 1000),
                    rollback_possible=False,
                )

            old_budget = live_state.budget_micros

            state_before = {
                "status": live_state.status,
                "budget_micros": old_budget,
            }

            # Build budget mutation
            client = self._get_client()
            campaign_budget_service = client.get_service("CampaignBudgetService")

            # Create budget operation
            budget_operation = client.get_type("CampaignBudgetOperation")
            budget = budget_operation.update

            # Set resource name (the budget_id is the full resource name)
            budget.resource_name = live_state.budget_id

            # Set new amount
            budget.amount_micros = new_budget_micros

            # Create field mask
            client.copy_from(
                budget_operation.update_mask,
                client.get_type("FieldMask")(paths=["amount_micros"])
            )

            # Execute mutation
            response = campaign_budget_service.mutate_campaign_budgets(
                customer_id=self.customer_id,
                operations=[budget_operation],
            )

            # Verify change
            new_state = await self.get_live_state(campaign_id)

            state_after = {
                "status": new_state.status,
                "budget_micros": new_state.budget_micros,
            }

            # Format for description
            old_formatted = f"${old_budget/1_000_000:.2f}" if old_budget else "N/A"
            new_formatted = f"${new_budget_micros/1_000_000:.2f}"

            return GoogleActionResult(
                success=True,
                campaign_id=campaign_id,
                customer_id=self.customer_id,
                action_type="update_budget",
                state_before=state_before,
                state_after=state_after,
                description=f"Campaign budget: {old_formatted} → {new_formatted}",
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=True,
                rollback_data={
                    "budget_id": live_state.budget_id,
                    "old_budget_micros": old_budget,
                },
            )

        except GoogleApiError:
            raise
        except Exception as e:
            logger.exception(f"Campaign budget update failed: {e}")
            return GoogleActionResult(
                success=False,
                campaign_id=campaign_id,
                customer_id=self.customer_id,
                action_type="update_budget",
                state_before=state_before if 'state_before' in locals() else {},
                state_after=state_before if 'state_before' in locals() else {},
                description="Campaign budget update failed",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=False,
            )

    # =========================================================================
    # Rollback
    # =========================================================================

    async def rollback_action(
        self,
        result: GoogleActionResult,
    ) -> GoogleActionResult:
        """
        Rollback a previous action.

        Parameters:
            result: Previous action result with rollback_data

        Returns:
            New GoogleActionResult for the rollback operation
        """
        if not result.rollback_possible or not result.rollback_data:
            return GoogleActionResult(
                success=False,
                campaign_id=result.campaign_id,
                customer_id=result.customer_id,
                action_type="rollback",
                state_before={},
                state_after={},
                description="Rollback not possible for this action",
                error="No rollback data available",
                rollback_possible=False,
            )

        if result.action_type == "update_status":
            old_status = result.rollback_data.get("old_status")
            if old_status:
                return await self.update_campaign_status(
                    result.campaign_id,
                    GoogleCampaignStatus(old_status),
                )

        elif result.action_type == "update_budget":
            old_budget = result.rollback_data.get("old_budget_micros")
            if old_budget:
                return await self.update_campaign_budget(
                    result.campaign_id,
                    old_budget,
                )

        return GoogleActionResult(
            success=False,
            campaign_id=result.campaign_id,
            customer_id=result.customer_id,
            action_type="rollback",
            state_before={},
            state_after={},
            description="Unknown action type for rollback",
            error=f"Cannot rollback action type: {result.action_type}",
            rollback_possible=False,
        )


class GoogleApiError(Exception):
    """Raised when Google Ads API returns an error."""
    pass


# =========================================================================
# Utility Functions
# =========================================================================

def dollars_to_micros(dollars: float) -> int:
    """
    Convert dollars to Google micros.

    Parameters:
        dollars: Amount in dollars (e.g., 10.50)

    Returns:
        Amount in micros (e.g., 10500000)
    """
    return int(dollars * 1_000_000)


def micros_to_dollars(micros: int) -> float:
    """
    Convert Google micros to dollars.

    Parameters:
        micros: Amount in micros (e.g., 10500000)

    Returns:
        Amount in dollars (e.g., 10.50)
    """
    return micros / 1_000_000
