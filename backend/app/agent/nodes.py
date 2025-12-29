"""
Agent Nodes
===========

**Version**: 1.1.0
**Created**: 2025-12-03
**Updated**: 2025-12-12 - Switched from Claude Sonnet 4 to GPT-4o-mini (95% cost reduction)

LangGraph node functions that process agent state.
Each node is a step in the agent's decision-making process.

WHY THIS FILE EXISTS
--------------------
LangGraph agents are state machines. Each node is a function that:
1. Reads from state
2. Performs some action (LLM call, tool call, etc.)
3. Writes to state
4. Returns next node to visit (or END)

This file contains all node implementations.

NODE TYPES
----------
- understand: Classify intent, extract entities
- fetch_data: Call semantic layer tools
- analyze: Reason about data (for "why" questions)
- respond: Generate natural language answer
- clarify: Ask user for clarification
- explain_limit: Explain why we can't answer

RELATED FILES
-------------
- app/agent/state.py: AgentState schema
- app/agent/tools.py: Tools called by nodes
- app/agent/graph.py: Connects nodes into graph
- app/agent/stream.py: Streaming publisher
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional, Dict, Any, List, Literal

from openai import OpenAI, AsyncOpenAI
from sqlalchemy.orm import Session

from app.agent.state import AgentState, Message, MessageRole
from app.agent.tools import (
    SemanticTools,
    get_tool_schemas,
    get_tools_description,
    get_agent_tools,
    AGENT_TOOLS,
)
from app.agent.stream import StreamPublisher, AsyncQueuePublisher
from app.agent.live_api_tools import LiveApiTools
from app.agent.rate_limiter import WorkspaceRateLimiter
from app.agent.exceptions import (
    LiveApiError,
    QuotaExhaustedError,
    TokenExpiredError,
    WorkspaceRateLimitError,
    ProviderNotConnectedError,
)
from app.models import Workspace, Connection

logger = logging.getLogger(__name__)


# =============================================================================
# WORKSPACE CONTEXT
# =============================================================================


def _fetch_workspace_context(
    db: Session, workspace_id: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch business profile context for a workspace.

    WHAT: Retrieves business profile data from workspace settings
    WHY: Personalizes Copilot responses based on user's business context

    RETURNS:
        Dict with business context or None if no profile data
    """
    try:
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            return None

        # Only return context if we have meaningful data
        context = {}

        if workspace.name:
            context["company_name"] = workspace.name

        if workspace.niche:
            context["industry"] = workspace.niche

        if workspace.target_markets:
            context["markets"] = workspace.target_markets

        if workspace.domain_description:
            context["about"] = workspace.domain_description

        if workspace.brand_voice:
            context["brand_voice"] = workspace.brand_voice

        # Add connected ad platforms
        connections = (
            db.query(Connection)
            .filter(
                Connection.workspace_id == workspace_id, Connection.status == "active"
            )
            .all()
        )
        if connections:
            context["connected_providers"] = list(
                set(c.provider.value for c in connections)
            )

        # Return context if we have any useful info
        return context if context else None

    except Exception as e:
        logger.warning(f"[CONTEXT] Failed to fetch workspace context: {e}")
        return None


def _build_business_context_prompt(context: Optional[Dict[str, Any]]) -> str:
    """
    Build a business context section for system prompts.

    WHAT: Formats workspace context into a prompt section
    WHY: Helps LLM personalize responses to the specific business

    RETURNS:
        Formatted business context string or empty string
    """
    if not context:
        return ""

    sections = ["BUSINESS CONTEXT:"]

    if context.get("company_name"):
        sections.append(f"- Company: {context['company_name']}")

    if context.get("industry"):
        sections.append(f"- Industry: {context['industry']}")

    if context.get("markets"):
        markets = context["markets"]
        if isinstance(markets, list):
            markets = ", ".join(markets)
        sections.append(f"- Target Markets: {markets}")

    if context.get("about"):
        sections.append(f"- About: {context['about']}")

    if context.get("brand_voice"):
        sections.append(f"- Brand Voice: {context['brand_voice']}")

    if context.get("connected_providers"):
        providers = context["connected_providers"]
        if isinstance(providers, list):
            providers = ", ".join(providers)
        sections.append(f"- Connected Ad Platforms: {providers}")

    sections.append("")
    sections.append("""HOW TO USE THIS CONTEXT:
- Reference the company name naturally when appropriate
- Use industry-specific language and terminology relevant to their niche
- Consider their target markets when discussing performance (e.g., seasonal trends, market-specific behaviors)
- Match their brand voice in your tone (Professional=formal, Casual=friendly, Luxury=sophisticated, Playful=energetic, Technical=data-focused)
- Draw on your knowledge of their industry to provide relevant insights (e.g., typical customer behavior, competitive landscape, industry-specific KPIs)
- If they mention a specific product or offering in their description, relate metrics to their business model""")
    sections.append("")

    return "\n".join(sections)


# =============================================================================
# LLM CLIENT
# =============================================================================

# Model configuration - easy to switch models
LLM_MODEL = "gpt-4o-mini"


def get_openai_client() -> OpenAI:
    """Get synchronous OpenAI client."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


def get_async_openai_client() -> AsyncOpenAI:
    """Get async OpenAI client for non-blocking API calls.

    WHY: The sync client blocks the event loop, preventing FastAPI
    from handling other requests during the API calls.
    The async client allows concurrent request handling.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return AsyncOpenAI(api_key=api_key)


# Backwards compatibility aliases (for imports elsewhere)
get_claude_client = get_openai_client
get_async_claude_client = get_async_openai_client


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

UNDERSTAND_PROMPT = """You are an expert advertising analyst for an e-commerce analytics platform.
Your job is to understand user questions about their advertising performance.

AVAILABLE METRICS (use these exact names):
- spend: Total ad spend
- revenue: Total revenue from ads
- roas: Return on ad spend (revenue/spend)
- cpc: Cost per click (spend/clicks)
- ctr: Click-through rate (clicks/impressions)
- cpa: Cost per acquisition (spend/conversions)
- clicks: Total clicks
- impressions: Total impressions
- conversions: Total conversions
- profit: Revenue minus spend
- aov: Average order value
- cvr: Conversion rate

CAPABILITIES:
- Answer questions about any of the metrics listed above
- Compare periods (this week vs last week, this month vs last month)
- Break down by campaign, ad set, ad, or platform (Meta, Google)
- Show trends over time with charts/graphs
- Find top/bottom performers
- Answer questions about the user's business profile (company name, industry, markets, etc.) if provided in BUSINESS CONTEXT

LIMITATIONS:
- Only advertising data available (not Shopify order details)
- Cannot modify campaigns, only report
- No data before account was connected
- Cannot predict the future

IMPORTANT - AVAILABLE FILTERS:
You can ONLY filter by:
- provider: "meta" or "google"
- entity_name: A specific campaign/ad name

You CANNOT filter by metric values. For "campaigns with zero sales", use breakdown_level="campaign".

INTENTS:
- metric_query: Questions about specific metrics
- comparison: Comparing time periods or entities
- ranking: Top/bottom performers
- analysis: "Why" questions
- business_context: Questions about their own company/business profile (name, industry, markets, etc.)
- clarification_needed: Ambiguous question
- out_of_scope: Cannot answer (use ONLY for questions completely unrelated to advertising or their business)

EXTRACT THESE FIELDS:
- metrics: Which metrics (use exact names from list above - e.g., "cpc" not "cost per click")
- time_range: "1d", "3d", "7d", "30d", "90d" (parse "last 3 days" as "3d", "yesterday" as "1d")
- entities: Specific campaigns/ads mentioned by name
- breakdown_level: "campaign", "adset", "ad", "provider", or null
- compare_to_previous: true if comparing to previous period
- include_timeseries: true if user wants a graph/chart/trend, or if time range is specified
- filters: ONLY {provider: "meta"|"google"} or {entity_name: "..."}

EXAMPLES:
- "what's my cpc?" -> intent: "metric_query", metrics: ["cpc"], include_timeseries: false
- "make a graph of cpc last 3 days" -> intent: "metric_query", metrics: ["cpc"], time_range: "3d", include_timeseries: true
- "show me spend trend this week" -> intent: "metric_query", metrics: ["spend"], time_range: "7d", include_timeseries: true
- "compare ROAS this week vs last week" -> intent: "comparison", metrics: ["roas"], compare_to_previous: true
- "give me spend, revenue, ROAS and profit for all campaigns" -> intent: "metric_query", metrics: ["spend", "revenue", "roas", "profit"], breakdown_level: "campaign"
- "show me all Meta campaign metrics this month" -> intent: "metric_query", metrics: ["spend", "revenue", "roas", "profit"], breakdown_level: "campaign", filters: {provider: "meta"}, time_range: "30d"
- "breakdown by campaign with spend and conversions" -> intent: "metric_query", metrics: ["spend", "conversions"], breakdown_level: "campaign"
- "what's my company name?" -> intent: "business_context" (answer from BUSINESS CONTEXT above)
- "what industry am I in?" -> intent: "business_context"
- "what are my target markets?" -> intent: "business_context"
- "tell me about my business" -> intent: "business_context"
- "who am I?" -> intent: "business_context"

LIVE DATA DETECTION:
Users expect current data - they shouldn't need to ask for "live" data explicitly.
Automatically set "needs_live_data": true when:

1. TIME-BASED TRIGGERS (most important):
   - Question is about "today" → ALWAYS use live data (time_range: "today")
   - Question is about "right now", "currently", "at the moment" → live data
   - No time specified but asking for a single current metric → assume today, use live

2. EXPLICIT TRIGGERS:
   - User says "live", "real-time", "fresh", "latest", "from the API"

3. USE SNAPSHOTS (needs_live_data: false) for:
   - Trend analysis: "this week", "this month", "last 7 days"
   - Comparisons: "compare to last week"
   - Historical questions: "how did we do last month?"

DECISION LOGIC:
- "What's my ROAS today?" → needs_live_data: true, time_range: "today"
- "What's my ROAS?" → needs_live_data: true, time_range: "today" (assume they want current)
- "How's my spend going?" → needs_live_data: true, time_range: "today" (present tense = now)
- "Show spend trend this week" → needs_live_data: false, time_range: "7d" (trend = historical)
- "Compare this week to last" → needs_live_data: false (comparison needs snapshots)
- "What was my ROAS yesterday?" → needs_live_data: false, time_range: "yesterday"

Examples:
- "What's my ROAS?" -> needs_live_data: true, time_range: "today"
- "How much have I spent today?" -> needs_live_data: true, time_range: "today"
- "What's my current CPC?" -> needs_live_data: true, time_range: "today"
- "How are my campaigns doing?" -> needs_live_data: true, time_range: "today"
- "Show my spend this week" -> needs_live_data: false, time_range: "7d"
- "Compare my ROAS week over week" -> needs_live_data: false, time_range: "7d"

Respond in JSON format:
{
  "intent": "metric_query|comparison|ranking|analysis|business_context|clarification_needed|out_of_scope",
  "metrics": ["roas"],
  "time_range": "today",
  "entities": [],
  "breakdown_level": null,
  "compare_to_previous": false,
  "include_timeseries": false,
  "filters": {},
  "clarification_needed": "..." (if needed),
  "out_of_scope_reason": "..." (if out of scope),
  "needs_live_data": true
}
"""

