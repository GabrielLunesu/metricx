"""Shopify webhooks for compliance and attribution.

WHAT:
    Implements Shopify webhooks for:
    1. GDPR/privacy compliance (mandatory for App Store)
    2. Order events for attribution engine

WHY:
    - Compliance webhooks required for GDPR
    - orders/paid webhook triggers attribution (connects ad spend to revenue)

WEBHOOKS:
    1. customers/data_request - Customer requests their stored data
    2. customers/redact - Store owner requests customer data deletion
    3. shop/redact - Delete all shop data 48h after app uninstall
    4. orders/paid - Order payment confirmed (TRIGGERS ATTRIBUTION)

REFERENCES:
    - https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance
    - https://shopify.dev/docs/apps/build/webhooks/mandatory-webhooks
    - docs/living-docs/ATTRIBUTION_ENGINE.md
"""

import os
import hmac
import hashlib
import base64
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import (
    Connection,
    ProviderEnum,
    ShopifyShop,
    ShopifyCustomer,
    ShopifyOrder,
    ShopifyOrderLineItem,
    ShopifyProduct,
    CustomerJourney,
    Attribution,
)
from decimal import Decimal
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/shopify", tags=["Shopify Webhooks"])

# =============================================================================
# CONFIGURATION
# =============================================================================

SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")


# =============================================================================
# HMAC VERIFICATION
# =============================================================================

def verify_shopify_webhook(request_body: bytes, hmac_header: Optional[str]) -> bool:
    """Verify that webhook request came from Shopify using HMAC.

    WHAT: Validates webhook signature using shared secret
    WHY: Prevent unauthorized webhook calls from malicious actors

    Args:
        request_body: Raw request body bytes
        hmac_header: X-Shopify-Hmac-SHA256 header value

    Returns:
        True if signature is valid, False otherwise
    """
    if not SHOPIFY_API_SECRET:
        logger.error("[SHOPIFY_WEBHOOK] SHOPIFY_API_SECRET not configured")
        return False

    if not hmac_header:
        logger.warning("[SHOPIFY_WEBHOOK] Missing HMAC header")
        return False

    # Calculate expected HMAC
    computed_hmac = base64.b64encode(
        hmac.new(
            SHOPIFY_API_SECRET.encode("utf-8"),
            request_body,
            hashlib.sha256
        ).digest()
    ).decode("utf-8")

    # Constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(computed_hmac, hmac_header)

    if not is_valid:
        logger.warning("[SHOPIFY_WEBHOOK] Invalid HMAC signature")

    return is_valid


async def get_verified_webhook_body(request: Request) -> dict:
    """Dependency that verifies webhook and returns parsed body.

    WHAT: Validates HMAC and parses JSON body
    WHY: Reusable verification for all webhook endpoints

    Raises:
        HTTPException: 401 if HMAC verification fails
    """
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256")

    if not verify_shopify_webhook(body, hmac_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )

    return await request.json()


# =============================================================================
# WEBHOOK PAYLOAD MODELS
# =============================================================================

class CustomerDataRequestPayload(BaseModel):
    """Payload for customers/data_request webhook."""
    shop_id: int
    shop_domain: str
    orders_requested: list[int] = []
    customer: dict
    data_request: dict


class CustomerRedactPayload(BaseModel):
    """Payload for customers/redact webhook."""
    shop_id: int
    shop_domain: str
    customer: dict
    orders_to_redact: list[int] = []


