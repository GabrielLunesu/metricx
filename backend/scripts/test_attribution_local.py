"""Local attribution pipeline smoke test against the real database.

WHAT:
    Tests the AttributionService against your real Postgres database by:
    1. Creating test journeys + touchpoints (simulating pixel events)
    2. Creating test orders (simulating Shopify webhook)
    3. Running attribution through the new service
    4. Printing results for manual verification
    5. Rolling back all test data (no DB changes)

WHY:
    Before deploying the refactored attribution pipeline to production,
    we need to verify it works against the real database schema, not just
    the SQLite test DB.

USAGE:
    cd backend
    python3 scripts/test_attribution_local.py

    Add --keep flag to commit test data to DB for inspection:
    python3 scripts/test_attribution_local.py --keep

REFERENCES:
    - backend/app/services/attribution_service.py
    - backend/app/models.py (CustomerJourney, JourneyTouchpoint, Attribution)
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models import (
    CustomerJourney,
    JourneyTouchpoint,
    ShopifyOrder,
    ShopifyShop,
    Attribution,
)
from app.services.attribution_service import AttributionService

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WORKSPACE_ID = "49335932-3ef0-4d96-b571-1b726c699d1c"
SHOP_DOMAIN = "demo-store.myshopify.com"
TEST_PREFIX = "LOCAL_TEST_"
KEEP_DATA = "--keep" in sys.argv

# Track pass/fail
results = []


def separator(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def run_test(db, test_name, description, order_kwargs,
             journey=True, touchpoint_kwargs=None,
             webhook_utms=None, referring_site=None,
             expect_provider=None, expect_match_type=None, expect_confidence=None):
    """
    Run a single attribution test scenario.

    Parameters:
        db: SQLAlchemy session
        test_name: Short label
        description: What this test verifies
        order_kwargs: Dict of ShopifyOrder fields (utm_*, landing_site, etc.)
        journey: Whether to create a CustomerJourney (True/False)
        touchpoint_kwargs: Dict of JourneyTouchpoint fields
        webhook_utms: Dict of UTMs parsed from webhook landing_site
        referring_site: Referring site URL
        expect_provider: Expected provider result (for auto-check)
        expect_match_type: Expected match_type result
        expect_confidence: Expected confidence level
    """
    print(f"  [{test_name}]")
    print(f"    {description}")

    checkout_token = f"{TEST_PREFIX}{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow()

    # 1. Create journey if requested
    journey_obj = None
    if journey:
        journey_obj = CustomerJourney(
            workspace_id=WORKSPACE_ID,
            visitor_id=f"{TEST_PREFIX}v_{uuid.uuid4().hex[:8]}",
            checkout_token=checkout_token,
            first_seen_at=now - timedelta(hours=2),
            last_seen_at=now - timedelta(minutes=30),
            touchpoint_count=1 if touchpoint_kwargs else 0,
        )
        db.add(journey_obj)
        db.flush()

        # 2. Create touchpoint if specified
        if touchpoint_kwargs:
            touched_at = touchpoint_kwargs.pop("touched_at", now - timedelta(hours=1))
            tp = JourneyTouchpoint(
                journey_id=journey_obj.id,
                event_type=touchpoint_kwargs.pop("event_type", "page_viewed"),
                touched_at=touched_at,
                **touchpoint_kwargs,
            )
            db.add(tp)
            db.flush()

    # 3. Find the real shop
    shop = db.query(ShopifyShop).filter(
        ShopifyShop.shop_domain == SHOP_DOMAIN
    ).first()

    if not shop:
        print(f"    ERROR: Shop {SHOP_DOMAIN} not found!")
        results.append((test_name, "ERROR"))
        return

    # 4. Create test order
    order = ShopifyOrder(
        workspace_id=WORKSPACE_ID,
        shop_id=shop.id,
        external_order_id=f"gid://shopify/Order/{TEST_PREFIX}{uuid.uuid4().hex[:8]}",
        order_number=99999,
        name="#99999",
        total_price=Decimal("149.99"),
        currency="USD",
        financial_status="paid",
        checkout_token=checkout_token,
        order_created_at=now,
        **order_kwargs,
    )
    db.add(order)
    db.flush()

    # 5. Run attribution
    service = AttributionService(db)
    try:
        result = asyncio.run(service.attribute_order(
            workspace_id=WORKSPACE_ID,
            order=order,
            checkout_token=checkout_token,
            customer_email=f"test-{uuid.uuid4().hex[:6]}@example.com",
            webhook_utms=webhook_utms,
            referring_site=referring_site,
        ))

        # Print result
        print(f"    Result: provider={result.provider}, match={result.match_type}, confidence={result.confidence}")
        if result.entity_id:
            print(f"            entity_id={result.entity_id}")

        # Auto-check expectations
        passed = True
        if expect_provider and result.provider != expect_provider:
            print(f"    FAIL: expected provider={expect_provider}, got {result.provider}")
            passed = False
        if expect_match_type and result.match_type != expect_match_type:
            print(f"    FAIL: expected match_type={expect_match_type}, got {result.match_type}")
            passed = False
        if expect_confidence and result.confidence != expect_confidence:
            print(f"    FAIL: expected confidence={expect_confidence}, got {result.confidence}")
            passed = False

        if passed:
            print(f"    PASS")
        results.append((test_name, "PASS" if passed else "FAIL"))

    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback
        traceback.print_exc()
        results.append((test_name, "ERROR"))

    print()


def test_deduplication(db):
    """Test that running attribution twice for the same order produces only one record."""
    print(f"  [Deduplication]")
    print(f"    Same order attributed twice → expect 1 record")

    now = datetime.utcnow()
    checkout_token = f"{TEST_PREFIX}dedup_{uuid.uuid4().hex[:8]}"

    journey = CustomerJourney(
        workspace_id=WORKSPACE_ID,
        visitor_id=f"{TEST_PREFIX}v_dedup_{uuid.uuid4().hex[:6]}",
        checkout_token=checkout_token,
        first_seen_at=now - timedelta(hours=2),
        last_seen_at=now - timedelta(minutes=30),
        touchpoint_count=1,
    )
    db.add(journey)
    db.flush()

    tp = JourneyTouchpoint(
        journey_id=journey.id,
        event_type="page_viewed",
        utm_source="facebook",
        utm_campaign="dedup_test",
        touched_at=now - timedelta(hours=1),
    )
    db.add(tp)
    db.flush()

    shop = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == SHOP_DOMAIN).first()
    order = ShopifyOrder(
        workspace_id=WORKSPACE_ID,
        shop_id=shop.id,
        external_order_id=f"gid://shopify/Order/{TEST_PREFIX}dedup_{uuid.uuid4().hex[:8]}",
        order_number=99998,
        name="#99998",
        total_price=Decimal("75.00"),
        currency="USD",
        financial_status="paid",
        checkout_token=checkout_token,
        order_created_at=now,
    )
    db.add(order)
    db.flush()

    service = AttributionService(db)

    r1 = asyncio.run(service.attribute_order(
        workspace_id=WORKSPACE_ID, order=order,
        checkout_token=checkout_token, customer_email="dedup@example.com",
    ))
    r2 = asyncio.run(service.attribute_order(
        workspace_id=WORKSPACE_ID, order=order,
        checkout_token=checkout_token, customer_email="dedup@example.com",
    ))

    attr_count = db.query(Attribution).filter(
        Attribution.shopify_order_id == order.id,
    ).count()

    print(f"    Call 1: provider={r1.provider}")
    print(f"    Call 2: provider={r2.provider}")
    print(f"    Attribution records: {attr_count}")

    if attr_count == 1:
        print(f"    PASS")
        results.append(("Deduplication", "PASS"))
    else:
        print(f"    FAIL — expected 1, got {attr_count}")
        results.append(("Deduplication", "FAIL"))
    print()


def main():
    separator("Local Attribution Pipeline Test")
    print(f"  Database:  Real Postgres (Railway)")
    print(f"  Workspace: {WORKSPACE_ID}")
    print(f"  Shop:      {SHOP_DOMAIN}")
    print(f"  Mode:      {'KEEP data' if KEEP_DATA else 'ROLLBACK (safe)'}")

    db = SessionLocal()

    try:
        separator("Running Tests")

        # Test 1: UTM campaign (Meta)
        run_test(db,
            test_name="UTM Campaign (Meta)",
            description="Pixel: utm_source=facebook, utm_campaign=summer_sale",
            order_kwargs={
                "landing_site": "/?utm_source=facebook&utm_campaign=summer_sale",
                "utm_source": "facebook", "utm_campaign": "summer_sale",
            },
            touchpoint_kwargs={
                "utm_source": "facebook", "utm_medium": "paid",
                "utm_campaign": "summer_sale",
            },
            expect_provider="meta",
            expect_match_type="utm_campaign",
            expect_confidence="high",
        )

        # Test 2: UTM campaign (Google)
        run_test(db,
            test_name="UTM Campaign (Google)",
            description="Pixel: utm_source=google, utm_campaign=brand_search",
            order_kwargs={
                "landing_site": "/?utm_source=google&utm_campaign=brand_search",
                "utm_source": "google", "utm_campaign": "brand_search",
            },
            touchpoint_kwargs={
                "utm_source": "google", "utm_medium": "cpc",
                "utm_campaign": "brand_search",
            },
            expect_provider="google",
            expect_match_type="utm_campaign",
            expect_confidence="high",
        )

        # Test 3: gclid (Google)
        run_test(db,
            test_name="gclid (Google)",
            description="Pixel: gclid=test_gclid_123",
            order_kwargs={"landing_site": "/?gclid=test_gclid_123"},
            touchpoint_kwargs={"gclid": "test_gclid_123", "utm_source": "google"},
            expect_provider="google",
            expect_match_type="gclid",
        )

        # Test 4: fbclid (Meta)
        run_test(db,
            test_name="fbclid (Meta)",
            description="Pixel: fbclid=fb_test_789",
            order_kwargs={"landing_site": "/?fbclid=fb_test_789"},
            touchpoint_kwargs={"fbclid": "fb_test_789"},
            expect_provider="meta",
            expect_match_type="fbclid",
            expect_confidence="medium",
        )

        # Test 5: Webhook UTM fallback (no pixel)
        run_test(db,
            test_name="Webhook UTM Fallback",
            description="No pixel journey, webhook has UTMs",
            order_kwargs={
                "landing_site": "/?utm_source=google&utm_campaign=brand",
                "utm_source": "google", "utm_campaign": "brand",
            },
            journey=False,
            webhook_utms={"utm_source": "google", "utm_campaign": "brand"},
            expect_provider="google",
            expect_match_type="utm_campaign",
            expect_confidence="medium",
        )

        # Test 6: Direct traffic
        run_test(db,
            test_name="Direct Traffic",
            description="No pixel, no UTMs, no referrer",
            order_kwargs={},
            journey=False,
            expect_provider="direct",
            expect_confidence="none",
        )

        # Test 7: Organic search referrer
        run_test(db,
            test_name="Organic Search",
            description="No UTMs, referring_site=google.com",
            order_kwargs={"referring_site": "https://www.google.com/"},
            journey=False,
            referring_site="https://www.google.com/",
            expect_provider="organic",
            expect_match_type="referrer",
        )

        # Test 8: Attribution window enforcement
        run_test(db,
            test_name="Window Enforcement",
            description="Touchpoint 45 days old → should ignore, fall back",
            order_kwargs={},
            touchpoint_kwargs={
                "utm_source": "facebook", "utm_campaign": "old_campaign",
                "touched_at": datetime.utcnow() - timedelta(days=45),
            },
            expect_provider="direct",
            expect_confidence="none",
        )

        # Test 9: Deduplication
        test_deduplication(db)

        # ---------------------------------------------------------------
        # Summary
        # ---------------------------------------------------------------
        separator("RESULTS")
        total = len(results)
        passed = sum(1 for _, s in results if s == "PASS")
        failed = sum(1 for _, s in results if s == "FAIL")
        errors = sum(1 for _, s in results if s == "ERROR")

        for name, status in results:
            icon = "✓" if status == "PASS" else "✗" if status == "FAIL" else "!"
            print(f"  {icon} {name}: {status}")

        print(f"\n  {passed}/{total} passed, {failed} failed, {errors} errors")

        if KEEP_DATA:
            db.commit()
            print(f"\n  --keep: Test data committed to database.")
        else:
            db.rollback()
            print(f"\n  All test data rolled back. No changes to your database.")

        # Exit code
        if failed > 0 or errors > 0:
            sys.exit(1)

    except Exception as e:
        db.rollback()
        print(f"\nFATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
