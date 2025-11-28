"""Shopify sync service functions.

WHAT:
    Provides reusable functions for syncing Shopify data:
    - Products (catalog with COGS)
    - Customers (for LTV calculations)
    - Orders (revenue and profit tracking)

WHY:
    - Enables both HTTP endpoints and background workers to share the same logic.
    - Keeps routers thin (auth, request parsing) while services handle business logic.
    - Matches the pattern established by meta_sync_service.py

REFERENCES:
    - docs/living-docs/REALTIME_SYNC_IMPLEMENTATION_SUMMARY.md
    - backend/app/services/meta_sync_service.py (similar pattern)
    - backend/app/services/shopify_client.py (API client)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import (
    Connection,
    ProviderEnum,
    ShopifyShop,
    ShopifyProduct,
    ShopifyCustomer,
    ShopifyOrder,
    ShopifyOrderLineItem,
    ShopifyFinancialStatusEnum,
    ShopifyFulfillmentStatusEnum,
)
from app.security import decrypt_secret
from app.services.shopify_client import ShopifyClient, ShopifyAPIError

logger = logging.getLogger(__name__)


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================
# WHAT: Dataclasses for sync response formatting
# WHY: Consistent response structure across all sync operations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ShopifySyncStats:
    """Statistics from a Shopify sync operation."""
    products_created: int = 0
    products_updated: int = 0
    products_with_cost: int = 0
    products_missing_cost: int = 0
    customers_created: int = 0
    customers_updated: int = 0
    orders_created: int = 0
    orders_updated: int = 0
    line_items_created: int = 0
    total_revenue: Decimal = field(default_factory=lambda: Decimal("0"))
    total_profit: Decimal = field(default_factory=lambda: Decimal("0"))
    orders_missing_cost: int = 0
    duration_seconds: float = 0.0


@dataclass
class ShopifySyncResponse:
    """Response from a Shopify sync operation."""
    success: bool
    stats: ShopifySyncStats
    errors: List[str] = field(default_factory=list)
    message: str = ""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_access_token(connection: Connection) -> str:
    """Get decrypted access token from connection.

    WHAT: Decrypt token from connection's Token record
    WHY: Tokens are stored encrypted; need plaintext for API calls
    """
    if not connection.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection has no associated token. Please reconnect.",
        )

    if not connection.token.access_token_enc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection token is empty. Please reconnect.",
        )

    label = f"{connection.provider.value}:{connection.external_account_id}"
    return decrypt_secret(connection.token.access_token_enc, context=f"{label}:access")


def _get_shop_for_connection(db: Session, connection: Connection) -> ShopifyShop:
    """Get ShopifyShop record for a connection.

    WHAT: Fetch shop record linked to this connection
    WHY: Need shop_id for all Shopify data operations
    """
    shop = db.query(ShopifyShop).filter(
        ShopifyShop.connection_id == connection.id
    ).first()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Shopify shop found for this connection. Please reconnect.",
        )

    return shop


def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string to datetime object.

    WHAT: Convert Shopify datetime strings to Python datetime
    WHY: Shopify returns ISO format strings; need datetime for DB
    """
    if not dt_str:
        return None
    try:
        # Handle various ISO formats
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None


def _map_financial_status(status_str: Optional[str]) -> Optional[ShopifyFinancialStatusEnum]:
    """Map Shopify financial status string to enum.

    WHAT: Convert status string to enum value
    WHY: Database uses enum for type safety
    """
    if not status_str:
        return None

    status_map = {
        "pending": ShopifyFinancialStatusEnum.pending,
        "authorized": ShopifyFinancialStatusEnum.authorized,
        "partially_paid": ShopifyFinancialStatusEnum.partially_paid,
        "paid": ShopifyFinancialStatusEnum.paid,
        "partially_refunded": ShopifyFinancialStatusEnum.partially_refunded,
        "refunded": ShopifyFinancialStatusEnum.refunded,
        "voided": ShopifyFinancialStatusEnum.voided,
    }
    return status_map.get(status_str.lower())