class ShopRedactPayload(BaseModel):
    """Payload for shop/redact webhook."""
    shop_id: int
    shop_domain: str


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@router.post("/customers/data_request")
async def handle_customer_data_request(
    request: Request,
    db: Session = Depends(get_db),
):
    """Handle customer data request webhook.

    WHAT:
        Triggered when a customer requests their stored data (GDPR Article 15).
        We must respond within 30 days with the customer's data.

    WHY:
        Required for GDPR compliance - customers have the right to access their data.

    RESPONSE:
        Return 200 OK to acknowledge receipt. Actual data export should be
        handled asynchronously (email to merchant or dashboard notification).
    """
    # Verify webhook signature
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256")

    if not verify_shopify_webhook(body, hmac_header):
        logger.warning("[SHOPIFY_WEBHOOK] customers/data_request - Invalid signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"[SHOPIFY_WEBHOOK] Failed to parse JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    shop_domain = payload.get("shop_domain", "unknown")
    customer_email = payload.get("customer", {}).get("email", "unknown")
    customer_id = payload.get("customer", {}).get("id")

    logger.info(
        f"[SHOPIFY_WEBHOOK] customers/data_request received for "
        f"shop={shop_domain}, customer_email={customer_email}"
    )

    # Find the shop in our database
    shop = db.query(ShopifyShop).filter(
        ShopifyShop.shop_domain == shop_domain
    ).first()

    if shop and customer_id:
        # Find customer data we have stored
        customer = db.query(ShopifyCustomer).filter(
            ShopifyCustomer.shop_id == shop.id,
            ShopifyCustomer.external_customer_id == f"gid://shopify/Customer/{customer_id}"
        ).first()

        if customer:
            # Log what data we have (in production, you'd email this to merchant)
            logger.info(
                f"[SHOPIFY_WEBHOOK] Customer data found: "
                f"email={customer.email}, "
                f"orders={customer.order_count}, "
                f"total_spent={customer.total_spent}"
            )

            # Find associated orders
            orders = db.query(ShopifyOrder).filter(
                ShopifyOrder.customer_id == customer.id
            ).all()

            logger.info(
                f"[SHOPIFY_WEBHOOK] Found {len(orders)} orders for customer data request"
            )
        else:
            logger.info(
                f"[SHOPIFY_WEBHOOK] No customer data found for customer_id={customer_id}"
            )
    else:
        logger.info(
            f"[SHOPIFY_WEBHOOK] Shop or customer not found in our database"
        )

    # Return 200 to acknowledge receipt
    # NOTE: In production, you should:
    # 1. Queue a job to compile customer data
    # 2. Email the data to the merchant within 30 days
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Data request received and will be processed"}
    )


@router.post("/customers/redact")
async def handle_customer_redact(
    request: Request,
    db: Session = Depends(get_db),
):
    """Handle customer data redaction webhook.

    WHAT:
        Triggered when a store owner requests deletion of customer data
        (GDPR Article 17 - Right to Erasure).

    WHY:
        Required for GDPR compliance - must delete customer data on request.

    ACTIONS:
        - Delete customer record
        - Anonymize order data (remove PII but keep aggregates)
    """
    # Verify webhook signature
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256")

    if not verify_shopify_webhook(body, hmac_header):
        logger.warning("[SHOPIFY_WEBHOOK] customers/redact - Invalid signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"[SHOPIFY_WEBHOOK] Failed to parse JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    shop_domain = payload.get("shop_domain", "unknown")
    customer_email = payload.get("customer", {}).get("email", "unknown")
    customer_id = payload.get("customer", {}).get("id")
    orders_to_redact = payload.get("orders_to_redact", [])

    logger.info(
        f"[SHOPIFY_WEBHOOK] customers/redact received for "
        f"shop={shop_domain}, customer_email={customer_email}, "
        f"orders_to_redact={len(orders_to_redact)}"
    )

    # Find the shop in our database
    shop = db.query(ShopifyShop).filter(
        ShopifyShop.shop_domain == shop_domain
    ).first()

    if shop and customer_id:
        # Find and delete customer
        customer = db.query(ShopifyCustomer).filter(
            ShopifyCustomer.shop_id == shop.id,
            ShopifyCustomer.external_customer_id == f"gid://shopify/Customer/{customer_id}"
        ).first()

        if customer:
            # Anonymize orders (keep for revenue tracking but remove customer link)
            orders = db.query(ShopifyOrder).filter(
                ShopifyOrder.customer_id == customer.id
            ).all()

            for order in orders:
                order.customer_id = None  # Remove customer association
                # Clear any PII in order notes if present
                if order.note:
                    order.note = "[REDACTED]"

            logger.info(
                f"[SHOPIFY_WEBHOOK] Anonymized {len(orders)} orders for customer"
            )

            # Delete the customer record
            db.delete(customer)
            db.commit()

            logger.info(
                f"[SHOPIFY_WEBHOOK] Deleted customer record for customer_id={customer_id}"
            )
        else:
            logger.info(
                f"[SHOPIFY_WEBHOOK] No customer found to redact for customer_id={customer_id}"
            )
    else:
        logger.info(
            f"[SHOPIFY_WEBHOOK] Shop not found or no customer_id provided"
        )

    # Return 200 to acknowledge receipt
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Customer data redaction processed"}
    )


