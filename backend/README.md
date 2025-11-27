# metricx Backend (FastAPI + PostgreSQL + SQLAlchemy + Alembic)

This service provides email/password authentication using JWT stored in an HTTP-only cookie, backed by PostgreSQL. It is designed to work with the metricx Next.js frontend at `http://localhost:3000`.

## Prerequisites
- Python 3.11+
- Docker (for PostgreSQL and Redis)
- A virtual environment (recommended)

to run: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 

## .env
Create a `.env` file in this directory with the following keys:

```
# JWT
JWT_SECRET=change_me_in_prod
JWT_EXPIRES_MINUTES=10080

# DB (match docker-compose service, user, pass, db)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=metricx
POSTGRES_PASSWORD=metricx
POSTGRES_DB=metricx

# SQLAlchemy URL (sync driver)
DATABASE_URL=postgresql+psycopg2://metricx:metricx@localhost:5432/metricx

# CORS / Cookies
BACKEND_CORS_ORIGINS=http://localhost:3000
COOKIE_DOMAIN=localhost

# Redis (for conversation context)
# Option 1: Railway Redis (set this for both local and production)
REDIS_URL=redis://default:aeauElUBRUoaHdgmBsgXntUcDsqPuRpm@gondola.proxy.rlwy.net:41155
# Option 2: Local Redis (uncomment this and comment above for local-only)
# REDIS_URL=redis://localhost:6379/0
CONTEXT_MAX_HISTORY=5
CONTEXT_TTL_SECONDS=3600
```

## Start DB (Redis uses Railway)
```bash
cd ..
docker compose up -d
# PostgreSQL runs locally
# Redis uses Railway instance (configured via REDIS_URL)
```

## Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run Migrations
```bash
alembic upgrade head
```

## Seed Mock Data (Optional)
To populate the database with test data for development:
```bash
python -m app.seed_mock
```

This creates:
- Workspace: "Defang Labs"
- Users: owner@defanglabs.com / viewer@defanglabs.com (password: password123)
- Mock connection with entity hierarchy (2 campaigns > 4 adsets > 8 ads)
- 30 days of metric data (240 records)
- P&L snapshots with calculated CPA/ROAS

View the data at: http://localhost:8000/admin

## Run API
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test
```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Login (sets cookie)
curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Me
curl -i http://localhost:8000/auth/me

# Logout
curl -i -X POST http://localhost:8000/auth/logout
```

## Alembic
- Configured via `alembic.ini` and `alembic/` directory
- First migration creates `users` table

```bash
alembic revision --autogenerate -m "create users"
alembic upgrade head
```

## Notes
- Do not call `Base.metadata.create_all()`; use migrations only.
- JWT is stored as an HTTP-only cookie named `access_token` with value `Bearer <jwt>`.
- CORS allows `http://localhost:3000` with credentials.

## How the AI andpoints (chat and answer work with user data)


User asks a question
Example: “Why is my CVR down this week?”

AI translates question → DSL (Domain-Specific Language)

We send the question to OpenAI with a system prompt that says: “Always output JSON following this schema…”.

The LLM doesn’t do any math — it just produces structured JSON.

Example DSL:

{
  "metric": "cvr",
  "time_range": { "last_n_days": 7 },
  "compare_to_previous": true,
  "group_by": "campaign",
  "filters": {}
}


Backend validates DSL

We use Pydantic (MetricQuery) to ensure the JSON is valid.

If invalid, we reject the request (safe against prompt injection).

Metrics Service executes DSL

DSL is passed to our MetricService, which queries MetricFact in Postgres.

It computes totals, derived metrics (ROAS, CPA, CVR), comparisons, and groupings.

AI Service builds an answer

Results from MetricService are turned into a human-readable summary.

Example: “Your CVR decreased by 12% compared to last week. Campaign ‘Shoes’ dropped the most.”

Everything is logged

The full interaction (question, DSL, answer, duration) is stored in QaQueryLog for history.

Frontend renders chat

User’s question → user bubble.

Copilot answer → AI bubble.

History is pulled from QaQueryLog so the conversation feels persistent.