RESPOND_PROMPT = """You are a friendly advertising analyst helping merchants understand their ad performance.

Based on the data provided, write a clear, helpful response. Be:
- Conversational but professional
- Specific with numbers (format properly: $1,234.56, 6.24×, 12.5%)
- Insightful - don't just repeat numbers, explain what they mean
- Concise - 2-4 sentences for simple queries

IMPORTANT: Charts and graphs ARE automatically generated and displayed below your text response.
- Do NOT say you cannot create graphs or charts
- Do NOT suggest using Excel or other tools to create charts
- Do NOT say "I can only provide text" or similar
- Simply describe the data and insights - the visualization will appear automatically

If there's comparison data, highlight the change and whether it's good or bad.
If there's a breakdown, mention the top performers.
If there's timeseries data, reference the trend shown in the chart.

Do NOT include raw data or JSON. Speak naturally."""


# =============================================================================
# NODE FUNCTIONS
# =============================================================================


def understand_node(
    state: AgentState,
    db: Session,
    publisher: Optional[StreamPublisher] = None,
) -> Dict[str, Any]:
    """
    Understand the user's question.

    WHAT: Classifies intent and extracts query parameters.

    WHY: First step - we need to understand what the user wants
    before we can fetch the right data.

    PROCESS:
        1. Get conversation context
        2. Call Claude to classify intent
        3. Extract metrics, time range, entities, filters
        4. Return parsed intent for routing

    RETURNS:
        State updates: intent, semantic_query
    """
    logger.info(f"[NODE] understand: {state.get('current_question', '')[:50]}...")

    if publisher:
        publisher.thinking("Understanding your question...")

    # Build messages for Claude
    messages = []

    # Add conversation history for context
    for msg in state.get("messages", [])[:-1]:  # Exclude current question
        messages.append(
            {
                "role": msg.role.value
                if hasattr(msg, "role")
                else msg.get("role", "user"),
                "content": msg.content
                if hasattr(msg, "content")
                else msg.get("content", ""),
            }
        )

    # Add current question
    messages.append(
        {
            "role": "user",
            "content": state["current_question"],
        }
    )

    try:
        client = get_openai_client()

        # Fetch business context for personalization
        workspace_id = state.get("workspace_id")
        print(f"[DEBUG] understand workspace_id: {workspace_id}")
        business_context = (
            _fetch_workspace_context(db, workspace_id) if workspace_id else None
        )
        print(f"[DEBUG] business_context fetched: {business_context}")
        context_prompt = _build_business_context_prompt(business_context)

        # Build system prompt with optional business context
        system_prompt = UNDERSTAND_PROMPT
        if context_prompt:
            system_prompt = f"{context_prompt}\n{UNDERSTAND_PROMPT}"
            logger.info(
                f"[NODE] Injecting business context for workspace: {workspace_id}"
            )
        else:
            logger.warning(
                f"[NODE] No business context found for workspace: {workspace_id}"
            )

        # OpenAI format: system prompt goes in messages array
        openai_messages = [{"role": "system", "content": system_prompt}] + messages

        response = client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=1024,
            messages=openai_messages,
        )

        # Parse JSON response
        content = response.choices[0].message.content
        logger.info(f"[NODE] understand response: {content[:200]}...")

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
        else:
            json_str = content

        parsed = json.loads(json_str.strip())

        intent = parsed.get("intent", "metric_query")
        print(
            f"[DEBUG] Classified intent: {intent}, question was: {state.get('current_question', '')[:100]}"
        )

        # Build semantic query dict
        compare_to_previous = parsed.get("compare_to_previous", False)

        # Auto-enable timeseries for comparison questions (for charts)
        include_timeseries = parsed.get("include_timeseries", False)
        if compare_to_previous and not include_timeseries:
            include_timeseries = True  # Always show chart for comparisons

        semantic_query = {
            "metrics": parsed.get("metrics", ["roas"]),
            "time_range": parsed.get("time_range", "7d"),
            "breakdown_level": parsed.get("breakdown_level"),
            "compare_to_previous": compare_to_previous,
            "include_timeseries": include_timeseries,
            "filters": parsed.get("filters", {}),
            "entities": parsed.get("entities", []),
        }

        # Extract live data flag from parsed response
        needs_live_data = parsed.get("needs_live_data", False)
        live_data_reason = "user_requested" if needs_live_data else None

        # Handle special intents
        if intent == "clarification_needed":
            return {
                "intent": intent,
                "needs_clarification": True,
                "clarification_question": parsed.get("clarification_needed"),
                "stage": "responding",
            }

        if intent == "out_of_scope":
            return {
                "intent": intent,
                "error": parsed.get(
                    "out_of_scope_reason",
                    "I can only answer questions about your advertising data.",
                ),
                "stage": "responding",
            }

        # Business context questions don't need data fetch - go straight to respond
        if intent == "business_context":
            return {
                "intent": intent,
                "business_context": business_context,  # Pass the context to respond node
                "stage": "responding",
            }

        return {
            "intent": intent,
            "semantic_query": semantic_query,
            "stage": "checking_freshness",  # Go to freshness check before fetching
            "needs_live_data": needs_live_data,
            "live_data_reason": live_data_reason,
        }

    except json.JSONDecodeError as e:
        logger.error(f"[NODE] Failed to parse understand response: {e}")
        # Fallback to simple metric query
        return {
            "intent": "metric_query",
            "semantic_query": {
                "metrics": ["roas"],
                "time_range": "7d",
            },
            "stage": "checking_freshness",
            "needs_live_data": False,
            "live_data_reason": None,
        }

    except Exception as e:
        logger.exception(f"[NODE] understand failed: {e}")
        return {
            "error": f"Failed to understand question: {str(e)}",
            "stage": "error",
        }


