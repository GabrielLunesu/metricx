# QA System Architecture

This document describes the QA (Question Answering) system evaluation architecture, including the DeepEval + Confident AI integration for tracking LLM performance metrics.

## Overview

The QA evaluation system provides:
- Golden test cases for regression testing
- LLM answer quality metrics (faithfulness, relevancy)
- Visual intent classification testing
- Integration with Confident AI for tracking and monitoring

## Directory Structure

```
app/tests/qa_evaluation/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── deepeval_config.py       # DeepEval + Confident AI configuration
├── run_evaluation.py        # CLI evaluation runner
├── setup_confident.py       # Interactive setup script
└── test_qa_golden.py        # Golden test cases and DeepEval tests
```

## Setup

### Prerequisites

1. **Install DeepEval**:
   ```bash
   pip install deepeval
   ```

2. **Set environment variables**:
   ```bash
   export CONFIDENT_API_KEY=your_confident_ai_key
   export OPENAI_API_KEY=your_openai_key  # Required for LLM metrics
   ```

### Quick Setup

Run the interactive setup script:
```bash
python -m app.tests.qa_evaluation.setup_confident
```

## Running Tests

### Run All Golden Tests (pytest)

```bash
pytest app/tests/qa_evaluation/test_qa_golden.py -v
```

### Run DeepEval Tests with Confident AI Tracking

**Important**: Use the `deepeval test run` command with `CONFIDENT_METRIC_LOGGING_FLUSH=1` to ensure metrics are sent to Confident AI:

```bash
CONFIDENT_METRIC_LOGGING_FLUSH=1 deepeval test run app/tests/qa_evaluation/test_qa_golden.py::TestAnswerQuality -v
```

### Run Evaluation Suite

```bash
# Dry run (validates test case expectations)
python -m app.tests.qa_evaluation.run_evaluation

# With Confident AI tracking
python -m app.tests.qa_evaluation.run_evaluation --confident

# Live evaluation against QA service
python -m app.tests.qa_evaluation.run_evaluation --live --confident
```

## Test Categories

### 1. DSL Generation Tests (`TestDSLGeneration`)

Validates that the DSL translator generates correct query structures:
- Metric extraction
- Breakdown handling
- Time range parsing
- Compare-to-previous flags

### 2. Visual Intent Tests (`TestVisualIntent`)

Tests visual intent classification:
- `SINGLE_METRIC` - Simple metric queries
- `COMPARISON` - Time-based comparisons (vs last week)
- `RANKING` - Top N / breakdown queries
- `BREAKDOWN` - Entity breakdowns (by campaign, provider)

### 3. Visual Builder Tests (`TestVisualBuilder`)

Tests visual payload generation:
- Comparison charts have 2 series (current + previous)
- Ranking queries include tables
- Correct chart types

### 4. Answer Quality Tests (`TestAnswerQuality`)

DeepEval-powered LLM metrics:
- **Faithfulness**: Does the answer stick to provided data?
- **Answer Relevancy**: Is the answer relevant to the question?

### 5. Known Bug Regression Tests (`TestKnownBugs`)

Prevents regression of fixed bugs:
- "Compare all campaigns" empty chart fix
- Comparison chart single-line fix

## Golden Test Cases

The system includes 20+ golden test cases covering:

| Category | Example Query |
|----------|--------------|
| Simple Metrics | "What's my ROAS this week?" |
| Time Comparisons | "Spend vs last week" |
| All/Compare Queries | "Compare all campaigns" |
| Top N Queries | "Top 5 campaigns by revenue" |
| Filtering | "Campaigns with ROAS above 4" |
| Provider Breakdown | "Compare Google vs Meta performance" |

## Confident AI Dashboard

After running tests with `deepeval test run`, view results at:
- https://app.confident-ai.com

The dashboard shows:
- Test run history
- Metric scores over time
- Failed test analysis
- Model cost tracking

## Adding New Test Cases

### 1. Add to Golden Test Cases

Edit `test_qa_golden.py`:

```python
GOLDEN_TEST_CASES.append(
    GoldenTestCase(
        question="Your new test question",
        expected_metric="roas",
        expected_query_type="metrics",
        expected_breakdown="campaign",
        tags=["your-tag"],
    )
)
```

### 2. Add DeepEval Test

```python
@pytest.mark.skipif(
    not DEEPEVAL_AVAILABLE or not OPENAI_API_KEY,
    reason="Requires DeepEval and OPENAI_API_KEY"
)
def test_your_new_metric(self):
    test_case = LLMTestCase(
        input="Your question",
        actual_output="Expected answer",
        retrieval_context=["Context data"],
    )

    metric = AnswerRelevancyMetric(threshold=0.7)
    assert_test(test_case, [metric])
```

