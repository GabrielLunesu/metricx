"""Unit tests for MetaAdsClient service.

WHAT:
    Tests Meta Ads API client functionality with mocked Facebook SDK responses.
    Verifies rate limiting, pagination, error handling, and data fetching.

WHY:
    Ensures MetaAdsClient works correctly without making real API calls.
    Fast, deterministic tests that don't require Meta credentials.

REFERENCES:
    - app/services/meta_ads_client.py (module under test)
    - facebook_business SDK (mocked)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from time import time

from app.services.meta_ads_client import (
    MetaAdsClient,
    MetaAdsClientError,
    MetaAdsAuthenticationError,
    MetaAdsPermissionError,
    MetaAdsValidationError,
    rate_limit,
)
from facebook_business.exceptions import FacebookRequestError


class TestRateLimiting:
    """Test rate limiting decorator functionality."""
    
    def test_rate_limit_allows_under_limit(self):
        """WHAT: Rate limiter should allow calls under the limit.
        WHY: Ensures normal operation doesn't block valid calls.
        """
        call_count = 0
        
        @rate_limit(calls_per_hour=5)
        def dummy_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        # Should allow 5 calls without blocking
        for _ in range(5):
            assert dummy_func() == "success"
        
        assert call_count == 5
    
    def test_rate_limit_blocks_when_exceeded(self):
        """WHAT: Rate limiter should block calls when limit exceeded.
        WHY: Prevents exceeding Meta's 200 calls/hour limit.
        """
        call_count = 0
        
        @rate_limit(calls_per_hour=2)
        def dummy_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        # First 2 calls should succeed immediately
        start = time()
        dummy_func()
        dummy_func()
        elapsed = time() - start
        
        # Should be fast (no sleeping)
        assert elapsed < 0.1
        assert call_count == 2
    
    def test_rate_limit_preserves_function_metadata(self):
        """WHAT: Rate limiter should preserve original function metadata.
        WHY: Important for debugging and introspection.
        """
        @rate_limit(calls_per_hour=10)
        def dummy_func():
            """Test function docstring."""
            pass
        
        assert dummy_func.__name__ == "dummy_func"
        assert "Test function docstring" in dummy_func.__doc__

    @patch("app.services.meta_ads_client.sleep")
    @patch("app.services.meta_ads_client.time")
    def test_rate_limit_shares_budget_for_same_client_token(
        self, mock_time, mock_sleep
    ):
        """WHAT: Different decorated methods should share one budget per client token.
        WHY: Meta rate limits apply across API endpoints for the same client/account.
        """
        from app.services import meta_ads_client as module

        module._rate_limit_call_times.clear()
        mock_time.side_effect = [0.0, 0.0, 0.0, 3602.0]

        class FakeClient:
            access_token = "token-1"

        @rate_limit(calls_per_hour=2)
        def f1(client):
            return "f1"

        @rate_limit(calls_per_hour=2)
        def f2(client):
            return "f2"

        client = FakeClient()
        assert f1(client) == "f1"
        assert f2(client) == "f2"
        assert f1(client) == "f1"  # 3rd call should trigger limiter sleep path

        mock_sleep.assert_called_once()


class TestMetaAdsClientInitialization:
    """Test client initialization."""
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    def test_init_with_token_only(self, mock_api):
        """WHAT: Client should initialize with access token only.
        WHY: System user tokens don't require app credentials.
        """
        client = MetaAdsClient(access_token="test_token")
        
        mock_api.init.assert_called_once_with(
            app_id=None,
            app_secret=None,
            access_token="test_token"
        )
        assert client.access_token == "test_token"
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    def test_init_with_full_credentials(self, mock_api):
        """WHAT: Client should initialize with all credentials.
        WHY: OAuth tokens (Phase 7) will need app credentials.
        """
        client = MetaAdsClient(
            access_token="test_token",
            app_id="123",
            app_secret="secret"
        )
        
        mock_api.init.assert_called_once_with(
            app_id="123",
            app_secret="secret",
            access_token="test_token"
        )


class TestGetCampaigns:
    """Test campaign fetching functionality."""
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    @patch('app.services.meta_ads_client.AdAccount')
    def test_get_campaigns_success(self, mock_account_class, mock_api):
        """WHAT: Should fetch and return all campaigns.
        WHY: Verifies basic campaign fetching works correctly.
        """
        # Setup mocks
        mock_account = Mock()
        mock_account_class.return_value = mock_account
        
        # Mock campaign data
        mock_campaign_1 = {
            'id': '123',
            'name': 'Test Campaign 1',
            'status': 'ACTIVE',
            'objective': 'OUTCOME_SALES'
        }
        mock_campaign_2 = {
            'id': '456',
            'name': 'Test Campaign 2',
            'status': 'PAUSED',
            'objective': 'OUTCOME_TRAFFIC'
        }
        
        mock_account.get_campaigns.return_value = [mock_campaign_1, mock_campaign_2]
        
        # Test
        client = MetaAdsClient(access_token="test_token")
        campaigns = client.get_campaigns("act_123")
        
        # Verify
        assert len(campaigns) == 2
        assert campaigns[0]['id'] == '123'
        assert campaigns[0]['name'] == 'Test Campaign 1'
        assert campaigns[1]['id'] == '456'
        mock_account_class.assert_called_once_with("act_123")
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    @patch('app.services.meta_ads_client.AdAccount')
    def test_get_campaigns_empty_account(self, mock_account_class, mock_api):
        """WHAT: Should handle accounts with no campaigns.
        WHY: New accounts or deleted campaigns result in empty list.
        """
        mock_account = Mock()
        mock_account_class.return_value = mock_account
        mock_account.get_campaigns.return_value = []
        
        client = MetaAdsClient(access_token="test_token")
        campaigns = client.get_campaigns("act_123")
        
        assert campaigns == []
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    @patch('app.services.meta_ads_client.AdAccount')
    def test_get_campaigns_authentication_error(self, mock_account_class, mock_api):
        """WHAT: Should raise MetaAdsAuthenticationError on 401.
        WHY: Token expired or invalid needs specific handling.
        """
        mock_account = Mock()
        mock_account_class.return_value = mock_account
        
        # Mock 401 error
        error = FacebookRequestError(
            message="Invalid token",
            request_context={},
            http_status=401,
            http_headers={},
            body={}
        )
        mock_account.get_campaigns.side_effect = error
        
        client = MetaAdsClient(access_token="test_token")
        
        with pytest.raises(MetaAdsAuthenticationError) as exc_info:
            client.get_campaigns("act_123")
        
        assert "Authentication failed" in str(exc_info.value)
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    @patch('app.services.meta_ads_client.AdAccount')
    def test_get_campaigns_permission_error(self, mock_account_class, mock_api):
        """WHAT: Should raise MetaAdsPermissionError on 403.
        WHY: Insufficient permissions needs specific handling.
        """
        mock_account = Mock()
        mock_account_class.return_value = mock_account
        
        error = FacebookRequestError(
            message="Permission denied",
            request_context={},
            http_status=403,
            http_headers={},
            body={}
        )
        mock_account.get_campaigns.side_effect = error
        
        client = MetaAdsClient(access_token="test_token")
        
        with pytest.raises(MetaAdsPermissionError) as exc_info:
            client.get_campaigns("act_123")
        
        assert "Permission denied" in str(exc_info.value)


class TestGetAdsets:
    """Test adset fetching functionality."""
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    @patch('app.services.meta_ads_client.Campaign')
    def test_get_adsets_success(self, mock_campaign_class, mock_api):
        """WHAT: Should fetch and return all adsets for campaign.
        WHY: Verifies basic adset fetching works correctly.
        """
        mock_campaign = Mock()
        mock_campaign_class.return_value = mock_campaign
        
        mock_adset_1 = {
            'id': '789',
            'name': 'Test AdSet 1',
            'status': 'ACTIVE',
            'campaign_id': '123'
        }
        mock_adset_2 = {
            'id': '790',
            'name': 'Test AdSet 2',
            'status': 'PAUSED',
            'campaign_id': '123'
        }
        
        mock_campaign.get_ad_sets.return_value = [mock_adset_1, mock_adset_2]
        
        client = MetaAdsClient(access_token="test_token")
        adsets = client.get_adsets("123")
        
        assert len(adsets) == 2
        assert adsets[0]['id'] == '789'
        assert adsets[1]['campaign_id'] == '123'
        mock_campaign_class.assert_called_once_with("123")


class TestGetAds:
    """Test ad fetching functionality."""
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    @patch('app.services.meta_ads_client.AdSet')
    def test_get_ads_success(self, mock_adset_class, mock_api):
        """WHAT: Should fetch and return all ads for adset.
        WHY: Verifies basic ad fetching works correctly.
        """
        mock_adset = Mock()
        mock_adset_class.return_value = mock_adset
        
        mock_ad_1 = {
            'id': '111',
            'name': 'Test Ad 1',
            'status': 'ACTIVE',
            'adset_id': '789'
        }
        
        mock_adset.get_ads.return_value = [mock_ad_1]
        
        client = MetaAdsClient(access_token="test_token")
        ads = client.get_ads("789")
        
        assert len(ads) == 1
        assert ads[0]['id'] == '111'
        assert ads[0]['adset_id'] == '789'
        mock_adset_class.assert_called_once_with("789")


class TestGetInsights:
    """Test insights (metrics) fetching functionality."""
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    @patch('app.services.meta_ads_client.Ad')
    def test_get_insights_ad_level_success(self, mock_ad_class, mock_api):
        """WHAT: Should fetch insights for ad with date range.
        WHY: Verifies basic insights fetching works correctly.
        """
        mock_ad = Mock()
        mock_ad_class.return_value = mock_ad
        
        mock_insight = {
            'date_start': '2024-01-01',
            'date_stop': '2024-01-01',
            'spend': '100.50',
            'impressions': '1000',
            'clicks': '50',
            'actions': []
        }
        
        mock_ad.get_insights.return_value = [mock_insight]
        
        client = MetaAdsClient(access_token="test_token")
        insights = client.get_insights(
            entity_id="111",
            start_date="2024-01-01",
            end_date="2024-01-07",
            level="ad"
        )
        
        assert len(insights) == 1
        assert insights[0]['spend'] == '100.50'
        assert insights[0]['impressions'] == '1000'
        mock_ad_class.assert_called_once_with("111")
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    @patch('app.services.meta_ads_client.AdAccount')
    def test_get_insights_account_level(self, mock_account_class, mock_api):
        """WHAT: Should fetch insights at account level.
        WHY: Different entity types need different API objects.
        """
        mock_account = Mock()
        mock_account_class.return_value = mock_account
        mock_account.get_insights.return_value = []
        
        client = MetaAdsClient(access_token="test_token")
        insights = client.get_insights(
            entity_id="act_123",
            start_date="2024-01-01",
            end_date="2024-01-07",
            level="account"
        )
        
        assert insights == []
        mock_account_class.assert_called_once_with("act_123")
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    @patch('app.services.meta_ads_client.Campaign')
    def test_get_insights_campaign_level(self, mock_campaign_class, mock_api):
        """WHAT: Should fetch insights at campaign level.
        WHY: Verifies level parameter routing works correctly.
        """
        mock_campaign = Mock()
        mock_campaign_class.return_value = mock_campaign
        mock_campaign.get_insights.return_value = []
        
        client = MetaAdsClient(access_token="test_token")
        insights = client.get_insights(
            entity_id="123",
            start_date="2024-01-01",
            end_date="2024-01-07",
            level="campaign"
        )
        
        assert insights == []
        mock_campaign_class.assert_called_once_with("123")
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    @patch('app.services.meta_ads_client.Ad')
    def test_get_insights_validation_error(self, mock_ad_class, mock_api):
        """WHAT: Should raise MetaAdsValidationError on 400.
        WHY: Invalid date range or entity ID needs specific handling.
        """
        mock_ad = Mock()
        mock_ad_class.return_value = mock_ad
        
        error = FacebookRequestError(
            message="Invalid date range",
            request_context={},
            http_status=400,
            http_headers={},
            body={}
        )
        mock_ad.get_insights.side_effect = error
        
        client = MetaAdsClient(access_token="test_token")
        
        with pytest.raises(MetaAdsValidationError) as exc_info:
            client.get_insights("111", "2024-01-01", "2024-01-07")
        
        assert "Invalid request" in str(exc_info.value)


class TestExtractTrackingParams:
    """Test UTM tracking parameter extraction from Meta ads.

    WHAT: Tests the _extract_tracking_params helper method
    WHY: Proactive UTM detection enables warnings before orders come in
    REFERENCES: docs/living-docs/FRONTEND_REFACTOR_PLAN.md
    """

    @patch('app.services.meta_ads_client.FacebookAdsApi')
    def test_extract_tracking_params_with_full_utm(self, mock_api):
        """WHAT: Should detect all UTM parameters.
        WHY: Full UTM setup is the ideal attribution configuration.
        """
        client = MetaAdsClient(access_token="test_token")

        ad_dict = {
            "url_tags": "utm_source=facebook&utm_medium=cpc&utm_campaign={{campaign.name}}&utm_content={{ad.name}}"
        }

        result = client._extract_tracking_params(ad_dict)

        assert result is not None
        assert result["has_utm_source"] is True
        assert result["has_utm_medium"] is True
        assert result["has_utm_campaign"] is True
        assert "utm_source" in result["detected_params"]
        assert "utm_medium" in result["detected_params"]
        assert "utm_campaign" in result["detected_params"]
        assert "utm_content" in result["detected_params"]

    @patch('app.services.meta_ads_client.FacebookAdsApi')
    def test_extract_tracking_params_with_partial_utm(self, mock_api):
        """WHAT: Should detect partial UTM setup.
        WHY: Some advertisers only use utm_source and utm_campaign.
        """
        client = MetaAdsClient(access_token="test_token")

        ad_dict = {
            "url_tags": "utm_source=fb&utm_campaign=sale2024"
        }

        result = client._extract_tracking_params(ad_dict)

        assert result is not None
        assert result["has_utm_source"] is True
        assert result["has_utm_medium"] is False
        assert result["has_utm_campaign"] is True
        assert len(result["detected_params"]) == 2

    @patch('app.services.meta_ads_client.FacebookAdsApi')
    def test_extract_tracking_params_with_fbclid(self, mock_api):
        """WHAT: Should detect fbclid parameter.
        WHY: fbclid is Meta's automatic click ID for tracking.
        """
        client = MetaAdsClient(access_token="test_token")

        ad_dict = {
            "url_tags": "fbclid={{ad.id}}"
        }

        result = client._extract_tracking_params(ad_dict)

        assert result is not None
        assert "fbclid" in result["detected_params"]

    @patch('app.services.meta_ads_client.FacebookAdsApi')
    def test_extract_tracking_params_case_insensitive(self, mock_api):
        """WHAT: Should detect UTM params regardless of case.
        WHY: URL parameters can be in any case.
        """
        client = MetaAdsClient(access_token="test_token")

        ad_dict = {
            "url_tags": "UTM_SOURCE=Facebook&UTM_CAMPAIGN=Test"
        }

        result = client._extract_tracking_params(ad_dict)

        assert result is not None
        assert result["has_utm_source"] is True
        assert result["has_utm_campaign"] is True

    @patch('app.services.meta_ads_client.FacebookAdsApi')
    def test_extract_tracking_params_no_url_tags(self, mock_api):
        """WHAT: Should return None when no url_tags.
        WHY: Ads without URL tags have no tracking configured.
        """
        client = MetaAdsClient(access_token="test_token")

        ad_dict = {}

        result = client._extract_tracking_params(ad_dict)

        assert result is None

    @patch('app.services.meta_ads_client.FacebookAdsApi')
    def test_extract_tracking_params_empty_url_tags(self, mock_api):
        """WHAT: Should return None for empty url_tags.
        WHY: Empty string means no tracking configured.
        """
        client = MetaAdsClient(access_token="test_token")

        ad_dict = {"url_tags": ""}

        result = client._extract_tracking_params(ad_dict)

        assert result is None

    @patch('app.services.meta_ads_client.FacebookAdsApi')
    def test_extract_tracking_params_preserves_raw_url_tags(self, mock_api):
        """WHAT: Should include raw url_tags in result.
        WHY: Useful for debugging and displaying to users.
        """
        client = MetaAdsClient(access_token="test_token")

        original_url_tags = "utm_source=facebook&custom_param=test"
        ad_dict = {"url_tags": original_url_tags}

        result = client._extract_tracking_params(ad_dict)

        assert result is not None
        assert result["url_tags"] == original_url_tags


class TestErrorHandling:
    """Test error handling and exception mapping."""

    @patch('app.services.meta_ads_client.FacebookAdsApi')
    @patch('app.services.meta_ads_client.AdAccount')
    def test_rate_limit_error_handling(self, mock_account_class, mock_api):
        """WHAT: Should raise MetaAdsClientError on 429.
        WHY: Rate limit errors need to be caught and logged.
        Note: Should rarely happen due to rate limiting decorator.
        """
        mock_account = Mock()
        mock_account_class.return_value = mock_account
        
        error = FacebookRequestError(
            message="Rate limit exceeded",
            request_context={},
            http_status=429,
            http_headers={},
            body={}
        )
        mock_account.get_campaigns.side_effect = error
        
        client = MetaAdsClient(access_token="test_token")
        
        with pytest.raises(MetaAdsClientError) as exc_info:
            client.get_campaigns("act_123")
        
        assert "Rate limit exceeded" in str(exc_info.value)
    
    @patch('app.services.meta_ads_client.FacebookAdsApi')
    @patch('app.services.meta_ads_client.AdAccount')
    def test_server_error_handling(self, mock_account_class, mock_api):
        """WHAT: Should raise MetaAdsClientError on 500.
        WHY: Server errors need to be caught for retry logic.
        """
        mock_account = Mock()
        mock_account_class.return_value = mock_account
        
        error = FacebookRequestError(
            message="Internal server error",
            request_context={},
            http_status=500,
            http_headers={},
            body={}
        )
        mock_account.get_campaigns.side_effect = error
        
        client = MetaAdsClient(access_token="test_token")
        
        with pytest.raises(MetaAdsClientError) as exc_info:
            client.get_campaigns("act_123")
        
        assert "API error" in str(exc_info.value)
