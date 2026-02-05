"""
Agent Notification Service.

WHAT:
    Handles sending notifications when agents trigger, error, or stop.
    Supports multiple channels: Email (Resend), Slack (Webhooks), HTTP Webhooks.

WHY:
    Users need to be notified about agent events:
    - Trigger: Agent condition was met, actions executed
    - Error: Agent evaluation failed
    - Stopped: Agent was stopped due to repeated errors
    - Circuit Breaker: Safety mechanism tripped

DESIGN:
    - Multi-channel: Email, Slack, Webhooks
    - Beautiful HTML emails with dark/light mode support
    - Slack Block Kit for rich Slack messages
    - Plain text fallbacks
    - Settings integration for API keys
    - Graceful fallback when services not configured

REFERENCES:
    - Agent System Implementation Plan (Phase 4: Notifications)
    - Resend Python SDK: https://resend.com/docs/api-reference/emails/send-email
    - Slack Incoming Webhooks: https://api.slack.com/messaging/webhooks
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

import httpx

from .slack_formatter import format_slack_message

logger = logging.getLogger(__name__)


# =============================================================================
# EMAIL TEMPLATES - Professional HTML with inline styles
# =============================================================================

EMAIL_HEADER = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f9fafb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" style="width: 100%; max-width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
"""

