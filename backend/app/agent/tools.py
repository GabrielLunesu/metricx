"""
Agent Tools - Semantic Layer Wrappers
=====================================

**Version**: 1.0.0
**Created**: 2025-12-03

LangGraph tools that wrap the Semantic Layer for agent use.
The agent calls these tools to fetch data, and they return structured results.

WHY THIS FILE EXISTS
--------------------
LangGraph agents use tools to take actions. These tools wrap the Semantic Layer
so the agent can:
- Query metrics (query_metrics)
- Get entity lists (get_entities)
- Compare periods (compare_periods)
- Analyze changes (analyze_change)

Each tool is defined with a schema that Claude can understand and call.

SECURITY NOTE
-------------
These tools are ALREADY security-scoped:
- workspace_id is always passed from the agent state
- The Semantic Layer validates all inputs
- No raw SQL is ever executed

RELATED FILES
-------------
- app/semantic/compiler.py: What these tools call
- app/semantic/query.py: SemanticQuery structure
- app/agent/nodes.py: Agent nodes that call these tools
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.semantic import (
    SemanticQuery,
    SemanticCompiler,
    SemanticValidator,
    TimeRange,
    Breakdown,
    Comparison,
    ComparisonType,
    Filter,
)
from app.semantic.model import get_all_metric_names, METRICS

logger = logging.getLogger(__name__)


# =============================================================================
# TOOL SCHEMAS (for LLM function calling)
# =============================================================================

TOOL_SCHEMAS = {
    "query_metrics": {
        "name": "query_metrics",
        "description": """Query advertising metrics from the database.
Use this for questions about spend, revenue, ROAS, CPC, CTR, conversions, etc.

Examples:
- "What's my ROAS?" -> query_metrics(metrics=["roas"])
- "Total spend last week" -> query_metrics(metrics=["spend"], time_range="7d")
- "Top 5 campaigns by revenue" -> query_metrics(metrics=["revenue"], breakdown_level="campaign", limit=5)
- "Compare CPC this week vs last week" -> query_metrics(metrics=["cpc"], compare_to_previous=True)
""",
        "parameters": {
            "type": "object",
            "properties": {
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Metrics to query: spend, revenue, roas, cpc, ctr, cpa, clicks, impressions, conversions, profit, aov, cvr",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range: '1d' (today), '7d' (week), '30d' (month), '90d' (quarter). Default: 7d",
                },
                "breakdown_level": {
                    "type": "string",
                    "enum": ["campaign", "adset", "ad", "provider"],
                    "description": "Break down by entity level or platform",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of entities to return (for breakdown). Default: 5",
                },
                "compare_to_previous": {
                    "type": "boolean",
                    "description": "Compare to previous period (e.g., this week vs last week)",
                },
                "include_timeseries": {
                    "type": "boolean",
                    "description": "Include daily data for charts",
                },
                "filters": {
                    "type": "object",
                    "description": "Filters: {provider: 'meta'|'google', entity_name: 'Campaign Name'}",
                },
            },
            "required": ["metrics"],
        },
    },
    "get_entities": {
        "name": "get_entities",
        "description": """Get a list of campaigns, ad sets, or ads.
Use this to find specific entities by name or list all entities.

Examples:
- "List all campaigns" -> get_entities(level="campaign")
- "Find the Summer Sale campaign" -> get_entities(level="campaign", name_contains="Summer Sale")
""",
        "parameters": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["campaign", "adset", "ad"],
                    "description": "Entity level to query",
                },
                "name_contains": {
                    "type": "string",
                    "description": "Filter by name (case-insensitive substring match)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum entities to return. Default: 20",
                },
            },
            "required": ["level"],
        },
    },
    "analyze_change": {
        "name": "analyze_change",
        "description": """Analyze why a metric changed.
Use this for "why" questions about metric changes.

Examples:
- "Why is my ROAS down?" -> analyze_change(metric="roas", direction="down")
- "What caused the spend increase?" -> analyze_change(metric="spend", direction="up")
""",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": "Metric that changed: roas, spend, cpc, etc.",
                },
                "direction": {
                    "type": "string",
                    "enum": ["up", "down"],
                    "description": "Direction of change",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range to analyze. Default: 7d",
                },
            },
            "required": ["metric"],
        },
    },
}


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Get all tool schemas for LLM."""
    return list(TOOL_SCHEMAS.values())


# =============================================================================
# FREE AGENT TOOLS (OpenAI function calling format)
# =============================================================================
# These tools are used by the new free-form agent that lets the LLM decide
# what to call. The LLM sees ALL tools and picks the right one based on the
# question.
#
# KEY PRINCIPLE: Snapshots first, Live API only when needed
# - Snapshots are updated every 15 minutes
# - For metrics (spend, ROAS, etc.), ALWAYS use query_metrics first
# - For data not in snapshots (start_date, keywords), use live API
# =============================================================================