@router.post("/shop/redact")
async def handle_shop_redact(
    request: Request,
    db: Session = Depends(get_db),
):
    """Handle shop data redaction webhook.

    WHAT:
        Triggered 48 hours after a merchant uninstalls the app.
        Must delete ALL data associated with this shop.

    WHY:
        Required for Shopify compliance - when app is uninstalled,
        all shop data must be deleted.

    ACTIONS:
        - Delete all orders and line items
        - Delete all customers
        - Delete all products
        - Delete ShopifyShop record
        - Delete Connection record
    """
    # Verify webhook signature
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256")

    if not verify_shopify_webhook(body, hmac_header):
        logger.warning("[SHOPIFY_WEBHOOK] shop/redact - Invalid signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"[SHOPIFY_WEBHOOK] Failed to parse JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    shop_id = payload.get("shop_id")
    shop_domain = payload.get("shop_domain", "unknown")

    logger.info(
        f"[SHOPIFY_WEBHOOK] shop/redact received for "
        f"shop_id={shop_id}, shop_domain={shop_domain}"
    )

    # Find the shop in our database
    shop = db.query(ShopifyShop).filter(
        ShopifyShop.shop_domain == shop_domain
    ).first()

    if shop:
        workspace_id = shop.workspace_id
        connection_id = shop.connection_id

        # Delete in order (respect foreign key constraints)

        # 1. Delete order line items
        line_items_deleted = db.query(ShopifyOrderLineItem).filter(
            ShopifyOrderLineItem.order_id.in_(
                db.query(ShopifyOrder.id).filter(ShopifyOrder.shop_id == shop.id)
            )
        ).delete(synchronize_session=False)
        logger.info(f"[SHOPIFY_WEBHOOK] Deleted {line_items_deleted} order line items")

        # 2. Delete orders
        orders_deleted = db.query(ShopifyOrder).filter(
            ShopifyOrder.shop_id == shop.id
        ).delete(synchronize_session=False)
        logger.info(f"[SHOPIFY_WEBHOOK] Deleted {orders_deleted} orders")

        # 3. Delete customers
        customers_deleted = db.query(ShopifyCustomer).filter(
            ShopifyCustomer.shop_id == shop.id
        ).delete(synchronize_session=False)
        logger.info(f"[SHOPIFY_WEBHOOK] Deleted {customers_deleted} customers")

        # 4. Delete products
        products_deleted = db.query(ShopifyProduct).filter(
            ShopifyProduct.shop_id == shop.id
        ).delete(synchronize_session=False)
        logger.info(f"[SHOPIFY_WEBHOOK] Deleted {products_deleted} products")

        # 5. Delete ShopifyShop record
        db.delete(shop)
        logger.info(f"[SHOPIFY_WEBHOOK] Deleted ShopifyShop record")

        # 6. Delete Connection record
        connection = db.query(Connection).filter(
            Connection.id == connection_id
        ).first()
        if connection:
            db.delete(connection)
            logger.info(f"[SHOPIFY_WEBHOOK] Deleted Connection record")

        db.commit()

        logger.info(
            f"[SHOPIFY_WEBHOOK] Successfully redacted all data for shop={shop_domain}"
        )
    else:
        logger.info(
            f"[SHOPIFY_WEBHOOK] Shop not found in database, nothing to redact"
        )

    # Return 200 to acknowledge receipt
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Shop data redaction processed"}
    )