EMAIL_FOOTER = """
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 32px; border-top: 1px solid #e5e7eb;">
                            <table role="presentation" style="width: 100%;">
                                <tr>
                                    <td style="color: #6b7280; font-size: 13px;">
                                        <p style="margin: 0 0 8px;">This is an automated notification from your Metricx agents.</p>
                                        <p style="margin: 0;">
                                            <a href="{dashboard_url}/settings?tab=notifications" style="color: #3b82f6; text-decoration: none;">Manage notification settings</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>

                <!-- Logo/Branding -->
                <table role="presentation" style="width: 100%; max-width: 600px; margin-top: 24px;">
                    <tr>
                        <td align="center" style="color: #9ca3af; font-size: 12px;">
                            <p style="margin: 0;">Powered by <strong>Metricx</strong> — Ad Analytics & Optimization</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def _generate_trigger_headline(
    condition_explanation: str,
    observations: Dict[str, float],
) -> tuple[str, str, str]:
    """
    Generate an exciting, human-friendly headline from the condition.

    Returns:
        (headline, emoji, color) - The main headline text, emoji, and accent color
    """
    explanation_lower = condition_explanation.lower()

    # Try to extract metric value from observations for the headline
    # Map common metrics to friendly names and formats
    # (friendly_name, format, positive_verb, negative_verb)
    metric_display = {
        "revenue": ("Revenue", "${:,.0f}", "crossed"),
        "spend": ("Spend", "${:,.0f}", "exceeded"),
        "roas": ("ROAS", "{:.2f}x", "reached"),
        "poas": ("POAS", "{:.2f}x", "reached"),
        "cpc": ("CPC", "${:.2f}", "changed to"),
        "cpa": ("CPA", "${:.2f}", "changed to"),
        "ctr": ("CTR", "{:.2f}%", "hit"),
        "cvr": ("Conversion Rate", "{:.2f}%", "reached"),
        "clicks": ("Clicks", "{:,.0f}", "reached"),
        "conversions": ("Conversions", "{:,.0f}", "hit"),
        "impressions": ("Impressions", "{:,.0f}", "crossed"),
    }

    # Detect positive vs negative trigger (for color and emoji)
    # Costs going up (spend, CPC, CPA) are typically warnings, not celebrations
    cost_metrics = ["spend", "cpc", "cpa"]
    is_cost_increase = any(m in explanation_lower for m in cost_metrics) and any(
        word in explanation_lower for word in ["limit", "exceeded", "crossed", "above", "increased"]
    )
    is_positive = not is_cost_increase and any(word in explanation_lower for word in ["above", "exceeded", "crossed", "reached", "increased"])
    is_negative = any(word in explanation_lower for word in ["below", "dropped", "fell", "decreased", "under"]) or is_cost_increase

    # Determine if it's a threshold crossing or change detection
    is_change = "change" in explanation_lower or "increased" in explanation_lower or "decreased" in explanation_lower

    # Pick emoji and color based on context
    if is_positive:
        emoji = "🎉"  # or 📈
        color = "#10b981"  # Green
    elif is_negative:
        emoji = "⚠️"  # or 📉
        color = "#f59e0b"  # Amber/warning
    else:
        emoji = "🔔"
        color = "#3b82f6"  # Blue

    # Try to build a specific headline from the observations
    for metric_key, (friendly_name, fmt, verb) in metric_display.items():
        if metric_key in observations:
            value = observations[metric_key]
            formatted_value = fmt.format(value)

            # Check if this metric is mentioned in the condition
            if metric_key in explanation_lower:
                # Special handling for cost metrics - say "spiked to" or "exceeded"
                if metric_key in cost_metrics and is_cost_increase:
                    if metric_key == "spend":
                        headline = f"{friendly_name} exceeded {formatted_value}"
                    else:
                        headline = f"{friendly_name} spiked to {formatted_value}"
                elif is_change:
                    if is_positive:
                        headline = f"{friendly_name} jumped to {formatted_value}!"
                    elif is_negative:
                        headline = f"{friendly_name} dropped to {formatted_value}"
                    else:
                        headline = f"{friendly_name} changed to {formatted_value}"
                else:
                    if is_positive:
                        headline = f"{friendly_name} {verb} {formatted_value}!"
                    elif is_negative:
                        headline = f"{friendly_name} fell to {formatted_value}"
                    else:
                        headline = f"{friendly_name} is now {formatted_value}"

                return headline, emoji, color

    # Fallback: use the condition explanation directly but make it punchier
    # Remove technical jargon and clean up
    headline = condition_explanation
    if "threshold" in headline.lower():
        # Strip "threshold" language
        headline = headline.replace("threshold", "").replace("(current:", "-").rstrip(")")

    return headline, emoji, color


def _build_trigger_email(
    agent_name: str,
    entity_name: str,
    entity_provider: str,
    condition_explanation: str,
    observations: Dict[str, float],
    action_results: List[Dict[str, Any]],
    dashboard_url: str,
    timestamp: str,
) -> str:
    """Build trigger notification HTML email with exciting headline."""

    # Generate the exciting headline
    headline, emoji, accent_color = _generate_trigger_headline(condition_explanation, observations)

    # Format metrics as table rows
    metrics_rows = ""
    for metric, value in observations.items():
        if metric in ["spend", "revenue", "cpc", "cpa"]:
            formatted = f"${value:,.2f}"
        elif metric in ["roas", "poas"]:
            formatted = f"{value:.2f}x"
        elif metric in ["ctr", "cvr"]:
            formatted = f"{value:.2f}%"
        else:
            formatted = f"{value:,.0f}"

        metrics_rows += f"""
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #f3f4f6; color: #6b7280; font-size: 14px;">{metric.upper()}</td>
                <td style="padding: 8px 0; border-bottom: 1px solid #f3f4f6; text-align: right; font-weight: 600; color: #111827; font-size: 14px;">{formatted}</td>
            </tr>
        """

    # Format actions
    actions_html = ""
    for result in action_results:
        status_color = "#10b981" if result.get("success") else "#ef4444"
        status_icon = "&#10003;" if result.get("success") else "&#10007;"
        actions_html += f"""
            <div style="display: flex; align-items: center; padding: 8px 0;">
                <span style="color: {status_color}; margin-right: 8px; font-size: 16px;">{status_icon}</span>
                <span style="color: #374151; font-size: 14px;">{result.get('description', 'Action executed')}</span>
            </div>
        """

    if not actions_html:
        actions_html = '<p style="color: #6b7280; font-size: 14px; margin: 0;">Notification sent</p>'

    # Provider badge colors
    provider_colors = {
        "meta": ("#1877f2", "#e7f3ff"),
        "google": ("#4285f4", "#e8f0fe"),
        "tiktok": ("#000000", "#f5f5f5"),
    }
    provider_color, provider_bg = provider_colors.get(entity_provider.lower(), ("#6b7280", "#f3f4f6"))

    content = f"""
                    <!-- Hero Section - The Big Headline -->
                    <tr>
                        <td style="padding: 40px 32px 24px; text-align: center; background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%);">
                            <div style="font-size: 48px; margin-bottom: 16px;">{emoji}</div>
                            <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #111827; line-height: 1.3;">
                                {headline}
                            </h1>
                            <p style="margin: 12px 0 0; font-size: 15px; color: #6b7280;">
                                on <strong style="color: #111827;">{entity_name}</strong>
                            </p>
                        </td>
                    </tr>

                    <!-- Agent & Context Bar -->
                    <tr>
                        <td style="padding: 16px 32px; background-color: #f9fafb; border-top: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb;">
                            <table role="presentation" style="width: 100%;">
                                <tr>
                                    <td style="vertical-align: middle;">
                                        <span style="display: inline-block; background-color: {provider_bg}; color: {provider_color}; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; margin-right: 8px;">
                                            {entity_provider.upper()}
                                        </span>
                                        <span style="color: #6b7280; font-size: 13px;">Agent: <strong style="color: #374151;">{agent_name}</strong></span>
                                    </td>
                                    <td style="text-align: right; vertical-align: middle;">
                                        <span style="color: #9ca3af; font-size: 12px;">{timestamp}</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Condition Detail (smaller, secondary) -->
                    <tr>
                        <td style="padding: 24px 32px 16px;">
                            <p style="margin: 0 0 8px; font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">What Triggered</p>
                            <p style="margin: 0; font-size: 14px; color: #374151; line-height: 1.5;">{condition_explanation}</p>
                        </td>
                    </tr>

                    <!-- Metrics -->
                    <tr>
                        <td style="padding: 8px 32px 24px;">
                            <p style="margin: 0 0 12px; font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Current Metrics</p>
                            <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #f9fafb; border-radius: 8px; padding: 8px;">
                                {metrics_rows}
                            </table>
                        </td>
                    </tr>

                    <!-- Actions -->
                    <tr>
                        <td style="padding: 0 32px 24px;">
                            <p style="margin: 0 0 12px; font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Actions Taken</p>
                            <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 16px; border-radius: 8px;">
                                {actions_html}
                            </div>
                        </td>
                    </tr>

                    <!-- CTA Button -->
                    <tr>
                        <td style="padding: 0 32px 32px;">
                            <table role="presentation" style="width: 100%;">
                                <tr>
                                    <td align="center">
                                        <a href="{dashboard_url}" style="display: inline-block; background-color: #111827; padding: 14px 32px; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                                            View Full Details &rarr;
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
    """

    return (
        EMAIL_HEADER.format(title=headline) +
        content +
        EMAIL_FOOTER.format(dashboard_url=dashboard_url.rsplit('/agents', 1)[0])
    )


def _build_error_email(
    agent_name: str,
    error_message: str,
    dashboard_url: str,
    timestamp: str,
) -> str:
    """Build error notification HTML email."""

    content = f"""
                    <!-- Header -->
                    <tr>
                        <td style="padding: 32px 32px 24px;">
                            <table role="presentation" style="width: 100%;">
                                <tr>
                                    <td>
                                        <span style="display: inline-block; background-color: #fef3c7; color: #92400e; font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">
                                            &#9888; Agent Error
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 16px;">
                                        <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #111827;">{agent_name}</h1>
                                        <p style="margin: 8px 0 0; font-size: 15px; color: #6b7280;">encountered an error during evaluation</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Time -->
                    <tr>
                        <td style="padding: 0 32px 24px;">
                            <span style="color: #9ca3af; font-size: 13px;">{timestamp}</span>
                        </td>
                    </tr>

                    <!-- Error Message -->
                    <tr>
                        <td style="padding: 0 32px 24px;">
                            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 0 8px 8px 0;">
                                <p style="margin: 0 0 4px; font-size: 12px; font-weight: 600; color: #92400e; text-transform: uppercase; letter-spacing: 0.5px;">Error Details</p>
                                <p style="margin: 0; font-size: 14px; color: #78350f; font-family: monospace; word-break: break-word;">{error_message[:500]}</p>
                            </div>
                        </td>
                    </tr>

                    <!-- Info -->
                    <tr>
                        <td style="padding: 0 32px 24px;">
                            <p style="margin: 0; font-size: 14px; color: #6b7280; line-height: 1.6;">
                                The agent has been temporarily paused to prevent further errors.
                                Please review the configuration and fix any issues before resuming.
                            </p>
                        </td>
                    </tr>

                    <!-- CTA Button -->
                    <tr>
                        <td style="padding: 0 32px 32px;">
                            <table role="presentation">
                                <tr>
                                    <td style="background-color: #111827; border-radius: 8px;">
                                        <a href="{dashboard_url}" style="display: inline-block; padding: 14px 28px; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none;">
                                            Review Agent &rarr;
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
    """

    return (
        EMAIL_HEADER.format(title=f"Agent Error: {agent_name}") +
        content +
        EMAIL_FOOTER.format(dashboard_url=dashboard_url.rsplit('/agents', 1)[0])
    )


def _build_stopped_email(
    agent_name: str,
    reason: str,
    dashboard_url: str,
    timestamp: str,
) -> str:
    """Build stopped notification HTML email."""

    content = f"""
                    <!-- Header -->
                    <tr>
                        <td style="padding: 32px 32px 24px;">
                            <table role="presentation" style="width: 100%;">
                                <tr>
                                    <td>
                                        <span style="display: inline-block; background-color: #fee2e2; color: #991b1b; font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">
                                            &#128721; Agent Stopped
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 16px;">
                                        <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #111827;">{agent_name}</h1>
                                        <p style="margin: 8px 0 0; font-size: 15px; color: #6b7280;">has been automatically stopped</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Time -->
                    <tr>
                        <td style="padding: 0 32px 24px;">
                            <span style="color: #9ca3af; font-size: 13px;">{timestamp}</span>
                        </td>
                    </tr>

                    <!-- Reason -->
                    <tr>
                        <td style="padding: 0 32px 24px;">
                            <div style="background-color: #fee2e2; border-left: 4px solid #ef4444; padding: 16px; border-radius: 0 8px 8px 0;">
                                <p style="margin: 0 0 4px; font-size: 12px; font-weight: 600; color: #991b1b; text-transform: uppercase; letter-spacing: 0.5px;">Reason</p>
                                <p style="margin: 0; font-size: 15px; color: #7f1d1d;">{reason}</p>
                            </div>
                        </td>
                    </tr>

                    <!-- Info -->
                    <tr>
                        <td style="padding: 0 32px 24px;">
                            <p style="margin: 0; font-size: 14px; color: #6b7280; line-height: 1.6;">
                                To resume monitoring, please fix the underlying issue and manually restart the agent
                                from the dashboard.
                            </p>
                        </td>
                    </tr>

                    <!-- CTA Button -->
                    <tr>
                        <td style="padding: 0 32px 32px;">
                            <table role="presentation">
                                <tr>
                                    <td style="background-color: #111827; border-radius: 8px;">
                                        <a href="{dashboard_url}" style="display: inline-block; padding: 14px 28px; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none;">
                                            View Agent &rarr;
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
    """

    return (
        EMAIL_HEADER.format(title=f"Agent Stopped: {agent_name}") +
        content +
        EMAIL_FOOTER.format(dashboard_url=dashboard_url.rsplit('/agents', 1)[0])
    )


def _build_circuit_breaker_email(
    agent_name: str,
    entity_name: str,
    trigger_reason: str,
    metric_values: Dict[str, float],
    dashboard_url: str,
    timestamp: str,
) -> str:
    """Build circuit breaker notification HTML email."""

    # Format metrics
    metrics_rows = ""
    for metric, value in metric_values.items():
        if isinstance(value, float):
            formatted = f"{value:.2f}"
        else:
            formatted = str(value)
        metrics_rows += f"""
            <tr>
                <td style="padding: 6px 0; color: #6b7280; font-size: 13px;">{metric}</td>
                <td style="padding: 6px 0; text-align: right; font-weight: 500; color: #111827; font-size: 13px;">{formatted}</td>
            </tr>
        """

    content = f"""
                    <!-- Header -->
                    <tr>
                        <td style="padding: 32px 32px 24px;">
                            <table role="presentation" style="width: 100%;">
                                <tr>
                                    <td>
                                        <span style="display: inline-block; background-color: #fef3c7; color: #92400e; font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">
                                            &#128737; Safety Alert
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 16px;">
                                        <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #111827;">Circuit Breaker Triggered</h1>
                                        <p style="margin: 8px 0 0; font-size: 15px; color: #6b7280;">
                                            Agent <strong style="color: #111827;">{agent_name}</strong> on <strong style="color: #111827;">{entity_name}</strong>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Time -->
                    <tr>
                        <td style="padding: 0 32px 24px;">
                            <span style="color: #9ca3af; font-size: 13px;">{timestamp}</span>
                        </td>
                    </tr>

                    <!-- Reason -->
                    <tr>
                        <td style="padding: 0 32px 24px;">
                            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 0 8px 8px 0;">
                                <p style="margin: 0 0 4px; font-size: 12px; font-weight: 600; color: #92400e; text-transform: uppercase; letter-spacing: 0.5px;">Trigger Reason</p>
                                <p style="margin: 0; font-size: 15px; color: #78350f;">{trigger_reason}</p>
                            </div>
                        </td>
                    </tr>

                    <!-- Metrics -->
                    <tr>
                        <td style="padding: 0 32px 24px;">
                            <p style="margin: 0 0 12px; font-size: 14px; font-weight: 600; color: #374151;">Current Values</p>
                            <table role="presentation" style="width: 100%; background-color: #f9fafb; padding: 12px; border-radius: 8px;">
                                {metrics_rows}
                            </table>
                        </td>
                    </tr>

                    <!-- Info -->
                    <tr>
                        <td style="padding: 0 32px 24px;">
                            <p style="margin: 0; font-size: 14px; color: #6b7280; line-height: 1.6;">
                                The agent has been paused to protect your campaigns from potential issues.
                                Please review the performance data and decide whether to resume the agent.
                            </p>
                        </td>
                    </tr>

                    <!-- CTA Button -->
                    <tr>
                        <td style="padding: 0 32px 32px;">
                            <table role="presentation">
                                <tr>
                                    <td style="background-color: #111827; border-radius: 8px;">
                                        <a href="{dashboard_url}" style="display: inline-block; padding: 14px 28px; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none;">
                                            Review Agent &rarr;
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
    """

    return (
        EMAIL_HEADER.format(title=f"Safety Alert: {agent_name}") +
        content +
        EMAIL_FOOTER.format(dashboard_url=dashboard_url.rsplit('/agents', 1)[0])
    )


# =============================================================================
# NOTIFICATION SERVICE
# =============================================================================

@dataclass
class NotificationResult:
    """
    Result of sending a notification.

    Attributes:
        success: Whether notification was sent
        message_id: Provider message ID if successful
        error: Error message if failed
        recipients: List of recipients
    """

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    recipients: Optional[List[str]] = None


@dataclass
class ChannelResult:
    """
    Result of sending to a single notification channel.

    Attributes:
        channel_type: The channel type (email, slack, webhook)
        success: Whether notification was sent
        message_id: Provider message ID if successful
        error: Error message if failed
        details: Additional details about the result
    """

    channel_type: Literal["email", "slack", "webhook"]
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiChannelResult:
    """
    Result of sending to multiple notification channels.

    Attributes:
        overall_success: True if at least one channel succeeded
        channel_results: List of individual channel results
        total_channels: Number of channels attempted
        successful_channels: Number of successful channels
    """

    overall_success: bool
    channel_results: List[ChannelResult]
    total_channels: int = 0
    successful_channels: int = 0


class AgentNotificationService:
    """
    Service for sending agent-related notifications.

    WHAT: Sends emails for agent events via Resend
    WHY: Keep users informed about their agents

    Usage:
        service = AgentNotificationService.from_settings()
        await service.send_trigger_notification(...)
    """

    def __init__(
        self,
        resend_api_key: Optional[str] = None,
        from_email: str = "Metricx Agents <agents@metricx.ai>",
        dashboard_base_url: str = "https://www.metricx.ai",
    ):
        """
        Initialize notification service.

        Parameters:
            resend_api_key: Resend API key (optional for testing)
            from_email: From address for emails
            dashboard_base_url: Base URL for dashboard links
        """
        self.resend_api_key = resend_api_key
        self.from_email = from_email
        self.dashboard_base_url = dashboard_base_url.rstrip('/')

        # Initialize Resend client if API key provided
        self.resend_client = None
        if resend_api_key:
            try:
                import resend
                resend.api_key = resend_api_key
                self.resend_client = resend
                logger.info("[NotificationService] Resend client initialized")
            except ImportError:
                logger.warning("[NotificationService] Resend package not installed")

    @classmethod
    def from_settings(cls) -> "AgentNotificationService":
        """
        Create service instance from application settings.

        Returns:
            AgentNotificationService configured from environment
        """
        from ...deps import get_settings

        settings = get_settings()

        # Get dashboard URL from environment
        dashboard_url = os.getenv("FRONTEND_URL", "https://www.metricx.ai")

        return cls(
            resend_api_key=settings.RESEND_API_KEY,
            from_email=settings.RESEND_FROM_EMAIL,
            dashboard_base_url=dashboard_url,
        )

    async def send_trigger_notification(
        self,
        agent_id: str,
        agent_name: str,
        entity_name: str,
        entity_provider: str,
        condition_explanation: str,
        observations: Dict[str, float],
        action_results: List[Dict[str, Any]],
        recipients: List[str],
        workspace_id: str,
    ) -> NotificationResult:
        """
        Send notification when agent triggers.

        Parameters:
            agent_id: Agent UUID
            agent_name: Agent display name
            entity_name: Entity that triggered
            entity_provider: Platform (Meta, Google)
            condition_explanation: What condition was met
            observations: Current metric values
            action_results: Results of actions taken
            recipients: Email addresses to notify
            workspace_id: Workspace UUID

        Returns:
            NotificationResult
        """
        if not recipients:
            return NotificationResult(success=False, error="No recipients specified")

        # Generate the exciting headline for subject line
        headline, emoji, _ = _generate_trigger_headline(condition_explanation, observations)
        subject = f"{emoji} {headline} ({entity_name})"

        timestamp = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
        dashboard_url = f"{self.dashboard_base_url}/agents/{agent_id}"

        html_body = _build_trigger_email(
            agent_name=agent_name,
            entity_name=entity_name,
            entity_provider=entity_provider,
            condition_explanation=condition_explanation,
            observations=observations,
            action_results=action_results,
            dashboard_url=dashboard_url,
            timestamp=timestamp,
        )

        # Format metrics for text email
        def format_metric(k, v):
            if k in ["spend", "revenue", "cpc", "cpa"]:
                return f"  {k.upper()}: ${v:,.2f}"
            elif k in ["roas", "poas"]:
                return f"  {k.upper()}: {v:.2f}x"
            elif k in ["ctr", "cvr"]:
                return f"  {k.upper()}: {v:.2f}%"
            else:
                return f"  {k.upper()}: {v:,.0f}"

        metrics_text = chr(10).join(format_metric(k, v) for k, v in observations.items())
        actions_text = chr(10).join(
            f'  {"✓" if r.get("success") else "✗"} {r.get("description", "Action")}'
            for r in action_results
        ) or "  Notification sent"

        text_body = f"""
{emoji} {headline}

