"""
Platform-Aware Action Executor for Agents.

WHAT:
    Executes agent actions with full platform integration:
    - Health checks before action
    - Live state fetching
    - Actual platform API calls
    - Safety validation
    - Audit logging

WHY:
    Bridges the gap between abstract actions and real platform APIs.
    Ensures all safety checks are performed before autonomous actions.

FLOW:
    1. Health Check → Is connection healthy?
    2. Live State → Get current entity state from platform
    3. Pre-Validation → Should we proceed?
    4. Execute → Make the actual API call
    5. Verify → Confirm change took effect
    6. Log → Record everything for audit

REFERENCES:
    - backend/app/services/agents/actions.py (action definitions)
    - backend/app/services/agents/platform_health.py
    - backend/app/services/agents/platform_actions_meta.py
    - backend/app/services/agents/platform_actions_google.py
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ...models import Entity, Connection, ProviderEnum, LevelEnum
from .actions import Action, ActionContext, ActionResult, action_from_dict
from .platform_health import PlatformHealthService, require_healthy_connection, ConnectionUnhealthyError

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """
    Extended context for action execution with platform integration.

    WHAT: All data needed for platform-aware action execution
    WHY: Standard ActionContext + database session + entity details
    """
    db: Session
    agent_id: UUID
    agent_name: str
    workspace_id: UUID
    entity: Entity
    observations: Dict[str, float]
    evaluation_event_id: Optional[UUID] = None
    user_email: Optional[str] = None


class PlatformActionExecutor:
    """
    Executes agent actions with full platform integration.

    WHAT: Orchestrates health checks, live state, and actual API calls
    WHY: Safe, auditable, reversible autonomous actions
    """

    def __init__(self, db: Session):
        """
        Initialize executor.

        Parameters:
            db: Database session
        """
        self.db = db
        self.health_service = PlatformHealthService(db)

    async def execute_action(
        self,
        action_config: Dict[str, Any],
        context: ExecutionContext,
    ) -> ActionResult:
        """
        Execute a single action with full safety checks.

        Parameters:
            action_config: Action configuration dict
            context: Execution context with entity and observations

        Returns:
            ActionResult with full details

        FLOW:
            1. Parse action config
            2. Check if action needs platform access
            3. If yes: health check → live state → execute
            4. If no: execute directly (email, webhook)
        """
        import time
        start = time.time()

        try:
            # Parse action
            action = action_from_dict(action_config)
            action_type = action_config.get("type", "unknown")

            # Check if this action needs platform access
            if action_type in ["scale_budget", "pause_campaign", "resume_campaign"]:
                return await self._execute_platform_action(
                    action_config, action, context
                )
            else:
                # Non-platform actions (email, webhook)
                return await self._execute_simple_action(action, context)

        except Exception as e:
            logger.exception(f"Action execution failed: {e}")
            return ActionResult(
                success=False,
                description="Action execution failed",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def _execute_platform_action(
        self,
        action_config: Dict[str, Any],
        action: Action,
        context: ExecutionContext,
    ) -> ActionResult:
        """
        Execute an action that requires platform API access.

        Parameters:
            action_config: Action configuration
            action: Parsed action object
            context: Execution context

        Returns:
            ActionResult
        """
        import time
        start = time.time()

        entity = context.entity
        action_type = action_config.get("type")

        # Step 1: Verify entity has connection
        if not entity.connection_id:
            return ActionResult(
                success=False,
                description="Entity has no platform connection",
                error="No connection_id on entity",
                duration_ms=int((time.time() - start) * 1000),
                skipped=True,
                skip_reason="No platform connection",
            )

        # Step 2: Health check
        try:
            health_result = await self.health_service.check_health(entity.connection_id)
            if not health_result.healthy:
                return ActionResult(
                    success=False,
                    description=f"Platform connection unhealthy: {health_result.reason}",
                    error=health_result.reason,
                    duration_ms=int((time.time() - start) * 1000),
                    skipped=True,
                    skip_reason=f"Connection unhealthy: {health_result.reason}",
                )
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return ActionResult(
                success=False,
                description="Health check failed",
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
                skipped=True,
                skip_reason="Health check failed",
            )

        # Step 3: Get connection and route to appropriate platform
        connection = self.db.query(Connection).filter(
            Connection.id == entity.connection_id
        ).first()

        if not connection:
            return ActionResult(
                success=False,
                description="Connection not found",
                error="Connection record missing",
                duration_ms=int((time.time() - start) * 1000),
            )

        # Step 4: Execute based on provider
        if connection.provider == ProviderEnum.meta:
            return await self._execute_meta_action(
                action_config, context, connection
            )
        elif connection.provider == ProviderEnum.google:
            return await self._execute_google_action(
                action_config, context, connection
            )
        else:
            return ActionResult(
                success=False,
                description=f"Unsupported provider: {connection.provider.value}",
                error="Provider not supported for actions",
                duration_ms=int((time.time() - start) * 1000),
            )

    async def _execute_meta_action(
        self,
        action_config: Dict[str, Any],
        context: ExecutionContext,
        connection: Connection,
    ) -> ActionResult:
        """
        Execute action via Meta Marketing API.

        Parameters:
            action_config: Action configuration
            context: Execution context
            connection: Meta connection

        Returns:
            ActionResult
        """
        from .platform_actions_meta import (
            MetaPlatformActions,
            MetaStatus,
            MetaEntityLevel,
        )

        action_type = action_config.get("type")
        entity = context.entity

        # Initialize Meta client
        meta_client = MetaPlatformActions(
            db=self.db,
            connection_id=connection.id,
        )

        # Determine Meta entity level from our entity level
        meta_level = self._map_entity_level_to_meta(entity.level)

        # Get Meta entity ID (external_id stored on entity)
        meta_entity_id = entity.external_id
        if not meta_entity_id:
            return ActionResult(
                success=False,
                description="Entity has no external_id (Meta ID)",
                error="Missing external_id",
            )

        # Execute based on action type
        if action_type == "scale_budget":
            return await self._execute_meta_scale_budget(
                meta_client, meta_entity_id, meta_level, action_config, context
            )
        elif action_type == "pause_campaign":
            return await self._execute_meta_pause(
                meta_client, meta_entity_id, meta_level
            )
        elif action_type == "resume_campaign":
            return await self._execute_meta_resume(
                meta_client, meta_entity_id, meta_level
            )
        else:
            return ActionResult(
                success=False,
                description=f"Unknown Meta action: {action_type}",
                error="Unknown action type",
            )

    async def _execute_meta_scale_budget(
        self,
        client,
        meta_entity_id: str,
        meta_level,
        action_config: Dict[str, Any],
        context: ExecutionContext,
    ) -> ActionResult:
        """Execute Meta budget scaling."""
        from .platform_actions_meta import MetaEntityLevel

        # Get current state
        live_state = await client.get_live_state(meta_entity_id, meta_level)

        # Determine which budget to scale
        current_budget = live_state.daily_budget or live_state.lifetime_budget
        budget_type = "daily" if live_state.daily_budget else "lifetime"

        if not current_budget:
            return ActionResult(
                success=False,
                description="Entity has no budget to scale",
                error="No budget found",
                state_before={"status": live_state.status},
            )

        # Calculate new budget
        scale_percent = action_config.get("scale_percent", 0)
        max_budget = action_config.get("max_budget")
        min_budget = action_config.get("min_budget")

        # Current budget is in cents, convert to dollars for calculation
        current_dollars = current_budget / 100
        new_dollars = current_dollars * (1 + scale_percent / 100)

        # Apply caps
        if max_budget:
            new_dollars = min(new_dollars, max_budget)
        if min_budget:
            new_dollars = max(new_dollars, min_budget)

        new_budget_cents = int(new_dollars * 100)

        # Execute based on level
        if meta_level == MetaEntityLevel.CAMPAIGN:
            result = await client.update_campaign_budget(
                meta_entity_id, new_budget_cents, budget_type
            )
        elif meta_level == MetaEntityLevel.ADSET:
            result = await client.update_adset_budget(
                meta_entity_id, new_budget_cents, budget_type
            )
        else:
            return ActionResult(
                success=False,
                description="Cannot scale budget at ad level",
                error="Ads don't have budgets",
            )

        return ActionResult(
            success=result.success,
            description=result.description,
            error=result.error,
            duration_ms=result.duration_ms,
            state_before=result.state_before,
            state_after=result.state_after,
            rollback_possible=result.rollback_possible,
        )

    async def _execute_meta_pause(
        self,
        client,
        meta_entity_id: str,
        meta_level,
    ) -> ActionResult:
        """Execute Meta pause action."""
        from .platform_actions_meta import MetaStatus, MetaEntityLevel

        if meta_level == MetaEntityLevel.CAMPAIGN:
            result = await client.update_campaign_status(meta_entity_id, MetaStatus.PAUSED)
        elif meta_level == MetaEntityLevel.ADSET:
            result = await client.update_adset_status(meta_entity_id, MetaStatus.PAUSED)
        elif meta_level == MetaEntityLevel.AD:
            result = await client.update_ad_status(meta_entity_id, MetaStatus.PAUSED)
        else:
            return ActionResult(
                success=False,
                description=f"Unknown entity level: {meta_level}",
                error="Invalid level",
            )

        return ActionResult(
            success=result.success,
            description=result.description,
            error=result.error,
            duration_ms=result.duration_ms,
            state_before=result.state_before,
            state_after=result.state_after,
            rollback_possible=result.rollback_possible,
        )

    async def _execute_meta_resume(
        self,
        client,
        meta_entity_id: str,
        meta_level,
    ) -> ActionResult:
        """Execute Meta resume action."""
        from .platform_actions_meta import MetaStatus, MetaEntityLevel

        if meta_level == MetaEntityLevel.CAMPAIGN:
            result = await client.update_campaign_status(meta_entity_id, MetaStatus.ACTIVE)
        elif meta_level == MetaEntityLevel.ADSET:
            result = await client.update_adset_status(meta_entity_id, MetaStatus.ACTIVE)
        elif meta_level == MetaEntityLevel.AD:
            result = await client.update_ad_status(meta_entity_id, MetaStatus.ACTIVE)
        else:
            return ActionResult(
                success=False,
                description=f"Unknown entity level: {meta_level}",
                error="Invalid level",
            )

        return ActionResult(
            success=result.success,
            description=result.description,
            error=result.error,
            duration_ms=result.duration_ms,
            state_before=result.state_before,
            state_after=result.state_after,
            rollback_possible=result.rollback_possible,
        )

    async def _execute_google_action(
        self,
        action_config: Dict[str, Any],
        context: ExecutionContext,
        connection: Connection,
    ) -> ActionResult:
        """
        Execute action via Google Ads API.

        NOTE: Google actions are campaign-level only.

        Parameters:
            action_config: Action configuration
            context: Execution context
            connection: Google connection

        Returns:
            ActionResult
        """
        from .platform_actions_google import (
            GooglePlatformActions,
            GoogleCampaignStatus,
            dollars_to_micros,
        )

        action_type = action_config.get("type")
        entity = context.entity

        # Google actions are campaign-level only
        if entity.level != LevelEnum.campaign:
            return ActionResult(
                success=False,
                description="Google actions only support campaign level",
                error="Only campaign-level actions supported for Google",
                skipped=True,
                skip_reason="Google only supports campaign-level actions",
            )

        # Initialize Google client
        google_client = GooglePlatformActions(
            db=self.db,
            connection_id=connection.id,
        )

        # Get Google campaign ID
        google_campaign_id = entity.external_id
        if not google_campaign_id:
            return ActionResult(
                success=False,
                description="Entity has no external_id (Google ID)",
                error="Missing external_id",
            )

        # Execute based on action type
        if action_type == "scale_budget":
            return await self._execute_google_scale_budget(
                google_client, google_campaign_id, action_config
            )
        elif action_type == "pause_campaign":
            result = await google_client.update_campaign_status(
                google_campaign_id, GoogleCampaignStatus.PAUSED
            )
            return ActionResult(
                success=result.success,
                description=result.description,
                error=result.error,
                duration_ms=result.duration_ms,
                state_before=result.state_before,
                state_after=result.state_after,
                rollback_possible=result.rollback_possible,
            )
        elif action_type == "resume_campaign":
            result = await google_client.update_campaign_status(
                google_campaign_id, GoogleCampaignStatus.ENABLED
            )
            return ActionResult(
                success=result.success,
                description=result.description,
                error=result.error,
                duration_ms=result.duration_ms,
                state_before=result.state_before,
                state_after=result.state_after,
                rollback_possible=result.rollback_possible,
            )
        else:
            return ActionResult(
                success=False,
                description=f"Unknown Google action: {action_type}",
                error="Unknown action type",
            )

    async def _execute_google_scale_budget(
        self,
        client,
        campaign_id: str,
        action_config: Dict[str, Any],
    ) -> ActionResult:
        """Execute Google budget scaling."""
        from .platform_actions_google import dollars_to_micros, micros_to_dollars

        # Get current state
        live_state = await client.get_live_state(campaign_id)

        if not live_state.budget_micros:
            return ActionResult(
                success=False,
                description="Campaign has no budget to scale",
                error="No budget found",
                state_before={"status": live_state.status},
            )

        # Calculate new budget
        scale_percent = action_config.get("scale_percent", 0)
        max_budget = action_config.get("max_budget")
        min_budget = action_config.get("min_budget")

        current_dollars = micros_to_dollars(live_state.budget_micros)
        new_dollars = current_dollars * (1 + scale_percent / 100)

        # Apply caps
        if max_budget:
            new_dollars = min(new_dollars, max_budget)
        if min_budget:
            new_dollars = max(new_dollars, min_budget)

        new_budget_micros = dollars_to_micros(new_dollars)

        # Execute
        result = await client.update_campaign_budget(campaign_id, new_budget_micros)

        return ActionResult(
            success=result.success,
            description=result.description,
            error=result.error,
            duration_ms=result.duration_ms,
            state_before=result.state_before,
            state_after=result.state_after,
            rollback_possible=result.rollback_possible,
        )

    async def _execute_simple_action(
        self,
        action: Action,
        context: ExecutionContext,
    ) -> ActionResult:
        """
        Execute non-platform action (email, webhook).

        Parameters:
            action: Parsed action object
            context: Execution context

        Returns:
            ActionResult
        """
        # Build standard ActionContext
        action_context = ActionContext(
            agent_id=str(context.agent_id),
            agent_name=context.agent_name,
            entity_id=str(context.entity.id),
            entity_name=context.entity.name,
            entity_provider=(
                context.entity.connection.provider.value
                if context.entity.connection else "unknown"
            ),
            workspace_id=str(context.workspace_id),
            observations=context.observations,
            evaluation_event_id=str(context.evaluation_event_id) if context.evaluation_event_id else "",
            user_email=context.user_email,
        )

        return await action.execute(action_context)

    def _map_entity_level_to_meta(self, level: LevelEnum):
        """Map our EntityLevel to Meta's entity level."""
        from .platform_actions_meta import MetaEntityLevel

        mapping = {
            LevelEnum.campaign: MetaEntityLevel.CAMPAIGN,
            LevelEnum.adset: MetaEntityLevel.ADSET,
            LevelEnum.ad: MetaEntityLevel.AD,
        }
        return mapping.get(level, MetaEntityLevel.CAMPAIGN)


