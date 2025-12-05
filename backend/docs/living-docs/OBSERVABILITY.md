# Metricx Observability Stack

Production-grade observability for the Metricx platform.

## Overview

| Service | Purpose | Dashboard |
|---------|---------|-----------|
| **Sentry** | Error tracking & performance | https://sentry.io |
| **RudderStack** | User analytics → GA4 | https://app.rudderstack.com |
| **Langfuse** | LLM observability | https://cloud.langfuse.com |

## Quick Start

### 1. Environment Variables

Add to `.env`:

```bash
# Sentry - Error Tracking
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# RudderStack - User Analytics
RUDDERSTACK_WRITE_KEY=xxx
RUDDERSTACK_DATA_PLANE_URL=https://xxx.dataplane.rudderstack.com

# Langfuse - LLM Observability
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com

# Environment
ENVIRONMENT=production
LOG_LEVEL=WARNING
```

### 2. Install Dependencies

```bash
pip install sentry-sdk[fastapi] rudder-sdk-python langfuse
```

### 3. Verify

Restart the server. You should see:
```
WARNING:app.main:[STARTUP] Observability: sentry, analytics, langfuse
```

---

## Service Setup

### Sentry (Error Tracking)

1. Create account at [sentry.io](https://sentry.io)
2. Create project → Select "FastAPI"
3. Copy DSN to `SENTRY_DSN`

**What gets tracked:**
- All unhandled exceptions
- User context (ID, email, workspace)
- Request context (URL, method, headers)
- Performance traces (10% sampled)

### RudderStack (User Analytics → GA4)

1. Create account at [rudderstack.com](https://rudderstack.com)
2. Create Source → Select "Python"
3. Copy Write Key and Data Plane URL
4. Add Destination → "Google Analytics 4"
5. Connect your GA4 property

**Events tracked:**

| Event | Trigger | Properties |
|-------|---------|------------|
| `user_signed_up` | New registration | email, workspace_id |
| `user_logged_in` | Login | email, workspace_id |
| `connected_google_ads` | Google OAuth complete | account_id, account_name |
| `connected_meta_ads` | Meta OAuth complete | account_id, account_name |
| `connected_shopify` | Shopify OAuth complete | shop_domain |
| `copilot_query_sent` | AI copilot question | question_length, workspace_id |

### Langfuse (LLM Observability)

1. Create account at [langfuse.com](https://langfuse.com)
2. Create Project
3. Copy Public Key, Secret Key, Host

**What gets tracked:**
- Every LLM call (model, input, output)
- Token usage (input/output/total)
- Latency (time to response)
- User ID for attribution
- Success/failure status

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Sentry     │  │  RudderStack │  │   Langfuse   │       │
│  │              │  │              │  │              │       │
│  │  • Errors    │  │  • Signups   │  │  • LLM calls │       │
│  │  • Perf      │  │  • Logins    │  │  • Tokens    │       │
│  │  • Context   │  │  • OAuth     │  │  • Latency   │       │
│  │              │  │  • Copilot   │  │  • Traces    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
└─────────┼─────────────────┼─────────────────┼────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐
    │ Sentry   │      │   GA4    │      │ Langfuse │
    │ Dashboard│      │ Reports  │      │ Traces   │
    └──────────┘      └──────────┘      └──────────┘
```

---

## Logging Levels

Control console verbosity with `LOG_LEVEL`:

| Level | Use Case | Console Output |
|-------|----------|----------------|
| `WARNING` | Production | Only warnings and errors |
| `INFO` | Staging | + Key events |
| `DEBUG` | Development | + All details |

```bash
# Production (quiet console, details to observability)
LOG_LEVEL=WARNING

# Development (verbose console)
LOG_LEVEL=DEBUG
```

---

## Code Integration

### Tracking User Events

```python
from app.telemetry import track, identify

# Identify user (on login/signup)
identify(
    user_id=str(user.id),
    email=user.email,
    traits={"workspace_id": str(workspace.id)}
)

# Track custom event
track(
    user_id=str(user.id),
    event="feature_used",
    properties={"feature": "export", "format": "csv"}
)
```

### Tracking LLM Calls

```python
from app.telemetry import create_copilot_trace, log_generation, complete_copilot_trace

# Start trace
trace = create_copilot_trace(
    user_id=str(user.id),
    workspace_id=str(workspace_id),
    question=question,
)

# Log LLM generation
log_generation(
    trace=trace,
    name="understand",
    model="claude-sonnet-4-20250514",
    input_messages=messages,
    output=response,
    usage={"input": 100, "output": 50, "total": 150},
)

# Complete trace
complete_copilot_trace(
    trace=trace,
    success=True,
    answer=answer,
    latency_ms=1500,
    total_tokens=150,
)
```

### Error Context

```python
from app.telemetry import set_user_context, capture_exception

# Set user context (errors will include user info)
set_user_context(
    user_id=str(user.id),
    email=user.email,
    workspace_id=str(workspace_id),
)

# Manually capture exception
try:
    risky_operation()
except Exception as e:
    capture_exception(e, extra={"operation": "risky"})
```

---

## Monitoring Checklist

### Daily
- [ ] Check Sentry for new errors
- [ ] Review Langfuse for failed LLM calls

### Weekly
- [ ] GA4: User signup/login trends
- [ ] GA4: OAuth connection rates
- [ ] Langfuse: Token usage and costs

### On Deploy
- [ ] Verify all 3 services initialize
- [ ] Test a copilot query, check Langfuse
- [ ] Trigger a test error, check Sentry

---

## Troubleshooting

### Services Not Initializing

Check startup log:
```
WARNING:app.main:[STARTUP] Observability: sentry, analytics, langfuse
```

If a service is missing:
1. Verify environment variables are set
2. Verify packages are installed: `pip show sentry-sdk langfuse rudder-sdk-python`
3. Check for import errors: `python -c "from app.telemetry import init_observability; print(init_observability())"`

### Events Not Appearing

**RudderStack/GA4:**
- Events are batched, may take 1-2 minutes
- Check GA4 Realtime report for immediate visibility
- Verify RudderStack source is connected to GA4 destination

**Langfuse:**
- Traces appear within seconds
- Check filters (time range, user ID)
- Verify `LANGFUSE_HOST` is correct

**Sentry:**
- Errors appear immediately
- Check project filters
- Verify `SENTRY_DSN` is correct

---

## Files Reference

| File | Purpose |
|------|---------|
| `app/telemetry/__init__.py` | Main exports and `init_observability()` |
| `app/telemetry/sentry.py` | Sentry integration |
| `app/telemetry/analytics.py` | RudderStack integration |
| `app/telemetry/llm_trace.py` | Langfuse integration |
| `app/main.py` | Initializes on startup |
| `app/routers/auth.py` | Tracks signup/login |
| `app/routers/qa.py` | Tracks copilot queries |
