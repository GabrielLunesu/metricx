"""
Agent System Services Package.

WHAT:
    Core services for autonomous monitoring agents that watch ad performance metrics,
    evaluate conditions over time, and execute actions (notifications, budget scaling,
    campaign pausing).

WHY:
    Merchants need automated monitoring for:
    - Stop-losses (pause when ROAS drops)
    - Scaling (increase budget when performing well)
    - Alerts (notify when metrics hit thresholds)

ARCHITECTURE:
    - Event sourced: Every evaluation is an immutable event
    - Stateful: Agents track accumulation over time ("ROAS > 2 for 3 days")
    - Extensible: Pluggable conditions and actions
    - Observable: Full audit trail, real-time status
    - Safe: Health checks, live state validation, rollback capability

MODULES:
    - conditions: Condition classes (Threshold, Change, Composite, Not)
    - actions: Action classes (Email, ScaleBudget, PauseCampaign, Webhook)
    - state_machine: State transitions (WATCHING -> ACCUMULATING -> TRIGGERED -> COOLDOWN)
    - evaluation_engine: Core evaluation logic
    - notification_service: Email delivery via Resend
    - websocket_manager: Real-time WebSocket event streaming
    - platform_health: Connection health checks before actions
    - platform_actions_meta: Meta Marketing API mutations (campaign/adset/ad)
    - platform_actions_google: Google Ads API mutations (campaign only)
    - action_executor: Platform-aware action execution with safety
    - safety/: Safety mechanisms (rate limiting, circuit breakers, etc.)

REFERENCES:
    - Agent System Implementation Plan
    - backend/app/models.py (Agent, AgentEntityState, etc.)
    - backend/app/schemas.py (agent request/response schemas)
"""

from .conditions import (
    Condition,
    ThresholdCondition,
    ChangeCondition,
    CompositeCondition,
    NotCondition,
    condition_from_dict,
)
from .actions import (
    Action,
    EmailAction,
    ScaleBudgetAction,
    PauseCampaignAction,
    WebhookAction,
    action_from_dict,
)
from .state_machine import AgentStateMachine, StateTransitionResult
from .evaluation_engine import AgentEvaluationEngine
from .notification_service import AgentNotificationService
from .websocket_manager import agent_ws_manager, AgentWebSocketManager
from .platform_health import (
    PlatformHealthService,
    HealthCheckResult,
    HealthStatus,
    require_healthy_connection,
    ConnectionUnhealthyError,
)
from .platform_actions_meta import (
    MetaPlatformActions,
    MetaLiveState,
    MetaActionResult,
    MetaStatus,
    MetaEntityLevel,
)
from .platform_actions_google import (
    GooglePlatformActions,
    GoogleLiveState,
    GoogleActionResult,
    GoogleCampaignStatus,
    dollars_to_micros,
    micros_to_dollars,
)
from .action_executor import (
    PlatformActionExecutor,
    ExecutionContext,
    execute_agent_actions,
)

__all__ = [
    # Conditions
    "Condition",
    "ThresholdCondition",
    "ChangeCondition",
    "CompositeCondition",
    "NotCondition",
    "condition_from_dict",
    # Actions
    "Action",
    "EmailAction",
    "ScaleBudgetAction",
    "PauseCampaignAction",
    "WebhookAction",
    "action_from_dict",
    # State Machine
    "AgentStateMachine",
    "StateTransitionResult",
    # Engine
    "AgentEvaluationEngine",
    # Notifications
    "AgentNotificationService",
    # WebSocket
    "agent_ws_manager",
    "AgentWebSocketManager",
    # Platform Health
    "PlatformHealthService",
    "HealthCheckResult",
    "HealthStatus",
    "require_healthy_connection",
    "ConnectionUnhealthyError",
    # Meta Platform
    "MetaPlatformActions",
    "MetaLiveState",
    "MetaActionResult",
    "MetaStatus",
    "MetaEntityLevel",
    # Google Platform
    "GooglePlatformActions",
    "GoogleLiveState",
    "GoogleActionResult",
    "GoogleCampaignStatus",
    "dollars_to_micros",
    "micros_to_dollars",
    # Action Executor
    "PlatformActionExecutor",
    "ExecutionContext",
    "execute_agent_actions",
]
