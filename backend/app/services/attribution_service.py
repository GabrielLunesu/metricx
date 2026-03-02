"""Attribution Service — core attribution pipeline.

WHAT:
    Determines which marketing campaign/channel drove a Shopify order.
    Extracted from the orders/paid webhook handler into a testable service.

WHY:
    - Isolated, testable attribution logic (no HTTP/webhook coupling)
    - Single source of truth for attribution rules and priority
    - Enables end-to-end testing without Shopify webhook infrastructure

FLOW:
    1. Find customer journey (checkout_token → email → none)
    2. Get last touchpoint within attribution window
    3. Apply priority: gclid > utm_campaign > fbclid > utm_source > referrer > direct
    4. Resolve gclid via Google Ads API if applicable
    5. Store Attribution record (idempotent — one per order per model)
    6. Update journey stats (order count, revenue)
    7. Return result for downstream actions (Meta CAPI, Google Conversions)

REFERENCES:
    - backend/app/routers/shopify_webhooks.py (calls this service)
    - backend/app/services/gclid_resolution_service.py (gclid lookup)
    - backend/app/models.py (Attribution, CustomerJourney, JourneyTouchpoint)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    Attribution,
    CustomerJourney,
    Entity,
    ShopifyOrder,
)

logger = logging.getLogger(__name__)

# Default attribution window in days
DEFAULT_ATTRIBUTION_WINDOW_DAYS = 30


# =============================================================================
# RESULT TYPES
# =============================================================================


@dataclass
class AttributionResult:
    """Result of the attribution pipeline.

    WHAT: Structured output with provider, match details, and metadata
    WHY: Clean interface between attribution logic and downstream consumers
         (webhook response, Meta CAPI, Google Conversions)
    """

    provider: str  # meta, google, tiktok, direct, organic, unknown
    match_type: str  # gclid, utm_campaign, fbclid, utm_source, referrer, none
    confidence: str  # high, medium, low, none
    entity_id: Optional[str] = None  # UUID of matched Entity (campaign/adset/ad)
    journey_id: Optional[str] = None  # UUID of matched CustomerJourney
    attribution_id: Optional[str] = None  # UUID of created Attribution record
    gclid_data: Optional[Dict[str, Any]] = field(default_factory=dict)
    already_existed: bool = False  # True if attribution was already stored


# =============================================================================
# PROVIDER INFERENCE
# =============================================================================


def infer_provider(utm_source: Optional[str]) -> str:
    """Map utm_source to normalized provider name.

    WHAT: Normalize common utm_source values to provider names
    WHY: Consistent reporting across different naming conventions

    Args:
        utm_source: The utm_source parameter value

    Returns:
        Normalized provider name (meta, google, tiktok, etc.)
    """
    if not utm_source:
        return "unknown"

    source_lower = utm_source.lower()

    # Meta/Facebook
    if source_lower in ("facebook", "fb", "meta", "instagram", "ig"):
        return "meta"

    # Google
    if source_lower in ("google", "gads", "google_ads", "adwords"):
        return "google"

    # TikTok
    if source_lower in ("tiktok", "tt", "tiktok_ads"):
        return "tiktok"

    # Email
    if source_lower in ("email", "newsletter", "klaviyo", "mailchimp"):
        return "email"

    # Organic social
    if source_lower in ("organic", "organic_social"):
        return "organic_social"

    return source_lower


def infer_provider_from_referrer(referrer: Optional[str]) -> str:
    """Determine traffic source from referrer URL.

    WHAT: Classify referrer domain into provider category
    WHY: Attribute organic traffic when no UTMs are present

    Args:
        referrer: The referring URL

    Returns:
        Provider name (organic, organic_social, unknown)
    """
    if not referrer:
        return "unknown"

    referrer_lower = referrer.lower()

    search_engines = [
        "google.com", "bing.com", "yahoo.com", "duckduckgo.com",
        "baidu.com", "yandex.com",
    ]
    for engine in search_engines:
        if engine in referrer_lower:
            return "organic"

    social_platforms = [
        "facebook.com", "instagram.com", "twitter.com", "x.com",
        "linkedin.com", "tiktok.com", "pinterest.com", "reddit.com",
    ]
    for platform in social_platforms:
        if platform in referrer_lower:
            return "organic_social"

    return "unknown"


# =============================================================================
# ENTITY LOOKUP
# =============================================================================


def find_entity_by_google_campaign(
    db: Session,
    workspace_id: UUID,
    campaign_id: str,
) -> Optional[str]:
    """Find Entity UUID by Google Ads campaign ID.

    WHAT: Look up campaign Entity by external_id
    WHY: Link gclid attribution to our campaign entity for dashboard display

    Args:
        db: Database session
        workspace_id: Workspace UUID
        campaign_id: Google Ads campaign ID string

    Returns:
        Entity UUID as string, or None if not found
    """
    try:
        entity = db.query(Entity).filter(
            Entity.workspace_id == workspace_id,
            Entity.external_id == campaign_id,
            Entity.level == "campaign",
        ).first()

        if entity:
            return str(entity.id)

        # Fallback: try without level filter
        entity = db.query(Entity).filter(
            Entity.workspace_id == workspace_id,
            Entity.external_id == campaign_id,
        ).first()

        return str(entity.id) if entity else None

    except Exception as e:
        logger.warning(f"[ATTRIBUTION] Entity lookup error: {e}")
        return None


# =============================================================================
# GCLID RESOLUTION
# =============================================================================


async def resolve_gclid(
    gclid: str,
    workspace_id: UUID,
    landed_at: Optional[datetime],
    db: Session,
):
    """Resolve gclid to Google Ads campaign data.

    WHAT: Wrapper for gclid resolution service
    WHY: Provides high-confidence attribution for Google Ads clicks

    Args:
        gclid: Google Click ID
        workspace_id: Workspace UUID
        landed_at: Landing timestamp (determines click date for API query)
        db: Database session

    Returns:
        GclidResolutionResult or None
    """
    try:
        from app.services.gclid_resolution_service import resolve_gclid_for_attribution

        return await resolve_gclid_for_attribution(
            gclid=gclid,
            workspace_id=workspace_id,
            landed_at=landed_at,
            db=db,
        )
    except Exception as e:
        logger.warning(f"[ATTRIBUTION] Gclid resolution error: {e}")
        return None


# =============================================================================
# ATTRIBUTION SERVICE
# =============================================================================


class AttributionService:
    """Core attribution pipeline.

    WHAT: Determines which marketing source drove a Shopify order
    WHY: Central, testable service for the most important business logic

    Usage:
        ```python
        service = AttributionService(db)
        result = await service.attribute_order(
            workspace_id=uuid,
            order=shopify_order,
            checkout_token="tok_abc",
            customer_email="user@example.com",
            webhook_utms={"utm_source": "meta", "utm_campaign": "summer"},
            referring_site="https://facebook.com/...",
        )
        # result.provider == "meta"
        # result.confidence == "high"
        ```
    """

    def __init__(self, db: Session):
        self.db = db

    async def attribute_order(
        self,
        workspace_id: UUID,
        order: ShopifyOrder,
        checkout_token: Optional[str] = None,
        customer_email: Optional[str] = None,
        webhook_utms: Optional[Dict[str, Optional[str]]] = None,
        referring_site: Optional[str] = None,
        attribution_window_days: int = DEFAULT_ATTRIBUTION_WINDOW_DAYS,
    ) -> AttributionResult:
        """Run the full attribution pipeline for an order.

        WHAT: Finds journey, analyzes touchpoints, determines attribution
        WHY: Single entry point for attributing any Shopify order

        Args:
            workspace_id: Workspace UUID
            order: ShopifyOrder model instance (must have id, order_created_at)
            checkout_token: Shopify checkout token (from webhook payload)
            customer_email: Customer email (from webhook payload)
            webhook_utms: UTM params parsed from webhook landing_site
                          Keys: utm_source, utm_medium, utm_campaign, utm_content,
                                utm_term, gclid, fbclid
            referring_site: Referrer URL from webhook payload
            attribution_window_days: Max days between touchpoint and order (default 30)

        Returns:
            AttributionResult with provider, confidence, and stored Attribution ID
        """
        webhook_utms = webhook_utms or {}

        # Step 1: Find customer journey
        journey = self._find_journey(workspace_id, checkout_token, customer_email)

        # Step 2: Determine attribution from journey touchpoints or webhook fallback
        result = await self._determine_attribution(
            workspace_id=workspace_id,
            journey=journey,
            order=order,
            webhook_utms=webhook_utms,
            referring_site=referring_site,
            attribution_window_days=attribution_window_days,
        )

        # Step 3: Store attribution record (idempotent)
        result = self._store_attribution(
            workspace_id=workspace_id,
            order=order,
            journey=journey,
            result=result,
            attribution_window_days=attribution_window_days,
        )

        # Step 4: Update journey stats
        if journey:
            self._update_journey_stats(journey, order, customer_email)

        self.db.commit()

        logger.info(
            f"[ATTRIBUTION] Order attributed",
            extra={
                "order_id": str(order.id),
                "provider": result.provider,
                "match_type": result.match_type,
                "confidence": result.confidence,
                "has_journey": journey is not None,
                "already_existed": result.already_existed,
            },
        )

        return result

    # ─── STEP 1: FIND JOURNEY ────────────────────────────────────────

    def _find_journey(
        self,
        workspace_id: UUID,
        checkout_token: Optional[str],
        customer_email: Optional[str],
    ) -> Optional[CustomerJourney]:
        """Find customer journey by checkout_token or email.

        WHAT: Links an order to the pixel-tracked customer journey
        WHY: Journey contains touchpoints (UTMs, click IDs) for attribution

        Priority:
            1. checkout_token (highest confidence — pixel linked this during checkout)
            2. customer_email (lower confidence — could match wrong journey if
               same email visited from different devices)

        Args:
            workspace_id: Workspace UUID
            checkout_token: Shopify checkout token
            customer_email: Customer email address

        Returns:
            CustomerJourney or None
        """
        # Try checkout_token first (highest confidence link)
        if checkout_token:
            journey = self.db.query(CustomerJourney).filter(
                CustomerJourney.workspace_id == workspace_id,
                CustomerJourney.checkout_token == checkout_token,
            ).first()

            if journey:
                logger.info(
                    f"[ATTRIBUTION] Found journey by checkout_token",
                    extra={"journey_id": str(journey.id), "visitor_id": journey.visitor_id},
                )
                return journey

        # Fallback: try email
        if customer_email:
            journey = self.db.query(CustomerJourney).filter(
                CustomerJourney.workspace_id == workspace_id,
                CustomerJourney.customer_email == customer_email,
            ).first()

            if journey:
                logger.info(
                    f"[ATTRIBUTION] Found journey by email",
                    extra={"journey_id": str(journey.id), "email": customer_email},
                )
                return journey

        logger.debug("[ATTRIBUTION] No journey found for order")
        return None

    # ─── STEP 2: DETERMINE ATTRIBUTION ───────────────────────────────

    async def _determine_attribution(
        self,
        workspace_id: UUID,
        journey: Optional[CustomerJourney],
        order: ShopifyOrder,
        webhook_utms: Dict[str, Optional[str]],
        referring_site: Optional[str],
        attribution_window_days: int,
    ) -> AttributionResult:
        """Determine attribution source from journey touchpoints or webhook data.

        WHAT: Applies attribution priority rules to find the source
        WHY: Different signals have different confidence levels

        Priority (from journey touchpoints):
            gclid → utm_campaign → fbclid → utm_source → referrer

        Fallback (from webhook data, no pixel journey):
            gclid → fbclid → utm_source → referrer → direct

        Args:
            workspace_id: Workspace UUID
            journey: CustomerJourney (may be None)
            order: ShopifyOrder (for date-based window check)
            webhook_utms: UTMs parsed from webhook landing_site
            referring_site: Referrer URL from webhook
            attribution_window_days: Max age of touchpoint in days

        Returns:
            AttributionResult (not yet stored)
        """
        # ── Path A: Journey with touchpoints ──
        if journey and journey.touchpoints:
            result = await self._attribute_from_touchpoints(
                workspace_id=workspace_id,
                journey=journey,
                order=order,
                attribution_window_days=attribution_window_days,
            )
            if result:
                result.journey_id = str(journey.id)
                return result

        # ── Path B: Webhook UTM fallback (no pixel journey) ──
        result = await self._attribute_from_webhook_utms(
            workspace_id=workspace_id,
            order=order,
            webhook_utms=webhook_utms,
            referring_site=referring_site,
        )
        if journey:
            result.journey_id = str(journey.id)
        return result

    async def _attribute_from_touchpoints(
        self,
        workspace_id: UUID,
        journey: CustomerJourney,
        order: ShopifyOrder,
        attribution_window_days: int,
    ) -> Optional[AttributionResult]:
        """Attribute from journey touchpoints (pixel data).

        WHAT: Find the last touchpoint within the attribution window and apply
              priority rules to determine the source.
        WHY: Pixel-tracked touchpoints are the most reliable attribution data.

        Args:
            workspace_id: Workspace UUID
            journey: CustomerJourney with touchpoints loaded
            order: ShopifyOrder (for window calculation)
            attribution_window_days: Max touchpoint age

        Returns:
            AttributionResult or None if no valid touchpoints
        """
        # Filter touchpoints within attribution window
        # NOTE: Postgres returns timezone-aware datetimes; ensure comparison
        # works regardless of whether values are tz-aware or naive.
        order_date = order.order_created_at or datetime.now(timezone.utc)
        window_start = order_date - timedelta(days=attribution_window_days)

        def _within_window(tp_time):
            """Compare touchpoint time to window_start, handling tz mismatch."""
            if tp_time is None:
                return False
            # Make both aware or both naive for comparison
            if tp_time.tzinfo is None and window_start.tzinfo is not None:
                tp_time = tp_time.replace(tzinfo=timezone.utc)
            elif tp_time.tzinfo is not None and window_start.tzinfo is None:
                tp_time = tp_time.replace(tzinfo=None)
            return tp_time >= window_start

        valid_touchpoints = [
            tp for tp in journey.touchpoints
            if _within_window(tp.touched_at)
        ]

        if not valid_touchpoints:
            logger.debug(
                f"[ATTRIBUTION] All {len(journey.touchpoints)} touchpoints outside "
                f"{attribution_window_days}-day window"
            )
            return None

        # Sort: most recent first (last-click model)
        last_touchpoint = sorted(
            valid_touchpoints,
            key=lambda tp: tp.touched_at,
            reverse=True,
        )[0]

        # ── Priority: gclid > utm_campaign > fbclid > utm_source > referrer ──

        if last_touchpoint.gclid:
            return await self._attribute_gclid(
                workspace_id=workspace_id,
                gclid=last_touchpoint.gclid,
                landed_at=last_touchpoint.touched_at,
                entity_id=last_touchpoint.entity_id,
                from_pixel=True,
            )

        if last_touchpoint.utm_campaign:
            provider = infer_provider(last_touchpoint.utm_source)
            return AttributionResult(
                provider=provider,
                match_type="utm_campaign",
                confidence="high",
                entity_id=str(last_touchpoint.entity_id) if last_touchpoint.entity_id else None,
            )

        if last_touchpoint.fbclid:
            return AttributionResult(
                provider="meta",
                match_type="fbclid",
                confidence="medium",
                entity_id=None,
            )

        if last_touchpoint.utm_source:
            provider = infer_provider(last_touchpoint.utm_source)
            return AttributionResult(
                provider=provider,
                match_type="utm_source",
                confidence="low",
                entity_id=None,
            )

        if last_touchpoint.referrer:
            provider = infer_provider_from_referrer(last_touchpoint.referrer)
            return AttributionResult(
                provider=provider,
                match_type="referrer",
                confidence="low",
                entity_id=None,
            )

        return None

    async def _attribute_from_webhook_utms(
        self,
        workspace_id: UUID,
        order: ShopifyOrder,
        webhook_utms: Dict[str, Optional[str]],
        referring_site: Optional[str],
    ) -> AttributionResult:
        """Attribute from webhook UTMs (fallback when no pixel journey).

        WHAT: Use landing_site UTMs from the Shopify webhook payload
        WHY: Ad blockers prevent pixel from firing; webhook UTMs are the fallback

        Args:
            workspace_id: Workspace UUID
            order: ShopifyOrder
            webhook_utms: Parsed UTMs from webhook landing_site
            referring_site: Referrer URL from webhook

        Returns:
            AttributionResult (always returns something — direct traffic as last resort)
        """
        # gclid from webhook
        if webhook_utms.get("gclid"):
            return await self._attribute_gclid(
                workspace_id=workspace_id,
                gclid=webhook_utms["gclid"],
                landed_at=order.order_created_at,
                entity_id=None,
                from_pixel=False,
            )

        # fbclid from webhook
        if webhook_utms.get("fbclid"):
            return AttributionResult(
                provider="meta",
                match_type="fbclid",
                confidence="medium",
                entity_id=None,
            )

        # utm_campaign from webhook (more specific than utm_source alone)
        if webhook_utms.get("utm_campaign") and webhook_utms.get("utm_source"):
            provider = infer_provider(webhook_utms["utm_source"])
            return AttributionResult(
                provider=provider,
                match_type="utm_campaign",
                confidence="medium",
                entity_id=None,
            )

        # utm_source only from webhook
        if webhook_utms.get("utm_source"):
            provider = infer_provider(webhook_utms["utm_source"])
            return AttributionResult(
                provider=provider,
                match_type="utm_source",
                confidence="low",
                entity_id=None,
            )

        # Referrer analysis
        if not referring_site:
            return AttributionResult(
                provider="direct",
                match_type="none",
                confidence="none",
                entity_id=None,
            )

        provider = infer_provider_from_referrer(referring_site)
        if provider == "organic":
            return AttributionResult(
                provider="organic",
                match_type="referrer",
                confidence="low",
                entity_id=None,
            )
        if provider == "organic_social":
            return AttributionResult(
                provider="organic_social",
                match_type="referrer",
                confidence="low",
                entity_id=None,
            )

        return AttributionResult(
            provider="unknown",
            match_type="none",
            confidence="none",
            entity_id=None,
        )

    async def _attribute_gclid(
        self,
        workspace_id: UUID,
        gclid: str,
        landed_at: Optional[datetime],
        entity_id: Optional[Any],
        from_pixel: bool,
    ) -> AttributionResult:
        """Attribute via gclid (Google Click ID).

        WHAT: Resolve gclid to campaign data via Google Ads API
        WHY: Highest-confidence attribution for Google Ads

        Args:
            workspace_id: Workspace UUID
            gclid: Google Click ID
            landed_at: Timestamp of click landing
            entity_id: Pre-resolved entity_id from touchpoint (may be None)
            from_pixel: True if gclid came from pixel (higher confidence)

        Returns:
            AttributionResult with Google attribution data
        """
        gclid_result = await resolve_gclid(
            gclid=gclid,
            workspace_id=workspace_id,
            landed_at=landed_at,
            db=self.db,
        )

        if gclid_result:
            resolved_entity_id = find_entity_by_google_campaign(
                db=self.db,
                workspace_id=workspace_id,
                campaign_id=gclid_result.campaign_id,
            )
            return AttributionResult(
                provider="google",
                match_type="gclid",
                confidence="high",
                entity_id=resolved_entity_id,
                gclid_data={
                    "campaign_id": gclid_result.campaign_id,
                    "campaign_name": gclid_result.campaign_name,
                    "ad_group_id": gclid_result.ad_group_id,
                    "ad_group_name": gclid_result.ad_group_name,
                    "ad_id": gclid_result.ad_id,
                },
            )

        # Gclid resolution failed — still know it's Google
        confidence = "medium" if from_pixel else "medium"
        return AttributionResult(
            provider="google",
            match_type="gclid",
            confidence=confidence,
            entity_id=str(entity_id) if entity_id else None,
        )

    # ─── STEP 3: STORE ATTRIBUTION RECORD ────────────────────────────

    def _store_attribution(
        self,
        workspace_id: UUID,
        order: ShopifyOrder,
        journey: Optional[CustomerJourney],
        result: AttributionResult,
        attribution_window_days: int,
    ) -> AttributionResult:
        """Store Attribution record (idempotent — one per order per model).

        WHAT: Persists the attribution result to the database
        WHY: Enables fast dashboard queries for attributed revenue

        Args:
            workspace_id: Workspace UUID
            order: ShopifyOrder
            journey: CustomerJourney (may be None)
            result: AttributionResult from determination step
            attribution_window_days: Window used (stored for audit)

        Returns:
            Updated AttributionResult with attribution_id set
        """
        # Idempotency check: one attribution per order per model
        existing = self.db.query(Attribution).filter(
            Attribution.shopify_order_id == order.id,
            Attribution.attribution_model == "last_click",
        ).first()

        if existing:
            logger.info(f"[ATTRIBUTION] Attribution already exists for order {order.id}")
            result.attribution_id = str(existing.id)
            result.already_existed = True
            return result

        # Parse entity_id to UUID if it's a string
        entity_uuid = None
        if result.entity_id:
            try:
                entity_uuid = UUID(result.entity_id)
            except (ValueError, TypeError):
                logger.warning(f"[ATTRIBUTION] Invalid entity_id: {result.entity_id}")

        attribution = Attribution(
            workspace_id=workspace_id,
            journey_id=journey.id if journey else None,
            shopify_order_id=order.id,
            entity_id=entity_uuid,
            provider=result.provider,
            match_type=result.match_type,
            confidence=result.confidence,
            attribution_model="last_click",
            attribution_window_days=attribution_window_days,
            attributed_revenue=order.total_price,
            currency=order.currency or "USD",
            order_created_at=order.order_created_at,
        )
        self.db.add(attribution)
        self.db.flush()  # Get ID

        result.attribution_id = str(attribution.id)
        return result

    # ─── STEP 4: UPDATE JOURNEY STATS ────────────────────────────────

    def _update_journey_stats(
        self,
        journey: CustomerJourney,
        order: ShopifyOrder,
        customer_email: Optional[str],
    ) -> None:
        """Update journey with order statistics.

        WHAT: Increment order count and revenue on the journey
        WHY: Journey tracks lifetime value for the visitor

        Args:
            journey: CustomerJourney to update
            order: ShopifyOrder with revenue data
            customer_email: Email to link to journey (if not already set)
        """
        journey.total_orders = (journey.total_orders or 0) + 1
        journey.total_revenue = (
            (journey.total_revenue or Decimal("0")) + (order.total_price or Decimal("0"))
        )

        if not journey.first_order_at:
            journey.first_order_at = order.order_created_at
        journey.last_order_at = order.order_created_at

        # Link email if we have it and journey doesn't yet
        if customer_email and not journey.customer_email:
            journey.customer_email = customer_email
