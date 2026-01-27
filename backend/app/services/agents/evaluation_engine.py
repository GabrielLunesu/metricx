"""
Agent Evaluation Engine.

WHAT:
    Core evaluation logic that processes all agents every 15 minutes.
    Evaluates conditions, manages state, executes actions, and logs events.

WHY:
    This is the heart of the agent system:
    - Fetches current metrics for entities
    - Evaluates conditions against metrics
    - Tracks accumulation state
    - Executes actions when triggered
    - Logs everything for observability

DESIGN:
    - Event sourced: Every evaluation produces an immutable event
    - Batch processing: Evaluates all active agents in one cycle
    - Parallel entity evaluation: Multiple entities per agent
    - Full observability: Complete audit trail

REFERENCES:
    - Agent System Implementation Plan (Phase 2: Core Engine)
    - backend/app/models.py (Agent, AgentEvaluationEvent)
    - backend/app/services/agents/conditions.py
    - backend/app/services/agents/actions.py
    - backend/app/services/agents/state_machine.py
"""

import asyncio
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import logging

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from sqlalchemy import func

from ...models import (
    Agent,
    AgentEntityState,
    AgentEvaluationEvent,
    AgentActionExecution,
    Entity,
    Connection,
    MetricSnapshot,
    AgentStatusEnum,
    AgentStateEnum,
    AgentResultTypeEnum,
    ActionTypeEnum,
    ProviderEnum,
)
from .conditions import Condition, EvalContext, ConditionResult, condition_from_dict
from .actions import Action, ActionContext, ActionResult, action_from_dict
from .state_machine import AgentStateMachine, StateTransitionResult, AccumulationState

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """
    Result of evaluating one agent against one entity.

    WHAT: Complete record of what happened during evaluation
    WHY: Stored as AgentEvaluationEvent for observability
    """

    agent_id: str
    entity_id: str
    workspace_id: str
    evaluated_at: datetime
    duration_ms: int

    # Result classification
    result_type: AgentResultTypeEnum
    headline: str

    # Observations
    observations: Dict[str, float]
    entity_snapshot: Dict[str, Any]

    # Condition evaluation
    condition_definition: Dict[str, Any]
    condition_inputs: Dict[str, Any]
    condition_result: bool
    condition_explanation: str

    # Accumulation
    accumulation_before: Dict[str, Any]
    accumulation_after: Dict[str, Any]
    accumulation_explanation: str

    # State transition
    state_before: str
    state_after: str
    state_transition_reason: str

    # Trigger decision
    should_trigger: bool
    trigger_explanation: str

    # Summary
    summary: str

    # Actions executed
    action_results: List[ActionResult] = None

    # Error (if any)
    error: Optional[str] = None


