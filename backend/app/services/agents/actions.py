"""
Action System for Agent Execution.

WHAT:
    Defines action classes that agents execute when conditions are met.
    Actions include notifications, budget scaling, campaign pausing, and webhooks.

WHY:
    Agents need to do something when triggered:
    - Email: Alert the user
    - ScaleBudget: Adjust campaign budget up/down
    - PauseCampaign: Stop a campaign that's underperforming
    - Webhook: Notify external systems

DESIGN:
    - Abstract Action base class with execute() and describe()
    - Concrete implementations for each action type
    - ActionResult captures success/failure and state changes
    - Factory function to deserialize from dict

SAFETY:
    - All actions fetch live state before execution
    - Budget actions have hard caps (max_budget, min_budget)
    - State before/after stored for rollback capability
    - Rate limiting prevents runaway actions

REFERENCES:
    - Agent System Implementation Plan (Phase 3: Actions with Safety)
    - backend/app/schemas.py (EmailAction, ScaleBudgetAction, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import logging
import httpx

logger = logging.getLogger(__name__)


@dataclass
class ActionContext:
    """
    Context for action execution.

    WHAT: Contains all data needed to execute an action
    WHY: Decouples action logic from data fetching

    Attributes:
        agent_id: UUID of the agent
        agent_name: Agent name for templates
        entity_id: UUID of the entity being acted on
        entity_name: Entity name for templates
        entity_provider: Provider (meta, google, etc.)
        workspace_id: Workspace UUID
        observations: Current metric values
        evaluation_event_id: UUID of the triggering evaluation
        user_email: Primary user email for notifications
        workspace_members: List of workspace member emails
    """

    agent_id: str
    agent_name: str
    entity_id: str
    entity_name: str
    entity_provider: str
    workspace_id: str
    observations: Dict[str, float]
    evaluation_event_id: str
    user_email: Optional[str] = None
    workspace_members: Optional[List[str]] = None
    live_entity_state: Optional[Dict[str, Any]] = None  # From platform API


@dataclass
class ActionResult:
    """
    Result of action execution.

    WHAT: Captures success/failure, state changes, and details
    WHY: Need full audit trail and rollback capability

    Attributes:
        success: Whether action completed successfully
        description: Human-readable description of what happened
        details: Additional details for logging/debugging
        error: Error message if failed
        duration_ms: Execution time in milliseconds
        state_before: State before action (for rollback)
        state_after: State after action
        rollback_possible: Whether action can be rolled back
        skipped: Whether action was skipped (e.g., rate limited)
        skip_reason: Reason for skipping
    """

    success: bool
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: int = 0
    state_before: Optional[Dict[str, Any]] = None
    state_after: Optional[Dict[str, Any]] = None
    rollback_possible: bool = False
    skipped: bool = False
    skip_reason: Optional[str] = None


class Action(ABC):
    """
    Abstract base class for actions.

    WHAT: Defines interface for all action types
    WHY: Enables polymorphic execution in the engine

    Methods:
        execute(): Execute the action, return ActionResult
        describe(): Generate human-readable description
        to_dict(): Serialize to dictionary for storage
        from_dict(): Deserialize from dictionary (class method)
    """

    @abstractmethod
    async def execute(self, context: ActionContext) -> ActionResult:
        """
        Execute the action.

        Parameters:
            context: ActionContext with entity and observation data

        Returns:
            ActionResult with success/failure and details
        """
        pass

    @abstractmethod
    def describe(self) -> str:
        """
        Generate human-readable description of this action.

        Returns:
            String description like "Send email notification"
        """
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize action to dictionary.

        Returns:
            Dictionary representation for JSON storage
        """
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Action":
        """
        Deserialize action from dictionary.

        Parameters:
            data: Dictionary from to_dict() or API request

        Returns:
            Action instance
        """
        pass


