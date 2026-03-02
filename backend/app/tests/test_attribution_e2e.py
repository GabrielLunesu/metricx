"""End-to-end attribution pipeline tests.

WHAT:
    Tests the full attribution flow: pixel event → journey → order → attribution.
    Covers all attribution priority levels and edge cases.

WHY:
    Attribution accuracy is critical — these tests verify that the correct
    provider, match_type, and confidence are assigned for every scenario.
    This is what makes us compete with Triple Whale.

REFERENCES:
    - backend/app/services/attribution_service.py
    - backend/app/routers/pixel_events.py
    - backend/app/routers/shopify_webhooks.py
"""

import os
import pytest
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

# Set environment variables required by create_app() before importing app modules
os.environ.setdefault("META_APP_ID", "test-meta-app-id")
os.environ.setdefault("META_APP_SECRET", "test-meta-app-secret")
os.environ.setdefault("SHOPIFY_API_KEY", "test-shopify-api-key")
os.environ.setdefault("SHOPIFY_API_SECRET", "test-shopify-api-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-client-secret")
os.environ.setdefault("GOOGLE_DEVELOPER_TOKEN", "test-google-dev-token")
os.environ.setdefault("META_OAUTH_REDIRECT_URI", "http://localhost:3000/api/auth/meta/callback")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from app.models import (
    Workspace,
    Connection,
    ShopifyShop,
    ShopifyOrder,
    PixelEvent,
    CustomerJourney,
    JourneyTouchpoint,
    Attribution,
    Entity,
)
from app.services.attribution_service import (
    AttributionService,
    AttributionResult,
    infer_provider,
    infer_provider_from_referrer,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def workspace(test_db_session):
    """Create a workspace for attribution tests."""
    ws = Workspace(
        name="Attribution Test Store",
        created_at=datetime.utcnow(),
    )
    test_db_session.add(ws)
    test_db_session.commit()
    test_db_session.refresh(ws)
    return ws


@pytest.fixture
def shopify_connection(test_db_session, workspace):
    """Create a Shopify connection (required FK for ShopifyShop)."""
    conn = Connection(
        workspace_id=workspace.id,
        provider="shopify",
        external_account_id="test-store.myshopify.com",
        name="Test Shopify Store",
        status="active",
        connected_at=datetime.utcnow(),
    )
    test_db_session.add(conn)
    test_db_session.commit()
    test_db_session.refresh(conn)
    return conn


@pytest.fixture
def shop(test_db_session, workspace, shopify_connection):
    """Create a Shopify shop."""
    s = ShopifyShop(
        workspace_id=workspace.id,
        connection_id=shopify_connection.id,
        external_shop_id="gid://shopify/Shop/123456",
        shop_domain="test-store.myshopify.com",
        shop_name="Test Store",
    )
    test_db_session.add(s)
    test_db_session.commit()
    test_db_session.refresh(s)
    return s


@pytest.fixture
def attribution_service(test_db_session):
    """Create AttributionService with test DB session."""
    return AttributionService(test_db_session)


def _create_order(db, workspace, shop, total_price="99.99", checkout_token=None):
    """Helper: create a ShopifyOrder."""
    order = ShopifyOrder(
        workspace_id=workspace.id,
        shop_id=shop.id,
        external_order_id=f"gid://shopify/Order/{uuid.uuid4().hex[:8]}",
        order_number=int(uuid.uuid4().int % 100000),
        total_price=Decimal(total_price),
        currency="USD",
        financial_status="paid",
        checkout_token=checkout_token or f"tok_{uuid.uuid4().hex[:12]}",
        order_created_at=datetime.utcnow(),
    )
    db.add(order)
    db.flush()
    return order


def _create_journey(db, workspace, visitor_id=None, checkout_token=None, email=None):
    """Helper: create a CustomerJourney."""
    journey = CustomerJourney(
        workspace_id=workspace.id,
        visitor_id=visitor_id or f"mx_{uuid.uuid4().hex[:12]}",
        checkout_token=checkout_token,
        customer_email=email,
        first_seen_at=datetime.utcnow() - timedelta(hours=2),
        last_seen_at=datetime.utcnow(),
        touchpoint_count=0,
        total_orders=0,
        total_revenue=Decimal("0"),
    )
    db.add(journey)
    db.flush()
    return journey


def _create_touchpoint(
    db,
    journey,
    utm_source=None,
    utm_medium=None,
    utm_campaign=None,
    utm_content=None,
    fbclid=None,
    gclid=None,
    ttclid=None,
    referrer=None,
    touched_at=None,
):
    """Helper: create a JourneyTouchpoint."""
    tp = JourneyTouchpoint(
        journey_id=journey.id,
        event_type="page_viewed",
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
        fbclid=fbclid,
        gclid=gclid,
        ttclid=ttclid,
        referrer=referrer,
        touched_at=touched_at or datetime.utcnow() - timedelta(hours=1),
    )
    db.add(tp)
    db.flush()
    journey.touchpoint_count = (journey.touchpoint_count or 0) + 1
    return tp


# =============================================================================
# TEST: PROVIDER INFERENCE (unit tests for helper functions)
# =============================================================================


class TestInferProvider:
    """Test utm_source → provider mapping."""

    def test_meta_sources(self):
        assert infer_provider("facebook") == "meta"
        assert infer_provider("fb") == "meta"
        assert infer_provider("meta") == "meta"
        assert infer_provider("instagram") == "meta"
        assert infer_provider("ig") == "meta"
        assert infer_provider("Facebook") == "meta"  # case insensitive

    def test_google_sources(self):
        assert infer_provider("google") == "google"
        assert infer_provider("gads") == "google"
        assert infer_provider("google_ads") == "google"
        assert infer_provider("adwords") == "google"

    def test_tiktok_sources(self):
        assert infer_provider("tiktok") == "tiktok"
        assert infer_provider("tt") == "tiktok"
        assert infer_provider("tiktok_ads") == "tiktok"

    def test_email_sources(self):
        assert infer_provider("email") == "email"
        assert infer_provider("klaviyo") == "email"

    def test_unknown_passthrough(self):
        assert infer_provider("pinterest") == "pinterest"
        assert infer_provider(None) == "unknown"
        assert infer_provider("") == "unknown"


class TestInferProviderFromReferrer:
    """Test referrer → provider mapping."""

    def test_organic_search(self):
        assert infer_provider_from_referrer("https://www.google.com/search?q=test") == "organic"
        assert infer_provider_from_referrer("https://bing.com/") == "organic"

    def test_organic_social(self):
        assert infer_provider_from_referrer("https://www.facebook.com/page") == "organic_social"
        assert infer_provider_from_referrer("https://www.instagram.com/user") == "organic_social"
        assert infer_provider_from_referrer("https://www.tiktok.com/@user") == "organic_social"

    def test_unknown(self):
        assert infer_provider_from_referrer("https://random-blog.com/post") == "unknown"
        assert infer_provider_from_referrer(None) == "unknown"
        assert infer_provider_from_referrer("") == "unknown"


# =============================================================================
# TEST: FULL ATTRIBUTION PIPELINE — UTM CAMPAIGN (HIGH CONFIDENCE)
# =============================================================================


class TestAttributionUTMCampaign:
    """Test: pixel event with utm_source=meta, utm_campaign=summer_sale → Attribution."""

    @pytest.mark.asyncio
    async def test_utm_campaign_meta(self, test_db_session, workspace, shop, attribution_service):
        """Full flow: pixel → journey → touchpoint → order → attribution.

        Expected: provider=meta, match_type=utm_campaign, confidence=high
        """
        checkout_token = f"tok_{uuid.uuid4().hex[:12]}"

        # 1. Simulate pixel creating a journey + touchpoint
        journey = _create_journey(
            test_db_session, workspace,
            checkout_token=checkout_token,
        )
        _create_touchpoint(
            test_db_session, journey,
            utm_source="facebook",
            utm_medium="paid",
            utm_campaign="summer_sale_2025",
        )
        test_db_session.commit()

        # 2. Simulate order webhook
        order = _create_order(
            test_db_session, workspace, shop,
            checkout_token=checkout_token,
            total_price="149.99",
        )
        test_db_session.commit()

        # 3. Run attribution
        result = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            checkout_token=checkout_token,
        )

        # 4. Verify
        assert result.provider == "meta"
        assert result.match_type == "utm_campaign"
        assert result.confidence == "high"
        assert result.attribution_id is not None
        assert not result.already_existed

        # Verify DB record
        attr = test_db_session.query(Attribution).filter(
            Attribution.shopify_order_id == order.id,
        ).first()
        assert attr is not None
        assert attr.provider == "meta"
        assert attr.attributed_revenue == Decimal("149.99")

    @pytest.mark.asyncio
    async def test_utm_campaign_google(self, test_db_session, workspace, shop, attribution_service):
        """UTM campaign from Google source."""
        checkout_token = f"tok_{uuid.uuid4().hex[:12]}"

        journey = _create_journey(
            test_db_session, workspace,
            checkout_token=checkout_token,
        )
        _create_touchpoint(
            test_db_session, journey,
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="brand_search_q1",
        )
        test_db_session.commit()

        order = _create_order(test_db_session, workspace, shop, checkout_token=checkout_token)
        test_db_session.commit()

        result = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            checkout_token=checkout_token,
        )

        assert result.provider == "google"
        assert result.match_type == "utm_campaign"
        assert result.confidence == "high"