def _map_fulfillment_status(status_str: Optional[str]) -> Optional[ShopifyFulfillmentStatusEnum]:
    """Map Shopify fulfillment status string to enum.

    WHAT: Convert status string to enum value
    WHY: Database uses enum for type safety
    """
    if not status_str:
        return None

    status_map = {
        "unfulfilled": ShopifyFulfillmentStatusEnum.unfulfilled,
        "partial": ShopifyFulfillmentStatusEnum.partial,
        "fulfilled": ShopifyFulfillmentStatusEnum.fulfilled,
        "restocked": ShopifyFulfillmentStatusEnum.restocked,
        "pending_fulfillment": ShopifyFulfillmentStatusEnum.pending_fulfillment,
        "open": ShopifyFulfillmentStatusEnum.open,
        "in_progress": ShopifyFulfillmentStatusEnum.in_progress,
        "on_hold": ShopifyFulfillmentStatusEnum.on_hold,
        "scheduled": ShopifyFulfillmentStatusEnum.scheduled,
    }
    return status_map.get(status_str.lower())


# =============================================================================
# SYNC FUNCTIONS
# =============================================================================

async def sync_shopify_products(
    db: Session,
    workspace_id: UUID,
    connection_id: UUID,
) -> ShopifySyncResponse:
    """Sync products from Shopify to database.

    WHAT: Fetch all products and upsert into shopify_products table
    WHY: Need product catalog for:
        - Line item lookups during order sync
        - COGS (cost) for profit calculations
        - Product-level reporting

    Args:
        db: Database session
        workspace_id: Workspace UUID
        connection_id: Connection UUID

    Returns:
        ShopifySyncResponse with sync statistics
    """
    start_time = datetime.utcnow()
    stats = ShopifySyncStats()
    errors: List[str] = []

    logger.info(
        "[SHOPIFY_SYNC] Starting product sync: workspace=%s, connection=%s",
        workspace_id, connection_id
    )

    try:
        # Validate connection
        connection = db.query(Connection).filter(
            Connection.id == connection_id,
            Connection.workspace_id == workspace_id,
        ).first()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found or does not belong to workspace",
            )

        if connection.provider != ProviderEnum.shopify:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection is not a Shopify connection (provider={connection.provider})",
            )

        shop = _get_shop_for_connection(db, connection)
        access_token = _get_access_token(connection)

        # Initialize client and fetch products
        client = ShopifyClient(
            shop_domain=shop.shop_domain,
            access_token=access_token,
        )

        products = await client.get_all_products()
        logger.info(f"[SHOPIFY_SYNC] Fetched {len(products)} products from Shopify")

        # Upsert products
        for product_data in products:
            try:
                external_id = product_data["external_product_id"]

                # Check if product exists
                existing = db.query(ShopifyProduct).filter(
                    ShopifyProduct.shop_id == shop.id,
                    ShopifyProduct.external_product_id == external_id,
                ).first()

                if existing:
                    # Update existing product
                    existing.title = product_data["title"]
                    existing.handle = product_data.get("handle")
                    existing.status = product_data.get("status", "active")
                    existing.vendor = product_data.get("vendor")
                    existing.product_type = product_data.get("product_type")
                    existing.price = product_data.get("price")
                    existing.compare_at_price = product_data.get("compare_at_price")
                    existing.cost_per_item = product_data.get("cost_per_item")
                    existing.cost_source = product_data.get("cost_source")
                    existing.total_inventory = product_data.get("total_inventory")
                    existing.shopify_updated_at = _parse_datetime(product_data.get("shopify_updated_at"))
                    existing.updated_at = datetime.utcnow()
                    stats.products_updated += 1
                else:
                    # Create new product
                    new_product = ShopifyProduct(
                        workspace_id=workspace_id,
                        shop_id=shop.id,
                        external_product_id=external_id,
                        title=product_data["title"],
                        handle=product_data.get("handle"),
                        status=product_data.get("status", "active"),
                        vendor=product_data.get("vendor"),
                        product_type=product_data.get("product_type"),
                        price=product_data.get("price"),
                        compare_at_price=product_data.get("compare_at_price"),
                        cost_per_item=product_data.get("cost_per_item"),
                        cost_source=product_data.get("cost_source"),
                        total_inventory=product_data.get("total_inventory"),
                        shopify_created_at=_parse_datetime(product_data.get("shopify_created_at")),
                        shopify_updated_at=_parse_datetime(product_data.get("shopify_updated_at")),
                    )
                    db.add(new_product)
                    stats.products_created += 1

                # Track cost availability
                if product_data.get("cost_per_item"):
                    stats.products_with_cost += 1
                else:
                    stats.products_missing_cost += 1

            except Exception as e:
                error_msg = f"Error syncing product {product_data.get('external_product_id')}: {e}"
                logger.error(f"[SHOPIFY_SYNC] {error_msg}")
                errors.append(error_msg)

        db.commit()

        # Update shop sync timestamp
        shop.last_synced_at = datetime.utcnow()
        db.commit()

    except ShopifyAPIError as e:
        error_msg = f"Shopify API error: {e}"
        logger.error(f"[SHOPIFY_SYNC] {error_msg}")
        errors.append(error_msg)
        return ShopifySyncResponse(success=False, stats=stats, errors=errors)

    except HTTPException:
        raise

    except Exception as e:
        error_msg = f"Unexpected error during product sync: {e}"
        logger.exception(f"[SHOPIFY_SYNC] {error_msg}")
        errors.append(error_msg)
        return ShopifySyncResponse(success=False, stats=stats, errors=errors)

    stats.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

    logger.info(
        "[SHOPIFY_SYNC] Product sync complete: created=%d, updated=%d, with_cost=%d, missing_cost=%d, duration=%.2fs",
        stats.products_created, stats.products_updated,
        stats.products_with_cost, stats.products_missing_cost,
        stats.duration_seconds
    )

    return ShopifySyncResponse(
        success=True,
        stats=stats,
        errors=errors,
        message=f"Synced {stats.products_created + stats.products_updated} products"
    )


