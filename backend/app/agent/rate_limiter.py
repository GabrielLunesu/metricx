"""
Workspace Rate Limiter
======================

**Version**: 1.0.0
**Created**: 2025-12-17

Per-workspace rate limiting for live API calls to prevent abuse.

WHY THIS FILE EXISTS
--------------------
Live API calls to Google/Meta Ads consume shared quota. Without rate limiting:
- A single workspace could exhaust API quotas for all users
- Malicious or buggy code could spam the APIs
- Costs could escalate unexpectedly

This module implements per-workspace sliding window rate limiting.

RATE LIMITS
-----------
- Google Ads: 15 calls per minute per workspace
- Meta Ads: 30 calls per minute per workspace

These are conservative limits well below the actual API quotas to leave
headroom for sync jobs and other background processes.

RELATED FILES
-------------
- app/agent/live_api_tools.py: Uses this limiter before API calls
- app/agent/exceptions.py: WorkspaceRateLimitError
- app/state.py: Shared Redis client
"""

import logging
import time
from typing import Optional, Dict, Literal

from redis import Redis

from app.agent.exceptions import WorkspaceRateLimitError

logger = logging.getLogger(__name__)

# Rate limits per provider (calls per minute per workspace)
RATE_LIMITS: Dict[str, int] = {
    "google": 15,  # 15 calls/min/workspace
    "meta": 30,    # 30 calls/min/workspace
}

# Window size in seconds (1 minute sliding window)
WINDOW_SIZE_SECONDS = 60


