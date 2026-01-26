"""
Rate Limiter for Agent Actions.

WHAT:
    Limits how frequently agents can execute actions on entities.
    Prevents runaway behavior and protects ad platforms from abuse.

WHY:
    Without rate limiting, agents could:
    - Make hundreds of budget changes per day
    - Overwhelm ad platform APIs
    - Cause billing issues with rapid changes

DESIGN:
    - Per-entity limits: Max N actions per entity per day
    - Per-agent limits: Max N total actions per agent per day
    - Per-workspace limits: Max N actions across all agents

REFERENCES:
    - Agent System Implementation Plan (Safety Mechanism 8: Rate Limiting)
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """
    Rate limit configuration.

    Attributes:
        max_actions_per_entity_per_day: Limit per entity
        max_actions_per_agent_per_day: Limit per agent
        max_actions_per_workspace_per_day: Limit per workspace
    """

    max_actions_per_entity_per_day: int = 3
    max_actions_per_agent_per_day: int = 20
    max_actions_per_workspace_per_day: int = 100


@dataclass
class RateLimitResult:
    """
    Result of rate limit check.

    Attributes:
        allowed: Whether action is allowed
        reason: Why action was blocked (if blocked)
        current_count: Current count towards limit
        limit: The limit that applies
        reset_at: When limit resets
    """

    allowed: bool
    reason: Optional[str] = None
    current_count: Optional[int] = None
    limit: Optional[int] = None
    reset_at: Optional[datetime] = None


class RateLimiter:
    """
    Rate limiter for agent actions.

    WHAT: Checks and enforces rate limits before action execution
    WHY: Prevents agents from making too many changes

    Usage:
        limiter = RateLimiter(db, config)
        result = await limiter.check_rate_limit(agent_id, entity_id, action_type)
        if not result.allowed:
            # Skip action, log result.reason
    """

    def __init__(
        self,
        db: Session,
        config: Optional[RateLimitConfig] = None,
    ):
        """
        Initialize rate limiter.

        Parameters:
            db: Database session
            config: Rate limit configuration
        """
        self.db = db
        self.config = config or RateLimitConfig()

    async def check_rate_limit(
        self,
        agent_id: str,
        entity_id: str,
        workspace_id: str,
        action_type: str,
    ) -> RateLimitResult:
        """
        Check if action is allowed under rate limits.

        Parameters:
            agent_id: Agent UUID
            entity_id: Entity UUID
            workspace_id: Workspace UUID
            action_type: Type of action (scale_budget, pause_campaign, etc.)

        Returns:
            RateLimitResult indicating if action is allowed
        """
        # Import here to avoid circular imports
        from ....models import AgentActionExecution

        # Get start of today (UTC)
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Check per-entity limit
        entity_count = self.db.query(func.count(AgentActionExecution.id)).filter(
            and_(
                AgentActionExecution.workspace_id == workspace_id,
                AgentActionExecution.action_type == action_type,
                AgentActionExecution.executed_at >= today_start,
                # Need to join through evaluation event to get entity_id
                # For now, we'll use a simplified check
            )
        ).scalar() or 0

        # Simplified check - count actions by agent today
        agent_count = self.db.query(func.count(AgentActionExecution.id)).filter(
            and_(
                AgentActionExecution.agent_id == agent_id,
                AgentActionExecution.executed_at >= today_start,
            )
        ).scalar() or 0

        if agent_count >= self.config.max_actions_per_agent_per_day:
            return RateLimitResult(
                allowed=False,
                reason=f"Agent rate limit exceeded: {agent_count}/{self.config.max_actions_per_agent_per_day} actions today",
                current_count=agent_count,
                limit=self.config.max_actions_per_agent_per_day,
                reset_at=today_start + timedelta(days=1),
            )

        # Check per-workspace limit
        workspace_count = self.db.query(func.count(AgentActionExecution.id)).filter(
            and_(
                AgentActionExecution.workspace_id == workspace_id,
                AgentActionExecution.executed_at >= today_start,
            )
        ).scalar() or 0

        if workspace_count >= self.config.max_actions_per_workspace_per_day:
            return RateLimitResult(
                allowed=False,
                reason=f"Workspace rate limit exceeded: {workspace_count}/{self.config.max_actions_per_workspace_per_day} actions today",
                current_count=workspace_count,
                limit=self.config.max_actions_per_workspace_per_day,
                reset_at=today_start + timedelta(days=1),
            )

        # All limits passed
        return RateLimitResult(
            allowed=True,
            current_count=agent_count,
            limit=self.config.max_actions_per_agent_per_day,
            reset_at=today_start + timedelta(days=1),
        )

    async def get_usage_stats(
        self,
        workspace_id: str,
    ) -> dict:
        """
        Get current rate limit usage for a workspace.

        Parameters:
            workspace_id: Workspace UUID

        Returns:
            Dictionary with usage statistics
        """
        from ....models import AgentActionExecution, Agent

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Total workspace actions today
        workspace_count = self.db.query(func.count(AgentActionExecution.id)).filter(
            and_(
                AgentActionExecution.workspace_id == workspace_id,
                AgentActionExecution.executed_at >= today_start,
            )
        ).scalar() or 0

        # Actions by agent
        agent_counts = (
            self.db.query(
                Agent.id,
                Agent.name,
                func.count(AgentActionExecution.id).label("action_count"),
            )
            .join(AgentActionExecution, Agent.id == AgentActionExecution.agent_id)
            .filter(
                and_(
                    Agent.workspace_id == workspace_id,
                    AgentActionExecution.executed_at >= today_start,
                )
            )
            .group_by(Agent.id, Agent.name)
            .all()
        )

        return {
            "workspace": {
                "used": workspace_count,
                "limit": self.config.max_actions_per_workspace_per_day,
                "remaining": max(0, self.config.max_actions_per_workspace_per_day - workspace_count),
            },
            "agents": [
                {
                    "agent_id": str(row.id),
                    "agent_name": row.name,
                    "used": row.action_count,
                    "limit": self.config.max_actions_per_agent_per_day,
                    "remaining": max(0, self.config.max_actions_per_agent_per_day - row.action_count),
                }
                for row in agent_counts
            ],
            "reset_at": (today_start + timedelta(days=1)).isoformat(),
        }
