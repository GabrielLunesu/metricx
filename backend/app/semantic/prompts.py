"""
Semantic Layer Prompts
======================

**Version**: 1.0.0
**Created**: 2025-12-03
**Status**: Active

Prompt engineering for LLM translation to SemanticQuery format.
This is a CLEAN, SIMPLIFIED version replacing the legacy DSL prompts.

WHY THIS FILE EXISTS
--------------------
The old prompts.py (app/nlp/prompts.py) had ~2000 lines of examples
for the rigid DSL format. The SemanticQuery format is simpler and
more composable, requiring fewer examples.

KEY DIFFERENCES FROM OLD PROMPTS
--------------------------------
1. Composable components: breakdown + comparison + timeseries can combine
2. Simpler schema: fewer fields, clearer structure
3. No more mutually exclusive fields
4. Explicit composition detection

SCHEMA OVERVIEW
---------------
The LLM outputs this structure:
{
    "metrics": ["cpc", "roas"],           # One or more metrics
    "time_range": {"last_n_days": 7},     # Relative or absolute
    "breakdown": {                         # Optional grouping
        "dimension": "entity",
        "level": "campaign",
        "limit": 5,
        "sort_order": "desc"
    },
    "comparison": {                        # Optional comparison
        "type": "previous_period"
    },
    "include_timeseries": false,          # Optional timeseries
    "filters": [],                         # Optional filters
    "output_format": "auto"                # auto/chart/table/text
}

RELATED FILES
-------------
- app/semantic/query.py: SemanticQuery dataclass
- app/semantic/validator.py: Validates LLM output
- app/nlp/translator.py: Uses these prompts
- app/nlp/prompts.py: OLD prompts (being replaced)
"""

from __future__ import annotations

import json
from typing import List, Dict, Any


# =============================================================================
# SEMANTIC QUERY SCHEMA (for the LLM)
# =============================================================================

SEMANTIC_QUERY_SCHEMA = {
    "metrics": {
        "type": "array",
        "description": "One or more metric names",
        "items": {"type": "string"},
        "examples": ["roas", "cpc", "spend", "revenue", "ctr"]
    },
    "time_range": {
        "type": "object",
        "description": "Time period for the query",
        "oneOf": [
            {"properties": {"last_n_days": {"type": "integer"}}},
            {"properties": {"start": {"type": "string"}, "end": {"type": "string"}}}
        ]
    },
    "breakdown": {
        "type": "object",
        "nullable": True,
        "description": "How to group the data",
        "properties": {
            "dimension": {"enum": ["entity", "provider", "time"]},
            "level": {"enum": ["campaign", "adset", "ad"], "description": "Only for entity dimension"},
            "granularity": {"enum": ["day", "week", "month"], "description": "Only for time dimension"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
            "sort_order": {"enum": ["asc", "desc"], "default": "desc"}
        }
    },
    "comparison": {
        "type": "object",
        "nullable": True,
        "description": "Compare to previous period",
        "properties": {
            "type": {"enum": ["previous_period", "year_over_year"]},
            "include_timeseries": {"type": "boolean", "default": False}
        }
    },
    "include_timeseries": {
        "type": "boolean",
        "default": False,
        "description": "Include daily trend data"
    },
    "filters": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "field": {"enum": ["provider", "level", "status", "entity_name"]},
                "operator": {"enum": ["=", "!=", "in", "contains"]},
                "value": {}
            }
        }
    },
    "output_format": {
        "enum": ["auto", "chart", "table", "text"],
        "default": "auto"
    }
}


# =============================================================================
# FEW-SHOT EXAMPLES (Semantic Format)
# =============================================================================