# =============================================================================
# TEST: GCLID ATTRIBUTION (HIGH CONFIDENCE)
# =============================================================================


class TestAttributionGclid:
    """Test: gclid-based attribution with Google Ads API resolution."""

    @pytest.mark.asyncio
    async def test_gclid_resolved(self, test_db_session, workspace, shop, attribution_service):
        """Gclid resolves successfully → high confidence Google attribution."""
        from app.services.gclid_resolution_service import GclidResolutionResult

        checkout_token = f"tok_{uuid.uuid4().hex[:12]}"

        journey = _create_journey(
            test_db_session, workspace,
            checkout_token=checkout_token,
        )
        _create_touchpoint(
            test_db_session, journey,
            gclid="CjwKCAjw_test_gclid_abc123",
        )
        test_db_session.commit()

        order = _create_order(test_db_session, workspace, shop, checkout_token=checkout_token)
        test_db_session.commit()

        # Mock gclid resolution
        mock_result = GclidResolutionResult(
            campaign_id="12345678",
            campaign_name="Brand Search Q1",
            ad_group_id="87654321",
            ad_group_name="Branded Terms",
        )

        with patch(
            "app.services.attribution_service.resolve_gclid",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await attribution_service.attribute_order(
                workspace_id=workspace.id,
                order=order,
                checkout_token=checkout_token,
            )

        assert result.provider == "google"
        assert result.match_type == "gclid"
        assert result.confidence == "high"
        assert result.gclid_data["campaign_name"] == "Brand Search Q1"

    @pytest.mark.asyncio
    async def test_gclid_unresolved(self, test_db_session, workspace, shop, attribution_service):
        """Gclid resolution fails → medium confidence Google attribution."""
        checkout_token = f"tok_{uuid.uuid4().hex[:12]}"

        journey = _create_journey(
            test_db_session, workspace,
            checkout_token=checkout_token,
        )
        _create_touchpoint(
            test_db_session, journey,
            gclid="CjwKCAjw_test_gclid_unresolvable",
        )
        test_db_session.commit()

        order = _create_order(test_db_session, workspace, shop, checkout_token=checkout_token)
        test_db_session.commit()

        with patch(
            "app.services.attribution_service.resolve_gclid",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await attribution_service.attribute_order(
                workspace_id=workspace.id,
                order=order,
                checkout_token=checkout_token,
            )

        assert result.provider == "google"
        assert result.match_type == "gclid"
        assert result.confidence == "medium"


# =============================================================================
# TEST: FBCLID ATTRIBUTION (MEDIUM CONFIDENCE)
# =============================================================================


class TestAttributionFbclid:
    """Test: fbclid-based attribution."""

    @pytest.mark.asyncio
    async def test_fbclid_only(self, test_db_session, workspace, shop, attribution_service):
        """Fbclid without UTM → medium confidence Meta attribution."""
        checkout_token = f"tok_{uuid.uuid4().hex[:12]}"

        journey = _create_journey(
            test_db_session, workspace,
            checkout_token=checkout_token,
        )
        _create_touchpoint(
            test_db_session, journey,
            fbclid="fb.1.1234567890.abcdef",
        )
        test_db_session.commit()

        order = _create_order(test_db_session, workspace, shop, checkout_token=checkout_token)
        test_db_session.commit()

        result = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            checkout_token=checkout_token,
        )

        assert result.provider == "meta"
        assert result.match_type == "fbclid"
        assert result.confidence == "medium"


# =============================================================================
# TEST: WEBHOOK UTM FALLBACK (NO PIXEL JOURNEY)
# =============================================================================


class TestAttributionWebhookFallback:
    """Test: when pixel data is missing, fall back to webhook UTMs."""

    @pytest.mark.asyncio
    async def test_webhook_utm_source(self, test_db_session, workspace, shop, attribution_service):
        """No pixel journey, webhook has utm_source → low confidence."""
        order = _create_order(test_db_session, workspace, shop)
        test_db_session.commit()

        result = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            webhook_utms={"utm_source": "facebook", "utm_campaign": None},
        )

        assert result.provider == "meta"
        assert result.match_type == "utm_source"
        assert result.confidence == "low"

    @pytest.mark.asyncio
    async def test_webhook_fbclid(self, test_db_session, workspace, shop, attribution_service):
        """No pixel journey, webhook has fbclid."""
        order = _create_order(test_db_session, workspace, shop)
        test_db_session.commit()

        result = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            webhook_utms={"fbclid": "fb.1.test"},
        )

        assert result.provider == "meta"
        assert result.match_type == "fbclid"
        assert result.confidence == "medium"

    @pytest.mark.asyncio
    async def test_webhook_gclid(self, test_db_session, workspace, shop, attribution_service):
        """No pixel journey, webhook has gclid → resolve via API."""
        order = _create_order(test_db_session, workspace, shop)
        test_db_session.commit()

        with patch(
            "app.services.attribution_service.resolve_gclid",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await attribution_service.attribute_order(
                workspace_id=workspace.id,
                order=order,
                webhook_utms={"gclid": "CjwKCAjw_test"},
            )

        assert result.provider == "google"
        assert result.match_type == "gclid"


# =============================================================================
# TEST: DIRECT TRAFFIC (NO ATTRIBUTION DATA)
# =============================================================================


class TestAttributionDirect:
    """Test: no UTMs, no pixel, no referrer → direct traffic."""

    @pytest.mark.asyncio
    async def test_direct_no_data(self, test_db_session, workspace, shop, attribution_service):
        """No attribution data at all → direct."""
        order = _create_order(test_db_session, workspace, shop)
        test_db_session.commit()

        result = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
        )

        assert result.provider == "direct"
        assert result.match_type == "none"
        assert result.confidence == "none"

    @pytest.mark.asyncio
    async def test_organic_search_referrer(self, test_db_session, workspace, shop, attribution_service):
        """Referrer from Google but no UTMs → organic search."""
        order = _create_order(test_db_session, workspace, shop)
        test_db_session.commit()

        result = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            referring_site="https://www.google.com/search?q=my+store",
        )

        assert result.provider == "organic"
        assert result.match_type == "referrer"
        assert result.confidence == "low"


