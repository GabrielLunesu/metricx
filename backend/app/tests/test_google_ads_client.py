"""Unit tests for Google Ads client service.

WHAT:
    Validate GAQL helpers, mapping, and basic parsing without real SDK/network.

WHY:
    Ensure separation and single responsibility with testable behavior.

REFERENCES:
    app/services/google_ads_client.py
    docs/living-docs/GOOGLE_INTEGRATION_STATUS.MD
"""

from datetime import date

import types

from app.models import GoalEnum
from app.services.google_ads_client import GAdsClient, map_channel_to_goal


class _FakeService:
    def __init__(self, responses):
        self._responses = responses

    def search(self, customer_id, query, page_size=10000):  # noqa: ARG002
        # Return the pre-seeded response iterator
        return iter(self._responses.get(query, []))

    def search_stream(self, customer_id, query):  # noqa: ARG002
        # Return batches with `.results` to simulate streaming
        batch = types.SimpleNamespace(results=self._responses.get(query, []))
        return [batch]


class _FakeClient:
    def __init__(self, service):
        self._service = service

    def get_service(self, name):  # noqa: ARG002
        return self._service


def _mk_row(ns_dict):
    # Build a nested SimpleNamespace mock similar to SDK rows
    return types.SimpleNamespace(**ns_dict)


def test_map_channel_to_goal():
    assert map_channel_to_goal("SEARCH") == GoalEnum.conversions
    assert map_channel_to_goal("DISPLAY") == GoalEnum.awareness
    assert map_channel_to_goal("PERFORMANCE_MAX") == GoalEnum.purchases
    assert map_channel_to_goal("APP") == GoalEnum.app_installs
    assert map_channel_to_goal("UNKNOWN") == GoalEnum.other
    assert map_channel_to_goal(None) == GoalEnum.other


def test_list_campaigns_parses_fields():
    q = (
        "SELECT campaign.id, campaign.name, campaign.status, "
        "campaign.serving_status, campaign.primary_status, "
        "campaign.primary_status_reasons, campaign.advertising_channel_type "
        "FROM campaign ORDER BY campaign.name"
    )
    fake_row = _mk_row({
        "campaign": types.SimpleNamespace(
            id="123",
            name="Test Campaign",
            status="ENABLED",
            serving_status="SERVING",
            primary_status="ELIGIBLE",
            primary_status_reasons=["POLICY_APPROVED"],
            advertising_channel_type="SEARCH",
        )
    })
    fake_service = _FakeService({q: [fake_row]})
    client = GAdsClient(client=_FakeClient(fake_service))
    rows = client.list_campaigns("1111111111")
    assert rows and rows[0]["id"] == "123"
    assert rows[0]["primary_status"] == "ELIGIBLE"
    assert rows[0]["advertising_channel_type"] == "SEARCH"


def test_get_customer_metadata_returns_timezone_currency():
    q = "SELECT customer.time_zone, customer.currency_code FROM customer LIMIT 1"
    fake_row = _mk_row({
        "customer": types.SimpleNamespace(time_zone="Europe/Vienna", currency_code="USD")
    })
    client = GAdsClient(client=_FakeClient(_FakeService({q: [fake_row]})))
    meta = client.get_customer_metadata("2222222222")
    assert meta["time_zone"] == "Europe/Vienna"
    assert meta["currency_code"] == "USD"


def test_fetch_daily_metrics_normalizes_spend_and_fields():
    start = date(2024, 10, 1)
    end = date(2024, 10, 2)
    q = (
        f"SELECT campaign.id, campaign.name, "
        "metrics.impressions, metrics.clicks, metrics.cost_micros, "
        "metrics.conversions, metrics.conversions_value, segments.date "
        f"FROM campaign WHERE segments.date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}'"
    )
    fake_row = _mk_row({
        "metrics": types.SimpleNamespace(
            impressions=100,
            clicks=10,
            cost_micros=1234567,
            conversions=2.0,
            conversions_value=50.0,
        ),
        "segments": types.SimpleNamespace(date=start),
    })
    client = GAdsClient(client=_FakeClient(_FakeService({q: [fake_row]})))
    data = client.fetch_daily_metrics("3333333333", start, end, level="campaign")
    assert data and data[0]["spend"] == 1.234567
    assert data[0]["clicks"] == 10
    assert data[0]["revenue"] == 50.0
    assert "resource_id" in data[0]


