# Live API Copilot

**Last Updated**: 2025-12-22
**Version**: 1.0.0
**Status**: Production

---

## Overview

The AI Copilot can now fetch **live data directly from Google Ads and Meta Ads APIs** when answering questions. This ensures users always get current, accurate metrics without needing to ask for "live" or "real-time" data explicitly.

### Key Features

| Feature | Description |
|---------|-------------|
| **Smart Auto-Detection** | Automatically uses live API for "today" questions |
| **Graceful Fallback** | Falls back to cached snapshots if live API fails |
| **Rate Limiting** | Per-workspace limits prevent API abuse |
| **Read-Only** | Only fetches data - never modifies campaigns |
| **Langfuse Tracking** | All live API calls logged for observability |

---

## How It Works

### Decision Logic

The copilot automatically decides when to use live API vs cached snapshots:

```
User Question → Understand Intent → Check Time Context → Choose Data Source
                                            ↓
                              ┌─────────────┴─────────────┐
                              ↓                           ↓
                        "today" / present tense    "this week" / trends
                              ↓                           ↓
                         LIVE API                    SNAPSHOTS
```

### When Live API is Used

| Trigger | Example | Result |
|---------|---------|--------|
| Present tense questions | "What's my ROAS?" | Live API (today) |
| Explicit "today" | "How much did I spend today?" | Live API (today) |
| Current state questions | "How are my campaigns doing?" | Live API (today) |
| Explicit live request | "Give me live metrics" | Live API (today) |

### When Snapshots are Used

| Trigger | Example | Result |
|---------|---------|--------|
| Trend analysis | "Show spend this week" | Snapshots (7d) |
| Comparisons | "Compare to last week" | Snapshots |
| Historical questions | "What was my ROAS yesterday?" | Snapshots |
| Multi-day breakdowns | "Daily spend breakdown" | Snapshots |

---

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `backend/app/agent/exceptions.py` | Custom exception types for live API errors |
| `backend/app/agent/rate_limiter.py` | Per-workspace Redis rate limiter |
| `backend/app/agent/connection_resolver.py` | Token decryption & client instantiation |
| `backend/app/agent/live_api_tools.py` | Core live API query tools |
| `backend/app/tests/test_live_api_tools.py` | Unit tests |

### Modified Files

| File | Changes |
|------|---------|
| `backend/app/agent/state.py` | Added live API tracking fields |
| `backend/app/agent/nodes.py` | Smart live data detection, check_freshness node |
| `backend/app/agent/graph.py` | Added check_freshness node to flow |
| `backend/app/telemetry/llm_trace.py` | Live API call logging |
| `backend/app/routers/qa.py` | Live API SSE events |

### Agent Flow

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
┌──────▼──────┐
│ understand  │ ← Detects needs_live_data based on question
└──────┬──────┘
       │
┌──────▼──────────┐
│ check_freshness │ ← Auto-enables live API if snapshots stale (>24h)
└──────┬──────────┘
       │
┌──────▼──────┐
│   fetch     │ ← Uses LiveApiTools OR SemanticTools
└──────┬──────┘
       │
┌──────▼──────┐
│   respond   │
└─────────────┘
```

---

## LiveApiTools Class

### Methods

```python
class LiveApiTools:
    def check_data_freshness(provider=None) -> Dict
    """Check if snapshot data is stale (>24h)."""

    def get_live_metrics(
        provider: "google"|"meta",
        entity_type: "account"|"campaign"|"adset"|"ad",
        entity_ids: Optional[List[str]],
        metrics: List[str],
        date_range: "today"|"yesterday"|"last_7d"|"last_30d"
    ) -> Dict
    """Fetch live metrics from Google/Meta APIs."""

    def get_live_entity_details(
        provider: "google"|"meta",
        entity_type: "campaign"|"adset"|"ad",
        entity_id: str,
        fields: List[str]
    ) -> Dict
    """Get entity details (budget, status, etc.)."""

    def list_live_entities(
        provider: "google"|"meta",
        entity_type: "campaign"|"adset"|"ad",
        status_filter: "active"|"paused"|"all"
    ) -> List[Dict]
    """List campaigns/adsets/ads from live API."""
```

### Calculated Metrics

The live API automatically calculates derived metrics:

| Metric | Formula |
|--------|---------|
| `roas` | revenue / spend |
| `cpc` | spend / clicks |
| `ctr` | (clicks / impressions) * 100 |

---

## Rate Limiting

### Per-Workspace Limits

| Provider | Limit | Window |
|----------|-------|--------|
| Google Ads | 15 calls/min | Sliding window |
| Meta Ads | 30 calls/min | Sliding window |

### Implementation

```python
# Redis key format
live_api_rate:{workspace_id}:{provider}