# =============================================================================
# TEST: ATTRIBUTION WINDOW ENFORCEMENT
# =============================================================================


class TestAttributionWindow:
    """Test: touchpoints outside the attribution window are ignored."""

    @pytest.mark.asyncio
    async def test_touchpoint_within_window(self, test_db_session, workspace, shop, attribution_service):
        """Touchpoint 5 days ago (within 30-day window) → attributed."""
        checkout_token = f"tok_{uuid.uuid4().hex[:12]}"

        journey = _create_journey(test_db_session, workspace, checkout_token=checkout_token)
        _create_touchpoint(
            test_db_session, journey,
            utm_source="facebook",
            utm_campaign="recent_campaign",
            touched_at=datetime.utcnow() - timedelta(days=5),
        )
        test_db_session.commit()

        order = _create_order(test_db_session, workspace, shop, checkout_token=checkout_token)
        test_db_session.commit()

        result = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            checkout_token=checkout_token,
        )

        assert result.provider == "meta"
        assert result.confidence == "high"

    @pytest.mark.asyncio
    async def test_touchpoint_outside_window(self, test_db_session, workspace, shop, attribution_service):
        """Touchpoint 45 days ago (outside 30-day window) → falls through to direct."""
        checkout_token = f"tok_{uuid.uuid4().hex[:12]}"

        journey = _create_journey(test_db_session, workspace, checkout_token=checkout_token)
        _create_touchpoint(
            test_db_session, journey,
            utm_source="facebook",
            utm_campaign="old_campaign",
            touched_at=datetime.utcnow() - timedelta(days=45),
        )
        test_db_session.commit()

        order = _create_order(test_db_session, workspace, shop, checkout_token=checkout_token)
        test_db_session.commit()

        result = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            checkout_token=checkout_token,
        )

        # Outside window → falls through to webhook fallback → direct
        assert result.provider == "direct"
        assert result.confidence == "none"

    @pytest.mark.asyncio
    async def test_custom_window(self, test_db_session, workspace, shop, attribution_service):
        """Custom 7-day window: 10-day-old touchpoint is excluded."""
        checkout_token = f"tok_{uuid.uuid4().hex[:12]}"

        journey = _create_journey(test_db_session, workspace, checkout_token=checkout_token)
        _create_touchpoint(
            test_db_session, journey,
            utm_source="facebook",
            utm_campaign="ten_day_old",
            touched_at=datetime.utcnow() - timedelta(days=10),
        )
        test_db_session.commit()

        order = _create_order(test_db_session, workspace, shop, checkout_token=checkout_token)
        test_db_session.commit()

        result = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            checkout_token=checkout_token,
            attribution_window_days=7,  # 7-day window
        )

        assert result.provider == "direct"