## Configuration

### DeepEval Metrics Configuration

In `deepeval_config.py`:

```python
DEFAULT_THRESHOLDS = QAMetricThresholds(
    faithfulness=0.8,
    answer_relevancy=0.8,
    contextual_relevancy=0.7,
    dsl_accuracy=0.9,
    visual_accuracy=0.9,
)
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `CONFIDENT_API_KEY` | Confident AI API key |
| `OPENAI_API_KEY` | OpenAI API key for metrics |
| `CONFIDENT_METRIC_LOGGING_FLUSH` | Set to `1` to flush metrics before exit |
| `CONFIDENT_METRIC_LOGGING_VERBOSE` | Set to `0` to disable logging |

## Troubleshooting

### "No test cases found" in Confident AI

Use `assert_test()` instead of manual assertions:
```python
# Wrong
metric.measure(test_case)
assert metric.is_successful()

# Correct
assert_test(test_case, [metric])
```

### Metrics not appearing in dashboard

Ensure you set the flush flag:
```bash
CONFIDENT_METRIC_LOGGING_FLUSH=1 deepeval test run ...
```

### DeepEval import errors

Install with:
```bash
pip install deepeval
```

## Self-Learning / Feedback System

The QA system includes a feedback mechanism for continuous improvement.

### Feedback API

**Submit Feedback:**
```bash
POST /qa/feedback
{
    "query_log_id": "uuid-of-query",
    "rating": 5,           # 1-5 scale
    "feedback_type": "accuracy",  # accuracy, relevance, visualization, completeness, other
    "comment": "Great answer!",   # optional
    "corrected_answer": null      # optional - what it should have said
}
```

**Get Feedback Stats:**
```bash
GET /qa/feedback/stats?workspace_id=...
```

Returns:
```json
{
    "total_feedback": 100,
    "average_rating": 4.2,
    "rating_distribution": {"1": 5, "2": 10, "3": 15, "4": 30, "5": 40},
    "feedback_by_type": {"accuracy": 20, "relevance": 30},
    "few_shot_examples_count": 25
}
```

**Get Few-Shot Examples:**
```bash
GET /qa/examples?workspace_id=...&limit=10
```

Returns highly-rated Q&A pairs for use as training examples.

### Database Schema

```sql
-- qa_feedback table
CREATE TABLE qa_feedback (
    id UUID PRIMARY KEY,
    query_log_id UUID REFERENCES qa_query_logs(id),
    user_id UUID REFERENCES users(id),
    rating INTEGER NOT NULL,  -- 1-5
    feedback_type feedbacktypeenum,
    comment TEXT,
    corrected_answer TEXT,
    is_few_shot_example BOOLEAN DEFAULT FALSE,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP
);
```

### Self-Learning Flow

1. User submits feedback via thumbs up/down or rating
2. Highly-rated answers (5 stars) auto-marked as few-shot examples
3. Low-rated answers flagged for review
4. `/qa/examples` endpoint returns quality examples for prompt improvement
5. Feedback stats tracked for monitoring QA performance

## Visual Output Improvements (v2.3)

### Output Format DSL Field

The DSL supports an `output_format` field that controls visual output:

| Value | Behavior |
|-------|----------|
| `auto` | System determines best visualization (default) |
| `table` | Force table-only output |
| `chart` | Force chart-only output (no cards/tables) |
| `text` | Plain text answer only |

**Important**: When user says "graph" or "make a graph", the translator sets `output_format: "chart"` which triggers multi-line LINE chart generation for entity breakdowns.

### Multi-Line Entity Charts

When a user requests a "graph" of top N entities (ads, campaigns, adsets), the system generates a **multi-line LINE chart** showing each entity's performance over time.

**Example Query**: "make a graph of the top 5 ads last week"

**DSL Generated**:
```json
{
    "query_type": "metrics",
    "metric": "spend",
    "breakdown": "ad",
    "top_n": 5,
    "output_format": "chart"
}
```

**Visual Output**: A line chart with 5 colored lines (one per ad) showing daily values with a legend.

### Entity Timeseries Data Flow

```
User Query: "graph of top 5 ads"
         ↓
DSL Translator → output_format: "chart", breakdown: "ad", top_n: 5
         ↓
Executor (_execute_metrics_plan)
    1. Fetch top 5 ads breakdown (with entity_id)
    2. If output_format='chart' + entity breakdown:
       → Call get_entity_timeseries() for each entity_id
         ↓
MetricResult.entity_timeseries = [
    {entity_id, entity_name, timeseries: [{date, value}, ...]},
    ...
]
         ↓
Visual Builder (_build_entity_timeseries_spec)
    → Creates multi-line chart spec with series per entity
         ↓