async def sync_shopify_customers(
    db: Session,
    workspace_id: UUID,
    connection_id: UUID,
) -> ShopifySyncResponse:
    """Sync customers from Shopify to database.

    WHAT: Fetch all customers and upsert into shopify_customers table
    WHY: Need customer data for:
        - LTV (Lifetime Value) calculations
        - Order-customer linkage
        - Customer-level reporting

    Args:
        db: Database session
        workspace_id: Workspace UUID
        connection_id: Connection UUID

    Returns:
        ShopifySyncResponse with sync statistics
    """
    start_time = datetime.utcnow()
    stats = ShopifySyncStats()
    errors: List[str] = []

    logger.info(
        "[SHOPIFY_SYNC] Starting customer sync: workspace=%s, connection=%s",
        workspace_id, connection_id
    )

    try:
        # Validate connection
        connection = db.query(Connection).filter(
            Connection.id == connection_id,
            Connection.workspace_id == workspace_id,
        ).first()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found or does not belong to workspace",
            )

        if connection.provider != ProviderEnum.shopify:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection is not a Shopify connection",
            )

        shop = _get_shop_for_connection(db, connection)
        access_token = _get_access_token(connection)

        # Initialize client and fetch customers
        client = ShopifyClient(
            shop_domain=shop.shop_domain,
            access_token=access_token,
        )

        customers = await client.get_all_customers()
        logger.info(f"[SHOPIFY_SYNC] Fetched {len(customers)} customers from Shopify")

        # Upsert customers
        for customer_data in customers:
            try:
                external_id = customer_data["external_customer_id"]

                # Check if customer exists
                existing = db.query(ShopifyCustomer).filter(
                    ShopifyCustomer.shop_id == shop.id,
                    ShopifyCustomer.external_customer_id == external_id,
                ).first()

                total_spent = customer_data.get("total_spent", Decimal("0"))
                order_count = customer_data.get("order_count", 0)
                avg_order_value = total_spent / order_count if order_count > 0 else None

                if existing:
                    # Update existing customer
                    existing.email = customer_data.get("email")
                    existing.first_name = customer_data.get("first_name")
                    existing.last_name = customer_data.get("last_name")
                    existing.phone = customer_data.get("phone")
                    existing.state = customer_data.get("state")
                    existing.verified_email = customer_data.get("verified_email", False)
                    existing.accepts_marketing = customer_data.get("accepts_marketing", False)
                    existing.total_spent = total_spent
                    existing.order_count = order_count
                    existing.average_order_value = avg_order_value
                    existing.tags = customer_data.get("tags")
                    existing.updated_at = datetime.utcnow()
                    stats.customers_updated += 1
                else:
                    # Create new customer
                    new_customer = ShopifyCustomer(
                        workspace_id=workspace_id,
                        shop_id=shop.id,
                        external_customer_id=external_id,
                        email=customer_data.get("email"),
                        first_name=customer_data.get("first_name"),
                        last_name=customer_data.get("last_name"),
                        phone=customer_data.get("phone"),
                        state=customer_data.get("state"),
                        verified_email=customer_data.get("verified_email", False),
                        accepts_marketing=customer_data.get("accepts_marketing", False),
                        total_spent=total_spent,
                        order_count=order_count,
                        average_order_value=avg_order_value,
                        tags=customer_data.get("tags"),
                        shopify_created_at=_parse_datetime(customer_data.get("shopify_created_at")),
                    )
                    db.add(new_customer)
                    stats.customers_created += 1

            except Exception as e:
                error_msg = f"Error syncing customer {customer_data.get('external_customer_id')}: {e}"
                logger.error(f"[SHOPIFY_SYNC] {error_msg}")
                errors.append(error_msg)

        db.commit()

    except ShopifyAPIError as e:
        error_msg = f"Shopify API error: {e}"
        logger.error(f"[SHOPIFY_SYNC] {error_msg}")
        errors.append(error_msg)
        return ShopifySyncResponse(success=False, stats=stats, errors=errors)

    except HTTPException:
        raise

    except Exception as e:
        error_msg = f"Unexpected error during customer sync: {e}"
        logger.exception(f"[SHOPIFY_SYNC] {error_msg}")
        errors.append(error_msg)
        return ShopifySyncResponse(success=False, stats=stats, errors=errors)

    stats.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

    logger.info(
        "[SHOPIFY_SYNC] Customer sync complete: created=%d, updated=%d, duration=%.2fs",
        stats.customers_created, stats.customers_updated, stats.duration_seconds
    )

    return ShopifySyncResponse(
        success=True,
        stats=stats,
        errors=errors,
        message=f"Synced {stats.customers_created + stats.customers_updated} customers"
    )