Campaign: {entity_name} ({entity_provider})
Agent: {agent_name}

{condition_explanation}

Current Metrics:
{metrics_text}

Actions Taken:
{actions_text}

View details: {dashboard_url}

— The Metricx Team
        """

        return await self._send_email(
            to=recipients,
            subject=subject,
            html=html_body,
            text=text_body,
        )

    async def send_error_notification(
        self,
        agent_id: str,
        agent_name: str,
        error_message: str,
        recipients: List[str],
        workspace_id: str,
    ) -> NotificationResult:
        """Send notification when agent encounters an error."""
        if not recipients:
            return NotificationResult(success=False, error="No recipients specified")

        subject = f"Agent '{agent_name}' encountered an error"
        timestamp = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
        dashboard_url = f"{self.dashboard_base_url}/agents/{agent_id}"

        html_body = _build_error_email(
            agent_name=agent_name,
            error_message=error_message,
            dashboard_url=dashboard_url,
            timestamp=timestamp,
        )

        text_body = f"""
Agent Error: {agent_name}

Your agent "{agent_name}" encountered an error during evaluation.

Error: {error_message[:500]}

The agent has been temporarily paused. Please review and fix the issue.

View agent: {dashboard_url}

— The Metricx Team
        """

        return await self._send_email(
            to=recipients,
            subject=subject,
            html=html_body,
            text=text_body,
        )

    async def send_stopped_notification(
        self,
        agent_id: str,
        agent_name: str,
        reason: str,
        recipients: List[str],
        workspace_id: str,
    ) -> NotificationResult:
        """Send notification when agent is automatically stopped."""
        if not recipients:
            return NotificationResult(success=False, error="No recipients specified")

        subject = f"Agent '{agent_name}' has been stopped"
        timestamp = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
        dashboard_url = f"{self.dashboard_base_url}/agents/{agent_id}"

        html_body = _build_stopped_email(
            agent_name=agent_name,
            reason=reason,
            dashboard_url=dashboard_url,
            timestamp=timestamp,
        )

        text_body = f"""
