"""
Slack Block Kit Message Formatter.

WHAT:
    Formats agent notifications as Slack Block Kit messages for
    beautiful, interactive notifications in Slack channels.

WHY:
    Users want notifications in Slack, not just email. Block Kit provides
    rich formatting with sections, buttons, and metrics tables.

DESIGN:
    - Template presets: alert, daily_summary, digest
    - Custom template support with variable substitution
    - Rich formatting with emojis, links, and structured data

REFERENCES:
    - Slack Block Kit: https://api.slack.com/block-kit
    - Incoming Webhooks: https://api.slack.com/messaging/webhooks
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _format_metric_value(key: str, value: float) -> str:
    """
    Format a metric value for display.

    Parameters:
        key: Metric name (e.g., 'spend', 'roas')
        value: Metric value

    Returns:
        Formatted string (e.g., '$1,234.56', '2.5x')
    """
    if key in ["spend", "revenue", "cpc", "cpa", "profit"]:
        return f"${value:,.2f}"
    elif key in ["roas", "poas"]:
        return f"{value:.2f}x"
    elif key in ["ctr", "cvr"]:
        return f"{value:.2f}%"
    else:
        return f"{value:,.0f}"


def _get_trigger_emoji_and_context(
    observations: Dict[str, float],
    condition_explanation: str,
) -> tuple[str, str]:
    """
    Determine emoji and context color based on the trigger nature.

    Returns:
        (emoji, context_message)
    """
    explanation_lower = condition_explanation.lower()

    # Detect positive vs negative trigger
    cost_metrics = ["spend", "cpc", "cpa"]
    is_cost_increase = any(m in explanation_lower for m in cost_metrics) and any(
        word in explanation_lower
        for word in ["limit", "exceeded", "crossed", "above", "increased"]
    )
    is_positive = not is_cost_increase and any(
        word in explanation_lower
        for word in ["above", "exceeded", "crossed", "reached", "increased"]
    )

    if is_positive:
        return ":tada:", "good"
    elif is_cost_increase:
        return ":warning:", "caution"
    else:
        return ":bell:", "info"


def format_alert_blocks(
    agent_name: str,
    entity_name: str,
    entity_provider: str,
    headline: str,
    condition_explanation: str,
    observations: Dict[str, float],
    action_results: List[Dict[str, Any]],
    dashboard_url: str,
) -> Dict[str, Any]:
    """
    Format an alert notification as Slack Block Kit.

    This is the primary notification format for real-time agent triggers.

    Parameters:
        agent_name: Display name of the agent
        entity_name: Campaign/ad/adset name
        entity_provider: Platform (Meta, Google, TikTok)
        headline: Main alert headline
        condition_explanation: What condition was met
        observations: Current metric values
        action_results: Results of actions taken
        dashboard_url: Link to agent in dashboard

    Returns:
        Slack Block Kit payload
    """
    emoji, _ = _get_trigger_emoji_and_context(observations, condition_explanation)

    # Build metrics fields (Slack mrkdwn format)
    metrics_fields = []
    for metric, value in observations.items():
        formatted = _format_metric_value(metric, value)
        metrics_fields.append({
            "type": "mrkdwn",
            "text": f"*{metric.upper()}*\n{formatted}"
        })

    # Build actions text
    actions_text = ""
    for result in action_results:
        status = ":white_check_mark:" if result.get("success") else ":x:"
        actions_text += f"{status} {result.get('description', 'Action executed')}\n"

    if not actions_text:
        actions_text = ":white_check_mark: Notification sent"

    blocks = [
        # Header with emoji and headline
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {headline}",
                "emoji": True
            }
        },
        # Context: entity and agent info
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f":package: *{entity_name}* ({entity_provider.upper()})"
                },
                {
                    "type": "mrkdwn",
                    "text": f":robot_face: Agent: {agent_name}"
                }
            ]
        },
        {"type": "divider"},
        # Condition explanation
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*What triggered:*\n{condition_explanation}"
            }
        },
        # Metrics (up to 10 fields in a section)
        {
            "type": "section",
            "fields": metrics_fields[:10]  # Slack limits to 10 fields
        },
        {"type": "divider"},
        # Actions taken
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Actions taken:*\n{actions_text}"
            }
        },
        # Button to dashboard
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Details",
                        "emoji": True
                    },
                    "url": dashboard_url,
                    "style": "primary"
                }
            ]
        },
        # Footer
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_Sent by Metricx at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"
                }
            ]
        }
    ]

    return {
        "blocks": blocks,
        "text": f"{headline} on {entity_name}"  # Fallback for notifications
    }


def format_daily_summary_blocks(
    agent_name: str,
    entity_name: str,
    observations: Dict[str, float],
    date_range: str,
    dashboard_url: str,
) -> Dict[str, Any]:
    """
    Format a daily summary report as Slack Block Kit.

    Parameters:
        agent_name: Display name of the agent
        entity_name: Campaign/ad/adset name (or "All Campaigns" for workspace)
        observations: Metric values for the period
        date_range: Human-readable date range (e.g., "Yesterday", "Last 7 days")
        dashboard_url: Link to dashboard

    Returns:
        Slack Block Kit payload
    """
    # Build metrics section
    metrics_lines = []
    for metric, value in observations.items():
        formatted = _format_metric_value(metric, value)
        metrics_lines.append(f"• *{metric.upper()}:* {formatted}")

    metrics_text = "\n".join(metrics_lines)

    blocks = [
        # Header
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":bar_chart: Daily Report - {date_range}",
                "emoji": True
            }
        },
        # Context
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f":robot_face: *{agent_name}*"
                }
            ]
        },
        {"type": "divider"},
        # Entity name section
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{entity_name}*"
            }
        },
        # Metrics
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": metrics_text
            }
        },
        {"type": "divider"},
        # Button
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Dashboard",
                        "emoji": True
                    },
                    "url": dashboard_url
                }
            ]
        },
        # Footer
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_Powered by Metricx_"
                }
            ]
        }
    ]

    return {
        "blocks": blocks,
        "text": f"Daily Report: {entity_name} - {date_range}"
    }


def format_digest_blocks(
    agent_name: str,
    entity_name: str,
    observations: Dict[str, float],
    start_date: str,
    end_date: str,
    dashboard_url: str,
) -> Dict[str, Any]:
    """
    Format a weekly/monthly digest as Slack Block Kit.

    Parameters:
        agent_name: Display name of the agent
        entity_name: Scope name (or "All Campaigns")
        observations: Aggregated metrics for the period
        start_date: Period start
        end_date: Period end
        dashboard_url: Link to report

    Returns:
        Slack Block Kit payload
    """
    # Build totals section with a table-like format
    totals_lines = []
    for metric, value in observations.items():
        formatted = _format_metric_value(metric, value)
        totals_lines.append(f"• *{metric.upper()}:* {formatted}")

    totals_text = "\n".join(totals_lines)

    blocks = [
        # Header
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":chart_with_upwards_trend: Performance Summary",
                "emoji": True
            }
        },
        # Date range
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_{start_date} - {end_date}_"
                }
            ]
        },
        {"type": "divider"},
        # Totals header
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Totals for {entity_name}:*"
            }
        },
        # Metrics
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": totals_text
            }
        },
        {"type": "divider"},
        # Button
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Full Report",
                        "emoji": True
                    },
                    "url": dashboard_url,
                    "style": "primary"
                }
            ]
        },
        # Footer
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_Generated by Metricx | Agent: {agent_name}_"
                }
            ]
        }
    ]

    return {
        "blocks": blocks,
        "text": f"Performance Summary: {entity_name} ({start_date} - {end_date})"
    }


def format_error_blocks(
    agent_name: str,
    error_message: str,
    dashboard_url: str,
) -> Dict[str, Any]:
    """
    Format an error notification as Slack Block Kit.

    Parameters:
        agent_name: Display name of the agent
        error_message: Error description
        dashboard_url: Link to agent settings

    Returns:
        Slack Block Kit payload
    """
    blocks = [
        # Header
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":warning: Agent Error",
                "emoji": True
            }
        },
        # Agent name
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{agent_name}* encountered an error"
            }
        },
        {"type": "divider"},
        # Error details
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```{error_message[:500]}```"
            }
        },
        # Info
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "The agent has been paused. Please review the configuration."
                }
            ]
        },
        # Button
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Review Agent"
                    },
                    "url": dashboard_url
                }
            ]
        }
    ]

    return {
        "blocks": blocks,
        "text": f"Agent Error: {agent_name}"
    }


def format_custom_template(
    template: str,
    variables: Dict[str, Any],
    dashboard_url: str,
) -> Dict[str, Any]:
    """
    Format a custom message template with variable substitution.

    Supports Mustache-like variables: {{variable_name}}

    Parameters:
        template: Message template with {{variables}}
        variables: Dictionary of variable values
        dashboard_url: Dashboard URL

    Returns:
        Slack Block Kit payload
    """
    # Simple variable substitution
    message = template
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        if isinstance(value, float):
            # Try to format nicely
            formatted = _format_metric_value(key, value)
        else:
            formatted = str(value)
        message = message.replace(placeholder, formatted)

    # Also replace {{dashboard_url}}
    message = message.replace("{{dashboard_url}}", dashboard_url)

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message
            }
        },
        # Button if dashboard URL provided
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Dashboard"
                    },
                    "url": dashboard_url
                }
            ]
        }
    ]

    return {
        "blocks": blocks,
        "text": message[:150]  # Fallback text (truncated)
    }


def format_slack_message(
    template_preset: str,
    agent_name: str,
    entity_name: str,
    observations: Dict[str, float],
    dashboard_url: str,
    entity_provider: str = "",
    headline: str = "",
    condition_explanation: str = "",
    action_results: Optional[List[Dict[str, Any]]] = None,
    date_range: str = "",
    start_date: str = "",
    end_date: str = "",
    error_message: str = "",
    custom_template: str = "",
) -> Dict[str, Any]:
    """
    Format a Slack message based on template preset.

    This is the main entry point for generating Slack messages.

    Parameters:
        template_preset: One of 'alert', 'daily_summary', 'digest', 'error', 'custom'
        agent_name: Agent display name
        entity_name: Entity display name
        observations: Metric values
        dashboard_url: Dashboard link
        entity_provider: Platform name (for alerts)
        headline: Main headline (for alerts)
        condition_explanation: What triggered (for alerts)
        action_results: Actions taken (for alerts)
        date_range: Date range string (for summaries)
        start_date: Period start (for digests)
        end_date: Period end (for digests)
        error_message: Error text (for error messages)
        custom_template: Custom template text

    Returns:
        Slack Block Kit payload ready to POST to webhook
    """
    if template_preset == "alert":
        return format_alert_blocks(
            agent_name=agent_name,
            entity_name=entity_name,
            entity_provider=entity_provider,
            headline=headline,
            condition_explanation=condition_explanation,
            observations=observations,
            action_results=action_results or [],
            dashboard_url=dashboard_url,
        )
    elif template_preset == "daily_summary":
        return format_daily_summary_blocks(
            agent_name=agent_name,
            entity_name=entity_name,
            observations=observations,
            date_range=date_range or "Yesterday",
            dashboard_url=dashboard_url,
        )
    elif template_preset == "digest":
        return format_digest_blocks(
            agent_name=agent_name,
            entity_name=entity_name,
            observations=observations,
            start_date=start_date or "Start",
            end_date=end_date or "End",
            dashboard_url=dashboard_url,
        )
    elif template_preset == "error":
        return format_error_blocks(
            agent_name=agent_name,
            error_message=error_message,
            dashboard_url=dashboard_url,
        )
    elif template_preset == "custom" and custom_template:
        # Build variables dict from all inputs
        variables = {
            "agent_name": agent_name,
            "entity_name": entity_name,
            "headline": headline,
            "condition_explanation": condition_explanation,
            "date_range": date_range,
            "start_date": start_date,
            "end_date": end_date,
            **observations,
        }
        return format_custom_template(
            template=custom_template,
            variables=variables,
            dashboard_url=dashboard_url,
        )
    else:
        # Fallback to alert format
        return format_alert_blocks(
            agent_name=agent_name,
            entity_name=entity_name,
            entity_provider=entity_provider or "Unknown",
            headline=headline or "Agent Triggered",
            condition_explanation=condition_explanation or "Condition met",
            observations=observations,
            action_results=action_results or [],
            dashboard_url=dashboard_url,
        )