# Example
live_api_rate:abc-123:google
```

### Rate Limit Response

When rate limited, the copilot:
1. Returns a friendly message with retry time
2. Falls back to cached snapshot data
3. Logs the event to Langfuse

---

## Exception Types

| Exception | When Raised | User Message |
|-----------|-------------|--------------|
| `QuotaExhaustedError` | API quota exceeded | "Using cached data because the API is at its limit" |
| `TokenExpiredError` | OAuth token invalid | "Please reconnect in Settings" |
| `WorkspaceRateLimitError` | Per-workspace limit hit | "Please wait X seconds" |
| `ProviderNotConnectedError` | No connection exists | "Connect your account in Settings" |
| `LiveApiTimeoutError` | API call timed out | "API responding slowly, using cached data" |
| `LiveApiPermissionError` | Insufficient permissions | "Check your account permissions" |

---

## SSE Events

The `/qa/agent/sse` endpoint emits live API progress events:

### Event Types

```javascript
// Fetching live data
{"type": "live_api", "data": {"status": "fetching", "provider": "google"}}

// Success
{"type": "live_api", "data": {"status": "success", "provider": "google"}}

// Fallback to snapshots
{"type": "live_api", "data": {"status": "fallback", "reason": "api_error"}}
```

### User Notifications

```
🔴 **Fetching live data from Google Ads...**

✅ **Got live data from Google Ads for today**
```

### Final Response

```javascript
{
  "type": "done",
  "data": {
    "success": true,
    "answer": "...",
    "used_live_api": true,
    "live_data_reason": "user_requested",
    "live_api_calls": [
      {"provider": "google", "endpoint": "get_live_metrics", "success": true, "latency_ms": 245}
    ]
  }
}
```

---

## Langfuse Observability

### Spans Logged

| Span Name | Metadata |
|-----------|----------|
| `live_api_google_get_live_metrics` | provider, endpoint, latency_ms, success, error |
| `live_api_meta_get_live_metrics` | provider, endpoint, latency_ms, success, error |
| `data_source_fallback` | from_source, to_source, reason |

### Dashboard Queries

In Langfuse, you can filter by:
- `metadata.provider = "google"` - Google Ads calls only
- `metadata.success = false` - Failed calls
- `name LIKE "live_api_%"` - All live API calls

---

## Security Guardrails

| Guardrail | Implementation |
|-----------|----------------|
| **Read-Only** | LiveApiTools only exposes read methods |
| **Workspace Scoping** | All queries filtered by workspace_id |
| **Rate Limiting** | Per-workspace Redis limits |
| **Token Security** | Tokens decrypted only when needed, never logged |
| **Audit Trail** | All calls logged with workspace_id, user_id |

---

## Configuration

### Environment Variables

No new environment variables required. Uses existing:
- `GOOGLE_ADS_*` credentials
- `META_ADS_*` credentials
- `REDIS_URL` for rate limiting

### Feature Flags (Future)

```bash
# Optional: Disable live API globally
ENABLE_LIVE_API_COPILOT=true  # default
```

---

## Testing

### Manual Testing

```bash
# Test live data detection
curl -X POST 'http://localhost:8000/qa/agent/sse?workspace_id=YOUR_ID' \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is my ROAS?"}'

# Should see:
# 1. "Fetching live data from Google Ads..."
# 2. "Got live data from Google Ads for today"
# 3. Today's ROAS in the response
```

### Unit Tests

```bash
cd backend
python -m pytest app/tests/test_live_api_tools.py -v
```

---

## Troubleshooting

### Live API Not Triggering

1. Check if question triggers live data:
   - Present tense? → Should trigger
   - About "today"? → Should trigger
   - Trend/comparison? → Uses snapshots (correct)

2. Check Langfuse for `needs_live_data` in understand response

### Wrong Data Returned

1. Verify time range in Langfuse trace
2. Check `live_date_range` in logs
3. Compare with Google/Meta Ads dashboard for same date

### Rate Limited

1. Check `[RATE_LIMITER]` logs
2. Wait for window to reset (60 seconds)
3. Falls back to snapshots automatically

---

## Files Reference

| File | Purpose |
|------|---------|
| `app/agent/exceptions.py` | Custom exception types |
| `app/agent/rate_limiter.py` | Redis rate limiter |
| `app/agent/connection_resolver.py` | Credential management |
| `app/agent/live_api_tools.py` | Main API tools |
| `app/agent/state.py` | State with live API fields |
| `app/agent/nodes.py` | Smart detection logic |
| `app/agent/graph.py` | Agent flow |
| `app/telemetry/llm_trace.py` | Observability |
| `app/routers/qa.py` | SSE endpoint |
| `app/tests/test_live_api_tools.py` | Unit tests |
