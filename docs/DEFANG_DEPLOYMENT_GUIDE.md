# Defang Deployment Guide

**Quick Reference for metricx Production Deployment**

---

## Required Defang Configs

These are the **ONLY** configs you need to set in Defang. User tokens come from OAuth.

### Core Infrastructure (Required)

```bash
# Database & Cache
defang config set DATABASE_URL "postgresql://user:pass@host:port/dbname"
defang config set REDIS_URL "redis://default:pass@host:port"

# Security
defang config set JWT_SECRET "your-random-jwt-secret-min-32-chars"
defang config set TOKEN_ENCRYPTION_KEY "your-fernet-encryption-key"
defang config set ADMIN_SECRET_KEY "your-admin-panel-secret"

# AI
defang config set OPENAI_API_KEY "sk-..."
```

### Google Ads SDK Config (Required for SDK initialization)

```bash
# These are needed for the Google Ads SDK to work, NOT user tokens
defang config set GOOGLE_DEVELOPER_TOKEN "your-google-dev-token"
defang config set GOOGLE_CLIENT_ID "your-oauth-client-id.apps.googleusercontent.com"
defang config set GOOGLE_CLIENT_SECRET "your-oauth-client-secret"
```

**Why needed?**
- The Google Ads SDK requires these to initialize
- They're SDK config, not user credentials
- Every API call uses these + user's OAuth refresh token

### ❌ NOT Required (OAuth Provides These)

These are **OPTIONAL** and only used for `/from-env` fallback endpoints:

```bash
# Don't need these in production - OAuth provides them
# META_ACCESS_TOKEN (comes from Meta OAuth)
# META_AD_ACCOUNT_ID (comes from Meta OAuth)
# GOOGLE_REFRESH_TOKEN (comes from Google OAuth)
# GOOGLE_CUSTOMER_ID (comes from Google OAuth)
```

---

## How OAuth Works

### Google Ads Connection Flow

1. User clicks "Connect Google Ads" in Settings
2. OAuth redirects to Google consent screen
3. User grants permission
4. Callback receives authorization code
5. Backend exchanges code for **refresh token** ← This is the user's token
6. Backend fetches user's **customer ID** ← This is the account ID
7. Both stored encrypted in database:
   - `Token.refresh_token_enc` = encrypted refresh token
   - `Connection.external_account_id` = customer ID

8. When syncing:
   - Worker reads `Connection` → gets `external_account_id`
   - Worker decrypts `Token.refresh_token_enc`
   - Worker uses SDK config (CLIENT_ID/SECRET/DEV_TOKEN) + user's refresh token

### Meta Ads Connection Flow

1. User clicks "Connect Meta Ads" in Settings
2. OAuth redirects to Meta consent screen
3. User grants permission
4. Callback receives authorization code
5. Backend exchanges code for **access token** ← This is the user's token
6. Backend fetches user's **ad account IDs** ← These are account IDs
7. Both stored encrypted in database:
   - `Token.access_token_enc` = encrypted access token
   - `Connection.external_account_id` = ad account ID

8. When syncing:
   - Worker reads `Connection` → gets `external_account_id`
   - Worker decrypts `Token.access_token_enc`
   - Worker calls Meta API with user's access token

---

## Deployment Commands

### 1. Set Required Configs (One Time)

```bash
# Core (all required)
defang config set DATABASE_URL "your-railway-postgres-url"
defang config set REDIS_URL "your-railway-redis-url"
defang config set JWT_SECRET "$(openssl rand -base64 32)"
defang config set TOKEN_ENCRYPTION_KEY "$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
defang config set ADMIN_SECRET_KEY "$(openssl rand -base64 32)"
defang config set OPENAI_API_KEY "sk-your-openai-key"

# Google SDK (required for SDK)
defang config set GOOGLE_DEVELOPER_TOKEN "your-google-dev-token"
defang config set GOOGLE_CLIENT_ID "your-client-id.apps.googleusercontent.com"
defang config set GOOGLE_CLIENT_SECRET "your-client-secret"
```

### 2. Deploy

```bash
defang compose up
```

### 3. Verify

```bash
# Check all 4 services running
defang ps

# Should see:
# - backend (FastAPI)
# - worker (RQ worker)
# - scheduler (Sync scheduler)
# - frontend (Next.js)
```

---

## Why The Confusion?

### Development vs Production

**Development** (local testing):
- Use `/connections/google/from-env` endpoint
- Manually set `GOOGLE_CUSTOMER_ID` and `GOOGLE_REFRESH_TOKEN` in .env
- Quick way to test without OAuth flow

**Production** (real users):
- Users click "Connect Google Ads" button
- OAuth flow handles everything
- Account IDs and tokens come from OAuth
- No env vars needed

### The `/from-env` Endpoints

These are **development shortcuts** only:

```python
# backend/app/routers/connections.py

@router.post("/google/from-env")  # ← Development only
def ensure_google_connection_from_env(...):
    customer_id = os.getenv("GOOGLE_CUSTOMER_ID")  # ← Only used here
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")  # ← Only used here
    # Creates connection from env vars

@router.post("/meta/from-env")  # ← Development only
def ensure_meta_connection_from_env(...):
    ad_account_id = os.getenv("META_AD_ACCOUNT_ID")  # ← Only used here
    access_token = os.getenv("META_ACCESS_TOKEN")  # ← Only used here
    # Creates connection from env vars
```

In production, users use OAuth instead → no need for these env vars.

---

## Updated compose.yaml

The fix I just applied makes these optional with `:-` syntax:

```yaml
# Optional: Only used for /from-env fallback endpoints (OAuth provides these)
META_ACCESS_TOKEN: ${META_ACCESS_TOKEN:-}
META_AD_ACCOUNT_ID: ${META_AD_ACCOUNT_ID:-}
GOOGLE_REFRESH_TOKEN: ${GOOGLE_REFRESH_TOKEN:-}
GOOGLE_CUSTOMER_ID: ${GOOGLE_CUSTOMER_ID:-}
```

This means:
- ✅ If env var exists → use it
- ✅ If env var missing → use empty string (no error)
- ✅ OAuth connections work fine (they don't use env vars anyway)

---

## Try Deployment Now

```bash
defang compose up
```

This should work now! Defang will only complain about truly required configs:
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `TOKEN_ENCRYPTION_KEY`
- `ADMIN_SECRET_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_DEVELOPER_TOKEN`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

---

## Summary

**What changed**: Made 4 env vars optional in compose.yaml
- ❌ Before: Defang required them (error if missing)
- ✅ After: Defang allows empty values (OAuth provides data)

**Why**: These env vars are **fallback values for testing only**. Real production uses:
- Meta OAuth → stores encrypted access tokens in `tokens` table
- Google OAuth → stores encrypted refresh tokens in `tokens` table
- Account IDs stored in `connections.external_account_id`

**Result**: You can now deploy without setting these 4 configs!