def check_data_freshness_node(
    state: AgentState,
    db: Session,
    publisher: Optional[StreamPublisher] = None,
) -> Dict[str, Any]:
    """
    Check if snapshot data is stale and enable auto-fallback.

    WHAT: Queries MetricSnapshot to find the most recent data timestamp.

    WHY: Auto-fallback ensures users get data even if sync jobs failed.
         If data is older than 24 hours, sets needs_live_data=True.

    PROCESS:
        1. If needs_live_data already true (user requested) → pass through
        2. Query MetricSnapshot for latest timestamp in workspace
        3. If latest > 24h ago → set needs_live_data=True, live_data_reason="stale_snapshot"

    RETURNS:
        State updates: needs_live_data, live_data_reason, stage
    """
    logger.info("[NODE] check_data_freshness")

    # If user explicitly requested live data, pass through
    if state.get("needs_live_data"):
        logger.info(
            "[NODE] Live data already requested by user, skipping freshness check"
        )
        return {
            "stage": "fetching",
        }

    workspace_id = state.get("workspace_id")
    if not workspace_id:
        logger.warning("[NODE] No workspace_id in state, skipping freshness check")
        return {
            "stage": "fetching",
        }

    try:
        # Use LiveApiTools to check freshness
        # Note: We create a minimal instance just for freshness check
        from app import state as app_state

        redis_client = getattr(app_state, "redis_client", None)

        live_tools = LiveApiTools(
            db=db,
            workspace_id=workspace_id,
            user_id=state.get("user_id", ""),
            redis_client=redis_client,
        )

        freshness = live_tools.check_data_freshness()

        # Check if any provider has stale data
        any_stale = False
        stale_providers = []

        for provider, status in freshness.items():
            if status.get("is_stale"):
                any_stale = True
                stale_providers.append(provider)
                logger.warning(
                    f"[NODE] {provider} data is stale "
                    f"(last sync: {status.get('last_sync')}, "
                    f"{status.get('hours_old')} hours old)"
                )

        if any_stale:
            logger.info(
                f"[NODE] Enabling auto-fallback to live API for stale providers: {stale_providers}"
            )
            return {
                "needs_live_data": True,
                "live_data_reason": "stale_snapshot",
                "stage": "fetching",
            }

        logger.info("[NODE] Data is fresh, using snapshots")
        return {
            "stage": "fetching",
        }

    except Exception as e:
        logger.warning(f"[NODE] Freshness check failed, continuing with snapshots: {e}")
        return {
            "stage": "fetching",
        }


# =============================================================================
# LIVE API HELPER FUNCTIONS
# =============================================================================


def _map_time_range_to_live(time_range: str) -> str:
    """
    Map semantic layer time_range format to live API date_range format.

    WHAT:
        Converts "7d", "30d" etc. to "last_7d", "last_30d" etc.

    WHY:
        Live API uses different format than semantic layer.
    """
    mapping = {
        "1d": "today",
        "3d": "last_7d",  # Round up to 7 for live API
        "7d": "last_7d",
        "14d": "last_30d",  # Round up to 30
        "30d": "last_30d",
        "90d": "last_30d",  # Cap at 30 for live
    }
    return mapping.get(time_range, "last_7d")


def _map_breakdown_to_entity_type(breakdown_level: Optional[str]) -> str:
    """
    Map semantic layer breakdown_level to live API entity_type.

    WHAT:
        Converts "campaign", "adset", "ad" to entity_type format.

    WHY:
        Live API uses entity_type parameter.
    """
    if not breakdown_level:
        return "account"

    mapping = {
        "campaign": "campaign",
        "adset": "adset",
        "ad": "ad",
        "provider": "account",
    }
    return mapping.get(breakdown_level, "account")


