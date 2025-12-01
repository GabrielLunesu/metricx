# Local Development Guide

This guide explains how to run the Metricx project locally for development.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (for PostgreSQL)
- ngrok (for Shopify webhooks)

## Project Structure

```
AdNavi/
├── backend/          # FastAPI backend
├── ui/               # Next.js frontend
├── shopify-app/      # Shopify CLI app (web pixel extension)
├── compose.yaml      # Docker Compose for production
└── docs/             # Documentation
```

---

## Quick Start (All Services)

Open **5 terminal tabs** and run these commands:

### Terminal 1: PostgreSQL (Docker) (NO NEED TO RUN THIS IF YOU USE POSTGRES)
```bash
cd /Users/gabriellunesu/Git/AdNavi
docker run --name metricx-postgres -e POSTGRES_USER=metricx -e POSTGRES_PASSWORD=metricx -e POSTGRES_DB=metricx -p 5432:5432 -d postgres:15
```

### Terminal 2: Backend API
```bash
cd /Users/gabriellunesu/Git/AdNavi/backend
 source bin/activate
 uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 3: Worker (RQ)
```bash
cd /Users/gabriellunesu/Git/AdNavi/backend
 source bin/activate
python -u -m app.workers.start_worker
```

### Terminal 4: Frontend (Next.js)
```bash
cd /Users/gabriellunesu/Git/AdNavi/ui
npm run dev
```

### Terminal 5: ngrok (for Shopify webhooks)
```bash
ngrok http 8000
```

---

## Detailed Setup

### 1. Database (PostgreSQL)

**Option A: Docker (recommended)**
```bash
# Start PostgreSQL
docker run --name metricx-postgres \
  -e POSTGRES_USER=metricx \
  -e POSTGRES_PASSWORD=metricx \
  -e POSTGRES_DB=metricx \
  -p 5432:5432 \
  -d postgres:15

# Check it's running
docker ps

# Stop when done
docker stop metricx-postgres

# Start again later
docker start metricx-postgres
```

**Option B: Local PostgreSQL**
```bash
# macOS with Homebrew
brew install postgresql@15
brew services start postgresql@15
createdb metricx
```

### 2. Redis

The project uses Railway Redis by default (configured in `.env`). For local Redis:

```bash
# Option A: Docker
docker run --name metricx-redis -p 6379:6379 -d redis:7

# Option B: Homebrew
brew install redis
brew services start redis
```

Update `.env` if using local Redis:
```
REDIS_URL=redis://localhost:6379/0
```

### 3. Backend Setup

```bash
cd /Users/gabriellunesu/Git/AdNavi/backend

# Create virtual environment (first time only)
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Ensure Google Ads SDK is up to date (required for OAuth)
pip install --upgrade google-ads

# Run migrations
alembic upgrade head

# (Optional) Seed test data
python -m app.seed_mock
```

**Environment Variables** (`.env` file in backend/):
```bash
# Database
DATABASE_URL=postgresql+psycopg2://metricx:metricx@localhost:5432/metricx

# JWT
JWT_SECRET=your-secret-key-change-in-prod
JWT_EXPIRES_MINUTES=10080

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI (for QA/chat features)
OPENAI_API_KEY=sk-xxx

# Token Encryption
TOKEN_ENCRYPTION_KEY=your-32-byte-key-here

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000

# Shopify OAuth
SHOPIFY_API_KEY=your-shopify-api-key
SHOPIFY_API_SECRET=your-shopify-api-secret
SHOPIFY_OAUTH_REDIRECT_URI=http://localhost:8000/auth/shopify/callback

# Meta OAuth
META_APP_ID=xxx
META_APP_SECRET=xxx
META_OAUTH_REDIRECT_URI=http://localhost:8000/auth/meta/callback

# Google OAuth
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_DEVELOPER_TOKEN=xxx
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Frontend URL
FRONTEND_URL=http://localhost:3000

# Attribution Engine (ngrok for webhooks)
NGROK_URL=https://your-ngrok-url.ngrok-free.dev

# Meta CAPI (Conversions API)
META_PIXEL_ID=your-pixel-id
META_CAPI_ACCESS_TOKEN=your-capi-access-token  # Optional: override connection token
META_CAPI_TEST_EVENT_CODE=TEST12345           # Optional: test events in Events Manager