SEMANTIC_EXAMPLES = [
    # Simple metric queries
    {
        "question": "What's my ROAS this week?",
        "query": {
            "metrics": ["roas"],
            "time_range": {"last_n_days": 7}
        }
    },
    {
        "question": "How much did I spend yesterday?",
        "query": {
            "metrics": ["spend"],
            "time_range": {"last_n_days": 1}
        }
    },

    # Comparison queries
    {
        "question": "Compare my spend this week vs last week",
        "query": {
            "metrics": ["spend"],
            "time_range": {"last_n_days": 7},
            "comparison": {"type": "previous_period"}
        }
    },
    {
        "question": "ROAS this month vs last month",
        "query": {
            "metrics": ["roas"],
            "time_range": {"last_n_days": 30},
            "comparison": {"type": "previous_period"}
        }
    },

    # Breakdown queries
    {
        "question": "Top 5 campaigns by ROAS",
        "query": {
            "metrics": ["roas"],
            "time_range": {"last_n_days": 7},
            "breakdown": {
                "dimension": "entity",
                "level": "campaign",
                "limit": 5,
                "sort_order": "desc"
            }
        }
    },
    {
        "question": "Which ad has the lowest CPC?",
        "query": {
            "metrics": ["cpc"],
            "time_range": {"last_n_days": 7},
            "breakdown": {
                "dimension": "entity",
                "level": "ad",
                "limit": 1,
                "sort_order": "asc"
            }
        }
    },
    {
        "question": "Show me all campaigns",
        "query": {
            "metrics": ["revenue"],
            "time_range": {"last_n_days": 7},
            "breakdown": {
                "dimension": "entity",
                "level": "campaign",
                "limit": 50,
                "sort_order": "desc"
            }
        }
    },

    # THE KEY FEATURE: Breakdown + Comparison (was impossible before!)
    {
        "question": "Compare CPC this week vs last week for top 3 ads",
        "query": {
            "metrics": ["cpc"],
            "time_range": {"last_n_days": 7},
            "breakdown": {
                "dimension": "entity",
                "level": "ad",
                "limit": 3,
                "sort_order": "desc"
            },
            "comparison": {"type": "previous_period"}
        }
    },
    {
        "question": "How did my top campaigns perform vs last week?",
        "query": {
            "metrics": ["roas"],
            "time_range": {"last_n_days": 7},
            "breakdown": {
                "dimension": "entity",
                "level": "campaign",
                "limit": 5,
                "sort_order": "desc"
            },
            "comparison": {"type": "previous_period"}
        }
    },

    # Breakdown + Timeseries (multi-line charts)
    {
        "question": "Graph daily spend for top 5 campaigns",
        "query": {
            "metrics": ["spend"],
            "time_range": {"last_n_days": 7},
            "breakdown": {
                "dimension": "entity",
                "level": "campaign",
                "limit": 5,
                "sort_order": "desc"
            },
            "include_timeseries": True,
            "output_format": "chart"
        }
    },
    {
        "question": "Show me daily ROAS for top 3 ads",
        "query": {
            "metrics": ["roas"],
            "time_range": {"last_n_days": 14},
            "breakdown": {
                "dimension": "entity",
                "level": "ad",
                "limit": 3,
                "sort_order": "desc"
            },
            "include_timeseries": True,
            "output_format": "chart"
        }
    },

    # Provider breakdown
    {
        "question": "Compare spend by platform",
        "query": {
            "metrics": ["spend"],
            "time_range": {"last_n_days": 7},
            "breakdown": {
                "dimension": "provider",
                "limit": 5,
                "sort_order": "desc"
            }
        }
    },
    {
        "question": "Which platform has the best ROAS?",
        "query": {
            "metrics": ["roas"],
            "time_range": {"last_n_days": 7},
            "breakdown": {
                "dimension": "provider",
                "limit": 1,
                "sort_order": "desc"
            }
        }
    },

    # Time breakdown
    {
        "question": "Show me weekly spend over the last month",
        "query": {
            "metrics": ["spend"],
            "time_range": {"last_n_days": 30},
            "breakdown": {
                "dimension": "time",
                "granularity": "week"
            }
        }
    },
    {
        "question": "Daily revenue trend",
        "query": {
            "metrics": ["revenue"],
            "time_range": {"last_n_days": 7},
            "include_timeseries": True,
            "output_format": "chart"
        }
    },

    # Filtered queries
    {
        "question": "Meta campaigns ROAS this week",
        "query": {
            "metrics": ["roas"],
            "time_range": {"last_n_days": 7},
            "filters": [
                {"field": "provider", "operator": "=", "value": "meta"}
            ]
        }
    },
    {
        "question": "Show me the Summer Sale campaign performance",
        "query": {
            "metrics": ["roas", "spend", "revenue"],
            "time_range": {"last_n_days": 7},
            "filters": [
                {"field": "entity_name", "operator": "contains", "value": "Summer Sale"}
            ]
        }
    },
    {
        "question": "Active campaigns by CPC",
        "query": {
            "metrics": ["cpc"],
            "time_range": {"last_n_days": 7},
            "breakdown": {
                "dimension": "entity",
                "level": "campaign",
                "limit": 10,
                "sort_order": "asc"
            },
            "filters": [
                {"field": "status", "operator": "=", "value": "active"}
            ]
        }
    },

    # Multiple metrics
    {
        "question": "Give me spend, revenue, and ROAS for last week",
        "query": {
            "metrics": ["spend", "revenue", "roas"],
            "time_range": {"last_n_days": 7}
        }
    },
    {
        "question": "CPC and CTR by campaign",
        "query": {
            "metrics": ["cpc", "ctr"],
            "time_range": {"last_n_days": 7},
            "breakdown": {
                "dimension": "entity",
                "level": "campaign",
                "limit": 10,
                "sort_order": "desc"
            }
        }
    },

    # Output format preferences
    {
        "question": "Compare all campaigns in a table",
        "query": {
            "metrics": ["spend", "revenue", "roas"],
            "time_range": {"last_n_days": 7},
            "breakdown": {
                "dimension": "entity",
                "level": "campaign",
                "limit": 50,
                "sort_order": "desc"
            },
            "output_format": "table"
        }
    },
    {
        "question": "Just tell me the total spend",
        "query": {
            "metrics": ["spend"],
            "time_range": {"last_n_days": 7},
            "output_format": "text"
        }
    },

    # Full composition example (breakdown + comparison + timeseries)
    {
        "question": "Show me daily CPC for top 3 campaigns this week vs last week",
        "query": {
            "metrics": ["cpc"],
            "time_range": {"last_n_days": 7},
            "breakdown": {
                "dimension": "entity",
                "level": "campaign",
                "limit": 3,
                "sort_order": "desc"
            },
            "comparison": {
                "type": "previous_period",
                "include_timeseries": True
            },
            "include_timeseries": True,
            "output_format": "chart"
        }
    },
]


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_semantic_system_prompt() -> str:
    """
    Build the system prompt for SemanticQuery translation.

    WHAT: Creates the instruction prompt for the LLM.

    WHY: Clear, focused prompt produces better translations than
    the overly complex legacy prompt.

    RETURNS:
        Complete system prompt string
    """
    return """You are a marketing analytics query translator.

TASK: Convert user questions into a structured JSON query format.

SCHEMA:
```json
{
    "metrics": ["metric1", "metric2"],  // Required: one or more
    "time_range": {"last_n_days": 7},   // Required: relative or absolute dates
    "breakdown": {                       // Optional: how to group data
        "dimension": "entity" | "provider" | "time",
        "level": "campaign" | "adset" | "ad",  // For entity dimension
        "granularity": "day" | "week" | "month",  // For time dimension
        "limit": 5,  // 1-50, default 5
        "sort_order": "desc" | "asc"  // Default desc
    },
    "comparison": {                      // Optional: compare to previous period
        "type": "previous_period" | "year_over_year"
    },
    "include_timeseries": false,         // Optional: daily trend data
    "filters": [],                        // Optional: filter conditions
    "output_format": "auto"              // auto | chart | table | text
}
```

METRICS:
- Base: spend, revenue, profit, clicks, impressions, conversions, leads, installs, purchases, visitors
- Cost: cpc (cost per click), cpm (per 1000 impressions), cpa (per acquisition), cpl (per lead), cpi (per install), cpp (per purchase)
- Value: roas (return on ad spend), poas (profit on ad spend), aov (average order value)
- Engagement: ctr (click-through rate), cvr (conversion rate)

TIME RANGE:
- Relative: {"last_n_days": N} - "today"=1, "this week"=7, "this month"=30
- Absolute: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}

BREAKDOWN RULES:
- "entity" dimension needs "level" (campaign/adset/ad)
- "time" dimension needs "granularity" (day/week/month)
- "provider" dimension groups by platform (google/meta/tiktok)
- "all" or "every" → limit: 50
- "top N" or "best N" → limit: N
- "which one" or "best" → limit: 1

COMPOSITION (KEY FEATURE):
These components COMPOSE freely:
- breakdown + comparison = per-entity comparison (e.g., "compare top 3 ads vs last week")
- breakdown + timeseries = multi-line chart (e.g., "graph daily spend by campaign")
- All three together = full flexibility

COMPARISON TRIGGERS:
- "vs", "compared to", "change", "vs last week" → add comparison
- "how did X perform vs" → add comparison

TIMESERIES TRIGGERS:
- "trend", "over time", "daily", "graph", "chart" → include_timeseries: true

OUTPUT FORMAT:
- "table", "as a table" → output_format: "table"
- "chart", "graph", "visualize" → output_format: "chart"
- "just tell me", "text only" → output_format: "text"
- Default: "auto" (system chooses)

CRITICAL RULES:
1. Output ONLY valid JSON, nothing else
2. Always include "metrics" and "time_range"
3. Use "breakdown" for grouping (not the old "group_by")
4. breakdown + comparison is NOW POSSIBLE (the key feature!)
5. Default time range: last 7 days
6. Default metric for vague "performance" questions: roas"""