def _convert_live_to_compilation_result(
    live_result: Dict[str, Any],
    semantic_query: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert live API result to compilation_result format.

    WHAT:
        Transforms live API response to match semantic layer output format.

    WHY:
        Allows respond_node to work identically with live or snapshot data.
    """
    if not live_result.get("success"):
        return {"success": False, "error": "Live API query failed"}

    data = live_result.get("data", {})
    summary = data.get("summary", {})
    breakdown = data.get("breakdown", [])

    # Convert summary to metric format expected by respond_node
    formatted_summary = {}
    for metric, value in summary.items():
        formatted_summary[metric] = {
            "value": value,
            "formatted": _format_metric_value(metric, value),
        }

    result = {
        "success": True,
        "data": {
            "summary": formatted_summary,
            "is_live": True,
            "fetched_at": live_result.get("fetched_at"),
            "date_range": live_result.get("date_range"),
        },
    }

    # Add breakdown if present
    if breakdown:
        formatted_breakdown = []
        for item in breakdown:
            formatted_item = {
                "entity_name": item.get("name", item.get("id", "Unknown")),
                "entity_id": item.get("id"),
            }
            for metric in ["spend", "impressions", "clicks", "conversions", "revenue"]:
                if metric in item:
                    formatted_item[metric] = {
                        "value": item[metric],
                        "formatted": _format_metric_value(metric, item[metric]),
                    }
            formatted_breakdown.append(formatted_item)
        result["data"]["breakdown"] = formatted_breakdown

    return result


def _format_metric_value(metric: str, value: Any) -> str:
    """Format metric value for display."""
    if value is None:
        return "N/A"

    if metric in ["spend", "revenue"]:
        return f"${value:,.2f}"
    elif metric in ["roas", "poas"]:
        return f"{value:.2f}×"
    elif metric in ["ctr", "cvr"]:
        return f"{value:.2%}"
    elif metric in ["impressions", "clicks", "conversions"]:
        return f"{int(value):,}"
    else:
        return f"{value:.2f}"


def fetch_data_node(
    state: AgentState,
    db: Session,
    publisher: Optional[StreamPublisher] = None,
) -> Dict[str, Any]:
    """
    Fetch data from the semantic layer or live API.

    WHAT: Calls semantic layer tools or live API based on state.

    WHY: Get the actual data to answer the question. Uses live API when:
         - User explicitly requested live data
         - Snapshot data is stale (>24h)

    PROCESS:
        1. Check if needs_live_data is True
        2. If live, use LiveApiTools
        3. If snapshot, use SemanticTools
        4. Fallback: if live fails, try snapshot; if snapshot empty, try live

    RETURNS:
        State updates: compilation_result, live_api_calls
    """
    logger.info("[NODE] fetch_data")

    semantic_query = state.get("semantic_query", {})
    intent = state.get("intent", "metric_query")
    needs_live_data = state.get("needs_live_data", False)
    live_data_reason = state.get("live_data_reason")

    workspace_id = state["workspace_id"]
    user_id = state.get("user_id", "")

    # Initialize tools
    tools = SemanticTools(db, workspace_id, user_id)

    # Get Redis client for rate limiting
    from app import state as app_state

    redis_client = getattr(app_state, "redis_client", None)

    live_api_calls = []
    result = None

    # Determine data source based on needs_live_data flag
    if needs_live_data:
        logger.info(f"[NODE] Using live API (reason: {live_data_reason})")

        if publisher:
            publisher.thinking("Fetching live data from ad platform...")

        try:
            live_tools = LiveApiTools(
                db=db,
                workspace_id=workspace_id,
                user_id=user_id,
                redis_client=redis_client,
            )

            # Map time_range to live API format
            time_range = semantic_query.get("time_range", "7d")
            live_date_range = _map_time_range_to_live(time_range)

            # Determine entity type from breakdown level
            breakdown_level = semantic_query.get("breakdown_level")
            entity_type = _map_breakdown_to_entity_type(breakdown_level)

            # Determine provider from filters
            filters = semantic_query.get("filters", {})
            provider = filters.get("provider")

            # If no provider specified, try to determine from connected accounts
            if not provider:
                from app.agent.connection_resolver import ConnectionResolver

                resolver = ConnectionResolver(db, workspace_id)
                available = resolver.get_available_providers()
                provider = available[0] if available else "meta"

            if publisher:
                publisher.tool_call(
                    "live_api_query",
                    {
                        "provider": provider,
                        "entity_type": entity_type,
                        "date_range": live_date_range,
                    },
                )

            # Fetch live metrics
            live_result = live_tools.get_live_metrics(
                provider=provider,
                entity_type=entity_type,
                metrics=semantic_query.get(
                    "metrics", ["spend", "impressions", "clicks"]
                ),
                date_range=live_date_range,
            )

            # Track API calls
            live_api_calls = live_tools.api_calls

            if live_result.get("success"):
                # Convert live result to compilation_result format
                result = _convert_live_to_compilation_result(
                    live_result, semantic_query
                )

                if publisher:
                    summary = live_result.get("data", {}).get("summary", {})
                    preview_parts = []
                    for metric, val in summary.items():
                        if val is not None:
                            if metric in ["spend", "revenue"]:
                                preview_parts.append(f"{metric}: ${val:,.2f}")
                            else:
                                preview_parts.append(f"{metric}: {val:,.0f}")
                    publisher.tool_result(
                        "live_api_query",
                        ", ".join(preview_parts)
                        if preview_parts
                        else "Live data retrieved",
                    )
            else:
                logger.warning(f"[NODE] Live API failed, falling back to snapshot")
                result = None  # Will trigger fallback below

        except (QuotaExhaustedError, WorkspaceRateLimitError) as e:
            logger.warning(
                f"[NODE] Live API rate limited: {e}, falling back to snapshot"
            )
            live_api_calls.append(
                {
                    "provider": getattr(e, "provider", "unknown"),
                    "endpoint": "get_live_metrics",
                    "success": False,
                    "error": str(e),
                }
            )
            result = None  # Fallback to snapshot

        except (TokenExpiredError, ProviderNotConnectedError) as e:
            logger.warning(f"[NODE] Live API auth error: {e}")
            # For auth errors, don't fallback - return error to user
            return {
                "error": e.to_user_message(),
                "stage": "error",
                "live_api_calls": live_api_calls,
            }

        except LiveApiError as e:
            logger.warning(f"[NODE] Live API error: {e}, falling back to snapshot")
            live_api_calls.append(
                {
                    "provider": getattr(e, "provider", "unknown"),
                    "endpoint": "get_live_metrics",
                    "success": False,
                    "error": str(e),
                }
            )
            result = None  # Fallback to snapshot

    # If not using live API or live API failed, use snapshot data
    if result is None:
        logger.info("[NODE] Using snapshot data")

        if publisher and needs_live_data:
            publisher.thinking("Live API unavailable, using cached data...")
        elif publisher:
            publisher.thinking("Fetching your data...")

        try:
            # Choose tool based on intent
            if intent == "analysis":
                # Use analyze_change for "why" questions
                metrics = semantic_query.get("metrics") or ["roas"]
                metric = metrics[0] if metrics else "roas"
                if publisher:
                    publisher.tool_call("analyze_change", {"metric": metric})

                result = tools.analyze_change(
                    metric=metric,
                    time_range=semantic_query.get("time_range", "7d"),
                )

                if publisher:
                    if result and result.get("success"):
                        direction = result.get("direction", "")
                        change = result.get("change_str", "")
                        publisher.tool_result(
                            "analyze_change", f"{metric.upper()} {direction} {change}"
                        )
                    else:
                        publisher.tool_result(
                            "analyze_change", "No change data available"
                        )

            else:
                # Use query_metrics for most queries
                if publisher:
                    publisher.tool_call("query_metrics", semantic_query)

                result = tools.query_metrics(
                    metrics=semantic_query.get("metrics", ["roas"]),
                    time_range=semantic_query.get("time_range", "7d"),
                    breakdown_level=semantic_query.get("breakdown_level"),
                    limit=semantic_query.get("limit", 5),
                    compare_to_previous=semantic_query.get(
                        "compare_to_previous", False
                    ),
                    include_timeseries=semantic_query.get("include_timeseries", False),
                    filters=semantic_query.get("filters"),
                )

                if publisher and result.get("success"):
                    data = result.get("data", {})
                    summary = data.get("summary", {})
                    preview_parts = []
                    for metric, values in summary.items():
                        if isinstance(values, dict) and values.get("value"):
                            val = values["value"]
                            if metric in ["spend", "revenue"]:
                                preview_parts.append(f"{metric}: ${val:,.2f}")
                            elif metric in ["roas", "poas"]:
                                preview_parts.append(f"{metric}: {val:.2f}×")
                            else:
                                preview_parts.append(f"{metric}: {val:.2f}")
                    publisher.tool_result(
                        "query_metrics",
                        ", ".join(preview_parts) if preview_parts else "Data retrieved",
                    )

        except Exception as e:
            logger.exception(f"[NODE] Snapshot query failed: {e}")
            return {
                "error": f"Failed to fetch data: {str(e)}",
                "stage": "error",
                "live_api_calls": live_api_calls,
            }

        logger.info(
            f"[NODE] fetch_data result: {result.get('success', False) if result else False}"
        )

    # Return result
    if result and result.get("error"):
        return {
            "error": result["error"],
            "stage": "error",
            "live_api_calls": live_api_calls,
        }

    return {
        "compilation_result": result,
        "stage": "responding",
        "live_api_calls": live_api_calls,
    }


def respond_node(
    state: AgentState,
    db: Session,
    publisher: Optional[StreamPublisher] = None,
) -> Dict[str, Any]:
    """
    Generate natural language response.

    WHAT: Uses Claude to generate a helpful answer.

    WHY: Convert raw data into natural, insightful response.

    PROCESS:
        1. Read data from state
        2. Call Claude with data context
        3. Stream tokens to publisher
        4. Build visuals

    RETURNS:
        State updates: answer_chunks, visuals
    """
    logger.info("[NODE] respond")

    # Handle special cases
    if state.get("needs_clarification"):
        answer = state.get(
            "clarification_question", "Could you please clarify your question?"
        )
        if publisher:
            publisher.answer_chunk(answer)
        return {
            "answer_chunks": [answer],
            "stage": "done",
        }

    if state.get("error") and state.get("intent") == "out_of_scope":
        answer = state["error"]
        if publisher:
            publisher.answer_chunk(answer)
        return {
            "answer_chunks": [answer],
            "stage": "done",
        }

    # Handle business context questions (no data fetch needed)
    if state.get("intent") == "business_context":
        business_ctx = state.get("business_context") or {}
        if not business_ctx:
            # Fetch it if not in state
            workspace_id = state.get("workspace_id")
            if workspace_id:
                business_ctx = _fetch_workspace_context(db, workspace_id) or {}

        # Build a simple response based on the context
        question = state.get("current_question", "").lower()

        # Try to answer common business context questions
        if business_ctx:
            if "company" in question or "name" in question or "business" in question:
                company = business_ctx.get("company_name")
                if company:
                    answer = f"Your company is **{company}**."
                else:
                    answer = "I don't have your company name on file. You can add it in Settings → Business."
            elif "industry" in question or "niche" in question:
                industry = business_ctx.get("industry")
                if industry:
                    answer = f"Your industry/niche is **{industry}**."
                else:
                    answer = "I don't have your industry/niche on file. You can add it in Settings → Business."
            elif "market" in question:
                markets = business_ctx.get("markets")
                if markets:
                    if isinstance(markets, list):
                        markets = ", ".join(markets)
                    answer = f"Your target markets are: **{markets}**."
                else:
                    answer = "I don't have your target markets on file. You can add them in Settings → Business."
            elif "brand" in question or "voice" in question:
                voice = business_ctx.get("brand_voice")
                if voice:
                    answer = f"Your brand voice is set to **{voice}**."
                else:
                    answer = "I don't have your brand voice on file. You can set it in Settings → Business."
            else:
                # General business context summary
                parts = []
                if business_ctx.get("company_name"):
                    parts.append(f"**Company:** {business_ctx['company_name']}")
                if business_ctx.get("industry"):
                    parts.append(f"**Industry:** {business_ctx['industry']}")
                if business_ctx.get("markets"):
                    markets = business_ctx["markets"]
                    if isinstance(markets, list):
                        markets = ", ".join(markets)
                    parts.append(f"**Markets:** {markets}")
                if business_ctx.get("about"):
                    parts.append(f"**About:** {business_ctx['about']}")
                if business_ctx.get("brand_voice"):
                    parts.append(f"**Brand Voice:** {business_ctx['brand_voice']}")

                if parts:
                    answer = "Here's your business profile:\n\n" + "\n".join(parts)
                else:
                    answer = "I don't have your business profile on file yet. You can set it up in Settings → Business."
        else:
            answer = "I don't have your business profile on file yet. You can set it up in Settings → Business."

        if publisher:
            publisher.answer_chunk(answer)
        return {
            "answer_chunks": [answer],
            "stage": "done",
        }

    compilation_result = state.get("compilation_result") or {}
    data = (
        compilation_result.get("data") if isinstance(compilation_result, dict) else {}
    )
    data = data or {}  # Ensure data is never None
    intent = state.get("intent", "metric_query")

    if publisher:
        publisher.thinking("Preparing your answer...")

    try:
        client = get_openai_client()

        # Fetch business context for personalization
        workspace_id = state.get("workspace_id")
        business_context = (
            _fetch_workspace_context(db, workspace_id) if workspace_id else None
        )
        context_prompt = _build_business_context_prompt(business_context)

        # Build system prompt with optional business context
        system_prompt = RESPOND_PROMPT
        if context_prompt:
            system_prompt = f"{context_prompt}\n{RESPOND_PROMPT}"

        # Build context message with data
        data_summary = json.dumps(data, indent=2, default=str)

        # OpenAI format: system prompt in messages array
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""User asked: "{state["current_question"]}"

Intent: {intent}

Data retrieved:
{data_summary}

Please write a helpful, conversational response based on this data.""",
            },
        ]

        # Stream the response
        answer_chunks = []

        stream = client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=1024,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:  # OpenAI sends None for some chunks
                answer_chunks.append(text)
                if publisher:
                    publisher.answer_token(text)

        full_answer = "".join(answer_chunks)
        logger.info(f"[NODE] respond generated: {full_answer[:100]}...")

        # Build visuals from data
        semantic_query = state.get("semantic_query") or {}
        visuals = _build_visuals_from_data(data, semantic_query)

        if publisher and visuals:
            publisher.visual(visuals)

        return {
            "answer_chunks": answer_chunks,
            "visuals": visuals,
            "stage": "done",
        }

    except Exception as e:
        logger.exception(f"[NODE] respond failed: {e}")
        fallback = "I encountered an error generating the response. Please try again."
        if publisher:
            publisher.answer_chunk(fallback)
        return {
            "answer_chunks": [fallback],
            "error": str(e),
            "stage": "done",
        }


