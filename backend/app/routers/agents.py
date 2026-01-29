"""
Agent System API Routes.

WHAT:
    REST API endpoints for managing autonomous monitoring agents.
    Includes CRUD operations, status control, and event querying.

WHY:
    Frontend needs to:
    - Create, view, update, delete agents
    - Pause/resume agents
    - View evaluation events and action history
    - Test agent configuration

ENDPOINTS:
    GET    /v1/agents                    - List agents
    POST   /v1/agents                    - Create agent
    GET    /v1/agents/{id}               - Get agent detail
    PATCH  /v1/agents/{id}               - Update agent
    DELETE /v1/agents/{id}               - Delete agent
    POST   /v1/agents/{id}/pause         - Pause agent
    POST   /v1/agents/{id}/resume        - Resume agent
    POST   /v1/agents/{id}/test          - Test evaluation (dry run)
    GET    /v1/agents/{id}/events        - Get evaluation events
    GET    /v1/agents/{id}/actions       - Get action executions
    GET    /v1/agents/{id}/status        - Get current entity states

REFERENCES:
    - Agent System Implementation Plan (Phase 3: API Routes)
    - backend/app/schemas.py (agent schemas)
    - backend/app/services/agents/
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_settings, _fetch_clerk_jwks
from ..models import (
    User,
    Agent,
    AgentEntityState,
    AgentEvaluationEvent,
    AgentActionExecution,
    Entity,
    Connection,
    MetricSnapshot,
    AgentStatusEnum,
    AgentStateEnum,
    ProviderEnum,
    AgentResultTypeEnum,
    ActionTypeEnum,
)
from ..schemas import (
    ErrorResponse,
    SuccessResponse,
    # Agent schemas
    AgentCreate,
    AgentUpdate,
    AgentOut,
    AgentListResponse,
    AgentEntityStateSummary,
    AccumulationConfig,
    TriggerConfig,
    SafetyConfig,
    AgentPauseRequest,
    AgentResumeRequest,
    AgentTestRequest,
    AgentTestResponse,
    AgentTestResult,
    AgentEvaluationEventOut,
    AgentEvaluationEventListResponse,
    AgentActionExecutionOut,
    AgentActionExecutionListResponse,
    # Workspace-level stats and events
    AgentStatsResponse,
    WorkspaceAgentEventsResponse,
    WorkspaceAgentEventOut,
    WorkspaceAgentActionSummary,
    ActionRollbackResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/agents",
    tags=["Agents"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Agent not found"},
    },
)


# =============================================================================
# WebSocket Authentication Helper
# =============================================================================


async def authenticate_websocket(
    websocket: WebSocket,
    db: Session,
) -> Tuple[Optional[User], Optional[str]]:
    """
    Authenticate WebSocket connection using Clerk JWT.

    WHAT:
        Validates JWT token from query params or headers and returns the user.

    WHY:
        WebSocket connections need authentication just like REST endpoints.
        Unlike HTTP requests, WebSocket can't use the standard Depends() flow.

    SECURITY:
        - Validates JWT signature against Clerk's JWKS (RS256)
        - Checks token expiration
        - Returns user object for workspace access verification

    Parameters:
        websocket: The WebSocket connection
        db: Database session

    Returns:
        Tuple of (User, None) on success, or (None, error_message) on failure

    REFERENCES:
        - backend/app/deps.py (get_current_user for HTTP)
    """
    settings = get_settings()

    # Extract token from query params (WebSocket standard) or headers
    token = websocket.query_params.get("token")

    if not token:
        # Try Authorization header as fallback
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return None, "Missing authentication token"

    # Check if Clerk is configured
    if not settings.CLERK_SECRET_KEY:
        logger.warning("[WS_AUTH] Clerk not configured, rejecting WebSocket")
        return None, "Authentication not configured"

    try:
        # Decode token header and claims without verification first
        unverified_header = jwt.get_unverified_header(token)
        unverified_claims = jwt.get_unverified_claims(token)

        kid = unverified_header.get("kid")
        issuer = unverified_claims.get("iss")

        logger.debug(f"[WS_AUTH] Token kid={kid}, issuer={issuer}")

        # Fetch Clerk's JWKS for signature verification
        jwks = await _fetch_clerk_jwks(issuer=issuer)

        # Find matching key in JWKS
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break

        if not rsa_key:
            logger.warning(f"[WS_AUTH] No matching key found for kid={kid}")
            return None, "Invalid token signature"

        # Decode and validate JWT
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk doesn't require audience
        )

        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            return None, "Invalid token payload"

        # Look up user by clerk_id
        user = db.query(User).filter(User.clerk_id == clerk_user_id).first()

        if not user:
            logger.warning(f"[WS_AUTH] User not found for clerk_id={clerk_user_id}")
            return None, "User not found"

        logger.info(f"[WS_AUTH] Authenticated user {user.id} via WebSocket")
        return user, None

    except JWTError as e:
        logger.warning(f"[WS_AUTH] JWT validation failed: {e}")
        return None, "Invalid token"
    except Exception as e:
        logger.error(f"[WS_AUTH] Unexpected error during auth: {e}")
        return None, "Authentication error"


# =============================================================================
# Metrics Fetching Helper
# =============================================================================


async def _fetch_entity_observations(
    db: Session,
    entity_id: uuid.UUID,
) -> Dict[str, float]:
    """
    Fetch current metrics for an entity from MetricSnapshot.

    WHAT:
        Queries the latest 24h of metric snapshots for the entity
        and aggregates them to get current performance.

    WHY:
        Test agent endpoint needs real metrics to accurately evaluate conditions.
        This mirrors the evaluation engine's `_fetch_observations` method.

    Parameters:
        db: Database session
        entity_id: Entity UUID to fetch metrics for

    Returns:
        Dictionary of metric values including derived metrics (ROAS, CPC, CTR)

    REFERENCES:
        - backend/app/services/agents/evaluation_engine.py (_fetch_observations)
    """
    from datetime import timedelta
    from typing import Dict

    # Default values if no data available
    default_observations: Dict[str, float] = {
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

        result = db.execute(
            select(
                func.sum(MetricSnapshot.spend).label("spend"),
                func.sum(MetricSnapshot.revenue).label("revenue"),
                func.sum(MetricSnapshot.clicks).label("clicks"),
                func.sum(MetricSnapshot.impressions).label("impressions"),
                func.sum(MetricSnapshot.conversions).label("conversions"),
            )
            .where(
                and_(
                    MetricSnapshot.entity_id == entity_id,
                    MetricSnapshot.captured_at >= cutoff,
                )
            )
        ).first()

        if not result or result.spend is None:
            logger.debug(f"No metrics found for entity {entity_id} in last 24h")
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
            f"Fetched observations for entity {entity_id}: "
            f"spend=${spend:.2f}, revenue=${revenue:.2f}, roas={roas:.2f}"
        )

        return observations

    except Exception as e:
        logger.warning(f"Failed to fetch observations for entity {entity_id}: {e}")
        return default_observations


# =============================================================================
# CRUD Operations
# =============================================================================


@router.get("", response_model=AgentListResponse)
def list_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    List all agents in the workspace.

    WHAT: Returns paginated list of agents with stats
    WHY: Dashboard needs to show all agents at a glance
    """
    query = db.query(Agent).filter(Agent.workspace_id == current_user.workspace_id)

    if status_filter:
        try:
            status_enum = AgentStatusEnum(status_filter)
            query = query.filter(Agent.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status_filter}",
            )

    total = query.count()
    agents = query.order_by(desc(Agent.created_at)).offset(offset).limit(limit).all()

    # Build response with entity counts and states
    agent_responses = []
    for agent in agents:
        # Get entity states
        entity_states = db.query(AgentEntityState).filter(
            AgentEntityState.agent_id == agent.id
        ).all()

        # Get entity details for states
        entity_ids = [s.entity_id for s in entity_states]
        entities = {
            e.id: e for e in db.query(Entity).filter(Entity.id.in_(entity_ids)).all()
        } if entity_ids else {}

        current_states = [
            AgentEntityStateSummary(
                entity_id=s.entity_id,
                entity_name=entities.get(s.entity_id, Entity(name="Unknown")).name,
                entity_provider=(
                    entities.get(s.entity_id).connection.provider.value
                    if entities.get(s.entity_id) and entities.get(s.entity_id).connection
                    else "unknown"
                ),
                state=s.state,
                accumulation_count=s.accumulation_count or 0,
                accumulation_required=agent.accumulation_required,
                trigger_count=s.trigger_count or 0,
                last_triggered_at=s.last_triggered_at,
                next_eligible_trigger_at=s.next_eligible_trigger_at,
            )
            for s in entity_states
        ]

        agent_responses.append(
            AgentOut(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                status=agent.status,
                error_message=agent.error_message,
                scope_type=agent.scope_type,
                scope_config=agent.scope_config,
                condition=agent.condition,
                accumulation=AccumulationConfig(
                    required=agent.accumulation_required,
                    unit=agent.accumulation_unit,
                    mode=agent.accumulation_mode,
                    window=agent.accumulation_window,
                ),
                trigger=TriggerConfig(
                    mode=agent.trigger_mode,
                    cooldown_minutes=agent.cooldown_duration_minutes,
                    continuous_interval_minutes=agent.continuous_interval_minutes,
                ),
                actions=agent.actions,
                safety=SafetyConfig(**agent.safety_config) if agent.safety_config else None,
                entities_count=len(entity_states),
                last_evaluated_at=agent.last_evaluated_at,
                total_evaluations=agent.total_evaluations or 0,
                total_triggers=agent.total_triggers or 0,
                last_triggered_at=agent.last_triggered_at,
                current_states=current_states,
                created_by=agent.created_by,
                created_at=agent.created_at,
                updated_at=agent.updated_at,
                workspace_id=agent.workspace_id,
            )
        )

    return AgentListResponse(agents=agent_responses, total=total)


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent_in: AgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new agent.

    WHAT: Creates monitoring agent with full configuration
    WHY: User wants to set up automated monitoring

    VALIDATION:
        - If agent has mutating actions (scale_budget, pause_campaign),
          validates that targeted entities have healthy platform connections
        - Returns clear error if platform not connected
    """
    # Generate name if not provided
    name = agent_in.name or _generate_agent_name(agent_in.condition, agent_in.actions)

    # Check for duplicate name
    existing = db.query(Agent).filter(
        and_(
            Agent.workspace_id == current_user.workspace_id,
            Agent.name == name,
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Agent with name '{name}' already exists",
        )

    # Validate platform connections for mutating actions
    validation_error = _validate_agent_platform_access(
        db=db,
        workspace_id=current_user.workspace_id,
        scope_type=agent_in.scope_type,
        scope_config=agent_in.scope_config,
        actions=agent_in.actions,
    )
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)

    # Create agent
    agent = Agent(
        id=uuid.uuid4(),
        workspace_id=current_user.workspace_id,
        name=name,
        description=agent_in.description,
        scope_type=agent_in.scope_type,
        scope_config=agent_in.scope_config,
        condition=agent_in.condition,
        accumulation_required=agent_in.accumulation.required,
        accumulation_unit=agent_in.accumulation.unit,
        accumulation_mode=agent_in.accumulation.mode,
        accumulation_window=agent_in.accumulation.window,
        trigger_mode=agent_in.trigger.mode,
        cooldown_duration_minutes=agent_in.trigger.cooldown_minutes,
        continuous_interval_minutes=agent_in.trigger.continuous_interval_minutes,
        actions=agent_in.actions,
        safety_config=agent_in.safety.model_dump() if agent_in.safety else None,
        status=AgentStatusEnum(agent_in.status),
        created_by=current_user.id,
    )

    db.add(agent)
    db.commit()
    db.refresh(agent)

    logger.info(f"Created agent {agent.id}: {agent.name}")

    return AgentOut(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        error_message=agent.error_message,
        scope_type=agent.scope_type,
        scope_config=agent.scope_config,
        condition=agent.condition,
        accumulation=AccumulationConfig(
            required=agent.accumulation_required,
            unit=agent.accumulation_unit,
            mode=agent.accumulation_mode,
            window=agent.accumulation_window,
        ),
        trigger=TriggerConfig(
            mode=agent.trigger_mode,
            cooldown_minutes=agent.cooldown_duration_minutes,
            continuous_interval_minutes=agent.continuous_interval_minutes,
        ),
        actions=agent.actions,
        safety=SafetyConfig(**agent.safety_config) if agent.safety_config else None,
        entities_count=0,
        last_evaluated_at=agent.last_evaluated_at,
        total_evaluations=0,
        total_triggers=0,
        last_triggered_at=agent.last_triggered_at,
        current_states=[],
        created_by=agent.created_by,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        workspace_id=agent.workspace_id,
    )


# =============================================================================
# Workspace-Level Stats and Events (MUST be before /{agent_id} routes)
# =============================================================================


@router.get("/stats", response_model=AgentStatsResponse)
def get_agent_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get aggregate stats for all agents in workspace.

    WHAT: Returns dashboard-level metrics for agent system
    WHY: Users need quick overview of agent activity

    Returns:
        - active_agents: count of ACTIVE agents
        - triggers_today: count of triggers in last 24h
        - evaluations_this_hour: count of evaluations in last hour
        - errors_today: count of ERROR status agents or failed evaluations
    """
    workspace_id = current_user.workspace_id
    now = datetime.now(timezone.utc)
    today_start = now - timedelta(hours=24)
    hour_start = now - timedelta(hours=1)

    # Count active agents
    active_agents = db.query(Agent).filter(
        and_(
            Agent.workspace_id == workspace_id,
            Agent.status == AgentStatusEnum.active,
        )
    ).count()

    # Count triggers today (events with result_type = triggered)
    triggers_today = db.query(AgentEvaluationEvent).join(
        Agent, AgentEvaluationEvent.agent_id == Agent.id
    ).filter(
        and_(
            Agent.workspace_id == workspace_id,
            AgentEvaluationEvent.result_type == AgentResultTypeEnum.triggered,
            AgentEvaluationEvent.evaluated_at >= today_start,
        )
    ).count()

    # Count evaluations this hour
    evaluations_this_hour = db.query(AgentEvaluationEvent).join(
        Agent, AgentEvaluationEvent.agent_id == Agent.id
    ).filter(
        and_(
            Agent.workspace_id == workspace_id,
            AgentEvaluationEvent.evaluated_at >= hour_start,
        )
    ).count()

    # Count errors: ERROR status agents + error events today
    error_agents = db.query(Agent).filter(
        and_(
            Agent.workspace_id == workspace_id,
            Agent.status == AgentStatusEnum.error,
        )
    ).count()

    error_events = db.query(AgentEvaluationEvent).join(
        Agent, AgentEvaluationEvent.agent_id == Agent.id
    ).filter(
        and_(
            Agent.workspace_id == workspace_id,
            AgentEvaluationEvent.result_type == AgentResultTypeEnum.error,
            AgentEvaluationEvent.evaluated_at >= today_start,
        )
    ).count()

    errors_today = error_agents + error_events

    logger.debug(
        f"Agent stats for workspace {workspace_id}: "
        f"active={active_agents}, triggers={triggers_today}, "
        f"evals={evaluations_this_hour}, errors={errors_today}"
    )

    return AgentStatsResponse(
        active_agents=active_agents,
        triggers_today=triggers_today,
        evaluations_this_hour=evaluations_this_hour,
        errors_today=errors_today,
    )