def build_semantic_few_shot_prompt() -> str:
    """
    Build few-shot examples section.

    RETURNS:
        Formatted examples string
    """
    examples_text = "\n\nEXAMPLES:\n"

    for i, example in enumerate(SEMANTIC_EXAMPLES, 1):
        examples_text += f"\n{i}. Q: \"{example['question']}\"\n"
        examples_text += f"   A: {json.dumps(example['query'], separators=(',', ':'))}\n"

    return examples_text


def build_semantic_full_prompt(question: str, context: str = None) -> str:
    """
    Build complete prompt for a question.

    PARAMETERS:
        question: User's natural language question
        context: Optional conversation context

    RETURNS:
        Complete prompt ready for LLM
    """
    system = build_semantic_system_prompt()
    examples = build_semantic_few_shot_prompt()

    prompt = f"{system}\n{examples}\n\n"

    if context:
        prompt += f"CONVERSATION CONTEXT:\n{context}\n\n"

    prompt += f'Question: "{question}"\n\nJSON:'

    return prompt


# =============================================================================
# ANSWER GENERATION PROMPTS (SIMPLE)
# =============================================================================

SEMANTIC_ANSWER_PROMPT = """You are a marketing analytics assistant explaining query results.

CONTEXT PROVIDED:
- Metric values with formatting
- Comparison data (if available)
- Breakdown data (if available)
- Workspace averages (if available)

YOUR TASK:
Generate a natural, concise answer (2-3 sentences max).

RULES:
1. Lead with the main finding
2. Include timeframe context
3. Add comparison if available
4. Highlight notable outliers
5. Be conversational, not robotic
6. Never invent data not provided

EXAMPLES:

Simple:
"Your ROAS was 3.8× last week."

Comparison:
"Your ROAS improved to 3.8× last week, up 15% from the week before."

Breakdown:
"Your top campaign by ROAS was Summer Sale at 5.2×, followed by Holiday Promo at 4.1×."

Entity Comparison (THE KEY FEATURE):
"Your top 3 ads by CPC: Video Ad dropped to $0.45 (-12%), Carousel held at $0.52 (+2%), and Image Ad rose to $0.68 (+8%)."

Multi-line Chart:
"Here's your daily spend for the top 3 campaigns. Summer Sale (blue) shows steady growth, while Holiday Promo (orange) peaked mid-week."

Remember: Be helpful and clear. Sound like a knowledgeable colleague, not a robot."""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_semantic_json_schema() -> Dict[str, Any]:
    """
    Get JSON schema for SemanticQuery.

    RETURNS:
        JSON Schema dict for structured outputs
    """
    return SEMANTIC_QUERY_SCHEMA


def get_semantic_examples() -> List[Dict[str, Any]]:
    """
    Get list of few-shot examples.

    RETURNS:
        List of question/query pairs
    """
    return SEMANTIC_EXAMPLES


def validate_example_queries():
    """
    Validate that all example queries are valid SemanticQuery format.

    This is for development/testing only.

    RAISES:
        ValueError if any example is invalid
    """
    from app.semantic.query import SemanticQuery

    for i, example in enumerate(SEMANTIC_EXAMPLES):
        try:
            SemanticQuery.from_dict(example["query"])
        except Exception as e:
            raise ValueError(
                f"Example {i+1} invalid: {example['question']}\n"
                f"Query: {example['query']}\n"
                f"Error: {e}"
            )

    return True