async def execute_agent_actions(
    db: Session,
    agent_id: UUID,
    agent_name: str,
    workspace_id: UUID,
    entity: Entity,
    action_configs: List[Dict[str, Any]],
    observations: Dict[str, float],
    evaluation_event_id: Optional[UUID] = None,
    user_email: Optional[str] = None,
) -> List[ActionResult]:
    """
    Execute all actions for an agent trigger.

    Parameters:
        db: Database session
        agent_id: Agent UUID
        agent_name: Agent name
        workspace_id: Workspace UUID
        entity: Entity being acted on
        action_configs: List of action configurations
        observations: Current metrics
        evaluation_event_id: Triggering evaluation event
        user_email: User email for notifications

    Returns:
        List of ActionResults

    WHAT: Convenience function for evaluation engine
    WHY: Single entry point for action execution
    """
    executor = PlatformActionExecutor(db)

    context = ExecutionContext(
        db=db,
        agent_id=agent_id,
        agent_name=agent_name,
        workspace_id=workspace_id,
        entity=entity,
        observations=observations,
        evaluation_event_id=evaluation_event_id,
        user_email=user_email,
    )

    results = []
    for action_config in action_configs:
        try:
            result = await executor.execute_action(action_config, context)
            results.append(result)
        except Exception as e:
            logger.exception(f"Action execution failed: {e}")
            results.append(ActionResult(
                success=False,
                description="Action execution failed",
                error=str(e),
            ))

    return results