async def sync_shopify_orders(
    db: Session,
    workspace_id: UUID,
    connection_id: UUID,
    since: Optional[datetime] = None,
    force_full_sync: bool = False,
) -> ShopifySyncResponse:
    """Sync orders from Shopify to database.

    WHAT: Fetch orders and upsert into shopify_orders and shopify_order_line_items
    WHY: Orders are the source of truth for:
        - Revenue metrics
        - Profit calculations (via line item costs)
        - Customer LTV updates
        - Attribution tracking

    Args:
        db: Database session
        workspace_id: Workspace UUID
        connection_id: Connection UUID
        since: Only sync orders after this date (default: incremental from last order)
        force_full_sync: If True, sync all orders regardless of last sync

    Returns:
        ShopifySyncResponse with sync statistics
    """
    start_time = datetime.utcnow()
    stats = ShopifySyncStats()
    errors: List[str] = []

    logger.info(
        "[SHOPIFY_SYNC] Starting order sync: workspace=%s, connection=%s, since=%s, force_full=%s",
        workspace_id, connection_id, since, force_full_sync
    )

    try:
        # Validate connection
        connection = db.query(Connection).filter(
            Connection.id == connection_id,
            Connection.workspace_id == workspace_id,
        ).first()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found or does not belong to workspace",
            )

        if connection.provider != ProviderEnum.shopify:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection is not a Shopify connection",
            )

        shop = _get_shop_for_connection(db, connection)
        access_token = _get_access_token(connection)

        # Determine sync start date
        if force_full_sync:
            sync_since = None  # Fetch all orders
        elif since:
            sync_since = since
        else:
            # Incremental: find last order and sync from there
            last_order = db.query(ShopifyOrder).filter(
                ShopifyOrder.shop_id == shop.id
            ).order_by(desc(ShopifyOrder.order_created_at)).first()

            if last_order:
                # Sync from 1 day before last order (overlap to catch updates)
                sync_since = last_order.order_created_at - timedelta(days=1)
                logger.info(f"[SHOPIFY_SYNC] Incremental sync from {sync_since}")
            else:
                # First sync: last 90 days
                sync_since = datetime.utcnow() - timedelta(days=90)
                logger.info(f"[SHOPIFY_SYNC] First sync, fetching last 90 days from {sync_since}")

        # Initialize client and fetch orders
        client = ShopifyClient(
            shop_domain=shop.shop_domain,
            access_token=access_token,
        )

        orders = await client.get_all_orders(since=sync_since)
        logger.info(f"[SHOPIFY_SYNC] Fetched {len(orders)} orders from Shopify")

        # Build product lookup for cost fallback
        product_costs: Dict[str, Decimal] = {}
        products = db.query(ShopifyProduct).filter(
            ShopifyProduct.shop_id == shop.id,
            ShopifyProduct.cost_per_item.isnot(None)
        ).all()
        for product in products:
            product_costs[product.external_product_id] = product.cost_per_item

        # Build customer lookup
        customer_lookup: Dict[str, ShopifyCustomer] = {}
        customers = db.query(ShopifyCustomer).filter(
            ShopifyCustomer.shop_id == shop.id
        ).all()
        for customer in customers:
            customer_lookup[customer.external_customer_id] = customer

        # Upsert orders
        for order_data in orders:
            try:
                external_order_id = order_data["external_order_id"]

                # Link to customer if exists
                customer_id = None
                if order_data.get("external_customer_id"):
                    customer = customer_lookup.get(order_data["external_customer_id"])
                    if customer:
                        customer_id = customer.id

                # Check if order exists
                existing_order = db.query(ShopifyOrder).filter(
                    ShopifyOrder.shop_id == shop.id,
                    ShopifyOrder.external_order_id == external_order_id,
                ).first()

                # Calculate profit from line items
                total_cost = Decimal("0")
                total_profit = Decimal("0")
                has_missing_costs = False
                line_items_data = order_data.get("line_items", [])

                for li in line_items_data:
                    quantity = li.get("quantity", 1)
                    price = li.get("price") or Decimal("0")
                    discount = li.get("total_discount") or Decimal("0")
                    line_revenue = (price * quantity) - discount

                    # Get cost: from line item, then product fallback
                    cost_per_item = li.get("cost_per_item")
                    cost_source = li.get("cost_source")

                    if cost_per_item is None and li.get("external_product_id"):
                        # Try product cost fallback
                        product_cost = product_costs.get(li["external_product_id"])
                        if product_cost:
                            cost_per_item = product_cost
                            cost_source = "product"

                    if cost_per_item:
                        line_cost = cost_per_item * quantity
                        li["cost_per_item"] = cost_per_item
                        li["cost_source"] = cost_source
                        li["line_profit"] = line_revenue - line_cost
                        total_cost += line_cost
                        total_profit += li["line_profit"]
                    else:
                        has_missing_costs = True
                        li["line_profit"] = None

                # Update stats
                if has_missing_costs:
                    stats.orders_missing_cost += 1

                order_total = order_data.get("total_price") or Decimal("0")
                stats.total_revenue += order_total
                stats.total_profit += total_profit

                if existing_order:
                    # Update existing order
                    existing_order.order_number = order_data.get("order_number")
                    existing_order.name = order_data.get("name")
                    existing_order.total_price = order_total
                    existing_order.subtotal_price = order_data.get("subtotal_price")
                    existing_order.total_tax = order_data.get("total_tax")
                    existing_order.total_shipping = order_data.get("total_shipping")
                    existing_order.total_discounts = order_data.get("total_discounts")
                    existing_order.currency = order_data.get("currency", "USD")
                    existing_order.total_cost = total_cost if not has_missing_costs else None
                    existing_order.total_profit = total_profit if not has_missing_costs else None
                    existing_order.has_missing_costs = has_missing_costs
                    existing_order.financial_status = _map_financial_status(order_data.get("financial_status"))
                    existing_order.fulfillment_status = _map_fulfillment_status(order_data.get("fulfillment_status"))
                    existing_order.cancelled_at = _parse_datetime(order_data.get("cancelled_at"))
                    existing_order.cancel_reason = order_data.get("cancel_reason")
                    existing_order.customer_id = customer_id
                    existing_order.source_name = order_data.get("source_name")
                    existing_order.landing_site = order_data.get("landing_site")
                    existing_order.referring_site = order_data.get("referring_site")
                    existing_order.utm_source = order_data.get("utm_source")
                    existing_order.utm_medium = order_data.get("utm_medium")
                    existing_order.utm_campaign = order_data.get("utm_campaign")
                    existing_order.utm_content = order_data.get("utm_content")
                    existing_order.utm_term = order_data.get("utm_term")
                    existing_order.app_name = order_data.get("app_name")
                    existing_order.tags = order_data.get("tags")
                    existing_order.note = order_data.get("note")
                    existing_order.order_processed_at = _parse_datetime(order_data.get("order_processed_at"))
                    existing_order.order_closed_at = _parse_datetime(order_data.get("order_closed_at"))
                    existing_order.updated_at = datetime.utcnow()

                    order = existing_order
                    stats.orders_updated += 1
                else:
                    # Create new order
                    order = ShopifyOrder(
                        workspace_id=workspace_id,
                        shop_id=shop.id,
                        customer_id=customer_id,
                        external_order_id=external_order_id,
                        order_number=order_data.get("order_number"),
                        name=order_data.get("name"),
                        total_price=order_total,
                        subtotal_price=order_data.get("subtotal_price"),
                        total_tax=order_data.get("total_tax"),
                        total_shipping=order_data.get("total_shipping"),
                        total_discounts=order_data.get("total_discounts"),
                        currency=order_data.get("currency", "USD"),
                        total_cost=total_cost if not has_missing_costs else None,
                        total_profit=total_profit if not has_missing_costs else None,
                        has_missing_costs=has_missing_costs,
                        financial_status=_map_financial_status(order_data.get("financial_status")),
                        fulfillment_status=_map_fulfillment_status(order_data.get("fulfillment_status")),
                        cancelled_at=_parse_datetime(order_data.get("cancelled_at")),
                        cancel_reason=order_data.get("cancel_reason"),
                        source_name=order_data.get("source_name"),
                        landing_site=order_data.get("landing_site"),
                        referring_site=order_data.get("referring_site"),
                        utm_source=order_data.get("utm_source"),
                        utm_medium=order_data.get("utm_medium"),
                        utm_campaign=order_data.get("utm_campaign"),
                        utm_content=order_data.get("utm_content"),
                        utm_term=order_data.get("utm_term"),
                        app_name=order_data.get("app_name"),
                        tags=order_data.get("tags"),
                        note=order_data.get("note"),
                        order_created_at=_parse_datetime(order_data.get("order_created_at")) or datetime.utcnow(),
                        order_processed_at=_parse_datetime(order_data.get("order_processed_at")),
                        order_closed_at=_parse_datetime(order_data.get("order_closed_at")),
                    )
                    db.add(order)
                    db.flush()  # Get order.id
                    stats.orders_created += 1

                # Sync line items (delete and recreate for simplicity)
                if existing_order:
                    db.query(ShopifyOrderLineItem).filter(
                        ShopifyOrderLineItem.order_id == order.id
                    ).delete()

                # Get product lookup by external_id
                product_lookup: Dict[str, ShopifyProduct] = {}
                for product in products:
                    product_lookup[product.external_product_id] = product

                for li in line_items_data:
                    # Link to product if exists
                    product_id = None
                    if li.get("external_product_id"):
                        product = product_lookup.get(li["external_product_id"])
                        if product:
                            product_id = product.id

                    line_item = ShopifyOrderLineItem(
                        order_id=order.id,
                        product_id=product_id,
                        external_line_item_id=li["external_line_item_id"],
                        external_product_id=li.get("external_product_id"),
                        external_variant_id=li.get("external_variant_id"),
                        title=li["title"],
                        variant_title=li.get("variant_title"),
                        sku=li.get("sku"),
                        quantity=li.get("quantity", 1),
                        price=li.get("price") or Decimal("0"),
                        total_discount=li.get("total_discount") or Decimal("0"),
                        cost_per_item=li.get("cost_per_item"),
                        cost_source=li.get("cost_source"),
                        line_profit=li.get("line_profit"),
                    )
                    db.add(line_item)
                    stats.line_items_created += 1

            except Exception as e:
                error_msg = f"Error syncing order {order_data.get('external_order_id')}: {e}"
                logger.error(f"[SHOPIFY_SYNC] {error_msg}")
                errors.append(error_msg)

        db.commit()

        # Update customer LTV metrics
        await _update_customer_ltv(db, shop.id)

    except ShopifyAPIError as e:
        error_msg = f"Shopify API error: {e}"
        logger.error(f"[SHOPIFY_SYNC] {error_msg}")
        errors.append(error_msg)
        return ShopifySyncResponse(success=False, stats=stats, errors=errors)

    except HTTPException:
        raise

    except Exception as e:
        error_msg = f"Unexpected error during order sync: {e}"
        logger.exception(f"[SHOPIFY_SYNC] {error_msg}")
        errors.append(error_msg)
        return ShopifySyncResponse(success=False, stats=stats, errors=errors)

    stats.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

    logger.info(
        "[SHOPIFY_SYNC] Order sync complete: created=%d, updated=%d, line_items=%d, "
        "revenue=$%.2f, profit=$%.2f, missing_cost=%d, duration=%.2fs",
        stats.orders_created, stats.orders_updated, stats.line_items_created,
        stats.total_revenue, stats.total_profit, stats.orders_missing_cost,
        stats.duration_seconds
    )

    return ShopifySyncResponse(
        success=True,
        stats=stats,
        errors=errors,
        message=f"Synced {stats.orders_created + stats.orders_updated} orders"
    )