# Google Offline Conversions
GOOGLE_CONVERSION_ACTION_ID=your-conversion-action-id  # From Google Ads > Conversions
```

### 4. Frontend Setup

```bash
cd /Users/gabriellunesu/Git/AdNavi/ui

# Install dependencies
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### 5. Shopify App (Web Pixel Extension)

```bash
cd /Users/gabriellunesu/Git/AdNavi/shopify-app/metricx

# Install dependencies
npm install

# Run dev server (for testing extension locally)
shopify app dev

# Deploy extension updates
shopify app deploy
```

---

## Running Services

### Backend API Server
```bash
cd /Users/gabriellunesu/Git/AdNavi/backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Admin: http://localhost:8000/admin

### Worker (processes sync and QA jobs)
```bash
cd /Users/gabriellunesu/Git/AdNavi/backend
source .venv/bin/activate
python -m app.workers.start_worker
```

The worker processes two queues:
- `qa_jobs` - AI question answering
- `sync_jobs` - Data sync from ad platforms

### Scheduler (optional - auto-enqueues sync jobs)
```bash
cd /Users/gabriellunesu/Git/AdNavi/backend
source .venv/bin/activate
python -m app.services.sync_scheduler
```

### Frontend
```bash
cd /Users/gabriellunesu/Git/AdNavi/ui
npm run dev
```
- App: http://localhost:3000

---

## Webhooks with ngrok

Shopify webhooks require a public URL. Use ngrok to expose your local backend:

```bash
# Install ngrok (first time)
brew install ngrok

# Start tunnel
ngrok http 8000
```

This gives you a URL like `https://abc123.ngrok.io`. Update your Shopify app settings:
- **Webhook URL**: `https://abc123.ngrok.io/webhooks/shopify/orders`
- **OAuth Redirect**: `https://abc123.ngrok.io/auth/shopify/callback`

**Important**: Update these environment variables when using ngrok:
```bash
SHOPIFY_OAUTH_REDIRECT_URI=https://abc123.ngrok.io/auth/shopify/callback
BACKEND_URL=https://abc123.ngrok.io
```

---

## Database Migrations

```bash
cd /Users/gabriellunesu/Git/AdNavi/backend
source .venv/bin/activate

# Apply all migrations
alembic upgrade head

# Check current version
alembic current

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1
```

---

## Testing

### Backend Tests
```bash
cd /Users/gabriellunesu/Git/AdNavi/backend
source .venv/bin/activate
pytest
```

### Frontend Tests
```bash
cd /Users/gabriellunesu/Git/AdNavi/ui
npm test
```

---

## Common Issues

### Port already in use
```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>
```

### Database connection refused
Make sure PostgreSQL is running:
```bash
docker ps  # Check if container is running
docker start metricx-postgres  # Start if stopped
```

### Redis connection error
Check Redis is running and REDIS_URL is correct:
```bash
redis-cli ping  # Should return PONG
```

### Worker not processing jobs
1. Check Redis connection
2. Check worker is running
3. Look at worker logs for errors

### Google Ads OAuth "failed to fetch accounts"
This is usually a **google-ads SDK version issue**. Google deprecates old API versions regularly.

**Error message**: `501 GRPC target method can't be resolved`

**Fix**: Upgrade the google-ads package:
```bash
pip install --upgrade google-ads
```

Required version: **28.0.0+** (as of Dec 2025). Older versions use deprecated API endpoints.

### Meta/Google OAuth 400 errors in console
If you see `api/connections/google/from-env` or `api/connections/meta/from-env` returning 400:
- These are dev-mode shortcuts that create connections from env vars
- They fail if the required env vars aren't set (expected behavior)
- Users should use the OAuth flow via connect buttons instead
- These errors don't affect normal OAuth functionality

---

## Useful Commands

```bash
# View backend logs
tail -f /var/log/uvicorn.log

# View worker logs (printed to stdout)
# Just watch the terminal where worker is running

# Check Redis queue sizes
redis-cli
> LLEN rq:queue:qa_jobs
> LLEN rq:queue:sync_jobs

# Clear all Redis queues (careful!)
redis-cli FLUSHALL

# Reset database (careful!)
dropdb metricx && createdb metricx && alembic upgrade head
```

---

## Service URLs (Local)

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Admin Panel | http://localhost:8000/admin |
| Pixel Events | http://localhost:8000/v1/pixel-events |