# =============================================================================
# ORDER WEBHOOKS (ATTRIBUTION ENGINE)
# =============================================================================

def _parse_utms_from_landing_site(landing_site: Optional[str]) -> dict:
    """Extract UTM parameters from landing site URL.

    WHAT: Parse URL query string to extract UTM params
    WHY: Shopify provides full URL; we need individual params for queries

    Args:
        landing_site: Full URL with query params (e.g., "/?utm_source=meta&utm_campaign=summer")

    Returns:
        Dict with utm_source, utm_medium, utm_campaign, utm_content, utm_term
    """
    if not landing_site:
        return {}

    try:
        parsed = urlparse(landing_site)
        params = parse_qs(parsed.query)
        return {
            "utm_source": params.get("utm_source", [None])[0],
            "utm_medium": params.get("utm_medium", [None])[0],
            "utm_campaign": params.get("utm_campaign", [None])[0],
            "utm_content": params.get("utm_content", [None])[0],
            "utm_term": params.get("utm_term", [None])[0],
            "gclid": params.get("gclid", [None])[0],
            "fbclid": params.get("fbclid", [None])[0],
        }
    except Exception as e:
        logger.warning(f"[SHOPIFY_WEBHOOK] Failed to parse landing_site: {e}")
        return {}


@router.post("/orders/paid")
async def handle_orders_paid(
    request: Request,
    db: Session = Depends(get_db),
):
    """Handle orders/paid webhook - THIS TRIGGERS ATTRIBUTION.

    WHAT:
        Triggered when an order payment is confirmed.
        This is the primary trigger for the attribution engine.

    WHY:
        - Orders/paid means real revenue (not abandoned checkout)
        - Webhook has checkout_token to link with pixel journey
        - Can extract UTMs from landing_site as fallback

    FLOW:
        1. Verify HMAC signature
        2. Find shop by domain
        3. Store/update order with checkout_token
        4. Find journey by checkout_token
        5. Run attribution and store result

    REFERENCES:
        - docs/living-docs/ATTRIBUTION_ENGINE.md
    """
    # Verify webhook signature
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256")
    shop_domain = request.headers.get("X-Shopify-Shop-Domain")

    if not verify_shopify_webhook(body, hmac_header):
        logger.warning("[SHOPIFY_WEBHOOK] orders/paid - Invalid signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"[SHOPIFY_WEBHOOK] Failed to parse JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    # Extract key fields from payload
    shopify_order_id = payload.get("id")
    order_number = payload.get("order_number")
    checkout_token = payload.get("checkout_token")
    total_price = payload.get("total_price", "0")
    currency = payload.get("currency", "USD")
    landing_site = payload.get("landing_site")
    referring_site = payload.get("referring_site")
    customer_email = payload.get("customer", {}).get("email")
    financial_status = payload.get("financial_status")

    logger.info(
        f"[SHOPIFY_WEBHOOK] orders/paid received",
        extra={
            "shop_domain": shop_domain,
            "order_id": shopify_order_id,
            "order_number": order_number,
            "checkout_token": checkout_token,
            "total_price": total_price,
            "landing_site": landing_site,
        }
    )

    # Find shop
    shop = db.query(ShopifyShop).filter(
        ShopifyShop.shop_domain == shop_domain
    ).first()

    if not shop:
        logger.warning(f"[SHOPIFY_WEBHOOK] Shop not found: {shop_domain}")
        # Return 200 to prevent retries for unknown shops
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Shop not found, webhook acknowledged"}
        )

    workspace_id = shop.workspace_id

    # Parse UTMs from landing_site
    utms = _parse_utms_from_landing_site(landing_site)

    # Check if order already exists (idempotency)
    external_order_id = f"gid://shopify/Order/{shopify_order_id}"
    existing_order = db.query(ShopifyOrder).filter(
        ShopifyOrder.shop_id == shop.id,
        ShopifyOrder.external_order_id == external_order_id,
    ).first()

    if existing_order:
        order = existing_order
        # Update checkout_token if not set
        if not order.checkout_token and checkout_token:
            order.checkout_token = checkout_token
        logger.info(f"[SHOPIFY_WEBHOOK] Order already exists, updating")
    else:
        # Create new order
        order = ShopifyOrder(
            workspace_id=workspace_id,
            shop_id=shop.id,
            external_order_id=external_order_id,
            order_number=order_number,
            name=f"#{order_number}" if order_number else None,
            total_price=Decimal(total_price),
            currency=currency,
            financial_status=financial_status,
            landing_site=landing_site,
            referring_site=referring_site,
            checkout_token=checkout_token,
            utm_source=utms.get("utm_source"),
            utm_medium=utms.get("utm_medium"),
            utm_campaign=utms.get("utm_campaign"),
            utm_content=utms.get("utm_content"),
            utm_term=utms.get("utm_term"),
            order_created_at=datetime.fromisoformat(
                payload.get("created_at", "").replace("Z", "+00:00")
            ) if payload.get("created_at") else datetime.utcnow(),
        )
        db.add(order)
        db.flush()  # Get order.id for attribution

        logger.info(
            f"[SHOPIFY_WEBHOOK] Created order {order.id}",
            extra={"external_order_id": external_order_id}
        )

    # =================================================================
    # ATTRIBUTION: Find journey and attribute the order
    # =================================================================

    journey = None
    attribution_result = {
        "provider": "unknown",
        "match_type": "none",
        "confidence": "none",
        "entity_id": None,
    }

    # 1. Try to find journey by checkout_token (highest confidence)
    if checkout_token:
        journey = db.query(CustomerJourney).filter(
            CustomerJourney.workspace_id == workspace_id,
            CustomerJourney.checkout_token == checkout_token,
        ).first()

        if journey:
            logger.info(
                f"[ATTRIBUTION] Found journey by checkout_token",
                extra={
                    "journey_id": str(journey.id),
                    "visitor_id": journey.visitor_id,
                }
            )

    # 2. Fallback: Try to find journey by customer email
    if not journey and customer_email:
        journey = db.query(CustomerJourney).filter(
            CustomerJourney.workspace_id == workspace_id,
            CustomerJourney.customer_email == customer_email,
        ).first()

        if journey:
            logger.info(
                f"[ATTRIBUTION] Found journey by email",
                extra={"journey_id": str(journey.id), "email": customer_email}
            )

    # 3. Determine attribution from journey or webhook data
    if journey and journey.touchpoints:
        # Use last touchpoint for last-click attribution
        last_touchpoint = sorted(
            journey.touchpoints,
            key=lambda tp: tp.touched_at,
            reverse=True
        )[0]

        # Attribution priority: gclid > utm_campaign > fbclid > utm_source > referrer
        if last_touchpoint.gclid:
            attribution_result = {
                "provider": "google",
                "match_type": "gclid",
                "confidence": "high",
                "entity_id": last_touchpoint.entity_id,
            }
        elif last_touchpoint.utm_campaign:
            # Infer provider from utm_source
            provider = _infer_provider(last_touchpoint.utm_source)
            attribution_result = {
                "provider": provider,
                "match_type": "utm_campaign",
                "confidence": "high",
                "entity_id": last_touchpoint.entity_id,
            }
        elif last_touchpoint.fbclid:
            attribution_result = {
                "provider": "meta",
                "match_type": "fbclid",
                "confidence": "medium",
                "entity_id": None,
            }
        elif last_touchpoint.utm_source:
            provider = _infer_provider(last_touchpoint.utm_source)
            attribution_result = {
                "provider": provider,
                "match_type": "utm_source",
                "confidence": "low",
                "entity_id": None,
            }
        elif last_touchpoint.referrer:
            provider = _infer_provider_from_referrer(last_touchpoint.referrer)
            attribution_result = {
                "provider": provider,
                "match_type": "referrer",
                "confidence": "low",
                "entity_id": None,
            }
    elif utms.get("gclid"):
        # Fallback to webhook UTMs if no journey
        attribution_result = {
            "provider": "google",
            "match_type": "gclid",
            "confidence": "medium",  # Lower confidence without pixel journey
            "entity_id": None,
        }
    elif utms.get("fbclid"):
        attribution_result = {
            "provider": "meta",
            "match_type": "fbclid",
            "confidence": "medium",
            "entity_id": None,
        }
    elif utms.get("utm_source"):
        provider = _infer_provider(utms.get("utm_source"))
        attribution_result = {
            "provider": provider,
            "match_type": "utm_source",
            "confidence": "low",
            "entity_id": None,
        }
    elif not referring_site:
        # No referrer, no UTMs = direct traffic
        attribution_result = {
            "provider": "direct",
            "match_type": "none",
            "confidence": "none",
            "entity_id": None,
        }
    else:
        # Has referrer but no UTMs - check if organic search
        provider = _infer_provider_from_referrer(referring_site)
        if provider == "organic":
            attribution_result = {
                "provider": "organic",
                "match_type": "referrer",
                "confidence": "low",
                "entity_id": None,
            }

    # 4. Store attribution record (idempotent - one per order per model)
    existing_attribution = db.query(Attribution).filter(
        Attribution.shopify_order_id == order.id,
        Attribution.attribution_model == "last_click",
    ).first()

    if existing_attribution:
        logger.info(f"[ATTRIBUTION] Attribution already exists for order")
    else:
        attribution = Attribution(
            workspace_id=workspace_id,
            journey_id=journey.id if journey else None,
            shopify_order_id=order.id,
            entity_id=attribution_result["entity_id"],
            provider=attribution_result["provider"],
            match_type=attribution_result["match_type"],
            confidence=attribution_result["confidence"],
            attribution_model="last_click",
            attribution_window_days=30,
            attributed_revenue=Decimal(total_price),
            currency=currency,
            order_created_at=order.order_created_at,
        )
        db.add(attribution)

        logger.info(
            f"[ATTRIBUTION] Created attribution",
            extra={
                "order_id": str(order.id),
                "provider": attribution_result["provider"],
                "match_type": attribution_result["match_type"],
                "confidence": attribution_result["confidence"],
                "revenue": total_price,
            }
        )

    # 5. Update journey stats if found
    if journey:
        journey.total_orders = (journey.total_orders or 0) + 1
        journey.total_revenue = (journey.total_revenue or Decimal("0")) + Decimal(total_price)
        if not journey.first_order_at:
            journey.first_order_at = order.order_created_at
        journey.last_order_at = order.order_created_at

        # Link email if we have it
        if customer_email and not journey.customer_email:
            journey.customer_email = customer_email

    db.commit()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Order processed and attributed",
            "order_id": str(order.id),
            "attribution": attribution_result,
        }
    )