# =============================================================================
# UTM Tracking Parameter Extraction Tests
# =============================================================================


class TestExtractGoogleTrackingParams:
    """Test UTM tracking parameter extraction from Google Ads.

    WHAT: Tests the _extract_google_tracking_params helper method
    WHY: Proactive UTM detection enables warnings before orders come in
    REFERENCES: docs/living-docs/FRONTEND_REFACTOR_PLAN.md
    """

    def test_extract_tracking_params_with_full_utm(self):
        """WHAT: Should detect all UTM parameters in tracking template.
        WHY: Full UTM setup is the ideal attribution configuration.
        """
        fake_service = _FakeService({})
        client = GAdsClient(client=_FakeClient(fake_service))

        result = client._extract_google_tracking_params(
            tracking_url_template="https://example.com/?utm_source=google&utm_medium=cpc&utm_campaign={campaignid}",
            final_url_suffix=None
        )

        assert result is not None
        assert result["has_utm_source"] is True
        assert result["has_utm_medium"] is True
        assert result["has_utm_campaign"] is True
        assert "utm_source" in result["detected_params"]
        assert "utm_medium" in result["detected_params"]
        assert "utm_campaign" in result["detected_params"]

    def test_extract_tracking_params_from_final_url_suffix(self):
        """WHAT: Should detect UTM params in final_url_suffix.
        WHY: Google Ads allows UTM params in either location.
        """
        fake_service = _FakeService({})
        client = GAdsClient(client=_FakeClient(fake_service))

        result = client._extract_google_tracking_params(
            tracking_url_template=None,
            final_url_suffix="utm_source=google&utm_campaign=test"
        )

        assert result is not None
        assert result["has_utm_source"] is True
        assert result["has_utm_campaign"] is True
        assert result["tracking_url_template"] is None
        assert result["final_url_suffix"] == "utm_source=google&utm_campaign=test"

    def test_extract_tracking_params_with_gclid(self):
        """WHAT: Should detect gclid (Google Click ID) auto-tagging.
        WHY: gclid enables Google's automatic conversion tracking.
        """
        fake_service = _FakeService({})
        client = GAdsClient(client=_FakeClient(fake_service))

        result = client._extract_google_tracking_params(
            tracking_url_template="https://track.com/?gclid={gclid}",
            final_url_suffix=None
        )

        assert result is not None
        assert result["has_gclid"] is True

    def test_extract_tracking_params_combined_sources(self):
        """WHAT: Should check both template and suffix.
        WHY: UTM params can be split across both fields.
        """
        fake_service = _FakeService({})
        client = GAdsClient(client=_FakeClient(fake_service))

        result = client._extract_google_tracking_params(
            tracking_url_template="https://track.com/?utm_source=google",
            final_url_suffix="utm_campaign={campaignid}"
        )

        assert result is not None
        assert result["has_utm_source"] is True
        assert result["has_utm_campaign"] is True

    def test_extract_tracking_params_case_insensitive(self):
        """WHAT: Should detect UTM params regardless of case.
        WHY: URL parameters can be in any case.
        """
        fake_service = _FakeService({})
        client = GAdsClient(client=_FakeClient(fake_service))

        result = client._extract_google_tracking_params(
            tracking_url_template="https://track.com/?UTM_SOURCE=Google&UTM_CAMPAIGN=Test",
            final_url_suffix=None
        )

        assert result is not None
        assert result["has_utm_source"] is True
        assert result["has_utm_campaign"] is True

    def test_extract_tracking_params_no_tracking(self):
        """WHAT: Should return None when no tracking configured.
        WHY: Ads without tracking have no URL parameters.
        """
        fake_service = _FakeService({})
        client = GAdsClient(client=_FakeClient(fake_service))

        result = client._extract_google_tracking_params(
            tracking_url_template=None,
            final_url_suffix=None
        )

        assert result is None

    def test_extract_tracking_params_preserves_raw_values(self):
        """WHAT: Should include raw tracking fields in result.
        WHY: Useful for debugging and displaying to users.
        """
        fake_service = _FakeService({})
        client = GAdsClient(client=_FakeClient(fake_service))

        template = "https://track.com/?utm_source=google"
        suffix = "utm_campaign=test"

        result = client._extract_google_tracking_params(
            tracking_url_template=template,
            final_url_suffix=suffix
        )

        assert result is not None
        assert result["tracking_url_template"] == template
        assert result["final_url_suffix"] == suffix