AGENT_TOOLS = [
    # ===================
    # SNAPSHOT DATA (Updated every 15 min - USE THIS FIRST for metrics)
    # ===================
    {
        "type": "function",
        "function": {
            "name": "query_metrics",
            "description": """Query advertising metrics from our database (snapshots updated every 15 minutes).

**USE THIS FIRST** for any metrics question. This is fast and doesn't hit external APIs.

RETURNS:
- Metrics data
- snapshot_time: When the data was last updated
- snapshot_age_minutes: How old the snapshot is

USE THIS FOR:
- Any spend, ROAS, CPC, etc. questions (even "today")
- Historical trends (this week, last month, etc.)
- Comparisons (this week vs last week)
- Aggregated metrics over time periods

AVAILABLE METRICS: spend, revenue, roas, cpc, ctr, cpa, clicks, impressions, conversions, profit

IMPORTANT: Always tell user the snapshot time in your response!
Example response: "Your spend today is $1,234 (based on data from 12:30 PM)"

EXAMPLE: "What's my spend today?" → query_metrics(metrics=["spend"], time_range="1d")""",
            "parameters": {
                "type": "object",
                "properties": {
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Metrics to query: spend, revenue, roas, cpc, ctr, cpa, clicks, impressions, conversions, profit",
                    },
                    "time_range": {
                        "type": "string",
                        "enum": ["1d", "7d", "14d", "30d", "90d"],
                        "description": "Time range. Default: 7d",
                    },
                    "breakdown_level": {
                        "type": "string",
                        "enum": ["campaign", "adset", "ad", "provider"],
                        "description": "Break down by entity level or platform",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of entities to return for breakdown. Default: 20. Max: 50. Use 50 for 'all' requests.",
                    },
                    "compare_to_previous": {
                        "type": "boolean",
                        "description": "Compare to previous period (this week vs last week)",
                    },
                    "include_timeseries": {
                        "type": "boolean",
                        "description": "Include daily data for charts",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Filters: {provider: 'meta'|'google', entity_name: 'Campaign Name'}",
                    },
                },
                "required": ["metrics"],
            },
        },
    },
    # ===================
    # LIVE GOOGLE ADS API (Use only when snapshots don't have the data)
    # ===================
    {
        "type": "function",
        "function": {
            "name": "google_ads_query",
            "description": """Query Google Ads API directly. **Only use when query_metrics can't answer.**

USE THIS FOR:
- Data NOT stored in snapshots:
  - Campaign start_date, end_date (for "went live yesterday")
  - Keywords (for "what keywords am I targeting")
  - Search terms (for "what did users search")
  - Audiences, targeting details
- User explicitly asks for "real-time" or "live" data
- When query_metrics returns stale data (>15 min) and user needs current

DO NOT USE FOR:
- Basic metrics (spend, ROAS, etc.) - use query_metrics first!
- General performance questions - use query_metrics first!

QUERY TYPES:
- campaigns: List campaigns with status, budget, start_date, end_date
- campaign_details: Full config for a specific campaign
- keywords: Search keywords (for Search campaigns)
- search_terms: What users actually searched
- ad_groups: Ad group details
- ads: Ad details and creatives
- metrics: Real-time metrics (only if user explicitly wants live)

IMPORTANT STATUS FILTER:
- For "live", "active", or "running" campaigns: use filters: {status: "ENABLED"}
- For "paused" campaigns: use filters: {status: "PAUSED"}
- Without status filter, returns BOTH enabled and paused campaigns

EXAMPLES:
- "What campaigns are live/active right now?" → google_ads_query(query_type="campaigns", filters={"status": "ENABLED"})
- "Which campaigns went live yesterday?" → google_ads_query(query_type="campaigns", filters={"start_date": "yesterday"})
- "Show all campaigns" → google_ads_query(query_type="campaigns")""",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": [
                            "campaigns",
                            "campaign_details",
                            "ad_groups",
                            "ads",
                            "keywords",
                            "search_terms",
                            "metrics",
                        ],
                        "description": "Type of data to query",
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Fields to fetch: name, status, start_date, end_date, budget, bid_strategy, etc.",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Filters: {status: 'ENABLED', start_date: 'yesterday', campaign_id: '123'}",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Specific entity ID for detail queries",
                    },
                    "date_range": {
                        "type": "string",
                        "enum": ["today", "yesterday", "last_7d", "last_30d"],
                        "description": "For metrics queries",
                    },
                },
                "required": ["query_type"],
            },
        },
    },
    # ===================
    # LIVE META ADS API (Use only when snapshots don't have the data)
    # ===================
    {
        "type": "function",
        "function": {
            "name": "meta_ads_query",
            "description": """Query Meta Ads API directly. **Only use when query_metrics can't answer.**

USE THIS FOR:
- Data NOT stored in snapshots:
  - Ad creative details (images, copy, CTAs)
  - Audience targeting information
  - Campaign objectives, optimization settings
- User explicitly asks for "real-time" or "live" data
- When query_metrics returns stale data (>15 min) and user needs current

DO NOT USE FOR:
- Basic metrics (spend, ROAS, etc.) - use query_metrics first!
- General performance questions - use query_metrics first!

QUERY TYPES:
- campaigns: List campaigns with status, budget, objective
- campaign_details: Full config for a specific campaign
- adsets: Ad set details with targeting
- ads: Ad details with creatives
- metrics: Real-time metrics (only if user explicitly wants live)

EXAMPLE: "What audiences am I targeting on Meta?" → meta_ads_query(query_type="adsets", fields=["targeting"])""",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": [
                            "campaigns",
                            "campaign_details",
                            "adsets",
                            "ads",
                            "metrics",
                        ],
                        "description": "Type of data to query",
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Fields to fetch: name, status, budget, objective, targeting, etc.",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Filters: {status: 'ACTIVE', campaign_id: '123'}",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Specific entity ID for detail queries",
                    },
                    "date_range": {
                        "type": "string",
                        "enum": ["today", "yesterday", "last_7d", "last_30d"],
                        "description": "For metrics queries",
                    },
                },
                "required": ["query_type"],
            },
        },
    },
    # ===================
    # ENTITY LISTING (from our database - fast)
    # ===================
    {
        "type": "function",
        "function": {
            "name": "list_entities",
            "description": """List campaigns, ad sets, or ads from our database.

USE THIS FOR:
- Finding entities by name
- Getting list of all campaigns/adsets/ads
- Quick lookups without hitting external APIs

NOTE: This uses cached data. For real-time status, use google_ads_query or meta_ads_query.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "string",
                        "enum": ["campaign", "adset", "ad"],
                        "description": "Entity level to query",
                    },
                    "name_contains": {
                        "type": "string",
                        "description": "Filter by name (case-insensitive)",
                    },
                    "provider": {
                        "type": "string",
                        "enum": ["google", "meta"],
                        "description": "Filter by ad platform",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max entities to return. Default: 20",
                    },
                },
                "required": ["level"],
            },
        },
    },
    # ===================
    # BUSINESS CONTEXT
    # ===================
    {
        "type": "function",
        "function": {
            "name": "get_business_context",
            "description": """Get the user's business profile information.

USE THIS FOR:
- Questions about company name, industry, target markets
- "What is my company?" "What industry am I in?"
- Personalizing responses with business context""",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    # ===================
    # AGENT MANAGEMENT (Autonomous monitoring agents)
    # ===================
    {
        "type": "function",
        "function": {
            "name": "list_agents",
            "description": """List the user's monitoring agents with their current status.

USE THIS FOR:
- "What agents do I have?"
- "Show me my active agents"
- "List all my monitoring rules"
- "Which agents are running?"

RETURNS:
- List of agents with: name, status (active/paused), last triggered, total triggers
- Brief summary of what each agent monitors""",
            "parameters": {
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "enum": ["active", "paused", "all"],
                        "description": "Filter by agent status. Default: all",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_agent_status",
            "description": """Get detailed status of a specific agent.

USE THIS FOR:
- "How is my ROAS agent doing?"
- "Status of the budget scaler"
- "Is my CPC alert working?"

RETURNS:
- Agent configuration summary
- Current state per monitored entity
- Recent evaluation history
- Last triggered time and reason""",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name or partial name of the agent to look up",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "UUID of the agent (if known)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_agent",
            "description": """Create a new monitoring agent from a natural language description.

ALWAYS call this tool when user wants to create/setup an agent or alert.
The tool returns a preview card - the UI handles confirmation, not you.

USE THIS FOR:
- "Alert me when ROAS drops below 2x"
- "Let me know if CPC goes above $3 on my Google campaigns"
- "Create an agent to monitor spend on Meta"
- "Setup a notification when conversions drop"

IMPORTANT: Just call the tool with the user's description. Do NOT ask for confirmation
in your response - the tool returns a visual preview card with Create/Edit buttons
that the user clicks to confirm. Your job is just to call the tool.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Natural language description of what the agent should do",
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["meta", "google", "all"],
                        "description": "Platform to monitor (optional, can be inferred from description)",
                    },
                    "campaign_name": {
                        "type": "string",
                        "description": "Specific campaign to monitor (optional)",
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "Set to true ONLY after user explicitly confirms. First call should be with confirmed=false to get preview.",
                    },
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pause_agent",
            "description": """Pause a running agent.

USE THIS FOR:
- "Pause my ROAS agent"
- "Stop the budget scaler"
- "Disable the CPC alert"

The agent will stop evaluating but configuration is preserved.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name or partial name of the agent to pause",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "UUID of the agent (if known)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional reason for pausing",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resume_agent",
            "description": """Resume a paused agent.

USE THIS FOR:
- "Resume my ROAS agent"
- "Start the budget scaler again"
- "Re-enable the CPC alert"

The agent will start evaluating again from its last state.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name or partial name of the agent to resume",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "UUID of the agent (if known)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_agent_behavior",
            "description": """Explain why an agent did or didn't trigger.

USE THIS FOR:
- "Why didn't my agents fire yesterday?" (explains ALL agents)
- "Why didn't my ROAS agent fire yesterday?" (explains specific agent)
- "What did the budget scaler do last week?"
- "Why was my CPC alert triggered?"

IMPORTANT: If user asks about "agents" (plural) or doesn't specify which agent,
call this WITHOUT agent_name/agent_id to get a summary of ALL agents.

RETURNS:
- If specific agent: detailed evaluation events with explanations
- If no agent specified: summary of ALL agents and their behavior""",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name or partial name of the agent. OMIT to explain ALL agents.",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "UUID of the agent (if known). OMIT to explain ALL agents.",
                    },
                    "time_range": {
                        "type": "string",
                        "enum": ["today", "yesterday", "last_7d", "last_30d"],
                        "description": "Time range to look at. Default: last_7d",
                    },
                    "question": {
                        "type": "string",
                        "description": "Specific question about the agent's behavior",
                    },
                },
            },
        },
    },
]