# =============================================================================
# TEST: DEDUPLICATION
# =============================================================================


class TestAttributionDeduplication:
    """Test: same order attributed twice → only one record."""

    @pytest.mark.asyncio
    async def test_idempotent_attribution(self, test_db_session, workspace, shop, attribution_service):
        """Running attribution twice on same order creates only one record."""
        checkout_token = f"tok_{uuid.uuid4().hex[:12]}"

        journey = _create_journey(test_db_session, workspace, checkout_token=checkout_token)
        _create_touchpoint(
            test_db_session, journey,
            utm_source="facebook",
            utm_campaign="dedup_test",
        )
        test_db_session.commit()

        order = _create_order(test_db_session, workspace, shop, checkout_token=checkout_token)
        test_db_session.commit()

        # First attribution
        result1 = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            checkout_token=checkout_token,
        )
        assert not result1.already_existed

        # Second attribution (same order)
        result2 = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            checkout_token=checkout_token,
        )
        assert result2.already_existed
        assert result2.attribution_id == result1.attribution_id

        # Verify only one record in DB
        count = test_db_session.query(Attribution).filter(
            Attribution.shopify_order_id == order.id,
        ).count()
        assert count == 1


# =============================================================================
# TEST: JOURNEY FINDING PRIORITY
# =============================================================================