class WorkspaceRateLimiter:
    """
    Redis-backed sliding window rate limiter for live API calls.

    WHAT:
        Limits API calls per workspace per provider using a sliding window.
        Each workspace has independent limits for Google and Meta APIs.

    WHY:
        - Prevents any single workspace from exhausting shared API quotas
        - Protects against accidental loops or abuse
        - Leaves headroom for background sync jobs

    HOW:
        Uses Redis sorted sets with timestamps as scores.
        - Key format: "live_api_rate:{workspace_id}:{provider}"
        - Each call adds a timestamp to the sorted set
        - Old entries (outside window) are removed on each check
        - Count of entries in window determines if limit exceeded

    USAGE:
        limiter = WorkspaceRateLimiter(redis_client, workspace_id)

        # Check before making call
        if not limiter.can_make_call("google"):
            raise WorkspaceRateLimitError(...)

        # Record the call after making it
        limiter.record_call("google")

    THREAD SAFETY:
        Redis operations are atomic. Multiple concurrent requests are safe.
    """

    def __init__(
        self,
        redis_client: Optional[Redis],
        workspace_id: str,
    ):
        """
        Initialize rate limiter for a workspace.

        PARAMETERS:
            redis_client: Shared Redis client (from app.state)
            workspace_id: UUID of the workspace to rate limit
        """
        self.redis = redis_client
        self.workspace_id = str(workspace_id)

        if not self.redis:
            logger.warning(
                f"[RATE_LIMITER] No Redis client - rate limiting disabled for {workspace_id}"
            )

    def _get_key(self, provider: str) -> str:
        """
        Get Redis key for this workspace + provider.

        PARAMETERS:
            provider: "google" or "meta"

        RETURNS:
            Redis key string
        """
        return f"live_api_rate:{self.workspace_id}:{provider}"

    def _cleanup_window(self, key: str) -> None:
        """
        Remove entries outside the sliding window.

        WHAT:
            Deletes timestamps older than WINDOW_SIZE_SECONDS.

        WHY:
            Keeps the sorted set small and accurate.
        """
        if not self.redis:
            return

        cutoff = time.time() - WINDOW_SIZE_SECONDS
        # Remove all entries with score (timestamp) less than cutoff
        self.redis.zremrangebyscore(key, "-inf", cutoff)

    def can_make_call(self, provider: Literal["google", "meta"]) -> bool:
        """
        Check if workspace can make another API call.

        WHAT:
            Checks if current call count is under the limit.

        WHY:
            Must check BEFORE making the API call to avoid exceeding limits.

        PARAMETERS:
            provider: Which API ("google" or "meta")

        RETURNS:
            True if call is allowed, False if rate limited
        """
        if not self.redis:
            # No Redis = no rate limiting (development mode)
            return True

        limit = RATE_LIMITS.get(provider, 15)
        key = self._get_key(provider)

        # Clean up old entries
        self._cleanup_window(key)

        # Count entries in current window
        current_count = self.redis.zcard(key)

        allowed = current_count < limit

        if not allowed:
            logger.warning(
                f"[RATE_LIMITER] Workspace {self.workspace_id} hit {provider} rate limit "
                f"({current_count}/{limit} calls/min)"
            )

        return allowed

    def record_call(self, provider: Literal["google", "meta"]) -> None:
        """
        Record that an API call was made.

        WHAT:
            Adds current timestamp to the sliding window.

        WHY:
            Tracks call history for rate limiting.

        PARAMETERS:
            provider: Which API ("google" or "meta")

        NOTE:
            Call this AFTER a successful API call, not before.
        """
        if not self.redis:
            return

        key = self._get_key(provider)
        now = time.time()

        # Add current timestamp to sorted set
        # Score = timestamp, Member = unique ID (timestamp with microseconds)
        self.redis.zadd(key, {f"{now}": now})

        # Set TTL on key so it auto-expires if not used
        # TTL = 2x window to ensure cleanup happens
        self.redis.expire(key, WINDOW_SIZE_SECONDS * 2)

        logger.debug(
            f"[RATE_LIMITER] Recorded {provider} call for workspace {self.workspace_id}"
        )

    def get_remaining(self, provider: Literal["google", "meta"]) -> int:
        """
        Get number of remaining calls allowed in current window.

        WHAT:
            Returns how many more API calls are allowed.

        WHY:
            Useful for logging, debugging, or informing users.

        PARAMETERS:
            provider: Which API ("google" or "meta")

        RETURNS:
            Number of remaining calls allowed (>= 0)
        """
        if not self.redis:
            return RATE_LIMITS.get(provider, 15)  # No limit without Redis

        limit = RATE_LIMITS.get(provider, 15)
        key = self._get_key(provider)

        # Clean up old entries
        self._cleanup_window(key)

        # Count entries in current window
        current_count = self.redis.zcard(key)

        return max(0, limit - current_count)

    def get_retry_after(self, provider: Literal["google", "meta"]) -> int:
        """
        Get seconds until rate limit resets (oldest entry expires).

        WHAT:
            Calculates how long until at least one slot opens up.

        WHY:
            Used in WorkspaceRateLimitError to tell user when to retry.

        PARAMETERS:
            provider: Which API ("google" or "meta")

        RETURNS:
            Seconds until limit resets (at least 1 slot available)
        """
        if not self.redis:
            return 0

        key = self._get_key(provider)

        # Get the oldest entry (lowest score)
        oldest = self.redis.zrange(key, 0, 0, withscores=True)

        if not oldest:
            return 0

        # oldest is [(member, score)] where score is timestamp
        oldest_timestamp = oldest[0][1]
        expires_at = oldest_timestamp + WINDOW_SIZE_SECONDS

        retry_after = int(expires_at - time.time())
        return max(1, retry_after)  # At least 1 second

    def check_and_record(
        self,
        provider: Literal["google", "meta"],
    ) -> None:
        """
        Check rate limit and record call in one operation.

        WHAT:
            Convenience method that checks limit, raises if exceeded,
            otherwise records the call.

        WHY:
            Simplifies the common pattern of check-then-record.

        PARAMETERS:
            provider: Which API ("google" or "meta")

        RAISES:
            WorkspaceRateLimitError: If rate limit exceeded
        """
        if not self.can_make_call(provider):
            retry_after = self.get_retry_after(provider)
            raise WorkspaceRateLimitError(
                retry_after=retry_after,
                workspace_id=self.workspace_id,
                provider=provider,
            )

        self.record_call(provider)

    def get_status(self) -> Dict[str, Dict[str, int]]:
        """
        Get current rate limit status for all providers.

        WHAT:
            Returns current usage and limits for debugging.

        RETURNS:
            Dict with status per provider:
            {
                "google": {"used": 5, "limit": 15, "remaining": 10},
                "meta": {"used": 10, "limit": 30, "remaining": 20}
            }
        """
        status = {}

        for provider, limit in RATE_LIMITS.items():
            remaining = self.get_remaining(provider)
            used = limit - remaining

            status[provider] = {
                "used": used,
                "limit": limit,
                "remaining": remaining,
            }

        return status