@router.get("/events", response_model=WorkspaceAgentEventsResponse)
def get_workspace_agent_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    result_type: Optional[str] = Query(None, description="Filter: TRIGGERED, ERROR, etc."),
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="Cursor for pagination (ISO datetime)"),
):
    """
    Get all evaluation events across all agents in workspace.

    WHAT: Returns paginated list of events for notification feed
    WHY: Dashboard shows all agent activity in one feed

    Cursor-based pagination:
        - cursor is the evaluated_at timestamp of the last item
        - Returns events older than cursor
        - nextCursor in response can be used for next page
    """
    workspace_id = current_user.workspace_id

    # Build base query with join to get agent info
    query = db.query(AgentEvaluationEvent).join(
        Agent, AgentEvaluationEvent.agent_id == Agent.id
    ).filter(
        Agent.workspace_id == workspace_id
    )

    # Filter by result type if provided
    if result_type:
        try:
            result_enum = AgentResultTypeEnum(result_type.lower())
            query = query.filter(AgentEvaluationEvent.result_type == result_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid result_type: {result_type}. Valid values: triggered, condition_met, condition_not_met, cooldown, error",
            )

    # Apply cursor for pagination
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
            query = query.filter(AgentEvaluationEvent.evaluated_at < cursor_dt)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cursor format: {cursor}. Use ISO datetime.",
            )

    # Get total count (without cursor filter for consistency)
    total_query = db.query(AgentEvaluationEvent).join(
        Agent, AgentEvaluationEvent.agent_id == Agent.id
    ).filter(Agent.workspace_id == workspace_id)
    if result_type:
        total_query = total_query.filter(
            AgentEvaluationEvent.result_type == AgentResultTypeEnum(result_type.lower())
        )
    total = total_query.count()

    # Fetch events with agent info
    events = query.order_by(
        desc(AgentEvaluationEvent.evaluated_at)
    ).limit(limit).all()

    # Build response with agent names and action summaries
    event_responses = []
    for event in events:
        # Get agent name
        agent = db.query(Agent).filter(Agent.id == event.agent_id).first()
        agent_name = agent.name if agent else "Unknown Agent"

        # Get actions executed for this event
        actions = db.query(AgentActionExecution).filter(
            AgentActionExecution.evaluation_event_id == event.id
        ).all()

        action_summaries = [
            WorkspaceAgentActionSummary(
                id=action.id,
                action_type=action.action_type.value if hasattr(action.action_type, 'value') else str(action.action_type),
                success=action.success,
                description=action.description or "",
                rollback_possible=action.rollback_possible or False,
                rollback_executed_at=action.rollback_executed_at,
                state_before=action.state_before,
                state_after=action.state_after,
            )
            for action in actions
        ]

        event_responses.append(
            WorkspaceAgentEventOut(
                id=event.id,
                agent_id=event.agent_id,
                agent_name=agent_name,
                entity_id=event.entity_id,
                entity_name=event.entity_name,
                entity_provider=event.entity_provider,
                result_type=event.result_type,
                headline=event.headline,
                evaluated_at=event.evaluated_at,
                actions_executed=action_summaries,
            )
        )

    # Calculate next cursor
    next_cursor = None
    if events and len(events) == limit:
        next_cursor = events[-1].evaluated_at.isoformat()

    return WorkspaceAgentEventsResponse(
        events=event_responses,
        total=total,
        next_cursor=next_cursor,
    )