async def _update_customer_ltv(db: Session, shop_id: UUID) -> None:
    """Update customer LTV metrics from orders.

    WHAT: Recalculate total_spent, order_count, first/last order dates
    WHY: Keep customer metrics in sync with order data for fast LTV queries
    """
    logger.info(f"[SHOPIFY_SYNC] Updating customer LTV metrics for shop {shop_id}")

    # Get all customers for this shop
    customers = db.query(ShopifyCustomer).filter(
        ShopifyCustomer.shop_id == shop_id
    ).all()

    for customer in customers:
        # Aggregate orders for this customer
        from sqlalchemy import func

        result = db.query(
            func.count(ShopifyOrder.id).label("order_count"),
            func.sum(ShopifyOrder.total_price).label("total_spent"),
            func.min(ShopifyOrder.order_created_at).label("first_order"),
            func.max(ShopifyOrder.order_created_at).label("last_order"),
        ).filter(
            ShopifyOrder.customer_id == customer.id,
            ShopifyOrder.financial_status.in_([
                ShopifyFinancialStatusEnum.paid,
                ShopifyFinancialStatusEnum.partially_refunded,
            ])
        ).first()

        if result:
            customer.order_count = result.order_count or 0
            customer.total_spent = result.total_spent or Decimal("0")
            customer.first_order_at = result.first_order
            customer.last_order_at = result.last_order

            if customer.order_count > 0:
                customer.average_order_value = customer.total_spent / customer.order_count
            else:
                customer.average_order_value = None

    db.commit()
    logger.info(f"[SHOPIFY_SYNC] Updated LTV for {len(customers)} customers")