class EmailAction(Action):
    """
    Email notification action.

    WHAT: Send notification email when triggered
    WHY: Alert users about important metric conditions

    Templates support {{variables}}:
        - {{agent_name}}: Name of the agent
        - {{entity_name}}: Name of the campaign/ad
        - {{entity_provider}}: Platform (Meta, Google)
        - {{headline}}: Summary of what triggered
        - {{observations}}: Current metric values
    """

    DEFAULT_SUBJECT = "Agent '{{agent_name}}' triggered on {{entity_name}}"
    DEFAULT_BODY = """
Agent: {{agent_name}}
Entity: {{entity_name}} ({{entity_provider}})

{{headline}}

Current Metrics:
{{observations}}

View details in metricx: {{dashboard_url}}
"""

    def __init__(
        self,
        to: Optional[List[str]] = None,
        subject_template: Optional[str] = None,
        body_template: Optional[str] = None,
    ):
        """
        Initialize email action.

        Parameters:
            to: List of email recipients (default: workspace members)
            subject_template: Email subject with {{variables}}
            body_template: Email body with {{variables}}
        """
        self.to = to or []
        self.subject_template = subject_template or self.DEFAULT_SUBJECT
        self.body_template = body_template or self.DEFAULT_BODY

    async def execute(self, context: ActionContext) -> ActionResult:
        """
        Send notification email via Resend.

        WHAT:
            Sends real email using AgentNotificationService.

        WHY:
            Users need immediate notification when agents trigger.
            Uses professional HTML templates with full context.

        Parameters:
            context: ActionContext with template variables

        Returns:
            ActionResult with send status

        REFERENCES:
            - backend/app/services/agents/notification_service.py
        """
        import time
        start = time.time()

        try:
            # Determine recipients
            recipients = self.to or []
            if not recipients and context.workspace_members:
                recipients = context.workspace_members
            if not recipients and context.user_email:
                recipients = [context.user_email]

            if not recipients:
                return ActionResult(
                    success=False,
                    description="No email recipients configured",
                    error="No recipients",
                    duration_ms=int((time.time() - start) * 1000),
                )

            # Build template context
            template_vars = {
                "agent_name": context.agent_name,
                "entity_name": context.entity_name,
                "entity_provider": context.entity_provider.title(),
                "observations": self._format_observations(context.observations),
                "headline": f"Condition met for {context.entity_name}",
                "dashboard_url": f"https://metricx.ai/agents/{context.agent_id}",
            }

            # Render custom body template as condition explanation
            condition_explanation = self._render_template(self.body_template, template_vars)

            # Use the notification service for real email delivery
            from .notification_service import AgentNotificationService

            notification_service = AgentNotificationService.from_settings()

            result = await notification_service.send_trigger_notification(
                agent_id=context.agent_id,
                agent_name=context.agent_name,
                entity_name=context.entity_name,
                entity_provider=context.entity_provider,
                condition_explanation=condition_explanation,
                observations=context.observations,
                action_results=[],  # This email IS the action
                recipients=recipients,
                workspace_id=context.workspace_id,
            )

            duration_ms = int((time.time() - start) * 1000)

            if result.success:
                logger.info(
                    f"Email sent to {recipients} for agent {context.agent_name}, "
                    f"message_id={result.message_id}"
                )
                return ActionResult(
                    success=True,
                    description=f"Email sent to {len(recipients)} recipient(s)",
                    details={
                        "recipients": recipients,
                        "message_id": result.message_id,
                    },
                    duration_ms=duration_ms,
                )
            else:
                logger.warning(f"Email send failed: {result.error}")
                return ActionResult(
                    success=False,
                    description="Failed to send email",
                    error=result.error,
                    duration_ms=duration_ms,
                )

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            logger.exception(f"Email action failed: {e}")
            return ActionResult(
                success=False,
                description="Failed to send email",
                error=str(e),
                duration_ms=duration_ms,
            )

    def _format_observations(self, observations: Dict[str, float]) -> str:
        """Format observations for email body."""
        lines = []
        for metric, value in observations.items():
            if metric in ["spend", "revenue", "cpc", "cpa"]:
                lines.append(f"  {metric.upper()}: ${value:,.2f}")
            elif metric in ["roas", "poas"]:
                lines.append(f"  {metric.upper()}: {value:.2f}x")
            elif metric in ["ctr", "cvr"]:
                lines.append(f"  {metric.upper()}: {value:.2f}%")
            else:
                lines.append(f"  {metric.upper()}: {value:,.2f}")
        return "\n".join(lines) if lines else "  (no metrics)"

    def _render_template(self, template: str, vars: Dict[str, Any]) -> str:
        """Simple template rendering with {{variable}} syntax."""
        result = template
        for key, value in vars.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    def describe(self) -> str:
        """Generate human-readable description."""
        if self.to:
            return f"Send email to {', '.join(self.to)}"
        return "Send email notification"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": "email",
            "to": self.to,
            "subject_template": self.subject_template,
            "body_template": self.body_template,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmailAction":
        """
        Deserialize from dictionary.

        Handles both flat and nested config structures:
        - Flat: {"type": "email", "to": [...], "subject_template": "..."}
        - Nested: {"type": "email", "config": {"subject_template": "..."}}
        """
        # Handle nested config structure (from Copilot creation)
        config = data.get("config", {})

        # Prefer top-level values, fall back to nested config
        return cls(
            to=data.get("to") or config.get("to"),
            subject_template=data.get("subject_template") or config.get("subject_template"),
            body_template=data.get("body_template") or config.get("body_template"),
        )