Agent Stopped: {agent_name}

Your agent "{agent_name}" has been automatically stopped.

Reason: {reason}

To resume monitoring, please fix the underlying issue and manually restart the agent.

View agent: {dashboard_url}

— The Metricx Team
        """

        return await self._send_email(
            to=recipients,
            subject=subject,
            html=html_body,
            text=text_body,
        )

    async def send_circuit_breaker_notification(
        self,
        agent_id: str,
        agent_name: str,
        entity_name: str,
        trigger_reason: str,
        metric_values: Dict[str, float],
        recipients: List[str],
        workspace_id: str,
    ) -> NotificationResult:
        """Send notification when circuit breaker trips."""
        if not recipients:
            return NotificationResult(success=False, error="No recipients specified")

        subject = f"Safety Alert: Agent '{agent_name}' circuit breaker triggered"
        timestamp = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
        dashboard_url = f"{self.dashboard_base_url}/agents/{agent_id}"

        html_body = _build_circuit_breaker_email(
            agent_name=agent_name,
            entity_name=entity_name,
            trigger_reason=trigger_reason,
            metric_values=metric_values,
            dashboard_url=dashboard_url,
            timestamp=timestamp,
        )

        text_body = f"""
Safety Alert: Circuit Breaker Triggered

Agent "{agent_name}" on {entity_name} has triggered a circuit breaker.