class TestJourneyFinding:
    """Test: checkout_token takes priority over email for journey matching."""

    @pytest.mark.asyncio
    async def test_checkout_token_priority(self, test_db_session, workspace, shop, attribution_service):
        """Checkout token match wins over email match."""
        token = f"tok_{uuid.uuid4().hex[:12]}"
        email = "customer@example.com"

        # Journey 1: matched by checkout_token (Meta campaign)
        journey_token = _create_journey(
            test_db_session, workspace,
            checkout_token=token,
        )
        _create_touchpoint(
            test_db_session, journey_token,
            utm_source="facebook",
            utm_campaign="token_journey_campaign",
        )

        # Journey 2: matched by email (Google campaign)
        journey_email = _create_journey(
            test_db_session, workspace,
            email=email,
        )
        _create_touchpoint(
            test_db_session, journey_email,
            utm_source="google",
            utm_campaign="email_journey_campaign",
        )
        test_db_session.commit()

        order = _create_order(test_db_session, workspace, shop, checkout_token=token)
        test_db_session.commit()

        result = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            checkout_token=token,
            customer_email=email,
        )

        # Should use token journey (Meta), not email journey (Google)
        assert result.provider == "meta"
        assert result.match_type == "utm_campaign"

    @pytest.mark.asyncio
    async def test_email_fallback(self, test_db_session, workspace, shop, attribution_service):
        """No checkout_token match → falls back to email."""
        email = "returning-customer@example.com"

        journey = _create_journey(
            test_db_session, workspace,
            email=email,
        )
        _create_touchpoint(
            test_db_session, journey,
            utm_source="google",
            utm_campaign="email_match_campaign",
        )
        test_db_session.commit()

        order = _create_order(test_db_session, workspace, shop)
        test_db_session.commit()

        result = await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            checkout_token="tok_nonexistent",  # Won't match any journey
            customer_email=email,
        )

        assert result.provider == "google"
        assert result.match_type == "utm_campaign"