Frontend renders LINE chart with legend
```

### Key Components

**UnifiedMetricService** (`app/services/unified_metric_service.py`):
- `MetricBreakdownItem.entity_id` - Entity ID for timeseries lookup
- `get_entity_timeseries()` - Fetches daily data per entity

**DSL Executor** (`app/dsl/executor.py`):
- Detects chart output + entity breakdown combination
- Fetches entity timeseries when conditions met
- Adds `entity_timeseries` to MetricResult

**Visual Builder** (`app/answer/visual_builder.py`):
- `_build_entity_timeseries_spec()` - Builds multi-line chart spec
- `_apply_output_format_override()` - Enforces output_format restrictions

### Visual Intent Classification

The system classifies queries into visual intents:

| Intent | Description | Example |
|--------|-------------|---------|
| `SINGLE_METRIC` | Single value display | "What's my ROAS?" |
| `COMPARISON` | Time-based comparison | "Spend vs last week" |
| `RANKING` | Top N entities | "Top 5 campaigns" |
| `BREAKDOWN` | Entity breakdown | "Breakdown by campaign" |
| `ENTITY_GRAPH` | Multi-entity timeseries | "Graph of top 5 ads" |

### Improvements Made

1. **Graph = Multi-Line Chart**: User saying "graph" now generates LINE charts with multiple series, not bar charts
2. **Output Format Enforcement**: `output_format: "chart"` now properly suppresses cards and tables
3. **Entity Timeseries**: New data flow fetches per-entity daily data for time-based visualization
4. **Breakdown-Focused Answers**: Chart/table queries focus on breakdown data, not workspace totals
5. **Metric Inference Clarification** (v2.4): When user asks "top 5 ads" without specifying a metric, the system:
   - Defaults to "spend" as the sorting metric
   - Sets `metric_inferred: true` in the DSL
   - Clarifies in the answer what metric was used (e.g., "sorted by spend since no specific metric was requested")

### Metric Inference Tracking (v2.4)

The DSL now includes a `metric_inferred` boolean field to track when the metric was auto-selected:

```json
{
    "metric": "spend",
    "breakdown": "ad",
    "top_n": 5,
    "metric_inferred": true  // User said "top 5 ads" without specifying metric
}
```

**When `metric_inferred: true`**:
- The answer builder includes clarification text
- Example: "Here are your top 5 ads by spend last week (sorted by this metric since no specific metric was requested)"

**When `metric_inferred: false` (or omitted)**:
- User explicitly specified the metric (e.g., "top 5 ads by revenue")
- No clarification needed in the answer

### Future Improvements

- [ ] Chart expand/fullscreen toggle for mobile
- [ ] Interactive legend to show/hide individual entity lines
- [x] ~~Metric selection in graph queries (currently defaults to spend)~~ - Now clarifies when metric is auto-selected

## Creative Support (v2.5)

### Overview

The QA system now supports **creative queries** - questions about ad creatives with thumbnail images and performance metrics. This feature displays actual creative images alongside performance data.

**Important Limitation**: Creative images are **only available for Meta (Facebook/Instagram) ads**. Google Ads and TikTok do not provide creative image URLs via their APIs. The system acknowledges this limitation in answers.

### Example Query

**User**: "Show my best creatives"

**DSL Generated**:
```json
{
    "metric": "roas",
    "breakdown": "ad",
    "top_n": 5,
    "sort_order": "desc"
}
```

**Answer**: "Here are your top 5 creatives by ROAS over the last 7 days. 3 have preview images available (Meta ads only)."

### Creative Data Flow

```
User Query: "Show best creatives"
         ↓
DSL Translator
    - breakdown: "ad" (creatives = ads)
    - top_n: 5 (default for creative queries, not 1)
    - metric: "roas" or "spend" (default)
         ↓
Executor → UnifiedMetricService.get_breakdown()
    - Returns MetricBreakdownItem with creative fields:
      - thumbnail_url (small preview)
      - image_url (full size)
      - media_type (image/video/carousel/unknown)
         ↓
Visual Builder (_build_creative_cards)
    - Creates creative_cards array
    - Each card has: name, thumbnail, metrics, has_image flag
         ↓
Answer Builder (_build_creative_intro)
    - Detects creative query
    - Generates answer with Meta-only acknowledgment
         ↓
Response includes:
{
    "answer": "Here are your top 5 creatives...",
    "visuals": {
        "creative_cards": [...],
        "tables": [...],
        "cards": [],
        "viz_specs": []
    }
}
```

### Database Schema

**Entity model** (`app/models.py`):
```python
class MediaTypeEnum(str, enum.Enum):
    image = "image"
    video = "video"
    carousel = "carousel"
    unknown = "unknown"