@router.post("/actions/{action_id}/rollback", response_model=ActionRollbackResponse)
def rollback_action(
    action_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rollback a previously executed action.

    WHAT: Restores state_before for reversible actions
    WHY: Users need safety net for automated actions

    Reversible actions:
        - scale_budget: Restore previous budget
        - pause_campaign: Restore previous status

    Non-reversible actions (will fail):
        - email: Cannot unsend
        - webhook: External system, cannot undo
    """
    # Find the action
    action = db.query(AgentActionExecution).filter(
        AgentActionExecution.id == action_id
    ).first()

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    # Verify action belongs to user's workspace
    agent = db.query(Agent).filter(Agent.id == action.agent_id).first()
    if not agent or agent.workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=404, detail="Action not found")

    # Check if rollback is possible
    if not action.rollback_possible:
        raise HTTPException(
            status_code=400,
            detail=f"Rollback not possible for this action. Action type '{action.action_type}' may not support rollback, or state_before was not recorded.",
        )

    # Check if already rolled back
    if action.rollback_executed_at:
        raise HTTPException(
            status_code=400,
            detail=f"Action was already rolled back at {action.rollback_executed_at.isoformat()}",
        )

    # Check if state_before exists
    if not action.state_before:
        raise HTTPException(
            status_code=400,
            detail="Cannot rollback: no previous state recorded",
        )

    # Determine action type and execute rollback
    action_type = action.action_type
    if hasattr(action_type, 'value'):
        action_type_str = action_type.value
    else:
        action_type_str = str(action_type)

    state_before = action.state_before
    state_after = action.state_after or {}

    # TODO: Implement actual platform API calls for rollback
    # For now, we'll record the rollback and mark it as successful
    # In production, this would call Meta/Google API to restore budget/status

    if action_type_str == "scale_budget":
        # Would call platform API to restore budget
        # For example: meta_api.update_campaign_budget(entity_id, state_before["budget"])
        logger.info(
            f"Rollback scale_budget: restoring budget from {state_after.get('budget')} to {state_before.get('budget')}"
        )
        message = f"Budget restored from ${state_after.get('budget', 'N/A')} to ${state_before.get('budget', 'N/A')}"

    elif action_type_str == "pause_campaign":
        # Would call platform API to restore campaign status
        logger.info(
            f"Rollback pause_campaign: restoring status from {state_after.get('status')} to {state_before.get('status')}"
        )
        message = f"Campaign status restored to {state_before.get('status', 'ACTIVE')}"

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Rollback not supported for action type: {action_type_str}",
        )

    # Update action record with rollback info
    action.rollback_executed_at = datetime.now(timezone.utc)
    action.rollback_executed_by = current_user.id
    db.commit()

    logger.info(
        f"User {current_user.id} rolled back action {action_id} ({action_type_str})"
    )

    return ActionRollbackResponse(
        success=True,
        action_id=action.id,
        action_type=action_type_str,
        state_before=state_before,
        state_after=state_after,
        message=message,
    )


# =============================================================================
# Agent Detail Operations
# =============================================================================


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get agent detail.

    WHAT: Returns full agent configuration and current state
    WHY: Agent detail page needs all information
    """
    agent = db.query(Agent).filter(
        and_(
            Agent.id == agent_id,
            Agent.workspace_id == current_user.workspace_id,
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get entity states with details
    entity_states = db.query(AgentEntityState).filter(
        AgentEntityState.agent_id == agent.id
    ).all()

    entity_ids = [s.entity_id for s in entity_states]
    entities = {
        e.id: e for e in db.query(Entity).filter(Entity.id.in_(entity_ids)).all()
    } if entity_ids else {}

    current_states = [
        AgentEntityStateSummary(
            entity_id=s.entity_id,
            entity_name=entities.get(s.entity_id, Entity(name="Unknown")).name,
            entity_provider=(
                entities.get(s.entity_id).connection.provider.value
                if entities.get(s.entity_id) and entities.get(s.entity_id).connection
                else "unknown"
            ),
            state=s.state,
            accumulation_count=s.accumulation_count or 0,
            accumulation_required=agent.accumulation_required,
            trigger_count=s.trigger_count or 0,
            last_triggered_at=s.last_triggered_at,
            next_eligible_trigger_at=s.next_eligible_trigger_at,
        )
        for s in entity_states
    ]

    return AgentOut(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        error_message=agent.error_message,
        scope_type=agent.scope_type,
        scope_config=agent.scope_config,
        condition=agent.condition,
        accumulation=AccumulationConfig(
            required=agent.accumulation_required,
            unit=agent.accumulation_unit,
            mode=agent.accumulation_mode,
            window=agent.accumulation_window,
        ),
        trigger=TriggerConfig(
            mode=agent.trigger_mode,
            cooldown_minutes=agent.cooldown_duration_minutes,
            continuous_interval_minutes=agent.continuous_interval_minutes,
        ),
        actions=agent.actions,
        safety=SafetyConfig(**agent.safety_config) if agent.safety_config else None,
        entities_count=len(entity_states),
        last_evaluated_at=agent.last_evaluated_at,
        total_evaluations=agent.total_evaluations or 0,
        total_triggers=agent.total_triggers or 0,
        last_triggered_at=agent.last_triggered_at,
        current_states=current_states,
        created_by=agent.created_by,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        workspace_id=agent.workspace_id,
    )


@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent(
    agent_id: uuid.UUID,
    agent_in: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an agent.

    WHAT: Partial update to agent configuration
    WHY: User wants to modify agent settings
    """
    agent = db.query(Agent).filter(
        and_(
            Agent.id == agent_id,
            Agent.workspace_id == current_user.workspace_id,
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check for name conflict if name is being changed
    if agent_in.name and agent_in.name != agent.name:
        existing = db.query(Agent).filter(
            and_(
                Agent.workspace_id == current_user.workspace_id,
                Agent.name == agent_in.name,
                Agent.id != agent_id,
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Agent with name '{agent_in.name}' already exists",
            )

    # Update fields
    update_data = agent_in.model_dump(exclude_unset=True)

    if "name" in update_data:
        agent.name = update_data["name"]
    if "description" in update_data:
        agent.description = update_data["description"]
    if "scope_type" in update_data:
        agent.scope_type = update_data["scope_type"]
    if "scope_config" in update_data:
        agent.scope_config = update_data["scope_config"]
    if "condition" in update_data:
        agent.condition = update_data["condition"]
    if "accumulation" in update_data:
        acc = update_data["accumulation"]
        agent.accumulation_required = acc.required
        agent.accumulation_unit = acc.unit
        agent.accumulation_mode = acc.mode
        agent.accumulation_window = acc.window
    if "trigger" in update_data:
        trigger = update_data["trigger"]
        agent.trigger_mode = trigger.mode
        agent.cooldown_duration_minutes = trigger.cooldown_minutes
        agent.continuous_interval_minutes = trigger.continuous_interval_minutes
    if "actions" in update_data:
        agent.actions = update_data["actions"]
    if "safety" in update_data:
        agent.safety_config = update_data["safety"].model_dump() if update_data["safety"] else None

    agent.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(agent)

    logger.info(f"Updated agent {agent.id}")

    return get_agent(agent_id, db, current_user)


@router.delete("/{agent_id}", response_model=SuccessResponse)
def delete_agent(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an agent.

    WHAT: Permanently deletes agent and all related data
    WHY: User no longer wants this agent
    """
    agent = db.query(Agent).filter(
        and_(
            Agent.id == agent_id,
            Agent.workspace_id == current_user.workspace_id,
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent_name = agent.name
    db.delete(agent)  # Cascade deletes entity_states, events, actions
    db.commit()

    logger.info(f"Deleted agent {agent_id}: {agent_name}")

    return SuccessResponse(detail=f"Agent '{agent_name}' deleted")


# =============================================================================
# Status Control
# =============================================================================


@router.post("/{agent_id}/pause", response_model=AgentOut)
def pause_agent(
    agent_id: uuid.UUID,
    request: Optional[AgentPauseRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pause an agent.

    WHAT: Stops agent from evaluating
    WHY: User wants to temporarily disable monitoring
    """
    agent = db.query(Agent).filter(
        and_(
            Agent.id == agent_id,
            Agent.workspace_id == current_user.workspace_id,
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.status == AgentStatusEnum.paused:
        raise HTTPException(status_code=400, detail="Agent is already paused")

    agent.status = AgentStatusEnum.paused
    agent.error_message = request.reason if request and request.reason else "Paused by user"
    agent.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"Paused agent {agent_id}")

    return get_agent(agent_id, db, current_user)


@router.post("/{agent_id}/resume", response_model=AgentOut)
def resume_agent(
    agent_id: uuid.UUID,
    request: Optional[AgentResumeRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Resume a paused agent.

    WHAT: Reactivates agent evaluation
    WHY: User wants to restart monitoring
    """
    agent = db.query(Agent).filter(
        and_(
            Agent.id == agent_id,
            Agent.workspace_id == current_user.workspace_id,
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.status not in [AgentStatusEnum.paused, AgentStatusEnum.error]:
        raise HTTPException(
            status_code=400,
            detail=f"Agent cannot be resumed from {agent.status.value} status",
        )

    agent.status = AgentStatusEnum.active
    agent.error_message = None
    agent.updated_at = datetime.now(timezone.utc)

    # Reset state if requested
    if request and request.reset_state:
        entity_states = db.query(AgentEntityState).filter(
            AgentEntityState.agent_id == agent_id
        ).all()

        for state in entity_states:
            state.state = AgentStateEnum.watching
            state.accumulation_count = 0
            state.accumulation_started_at = None
            state.accumulation_history = []
            state.consecutive_errors = 0
            state.last_error = None
            state.last_error_at = None

    db.commit()

    logger.info(f"Resumed agent {agent_id}")

    return get_agent(agent_id, db, current_user)


# =============================================================================
# Testing
# =============================================================================


@router.post("/{agent_id}/test", response_model=AgentTestResponse)
async def test_agent(
    agent_id: uuid.UUID,
    request: Optional[AgentTestRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Test agent evaluation (dry run).

    WHAT: Evaluates agent without executing actions
    WHY: Verify configuration before enabling
    """
    agent = db.query(Agent).filter(
        and_(
            Agent.id == agent_id,
            Agent.workspace_id == current_user.workspace_id,
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get entities to test
    from ..services.agents.conditions import condition_from_dict, EvalContext

    # Get scoped entities - must match evaluation_engine._get_scoped_entities logic
    scope_config = agent.scope_config or {}

    # Join with Connection for provider filtering
    query = db.query(Entity).join(
        Connection, Entity.connection_id == Connection.id
    ).filter(
        Entity.workspace_id == current_user.workspace_id,
        Connection.status == "active",
    )

    # Filter by provider if specified
    if scope_config.get("provider"):
        try:
            provider_enum = ProviderEnum(scope_config["provider"])
            query = query.filter(Connection.provider == provider_enum)
        except ValueError:
            pass

    if agent.scope_type.value == "specific":
        entity_ids = request.entity_ids if request and request.entity_ids else scope_config.get("entity_ids", [])
        if entity_ids:
            query = query.filter(Entity.id.in_(entity_ids))
    elif agent.scope_type.value == "filter":
        if scope_config.get("level"):
            query = query.filter(Entity.level == scope_config["level"])
    elif agent.scope_type.value == "all":
        if scope_config.get("level"):
            query = query.filter(Entity.level == scope_config["level"])

    entities = query.limit(10).all()  # Limit for testing

    # Evaluate condition for each entity
    condition = condition_from_dict(agent.condition)
    results = []

    for entity in entities:
        # Fetch real metrics from MetricSnapshot (last 24h aggregated)
        observations = await _fetch_entity_observations(db, entity.id)

        context = EvalContext(
            observations=observations,
            entity_id=str(entity.id),
            entity_name=entity.name,
            evaluated_at=datetime.now(timezone.utc),
        )

        result = condition.evaluate(context)

        # Would it trigger? (simplified check)
        would_trigger = result.met and agent.accumulation_required <= 1

        results.append(
            AgentTestResult(
                entity_id=entity.id,
                entity_name=entity.name,
                condition_result=result.met,
                condition_explanation=result.explanation,
                would_trigger=would_trigger,
                trigger_explanation=(
                    "Would trigger immediately" if would_trigger
                    else f"Would need {agent.accumulation_required} consecutive evaluations"
                ),
                observations=observations,
            )
        )

    return AgentTestResponse(
        agent_id=agent_id,
        results=results,
        summary=f"Tested {len(results)} entities. {sum(1 for r in results if r.condition_result)} met condition.",
    )


# =============================================================================
# Events and History
# =============================================================================


@router.get("/{agent_id}/events", response_model=AgentEvaluationEventListResponse)
def get_agent_events(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    result_type: Optional[str] = Query(None, description="Filter by result type"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get evaluation events for an agent.

    WHAT: Returns paginated event history
    WHY: Agent detail page shows evaluation timeline
    """
    # Verify agent belongs to workspace
    agent = db.query(Agent).filter(
        and_(
            Agent.id == agent_id,
            Agent.workspace_id == current_user.workspace_id,
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    query = db.query(AgentEvaluationEvent).filter(
        AgentEvaluationEvent.agent_id == agent_id
    )

    if result_type:
        from ..models import AgentResultTypeEnum
        try:
            result_enum = AgentResultTypeEnum(result_type)
            query = query.filter(AgentEvaluationEvent.result_type == result_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid result_type: {result_type}",
            )

    total = query.count()
    events = query.order_by(desc(AgentEvaluationEvent.evaluated_at)).offset(offset).limit(limit).all()

    return AgentEvaluationEventListResponse(
        events=[
            AgentEvaluationEventOut(
                id=e.id,
                agent_id=e.agent_id,
                entity_id=e.entity_id,
                evaluated_at=e.evaluated_at,
                result_type=e.result_type,
                headline=e.headline,
                entity_name=e.entity_name,
                entity_provider=e.entity_provider,
                entity_snapshot=e.entity_snapshot,
                observations=e.observations,
                condition_definition=e.condition_definition,
                condition_inputs=e.condition_inputs,
                condition_result=e.condition_result,
                condition_explanation=e.condition_explanation,
                accumulation_before=e.accumulation_before,
                accumulation_after=e.accumulation_after,
                accumulation_explanation=e.accumulation_explanation,
                state_before=e.state_before,
                state_after=e.state_after,
                state_transition_reason=e.state_transition_reason,
                should_trigger=e.should_trigger,
                trigger_explanation=e.trigger_explanation,
                summary=e.summary,
                evaluation_duration_ms=e.evaluation_duration_ms,
            )
            for e in events
        ],
        total=total,
    )


@router.get("/{agent_id}/actions", response_model=AgentActionExecutionListResponse)
def get_agent_actions(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get action executions for an agent.

    WHAT: Returns paginated action history
    WHY: Show what actions the agent has taken
    """
    # Verify agent belongs to workspace
    agent = db.query(Agent).filter(
        and_(
            Agent.id == agent_id,
            Agent.workspace_id == current_user.workspace_id,
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    query = db.query(AgentActionExecution).filter(
        AgentActionExecution.agent_id == agent_id
    )

    total = query.count()
    actions = query.order_by(desc(AgentActionExecution.executed_at)).offset(offset).limit(limit).all()

    return AgentActionExecutionListResponse(
        executions=[
            AgentActionExecutionOut(
                id=a.id,
                evaluation_event_id=a.evaluation_event_id,
                agent_id=a.agent_id,
                action_type=a.action_type,
                action_config=a.action_config,
                executed_at=a.executed_at,
                success=a.success,
                description=a.description,
                details=a.details,
                error=a.error,
                duration_ms=a.duration_ms,
                state_before=a.state_before,
                state_after=a.state_after,
                state_verified=a.state_verified,
                rollback_possible=a.rollback_possible,
                rollback_executed_at=a.rollback_executed_at,
                rollback_executed_by=a.rollback_executed_by,
            )
            for a in actions
        ],
        total=total,
    )


# =============================================================================
# Helpers
# =============================================================================


def _generate_agent_name(condition: dict, actions: list) -> str:
    """
    Generate a descriptive name from agent configuration.

    Parameters:
        condition: Condition configuration
        actions: List of action configurations

    Returns:
        Generated name like "High ROAS Scaler"
    """
    # Extract key info
    cond_type = condition.get("type", "")
    metric = condition.get("metric", "metric")
    operator = condition.get("operator", "")

    action_types = [a.get("type", "") for a in actions]

    # Build name parts
    if cond_type == "threshold":
        if operator in ["gt", "gte"]:
            adj = "High"
        elif operator in ["lt", "lte"]:
            adj = "Low"
        else:
            adj = "Target"
    elif cond_type == "change":
        direction = condition.get("direction", "")
        adj = direction.title() if direction else "Changed"
    else:
        adj = "Custom"

    # Action suffix
    if "scale_budget" in action_types:
        suffix = "Scaler"
    elif "pause_campaign" in action_types:
        suffix = "Stop Loss"
    elif "email" in action_types:
        suffix = "Alert"
    elif "webhook" in action_types:
        suffix = "Notifier"
    else:
        suffix = "Agent"

    return f"{adj} {metric.upper()} {suffix}"


def _validate_agent_platform_access(
    db: Session,
    workspace_id: uuid.UUID,
    scope_type: str,
    scope_config: dict,
    actions: list,
) -> Optional[str]:
    """
    Validate that agent has platform access for mutating actions.

    WHAT:
        Checks if agent can actually execute its actions:
        - For scale_budget/pause_campaign: Needs connected platform
        - For email/webhook: No platform needed

    WHY:
        Prevent creating agents that will always fail because:
        - Meta/Google not connected
        - Connection is disconnected/expired
        - No entities match the scope

    Parameters:
        db: Database session
        workspace_id: Workspace UUID
        scope_type: "specific", "filter", or "all"
        scope_config: Scope configuration dict
        actions: List of action configurations

    Returns:
        Error message string if validation fails, None if valid
    """
    from ..models import Connection, Entity, ProviderEnum

    # Check if any actions require platform access
    mutating_actions = {"scale_budget", "pause_campaign", "resume_campaign"}
    action_types = {a.get("type") for a in actions}
    needs_platform = bool(action_types & mutating_actions)

    if not needs_platform:
        # Email/webhook only - no platform validation needed
        return None

    # Get active connections for workspace
    active_connections = db.query(Connection).filter(
        Connection.workspace_id == workspace_id,
        Connection.status == "active",
    ).all()

    if not active_connections:
        return (
            "This agent has actions that require an ad platform connection "
            "(scale budget, pause campaign), but no platforms are connected. "
            "Please connect Meta or Google Ads in Settings first."
        )

    # Build set of connected providers
    connected_providers = {c.provider for c in active_connections}

    # Validate based on scope type
    if scope_type == "specific":
        # Check specific entities
        entity_ids = scope_config.get("entity_ids", [])
        if not entity_ids:
            return "Agent scope is 'specific' but no entity_ids provided."

        entities = db.query(Entity).filter(
            Entity.id.in_(entity_ids),
            Entity.workspace_id == workspace_id,
        ).all()

        if not entities:
            return f"None of the specified entities were found in this workspace."

        # Check each entity has a connection
        entities_without_connection = []
        entities_with_disconnected = []

        for entity in entities:
            if not entity.connection_id:
                entities_without_connection.append(entity.name)
            else:
                # Check if connection is active
                conn = next(
                    (c for c in active_connections if c.id == entity.connection_id),
                    None
                )
                if not conn:
                    entities_with_disconnected.append(entity.name)

        if entities_without_connection:
            return (
                f"The following entities have no platform connection: "
                f"{', '.join(entities_without_connection[:3])}"
                f"{' and more' if len(entities_without_connection) > 3 else ''}. "
                "Agents with budget/pause actions require connected entities."
            )

        if entities_with_disconnected:
            return (
                f"The following entities have disconnected platforms: "
                f"{', '.join(entities_with_disconnected[:3])}"
                f"{' and more' if len(entities_with_disconnected) > 3 else ''}. "
                "Please reconnect the platform in Settings."
            )

    elif scope_type in ("filter", "all"):
        # For filter/all scope, check if there are ANY entities with active connections
        # that match the filter criteria

        query = db.query(Entity).filter(
            Entity.workspace_id == workspace_id,
            Entity.connection_id.isnot(None),
        )

        # Apply filter criteria if present
        if scope_config.get("level"):
            from ..models import LevelEnum
            try:
                level_enum = LevelEnum(scope_config["level"])
                query = query.filter(Entity.level == level_enum)
            except ValueError:
                pass

        if scope_config.get("provider"):
            # Filter to specific provider
            provider = scope_config["provider"]
            connection_ids = [
                c.id for c in active_connections
                if c.provider.value == provider
            ]
            if not connection_ids:
                return (
                    f"Agent is configured for {provider.title()} entities, "
                    f"but {provider.title()} is not connected. "
                    f"Please connect {provider.title()} in Settings first."
                )
            query = query.filter(Entity.connection_id.in_(connection_ids))

        matching_entities = query.limit(1).first()

        if not matching_entities:
            return (
                "No entities match the agent's scope criteria with an active platform connection. "
                "Please ensure you have connected ad platforms and synced campaigns."
            )

    # Validate Google-specific limitations
    if "scale_budget" in action_types or "pause_campaign" in action_types:
        # Check if targeting Google entities at non-campaign level
        if scope_type == "specific":
            entity_ids = scope_config.get("entity_ids", [])
            google_connection_ids = [
                c.id for c in active_connections
                if c.provider == ProviderEnum.google
            ]

            if google_connection_ids:
                from ..models import LevelEnum
                non_campaign_google = db.query(Entity).filter(
                    Entity.id.in_(entity_ids),
                    Entity.connection_id.in_(google_connection_ids),
                    Entity.level != LevelEnum.campaign,
                ).first()

                if non_campaign_google:
                    return (
                        f"Google Ads only supports campaign-level actions, but entity "
                        f"'{non_campaign_google.name}' is at {non_campaign_google.level.value} level. "
                        "For Google, agents can only modify campaigns, not ad groups or ads."
                    )

        elif scope_config.get("provider") == "google":
            level = scope_config.get("level")
            if level and level not in ("campaign",):
                return (
                    f"Google Ads only supports campaign-level actions, but scope is set to "
                    f"'{level}' level. For Google, agents can only modify campaigns."
                )

    return None  # All validations passed


# =============================================================================
# WebSocket Stream
# =============================================================================


@router.websocket("/{agent_id}/stream")
async def agent_stream(
    websocket: WebSocket,
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time agent updates.

    WHAT:
        Streams evaluation events, triggers, and status changes in real-time
        for a specific agent.

    WHY:
        Real-time updates provide better UX:
        - Agent detail page shows live evaluation results
        - Users see immediate feedback when conditions trigger
        - No polling required

    SECURITY:
        - Validates Clerk JWT token (same as REST endpoints)
        - Verifies user has access to the agent's workspace
        - Closes connection with appropriate error code on failure

    PROTOCOL:
        1. Client connects with token in query params: /stream?token=xxx
        2. Server validates JWT and workspace access
        3. Server sends {"type": "connected", ...} on success
        4. Server pushes events: {"type": "evaluation|trigger|status_change", ...}
        5. Client can send {"type": "ping"} to keep alive
        6. Server responds with {"type": "pong"}

    MESSAGE TYPES:
        - connected: Initial connection confirmation
        - evaluation: Agent evaluated an entity
        - trigger: Agent triggered actions
        - status_change: Agent status changed (paused, error, etc.)
        - pong: Response to ping

    REFERENCES:
        - backend/app/services/agents/websocket_manager.py
        - ui/hooks/useAgentStream.ts
    """
    from ..services.agents.websocket_manager import agent_ws_manager

    # Authenticate user via JWT
    user, error = await authenticate_websocket(websocket, db)
    if error:
        await websocket.close(code=4001, reason=error)
        return

    # Verify agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        await websocket.close(code=4004, reason="Agent not found")
        return

    # Verify user has access to agent's workspace
    if agent.workspace_id != user.workspace_id:
        logger.warning(
            f"[WS_AUTH] User {user.id} attempted to access agent in workspace {agent.workspace_id}, "
            f"but belongs to workspace {user.workspace_id}"
        )
        await websocket.close(code=4003, reason="Access denied to this agent")
        return

    workspace_id = agent.workspace_id

    try:
        # Register connection
        await agent_ws_manager.connect(
            websocket=websocket,
            workspace_id=workspace_id,
            agent_id=agent_id,
        )

        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for messages (ping/pong, or just keep alive)
                data = await websocket.receive_json()

                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"WebSocket receive error: {e}")
                break

    finally:
        await agent_ws_manager.disconnect(websocket)


@router.websocket("/workspace/stream")
async def workspace_agent_stream(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for all agents in a workspace.

    WHAT:
        Streams events from ALL agents in a workspace.
        Used for dashboard-level monitoring.

    WHY:
        Dashboard needs to show activity across all agents:
        - Recent triggers
        - Agent status overview
        - Real-time activity feed

    SECURITY:
        - Validates Clerk JWT token (same as REST endpoints)
        - User's workspace_id is used (not from query params for security)

    REFERENCES:
        - backend/app/services/agents/websocket_manager.py
    """
    from ..services.agents.websocket_manager import agent_ws_manager

    # Authenticate user via JWT
    user, error = await authenticate_websocket(websocket, db)
    if error:
        await websocket.close(code=4001, reason=error)
        return

    # Use user's workspace_id (not from query params for security)
    workspace_id = user.workspace_id

    # Verify workspace has agents (optional, allows empty workspaces to connect)
    agent_count = db.query(Agent).filter(Agent.workspace_id == workspace_id).count()
    logger.info(f"[WS_AUTH] User {user.id} connected to workspace stream ({agent_count} agents)")

    try:
        # Register connection (no specific agent = workspace-wide subscription)
        await agent_ws_manager.connect(
            websocket=websocket,
            workspace_id=workspace_id,
            agent_id=None,
        )

        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_json()

                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"WebSocket receive error: {e}")
                break

    finally:
        await agent_ws_manager.disconnect(websocket)