def error_node(
    state: AgentState,
    db: Session,
    publisher: Optional[StreamPublisher] = None,
) -> Dict[str, Any]:
    """
    Handle errors gracefully.

    WHAT: Generate user-friendly error message.

    WHY: Never show raw errors to users. Always be helpful.
    """
    logger.info(f"[NODE] error: {state.get('error', 'Unknown error')}")

    error = state.get("error", "An unexpected error occurred.")

    # Make error message user-friendly
    friendly_message = _make_error_friendly(error)

    if publisher:
        publisher.error(friendly_message)

    return {
        "answer_chunks": [friendly_message],
        "stage": "done",
    }


# =============================================================================
# FREE AGENT NODE (ReAct-style)
# =============================================================================

# Agent system prompt with data source priority
AGENT_SYSTEM_PROMPT = """You are an expert advertising analyst copilot. You help users understand their ad performance across Google Ads and Meta Ads.

## CHARTS AND GRAPHS (CRITICAL)

**NEVER create ASCII charts, markdown tables, text-based graphs, or list individual daily values.**

Charts and visualizations are AUTOMATICALLY generated by our frontend based on the data you retrieve.
- If a user asks for a "graph" or "chart", just fetch the data with `include_timeseries: true`
- The frontend will render beautiful interactive charts automatically
- DO NOT repeat individual daily/hourly values - the chart shows them visually
- Only mention SUMMARY metrics (totals, averages, % change) in your text

**BAD (never do this):**
```
- Dec 23: $500
- Dec 24: $450
- Dec 25: $400
```

**ALSO BAD:**
"Here are the daily values: Monday $500, Tuesday $450..."

**GOOD:**
"Your spend this week totaled $5,147, down 40.8% from last week's $8,697. The chart below shows the daily breakdown."

## RESPONSE RULES (CRITICAL - READ CAREFULLY)

1. **ONLY use numbers EXACTLY as they appear in tool results** - NEVER calculate, estimate, or round
2. **For current period total**: Use `summary.<metric>.value` EXACTLY
3. **For previous period total**: Use `summary.<metric>.previous` EXACTLY  
4. **For % change**: Use `summary.<metric>.delta_pct` EXACTLY (multiply by 100 for percentage)
5. **NEVER add up timeseries values** - The summary already has the correct totals
6. **Don't list individual daily values** - The chart handles visualization
7. **Keep responses concise** - 2-3 sentences max

**EXAMPLE - Given this tool result:**
```json
{
  "summary": {
    "spend": {
      "value": 28579.86,
      "previous": 31543.84,
      "delta_pct": -0.094
    }
  },
  "time_range_resolved": {
    "start": "2025-11-30",
    "end": "2025-12-29"
  }
}
```

**CORRECT response (includes dates for clarity):**
"Your spend for the last 30 days (Nov 30 - Dec 29) was $28,580, down 9.4% from the previous 30 days' $31,544."

**ALSO CORRECT:**
"From Nov 30 to Dec 29, you spent $28,580. That's down 9.4% compared to the prior period ($31,544)."

**WRONG (ambiguous - what does 'last month' mean?):**
"Your spend for last month was $28,580..." ← User doesn't know if this means November or last 30 days!

**WRONG (hallucinated number):**
"Your spend was $28,580, down from $60,124." ← WRONG NUMBER!

## DATE CLARITY (IMPORTANT)

The tool uses **rolling time windows**, NOT calendar months:
- "7d" = last 7 days from today
- "30d" = last 30 days from today (NOT "November" or "last month")
- "90d" = last 90 days from today

**ALWAYS include the actual date range** from `time_range_resolved` in your response so users know exactly what period you're referring to.

## TOOL CALLING EFFICIENCY (CRITICAL)

**For period comparisons (this week vs last week, this month vs last month):**
- Use ONE call with `compare_to_previous: true`
- This returns BOTH periods: `summary.value` (current) and `summary.previous` (previous)
- Do NOT make multiple calls for different time ranges

**WRONG (2 calls):**
```
query_metrics(time_range="30d") → $28,580
query_metrics(time_range="60d") → $60,140  ← This is CUMULATIVE, not "month before"!
```

**CORRECT (1 call):**
```
query_metrics(time_range="30d", compare_to_previous=true)
→ value: $28,580 (last 30 days)
→ previous: $31,544 (30 days before that)
```

## DATA SOURCE PRIORITY (CRITICAL)

**ALWAYS use query_metrics FIRST** for any metrics question. Our database has snapshots updated every 15 minutes.

1. **query_metrics** (DATABASE - Fast, no external API calls)
   - Use for: spend, ROAS, CPC, CTR, conversions, revenue, profit
   - Even for "today" questions - snapshots are only ~15 min old
   - Returns: data + snapshot_time + snapshot_age_minutes
   - **For comparisons**: Set `compare_to_previous: true` to get both periods in ONE call
   - For graphs/charts: set `include_timeseries: true`
   - For comparisons: set `compare_to_previous: true`

2. **google_ads_query / meta_ads_query** (LIVE API - Slower, rate limited)
   - Use ONLY when query_metrics can't answer:
     - Campaign start_date, end_date ("went live yesterday")
     - Keywords, search terms ("what keywords am I targeting")
     - Audiences, targeting details
   - Or when user explicitly asks for "real-time" / "live" data

## RESPONSE FORMAT

**Always include data freshness in your response:**
- ✅ "Your spend today is $1,234 (data from 12:30 PM, ~8 min ago)"
- ✅ "Your ROAS is 3.2x (live from Google Ads)"
- ❌ "Your ROAS is 3.2x" (no context - BAD!)

## DECISION EXAMPLES

| Question | Tool to Use |
|----------|-------------|
| "What's my spend today?" | query_metrics ✓ |
| "What's my ROAS?" | query_metrics ✓ |
| "Which campaigns went live yesterday?" | google_ads_query (needs start_date) |
| "What keywords am I targeting?" | google_ads_query (not in snapshots) |
| "What's my spend RIGHT NOW?" | google_ads_query/meta_ads_query (explicit live request) |
| "Compare CPC this week vs last" | query_metrics ✓ |

## OTHER TOOLS

- **list_entities**: Find campaigns/adsets/ads by name from our database
- **get_business_context**: Get company info (name, industry, etc.)

## HANDLING USER FEEDBACK

If the user says the data is wrong, incorrect, doesn't match, or expresses doubt about the numbers:

1. **Acknowledge**: "I apologize for any discrepancy. Let me verify this with live data."

2. **Explain previous source**: Tell them the previous data came from our cached snapshots
   (which are updated every 15 minutes from the ad platforms).

3. **Fetch live data**: Immediately call google_ads_query or meta_ads_query with query_type="metrics"
   to get FRESH data directly from the ad platform.

4. **Compare and report**: Show the live data and note any differences from the snapshot.

Example triggers: "this is wrong", "that's not right", "doesn't match", "data is incorrect",
"my Google Ads shows different", "that can't be right", "check again"

Example response flow:
User: "This is wrong, my Google Ads shows different numbers"
→ You: "I apologize for the discrepancy. The previous numbers came from our cached data (updated every ~15 min).
   Let me fetch live data directly from Google Ads to verify..."
→ Call: google_ads_query(query_type="metrics", date_range="today")
→ You: "Here's what Google Ads shows right now: [live numbers]. The difference was likely due to
   [recent activity / sync timing / etc.]"

## PROVIDER ATTRIBUTION (CRITICAL)

**NEVER attribute data to the wrong provider!**

- If user asks about "Meta" but query_metrics returns data without a provider filter, that data is from ALL connected providers (likely Google only if Meta shows "not connected")
- If a tool returns an error like "Meta Ads not connected", DO NOT use data from other tools and call it "Meta data"
- ALWAYS check which provider the data actually came from

**WRONG:**
User: "How's Meta doing?"
Tool 1: query_metrics → returns $28,000 (this is Google data!)
Tool 2: meta_ads_query → Error: "Meta Ads not connected"
Response: "Your Meta Ads spend is $28,000" ← WRONG! This is Google data!

**CORRECT:**
Response: "Meta Ads is not connected to your account. The $28,000 spend shown is from Google Ads. To see Meta performance, please connect your Meta account in Settings → Connections."

## IMPORTANT

- If you need data you don't have, USE A TOOL to get it
- Don't guess or make up data
- If a tool fails, try a different approach or explain the limitation
- Be concise and actionable in your responses
- When user questions data accuracy, ALWAYS fetch live data to verify
- **NEVER mislabel data from one provider as another provider's data**

When you have enough information to answer, respond directly without calling more tools."""

# Guardrails for the agent loop
MAX_ITERATIONS = 5
MAX_TOOL_CALLS_PER_ITERATION = 3
TOOL_EXECUTION_TIMEOUT = 30  # seconds


import asyncio