class Entity(Base):
    # ... existing fields ...
    thumbnail_url = Column(String, nullable=True)  # Small preview
    image_url = Column(String, nullable=True)      # Full-size image
    media_type = Column(Enum(MediaTypeEnum), nullable=True)
```

**Migration**: `alembic/versions/20251126_000001_add_entity_creative_fields.py`

### Creative Card Structure

Each creative card in the `creative_cards` array:

```json
{
    "id": "creative-0",
    "type": "creative",
    "name": "Summer Sale Ad",
    "entity_id": 12345,
    "thumbnail_url": "https://...",
    "image_url": "https://...",
    "media_type": "image",
    "has_image": true,
    "metric": "roas",
    "metric_value": 4.2,
    "formatted_value": "4.20×",
    "spend": 150.0,
    "formatted_spend": "$150.00",
    "clicks": 500,
    "conversions": 25,
    "impressions": 10000,
    "revenue": 630.0,
    "timeframe": "last 7 days"
}
```

### Key Components

**Meta Sync Service** (`app/services/meta_sync_service.py`):
- Fetches creative details from Meta Graph API during ad sync
- Extracts thumbnail_url, image_url, media_type
- Stores in Entity model

**Meta Ads Client** (`app/services/meta_ads_client.py`):
- `get_creative_details(creative_id)` - Fetches AdCreative from Meta
- `_determine_media_type()` - Detects image/video/carousel

**Unified Metric Service** (`app/services/unified_metric_service.py`):
- `MetricBreakdownItem` includes creative fields
- `_build_entity_breakdown_query()` selects creative columns

**Visual Builder** (`app/answer/visual_builder.py`):
- `_build_creative_cards()` - Creates card payloads
- `_has_creative_data()` - Checks if breakdown has images

**Answer Builder** (`app/answer/answer_builder.py`):
- `_is_creative_query()` - Detects creative queries
- `_build_creative_intro()` - Generates Meta-aware answer text

**Prompts** (`app/nlp/prompts.py`):
- `CREATIVE_QUERIES_SECTION` - Rules for creative translation
- Few-shot examples for "show creatives" queries

### DSL Translation Rules

1. **"creatives" = ads**: Queries about "creatives" translate to `breakdown: "ad"`
2. **Default top_n: 5**: Creative queries default to showing 5 results, not 1
3. **Default metric: roas**: If no metric specified, sort by ROAS (or spend)
4. **Meta acknowledgment**: LLM knows to mention Meta-only image availability

### Answer Text Examples

**With images (Meta ads present)**:
> "Here are your top 5 creatives by ROAS over the last 7 days. 3 have preview images available (Meta ads only)."

**Without images (no Meta ads)**:
> "Here are your top 5 ads by ROAS over the last 7 days. Note: Creative preview images are currently only available for Meta (Facebook/Instagram) ads."

### Syncing Creative Images

To populate creative images, run a Meta ads sync:

```python
from app.services.meta_sync_service import MetaSyncService
from app.database import SessionLocal

db = SessionLocal()
service = MetaSyncService(db)
await service.sync_ads(workspace_id=1, account_id="act_123")
```

The sync fetches `AdCreative` objects and extracts:
- `thumbnail_url` from creative data
- `image_url` from `object_story_spec.link_data.image_hash` or similar
- `media_type` from creative structure (video_data, carousel, etc.)

### Future Improvements

- [ ] Support Google Ads creative previews (if API allows)
- [ ] Video thumbnail extraction for video creatives
- [ ] Creative A/B comparison visualization
- [ ] Carousel creative multi-image display

## Related Files

- `app/answer/visual_intent.py` - Visual intent classification
- `app/answer/visual_builder.py` - Visual payload generation + creative cards (v2.5)
- `app/answer/answer_builder.py` - Answer generation + creative query handling (v2.5)
- `app/services/unified_metric_service.py` - Entity timeseries and breakdown data + creative fields (v2.5)
- `app/services/meta_sync_service.py` - Meta ads sync + creative image fetching (v2.5)
- `app/services/meta_ads_client.py` - Meta Graph API client + AdCreative fetching (v2.5)
- `app/dsl/executor.py` - DSL execution with entity timeseries fetching
- `app/dsl/schema.py` - MetricResult schema with entity_timeseries field
- `app/nlp/prompts.py` - Graph/chart examples, output format rules, creative queries (v2.5)
- `app/services/dsl_translator.py` - DSL translation
- `app/services/qa_service.py` - Main QA service
- `app/routers/qa.py` - API endpoints including feedback
- `app/models.py` - Entity model with creative fields, MediaTypeEnum (v2.5)