Trigger Reason: {trigger_reason}

Current Values:
{chr(10).join(f'  {k}: {v}' for k, v in metric_values.items())}

The agent has been paused to prevent further actions. Please review the performance and decide whether to resume.

Review agent: {dashboard_url}

— The Metricx Team
        """

        return await self._send_email(
            to=recipients,
            subject=subject,
            html=html_body,
            text=text_body,
        )

    async def _send_email(
        self,
        to: List[str],
        subject: str,
        html: str,
        text: str,
    ) -> NotificationResult:
        """
        Send email via Resend.

        Parameters:
            to: Recipients
            subject: Email subject
            html: HTML body
            text: Plain text body

        Returns:
            NotificationResult
        """
        if not self.resend_client:
            logger.warning(f"[NotificationService] Resend not configured, would send: {subject} to {to}")
            return NotificationResult(
                success=True,
                message_id="mock-" + str(hash(subject))[:8],
                recipients=to,
            )

        try:
            response = self.resend_client.Emails.send({
                "from": self.from_email,
                "to": to,
                "subject": subject,
                "html": html,
                "text": text,
            })

            message_id = response.get("id") if isinstance(response, dict) else getattr(response, "id", None)
            logger.info(f"[NotificationService] Email sent: {subject} to {to}, id={message_id}")

            return NotificationResult(
                success=True,
                message_id=message_id,
                recipients=to,
            )

        except Exception as e:
            logger.exception(f"[NotificationService] Failed to send email: {e}")
            return NotificationResult(
                success=False,
                error=str(e),
                recipients=to,
            )

    # =========================================================================
    # SLACK CHANNEL
    # =========================================================================

    async def _send_slack(
        self,
        webhook_url: str,
        payload: Dict[str, Any],
        channel_override: Optional[str] = None,
    ) -> ChannelResult:
        """
        Send message to Slack via incoming webhook.

        Parameters:
            webhook_url: Slack incoming webhook URL
            payload: Slack Block Kit payload
            channel_override: Optional channel override (e.g., '#alerts')

        Returns:
            ChannelResult
        """
        if not webhook_url:
            return ChannelResult(
                channel_type="slack",
                success=False,
                error="No webhook URL provided",
            )

        # Add channel override if specified
        if channel_override:
            payload["channel"] = channel_override

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200 and response.text == "ok":
                    logger.info(f"[NotificationService] Slack message sent successfully")
                    return ChannelResult(
                        channel_type="slack",
                        success=True,
                        message_id=f"slack-{hash(webhook_url) % 10000}",
                        details={"status_code": response.status_code},
                    )
                else:
                    error_msg = f"Slack API error: {response.status_code} - {response.text}"
                    logger.error(f"[NotificationService] {error_msg}")
                    return ChannelResult(
                        channel_type="slack",
                        success=False,
                        error=error_msg,
                        details={"status_code": response.status_code, "response": response.text},
                    )

        except httpx.TimeoutException:
            logger.error("[NotificationService] Slack webhook timeout")
            return ChannelResult(
                channel_type="slack",
                success=False,
                error="Request timeout",
            )
        except Exception as e:
            logger.exception(f"[NotificationService] Failed to send Slack message: {e}")
            return ChannelResult(
                channel_type="slack",
                success=False,
                error=str(e),
            )

    # =========================================================================
    # WEBHOOK CHANNEL
    # =========================================================================

    async def _send_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
    ) -> ChannelResult:
        """
        Send notification to custom HTTP webhook.

        Parameters:
            url: Webhook URL
            payload: JSON payload to send
            method: HTTP method (GET, POST, PUT)
            headers: Optional custom headers

        Returns:
            ChannelResult
        """
        if not url:
            return ChannelResult(
                channel_type="webhook",
                success=False,
                error="No webhook URL provided",
            )

        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=request_headers)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=payload, headers=request_headers)
                else:  # Default POST
                    response = await client.post(url, json=payload, headers=request_headers)

                is_success = 200 <= response.status_code < 300

                if is_success:
                    logger.info(f"[NotificationService] Webhook sent successfully to {url}")
                    return ChannelResult(
                        channel_type="webhook",
                        success=True,
                        message_id=f"webhook-{hash(url) % 10000}",
                        details={
                            "status_code": response.status_code,
                            "url": url,
                        },
                    )
                else:
                    error_msg = f"Webhook error: {response.status_code}"
                    logger.error(f"[NotificationService] {error_msg} for {url}")
                    return ChannelResult(
                        channel_type="webhook",
                        success=False,
                        error=error_msg,
                        details={
                            "status_code": response.status_code,
                            "url": url,
                            "response": response.text[:500],
                        },
                    )

        except httpx.TimeoutException:
            logger.error(f"[NotificationService] Webhook timeout for {url}")
            return ChannelResult(
                channel_type="webhook",
                success=False,
                error="Request timeout",
            )
        except Exception as e:
            logger.exception(f"[NotificationService] Failed to send webhook: {e}")
            return ChannelResult(
                channel_type="webhook",
                success=False,
                error=str(e),
            )

    # =========================================================================
    # MULTI-CHANNEL NOTIFICATION
    # =========================================================================

    async def send_multi_channel_notification(
        self,
        channels: List[Dict[str, Any]],
        agent_id: str,
        agent_name: str,
        entity_name: str,
        entity_provider: str,
        observations: Dict[str, float],
        condition_explanation: str,
        action_results: List[Dict[str, Any]],
        workspace_id: str,
        template_preset: str = "alert",
        custom_template: Optional[str] = None,
        date_range: str = "",
        start_date: str = "",
        end_date: str = "",
        event_type: str = "trigger",
    ) -> MultiChannelResult:
        """
        Send notification to multiple channels.

        This is the unified entry point for the NotifyAction.

        Parameters:
            channels: List of channel configurations (NotificationChannelConfig dicts)
            agent_id: Agent UUID
            agent_name: Agent display name
            entity_name: Entity display name
            entity_provider: Platform (Meta, Google, etc.)
            observations: Metric values
            condition_explanation: What condition was met
            action_results: Actions taken
            workspace_id: Workspace UUID
            template_preset: Template to use ('alert', 'daily_summary', 'digest')
            custom_template: Custom template text (if preset is 'custom')
            date_range: Date range string (for summaries)
            start_date: Period start (for digests)
            end_date: Period end (for digests)
            event_type: Event type label (trigger, report, etc.)

        Returns:
            MultiChannelResult with results for each channel
        """
        results: List[ChannelResult] = []
        dashboard_url = f"{self.dashboard_base_url}/agents/{agent_id}"

        # Generate headline for this notification
        headline, emoji, _ = _generate_trigger_headline(condition_explanation, observations)

        for channel_config in channels:
            if not channel_config.get("enabled", True):
                continue

            channel_type = channel_config.get("type")

            if channel_type == "email":
                # Use existing email flow
                recipients = channel_config.get("recipients", [])
                if recipients:
                    email_result = await self.send_trigger_notification(
                        agent_id=agent_id,
                        agent_name=agent_name,
                        entity_name=entity_name,
                        entity_provider=entity_provider,
                        condition_explanation=condition_explanation,
                        observations=observations,
                        action_results=action_results,
                        recipients=recipients,
                        workspace_id=workspace_id,
                    )
                    results.append(ChannelResult(
                        channel_type="email",
                        success=email_result.success,
                        message_id=email_result.message_id,
                        error=email_result.error,
                        details={"recipients": recipients},
                    ))

            elif channel_type == "slack":
                webhook_url = channel_config.get("webhook_url")
                channel_override = channel_config.get("channel")

                if webhook_url:
                    # Format Slack message using template
                    slack_payload = format_slack_message(
                        template_preset=template_preset,
                        agent_name=agent_name,
                        entity_name=entity_name,
                        observations=observations,
                        dashboard_url=dashboard_url,
                        entity_provider=entity_provider,
                        headline=headline,
                        condition_explanation=condition_explanation,
                        action_results=action_results,
                        date_range=date_range,
                        start_date=start_date,
                        end_date=end_date,
                        custom_template=custom_template or "",
                    )

                    slack_result = await self._send_slack(
                        webhook_url=webhook_url,
                        payload=slack_payload,
                        channel_override=channel_override,
                    )
                    results.append(slack_result)
                else:
                    results.append(ChannelResult(
                        channel_type="slack",
                        success=False,
                        error="No Slack webhook URL configured",
                    ))

            elif channel_type == "webhook":
                webhook_url = channel_config.get("url")
                method = channel_config.get("method", "POST")
                headers = channel_config.get("headers")

                if webhook_url:
                    # Build webhook payload with all the notification data
                    webhook_payload = {
                        "event": f"agent_{event_type}",
                        "event_type": event_type,
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "workspace_id": workspace_id,
                        "entity_name": entity_name,
                        "entity_provider": entity_provider,
                        "headline": headline,
                        "condition_explanation": condition_explanation,
                        "observations": observations,
                        "action_results": action_results,
                        "date_range": date_range,
                        "start_date": start_date,
                        "end_date": end_date,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "dashboard_url": dashboard_url,
                    }

                    webhook_result = await self._send_webhook(
                        url=webhook_url,
                        payload=webhook_payload,
                        method=method,
                        headers=headers,
                    )
                    results.append(webhook_result)
                else:
                    results.append(ChannelResult(
                        channel_type="webhook",
                        success=False,
                        error="No webhook URL configured",
                    ))

        # Calculate overall success
        successful = [r for r in results if r.success]

        return MultiChannelResult(
            overall_success=len(successful) > 0,
            channel_results=results,
            total_channels=len(results),
            successful_channels=len(successful),
        )

    async def send_slack_alert(
        self,
        webhook_url: str,
        agent_name: str,
        entity_name: str,
        entity_provider: str,
        headline: str,
        condition_explanation: str,
        observations: Dict[str, float],
        action_results: List[Dict[str, Any]],
        dashboard_url: str,
        channel_override: Optional[str] = None,
    ) -> ChannelResult:
        """
        Convenience method for sending a single Slack alert.

        Parameters:
            webhook_url: Slack incoming webhook URL
            agent_name: Agent display name
            entity_name: Entity that triggered
            entity_provider: Platform (Meta, Google, etc.)
            headline: Alert headline
            condition_explanation: What condition was met
            observations: Current metric values
            action_results: Results of actions taken
            dashboard_url: Link to agent in dashboard
            channel_override: Optional channel override

        Returns:
            ChannelResult
        """
        payload = format_slack_message(
            template_preset="alert",
            agent_name=agent_name,
            entity_name=entity_name,
            observations=observations,
            dashboard_url=dashboard_url,
            entity_provider=entity_provider,
            headline=headline,
            condition_explanation=condition_explanation,
            action_results=action_results,
        )

        return await self._send_slack(
            webhook_url=webhook_url,
            payload=payload,
            channel_override=channel_override,
        )