async def agent_loop_node(
    state: AgentState,
    db: Session,
    publisher: Optional[StreamPublisher | AsyncQueuePublisher] = None,
) -> Dict[str, Any]:
    """
    Free-form ReAct-style agent that lets LLM decide what tools to call.

    WHAT: Single node that loops until LLM has enough info to answer.

    WHY: Replaces rigid intent classification with flexible tool selection.
         LLM sees ALL tools and picks the right one based on the question.

    FLOW:
        1. Send question + tools to LLM
        2. If LLM returns tool_calls → execute them, add results to messages, loop
        3. If LLM returns content (no tool_calls) → done, return answer
        4. Max 5 iterations to prevent runaway

    GUARDRAILS:
        - Max 5 iterations
        - Max 3 tool calls per iteration
        - 30s timeout per tool execution
        - Rate limits enforced per tool

    RETURNS:
        State updates: answer_chunks, tool_calls_made, iterations, stage
    """
    logger.info(
        f"[AGENT] Starting agent loop: {state.get('current_question', '')[:50]}..."
    )

    if publisher:
        publisher.thinking("Understanding your question...")

    workspace_id = state["workspace_id"]
    user_id = state.get("user_id", "")

    # Fetch business context for personalization
    business_context = (
        _fetch_workspace_context(db, workspace_id) if workspace_id else None
    )
    context_prompt = _build_business_context_prompt(business_context)

    # Build system prompt with optional business context
    system_prompt = AGENT_SYSTEM_PROMPT
    if context_prompt:
        system_prompt = f"{context_prompt}\n{AGENT_SYSTEM_PROMPT}"

    # Initialize messages for OpenAI
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["current_question"]},
    ]

    # Add conversation history if available
    history = state.get("messages", [])
    if history and len(history) > 1:  # Exclude current question which is last
        for msg in history[:-1]:
            role = msg.role.value if hasattr(msg, "role") else msg.get("role", "user")
            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
            messages.insert(-1, {"role": role, "content": content})

    client = get_async_openai_client()
    iteration = 0
    tool_calls_made = []
    answer_chunks = []

    # Track query_metrics results for building visuals
    collected_data = {}
    collected_semantic_query = {}

    while iteration < MAX_ITERATIONS:
        iteration += 1
        logger.info(f"[AGENT] Iteration {iteration}/{MAX_ITERATIONS}")

        try:
            # Call LLM with tools
            response = await client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                tools=AGENT_TOOLS,
                tool_choice="auto",  # LLM decides
                max_tokens=2048,
            )

            message = response.choices[0].message

            # If no tool calls, LLM is ready to answer
            if not message.tool_calls:
                logger.info(f"[AGENT] LLM ready to answer (iteration {iteration})")

                # Stream the answer to publisher
                answer = message.content or ""
                answer_chunks = [answer]

                if publisher and answer:
                    # Stream character by character for typing effect
                    for char in answer:
                        publisher.answer_token(char)

                # Build visuals from collected data (if any query_metrics was called)
                visuals = None
                if collected_data:
                    visuals = _build_visuals_from_data(
                        collected_data, collected_semantic_query
                    )
                    if publisher and visuals:
                        publisher.visual(visuals)

                return {
                    "answer_chunks": answer_chunks,
                    "tool_calls_made": tool_calls_made,
                    "iterations": iteration,
                    "visuals": visuals,
                    "data": collected_data,
                    "stage": "done",
                }

            # Execute tool calls
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
            )

            for tool_call in message.tool_calls[:MAX_TOOL_CALLS_PER_ITERATION]:
                tool_name = tool_call.function.name
                tool_args_str = tool_call.function.arguments

                try:
                    tool_args = json.loads(tool_args_str)
                except json.JSONDecodeError:
                    tool_args = {}

                logger.info(f"[AGENT] Executing tool: {tool_name}({tool_args})")

                # Emit tool_start event
                if publisher:
                    publisher.tool_start(tool_name, tool_args)

                # Track execution time
                import time

                start_time = time.time()

                # Execute the tool
                try:
                    result = await execute_tool_async(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        db=db,
                        workspace_id=workspace_id,
                        user_id=user_id,
                    )

                    duration_ms = int((time.time() - start_time) * 1000)
                    data_source = result.get("data_source", "snapshots")
                    success = result.get("success", not result.get("error"))

                    tool_calls_made.append(
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "success": success,
                            "duration_ms": duration_ms,
                            "data_source": data_source,
                        }
                    )

                    # Collect data from query_metrics for building visuals
                    if tool_name == "query_metrics" and success and result.get("data"):
                        collected_data = result.get("data", {})
                        collected_semantic_query = (
                            tool_args  # Store the query args for visual building
                        )
                        logger.info(
                            f"[AGENT] Collected data for visuals: {list(collected_data.keys())}"
                        )

                    # Emit tool_end event with timing and data source
                    if publisher:
                        if success:
                            preview = _get_tool_result_preview(tool_name, result)
                            publisher.tool_end(
                                tool_name,
                                preview,
                                success=True,
                                duration_ms=duration_ms,
                                data_source=data_source,
                            )
                        else:
                            publisher.tool_end(
                                tool_name,
                                f"Error: {result.get('error', 'Unknown error')}",
                                success=False,
                                duration_ms=duration_ms,
                            )

                except asyncio.TimeoutError:
                    duration_ms = int((time.time() - start_time) * 1000)
                    logger.warning(f"[AGENT] Tool {tool_name} timed out")
                    result = {
                        "error": f"Tool {tool_name} timed out after {TOOL_EXECUTION_TIMEOUT}s"
                    }
                    tool_calls_made.append(
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "success": False,
                            "error": "timeout",
                            "duration_ms": duration_ms,
                        }
                    )
                    if publisher:
                        publisher.tool_end(
                            tool_name,
                            "Timed out",
                            success=False,
                            duration_ms=duration_ms,
                        )

                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    logger.exception(f"[AGENT] Tool {tool_name} failed: {e}")
                    result = {"error": str(e)}
                    tool_calls_made.append(
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "success": False,
                            "error": str(e),
                            "duration_ms": duration_ms,
                        }
                    )
                    if publisher:
                        publisher.tool_end(
                            tool_name,
                            f"Error: {str(e)}",
                            success=False,
                            duration_ms=duration_ms,
                        )

                # Add tool result to messages (summarized for LLM, not full data)
                # We summarize timeseries data to prevent LLM from listing individual values
                summarized_result = _summarize_tool_result_for_llm(tool_name, result)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(summarized_result, default=str),
                    }
                )

        except Exception as e:
            logger.exception(f"[AGENT] LLM call failed: {e}")
            return {
                "error": f"Agent failed: {str(e)}",
                "tool_calls_made": tool_calls_made,
                "iterations": iteration,
                "stage": "error",
            }

    # Max iterations reached
    logger.warning(f"[AGENT] Max iterations ({MAX_ITERATIONS}) reached")
    fallback = "I wasn't able to fully answer your question. Please try rephrasing or being more specific."

    if publisher:
        publisher.answer_chunk(fallback)

    # Still try to build visuals if we collected any data
    visuals = None
    if collected_data:
        visuals = _build_visuals_from_data(collected_data, collected_semantic_query)
        if publisher and visuals:
            publisher.visual(visuals)

    return {
        "answer_chunks": [fallback],
        "tool_calls_made": tool_calls_made,
        "iterations": iteration,
        "visuals": visuals,
        "data": collected_data,
        "stage": "done",
    }


async def execute_tool_async(
    tool_name: str,
    tool_args: Dict[str, Any],
    db: Session,
    workspace_id: str,
    user_id: str = "",
) -> Dict[str, Any]:
    """
    Execute a tool asynchronously and return results.

    WHAT: Dispatcher for tool execution with async support.

    WHY: Tools are blocking (DB queries, API calls) so we run them
         in a thread pool to not block the event loop.

    PARAMETERS:
        tool_name: Name of the tool to execute
        tool_args: Arguments for the tool
        db: SQLAlchemy session
        workspace_id: Current workspace UUID
        user_id: Current user UUID

    RETURNS:
        Tool result dict with success/error status
    """

    if tool_name == "query_metrics":
        # Use existing SemanticTools - ADD SNAPSHOT FRESHNESS INFO
        def run_sync():
            tools = SemanticTools(db, workspace_id, user_id)
            result = tools.query_metrics(**tool_args)

            # Add snapshot freshness info
            from datetime import datetime, date

            snapshot_time = _get_latest_snapshot_time(db, workspace_id)
            if snapshot_time:
                # Handle both date and datetime types
                if isinstance(snapshot_time, date) and not isinstance(
                    snapshot_time, datetime
                ):
                    # It's a date, convert to datetime at end of day for comparison
                    snapshot_datetime = datetime.combine(
                        snapshot_time, datetime.max.time()
                    )
                    age_days = (date.today() - snapshot_time).days
                    result["snapshot_time"] = snapshot_time.strftime("%b %d, %Y")
                    result["snapshot_age_days"] = age_days
                    result["snapshot_age_minutes"] = age_days * 24 * 60  # Approximate
                else:
                    # It's a datetime
                    age_minutes = (
                        datetime.utcnow() - snapshot_time
                    ).total_seconds() / 60
                    result["snapshot_time"] = snapshot_time.strftime("%I:%M %p")
                    result["snapshot_age_minutes"] = round(age_minutes)
                result["data_source"] = "snapshots (updated every 15 min)"

            return result

        return await asyncio.to_thread(run_sync)

    elif tool_name == "google_ads_query":
        # Use GoogleAdsClient for live queries
        def run_sync():
            return _execute_google_ads_query(db, workspace_id, tool_args)

        return await asyncio.to_thread(run_sync)

    elif tool_name == "meta_ads_query":
        # Use Meta Ads API for live queries
        def run_sync():
            return _execute_meta_ads_query(db, workspace_id, tool_args)

        return await asyncio.to_thread(run_sync)

    elif tool_name == "list_entities":
        # Use SemanticTools.get_entities
        def run_sync():
            tools = SemanticTools(db, workspace_id, user_id)
            result = tools.get_entities(**tool_args)
            result["data_source"] = "database"
            return result

        return await asyncio.to_thread(run_sync)

    elif tool_name == "get_business_context":

        def run_sync():
            context = _fetch_workspace_context(db, workspace_id)
            if context:
                context["data_source"] = "workspace_settings"
                return context
            return {
                "success": True,
                "message": "No business profile configured. Set it up in Settings → Business.",
                "data_source": "workspace_settings",
            }

        return await asyncio.to_thread(run_sync)

    else:
        return {"error": f"Unknown tool: {tool_name}", "data_source": "none"}


