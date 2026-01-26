"""
Meta Marketing API Actions Client for Agents.

WHAT:
    Provides mutating API operations for Meta ad campaigns, ad sets, and ads.
    Used by agents to autonomously manage advertising.

WHY:
    Agents need to:
    - Scale budgets (campaign and ad set level)
    - Pause/resume campaigns, ad sets, ads
    - Make autonomous decisions based on performance

SUPPORTED OPERATIONS:
    Campaign Level:
        - Update status (ACTIVE, PAUSED)
        - Update daily_budget
        - Update lifetime_budget

    Ad Set Level:
        - Update status (ACTIVE, PAUSED)
        - Update daily_budget
        - Update lifetime_budget
        - Update bid_amount

    Ad Level:
        - Update status (ACTIVE, PAUSED)

SAFETY:
    All operations:
    - Fetch live state before action
    - Validate preconditions
    - Store state_before / state_after
    - Support rollback

REFERENCES:
    - Meta Marketing API docs: https://developers.facebook.com/docs/marketing-api
    - backend/app/services/meta_ads_client.py (read operations)
    - backend/app/services/agents/platform_health.py
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from ...models import Connection, Entity, ProviderEnum

logger = logging.getLogger(__name__)


class MetaEntityLevel(str, Enum):
    """Meta Ads hierarchy levels."""
    CAMPAIGN = "campaign"
    ADSET = "adset"
    AD = "ad"


class MetaStatus(str, Enum):
    """Valid Meta entity statuses."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


@dataclass
class MetaLiveState:
    """
    Live state fetched from Meta API before action.

    WHAT: Current state of entity directly from Meta
    WHY: We need actual current values, not cached data
    """
    entity_id: str
    entity_level: MetaEntityLevel
    status: str
    daily_budget: Optional[int] = None  # In cents
    lifetime_budget: Optional[int] = None  # In cents
    bid_amount: Optional[int] = None  # In cents (ad set only)
    name: Optional[str] = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetaActionResult:
    """
    Result of a Meta API mutation.

    WHAT: Complete record of what happened
    WHY: Audit trail, rollback capability, verification
    """
    success: bool
    entity_id: str
    entity_level: MetaEntityLevel
    action_type: str  # scale_budget, pause, resume, etc.

    state_before: Dict[str, Any]
    state_after: Dict[str, Any]

    description: str
    error: Optional[str] = None
    duration_ms: int = 0

    # For rollback
    rollback_possible: bool = True
    rollback_payload: Optional[Dict[str, Any]] = None


