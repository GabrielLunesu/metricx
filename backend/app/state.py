"""
Application State
=================

Global application state that persists across requests.

WHY this exists:
- Context manager needs to persist between HTTP requests
- Each QAService instance is created per-request and destroyed after
- Without shared state, conversation context is lost
- Redis connection pool should be shared to avoid connection overhead

WHAT it stores:
- context_manager: Singleton RedisContextManager instance for all QA requests
- redis_pool: Shared Redis connection pool (caching, pub/sub)
- redis_client: Shared Redis client instance

WHERE it's used:
- app/main.py: Initializes on startup with Redis validation
- app/routers/qa.py: Uses shared redis_client for caching
- app/workers/arq_worker.py: ARQ handles job queuing separately

Design:
- Simple module-level singleton pattern
- Thread-safe (Redis client has connection pooling)
- Redis-backed for production scalability
- ARQ manages its own Redis connection for job queuing
"""

import logging
from redis import Redis, ConnectionPool
from app.context.redis_context_manager import RedisContextManager
from app.deps import get_settings

logger = logging.getLogger(__name__)

# Shared Redis connection pool - reused across all requests
# Used for: caching, pub/sub, context management
# Note: ARQ worker manages its own Redis connection for job queuing
redis_pool: ConnectionPool | None = None
redis_client: Redis | None = None

# Singleton instance - shared across all requests
# This persists for the lifetime of the FastAPI application
# Uses Redis for distributed session storage across multiple instances
context_manager = None
try:
    settings = get_settings()

    # Initialize shared Redis connection pool
    redis_pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=20,  # Pool size for concurrent requests
        decode_responses=False,
    )
    redis_client = Redis(connection_pool=redis_pool)
    logger.info("[STATE] Shared Redis connection pool initialized (max_connections=20)")

    # Initialize context manager (uses its own pool internally)
    context_manager = RedisContextManager(
        redis_url=settings.REDIS_URL,
        max_history=settings.CONTEXT_MAX_HISTORY,
        ttl_seconds=settings.CONTEXT_TTL_SECONDS
    )
    logger.info("[STATE] Redis context manager initialized successfully")
except Exception as e:
    logger.error(f"[STATE] Failed to initialize Redis: {e}")
    logger.warning("[STATE] App will start but some features may be unavailable until Redis is configured")
    logger.warning(f"[STATE] REDIS_URL was: {settings.REDIS_URL if 'settings' in locals() else 'not loaded'}")
    # Don't raise - allow app to start. Individual requests will handle None