def _get_latest_snapshot_time(db: Session, workspace_id: str):
    """
    Get the most recent snapshot time for this workspace.

    WHY: So we can tell the user how fresh their data is.
    """
    from sqlalchemy import func
    from app.models import MetricSnapshot, Entity

    try:
        result = (
            db.query(func.max(MetricSnapshot.metrics_date))
            .join(Entity)
            .filter(Entity.workspace_id == workspace_id)
            .scalar()
        )
        return result
    except Exception as e:
        logger.warning(f"[AGENT] Failed to get snapshot time: {e}")
        return None


def _summarize_tool_result_for_llm(
    tool_name: str, result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a summarized version of tool result for the LLM.

    WHAT: Removes verbose timeseries data to prevent LLM from listing individual values.

    WHY: The LLM tends to repeat timeseries values in its response, which:
         1. Creates long, unhelpful responses
         2. Sometimes hallucinates values
         3. Duplicates what the chart already shows

    HOW: For query_metrics results, we:
         - Keep summary (totals, delta_pct)
         - Keep breakdown (entity comparisons)
         - Replace timeseries with a simple "data_points: N" indicator
         - Add a note telling LLM not to list individual values
    """
    if tool_name != "query_metrics":
        return result

    if not result.get("success") or not result.get("data"):
        return result

    # Deep copy to avoid modifying original
    summarized = {
        "success": result.get("success"),
        "snapshot_time": result.get("snapshot_time"),
        "snapshot_age_minutes": result.get("snapshot_age_minutes"),
        "data_source": result.get("data_source"),
    }

    data = result.get("data", {})
    summarized_data = {}

    # Keep summary as-is (this has the totals)
    if data.get("summary"):
        summarized_data["summary"] = data["summary"]

    # Keep breakdown as-is (entity comparisons)
    if data.get("breakdown"):
        summarized_data["breakdown"] = data["breakdown"]

    # Keep entity_comparison as-is
    if data.get("entity_comparison"):
        summarized_data["entity_comparison"] = data["entity_comparison"]

    # SUMMARIZE timeseries instead of passing full data
    if data.get("timeseries"):
        timeseries = data["timeseries"]
        timeseries_summary = {}
        for metric, points in timeseries.items():
            if isinstance(points, list) and len(points) > 0:
                # Just tell LLM how many points, not the actual values
                timeseries_summary[metric] = {
                    "data_points": len(points),
                    "first_date": points[0].get("date") if points else None,
                    "last_date": points[-1].get("date") if points else None,
                    "note": "Chart will display these values visually. Do NOT list individual values in your response.",
                }
        summarized_data["timeseries_info"] = timeseries_summary

    # Keep time_range_resolved
    if data.get("time_range_resolved"):
        summarized_data["time_range_resolved"] = data["time_range_resolved"]

    summarized["data"] = summarized_data

    # Add instruction for LLM
    summarized["response_instructions"] = (
        "Use summary values for totals and percentages. "
        "The chart will show daily breakdown - do NOT list individual daily values."
    )

    return summarized


def _get_tool_result_preview(tool_name: str, result: Dict[str, Any]) -> str:
    """Generate a short preview of tool result for streaming."""

    if result.get("error"):
        return f"Error: {result['error']}"

    if tool_name == "query_metrics":
        data = result.get("data", {})
        summary = data.get("summary", {})
        parts = []
        for metric, values in summary.items():
            if isinstance(values, dict) and values.get("value") is not None:
                val = values["value"]
                if metric in ["spend", "revenue"]:
                    parts.append(f"{metric}: ${val:,.2f}")
                elif metric in ["roas", "poas"]:
                    parts.append(f"{metric}: {val:.2f}×")
                else:
                    parts.append(f"{metric}: {val:.2f}")
        if result.get("snapshot_time"):
            parts.append(f"(data from {result['snapshot_time']})")
        return ", ".join(parts) if parts else "Data retrieved"

    elif tool_name in ["google_ads_query", "meta_ads_query"]:
        data = result.get("data", {})
        if isinstance(data, list):
            return f"Found {len(data)} results"
        elif isinstance(data, dict):
            return f"Retrieved {len(data)} fields"
        return "Live data retrieved"

    elif tool_name == "list_entities":
        entities = result.get("entities", [])
        return f"Found {len(entities)} entities"

    elif tool_name == "get_business_context":
        return "Business context retrieved"

    return "Tool executed"


def _execute_google_ads_query(
    db: Session,
    workspace_id: str,
    tool_args: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a Google Ads API query.

    WHY: Fetches data not available in snapshots (start_date, keywords, etc.)
    """
    from app.agent.connection_resolver import ConnectionResolver
    from app.agent.exceptions import ProviderNotConnectedError, TokenExpiredError
    from datetime import date, timedelta

    try:
        # Get authenticated client from ConnectionResolver
        resolver = ConnectionResolver(db, workspace_id)

        try:
            client = resolver.get_google_client()
            customer_id = resolver.get_account_id("google")
        except ProviderNotConnectedError:
            return {
                "error": "Google Ads not connected. Please connect in Settings → Connections.",
                "data_source": "live_google_ads",
            }
        except TokenExpiredError as e:
            return {
                "error": f"Google Ads authentication expired: {e.message}. Please reconnect in Settings.",
                "data_source": "live_google_ads",
            }
        query_type = tool_args.get("query_type", "campaigns")
        filters = tool_args.get("filters", {})
        entity_id = tool_args.get("entity_id")
        date_range = tool_args.get("date_range")

        # Execute based on query_type
        if query_type == "campaigns":
            result = client.get_campaigns_with_config(customer_id, filters)
        elif query_type == "keywords":
            result = client.list_keywords(customer_id, entity_id)
        elif query_type == "search_terms":
            result = client.list_search_terms(customer_id, entity_id)
        elif query_type == "ad_groups":
            if entity_id:
                result = client.list_ad_groups(customer_id, entity_id)
            else:
                result = client.list_all_ad_groups(customer_id)
        elif query_type == "ads":
            if entity_id:
                result = client.list_ads(customer_id, entity_id)
            else:
                result = client.list_all_ads(customer_id)
        elif query_type == "metrics" and date_range:
            # Parse date range
            if date_range == "today":
                start = date.today()
                end = date.today()
            elif date_range == "yesterday":
                start = date.today() - timedelta(days=1)
                end = date.today() - timedelta(days=1)
            elif date_range == "last_7d":
                end = date.today() - timedelta(days=1)
                start = end - timedelta(days=6)
            elif date_range == "last_30d":
                end = date.today() - timedelta(days=1)
                start = end - timedelta(days=29)
            else:
                end = date.today() - timedelta(days=1)
                start = end - timedelta(days=6)
            result = client.fetch_daily_metrics(customer_id, start, end)
        else:
            # Fallback to list_campaigns for unsupported types
            result = client.list_campaigns(customer_id)

        return {
            "success": True,
            "data": result,
            "data_source": "live_google_ads",
        }

    except Exception as e:
        logger.exception(f"[AGENT] Google Ads query failed: {e}")
        return {
            "error": str(e),
            "data_source": "live_google_ads",
        }


def _execute_meta_ads_query(
    db: Session,
    workspace_id: str,
    tool_args: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a Meta Ads API query.

    WHY: Fetches data not available in snapshots (creatives, audiences, etc.)
    """
    from app.agent.connection_resolver import ConnectionResolver
    from app.agent.exceptions import ProviderNotConnectedError, TokenExpiredError

    try:
        # Get authenticated client from ConnectionResolver
        resolver = ConnectionResolver(db, workspace_id)

        try:
            client = resolver.get_meta_client()
            account_id = resolver.get_account_id("meta")
        except ProviderNotConnectedError:
            return {
                "error": "Meta Ads not connected. Please connect in Settings → Connections.",
                "data_source": "live_meta_ads",
            }
        except TokenExpiredError as e:
            return {
                "error": f"Meta Ads authentication expired: {e.message}. Please reconnect in Settings.",
                "data_source": "live_meta_ads",
            }

        # TODO: Implement Meta Ads API client methods similar to GoogleAdsClient
        # For now, return a helpful message
        query_type = tool_args.get("query_type", "campaigns")

        return {
            "success": False,
            "error": f"Meta Ads live query for '{query_type}' not yet implemented. Using cached data.",
            "data_source": "live_meta_ads",
        }

    except Exception as e:
        logger.exception(f"[AGENT] Meta Ads query failed: {e}")
        return {
            "error": str(e),
            "data_source": "live_meta_ads",
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _build_visuals_from_data(
    data: Dict[str, Any],
    semantic_query: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Build visual specs from compilation result."""

    if not data:
        return None

    visuals = {"viz_specs": [], "tables": []}
    metrics = semantic_query.get("metrics") or ["roas"]
    primary_metric = metrics[0] if metrics else "roas"

    # Timeseries chart (area chart for trends, line chart for comparisons)
    timeseries = data.get("timeseries", {})

    # Group metrics and their previous-period counterparts
    base_metrics = set()
    previous_metrics = set()
    for key in timeseries.keys():
        if key.endswith("_previous"):
            previous_metrics.add(key)
            base_metrics.add(key.replace("_previous", ""))
        else:
            base_metrics.add(key)

    for metric in base_metrics:
        current_points = timeseries.get(metric, [])
        previous_points = timeseries.get(f"{metric}_previous", [])

        if not current_points:
            continue

        # If we have previous period data, create an overlaid comparison line chart
        if previous_points:
            # Normalize X-axis to "Day 1", "Day 2", etc. for proper overlay
            # (The dates are different between periods, so we use relative days)
            current_data = [
                {"x": f"Day {i + 1}", "y": p.get("value")}
                for i, p in enumerate(current_points)
            ]
            previous_data = [
                {"x": f"Day {i + 1}", "y": p.get("value")}
                for i, p in enumerate(previous_points)
            ]

            spec = {
                "id": f"comparison-timeseries-{metric}",
                "type": "line",
                "title": f"{metric.upper()} Comparison",
                "valueFormat": metric,
                "isComparison": True,
                "series": [
                    {
                        "name": "This Period",
                        "data": current_data,
                    },
                    {
                        "name": "Previous Period",
                        "data": previous_data,
                    },
                ],
            }
            visuals["viz_specs"].append(spec)
        else:
            # Single period - use area chart
            spec = {
                "id": f"timeseries-{metric}",
                "type": "area",
                "title": f"{metric.upper()} Trend",
                "valueFormat": metric,
                "series": [
                    {
                        "name": metric.upper(),
                        "data": [
                            {"x": p.get("date"), "y": p.get("value")}
                            for p in current_points
                        ],
                    }
                ],
            }
            visuals["viz_specs"].append(spec)

    # Comparison bar chart (this period vs last period)
    # Only create bar chart if we don't have a timeseries comparison for this metric
    summary = data.get("summary", {})
    metrics_with_timeseries_comparison = previous_metrics  # Already has line chart
    if summary:
        for metric, values in summary.items():
            if isinstance(values, dict) and values.get("previous") is not None:
                # Skip bar chart if we already have a line chart for this metric
                if f"{metric}_previous" in metrics_with_timeseries_comparison:
                    continue

                current_val = values.get("value", 0)
                previous_val = values.get("previous", 0)
                delta_pct = values.get("delta_pct", 0)

                # Create comparison bar chart (fallback when no timeseries)
                spec = {
                    "id": f"comparison-bar-{metric}",
                    "type": "bar",
                    "title": f"{metric.upper()} Comparison",
                    "valueFormat": metric,
                    "series": [
                        {
                            "name": metric.upper(),
                            "data": [
                                {"x": "Previous Period", "y": previous_val},
                                {"x": "This Period", "y": current_val},
                            ],
                        }
                    ],
                    "delta_pct": delta_pct,
                }
                visuals["viz_specs"].append(spec)

    # Breakdown chart (bar chart for rankings)
    breakdown = data.get("breakdown", [])
    if breakdown:
        spec = {
            "id": f"breakdown-{primary_metric}",
            "type": "bar",
            "title": f"{primary_metric.upper()} by {semantic_query.get('breakdown_level', 'campaign')}",
            "valueFormat": primary_metric,
            "series": [
                {
                    "name": primary_metric.upper(),
                    "data": [
                        {"x": item.get("label"), "y": item.get("value")}
                        for item in breakdown
                    ],
                }
            ],
        }
        visuals["viz_specs"].append(spec)

        # Multi-metric breakdown table (when multiple metrics requested)
        if len(metrics) > 1 and breakdown:
            # Build columns for each metric
            columns = [{"key": "entity", "label": "Campaign", "format": "text"}]
            for m in metrics:
                columns.append({"key": m, "label": m.upper(), "format": m})

            # Build rows from breakdown data
            rows = []
            for item in breakdown:
                row = {"entity": item.get("label")}

                # Get raw values for calculations
                spend = float(item.get("spend") or 0)
                revenue = float(item.get("revenue") or 0)

                for m in metrics:
                    # Try to get metric from item directly
                    if m == primary_metric:
                        row[m] = item.get("value")
                    elif m == "roas":
                        # Calculate ROAS if not directly available
                        if item.get("roas") is not None:
                            row[m] = item.get("roas")
                        elif spend > 0:
                            row[m] = revenue / spend
                        else:
                            row[m] = 0
                    elif m == "profit":
                        # Calculate profit if not directly available
                        if item.get("profit") is not None:
                            row[m] = item.get("profit")
                        else:
                            row[m] = revenue - spend
                    elif m == "cpa":
                        # Calculate CPA (cost per acquisition) if not directly available
                        conversions = float(item.get("conversions") or 0)
                        if item.get("cpa") is not None:
                            row[m] = item.get("cpa")
                        elif conversions > 0:
                            row[m] = spend / conversions
                        else:
                            row[m] = 0
                    elif m == "cpc":
                        # Calculate CPC if not directly available
                        clicks = float(item.get("clicks") or 0)
                        if item.get("cpc") is not None:
                            row[m] = item.get("cpc")
                        elif clicks > 0:
                            row[m] = spend / clicks
                        else:
                            row[m] = 0
                    elif m == "ctr":
                        # Calculate CTR if not directly available
                        clicks = float(item.get("clicks") or 0)
                        impressions = float(item.get("impressions") or 0)
                        if item.get("ctr") is not None:
                            row[m] = item.get("ctr")
                        elif impressions > 0:
                            row[m] = clicks / impressions
                        else:
                            row[m] = 0
                    else:
                        row[m] = item.get(m)
                rows.append(row)

            table = {
                "id": f"breakdown-table-{'_'.join(metrics)}",
                "type": "metrics_table",
                "title": f"Performance by {semantic_query.get('breakdown_level', 'Campaign')}",
                "columns": columns,
                "rows": rows,
            }
            visuals["tables"].append(table)

    # Entity comparison table
    entity_comparison = data.get("entity_comparison", [])
    if entity_comparison:
        table = {
            "id": f"comparison-table-{primary_metric}",
            "type": "comparison_table",
            "title": f"{primary_metric.upper()} Comparison",
            "columns": [
                {"key": "entity", "label": "Entity", "format": "text"},
                {"key": "current", "label": "This Period", "format": primary_metric},
                {"key": "previous", "label": "Previous", "format": primary_metric},
                {"key": "delta_pct", "label": "Change", "format": "percent"},
            ],
            "rows": [
                {
                    "entity": item.get("entity_name"),
                    "current": item.get("current_value"),
                    "previous": item.get("previous_value"),
                    "delta_pct": item.get("delta_pct"),
                }
                for item in entity_comparison
            ],
        }
        visuals["tables"].append(table)

    return visuals if (visuals["viz_specs"] or visuals["tables"]) else None


def _make_error_friendly(error: str) -> str:
    """Convert technical error to user-friendly message."""

    error_lower = error.lower()

    if "timeout" in error_lower:
        return "The query took too long. Try asking about a shorter time period."

    if "no data" in error_lower or "not found" in error_lower:
        return "I couldn't find any data for that query. Make sure the campaign or ad exists and has activity in the time period."

    if "validation" in error_lower:
        return "I didn't quite understand that. Could you rephrase your question?"

    if "metric" in error_lower:
        return "I'm not sure which metric you're asking about. Try asking about spend, revenue, ROAS, CPC, or CTR."

    # Generic fallback
    return (
        "I ran into an issue processing your question. "
        "Please try rephrasing it, or ask about a specific metric like ROAS or spend."
    )
