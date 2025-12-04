"""
Agent Nodes
===========

**Version**: 1.0.0
**Created**: 2025-12-03

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

from anthropic import Anthropic
from sqlalchemy.orm import Session

from app.agent.state import AgentState, Message, MessageRole
from app.agent.tools import SemanticTools, get_tool_schemas, get_tools_description
from app.agent.stream import StreamPublisher

logger = logging.getLogger(__name__)


# =============================================================================
# LLM CLIENT
# =============================================================================

def get_claude_client() -> Anthropic:
    """Get Anthropic client."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return Anthropic(api_key=api_key)


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
- clarification_needed: Ambiguous question
- out_of_scope: Cannot answer

EXTRACT THESE FIELDS:
- metrics: Which metrics (use exact names from list above - e.g., "cpc" not "cost per click")
- time_range: "1d", "3d", "7d", "30d", "90d" (parse "last 3 days" as "3d", "yesterday" as "1d")
- entities: Specific campaigns/ads mentioned by name
- breakdown_level: "campaign", "adset", "ad", "provider", or null
- compare_to_previous: true if comparing to previous period
- include_timeseries: true if user wants a graph/chart/trend, or if time range is specified
- filters: ONLY {provider: "meta"|"google"} or {entity_name: "..."}

EXAMPLES:
- "what's my cpc?" -> metrics: ["cpc"], include_timeseries: false
- "make a graph of cpc last 3 days" -> metrics: ["cpc"], time_range: "3d", include_timeseries: true
- "show me spend trend this week" -> metrics: ["spend"], time_range: "7d", include_timeseries: true
- "compare ROAS this week vs last week" -> metrics: ["roas"], compare_to_previous: true
- "give me spend, revenue, ROAS and profit for all campaigns" -> metrics: ["spend", "revenue", "roas", "profit"], breakdown_level: "campaign"
- "show me all Meta campaign metrics this month" -> metrics: ["spend", "revenue", "roas", "profit"], breakdown_level: "campaign", filters: {provider: "meta"}, time_range: "30d"
- "breakdown by campaign with spend and conversions" -> metrics: ["spend", "conversions"], breakdown_level: "campaign"

Respond in JSON format:
{
  "intent": "metric_query|comparison|ranking|analysis|clarification_needed|out_of_scope",
  "metrics": ["cpc"],
  "time_range": "7d",
  "entities": [],
  "breakdown_level": null,
  "compare_to_previous": false,
  "include_timeseries": false,
  "filters": {},
  "clarification_needed": "..." (if needed),
  "out_of_scope_reason": "..." (if out of scope)
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
        messages.append({
            "role": msg.role.value if hasattr(msg, 'role') else msg.get("role", "user"),
            "content": msg.content if hasattr(msg, 'content') else msg.get("content", ""),
        })

    # Add current question
    messages.append({
        "role": "user",
        "content": state["current_question"],
    })

    try:
        client = get_claude_client()

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=UNDERSTAND_PROMPT,
            messages=messages,
        )

        # Parse JSON response
        content = response.content[0].text
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
        logger.info(f"[NODE] Classified intent: {intent}")

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
                "error": parsed.get("out_of_scope_reason", "I can only answer questions about your advertising data."),
                "stage": "responding",
            }

        return {
            "intent": intent,
            "semantic_query": semantic_query,
            "stage": "fetching",
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
            "stage": "fetching",
        }

    except Exception as e:
        logger.exception(f"[NODE] understand failed: {e}")
        return {
            "error": f"Failed to understand question: {str(e)}",
            "stage": "error",
        }


def fetch_data_node(
    state: AgentState,
    db: Session,
    publisher: Optional[StreamPublisher] = None,
) -> Dict[str, Any]:
    """
    Fetch data from the semantic layer.

    WHAT: Calls semantic layer tools based on parsed query.

    WHY: Get the actual data to answer the question.

    PROCESS:
        1. Read semantic_query from state
        2. Call appropriate tool (query_metrics, analyze_change, etc.)
        3. Store result in state

    RETURNS:
        State updates: compilation_result
    """
    logger.info("[NODE] fetch_data")

    semantic_query = state.get("semantic_query", {})
    intent = state.get("intent", "metric_query")

    if publisher:
        publisher.thinking("Fetching your data...")

    workspace_id = state["workspace_id"]
    tools = SemanticTools(db, workspace_id, state.get("user_id"))

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
                    publisher.tool_result("analyze_change", f"{metric.upper()} {direction} {change}")
                else:
                    publisher.tool_result("analyze_change", "No change data available")

        else:
            # Use query_metrics for most queries
            if publisher:
                publisher.tool_call("query_metrics", semantic_query)

            result = tools.query_metrics(
                metrics=semantic_query.get("metrics", ["roas"]),
                time_range=semantic_query.get("time_range", "7d"),
                breakdown_level=semantic_query.get("breakdown_level"),
                limit=semantic_query.get("limit", 5),
                compare_to_previous=semantic_query.get("compare_to_previous", False),
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
                publisher.tool_result("query_metrics", ", ".join(preview_parts) if preview_parts else "Data retrieved")

        logger.info(f"[NODE] fetch_data result: {result.get('success', False)}")

        if result.get("error"):
            return {
                "error": result["error"],
                "stage": "error",
            }

        return {
            "compilation_result": result,
            "stage": "responding",
        }

    except Exception as e:
        logger.exception(f"[NODE] fetch_data failed: {e}")
        return {
            "error": f"Failed to fetch data: {str(e)}",
            "stage": "error",
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
        answer = state.get("clarification_question", "Could you please clarify your question?")
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

    compilation_result = state.get("compilation_result") or {}
    data = compilation_result.get("data") if isinstance(compilation_result, dict) else {}
    data = data or {}  # Ensure data is never None
    intent = state.get("intent", "metric_query")

    if publisher:
        publisher.thinking("Preparing your answer...")

    try:
        client = get_claude_client()

        # Build context message with data
        data_summary = json.dumps(data, indent=2, default=str)

        messages = [
            {
                "role": "user",
                "content": f"""User asked: "{state['current_question']}"

Intent: {intent}

Data retrieved:
{data_summary}

Please write a helpful, conversational response based on this data.""",
            }
        ]

        # Stream the response
        answer_chunks = []

        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=RESPOND_PROMPT,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
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
                {"x": f"Day {i+1}", "y": p.get("value")}
                for i, p in enumerate(current_points)
            ]
            previous_data = [
                {"x": f"Day {i+1}", "y": p.get("value")}
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
                "series": [{
                    "name": metric.upper(),
                    "data": [{"x": p.get("date"), "y": p.get("value")} for p in current_points],
                }],
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
                    "series": [{
                        "name": metric.upper(),
                        "data": [
                            {"x": "Previous Period", "y": previous_val},
                            {"x": "This Period", "y": current_val},
                        ],
                    }],
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
            "series": [{
                "name": primary_metric.upper(),
                "data": [{"x": item.get("label"), "y": item.get("value")} for item in breakdown],
            }],
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