async def sync_shopify_all(
    db: Session,
    workspace_id: UUID,
    connection_id: UUID,
    force_full_sync: bool = False,
) -> ShopifySyncResponse:
    """Run full Shopify sync: products -> customers -> orders.

    WHAT: Orchestrate complete data sync in correct order
    WHY: Products and customers must exist before orders (for FK linkage)

    Args:
        db: Database session
        workspace_id: Workspace UUID
        connection_id: Connection UUID
        force_full_sync: If True, sync all data regardless of last sync

    Returns:
        Combined ShopifySyncResponse with all statistics
    """
    start_time = datetime.utcnow()
    combined_stats = ShopifySyncStats()
    all_errors: List[str] = []

    logger.info(
        "[SHOPIFY_SYNC] Starting full sync: workspace=%s, connection=%s",
        workspace_id, connection_id
    )

    # 1. Sync products first (needed for line item cost lookup)
    product_result = await sync_shopify_products(db, workspace_id, connection_id)
    combined_stats.products_created = product_result.stats.products_created
    combined_stats.products_updated = product_result.stats.products_updated
    combined_stats.products_with_cost = product_result.stats.products_with_cost
    combined_stats.products_missing_cost = product_result.stats.products_missing_cost
    all_errors.extend(product_result.errors)

    if not product_result.success:
        logger.error("[SHOPIFY_SYNC] Product sync failed, aborting full sync")
        return ShopifySyncResponse(
            success=False,
            stats=combined_stats,
            errors=all_errors,
            message="Product sync failed"
        )

    # 2. Sync customers (optional - needed for order customer linkage)
    # NOTE: Customer API requires protected customer data access approval
    # If not approved, we skip customer sync but continue with orders
    customer_result = await sync_shopify_customers(db, workspace_id, connection_id)
    combined_stats.customers_created = customer_result.stats.customers_created
    combined_stats.customers_updated = customer_result.stats.customers_updated

    # Track if customer sync failure is just a permission issue (not a real error)
    customer_permission_error = False

    if not customer_result.success:
        # Check if it's a permission error (not approved for customer data)
        is_permission_error = any(
            "not approved" in err.lower() or "protected" in err.lower()
            for err in customer_result.errors
        )
        if is_permission_error:
            logger.warning(
                "[SHOPIFY_SYNC] Customer sync skipped - app not approved for customer data. "
                "Orders will sync without customer linkage. "
                "See https://shopify.dev/docs/apps/launch/protected-customer-data"
            )
            # Don't add to errors - this is expected for unapproved apps
            customer_permission_error = True
        else:
            # Real error - log but continue anyway
            logger.warning("[SHOPIFY_SYNC] Customer sync failed, continuing with orders")
            all_errors.extend(customer_result.errors)

    # 3. Sync orders (depends on products and customers)
    order_result = await sync_shopify_orders(
        db, workspace_id, connection_id,
        force_full_sync=force_full_sync
    )
    combined_stats.orders_created = order_result.stats.orders_created
    combined_stats.orders_updated = order_result.stats.orders_updated
    combined_stats.line_items_created = order_result.stats.line_items_created
    combined_stats.total_revenue = order_result.stats.total_revenue
    combined_stats.total_profit = order_result.stats.total_profit
    combined_stats.orders_missing_cost = order_result.stats.orders_missing_cost
    all_errors.extend(order_result.errors)

    combined_stats.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

    # Consider sync successful if:
    # - Products synced successfully
    # - Orders synced successfully
    # - Customers either synced OR failed due to permission (expected for unapproved apps)
    customer_ok = customer_result.success or customer_permission_error
    success = product_result.success and customer_ok and order_result.success

    logger.info(
        "[SHOPIFY_SYNC] Full sync complete: success=%s, products=%d, customers=%d, orders=%d, duration=%.2fs",
        success,
        combined_stats.products_created + combined_stats.products_updated,
        combined_stats.customers_created + combined_stats.customers_updated,
        combined_stats.orders_created + combined_stats.orders_updated,
        combined_stats.duration_seconds
    )

    return ShopifySyncResponse(
        success=success,
        stats=combined_stats,
        errors=all_errors,
        message=f"Full sync {'completed' if success else 'completed with errors'}"
    )