def get_agent_tools() -> List[Dict[str, Any]]:
    """Get tool schemas for the free-form agent (OpenAI function calling format)."""
    return AGENT_TOOLS


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================


@dataclass
class ToolContext:
    """Context passed to all tools."""

    db: Session
    workspace_id: str
    user_id: Optional[str] = None


class SemanticTools:
    """
    Tool implementations that wrap the Semantic Layer.

    WHAT: Provides tool methods that the agent can call.

    WHY: Encapsulates all data access in a clean interface.
    The agent doesn't need to know about SemanticQuery internals.

    USAGE:
        tools = SemanticTools(db, workspace_id)
        result = tools.query_metrics(metrics=["roas"], time_range="7d")
    """

    def __init__(self, db: Session, workspace_id: str, user_id: Optional[str] = None):
        """
        Initialize tools with database and context.

        PARAMETERS:
            db: SQLAlchemy session
            workspace_id: Current workspace UUID
            user_id: Current user UUID (optional)
        """
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.compiler = SemanticCompiler(db)
        self.validator = SemanticValidator()

    def query_metrics(
        self,
        metrics: List[str],
        time_range: str = "7d",
        breakdown_level: Optional[str] = None,
        limit: int = 20,
        compare_to_previous: bool = False,
        include_timeseries: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query metrics from the semantic layer.

        WHAT: Main tool for fetching metric data.

        WHY: Handles all metric queries - simple aggregates, breakdowns,
        comparisons, and timeseries. Single entry point for data.

        PARAMETERS:
            metrics: List of metric names (roas, spend, cpc, etc.)
            time_range: String like "7d", "30d", "1d"
            breakdown_level: Optional - "campaign", "adset", "ad", "provider"
            limit: Max entities for breakdown
            compare_to_previous: Compare to previous period
            include_timeseries: Include daily data points
            filters: Optional dict with provider, entity_name

        RETURNS:
            Dict with:
                - summary: Aggregate values
                - breakdown: Per-entity data (if breakdown_level)
                - comparison: Previous period data (if compare_to_previous)
                - timeseries: Daily points (if include_timeseries)
                - error: Error message if failed
        """
        logger.info(
            f"[TOOLS] query_metrics: {metrics}, range={time_range}, breakdown={breakdown_level}"
        )

        try:
            # Validate metrics
            valid_metrics = get_all_metric_names()
            for m in metrics:
                if m.lower() not in valid_metrics:
                    return {
                        "error": f"Unknown metric: {m}. Valid metrics: {', '.join(sorted(valid_metrics))}"
                    }

            # Parse time range
            days = self._parse_time_range(time_range)

            # Build SemanticQuery
            query = SemanticQuery(
                metrics=[m.lower() for m in metrics],
                time_range=TimeRange(last_n_days=days),
                include_timeseries=include_timeseries,
            )

            # Add breakdown if specified
            if breakdown_level:
                if breakdown_level == "provider":
                    query.breakdown = Breakdown(dimension="provider")
                else:
                    query.breakdown = Breakdown(
                        dimension="entity",
                        level=breakdown_level,
                        limit=limit,
                    )

            # Add comparison if specified
            if compare_to_previous:
                # Include previous period timeseries if timeseries is requested
                # This enables overlaid line charts for comparison queries
                query.comparison = Comparison(
                    type=ComparisonType.PREVIOUS_PERIOD,
                    include_timeseries=include_timeseries,
                )

            # Add filters if specified (only valid filter fields!)
            # Valid fields: provider, entity_name, level, status, entity_id
            if filters:
                if filters.get("provider") and filters["provider"] in [
                    "meta",
                    "google",
                    "tiktok",
                ]:
                    query.filters.append(
                        Filter(
                            field="provider",
                            operator="=",
                            value=filters["provider"],
                        )
                    )
                if filters.get("entity_name"):
                    query.filters.append(
                        Filter(
                            field="entity_name",
                            operator="contains",
                            value=filters["entity_name"],
                        )
                    )
                # Ignore any other filter fields (like conversions, spend, etc.)
                # These are metric values, not filter fields

            # Validate
            validation = self.validator.validate(query)
            if not validation.valid:
                return {"error": validation.to_user_message()}

            # Compile and execute
            result = self.compiler.compile(self.workspace_id, query)

            # Determine which providers contributed to this data
            # This helps the LLM correctly attribute data
            provider_filter = filters.get("provider") if filters else None
            if provider_filter:
                data_providers = [provider_filter]
            else:
                # Query which providers have active connections
                from app.models import Connection

                connections = (
                    self.db.query(Connection)
                    .filter(
                        Connection.workspace_id == self.workspace_id,
                        Connection.status == "active",
                    )
                    .all()
                )
                data_providers = [c.provider.value for c in connections]

            # Convert to dict
            result_dict = result.to_dict()

            # Generate pre-formatted text summary for LLM to use directly
            # This prevents LLM from misinterpreting or missing data
            formatted_summary = self._format_result_summary(
                result_dict, metrics, breakdown_level, data_providers
            )

            response = {
                "success": True,
                "query": query.to_dict(),
                "data": result_dict,
                "data_providers": data_providers,
                "data_providers_note": f"This data is from: {', '.join(data_providers) if data_providers else 'no connected providers'}. Do NOT attribute this data to any other provider.",
                "formatted_summary": formatted_summary,  # USE THIS IN YOUR RESPONSE - it's pre-formatted and accurate
            }
            return response

        except Exception as e:
            logger.exception(f"[TOOLS] query_metrics failed: {e}")
            return {"error": str(e)}

    def get_entities(
        self,
        level: str,
        name_contains: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Get list of entities (campaigns, ad sets, ads).

        WHAT: Lists entities with optional name filtering.

        WHY: Helps agent find specific campaigns/ads by name.

        PARAMETERS:
            level: "campaign", "adset", or "ad"
            name_contains: Optional substring to filter by
            limit: Max entities to return

        RETURNS:
            Dict with:
                - entities: List of {id, name, status}
                - error: Error message if failed
        """
        logger.info(f"[TOOLS] get_entities: level={level}, filter={name_contains}")

        try:
            # Build a simple breakdown query to get entity list
            query = SemanticQuery(
                metrics=["spend"],  # Use spend to get entities that have activity
                time_range=TimeRange(last_n_days=30),
                breakdown=Breakdown(
                    dimension="entity",
                    level=level,
                    limit=limit,
                ),
            )

            if name_contains:
                query.filters.append(
                    Filter(
                        field="entity_name",
                        operator="contains",
                        value=name_contains,
                    )
                )

            result = self.compiler.compile(self.workspace_id, query)

            entities = []
            for item in result.breakdown:
                entities.append(
                    {
                        "id": item.entity_id,
                        "name": item.label,
                        "spend": item.spend,
                    }
                )

            return {
                "success": True,
                "entities": entities,
                "count": len(entities),
            }

        except Exception as e:
            logger.exception(f"[TOOLS] get_entities failed: {e}")
            return {"error": str(e)}

    def analyze_change(
        self,
        metric: str,
        direction: Optional[str] = None,
        time_range: str = "7d",
    ) -> Dict[str, Any]:
        """
        Analyze why a metric changed.

        WHAT: Compares current vs previous period and finds contributing factors.

        WHY: Answers "why" questions by looking at what changed.

        ALGORITHM:
            1. Get overall metric change (this period vs last)
            2. Get per-entity breakdown for both periods
            3. Find entities with largest contribution to change
            4. Return analysis

        PARAMETERS:
            metric: Metric to analyze
            direction: Expected direction ("up" or "down")
            time_range: Time range to analyze

        RETURNS:
            Dict with:
                - change_pct: Overall percentage change
                - direction: "up" or "down"
                - top_contributors: Entities that contributed most to change
                - analysis: Human-readable summary
        """
        logger.info(f"[TOOLS] analyze_change: {metric}, direction={direction}")

        try:
            days = self._parse_time_range(time_range)

            # Get comparison data
            query = SemanticQuery(
                metrics=[metric.lower()],
                time_range=TimeRange(last_n_days=days),
                comparison=Comparison(type=ComparisonType.PREVIOUS_PERIOD),
                breakdown=Breakdown(dimension="entity", level="campaign", limit=10),
            )

            result = self.compiler.compile(self.workspace_id, query)
            result_dict = result.to_dict()

            # Extract change info
            summary = result_dict.get("summary", {})
            metric_data = summary.get(metric.lower(), {})
            change_pct = metric_data.get("delta_pct")

            if change_pct is None:
                return {
                    "success": True,
                    "analysis": f"No change data available for {metric}. This might mean there's no data for the comparison period.",
                }

            actual_direction = "up" if change_pct > 0 else "down"
            change_str = f"{abs(change_pct) * 100:.1f}%"

            # Find top contributors from entity comparison
            entity_comparison = result_dict.get("entity_comparison", [])
            contributors = []
            for item in entity_comparison[:5]:
                if item.get("delta_pct") is not None:
                    item_dir = "up" if item["delta_pct"] > 0 else "down"
                    contributors.append(
                        {
                            "name": item["entity_name"],
                            "change_pct": item["delta_pct"],
                            "direction": item_dir,
                            "current": item["current_value"],
                            "previous": item["previous_value"],
                        }
                    )

            return {
                "success": True,
                "metric": metric,
                "change_pct": change_pct,
                "direction": actual_direction,
                "change_str": change_str,
                "top_contributors": contributors,
                "data": result_dict,
            }

        except Exception as e:
            logger.exception(f"[TOOLS] analyze_change failed: {e}")
            return {"error": str(e)}

    def _format_result_summary(
        self,
        result_dict: Dict[str, Any],
        metrics: List[str],
        breakdown_level: Optional[str],
        data_providers: List[str],
    ) -> str:
        """
        Generate a pre-formatted text summary of the query results.

        This ensures the LLM has an accurate, complete summary to use
        rather than interpreting raw data (which can lead to errors).

        RETURNS:
            Human-readable summary string that the LLM should use verbatim.
        """
        lines = []

        # Get summary data
        summary = result_dict.get("summary", {})
        breakdown = result_dict.get("breakdown", [])
        time_range = result_dict.get("time_range_resolved", {})

        start_date = time_range.get("start", "")
        end_date = time_range.get("end", "")
        date_range_str = (
            f"({start_date} to {end_date})" if start_date and end_date else ""
        )

        provider_str = ", ".join(data_providers) if data_providers else "all providers"

        # Format summary metrics
        if summary:
            metric_parts = []
            for metric in metrics:
                metric_data = summary.get(metric, {})
                value = metric_data.get("value")
                if value is not None:
                    if metric in ["spend", "revenue", "profit", "cpc", "cpa"]:
                        metric_parts.append(f"{metric}: ${value:,.2f}")
                    elif metric in ["roas"]:
                        metric_parts.append(f"{metric}: {value:.2f}x")
                    elif metric in ["ctr"]:
                        metric_parts.append(f"{metric}: {value:.2%}")
                    else:
                        metric_parts.append(f"{metric}: {value:,.0f}")

            if metric_parts:
                lines.append(f"TOTALS {date_range_str}: {', '.join(metric_parts)}")

        # Format breakdown if present
        if breakdown and breakdown_level:
            lines.append(
                f"\n{breakdown_level.upper()} BREAKDOWN ({len(breakdown)} total):"
            )

            for i, item in enumerate(breakdown, 1):
                name = (
                    item.get("label")
                    or item.get("name")
                    or item.get("entity_name")
                    or "Unknown"
                )

                # Format each metric for this entity
                item_metrics = []
                for metric in metrics:
                    value = item.get(metric)
                    if value is not None:
                        if metric in ["spend", "revenue", "profit", "cpc", "cpa"]:
                            item_metrics.append(f"{metric}: ${value:,.2f}")
                        elif metric in ["roas"]:
                            item_metrics.append(f"{metric}: {value:.2f}x")
                        elif metric in ["ctr"]:
                            item_metrics.append(f"{metric}: {value:.2%}")
                        else:
                            item_metrics.append(f"{metric}: {value:,.0f}")

                metrics_str = ", ".join(item_metrics) if item_metrics else "no data"
                lines.append(f"  {i}. {name}: {metrics_str}")

        lines.append(f"\nData source: {provider_str}")

        return "\n".join(lines)

    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to days."""
        if time_range.endswith("d"):
            try:
                return int(time_range[:-1])
            except ValueError:
                pass

        # Common aliases
        aliases = {
            "today": 1,
            "yesterday": 1,
            "week": 7,
            "month": 30,
            "quarter": 90,
            "year": 365,
        }
        return aliases.get(time_range, 7)


# =============================================================================
# AGENT MANAGEMENT TOOLS
# =============================================================================


class AgentManagementTools:
    """
    Tool implementations for managing autonomous monitoring agents.

    WHAT: Provides copilot tools to list, create, pause, resume agents
    and explain their behavior.

    WHY: Enables natural language agent management through Copilot.
    Users can say "alert me when ROAS drops below 2" and we create the agent.
    """

    def __init__(self, db: Session, workspace_id: str, user_id: Optional[str] = None):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    def list_agents(
        self,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List user's monitoring agents.

        RETURNS:
            Dict with list of agents and their status summaries.
        """
        from app.models import Agent, AgentStatusEnum

        logger.info(f"[AGENT_TOOLS] list_agents: status={status_filter}")

        try:
            query = self.db.query(Agent).filter(
                Agent.workspace_id == self.workspace_id
            )

            if status_filter and status_filter != "all":
                try:
                    status_enum = AgentStatusEnum(status_filter)
                    query = query.filter(Agent.status == status_enum)
                except ValueError:
                    pass

            agents = query.order_by(Agent.created_at.desc()).limit(50).all()

            agent_list = []
            for agent in agents:
                # Build condition summary
                condition = agent.condition or {}
                condition_summary = self._summarize_condition(condition)

                # Build scope summary
                scope_config = agent.scope_config or {}
                scope_summary = self._summarize_scope(agent.scope_type, scope_config)

                agent_list.append({
                    "id": str(agent.id),
                    "name": agent.name,
                    "status": agent.status.value if agent.status else "unknown",
                    "description": agent.description,
                    "condition_summary": condition_summary,
                    "scope_summary": scope_summary,
                    "last_evaluated_at": agent.last_evaluated_at.isoformat() if agent.last_evaluated_at else None,
                    "last_triggered_at": agent.last_triggered_at.isoformat() if agent.last_triggered_at else None,
                    "total_triggers": agent.total_triggers or 0,
                    "total_evaluations": agent.total_evaluations or 0,
                })

            return {
                "success": True,
                "agents": agent_list,
                "count": len(agent_list),
                "summary": f"You have {len(agent_list)} agent(s)" + (
                    f" ({status_filter})" if status_filter and status_filter != "all" else ""
                ),
            }

        except Exception as e:
            logger.exception(f"[AGENT_TOOLS] list_agents failed: {e}")
            return {"error": str(e)}

    def get_agent_status(
        self,
        agent_name: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed status of a specific agent.
        """
        from app.models import Agent, AgentEntityState, AgentEvaluationEvent

        logger.info(f"[AGENT_TOOLS] get_agent_status: name={agent_name}, id={agent_id}")

        try:
            agent = self._find_agent(agent_name, agent_id)
            if not agent:
                return {"error": f"Agent not found: {agent_name or agent_id}"}

            # Get entity states
            entity_states = self.db.query(AgentEntityState).filter(
                AgentEntityState.agent_id == agent.id
            ).all()

            # Get recent events
            recent_events = self.db.query(AgentEvaluationEvent).filter(
                AgentEvaluationEvent.agent_id == agent.id
            ).order_by(AgentEvaluationEvent.evaluated_at.desc()).limit(5).all()

            # Build status summary
            states_summary = []
            for state in entity_states:
                states_summary.append({
                    "entity_id": str(state.entity_id),
                    "state": state.state.value if state.state else "unknown",
                    "accumulation_count": state.accumulation_count or 0,
                    "trigger_count": state.trigger_count or 0,
                })

            events_summary = []
            for event in recent_events:
                events_summary.append({
                    "evaluated_at": event.evaluated_at.isoformat() if event.evaluated_at else None,
                    "result_type": event.result_type,
                    "headline": event.headline,
                    "entity_name": event.entity_name,
                    "condition_result": event.condition_result,
                    "should_trigger": event.should_trigger,
                })

            return {
                "success": True,
                "agent": {
                    "id": str(agent.id),
                    "name": agent.name,
                    "status": agent.status.value if agent.status else "unknown",
                    "description": agent.description,
                    "condition": agent.condition,
                    "condition_summary": self._summarize_condition(agent.condition or {}),
                    "scope_summary": self._summarize_scope(agent.scope_type, agent.scope_config or {}),
                    "last_evaluated_at": agent.last_evaluated_at.isoformat() if agent.last_evaluated_at else None,
                    "last_triggered_at": agent.last_triggered_at.isoformat() if agent.last_triggered_at else None,
                    "total_triggers": agent.total_triggers or 0,
                    "total_evaluations": agent.total_evaluations or 0,
                },
                "entity_states": states_summary,
                "recent_events": events_summary,
            }

        except Exception as e:
            logger.exception(f"[AGENT_TOOLS] get_agent_status failed: {e}")
            return {"error": str(e)}

    def create_agent(
        self,
        description: str,
        platform: Optional[str] = None,
        campaign_name: Optional[str] = None,
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new agent from natural language description.

        When confirmed=False (default): Returns a PREVIEW of what will be created.
        When confirmed=True: Actually creates the agent.

        This two-step process ensures users confirm before agents are created.
        """
        from app.models import Agent, AgentStatusEnum, User
        import re

        logger.info(f"[AGENT_TOOLS] create_agent: {description}, confirmed={confirmed}")

        try:
            # Parse the natural language description
            parsed = self._parse_agent_description(description)

            if not parsed.get("metric"):
                return {
                    "error": "Couldn't understand what metric to monitor. Try something like 'alert me when ROAS drops below 2' or 'notify me if CPC goes above $3'"
                }

            # Map symbolic operators to named operators (ThresholdCondition expects gt/lt/etc)
            operator_map = {
                "<": "lt",
                "<=": "lte",
                ">": "gt",
                ">=": "gte",
                "=": "eq",
                "==": "eq",
                "!=": "neq",
            }
            raw_operator = parsed.get("operator", "<")
            named_operator = operator_map.get(raw_operator, raw_operator)

            # Build condition
            condition = {
                "type": "threshold",
                "metric": parsed["metric"],
                "operator": named_operator,
                "value": parsed.get("value", 0),
            }

            # Build scope config
            scope_type = "all"
            scope_config = {
                "level": "campaign",
                # AGGREGATE MODE: Evaluate totals across all campaigns, not each individually
                # This means "alert when spend > $50" checks TOTAL spend, not per-campaign
                "aggregate": True,
            }

            # Apply platform filter
            inferred_platform = platform or parsed.get("platform")
            if inferred_platform and inferred_platform != "all":
                scope_config["provider"] = inferred_platform

            # If specific campaign mentioned, use filter scope (NOT aggregate)
            if campaign_name or parsed.get("campaign_name"):
                scope_type = "filter"
                scope_config["entity_name_contains"] = campaign_name or parsed.get("campaign_name")
                scope_config["aggregate"] = False  # Specific campaign = individual evaluation

            # Generate agent name if not provided
            agent_name = parsed.get("name") or self._generate_agent_name(condition, scope_config)

            # If not confirmed, return preview for user to approve
            if not confirmed:
                condition_summary = self._summarize_condition(condition)
                scope_summary = self._summarize_scope(scope_type, scope_config)

                return {
                    "success": True,
                    "preview": True,
                    "requires_confirmation": True,
                    "message": "Here's what I'll create. Please confirm to proceed.",
                    "agent_preview": {
                        "name": agent_name,
                        "condition": condition_summary,
                        "scope": scope_summary,
                        "action": "Email notification when triggered",
                        "frequency": "Evaluates every 15 minutes",
                    },
                    "confirmation_prompt": f"I'll create an agent called '{agent_name}' that will {condition_summary.lower()} across {scope_summary.lower()}. You'll receive an email when it triggers. Should I create this?",
                }

            # Build email action
            actions = [{
                "type": "email",
                "config": {
                    "subject_template": f"🎯 {agent_name} triggered on {{{{entity_name}}}}",
                    "body_template": f"Your agent '{agent_name}' has triggered.\n\nCondition: {parsed['metric']} {parsed.get('operator', '<')} {parsed.get('value', 0)}\n\nCheck your dashboard for details.",
                }
            }]

            # Get user for created_by
            user = self.db.query(User).filter(User.id == self.user_id).first() if self.user_id else None

            # Create the agent
            agent = Agent(
                workspace_id=self.workspace_id,
                name=agent_name,
                description=f"Created via Copilot: {description}",
                scope_type=scope_type,
                scope_config=scope_config,
                condition=condition,
                accumulation_required=1,
                accumulation_unit="evaluations",
                accumulation_mode="consecutive",
                trigger_mode="once",
                actions=actions,
                status=AgentStatusEnum.active,
                created_by=user.id if user else None,
            )

            self.db.add(agent)
            self.db.commit()
            self.db.refresh(agent)

            return {
                "success": True,
                "message": f"Created agent '{agent_name}'",
                "agent": {
                    "id": str(agent.id),
                    "name": agent.name,
                    "status": "active",
                    "condition_summary": self._summarize_condition(condition),
                    "scope_summary": self._summarize_scope(scope_type, scope_config),
                },
                "note": "The agent is now active and will evaluate every 15 minutes. You'll receive an email when it triggers.",
            }

        except Exception as e:
            logger.exception(f"[AGENT_TOOLS] create_agent failed: {e}")
            self.db.rollback()
            return {"error": str(e)}

    def pause_agent(
        self,
        agent_name: Optional[str] = None,
        agent_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Pause a running agent."""
        from app.models import Agent, AgentStatusEnum

        logger.info(f"[AGENT_TOOLS] pause_agent: name={agent_name}, id={agent_id}")

        try:
            agent = self._find_agent(agent_name, agent_id)
            if not agent:
                return {"error": f"Agent not found: {agent_name or agent_id}"}

            if agent.status == AgentStatusEnum.paused:
                return {
                    "success": True,
                    "message": f"Agent '{agent.name}' is already paused",
                    "agent_id": str(agent.id),
                }

            agent.status = AgentStatusEnum.paused
            self.db.commit()

            return {
                "success": True,
                "message": f"Paused agent '{agent.name}'" + (f" (reason: {reason})" if reason else ""),
                "agent_id": str(agent.id),
                "agent_name": agent.name,
            }

        except Exception as e:
            logger.exception(f"[AGENT_TOOLS] pause_agent failed: {e}")
            self.db.rollback()
            return {"error": str(e)}

    def resume_agent(
        self,
        agent_name: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resume a paused agent."""
        from app.models import Agent, AgentStatusEnum

        logger.info(f"[AGENT_TOOLS] resume_agent: name={agent_name}, id={agent_id}")

        try:
            agent = self._find_agent(agent_name, agent_id)
            if not agent:
                return {"error": f"Agent not found: {agent_name or agent_id}"}

            if agent.status == AgentStatusEnum.active:
                return {
                    "success": True,
                    "message": f"Agent '{agent.name}' is already active",
                    "agent_id": str(agent.id),
                }

            agent.status = AgentStatusEnum.active
            self.db.commit()

            return {
                "success": True,
                "message": f"Resumed agent '{agent.name}'. It will evaluate on the next cycle (every 15 minutes).",
                "agent_id": str(agent.id),
                "agent_name": agent.name,
            }

        except Exception as e:
            logger.exception(f"[AGENT_TOOLS] resume_agent failed: {e}")
            self.db.rollback()
            return {"error": str(e)}

    def explain_agent_behavior(
        self,
        agent_name: Optional[str] = None,
        agent_id: Optional[str] = None,
        time_range: str = "last_7d",
        question: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Explain why an agent did or didn't trigger.

        Queries evaluation events and provides human-readable explanations.
        If no agent specified, explains behavior for ALL agents.
        """
        from app.models import Agent, AgentEvaluationEvent
        from datetime import datetime, timedelta

        logger.info(f"[AGENT_TOOLS] explain_agent_behavior: name={agent_name}, range={time_range}")

        try:
            # If no agent specified, explain ALL agents
            if not agent_name and not agent_id:
                return self._explain_all_agents_behavior(time_range)

            agent = self._find_agent(agent_name, agent_id)
            if not agent:
                return {"error": f"Agent not found: {agent_name or agent_id}"}

            # Determine date range
            days_map = {
                "today": 1,
                "yesterday": 2,
                "last_7d": 7,
                "last_30d": 30,
            }
            days = days_map.get(time_range, 7)
            since = datetime.utcnow() - timedelta(days=days)

            # Get evaluation events
            events = self.db.query(AgentEvaluationEvent).filter(
                AgentEvaluationEvent.agent_id == agent.id,
                AgentEvaluationEvent.evaluated_at >= since,
            ).order_by(AgentEvaluationEvent.evaluated_at.desc()).limit(20).all()

            if not events:
                return {
                    "success": True,
                    "agent_name": agent.name,
                    "explanation": f"No evaluations found for '{agent.name}' in the {time_range} period. This could mean:\n"
                                   f"1. The agent was just created\n"
                                   f"2. The agent is paused (current status: {agent.status.value if agent.status else 'unknown'})\n"
                                   f"3. No entities match the agent's scope",
                    "events": [],
                }

            # Build explanation
            trigger_count = sum(1 for e in events if e.should_trigger)
            condition_met_count = sum(1 for e in events if e.condition_result)

            events_summary = []
            for event in events[:10]:  # Top 10 most recent
                events_summary.append({
                    "time": event.evaluated_at.isoformat() if event.evaluated_at else None,
                    "entity": event.entity_name,
                    "result": event.result_type,
                    "headline": event.headline,
                    "condition_met": event.condition_result,
                    "triggered": event.should_trigger,
                    "explanation": event.condition_explanation,
                })

            explanation_lines = [
                f"**Agent: {agent.name}**",
                f"**Period: {time_range}** ({len(events)} evaluations)",
                f"**Condition: {self._summarize_condition(agent.condition or {})}**",
                "",
                f"📊 **Summary:**",
                f"- Total evaluations: {len(events)}",
                f"- Condition met: {condition_met_count} times",
                f"- Triggered actions: {trigger_count} times",
            ]

            if trigger_count == 0 and condition_met_count == 0:
                explanation_lines.append("\n⚠️ The condition was never met during this period.")
                explanation_lines.append("This means the monitored metric stayed within acceptable bounds.")
            elif trigger_count == 0 and condition_met_count > 0:
                explanation_lines.append("\n⚠️ Condition was met but agent didn't trigger.")
                explanation_lines.append("This could be due to accumulation requirements or cooldown settings.")

            return {
                "success": True,
                "agent_name": agent.name,
                "explanation": "\n".join(explanation_lines),
                "events": events_summary,
                "stats": {
                    "total_evaluations": len(events),
                    "condition_met": condition_met_count,
                    "triggered": trigger_count,
                },
            }

        except Exception as e:
            logger.exception(f"[AGENT_TOOLS] explain_agent_behavior failed: {e}")
            return {"error": str(e)}

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _explain_all_agents_behavior(self, time_range: str = "last_7d") -> Dict[str, Any]:
        """
        Explain behavior for ALL agents when no specific agent is mentioned.

        WHY: Users often ask "why didn't my agents fire?" without specifying which one.
        """
        from app.models import Agent, AgentEvaluationEvent
        from datetime import datetime, timedelta

        # Determine date range
        days_map = {
            "today": 1,
            "yesterday": 2,
            "last_7d": 7,
            "last_30d": 30,
        }
        days = days_map.get(time_range, 7)
        since = datetime.utcnow() - timedelta(days=days)

        # Get all agents
        agents = self.db.query(Agent).filter(
            Agent.workspace_id == self.workspace_id
        ).order_by(Agent.created_at.desc()).limit(20).all()

        if not agents:
            return {
                "success": True,
                "explanation": "You don't have any agents set up yet. Would you like me to create one? Just tell me what you want to monitor, like 'alert me when ROAS drops below 2'.",
                "agents": [],
            }

        # Build summary for each agent
        agents_summary = []
        total_triggers = 0
        total_evaluations = 0

        for agent in agents:
            # Get events for this agent
            events = self.db.query(AgentEvaluationEvent).filter(
                AgentEvaluationEvent.agent_id == agent.id,
                AgentEvaluationEvent.evaluated_at >= since,
            ).all()

            trigger_count = sum(1 for e in events if e.should_trigger)
            condition_met_count = sum(1 for e in events if e.condition_result)

            total_triggers += trigger_count
            total_evaluations += len(events)

            # Determine status explanation
            if agent.status.value == "paused":
                status_note = "⏸️ Paused - not evaluating"
            elif len(events) == 0:
                status_note = "⚠️ No evaluations - may be newly created or no matching entities"
            elif trigger_count > 0:
                status_note = f"✅ Triggered {trigger_count} time(s)"
            elif condition_met_count > 0:
                status_note = f"🔄 Condition met {condition_met_count}x but accumulation not reached"
            else:
                status_note = "✓ Monitoring - condition not met (metrics within bounds)"

            agents_summary.append({
                "name": agent.name,
                "status": agent.status.value if agent.status else "unknown",
                "condition": self._summarize_condition(agent.condition or {}),
                "scope": self._summarize_scope(agent.scope_type, agent.scope_config or {}),
                "evaluations": len(events),
                "condition_met": condition_met_count,
                "triggered": trigger_count,
                "status_note": status_note,
            })

        # Build explanation text
        explanation_lines = [
            f"**Agent Summary ({time_range})**",
            f"You have {len(agents)} agent(s). Here's what happened:",
            "",
        ]

        for i, agent_info in enumerate(agents_summary, 1):
            explanation_lines.append(f"**{i}. {agent_info['name']}** ({agent_info['status']})")
            explanation_lines.append(f"   Watches: {agent_info['scope']}")
            explanation_lines.append(f"   Condition: {agent_info['condition']}")
            explanation_lines.append(f"   {agent_info['status_note']}")
            explanation_lines.append("")

        if total_triggers == 0:
            explanation_lines.append("📊 **None of your agents triggered** during this period.")
            explanation_lines.append("This means all monitored metrics stayed within your defined thresholds.")
        else:
            explanation_lines.append(f"📊 **Total: {total_triggers} trigger(s)** across {total_evaluations} evaluations.")

        return {
            "success": True,
            "explanation": "\n".join(explanation_lines),
            "agents": agents_summary,
            "stats": {
                "total_agents": len(agents),
                "total_evaluations": total_evaluations,
                "total_triggers": total_triggers,
            },
        }

    def _find_agent(
        self,
        agent_name: Optional[str],
        agent_id: Optional[str],
    ):
        """Find an agent by name or ID."""
        from app.models import Agent
        import uuid as uuid_module

        if agent_id:
            try:
                uid = uuid_module.UUID(agent_id)
                return self.db.query(Agent).filter(
                    Agent.id == uid,
                    Agent.workspace_id == self.workspace_id,
                ).first()
            except ValueError:
                pass

        if agent_name:
            # Try exact match first
            agent = self.db.query(Agent).filter(
                Agent.workspace_id == self.workspace_id,
                Agent.name.ilike(agent_name),
            ).first()

            if agent:
                return agent

            # Try partial match
            return self.db.query(Agent).filter(
                Agent.workspace_id == self.workspace_id,
                Agent.name.ilike(f"%{agent_name}%"),
            ).first()

        return None

    def _summarize_condition(self, condition: Dict) -> str:
        """Generate human-readable summary of a condition."""
        cond_type = condition.get("type", "unknown")

        if cond_type == "threshold":
            metric = condition.get("metric", "metric")
            operator = condition.get("operator", "lt")
            value = condition.get("value", 0)

            # Handle both symbolic (<, >) and named (lt, gt) operators
            op_text = {
                "<": "drops below",
                "<=": "drops to or below",
                ">": "goes above",
                ">=": "goes to or above",
                "==": "equals",
                "lt": "drops below",
                "lte": "drops to or below",
                "gt": "goes above",
                "gte": "goes to or above",
                "eq": "equals",
                "neq": "is not equal to",
            }.get(operator, operator)

            # Format value based on metric
            if metric in ["roas"]:
                value_str = f"{value}x"
            elif metric in ["spend", "revenue", "cpc", "cpa"]:
                value_str = f"${value}"
            elif metric in ["ctr"]:
                value_str = f"{value}%"
            else:
                value_str = str(value)

            return f"When {metric.upper()} {op_text} {value_str}"

        elif cond_type == "composite":
            sub_conditions = condition.get("conditions", [])
            operator = condition.get("operator", "AND")
            summaries = [self._summarize_condition(c) for c in sub_conditions]
            return f" {operator} ".join(summaries)

        return "Custom condition"

    def _summarize_scope(self, scope_type: str, scope_config: Dict) -> str:
        """Generate human-readable summary of scope."""
        provider = scope_config.get("provider") or scope_config.get("platform")
        level = scope_config.get("level", "campaign")
        is_aggregate = scope_config.get("aggregate", False)

        if scope_type == "all":
            if is_aggregate:
                # Aggregate mode: monitoring totals
                if provider:
                    return f"{provider.title()} account total"
                return "Account total"
            else:
                # Individual mode: monitoring each campaign
                if provider:
                    return f"All {provider.title()} {level}s"
                return f"All {level}s"

        elif scope_type == "filter":
            name_filter = scope_config.get("entity_name_contains")
            if name_filter:
                return f"{level}s matching '{name_filter}'"
            return f"Filtered {level}s"

        elif scope_type == "specific":
            entity_ids = scope_config.get("entity_ids", [])
            return f"{len(entity_ids)} specific {level}(s)"

        return "Custom scope"

    def _parse_agent_description(self, description: str) -> Dict[str, Any]:
        """
        Parse natural language agent description to extract configuration.

        Examples:
        - "alert me when ROAS drops below 2" -> {metric: "roas", operator: "<", value: 2}
        - "notify me if CPC goes above $3" -> {metric: "cpc", operator: ">", value: 3}
        """
        import re

        description_lower = description.lower()
        result = {}

        # Extract metric
        metrics_map = {
            "roas": ["roas", "return on ad spend"],
            "cpc": ["cpc", "cost per click"],
            "ctr": ["ctr", "click through rate", "click-through rate"],
            "cpa": ["cpa", "cost per acquisition", "cost per action"],
            "spend": ["spend", "spending", "cost"],
            "revenue": ["revenue", "sales", "income"],
            "conversions": ["conversions", "conversion", "purchases"],
            "impressions": ["impressions", "views"],
            "clicks": ["clicks"],
        }

        for metric, keywords in metrics_map.items():
            for keyword in keywords:
                if keyword in description_lower:
                    result["metric"] = metric
                    break
            if "metric" in result:
                break

        # Extract operator and value
        patterns = [
            # "drops below X" or "falls below X"
            (r"(?:drops?|falls?|goes?)\s+(?:below|under)\s+\$?(\d+\.?\d*)", "<"),
            # "goes above X" or "exceeds X"
            (r"(?:goes?|rises?|exceeds?)\s+(?:above|over)\s+\$?(\d+\.?\d*)", ">"),
            # "below X" or "under X"
            (r"(?:below|under|less than|<)\s+\$?(\d+\.?\d*)", "<"),
            # "above X" or "over X"
            (r"(?:above|over|more than|greater than|>)\s+\$?(\d+\.?\d*)", ">"),
            # "< X" or "> X" patterns
            (r"<\s*\$?(\d+\.?\d*)", "<"),
            (r">\s*\$?(\d+\.?\d*)", ">"),
        ]

        for pattern, operator in patterns:
            match = re.search(pattern, description_lower)
            if match:
                result["operator"] = operator
                result["value"] = float(match.group(1))
                break

        # Extract platform
        if "google" in description_lower:
            result["platform"] = "google"
        elif "meta" in description_lower or "facebook" in description_lower:
            result["platform"] = "meta"

        return result

    def _generate_agent_name(self, condition: Dict, scope_config: Dict) -> str:
        """Generate a descriptive agent name from configuration."""
        metric = condition.get("metric", "metric").upper()
        operator = condition.get("operator", "lt")
        value = condition.get("value", 0)

        # Handle both symbolic (<, >) and named (lt, gt) operators
        op_word = "Low" if operator in ["<", "<=", "lt", "lte"] else "High"
        provider = scope_config.get("provider", "")
        provider_str = f" {provider.title()}" if provider else ""

        return f"{op_word} {metric} Alert{provider_str}"


def execute_tool(
    tool_name: str,
    tool_args: Dict[str, Any],
    db: Session,
    workspace_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a tool by name.

    WHAT: Dispatcher for tool execution.

    WHY: Single entry point for agent to call any tool.

    PARAMETERS:
        tool_name: Name of tool to execute
        tool_args: Arguments for the tool
        db: SQLAlchemy session
        workspace_id: Current workspace
        user_id: Current user

    RETURNS:
        Tool result dict
    """
    # Semantic/metrics tools
    if tool_name in ["query_metrics", "get_entities", "analyze_change"]:
        tools = SemanticTools(db, workspace_id, user_id)

        if tool_name == "query_metrics":
            return tools.query_metrics(**tool_args)
        elif tool_name == "get_entities":
            return tools.get_entities(**tool_args)
        elif tool_name == "analyze_change":
            return tools.analyze_change(**tool_args)

    # Agent management tools
    elif tool_name in ["list_agents", "get_agent_status", "create_agent", "pause_agent", "resume_agent", "explain_agent_behavior"]:
        agent_tools = AgentManagementTools(db, workspace_id, user_id)

        if tool_name == "list_agents":
            return agent_tools.list_agents(**tool_args)
        elif tool_name == "get_agent_status":
            return agent_tools.get_agent_status(**tool_args)
        elif tool_name == "create_agent":
            return agent_tools.create_agent(**tool_args)
        elif tool_name == "pause_agent":
            return agent_tools.pause_agent(**tool_args)
        elif tool_name == "resume_agent":
            return agent_tools.resume_agent(**tool_args)
        elif tool_name == "explain_agent_behavior":
            return agent_tools.explain_agent_behavior(**tool_args)

    return {"error": f"Unknown tool: {tool_name}"}


# =============================================================================
# TOOL DESCRIPTIONS FOR PROMPTS
# =============================================================================


def get_tools_description() -> str:
    """
    Get human-readable description of all tools.

    WHY: Used in system prompt to tell LLM what tools are available.
    """
    return """You have access to these tools:

## METRICS & ANALYTICS

1. **query_metrics** - Get advertising metrics
   - metrics: What to measure (roas, spend, cpc, ctr, revenue, conversions, etc.)
   - time_range: "1d", "7d", "30d", "90d"
   - breakdown_level: "campaign", "adset", "ad", "provider"
   - limit: Number of entities (default 5)
   - compare_to_previous: true/false for period comparison
   - include_timeseries: true/false for daily data
   - filters: {provider: "meta"|"google", entity_name: "..."}

2. **get_entities** - List campaigns, ad sets, or ads
   - level: "campaign", "adset", "ad"
   - name_contains: Filter by name
   - limit: Max results

3. **analyze_change** - Understand why a metric changed
   - metric: The metric that changed
   - direction: "up" or "down"
   - time_range: Period to analyze

## AGENT MANAGEMENT (Monitoring Automation)

4. **list_agents** - List user's monitoring agents
   - status_filter: "active", "paused", or "all"

5. **get_agent_status** - Get detailed status of an agent
   - agent_name: Name or partial name to search
   - agent_id: UUID if known

6. **create_agent** - Create agent from natural language
   - description: What the agent should do (e.g., "alert me when ROAS drops below 2")
   - platform: Optional platform filter (meta, google, all)
   - campaign_name: Optional specific campaign

7. **pause_agent** - Pause a running agent
   - agent_name or agent_id
   - reason: Optional pause reason

8. **resume_agent** - Resume a paused agent
   - agent_name or agent_id

9. **explain_agent_behavior** - Explain why an agent did/didn't trigger
   - agent_name or agent_id
   - time_range: "today", "yesterday", "last_7d", "last_30d"
   - question: Specific question about behavior

Always use query_metrics for data questions. Use analyze_change for "why" questions.
For monitoring setup, use create_agent with natural language like "alert me when CPC goes above $5".
"""
