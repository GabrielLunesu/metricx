"""
Agent Safety Module.

WHAT:
    Safety mechanisms that prevent agents from causing damage.
    Includes rate limiting, circuit breakers, entity locking, and validation.

WHY:
    Agents are autonomous - they need guardrails:
    - Prevent runaway budget increases
    - Stop if performance degrades after actions
    - Avoid race conditions between multiple agents
    - Adapt to manual changes made outside the system

PHILOSOPHY:
    1. Aggressive by default - Full auto from start, users trust the system
    2. Adapt to manual changes - When humans intervene, update baseline and continue
    3. Hard limits protect - Circuit breakers and caps prevent disasters
    4. Always auditable - Every decision logged with reasoning
    5. Always reversible - State before/after stored, rollback possible

MODULES:
    - pre_action_validator: Fetch live state, validate preconditions
    - baseline_reconciler: Detect and adapt to external changes
    - circuit_breaker: Performance/failure monitoring
    - rate_limiter: Action rate limiting
    - entity_locker: Redis-based entity locking (prevent races)

REFERENCES:
    - Agent System Implementation Plan (Safety Architecture section)
"""

from .rate_limiter import RateLimiter, RateLimitResult
from .circuit_breaker import CircuitBreaker, CircuitBreakerResult

__all__ = [
    "RateLimiter",
    "RateLimitResult",
    "CircuitBreaker",
    "CircuitBreakerResult",
]