class AgentEvaluationEngine:
    """
    Core evaluation engine for the agent system.

    WHAT: Orchestrates agent evaluation across all entities
    WHY: Centralized logic for batch processing and observability

    Usage:
        engine = AgentEvaluationEngine(db)
        await engine.evaluate_all_agents()
    """

    def __init__(
        self,
        db: Session,
        notification_service: Optional[Any] = None,
        metric_fetcher: Optional[Any] = None,
    ):
        """
        Initialize evaluation engine.

        Parameters:
            db: Database session
            notification_service: Service for sending notifications
            metric_fetcher: Service for fetching current metrics
        """
        self.db = db
        self.notification_service = notification_service
        self.metric_fetcher = metric_fetcher

    async def evaluate_all_agents(self) -> Dict[str, Any]:
        """
        Evaluate all active agents.

        Called every 15 minutes by ARQ scheduler.

        Returns:
            Summary of evaluation cycle
        """
        start_time = time.time()
        logger.info("Starting agent evaluation cycle")

        # Get all active agents
        agents = self.db.query(Agent).filter(
            Agent.status == AgentStatusEnum.active
        ).all()

        logger.info(f"Found {len(agents)} active agents to evaluate")

        results = {
            "agents_evaluated": 0,
            "entities_evaluated": 0,
            "triggers": 0,
            "errors": 0,
            "duration_ms": 0,
        }

        for agent in agents:
            try:
                agent_result = await self.evaluate_agent(agent)
                results["agents_evaluated"] += 1
                results["entities_evaluated"] += agent_result.get("entities_evaluated", 0)
                results["triggers"] += agent_result.get("triggers", 0)
                results["errors"] += agent_result.get("errors", 0)
            except Exception as e:
                logger.exception(f"Failed to evaluate agent {agent.id}: {e}")
                results["errors"] += 1
                # Mark agent as errored
                await self._mark_agent_error(agent, str(e))

        results["duration_ms"] = int((time.time() - start_time) * 1000)
        logger.info(f"Agent evaluation cycle complete: {results}")

        return results

    async def evaluate_agent(self, agent: Agent) -> Dict[str, Any]:
        """
        Evaluate a single agent across all scoped entities.

        Supports two modes:
        - Individual (default): Evaluate each entity separately
        - Aggregate: Sum metrics across all entities, evaluate ONCE

        Parameters:
            agent: Agent to evaluate

        Returns:
            Summary of agent evaluation
        """
        logger.debug(f"Evaluating agent {agent.id}: {agent.name}")

        # Get entities in scope
        entities = self._get_scoped_entities(agent)
        logger.debug(f"Agent {agent.id} has {len(entities)} entities in scope")

        results = {
            "entities_evaluated": 0,
            "triggers": 0,
            "errors": 0,
        }

        # Check if this is an AGGREGATE agent (evaluate totals, not individuals)
        scope_config = agent.scope_config or {}
        is_aggregate = scope_config.get("aggregate", False)

        if is_aggregate and entities:
            # AGGREGATE MODE: Sum metrics across all entities, evaluate ONCE
            try:
                eval_result = await self.evaluate_agent_aggregate(agent, entities)
                results["entities_evaluated"] = 1  # One aggregate evaluation
                if eval_result.should_trigger:
                    results["triggers"] += 1
                if eval_result.error:
                    results["errors"] += 1
            except Exception as e:
                logger.exception(f"Failed aggregate evaluation for agent {agent.id}: {e}")
                results["errors"] += 1
        else:
            # INDIVIDUAL MODE: Evaluate each entity separately
            for entity in entities:
                try:
                    eval_result = await self.evaluate_agent_entity(agent, entity)
                    results["entities_evaluated"] += 1

                    if eval_result.should_trigger:
                        results["triggers"] += 1

                    if eval_result.error:
                        results["errors"] += 1

                except Exception as e:
                    logger.exception(f"Failed to evaluate agent {agent.id} for entity {entity.id}: {e}")
                    results["errors"] += 1

        # Update agent stats
        agent.last_evaluated_at = datetime.now(timezone.utc)
        agent.total_evaluations += results["entities_evaluated"]
        agent.total_triggers += results["triggers"]
        self.db.commit()

        return results

    async def evaluate_agent_aggregate(
        self, agent: Agent, entities: List[Entity]
    ) -> EvaluationResult:
        """
        Evaluate agent against AGGREGATED metrics across all entities.

        WHAT:
            Instead of evaluating each campaign individually, aggregate metrics
            (sum spend, sum revenue, etc.) and evaluate ONCE.

        WHY:
            Users want to monitor TOTAL account spend/revenue, not per-campaign.
            "Alert when total Google spend > $100" = ONE evaluation, ONE notification.

        Parameters:
            agent: Agent to evaluate
            entities: List of entities to aggregate

        Returns:
            Single EvaluationResult for the aggregate
        """
        start_time = time.time()
        evaluated_at = datetime.now(timezone.utc)

        # Build aggregate entity name for display
        scope_config = agent.scope_config or {}
        provider = scope_config.get("provider", "all").title()
        aggregate_name = f"{provider} Account Total ({len(entities)} campaigns)"

        # Initialize result
        result = EvaluationResult(
            agent_id=str(agent.id),
            entity_id="aggregate",  # Virtual entity ID
            workspace_id=str(agent.workspace_id),
            evaluated_at=evaluated_at,
            duration_ms=0,
            result_type=AgentResultTypeEnum.condition_not_met,
            headline="",
            observations={},
            entity_snapshot={
                "name": aggregate_name,
                "status": "active",
                "provider": provider.lower(),
                "level": "account",
                "entity_count": len(entities),
            },
            condition_definition=agent.condition,
            condition_inputs={},
            condition_result=False,
            condition_explanation="",
            accumulation_before={},
            accumulation_after={},
            accumulation_explanation="",
            state_before="watching",
            state_after="watching",
            state_transition_reason="",
            should_trigger=False,
            trigger_explanation="",
            summary="",
        )

        try:
            # 1. Aggregate metrics across all entities
            aggregated_observations = await self._aggregate_observations(entities)
            result.observations = aggregated_observations

            logger.info(
                f"Aggregated metrics for agent {agent.id}: "
                f"spend=${aggregated_observations.get('spend', 0):.2f}, "
                f"revenue=${aggregated_observations.get('revenue', 0):.2f}"
            )

            # 2. Evaluate condition against aggregated metrics
            condition = condition_from_dict(agent.condition)
            eval_context = EvalContext(
                observations=aggregated_observations,
                entity_id="aggregate",
                entity_name=aggregate_name,
                evaluated_at=evaluated_at,
            )
            condition_result = condition.evaluate(eval_context)
            result.condition_result = condition_result.met
            result.condition_inputs = condition_result.inputs
            result.condition_explanation = condition_result.explanation

            # 3. For aggregate mode, trigger immediately if condition met (no accumulation)
            # This simplifies the logic - aggregate agents trigger on first match
            if condition_result.met:
                result.result_type = AgentResultTypeEnum.triggered
                result.should_trigger = True
                result.headline = f"Triggered: {condition_result.explanation}"
                result.trigger_explanation = "Aggregate condition met"
                result.state_after = "triggered"

                # 4. Execute actions
                result.action_results = await self._execute_aggregate_actions(
                    agent, aggregate_name, provider.lower(), result
                )
            else:
                result.result_type = AgentResultTypeEnum.condition_not_met
                result.headline = f"Condition not met: {condition_result.explanation}"
                result.trigger_explanation = "Aggregate condition not met"

            # 5. Generate summary
            result.summary = (
                f"Agent '{agent.name}' evaluated {aggregate_name}: "
                f"{condition_result.explanation}"
            )

        except Exception as e:
            logger.exception(f"Aggregate evaluation error for agent {agent.id}")
            result.result_type = AgentResultTypeEnum.error
            result.error = str(e)
            result.headline = f"Error: {str(e)[:100]}"
            result.summary = f"Aggregate evaluation failed: {str(e)}"

        # Calculate duration
        result.duration_ms = int((time.time() - start_time) * 1000)

        # Store evaluation event (with aggregate entity_id)
        await self._store_aggregate_evaluation_event(agent, result, aggregate_name, provider.lower())

        return result

    async def _aggregate_observations(self, entities: List[Entity]) -> Dict[str, float]:
        """
        Aggregate metrics across multiple entities.

        Sums: spend, revenue, clicks, impressions, conversions
        Calculates: ROAS, CPC, CTR from aggregated values
        """
        from datetime import timedelta

        totals = {
            "spend": 0.0,
            "revenue": 0.0,
            "clicks": 0,
            "impressions": 0,
            "conversions": 0.0,
        }

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        for entity in entities:
            result = self.db.execute(
                select(
                    func.sum(MetricSnapshot.spend).label("spend"),
                    func.sum(MetricSnapshot.revenue).label("revenue"),
                    func.sum(MetricSnapshot.clicks).label("clicks"),
                    func.sum(MetricSnapshot.impressions).label("impressions"),
                    func.sum(MetricSnapshot.conversions).label("conversions"),
                )
                .where(
                    and_(
                        MetricSnapshot.entity_id == entity.id,
                        MetricSnapshot.captured_at >= cutoff,
                    )
                )
            ).first()

            if result and result.spend is not None:
                totals["spend"] += float(result.spend or 0)
                totals["revenue"] += float(result.revenue or 0)
                totals["clicks"] += int(result.clicks or 0)
                totals["impressions"] += int(result.impressions or 0)
                totals["conversions"] += float(result.conversions or 0)

        # Calculate derived metrics
        spend = totals["spend"]
        revenue = totals["revenue"]
        clicks = totals["clicks"]
        impressions = totals["impressions"]

        return {
            "spend": round(spend, 2),
            "revenue": round(revenue, 2),
            "roas": round(revenue / spend, 2) if spend > 0 else 0.0,
            "clicks": clicks,
            "impressions": impressions,
            "conversions": round(totals["conversions"], 2),
            "cpc": round(spend / clicks, 2) if clicks > 0 else 0.0,
            "ctr": round((clicks / impressions * 100), 2) if impressions > 0 else 0.0,
        }

    async def _execute_aggregate_actions(
        self, agent: Agent, aggregate_name: str, provider: str, result: EvaluationResult
    ) -> List[ActionResult]:
        """Execute actions for an aggregate trigger."""
        from .action_executor import PlatformActionExecutor
        from .actions import ActionContext, action_from_dict

        # Get user email
        user_email = None
        from ...models import User

        if agent.created_by:
            user = self.db.query(User).filter(User.id == agent.created_by).first()
            if user and user.email:
                user_email = user.email

        if not user_email:
            workspace_user = self.db.query(User).filter(
                User.workspace_id == agent.workspace_id
            ).first()
            if workspace_user and workspace_user.email:
                user_email = workspace_user.email

        action_results = []
        for action_config in agent.actions:
            try:
                action = action_from_dict(action_config)

                # Build context for aggregate (no specific entity)
                context = ActionContext(
                    agent_id=str(agent.id),
                    agent_name=agent.name,
                    entity_id="aggregate",
                    entity_name=aggregate_name,
                    entity_provider=provider,
                    workspace_id=str(agent.workspace_id),
                    observations=result.observations,
                    evaluation_event_id="",
                    user_email=user_email,
                )

                action_result = await action.execute(context)
                action_results.append(action_result)

                logger.info(
                    f"Aggregate action {action_config.get('type')}: "
                    f"success={action_result.success}, desc={action_result.description}"
                )

            except Exception as e:
                logger.exception(f"Aggregate action failed: {e}")
                action_results.append(ActionResult(
                    success=False,
                    description="Action failed",
                    error=str(e),
                ))

        return action_results

    async def _store_aggregate_evaluation_event(
        self, agent: Agent, result: EvaluationResult, aggregate_name: str, provider: str
    ) -> AgentEvaluationEvent:
        """Store evaluation event for aggregate evaluation."""
        event = AgentEvaluationEvent(
            id=uuid.uuid4(),
            agent_id=agent.id,
            entity_id=None,  # No specific entity for aggregate
            workspace_id=agent.workspace_id,
            evaluated_at=result.evaluated_at,
            result_type=result.result_type,
            headline=result.headline,
            observations=result.observations,
            entity_snapshot=result.entity_snapshot,
            condition_definition=result.condition_definition,
            condition_inputs=result.condition_inputs,
            condition_result=result.condition_result,
            condition_explanation=result.condition_explanation,
            accumulation_before=result.accumulation_before,
            accumulation_after=result.accumulation_after,
            accumulation_explanation=result.accumulation_explanation,
            state_before=result.state_before,
            state_after=result.state_after,
            state_transition_reason=result.state_transition_reason,
            should_trigger=result.should_trigger,
            trigger_explanation=result.trigger_explanation,
            summary=result.summary,
            evaluation_duration_ms=result.duration_ms,
            entity_name=aggregate_name,
            entity_provider=provider,
        )

        self.db.add(event)
        self.db.flush()

        # Store action executions
        if result.action_results:
            for i, action_result in enumerate(result.action_results):
                action_config = agent.actions[i] if i < len(agent.actions) else {}
                action_type_str = action_config.get("type", "unknown")

                try:
                    action_type = ActionTypeEnum(action_type_str)
                except ValueError:
                    action_type = ActionTypeEnum.email

                execution = AgentActionExecution(
                    id=uuid.uuid4(),
                    evaluation_event_id=event.id,
                    agent_id=agent.id,
                    workspace_id=agent.workspace_id,
                    action_type=action_type,
                    action_config=action_config,
                    executed_at=result.evaluated_at,
                    success=action_result.success,
                    description=action_result.description,
                    details=action_result.details,
                    error=action_result.error,
                    duration_ms=action_result.duration_ms,
                    state_before=action_result.state_before,
                    state_after=action_result.state_after,
                    state_verified=False,
                    rollback_possible=action_result.rollback_possible,
                )
                self.db.add(execution)

        self.db.commit()
        return event

    async def evaluate_agent_entity(
        self, agent: Agent, entity: Entity
    ) -> EvaluationResult:
        """
        Evaluate a single agent against a single entity.

        This is the core evaluation logic:
        1. Get or create entity state
        2. Fetch current metrics
        3. Evaluate condition
        4. Update state machine
        5. Determine if should trigger
        6. Execute actions if triggered
        7. Store evaluation event

        Parameters:
            agent: Agent to evaluate
            entity: Entity to evaluate against

        Returns:
            EvaluationResult with full details
        """
        start_time = time.time()
        evaluated_at = datetime.now(timezone.utc)

        # Initialize result
        result = EvaluationResult(
            agent_id=str(agent.id),
            entity_id=str(entity.id),
            workspace_id=str(agent.workspace_id),
            evaluated_at=evaluated_at,
            duration_ms=0,
            result_type=AgentResultTypeEnum.condition_not_met,
            headline="",
            observations={},
            entity_snapshot={},
            condition_definition=agent.condition,
            condition_inputs={},
            condition_result=False,
            condition_explanation="",
            accumulation_before={},
            accumulation_after={},
            accumulation_explanation="",
            state_before="",
            state_after="",
            state_transition_reason="",
            should_trigger=False,
            trigger_explanation="",
            summary="",
        )

        try:
            # 1. Get or create entity state
            entity_state = self._get_or_create_entity_state(agent, entity)
            result.state_before = entity_state.state.value

            # 2. Capture entity snapshot
            result.entity_snapshot = {
                "name": entity.name,
                "status": entity.status,
                "provider": entity.connection.provider.value if entity.connection else "unknown",
                "level": entity.level.value,
            }

            # 3. Fetch current metrics
            observations = await self._fetch_observations(entity)
            result.observations = observations

            # 4. Evaluate condition
            condition = condition_from_dict(agent.condition)
            eval_context = EvalContext(
                observations=observations,
                entity_id=str(entity.id),
                entity_name=entity.name,
                evaluated_at=evaluated_at,
            )
            condition_result = condition.evaluate(eval_context)
            result.condition_result = condition_result.met
            result.condition_inputs = condition_result.inputs
            result.condition_explanation = condition_result.explanation

            # 5. Build accumulation state
            accumulation_state = AccumulationState(
                count=entity_state.accumulation_count or 0,
                required=agent.accumulation_required,
                started_at=entity_state.accumulation_started_at,
                history=[
                    datetime.fromisoformat(h) if isinstance(h, str) else h
                    for h in (entity_state.accumulation_history or [])
                ],
            )
            result.accumulation_before = {
                "count": accumulation_state.count,
                "required": accumulation_state.required,
                "started_at": accumulation_state.started_at.isoformat() if accumulation_state.started_at else None,
            }

            # 6. Process state machine
            state_machine = AgentStateMachine(
                accumulation_required=agent.accumulation_required,
                accumulation_unit=agent.accumulation_unit,
                accumulation_mode=agent.accumulation_mode,
                accumulation_window=agent.accumulation_window,
                trigger_mode=agent.trigger_mode,
                cooldown_duration_minutes=agent.cooldown_duration_minutes,
                continuous_interval_minutes=agent.continuous_interval_minutes,
            )

            transition = state_machine.process_evaluation(
                current_state=entity_state.state,
                condition_met=condition_result.met,
                accumulation_state=accumulation_state,
                evaluated_at=evaluated_at,
                last_triggered_at=entity_state.last_triggered_at,
                next_eligible_trigger_at=entity_state.next_eligible_trigger_at,
            )

            result.state_after = transition.state_after.value
            result.state_transition_reason = transition.reason
            result.accumulation_after = transition.accumulation_after
            result.accumulation_explanation = f"Count: {transition.accumulation_after.get('count', 0)}/{agent.accumulation_required}"
            result.should_trigger = transition.should_trigger
            result.trigger_explanation = transition.trigger_reason

            # 7. Determine result type
            if transition.should_trigger:
                result.result_type = AgentResultTypeEnum.triggered
                result.headline = f"Triggered: {condition_result.explanation}"
            elif transition.state_after == AgentStateEnum.cooldown:
                result.result_type = AgentResultTypeEnum.cooldown
                result.headline = f"In cooldown until {entity_state.next_eligible_trigger_at}"
            elif condition_result.met:
                result.result_type = AgentResultTypeEnum.condition_met
                result.headline = f"Condition met: {condition_result.explanation}"
            else:
                result.result_type = AgentResultTypeEnum.condition_not_met
                result.headline = f"Condition not met: {condition_result.explanation}"

            # 8. Update entity state
            entity_state.state = transition.state_after
            entity_state.accumulation_count = transition.accumulation_after.get("count", 0)
            entity_state.accumulation_started_at = (
                datetime.fromisoformat(transition.accumulation_after["started_at"])
                if transition.accumulation_after.get("started_at")
                else None
            )
            # Store history as ISO strings
            entity_state.accumulation_history = [
                h.isoformat() if isinstance(h, datetime) else h
                for h in accumulation_state.history
            ]

            if transition.should_trigger:
                entity_state.last_triggered_at = evaluated_at
                entity_state.trigger_count = (entity_state.trigger_count or 0) + 1
                entity_state.next_eligible_trigger_at = state_machine.calculate_next_eligible_trigger(
                    evaluated_at
                )
                agent.last_triggered_at = evaluated_at
                agent.total_triggers = (agent.total_triggers or 0) + 1

            # 9. Execute actions if triggered
            if transition.should_trigger:
                result.action_results = await self._execute_actions(agent, entity, result)

            # 10. Generate summary
            result.summary = self._generate_summary(agent, entity, result)

        except Exception as e:
            logger.exception(f"Evaluation error for agent {agent.id}, entity {entity.id}")
            result.result_type = AgentResultTypeEnum.error
            result.error = str(e)
            result.headline = f"Error: {str(e)[:100]}"
            result.summary = f"Evaluation failed: {str(e)}"

            # Update entity state with error
            if 'entity_state' in locals():
                entity_state.state = AgentStateEnum.error
                entity_state.consecutive_errors = (entity_state.consecutive_errors or 0) + 1
                entity_state.last_error = str(e)
                entity_state.last_error_at = evaluated_at

        # Calculate duration
        result.duration_ms = int((time.time() - start_time) * 1000)

        # 11. Store evaluation event
        event = await self._store_evaluation_event(agent, entity, result)

        # Commit all changes
        self.db.commit()

        # 12. Broadcast via WebSocket
        await self._broadcast_event(agent, entity, result, event)

        return result

    def _get_scoped_entities(self, agent: Agent) -> List[Entity]:
        """
        Get entities in the agent's scope.

        WHAT:
            Queries entities based on agent's scope configuration.
            Dynamically picks up new entities added since agent creation.

        WHY:
            Agents with scope_type="all" should monitor ALL campaigns for a provider,
            including ones created after the agent was set up.

        Parameters:
            agent: Agent with scope configuration

        Returns:
            List of entities to evaluate
        """
        scope_config = agent.scope_config or {}

        # Start with base query - join with Connection for provider filtering
        query = self.db.query(Entity).join(
            Connection, Entity.connection_id == Connection.id
        ).filter(
            Entity.workspace_id == agent.workspace_id,
            Connection.status == "active",  # Only active connections
        )

        # Filter by provider if specified (critical for "all Google campaigns")
        if scope_config.get("provider"):
            try:
                provider_enum = ProviderEnum(scope_config["provider"])
                query = query.filter(Connection.provider == provider_enum)
            except ValueError:
                logger.warning(
                    f"Unknown provider in scope_config: {scope_config['provider']}"
                )

        if agent.scope_type.value == "specific":
            # Specific entity IDs
            entity_ids = scope_config.get("entity_ids", [])
            if entity_ids:
                query = query.filter(Entity.id.in_(entity_ids))

        elif agent.scope_type.value == "filter":
            # Filter criteria
            if scope_config.get("level"):
                query = query.filter(Entity.level == scope_config["level"])
            if scope_config.get("status"):
                query = query.filter(Entity.status == scope_config["status"])
            if scope_config.get("name_contains"):
                query = query.filter(Entity.name.ilike(f"%{scope_config['name_contains']}%"))

        elif agent.scope_type.value == "all":
            # All entities at level for the specified provider
            if scope_config.get("level"):
                query = query.filter(Entity.level == scope_config["level"])

        entities = query.all()
        logger.debug(
            f"Agent {agent.id} scope query returned {len(entities)} entities "
            f"(scope_type={agent.scope_type.value}, provider={scope_config.get('provider')})"
        )
        return entities

    def _get_or_create_entity_state(
        self, agent: Agent, entity: Entity
    ) -> AgentEntityState:
        """
        Get or create entity state for agent-entity pair.

        Parameters:
            agent: Agent
            entity: Entity

        Returns:
            AgentEntityState record
        """
        state = self.db.query(AgentEntityState).filter(
            AgentEntityState.agent_id == agent.id,
            AgentEntityState.entity_id == entity.id,
        ).first()

        if not state:
            state = AgentEntityState(
                agent_id=agent.id,
                entity_id=entity.id,
                state=AgentStateEnum.watching,
                accumulation_count=0,
                accumulation_history=[],
                trigger_count=0,
            )
            self.db.add(state)
            self.db.flush()

        return state

    async def _fetch_observations(self, entity: Entity) -> Dict[str, float]:
        """
        Fetch current metrics for entity from MetricSnapshot.

        WHAT:
            Queries the latest 24h of metric snapshots for the entity
            and aggregates them to get current performance.

        WHY:
            Real-time agent evaluation needs actual metrics from ad platforms.
            MetricSnapshot is synced every 15 minutes, providing near real-time data.

        Parameters:
            entity: Entity to get metrics for

        Returns:
            Dictionary of metric values including derived metrics (ROAS, CPC, CTR)

        REFERENCES:
            - backend/app/models.py (MetricSnapshot)
            - backend/app/services/snapshot_sync_service.py
        """
        from datetime import timedelta

        # Default values if no data available
        default_observations = {
            "spend": 0.0,
            "revenue": 0.0,
            "roas": 0.0,
            "clicks": 0,
            "impressions": 0,
            "conversions": 0.0,
            "cpc": 0.0,
            "ctr": 0.0,
        }

        try:
            # Query last 24 hours of metric snapshots for this entity
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

            result = self.db.execute(
                select(
                    func.sum(MetricSnapshot.spend).label("spend"),
                    func.sum(MetricSnapshot.revenue).label("revenue"),
                    func.sum(MetricSnapshot.clicks).label("clicks"),
                    func.sum(MetricSnapshot.impressions).label("impressions"),
                    func.sum(MetricSnapshot.conversions).label("conversions"),
                )
                .where(
                    and_(
                        MetricSnapshot.entity_id == entity.id,
                        MetricSnapshot.captured_at >= cutoff,
                    )
                )
            ).first()

            if not result or result.spend is None:
                logger.debug(f"No metrics found for entity {entity.id} in last 24h")
                return default_observations

            # Extract base metrics (handle None values)
            spend = float(result.spend or 0)
            revenue = float(result.revenue or 0)
            clicks = int(result.clicks or 0)
            impressions = int(result.impressions or 0)
            conversions = float(result.conversions or 0)

            # Calculate derived metrics
            roas = revenue / spend if spend > 0 else 0.0
            cpc = spend / clicks if clicks > 0 else 0.0
            ctr = (clicks / impressions * 100) if impressions > 0 else 0.0

            observations = {
                "spend": round(spend, 2),
                "revenue": round(revenue, 2),
                "roas": round(roas, 2),
                "clicks": clicks,
                "impressions": impressions,
                "conversions": round(conversions, 2),
                "cpc": round(cpc, 2),
                "ctr": round(ctr, 2),
            }

            logger.debug(
                f"Fetched observations for entity {entity.id}: "
                f"spend=${spend:.2f}, revenue=${revenue:.2f}, roas={roas:.2f}"
            )

            return observations

        except Exception as e:
            logger.warning(f"Failed to fetch observations for entity {entity.id}: {e}")
            return default_observations

    async def _execute_actions(
        self, agent: Agent, entity: Entity, result: EvaluationResult
    ) -> List[ActionResult]:
        """
        Execute all actions for triggered agent using PlatformActionExecutor.

        WHAT:
            Routes actions through PlatformActionExecutor for real API calls.
            Platform actions (scale_budget, pause_campaign) go through Meta/Google APIs.
            Simple actions (email, webhook) execute directly.

        WHY:
            PlatformActionExecutor provides:
            - Health checks before action
            - Live state verification (before AND after)
            - Real platform API calls
            - Rollback capability
            - Full audit trail

        Parameters:
            agent: Agent that triggered
            entity: Entity that triggered on
            result: Evaluation result for context

        Returns:
            List of action results

        REFERENCES:
            - backend/app/services/agents/action_executor.py
            - backend/app/services/agents/platform_actions_meta.py
            - backend/app/services/agents/platform_actions_google.py
        """
        from .action_executor import execute_agent_actions

        # Get user email for notifications
        # Priority: 1) Agent creator, 2) Workspace owner, 3) Any workspace member
        user_email = None
        from ...models import User

        # Try agent creator first
        if agent.created_by:
            user = self.db.query(User).filter(User.id == agent.created_by).first()
            if user and user.email:
                user_email = user.email
                logger.debug(f"Using agent creator email: {user_email}")

        # Fall back to workspace owner/member
        if not user_email:
            workspace_user = self.db.query(User).filter(
                User.workspace_id == agent.workspace_id
            ).first()
            if workspace_user and workspace_user.email:
                user_email = workspace_user.email
                logger.debug(f"Using workspace user email: {user_email}")

        # Execute all actions through the platform-aware executor
        action_results = await execute_agent_actions(
            db=self.db,
            agent_id=agent.id,
            agent_name=agent.name,
            workspace_id=agent.workspace_id,
            entity=entity,
            action_configs=agent.actions,
            observations=result.observations,
            evaluation_event_id=None,  # Will be set after event is stored
            user_email=user_email,
        )

        # Log results
        for i, action_result in enumerate(action_results):
            action_type = agent.actions[i].get("type", "unknown") if i < len(agent.actions) else "unknown"
            logger.info(
                f"Action {action_type} for agent {agent.id} on entity {entity.id}: "
                f"success={action_result.success}, desc={action_result.description}"
            )
            if action_result.state_before and action_result.state_after:
                logger.info(
                    f"  State change: {action_result.state_before} → {action_result.state_after}"
                )

        return action_results

    async def _store_evaluation_event(
        self, agent: Agent, entity: Entity, result: EvaluationResult
    ) -> AgentEvaluationEvent:
        """
        Store evaluation event in database.

        Parameters:
            agent: Agent that was evaluated
            entity: Entity that was evaluated
            result: Evaluation result

        Returns:
            Created AgentEvaluationEvent
        """
        event = AgentEvaluationEvent(
            id=uuid.uuid4(),
            agent_id=agent.id,
            entity_id=entity.id,
            workspace_id=agent.workspace_id,
            evaluated_at=result.evaluated_at,
            result_type=result.result_type,
            headline=result.headline,
            observations=result.observations,
            entity_snapshot=result.entity_snapshot,
            condition_definition=result.condition_definition,
            condition_inputs=result.condition_inputs,
            condition_result=result.condition_result,
            condition_explanation=result.condition_explanation,
            accumulation_before=result.accumulation_before,
            accumulation_after=result.accumulation_after,
            accumulation_explanation=result.accumulation_explanation,
            state_before=result.state_before,
            state_after=result.state_after,
            state_transition_reason=result.state_transition_reason,
            should_trigger=result.should_trigger,
            trigger_explanation=result.trigger_explanation,
            summary=result.summary,
            evaluation_duration_ms=result.duration_ms,
            entity_name=entity.name,
            entity_provider=entity.connection.provider.value if entity.connection else "unknown",
        )

        self.db.add(event)
        self.db.flush()

        # Store action executions
        if result.action_results:
            for i, action_result in enumerate(result.action_results):
                action_config = agent.actions[i] if i < len(agent.actions) else {}
                action_type_str = action_config.get("type", "unknown")

                # Map string to enum
                try:
                    action_type = ActionTypeEnum(action_type_str)
                except ValueError:
                    action_type = ActionTypeEnum.email  # Default

                execution = AgentActionExecution(
                    id=uuid.uuid4(),
                    evaluation_event_id=event.id,
                    agent_id=agent.id,
                    workspace_id=agent.workspace_id,
                    action_type=action_type,
                    action_config=action_config,
                    executed_at=result.evaluated_at,
                    success=action_result.success,
                    description=action_result.description,
                    details=action_result.details,
                    error=action_result.error,
                    duration_ms=action_result.duration_ms,
                    state_before=action_result.state_before,
                    state_after=action_result.state_after,
                    state_verified=False,
                    rollback_possible=action_result.rollback_possible,
                )
                self.db.add(execution)

        return event

    def _generate_summary(
        self, agent: Agent, entity: Entity, result: EvaluationResult
    ) -> str:
        """
        Generate human-readable summary for Copilot.

        Parameters:
            agent: Agent
            entity: Entity
            result: Evaluation result

        Returns:
            Summary string
        """
        if result.result_type == AgentResultTypeEnum.triggered:
            return (
                f"Agent '{agent.name}' triggered on {entity.name}. "
                f"{result.condition_explanation}. "
                f"Actions executed: {len(result.action_results or [])}."
            )
        elif result.result_type == AgentResultTypeEnum.condition_met:
            return (
                f"Agent '{agent.name}' condition met on {entity.name}: "
                f"{result.condition_explanation}. "
                f"Accumulating: {result.accumulation_explanation}."
            )
        elif result.result_type == AgentResultTypeEnum.cooldown:
            return (
                f"Agent '{agent.name}' in cooldown for {entity.name}. "
                f"{result.state_transition_reason}."
            )
        elif result.result_type == AgentResultTypeEnum.error:
            return f"Agent '{agent.name}' evaluation error on {entity.name}: {result.error}"
        else:
            return (
                f"Agent '{agent.name}' evaluated {entity.name}: "
                f"condition not met. {result.condition_explanation}"
            )

    async def _mark_agent_error(self, agent: Agent, error: str) -> None:
        """
        Mark agent as errored.

        Parameters:
            agent: Agent to mark
            error: Error message
        """
        old_status = agent.status.value
        agent.status = AgentStatusEnum.error
        agent.error_message = error[:1000]  # Truncate long errors
        self.db.commit()

        # Broadcast status change via WebSocket
        try:
            from .websocket_manager import agent_ws_manager
            await agent_ws_manager.broadcast_status_change(
                workspace_id=agent.workspace_id,
                agent_id=agent.id,
                old_status=old_status,
                new_status="error",
                reason=error[:200],
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast status change: {e}")

        # Send error notification
        if self.notification_service:
            try:
                await self.notification_service.send_error_notification(agent, error)
            except Exception as e:
                logger.warning(f"Failed to send error notification: {e}")

        logger.error(f"Agent {agent.id} marked as error: {error}")

    async def _broadcast_event(
        self,
        agent: Agent,
        entity: Entity,
        result: EvaluationResult,
        event: AgentEvaluationEvent,
    ) -> None:
        """
        Broadcast evaluation event via WebSocket.

        Parameters:
            agent: Agent that was evaluated
            entity: Entity that was evaluated
            result: Evaluation result
            event: Stored evaluation event

        WHAT: Send real-time update to connected clients
        WHY: UI shows live evaluation results without polling
        """
        try:
            from .websocket_manager import agent_ws_manager

            # Build event data for WebSocket
            event_data = {
                "id": str(event.id),
                "agent_id": str(event.agent_id),
                "entity_id": str(event.entity_id),
                "evaluated_at": event.evaluated_at.isoformat(),
                "result_type": event.result_type.value,
                "headline": event.headline,
                "entity_name": event.entity_name,
                "entity_provider": event.entity_provider,
                "condition_result": event.condition_result,
                "condition_explanation": event.condition_explanation,
                "should_trigger": event.should_trigger,
                "summary": event.summary,
            }

            await agent_ws_manager.broadcast_evaluation_event(
                workspace_id=agent.workspace_id,
                agent_id=agent.id,
                event_data=event_data,
            )

            # If triggered, also send a dedicated trigger event
            if result.should_trigger:
                actions_executed = []
                if result.action_results:
                    for i, action_result in enumerate(result.action_results):
                        action_config = agent.actions[i] if i < len(agent.actions) else {}
                        actions_executed.append({
                            "type": action_config.get("type", "unknown"),
                            "success": action_result.success,
                            "description": action_result.description,
                        })

                await agent_ws_manager.broadcast_trigger(
                    workspace_id=agent.workspace_id,
                    agent_id=agent.id,
                    entity_id=entity.id,
                    entity_name=entity.name,
                    actions_executed=actions_executed,
                )

        except Exception as e:
            # Don't let WebSocket failures break evaluation
            logger.warning(f"Failed to broadcast WebSocket event: {e}")
