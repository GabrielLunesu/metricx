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
        limit: int = 5,
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
        logger.info(f"[TOOLS] query_metrics: {metrics}, range={time_range}, breakdown={breakdown_level}")

        try:
            # Validate metrics
            valid_metrics = get_all_metric_names()
            for m in metrics:
                if m.lower() not in valid_metrics:
                    return {"error": f"Unknown metric: {m}. Valid metrics: {', '.join(sorted(valid_metrics))}"}

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
                if filters.get("provider") and filters["provider"] in ["meta", "google", "tiktok"]:
                    query.filters.append(Filter(
                        field="provider",
                        operator="=",
                        value=filters["provider"],
                    ))
                if filters.get("entity_name"):
                    query.filters.append(Filter(
                        field="entity_name",
                        operator="contains",
                        value=filters["entity_name"],
                    ))
                # Ignore any other filter fields (like conversions, spend, etc.)
                # These are metric values, not filter fields

            # Validate
            validation = self.validator.validate(query)
            if not validation.valid:
                return {"error": validation.to_user_message()}

            # Compile and execute
            result = self.compiler.compile(self.workspace_id, query)

            # Convert to dict
            return {
                "success": True,
                "query": query.to_dict(),
                "data": result.to_dict(),
            }

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
                query.filters.append(Filter(
                    field="entity_name",
                    operator="contains",
                    value=name_contains,
                ))

            result = self.compiler.compile(self.workspace_id, query)

            entities = []
            for item in result.breakdown:
                entities.append({
                    "id": item.entity_id,
                    "name": item.label,
                    "spend": item.spend,
                })

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
            change_str = f"{abs(change_pct)*100:.1f}%"

            # Find top contributors from entity comparison
            entity_comparison = result_dict.get("entity_comparison", [])
            contributors = []
            for item in entity_comparison[:5]:
                if item.get("delta_pct") is not None:
                    item_dir = "up" if item["delta_pct"] > 0 else "down"
                    contributors.append({
                        "name": item["entity_name"],
                        "change_pct": item["delta_pct"],
                        "direction": item_dir,
                        "current": item["current_value"],
                        "previous": item["previous_value"],
                    })

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

    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to days."""
        time_range = time_range.lower().strip()
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
    tools = SemanticTools(db, workspace_id, user_id)

    if tool_name == "query_metrics":
        return tools.query_metrics(**tool_args)
    elif tool_name == "get_entities":
        return tools.get_entities(**tool_args)
    elif tool_name == "analyze_change":
        return tools.analyze_change(**tool_args)
    else:
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

Always use query_metrics for data questions. Use analyze_change for "why" questions.
"""
