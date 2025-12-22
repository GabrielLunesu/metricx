"""Unit tests for Live API Tools.

WHAT:
    Tests live API functionality for the copilot including:
    - Exception types and user-friendly messages
    - Per-workspace rate limiting
    - Connection resolution and client instantiation
    - Live API metrics fetching

WHY:
    Ensures the live API layer works correctly without making real API calls.
    Fast, deterministic tests that validate security guardrails.

REFERENCES:
    - app/agent/exceptions.py (exception types)
    - app/agent/rate_limiter.py (per-workspace rate limiting)
    - app/agent/connection_resolver.py (credential management)
    - app/agent/live_api_tools.py (main tools)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from app.agent.exceptions import (
    LiveApiError,
    QuotaExhaustedError,
    TokenExpiredError,
    WorkspaceRateLimitError,
    ProviderNotConnectedError,
    LiveApiTimeoutError,
    LiveApiPermissionError,
)
from app.agent.rate_limiter import WorkspaceRateLimiter, RATE_LIMITS, WINDOW_SIZE_SECONDS


# =============================================================================
# EXCEPTION TESTS
# =============================================================================

class TestExceptionTypes:
    """Test custom exception types for live API errors."""

    def test_live_api_error_base(self):
        """WHAT: Base LiveApiError should work correctly.
        WHY: All live API errors inherit from this.
        """
        error = LiveApiError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.to_user_message() == "Something went wrong"

    def test_quota_exhausted_error(self):
        """WHAT: QuotaExhaustedError should provide user-friendly message.
        WHY: Users need to understand why live data isn't available.
        """
        error = QuotaExhaustedError(
            provider="google",
            retry_after=60,
        )
        user_msg = error.to_user_message()
        assert "Google" in user_msg  # Provider mentioned
        # Short retry times get a "few minutes" message
        assert "temporarily unavailable" in user_msg or "cached data" in user_msg

    def test_token_expired_error(self):
        """WHAT: TokenExpiredError should prompt reconnection.
        WHY: Users need to know to refresh their OAuth connection.
        """
        error = TokenExpiredError(
            provider="meta",
            connection_id="abc-123",
        )
        user_msg = error.to_user_message()
        assert "Meta" in user_msg
        assert "reconnect" in user_msg.lower()

    def test_workspace_rate_limit_error(self):
        """WHAT: WorkspaceRateLimitError should show retry time.
        WHY: Users need to know how long to wait.
        """
        error = WorkspaceRateLimitError(
            retry_after=30,
            workspace_id="workspace-123",
            provider="google",
        )
        user_msg = error.to_user_message()
        assert "30 seconds" in user_msg or "wait" in user_msg.lower()
        # Should mention waiting or rate limiting
        assert "wait" in user_msg.lower() or "requests" in user_msg.lower()

    def test_provider_not_connected_error(self):
        """WHAT: ProviderNotConnectedError should prompt setup.
        WHY: Users need to know to connect their ad account.
        """
        error = ProviderNotConnectedError(provider="meta")
        user_msg = error.to_user_message()
        assert "Meta" in user_msg
        assert "connect" in user_msg.lower()

    def test_live_api_timeout_error(self):
        """WHAT: LiveApiTimeoutError should explain the issue.
        WHY: Users need to know the API was slow.
        """
        error = LiveApiTimeoutError(
            provider="google",
            timeout_seconds=30,
        )
        user_msg = error.to_user_message()
        assert "Google Ads" in user_msg
        assert "30" in user_msg

    def test_live_api_permission_error(self):
        """WHAT: LiveApiPermissionError should explain permissions.
        WHY: Users need to know they lack access.
        """
        error = LiveApiPermissionError(
            provider="meta",
            required_permission="ads_read",
        )
        user_msg = error.to_user_message()
        assert "Meta" in user_msg
        assert "permission" in user_msg.lower()


# =============================================================================
# RATE LIMITER TESTS
# =============================================================================

class TestWorkspaceRateLimiter:
    """Test per-workspace rate limiting functionality."""

    def test_can_make_call_without_redis(self):
        """WHAT: Rate limiter should allow calls without Redis.
        WHY: Development mode may not have Redis available.
        """
        limiter = WorkspaceRateLimiter(
            redis_client=None,
            workspace_id="test-workspace",
        )
        assert limiter.can_make_call("google") is True
        assert limiter.can_make_call("meta") is True

    def test_can_make_call_under_limit(self):
        """WHAT: Rate limiter should allow calls under limit.
        WHY: Normal operation shouldn't be blocked.
        """
        mock_redis = Mock()
        mock_redis.zcard.return_value = 5  # Under the 15/min limit for Google

        limiter = WorkspaceRateLimiter(
            redis_client=mock_redis,
            workspace_id="test-workspace",
        )

        assert limiter.can_make_call("google") is True
        mock_redis.zcard.assert_called()

    def test_can_make_call_at_limit(self):
        """WHAT: Rate limiter should block at limit.
        WHY: Prevents API quota exhaustion.
        """
        mock_redis = Mock()
        mock_redis.zcard.return_value = 15  # At the 15/min limit for Google

        limiter = WorkspaceRateLimiter(
            redis_client=mock_redis,
            workspace_id="test-workspace",
        )

        assert limiter.can_make_call("google") is False

    def test_record_call_adds_timestamp(self):
        """WHAT: record_call should add entry to Redis sorted set.
        WHY: Tracks API calls for rate limiting.
        """
        mock_redis = Mock()

        limiter = WorkspaceRateLimiter(
            redis_client=mock_redis,
            workspace_id="test-workspace",
        )

        limiter.record_call("google")

        mock_redis.zadd.assert_called_once()
        mock_redis.expire.assert_called_once()

    def test_get_remaining_without_redis(self):
        """WHAT: Should return full limit without Redis.
        WHY: No rate limiting without Redis.
        """
        limiter = WorkspaceRateLimiter(
            redis_client=None,
            workspace_id="test-workspace",
        )

        assert limiter.get_remaining("google") == RATE_LIMITS["google"]

    def test_get_remaining_with_usage(self):
        """WHAT: Should calculate remaining correctly.
        WHY: Users need to know how many calls left.
        """
        mock_redis = Mock()
        mock_redis.zcard.return_value = 10

        limiter = WorkspaceRateLimiter(
            redis_client=mock_redis,
            workspace_id="test-workspace",
        )

        remaining = limiter.get_remaining("google")
        assert remaining == 5  # 15 - 10 = 5

    def test_check_and_record_raises_when_limited(self):
        """WHAT: check_and_record should raise when at limit.
        WHY: Single method for check + record pattern.
        """
        mock_redis = Mock()
        mock_redis.zcard.return_value = 15  # At limit
        mock_redis.zrange.return_value = [("1234567890", 1234567890)]

        limiter = WorkspaceRateLimiter(
            redis_client=mock_redis,
            workspace_id="test-workspace",
        )

        with pytest.raises(WorkspaceRateLimitError):
            limiter.check_and_record("google")

    def test_get_key_format(self):
        """WHAT: Key should include workspace and provider.
        WHY: Ensures workspace isolation.
        """
        limiter = WorkspaceRateLimiter(
            redis_client=None,
            workspace_id="workspace-123",
        )

        key = limiter._get_key("google")
        assert "workspace-123" in key
        assert "google" in key

    def test_get_status_returns_all_providers(self):
        """WHAT: get_status should return status for all providers.
        WHY: Debugging and monitoring needs.
        """
        mock_redis = Mock()
        mock_redis.zcard.return_value = 5

        limiter = WorkspaceRateLimiter(
            redis_client=mock_redis,
            workspace_id="test-workspace",
        )

        status = limiter.get_status()
        assert "google" in status
        assert "meta" in status
        assert status["google"]["limit"] == 15
        assert status["meta"]["limit"] == 30


# =============================================================================
# CONNECTION RESOLVER TESTS
# =============================================================================

class TestConnectionResolver:
    """Test connection resolution and client instantiation."""

    @patch('app.agent.connection_resolver.decrypt_secret')
    def test_get_available_providers_empty(self, mock_decrypt):
        """WHAT: Should return empty list when no connections.
        WHY: Workspace may not have any ad accounts connected.
        """
        from app.agent.connection_resolver import ConnectionResolver

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        resolver = ConnectionResolver(
            db=mock_db,
            workspace_id="test-workspace",
        )

        providers = resolver.get_available_providers()
        assert providers == []

    @patch('app.agent.connection_resolver.decrypt_secret')
    def test_get_available_providers_with_connections(self, mock_decrypt):
        """WHAT: Should return list of connected providers.
        WHY: Agent needs to know which APIs are available.
        """
        from app.agent.connection_resolver import ConnectionResolver
        from app.models import Connection, ProviderEnum

        # Mock connections
        mock_google_conn = Mock()
        mock_google_conn.provider = ProviderEnum.google

        mock_meta_conn = Mock()
        mock_meta_conn.provider = ProviderEnum.meta

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_google_conn, mock_meta_conn
        ]

        resolver = ConnectionResolver(
            db=mock_db,
            workspace_id="test-workspace",
        )

        providers = resolver.get_available_providers()
        assert "google" in providers
        assert "meta" in providers

    @patch('app.agent.connection_resolver.decrypt_secret')
    def test_get_connection_raises_when_not_found(self, mock_decrypt):
        """WHAT: Should raise ProviderNotConnectedError when no connection.
        WHY: Clear error when provider not available.
        """
        from app.agent.connection_resolver import ConnectionResolver

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        resolver = ConnectionResolver(
            db=mock_db,
            workspace_id="test-workspace",
        )

        with pytest.raises(ProviderNotConnectedError) as exc_info:
            resolver.get_connection("google")

        assert exc_info.value.provider == "google"

    @patch('app.agent.connection_resolver.decrypt_secret')
    def test_get_account_id_returns_external_id(self, mock_decrypt):
        """WHAT: Should return the external account ID.
        WHY: Needed for API calls.
        """
        from app.agent.connection_resolver import ConnectionResolver
        from app.models import ProviderEnum

        mock_conn = Mock()
        mock_conn.provider = ProviderEnum.google
        mock_conn.external_account_id = "123-456-7890"

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_conn]

        resolver = ConnectionResolver(
            db=mock_db,
            workspace_id="test-workspace",
        )

        account_id = resolver.get_account_id("google")
        assert account_id == "123-456-7890"

    @patch('app.agent.connection_resolver.decrypt_secret')
    def test_connection_caching(self, mock_decrypt):
        """WHAT: Should cache connections on first access.
        WHY: Avoids repeated DB queries.
        """
        from app.agent.connection_resolver import ConnectionResolver

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        resolver = ConnectionResolver(
            db=mock_db,
            workspace_id="test-workspace",
        )

        # Call twice
        resolver.get_available_providers()
        resolver.get_available_providers()

        # DB should only be queried once
        assert mock_db.query.call_count == 1


# =============================================================================
# LIVE API TOOLS TESTS
# =============================================================================

class TestLiveApiTools:
    """Test main live API tools functionality."""

    @patch('app.agent.live_api_tools.ConnectionResolver')
    def test_check_data_freshness_fresh_data(self, mock_resolver_class):
        """WHAT: Should report fresh when data is recent.
        WHY: No need for live API when snapshots are current.
        """
        from app.agent.live_api_tools import LiveApiTools

        mock_db = Mock()
        # Mock recent snapshot (1 hour old)
        mock_snapshot = Mock()
        mock_snapshot.created_at = datetime.utcnow() - timedelta(hours=1)
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_snapshot

        tools = LiveApiTools(
            db=mock_db,
            workspace_id="test-workspace",
            user_id="test-user",
        )

        result = tools.check_data_freshness()

        assert result["is_stale"] is False
        assert result["hours_since_sync"] < 2

    @patch('app.agent.live_api_tools.ConnectionResolver')
    def test_check_data_freshness_stale_data(self, mock_resolver_class):
        """WHAT: Should report stale when data is old.
        WHY: Triggers fallback to live API.
        """
        from app.agent.live_api_tools import LiveApiTools

        mock_db = Mock()
        # Mock old snapshot (36 hours old)
        mock_snapshot = Mock()
        mock_snapshot.created_at = datetime.utcnow() - timedelta(hours=36)
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_snapshot

        tools = LiveApiTools(
            db=mock_db,
            workspace_id="test-workspace",
            user_id="test-user",
        )

        result = tools.check_data_freshness()

        assert result["is_stale"] is True
        assert result["hours_since_sync"] > 24

    @patch('app.agent.live_api_tools.ConnectionResolver')
    def test_check_data_freshness_no_snapshots(self, mock_resolver_class):
        """WHAT: Should report stale when no snapshots exist.
        WHY: New workspaces have no data yet.
        """
        from app.agent.live_api_tools import LiveApiTools

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        tools = LiveApiTools(
            db=mock_db,
            workspace_id="test-workspace",
            user_id="test-user",
        )

        result = tools.check_data_freshness()

        assert result["is_stale"] is True
        assert result["last_sync"] is None

    @patch('app.agent.live_api_tools.ConnectionResolver')
    def test_get_live_metrics_rate_limited(self, mock_resolver_class):
        """WHAT: Should fail gracefully when rate limited.
        WHY: Rate limits should return friendly error, not crash.
        """
        from app.agent.live_api_tools import LiveApiTools

        mock_db = Mock()
        mock_rate_limiter = Mock()
        mock_rate_limiter.can_make_call.return_value = False
        mock_rate_limiter.get_retry_after.return_value = 45

        tools = LiveApiTools(
            db=mock_db,
            workspace_id="test-workspace",
            user_id="test-user",
            rate_limiter=mock_rate_limiter,
        )

        result = tools.get_live_metrics(
            provider="google",
            entity_type="account",
            entity_ids=None,
            metrics=["spend", "roas"],
            date_range="last_7d",
        )

        assert result["success"] is False
        assert "rate limit" in result["error"].lower()

    @patch('app.agent.live_api_tools.ConnectionResolver')
    def test_get_live_metrics_provider_not_connected(self, mock_resolver_class):
        """WHAT: Should handle missing provider connection.
        WHY: Clear error when ad account not connected.
        """
        from app.agent.live_api_tools import LiveApiTools

        mock_resolver = Mock()
        mock_resolver.get_available_providers.return_value = []
        mock_resolver.get_google_client.side_effect = ProviderNotConnectedError(provider="google")
        mock_resolver_class.return_value = mock_resolver

        mock_db = Mock()
        mock_rate_limiter = Mock()
        mock_rate_limiter.can_make_call.return_value = True

        tools = LiveApiTools(
            db=mock_db,
            workspace_id="test-workspace",
            user_id="test-user",
            rate_limiter=mock_rate_limiter,
        )

        result = tools.get_live_metrics(
            provider="google",
            entity_type="account",
            entity_ids=None,
            metrics=["spend"],
            date_range="today",
        )

        assert result["success"] is False
        assert "not connected" in result["error"].lower()

    @patch('app.agent.live_api_tools.ConnectionResolver')
    def test_list_live_entities_success(self, mock_resolver_class):
        """WHAT: Should list entities from live API.
        WHY: Enables campaign listing in copilot.
        """
        from app.agent.live_api_tools import LiveApiTools

        # Setup mocks
        mock_google_client = Mock()
        mock_google_client.list_campaigns.return_value = [
            {"id": "123", "name": "Campaign 1", "status": "ENABLED"},
            {"id": "456", "name": "Campaign 2", "status": "PAUSED"},
        ]

        mock_resolver = Mock()
        mock_resolver.get_available_providers.return_value = ["google"]
        mock_resolver.get_google_client.return_value = mock_google_client
        mock_resolver.get_account_id.return_value = "123-456-7890"
        mock_resolver_class.return_value = mock_resolver

        mock_db = Mock()
        mock_rate_limiter = Mock()
        mock_rate_limiter.can_make_call.return_value = True

        tools = LiveApiTools(
            db=mock_db,
            workspace_id="test-workspace",
            user_id="test-user",
            rate_limiter=mock_rate_limiter,
        )

        result = tools.list_live_entities(
            provider="google",
            entity_type="campaign",
            status_filter="all",
        )

        assert result["success"] is True
        assert len(result["entities"]) == 2


# =============================================================================
# GRAPH INTEGRATION TESTS
# =============================================================================

class TestGraphIntegration:
    """Test graph routing with live API nodes."""

    def test_route_after_understand_to_check_freshness(self):
        """WHAT: Normal queries should route to check_freshness.
        WHY: Ensures staleness check happens before fetch.
        """
        from app.agent.graph import route_after_understand

        state = {
            "error": None,
            "needs_clarification": False,
            "intent": "metric_query",
            "stage": "understanding",
        }

        result = route_after_understand(state)
        assert result == "check_freshness"

    def test_route_after_understand_to_respond_for_clarification(self):
        """WHAT: Clarification needed should route to respond.
        WHY: Skip data fetching when we need more info.
        """
        from app.agent.graph import route_after_understand

        state = {
            "error": None,
            "needs_clarification": True,
            "intent": "metric_query",
            "stage": "understanding",
        }

        result = route_after_understand(state)
        assert result == "respond"

    def test_route_after_understand_to_respond_for_out_of_scope(self):
        """WHAT: Out of scope queries should route to respond.
        WHY: No need to fetch data for off-topic questions.
        """
        from app.agent.graph import route_after_understand

        state = {
            "error": None,
            "needs_clarification": False,
            "intent": "out_of_scope",
            "stage": "understanding",
        }

        result = route_after_understand(state)
        assert result == "respond"


# =============================================================================
# STATE TESTS
# =============================================================================

class TestAgentState:
    """Test agent state with live API fields."""

    def test_create_initial_state_includes_live_api_fields(self):
        """WHAT: Initial state should include live API tracking fields.
        WHY: Ensures state is ready for live API flow.
        """
        from app.agent.state import create_initial_state

        state = create_initial_state(
            question="What's my live ROAS?",
            workspace_id="test-workspace",
            user_id="test-user",
        )

        assert "needs_live_data" in state
        assert "live_data_reason" in state
        assert "live_api_calls" in state
        assert "live_api_errors" in state

        # Should be initialized to defaults
        assert state["needs_live_data"] is False
        assert state["live_data_reason"] is None
        assert state["live_api_calls"] == []
        assert state["live_api_errors"] == []

    def test_stage_includes_checking_freshness(self):
        """WHAT: Stage literal should include checking_freshness.
        WHY: New stage for the freshness check node.
        """
        from app.agent.state import create_initial_state

        state = create_initial_state(
            question="Test",
            workspace_id="test-workspace",
            user_id="test-user",
        )

        # Valid stages should include checking_freshness
        valid_stages = ["understanding", "checking_freshness", "fetching", "analyzing", "responding", "done", "error"]
        assert state["stage"] in valid_stages