def _infer_provider(utm_source: Optional[str]) -> str:
    """Infer ad provider from utm_source.

    WHAT: Map common utm_source values to provider names
    WHY: Normalize source names for consistent reporting

    Args:
        utm_source: The utm_source parameter value

    Returns:
        Provider name (meta, google, tiktok, etc.) or the source itself
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

    # Organic social (not paid)
    if source_lower in ("organic", "organic_social"):
        return "organic_social"

    return source_lower


def _infer_provider_from_referrer(referrer: Optional[str]) -> str:
    """Infer provider from referrer URL.

    WHAT: Determine traffic source from referrer domain
    WHY: Classify organic search vs social vs other

    Args:
        referrer: The referring URL

    Returns:
        Provider name or "unknown"
    """
    if not referrer:
        return "unknown"

    referrer_lower = referrer.lower()

    # Search engines (organic)
    search_engines = [
        "google.com", "bing.com", "yahoo.com", "duckduckgo.com",
        "baidu.com", "yandex.com"
    ]
    for engine in search_engines:
        if engine in referrer_lower:
            return "organic"

    # Social platforms (organic social)
    social_platforms = [
        "facebook.com", "instagram.com", "twitter.com", "x.com",
        "linkedin.com", "tiktok.com", "pinterest.com", "reddit.com"
    ]
    for platform in social_platforms:
        if platform in referrer_lower:
            return "organic_social"

    return "unknown"
