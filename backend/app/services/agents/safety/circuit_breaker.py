"""
Circuit Breaker for Agent Safety.

WHAT:
    Monitors agent behavior and pauses agents when things go wrong.
    Detects performance degradation, consecutive failures, and budget runaway.

WHY:
    Agents operate autonomously - circuit breakers are the safety net:
    - Pause if ROAS drops significantly after scaling
    - Pause after consecutive evaluation failures
    - Pause if total budget increase exceeds threshold

DESIGN:
    - Checks run after each action execution
    - Configurable thresholds per agent
    - Automatic pause with notification to user
    - Manual resume required after circuit trips

REFERENCES:
    - Agent System Implementation Plan (Safety Mechanism 4: Circuit Breakers)
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List
import logging

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerConfig:
    """
    Circuit breaker configuration.

    Attributes:
        pause_if_roas_drops_percent: Pause if ROAS drops more than this %
        performance_check_window_hours: Window for performance check
        pause_after_consecutive_failures: Pause after N failures
        pause_if_total_budget_increase_exceeds: Pause if total $ increase exceeds
        budget_tracking_window_days: Window for budget tracking
        enabled: Whether circuit breaker is active
    """

    pause_if_roas_drops_percent: float = 40.0
    performance_check_window_hours: int = 24
    pause_after_consecutive_failures: int = 5
    pause_if_total_budget_increase_exceeds: Optional[float] = None
    budget_tracking_window_days: int = 7
    enabled: bool = True


@dataclass
class CircuitBreakerResult:
    """
    Result of circuit breaker check.

    Attributes:
        tripped: Whether circuit breaker tripped
        reason: Why it tripped (if tripped)
        action: What action was taken (pause, notify, etc.)
        details: Additional details
    """

    tripped: bool
    reason: Optional[str] = None
    action: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class CircuitBreaker:
    """
    Circuit breaker for agent safety.

    WHAT: Monitors agent behavior and trips when thresholds exceeded
    WHY: Prevents agents from causing significant damage

    Usage:
        breaker = CircuitBreaker(db, config)
        result = await breaker.check_after_action(agent, entity, action_result)
        if result.tripped:
            # Agent has been paused, send notification
    """

    def __init__(
        self,
        db: Session,
        config: Optional[CircuitBreakerConfig] = None,
        notification_service: Optional[Any] = None,
    ):
        """
        Initialize circuit breaker.

        Parameters:
            db: Database session
            config: Circuit breaker configuration
            notification_service: Service for sending notifications
        """
        self.db = db
        self.config = config or CircuitBreakerConfig()
        self.notification_service = notification_service

    async def check_after_action(
        self,
        agent_id: str,
        entity_id: str,
        workspace_id: str,
        action_type: str,
        action_result: Dict[str, Any],
    ) -> CircuitBreakerResult:
        """
        Check circuit breakers after action execution.

        Parameters:
            agent_id: Agent UUID
            entity_id: Entity UUID
            workspace_id: Workspace UUID
            action_type: Type of action executed
            action_result: Result from action execution

        Returns:
            CircuitBreakerResult indicating if breaker tripped
        """
        if not self.config.enabled:
            return CircuitBreakerResult(tripped=False)

        # Check consecutive failures
        failure_result = await self._check_consecutive_failures(agent_id)
        if failure_result.tripped:
            return failure_result

        # Check performance degradation (for budget scaling actions)
        if action_type == "scale_budget":
            perf_result = await self._check_performance_degradation(
                agent_id, entity_id, action_result
            )
            if perf_result.tripped:
                return perf_result

            # Check budget runaway
            budget_result = await self._check_budget_runaway(agent_id, workspace_id)
            if budget_result.tripped:
                return budget_result

        return CircuitBreakerResult(tripped=False)

    async def _check_consecutive_failures(
        self,
        agent_id: str,
    ) -> CircuitBreakerResult:
        """
        Check for consecutive evaluation failures.

        Parameters:
            agent_id: Agent UUID

        Returns:
            CircuitBreakerResult
        """
        from ....models import AgentEntityState

        # Get all entity states for this agent
        states = self.db.query(AgentEntityState).filter(
            AgentEntityState.agent_id == agent_id
        ).all()

        # Count entities with consecutive errors
        high_error_count = sum(
            1 for s in states
            if (s.consecutive_errors or 0) >= self.config.pause_after_consecutive_failures
        )

        if high_error_count > 0:
            # Pause the agent
            await self._pause_agent(
                agent_id,
                f"Circuit breaker: {high_error_count} entities with {self.config.pause_after_consecutive_failures}+ consecutive failures"
            )

            return CircuitBreakerResult(
                tripped=True,
                reason=f"{high_error_count} entities exceeded consecutive failure limit",
                action="agent_paused",
                details={
                    "entities_affected": high_error_count,
                    "failure_threshold": self.config.pause_after_consecutive_failures,
                },
            )

        return CircuitBreakerResult(tripped=False)

    async def _check_performance_degradation(
        self,
        agent_id: str,
        entity_id: str,
        action_result: Dict[str, Any],
    ) -> CircuitBreakerResult:
        """
        Check if performance degraded significantly after scaling action.

        Parameters:
            agent_id: Agent UUID
            entity_id: Entity UUID
            action_result: Result from scale action

        Returns:
            CircuitBreakerResult
        """
        # This would need to fetch metrics from before and after the action
        # For now, return not tripped (would need metric_service integration)

        # TODO: Implement actual performance check
        # 1. Get metrics from before action (from action_result.state_before)
        # 2. Get current metrics
        # 3. Compare ROAS change
        # 4. If dropped more than threshold, trip breaker

        return CircuitBreakerResult(tripped=False)

    async def _check_budget_runaway(
        self,
        agent_id: str,
        workspace_id: str,
    ) -> CircuitBreakerResult:
        """
        Check if total budget increases exceed threshold.

        Parameters:
            agent_id: Agent UUID
            workspace_id: Workspace UUID

        Returns:
            CircuitBreakerResult
        """
        if not self.config.pause_if_total_budget_increase_exceeds:
            return CircuitBreakerResult(tripped=False)

        from ....models import AgentActionExecution

        # Get budget changes in tracking window
        window_start = datetime.now(timezone.utc) - timedelta(
            days=self.config.budget_tracking_window_days
        )

        # Get scale_budget actions in window
        actions = self.db.query(AgentActionExecution).filter(
            and_(
                AgentActionExecution.agent_id == agent_id,
                AgentActionExecution.action_type == "scale_budget",
                AgentActionExecution.success == True,
                AgentActionExecution.executed_at >= window_start,
            )
        ).all()

        # Calculate total budget increase
        total_increase = 0.0
        for action in actions:
            state_before = action.state_before or {}
            state_after = action.state_after or {}
            before_budget = state_before.get("budget", 0)
            after_budget = state_after.get("budget", 0)
            if after_budget > before_budget:
                total_increase += (after_budget - before_budget)

        if total_increase > self.config.pause_if_total_budget_increase_exceeds:
            # Pause the agent
            await self._pause_agent(
                agent_id,
                f"Circuit breaker: Total budget increase ${total_increase:.2f} exceeds limit ${self.config.pause_if_total_budget_increase_exceeds:.2f}"
            )

            return CircuitBreakerResult(
                tripped=True,
                reason=f"Total budget increase ${total_increase:.2f} exceeds ${self.config.pause_if_total_budget_increase_exceeds:.2f} limit",
                action="agent_paused",
                details={
                    "total_increase": total_increase,
                    "limit": self.config.pause_if_total_budget_increase_exceeds,
                    "window_days": self.config.budget_tracking_window_days,
                    "actions_count": len(actions),
                },
            )

        return CircuitBreakerResult(tripped=False)

    async def _pause_agent(self, agent_id: str, reason: str) -> None:
        """
        Pause an agent due to circuit breaker trip.

        Parameters:
            agent_id: Agent UUID
            reason: Why the agent was paused
        """
        from ....models import Agent, AgentStatusEnum

        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if agent:
            agent.status = AgentStatusEnum.paused
            agent.error_message = f"Circuit breaker: {reason}"
            self.db.commit()

            logger.warning(f"Circuit breaker paused agent {agent_id}: {reason}")

            # Send notification
            if self.notification_service:
                # Get workspace members for notification
                # await self.notification_service.send_circuit_breaker_notification(...)
                pass

    async def get_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get circuit breaker status for an agent.

        Parameters:
            agent_id: Agent UUID

        Returns:
            Status dictionary
        """
        from ....models import AgentEntityState, AgentActionExecution

        # Get consecutive errors
        states = self.db.query(AgentEntityState).filter(
            AgentEntityState.agent_id == agent_id
        ).all()

        max_consecutive_errors = max(
            (s.consecutive_errors or 0) for s in states
        ) if states else 0

        # Get recent budget changes
        window_start = datetime.now(timezone.utc) - timedelta(
            days=self.config.budget_tracking_window_days
        )

        budget_actions = self.db.query(AgentActionExecution).filter(
            and_(
                AgentActionExecution.agent_id == agent_id,
                AgentActionExecution.action_type == "scale_budget",
                AgentActionExecution.executed_at >= window_start,
            )
        ).all()

        total_increase = 0.0
        for action in budget_actions:
            state_before = action.state_before or {}
            state_after = action.state_after or {}
            before_budget = state_before.get("budget", 0)
            after_budget = state_after.get("budget", 0)
            if after_budget > before_budget:
                total_increase += (after_budget - before_budget)

        return {
            "enabled": self.config.enabled,
            "consecutive_failures": {
                "current": max_consecutive_errors,
                "threshold": self.config.pause_after_consecutive_failures,
                "healthy": max_consecutive_errors < self.config.pause_after_consecutive_failures,
            },
            "budget_runaway": {
                "total_increase": total_increase,
                "threshold": self.config.pause_if_total_budget_increase_exceeds,
                "window_days": self.config.budget_tracking_window_days,
                "healthy": (
                    self.config.pause_if_total_budget_increase_exceeds is None
                    or total_increase < self.config.pause_if_total_budget_increase_exceeds
                ),
            },
            "overall_healthy": (
                max_consecutive_errors < self.config.pause_after_consecutive_failures
                and (
                    self.config.pause_if_total_budget_increase_exceeds is None
                    or total_increase < self.config.pause_if_total_budget_increase_exceeds
                )
            ),
        }