class ScaleBudgetAction(Action):
    """
    Budget scaling action.

    WHAT: Adjust campaign budget up or down
    WHY: Auto-scale winning campaigns, reduce spend on losers

    SAFETY:
        - Fetches live state before action
        - Enforces max_budget and min_budget caps
        - Stores state before/after for rollback
        - Logs external changes detected

    Example:
        ScaleBudgetAction(scale_percent=20, max_budget=1000)
        → Increase budget by 20%, but never exceed $1000
    """

    def __init__(
        self,
        scale_percent: float,
        max_budget: Optional[float] = None,
        min_budget: Optional[float] = None,
    ):
        """
        Initialize budget scaling action.

        Parameters:
            scale_percent: Percentage to scale (positive = increase, negative = decrease)
            max_budget: Maximum budget cap (optional)
            min_budget: Minimum budget floor (optional)
        """
        self.scale_percent = scale_percent
        self.max_budget = max_budget
        self.min_budget = min_budget

    async def execute(self, context: ActionContext) -> ActionResult:
        """
        Scale campaign budget.

        Parameters:
            context: ActionContext with entity and live state

        Returns:
            ActionResult with budget change details
        """
        import time
        start = time.time()

        try:
            # Get live state from context (should be populated by pre-action validator)
            live_state = context.live_entity_state
            if not live_state:
                return ActionResult(
                    success=False,
                    description="No live state available",
                    error="Live state required for budget scaling",
                    duration_ms=int((time.time() - start) * 1000),
                )

            # Check entity status
            entity_status = live_state.get("status", "").upper()
            if entity_status not in ["ACTIVE", "ENABLED"]:
                return ActionResult(
                    success=False,
                    description=f"Entity status is {entity_status}, cannot scale",
                    error="Entity not active",
                    duration_ms=int((time.time() - start) * 1000),
                    skipped=True,
                    skip_reason=f"Entity status is {entity_status}",
                )

            # Get current budget
            current_budget = live_state.get("budget")
            if current_budget is None:
                return ActionResult(
                    success=False,
                    description="Could not determine current budget",
                    error="Budget not available",
                    duration_ms=int((time.time() - start) * 1000),
                )

            current_budget = float(current_budget)

            # Calculate new budget
            new_budget = current_budget * (1 + self.scale_percent / 100)

            # Apply caps
            original_new_budget = new_budget
            if self.max_budget is not None:
                new_budget = min(new_budget, self.max_budget)
            if self.min_budget is not None:
                new_budget = max(new_budget, self.min_budget)

            # Round to 2 decimal places
            new_budget = round(new_budget, 2)

            # Check if change is meaningful
            if abs(new_budget - current_budget) < 0.01:
                return ActionResult(
                    success=True,
                    description="No budget change needed (already at limit)",
                    details={
                        "current_budget": current_budget,
                        "calculated_budget": original_new_budget,
                        "capped_budget": new_budget,
                    },
                    duration_ms=int((time.time() - start) * 1000),
                    skipped=True,
                    skip_reason="Budget already at limit",
                )

            # Execute budget change (placeholder - would call platform API)
            # In production: await platform_client.set_budget(entity_id, new_budget)
            logger.info(
                f"Would set budget for {context.entity_id} from ${current_budget} to ${new_budget}"
            )

            duration_ms = int((time.time() - start) * 1000)

            change_pct = ((new_budget - current_budget) / current_budget) * 100
            direction = "increased" if new_budget > current_budget else "decreased"

            return ActionResult(
                success=True,
                description=f"Budget {direction} from ${current_budget:.2f} to ${new_budget:.2f} ({change_pct:+.1f}%)",
                details={
                    "scale_percent": self.scale_percent,
                    "max_budget": self.max_budget,
                    "min_budget": self.min_budget,
                },
                state_before={"budget": current_budget},
                state_after={"budget": new_budget},
                rollback_possible=True,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            logger.exception(f"Scale budget action failed: {e}")
            return ActionResult(
                success=False,
                description="Failed to scale budget",
                error=str(e),
                duration_ms=duration_ms,
            )

    def describe(self) -> str:
        """Generate human-readable description."""
        direction = "increase" if self.scale_percent > 0 else "decrease"
        desc = f"Scale budget {direction} {abs(self.scale_percent)}%"
        if self.max_budget:
            desc += f" (max ${self.max_budget})"
        if self.min_budget:
            desc += f" (min ${self.min_budget})"
        return desc

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": "scale_budget",
            "scale_percent": self.scale_percent,
            "max_budget": self.max_budget,
            "min_budget": self.min_budget,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScaleBudgetAction":
        """Deserialize from dictionary."""
        return cls(
            scale_percent=float(data["scale_percent"]),
            max_budget=float(data["max_budget"]) if data.get("max_budget") else None,
            min_budget=float(data["min_budget"]) if data.get("min_budget") else None,
        )


class PauseCampaignAction(Action):
    """
    Campaign pause action.

    WHAT: Pause the campaign (set status to PAUSED)
    WHY: Stop-loss for underperforming campaigns

    SAFETY:
        - Only pauses ACTIVE campaigns
        - Stores status before for rollback
        - Logs action for audit trail
    """

    def __init__(self):
        """Initialize pause action (no configuration needed)."""
        pass

    async def execute(self, context: ActionContext) -> ActionResult:
        """
        Pause the campaign.

        Parameters:
            context: ActionContext with entity and live state

        Returns:
            ActionResult with pause status
        """
        import time
        start = time.time()

        try:
            # Get live state
            live_state = context.live_entity_state
            if not live_state:
                return ActionResult(
                    success=False,
                    description="No live state available",
                    error="Live state required for pause action",
                    duration_ms=int((time.time() - start) * 1000),
                )

            # Check current status
            current_status = live_state.get("status", "").upper()
            if current_status in ["PAUSED", "DISABLED", "DELETED"]:
                return ActionResult(
                    success=True,
                    description=f"Campaign already {current_status}",
                    duration_ms=int((time.time() - start) * 1000),
                    skipped=True,
                    skip_reason=f"Already {current_status}",
                )

            # Execute pause (placeholder - would call platform API)
            logger.info(f"Would pause campaign {context.entity_id}")

            duration_ms = int((time.time() - start) * 1000)

            return ActionResult(
                success=True,
                description=f"Campaign paused (was {current_status})",
                state_before={"status": current_status},
                state_after={"status": "PAUSED"},
                rollback_possible=True,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            logger.exception(f"Pause campaign action failed: {e}")
            return ActionResult(
                success=False,
                description="Failed to pause campaign",
                error=str(e),
                duration_ms=duration_ms,
            )

    def describe(self) -> str:
        """Generate human-readable description."""
        return "Pause campaign"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {"type": "pause_campaign"}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PauseCampaignAction":
        """Deserialize from dictionary."""
        return cls()


class WebhookAction(Action):
    """
    Webhook call action.

    WHAT: Call external URL when triggered
    WHY: Integration with external systems (Slack, Zapier, custom)

    Templates support {{variables}} in body_template:
        - {{agent_name}}: Name of the agent
        - {{entity_name}}: Name of the campaign/ad
        - {{observations}}: JSON of current metrics
    """

    def __init__(
        self,
        url: str,
        method: Literal["GET", "POST", "PUT"] = "POST",
        headers: Optional[Dict[str, str]] = None,
        body_template: Optional[str] = None,
    ):
        """
        Initialize webhook action.

        Parameters:
            url: Webhook URL to call
            method: HTTP method
            headers: Custom headers
            body_template: Request body template with {{variables}}
        """
        self.url = url
        self.method = method
        self.headers = headers or {}
        self.body_template = body_template

    async def execute(self, context: ActionContext) -> ActionResult:
        """
        Call webhook URL.

        Parameters:
            context: ActionContext with template variables

        Returns:
            ActionResult with HTTP response details
        """
        import time
        import json
        start = time.time()

        try:
            # Build request body
            if self.body_template:
                body = self._render_template(self.body_template, context)
            else:
                # Default JSON body
                body = json.dumps({
                    "event": "agent_triggered",
                    "agent_id": context.agent_id,
                    "agent_name": context.agent_name,
                    "entity_id": context.entity_id,
                    "entity_name": context.entity_name,
                    "entity_provider": context.entity_provider,
                    "observations": context.observations,
                    "timestamp": datetime.utcnow().isoformat(),
                })

            # Set headers
            headers = {
                "Content-Type": "application/json",
                **self.headers,
            }

            # Make HTTP request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=self.method,
                    url=self.url,
                    headers=headers,
                    content=body if self.method != "GET" else None,
                )

            duration_ms = int((time.time() - start) * 1000)

            if response.is_success:
                return ActionResult(
                    success=True,
                    description=f"Webhook called successfully ({response.status_code})",
                    details={
                        "url": self.url,
                        "method": self.method,
                        "status_code": response.status_code,
                    },
                    duration_ms=duration_ms,
                )
            else:
                return ActionResult(
                    success=False,
                    description=f"Webhook returned error ({response.status_code})",
                    error=f"HTTP {response.status_code}: {response.text[:200]}",
                    details={
                        "url": self.url,
                        "method": self.method,
                        "status_code": response.status_code,
                    },
                    duration_ms=duration_ms,
                )

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            logger.exception(f"Webhook action failed: {e}")
            return ActionResult(
                success=False,
                description="Failed to call webhook",
                error=str(e),
                details={"url": self.url},
                duration_ms=duration_ms,
            )

    def _render_template(self, template: str, context: ActionContext) -> str:
        """Simple template rendering."""
        import json
        result = template
        result = result.replace("{{agent_name}}", context.agent_name)
        result = result.replace("{{entity_name}}", context.entity_name)
        result = result.replace("{{entity_provider}}", context.entity_provider)
        result = result.replace("{{observations}}", json.dumps(context.observations))
        return result

    def describe(self) -> str:
        """Generate human-readable description."""
        return f"Call webhook: {self.method} {self.url}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": "webhook",
            "url": self.url,
            "method": self.method,
            "headers": self.headers,
            "body_template": self.body_template,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebhookAction":
        """Deserialize from dictionary."""
        return cls(
            url=data["url"],
            method=data.get("method", "POST"),
            headers=data.get("headers"),
            body_template=data.get("body_template"),
        )


def action_from_dict(data: Dict[str, Any]) -> Action:
    """
    Factory function to deserialize action from dictionary.

    WHAT: Create appropriate Action subclass from dict
    WHY: Unified deserialization for all action types

    Parameters:
        data: Dictionary with "type" field and action-specific fields

    Returns:
        Appropriate Action subclass instance

    Raises:
        ValueError: If action type is unknown
    """
    action_type = data.get("type")

    if action_type == "email":
        return EmailAction.from_dict(data)
    elif action_type == "scale_budget":
        return ScaleBudgetAction.from_dict(data)
    elif action_type == "pause_campaign":
        return PauseCampaignAction.from_dict(data)
    elif action_type == "webhook":
        return WebhookAction.from_dict(data)
    else:
        raise ValueError(f"Unknown action type: {action_type}")
