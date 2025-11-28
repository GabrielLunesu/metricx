"""Shopify mandatory compliance webhooks.

WHAT:
    Implements required GDPR/privacy compliance webhooks for Shopify apps.
    These are mandatory for all apps distributed through the Shopify App Store.

WHY:
    Shopify requires apps to handle customer data requests and deletions
    to comply with GDPR and other privacy regulations.

WEBHOOKS:
    1. customers/data_request - Customer requests their stored data
    2. customers/redact - Store owner requests customer data deletion
    3. shop/redact - Delete all shop data 48h after app uninstall

REFERENCES:
    - https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance
    - https://shopify.dev/docs/apps/build/webhooks/mandatory-webhooks
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
)

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