# =============================================================================
# TEST: TOUCHPOINT PRIORITY ORDER
# =============================================================================


class TestTouchpointPriority:
    """Test: gclid > utm_campaign > fbclid > utm_source > referrer."""

    @pytest.mark.asyncio
    async def test_gclid_beats_utm(self, test_db_session, workspace, shop, attribution_service):
        """Most recent touchpoint has gclid — wins over older utm_campaign touchpoint."""
        checkout_token = f"tok_{uuid.uuid4().hex[:12]}"

        journey = _create_journey(test_db_session, workspace, checkout_token=checkout_token)

        # Older touchpoint: UTM campaign
        _create_touchpoint(
            test_db_session, journey,
            utm_source="facebook",
            utm_campaign="older_meta_campaign",
            touched_at=datetime.utcnow() - timedelta(hours=2),
        )

        # Newer touchpoint: gclid (this should win — last click)
        _create_touchpoint(
            test_db_session, journey,
            gclid="CjwKCAjw_priority_test",
            touched_at=datetime.utcnow() - timedelta(minutes=30),
        )
        test_db_session.commit()

        order = _create_order(test_db_session, workspace, shop, checkout_token=checkout_token)
        test_db_session.commit()

        with patch(
            "app.services.attribution_service.resolve_gclid",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await attribution_service.attribute_order(
                workspace_id=workspace.id,
                order=order,
                checkout_token=checkout_token,
            )

        # Last click wins → gclid (Google)
        assert result.provider == "google"
        assert result.match_type == "gclid"


# =============================================================================
# TEST: JOURNEY STATS UPDATE
# =============================================================================


class TestJourneyStatsUpdate:
    """Test: attribution updates journey order count and revenue."""

    @pytest.mark.asyncio
    async def test_journey_stats_updated(self, test_db_session, workspace, shop, attribution_service):
        """Journey order count and revenue are incremented."""
        checkout_token = f"tok_{uuid.uuid4().hex[:12]}"
        email = "buyer@example.com"

        journey = _create_journey(test_db_session, workspace, checkout_token=checkout_token)
        _create_touchpoint(
            test_db_session, journey,
            utm_source="facebook",
            utm_campaign="stats_test",
        )
        test_db_session.commit()

        order = _create_order(
            test_db_session, workspace, shop,
            checkout_token=checkout_token,
            total_price="199.99",
        )
        test_db_session.commit()

        await attribution_service.attribute_order(
            workspace_id=workspace.id,
            order=order,
            checkout_token=checkout_token,
            customer_email=email,
        )

        # Refresh journey from DB
        test_db_session.refresh(journey)

        assert journey.total_orders == 1
        assert journey.total_revenue == Decimal("199.99")
        assert journey.customer_email == email
        assert journey.first_order_at is not None
        assert journey.last_order_at is not None


# =============================================================================
# TEST: PIXEL EVENT ENDPOINT (HTTP LEVEL)
# =============================================================================


try:
    import polar_sdk  # noqa: F401
    _HAS_POLAR = True
except ImportError:
    _HAS_POLAR = False


@pytest.mark.skipif(not _HAS_POLAR, reason="polar_sdk not installed (full app deps required)")
class TestPixelEventEndpoint:
    """Test: POST /v1/pixel-events creates PixelEvent and Journey.

    NOTE: These tests require the full FastAPI app with all dependencies.
    They run in CI but may skip locally if polar_sdk is not installed.
    """

    def test_pixel_event_creates_journey(self, client, test_db_session, workspace):
        """Posting a pixel event creates a PixelEvent and CustomerJourney."""
        payload = {
            "workspace_id": str(workspace.id),
            "visitor_id": "mx_test_visitor_123",
            "event_id": "evt_unique_abc",
            "event": "page_viewed",
            "data": {"path": "/products/test-product"},
            "attribution": {
                "utm_source": "meta",
                "utm_medium": "paid",
                "utm_campaign": "summer_sale",
                "fbclid": None,
                "gclid": None,
            },
            "context": {
                "url": "https://test-store.myshopify.com/products/test-product?utm_source=meta&utm_campaign=summer_sale",
                "referrer": "https://www.facebook.com/ads/click",
            },
            "ts": datetime.utcnow().isoformat() + "Z",
        }

        response = client.post("/v1/pixel-events", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["event_id"] is not None
        assert data["journey_id"] is not None

        # Verify PixelEvent in DB
        event = test_db_session.query(PixelEvent).filter(
            PixelEvent.event_id == "evt_unique_abc",
        ).first()
        assert event is not None
        assert event.event_type == "page_viewed"
        assert event.utm_source == "meta"
        assert event.utm_campaign == "summer_sale"

        # Verify Journey in DB
        journey = test_db_session.query(CustomerJourney).filter(
            CustomerJourney.visitor_id == "mx_test_visitor_123",
        ).first()
        assert journey is not None
        assert journey.first_touch_source == "meta"

    def test_pixel_event_deduplication(self, client, test_db_session, workspace):
        """Duplicate event_id returns 'duplicate' status."""
        payload = {
            "workspace_id": str(workspace.id),
            "visitor_id": "mx_dedup_visitor",
            "event_id": "evt_dedup_test",
            "event": "page_viewed",
            "data": {},
            "ts": datetime.utcnow().isoformat() + "Z",
        }

        # First request
        response1 = client.post("/v1/pixel-events", json=payload)
        assert response1.status_code == 200
        assert response1.json()["status"] == "ok"

        # Duplicate request
        response2 = client.post("/v1/pixel-events", json=payload)
        assert response2.status_code == 200
        assert response2.json()["status"] == "duplicate"

    def test_pixel_event_creates_touchpoint(self, client, test_db_session, workspace):
        """Page view with UTMs creates a JourneyTouchpoint."""
        payload = {
            "workspace_id": str(workspace.id),
            "visitor_id": "mx_touchpoint_test",
            "event_id": "evt_tp_test",
            "event": "page_viewed",
            "data": {},
            "attribution": {
                "utm_source": "google",
                "utm_medium": "cpc",
                "utm_campaign": "brand_search",
                "gclid": "CjwKCAjw_test_touchpoint",
            },
            "ts": datetime.utcnow().isoformat() + "Z",
        }

        response = client.post("/v1/pixel-events", json=payload)
        assert response.status_code == 200

        journey_id = response.json()["journey_id"]

        # Verify touchpoint
        touchpoints = test_db_session.query(JourneyTouchpoint).filter(
            JourneyTouchpoint.journey_id == journey_id,
        ).all()
        assert len(touchpoints) == 1
        assert touchpoints[0].utm_source == "google"
        assert touchpoints[0].gclid == "CjwKCAjw_test_touchpoint"

    def test_checkout_completed_links_token(self, client, test_db_session, workspace):
        """Checkout completed event links checkout_token to journey."""
        visitor_id = "mx_checkout_visitor"

        # First: page view (creates journey)
        client.post("/v1/pixel-events", json={
            "workspace_id": str(workspace.id),
            "visitor_id": visitor_id,
            "event_id": "evt_page1",
            "event": "page_viewed",
            "data": {},
            "attribution": {"utm_source": "facebook", "utm_campaign": "test"},
            "ts": datetime.utcnow().isoformat() + "Z",
        })

        # Then: checkout completed (links token)
        client.post("/v1/pixel-events", json={
            "workspace_id": str(workspace.id),
            "visitor_id": visitor_id,
            "event_id": "evt_checkout1",
            "event": "checkout_completed",
            "data": {"checkout_token": "shopify_checkout_abc123", "value": "99.99"},
            "ts": datetime.utcnow().isoformat() + "Z",
        })

        # Verify checkout_token linked to journey
        journey = test_db_session.query(CustomerJourney).filter(
            CustomerJourney.visitor_id == visitor_id,
        ).first()
        assert journey is not None
        assert journey.checkout_token == "shopify_checkout_abc123"