class MetaPlatformActions:
    """
    Meta Marketing API mutation client for agents.

    WHAT: Executes campaign/ad set/ad mutations with safety
    WHY: Agents need controlled, auditable API access
    """

    API_VERSION = "v24.0"
    BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

    def __init__(
        self,
        db: Session,
        connection_id: UUID,
        access_token: Optional[str] = None,
    ):
        """
        Initialize Meta actions client.

        Parameters:
            db: Database session
            connection_id: Meta connection ID
            access_token: Optional pre-fetched token (will fetch if None)
        """
        self.db = db
        self.connection_id = connection_id
        self._access_token = access_token
        self._connection: Optional[Connection] = None

    @property
    def access_token(self) -> str:
        """Get access token, fetching if needed."""
        if self._access_token:
            return self._access_token

        from ..token_service import get_decrypted_token
        token = get_decrypted_token(self.db, self.connection_id, "access")
        if not token:
            raise ValueError("Could not get access token for connection")
        self._access_token = token
        return token

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

    # =========================================================================
    # Live State Fetching
    # =========================================================================

    async def get_live_state(
        self,
        meta_entity_id: str,
        level: MetaEntityLevel,
    ) -> MetaLiveState:
        """
        Fetch current state directly from Meta API.

        Parameters:
            meta_entity_id: Meta's entity ID
            level: campaign, adset, or ad

        Returns:
            MetaLiveState with current values

        WHAT: Get real-time state before any mutation
        WHY: Cached data may be stale, need actual values
        """
        fields = self._get_fields_for_level(level)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/{meta_entity_id}",
                params={
                    "access_token": self.access_token,
                    "fields": ",".join(fields),
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                raise MetaApiError(f"Failed to fetch state: {error_msg}")

            data = response.json()

        return MetaLiveState(
            entity_id=meta_entity_id,
            entity_level=level,
            status=data.get("status") or data.get("effective_status", "UNKNOWN"),
            daily_budget=int(data["daily_budget"]) if data.get("daily_budget") else None,
            lifetime_budget=int(data["lifetime_budget"]) if data.get("lifetime_budget") else None,
            bid_amount=int(data["bid_amount"]) if data.get("bid_amount") else None,
            name=data.get("name"),
            raw_response=data,
        )

    def _get_fields_for_level(self, level: MetaEntityLevel) -> List[str]:
        """Get relevant fields for each entity level."""
        base_fields = ["id", "name", "status", "effective_status"]

        if level == MetaEntityLevel.CAMPAIGN:
            return base_fields + ["daily_budget", "lifetime_budget", "objective"]
        elif level == MetaEntityLevel.ADSET:
            return base_fields + ["daily_budget", "lifetime_budget", "bid_amount", "billing_event"]
        else:  # AD
            return base_fields + ["creative"]

    # =========================================================================
    # Campaign Actions
    # =========================================================================

    async def update_campaign_status(
        self,
        campaign_id: str,
        new_status: MetaStatus,
    ) -> MetaActionResult:
        """
        Update campaign status (pause/resume).

        Parameters:
            campaign_id: Meta campaign ID
            new_status: ACTIVE or PAUSED

        Returns:
            MetaActionResult with before/after state
        """
        import time
        start = time.time()

        # Fetch live state
        live_state = await self.get_live_state(campaign_id, MetaEntityLevel.CAMPAIGN)

        state_before = {
            "status": live_state.status,
            "daily_budget": live_state.daily_budget,
        }

        # Execute update
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/{campaign_id}",
                    data={
                        "status": new_status.value,
                        "access_token": self.access_token,
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    return MetaActionResult(
                        success=False,
                        entity_id=campaign_id,
                        entity_level=MetaEntityLevel.CAMPAIGN,
                        action_type="update_status",
                        state_before=state_before,
                        state_after=state_before,  # No change
                        description=f"Failed to update campaign status",
                        error=error_msg,
                        duration_ms=int((time.time() - start) * 1000),
                        rollback_possible=False,
                    )

            # Verify change
            new_state = await self.get_live_state(campaign_id, MetaEntityLevel.CAMPAIGN)

            state_after = {
                "status": new_state.status,
                "daily_budget": new_state.daily_budget,
            }

            return MetaActionResult(
                success=True,
                entity_id=campaign_id,
                entity_level=MetaEntityLevel.CAMPAIGN,
                action_type="update_status",
                state_before=state_before,
                state_after=state_after,
                description=f"Campaign status changed from {live_state.status} to {new_status.value}",
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=True,
                rollback_payload={"status": live_state.status},
            )

        except Exception as e:
            logger.exception(f"Campaign status update failed: {e}")
            return MetaActionResult(
                success=False,
                entity_id=campaign_id,
                entity_level=MetaEntityLevel.CAMPAIGN,
                action_type="update_status",
                state_before=state_before,
                state_after=state_before,
                description="Campaign status update failed",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=False,
            )

    async def update_campaign_budget(
        self,
        campaign_id: str,
        new_budget_cents: int,
        budget_type: str = "daily",  # daily or lifetime
    ) -> MetaActionResult:
        """
        Update campaign budget.

        Parameters:
            campaign_id: Meta campaign ID
            new_budget_cents: New budget in cents (smallest currency unit)
            budget_type: "daily" or "lifetime"

        Returns:
            MetaActionResult with before/after state

        NOTE: Meta requires budget to be at least 10% more than spent amount
              when decreasing. We don't validate this here - Meta will error.
        """
        import time
        start = time.time()

        # Fetch live state
        live_state = await self.get_live_state(campaign_id, MetaEntityLevel.CAMPAIGN)

        budget_field = f"{budget_type}_budget"
        old_budget = (
            live_state.daily_budget if budget_type == "daily"
            else live_state.lifetime_budget
        )

        state_before = {
            "status": live_state.status,
            budget_field: old_budget,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/{campaign_id}",
                    data={
                        budget_field: str(new_budget_cents),
                        "access_token": self.access_token,
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    return MetaActionResult(
                        success=False,
                        entity_id=campaign_id,
                        entity_level=MetaEntityLevel.CAMPAIGN,
                        action_type="update_budget",
                        state_before=state_before,
                        state_after=state_before,
                        description=f"Failed to update campaign {budget_type} budget",
                        error=error_msg,
                        duration_ms=int((time.time() - start) * 1000),
                        rollback_possible=False,
                    )

            # Verify change
            new_state = await self.get_live_state(campaign_id, MetaEntityLevel.CAMPAIGN)
            new_budget = (
                new_state.daily_budget if budget_type == "daily"
                else new_state.lifetime_budget
            )

            state_after = {
                "status": new_state.status,
                budget_field: new_budget,
            }

            # Format budget for description
            old_formatted = f"${old_budget/100:.2f}" if old_budget else "N/A"
            new_formatted = f"${new_budget/100:.2f}" if new_budget else "N/A"

            return MetaActionResult(
                success=True,
                entity_id=campaign_id,
                entity_level=MetaEntityLevel.CAMPAIGN,
                action_type="update_budget",
                state_before=state_before,
                state_after=state_after,
                description=f"Campaign {budget_type} budget: {old_formatted} → {new_formatted}",
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=True,
                rollback_payload={budget_field: old_budget},
            )

        except Exception as e:
            logger.exception(f"Campaign budget update failed: {e}")
            return MetaActionResult(
                success=False,
                entity_id=campaign_id,
                entity_level=MetaEntityLevel.CAMPAIGN,
                action_type="update_budget",
                state_before=state_before,
                state_after=state_before,
                description="Campaign budget update failed",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=False,
            )

    # =========================================================================
    # Ad Set Actions
    # =========================================================================

    async def update_adset_status(
        self,
        adset_id: str,
        new_status: MetaStatus,
    ) -> MetaActionResult:
        """
        Update ad set status (pause/resume).

        Parameters:
            adset_id: Meta ad set ID
            new_status: ACTIVE or PAUSED

        Returns:
            MetaActionResult with before/after state
        """
        import time
        start = time.time()

        live_state = await self.get_live_state(adset_id, MetaEntityLevel.ADSET)

        state_before = {
            "status": live_state.status,
            "daily_budget": live_state.daily_budget,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/{adset_id}",
                    data={
                        "status": new_status.value,
                        "access_token": self.access_token,
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    return MetaActionResult(
                        success=False,
                        entity_id=adset_id,
                        entity_level=MetaEntityLevel.ADSET,
                        action_type="update_status",
                        state_before=state_before,
                        state_after=state_before,
                        description="Failed to update ad set status",
                        error=error_msg,
                        duration_ms=int((time.time() - start) * 1000),
                        rollback_possible=False,
                    )

            new_state = await self.get_live_state(adset_id, MetaEntityLevel.ADSET)

            state_after = {
                "status": new_state.status,
                "daily_budget": new_state.daily_budget,
            }

            return MetaActionResult(
                success=True,
                entity_id=adset_id,
                entity_level=MetaEntityLevel.ADSET,
                action_type="update_status",
                state_before=state_before,
                state_after=state_after,
                description=f"Ad set status changed from {live_state.status} to {new_status.value}",
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=True,
                rollback_payload={"status": live_state.status},
            )

        except Exception as e:
            logger.exception(f"Ad set status update failed: {e}")
            return MetaActionResult(
                success=False,
                entity_id=adset_id,
                entity_level=MetaEntityLevel.ADSET,
                action_type="update_status",
                state_before=state_before,
                state_after=state_before,
                description="Ad set status update failed",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=False,
            )

    async def update_adset_budget(
        self,
        adset_id: str,
        new_budget_cents: int,
        budget_type: str = "daily",
    ) -> MetaActionResult:
        """
        Update ad set budget.

        Parameters:
            adset_id: Meta ad set ID
            new_budget_cents: New budget in cents
            budget_type: "daily" or "lifetime"

        Returns:
            MetaActionResult with before/after state
        """
        import time
        start = time.time()

        live_state = await self.get_live_state(adset_id, MetaEntityLevel.ADSET)

        budget_field = f"{budget_type}_budget"
        old_budget = (
            live_state.daily_budget if budget_type == "daily"
            else live_state.lifetime_budget
        )

        state_before = {
            "status": live_state.status,
            budget_field: old_budget,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/{adset_id}",
                    data={
                        budget_field: str(new_budget_cents),
                        "access_token": self.access_token,
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    return MetaActionResult(
                        success=False,
                        entity_id=adset_id,
                        entity_level=MetaEntityLevel.ADSET,
                        action_type="update_budget",
                        state_before=state_before,
                        state_after=state_before,
                        description=f"Failed to update ad set {budget_type} budget",
                        error=error_msg,
                        duration_ms=int((time.time() - start) * 1000),
                        rollback_possible=False,
                    )

            new_state = await self.get_live_state(adset_id, MetaEntityLevel.ADSET)
            new_budget = (
                new_state.daily_budget if budget_type == "daily"
                else new_state.lifetime_budget
            )

            state_after = {
                "status": new_state.status,
                budget_field: new_budget,
            }

            old_formatted = f"${old_budget/100:.2f}" if old_budget else "N/A"
            new_formatted = f"${new_budget/100:.2f}" if new_budget else "N/A"

            return MetaActionResult(
                success=True,
                entity_id=adset_id,
                entity_level=MetaEntityLevel.ADSET,
                action_type="update_budget",
                state_before=state_before,
                state_after=state_after,
                description=f"Ad set {budget_type} budget: {old_formatted} → {new_formatted}",
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=True,
                rollback_payload={budget_field: old_budget},
            )

        except Exception as e:
            logger.exception(f"Ad set budget update failed: {e}")
            return MetaActionResult(
                success=False,
                entity_id=adset_id,
                entity_level=MetaEntityLevel.ADSET,
                action_type="update_budget",
                state_before=state_before,
                state_after=state_before,
                description="Ad set budget update failed",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=False,
            )

    # =========================================================================
    # Ad Actions
    # =========================================================================

    async def update_ad_status(
        self,
        ad_id: str,
        new_status: MetaStatus,
    ) -> MetaActionResult:
        """
        Update ad status (pause/resume).

        Parameters:
            ad_id: Meta ad ID
            new_status: ACTIVE or PAUSED

        Returns:
            MetaActionResult with before/after state
        """
        import time
        start = time.time()

        live_state = await self.get_live_state(ad_id, MetaEntityLevel.AD)

        state_before = {"status": live_state.status}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/{ad_id}",
                    data={
                        "status": new_status.value,
                        "access_token": self.access_token,
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    return MetaActionResult(
                        success=False,
                        entity_id=ad_id,
                        entity_level=MetaEntityLevel.AD,
                        action_type="update_status",
                        state_before=state_before,
                        state_after=state_before,
                        description="Failed to update ad status",
                        error=error_msg,
                        duration_ms=int((time.time() - start) * 1000),
                        rollback_possible=False,
                    )

            new_state = await self.get_live_state(ad_id, MetaEntityLevel.AD)

            state_after = {"status": new_state.status}

            return MetaActionResult(
                success=True,
                entity_id=ad_id,
                entity_level=MetaEntityLevel.AD,
                action_type="update_status",
                state_before=state_before,
                state_after=state_after,
                description=f"Ad status changed from {live_state.status} to {new_status.value}",
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=True,
                rollback_payload={"status": live_state.status},
            )

        except Exception as e:
            logger.exception(f"Ad status update failed: {e}")
            return MetaActionResult(
                success=False,
                entity_id=ad_id,
                entity_level=MetaEntityLevel.AD,
                action_type="update_status",
                state_before=state_before,
                state_after=state_before,
                description="Ad status update failed",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=False,
            )

    # =========================================================================
    # Rollback
    # =========================================================================

    async def rollback_action(
        self,
        result: MetaActionResult,
    ) -> MetaActionResult:
        """
        Rollback a previous action using stored rollback payload.

        Parameters:
            result: Previous action result with rollback_payload

        Returns:
            New MetaActionResult for the rollback operation
        """
        if not result.rollback_possible or not result.rollback_payload:
            return MetaActionResult(
                success=False,
                entity_id=result.entity_id,
                entity_level=result.entity_level,
                action_type="rollback",
                state_before={},
                state_after={},
                description="Rollback not possible for this action",
                error="No rollback payload available",
                rollback_possible=False,
            )

        import time
        start = time.time()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/{result.entity_id}",
                    data={
                        **result.rollback_payload,
                        "access_token": self.access_token,
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    return MetaActionResult(
                        success=False,
                        entity_id=result.entity_id,
                        entity_level=result.entity_level,
                        action_type="rollback",
                        state_before=result.state_after,
                        state_after=result.state_after,
                        description="Rollback failed",
                        error=error_msg,
                        duration_ms=int((time.time() - start) * 1000),
                        rollback_possible=False,
                    )

            return MetaActionResult(
                success=True,
                entity_id=result.entity_id,
                entity_level=result.entity_level,
                action_type="rollback",
                state_before=result.state_after,
                state_after=result.state_before,  # Rolled back to original
                description=f"Successfully rolled back {result.action_type}",
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=False,  # Can't rollback a rollback
            )

        except Exception as e:
            logger.exception(f"Rollback failed: {e}")
            return MetaActionResult(
                success=False,
                entity_id=result.entity_id,
                entity_level=result.entity_level,
                action_type="rollback",
                state_before=result.state_after,
                state_after=result.state_after,
                description="Rollback failed",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
                rollback_possible=False,
            )


class MetaApiError(Exception):
    """Raised when Meta API returns an error."""
    pass
