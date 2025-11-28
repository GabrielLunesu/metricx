"""Shopify synchronization endpoints.

WHAT:
    Thin HTTP wrappers for Shopify sync services.

WHY:
    - Routers handle auth + request parsing only
    - Business logic reused by both HTTP calls and background workers
    - Consistent pattern with Meta/Google sync routers

REFERENCES:
    - backend/app/services/shopify_sync_service.py
    - backend/app/routers/meta_sync.py (pattern followed)
    - docs/living-docs/SHOPIFY_INTEGRATION_PLAN.md
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Connection, ProviderEnum, User
from app.services.shopify_sync_service import (
    ShopifySyncResponse,
    sync_shopify_all,
    sync_shopify_customers,
    sync_shopify_orders,
    sync_shopify_products,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Response Models (thin wrappers for API responses)
# =============================================================================
# WHAT: Define response schemas specific to Shopify sync operations
# WHY: Pydantic models provide OpenAPI docs and validation, while
#      internal dataclasses (ShopifySyncStats) handle business logic

class ShopifySyncStatsResponse(BaseModel):
    """Statistics returned from Shopify sync operations."""

    # Product stats
    products_created: int = Field(default=0, description="New products added")
    products_updated: int = Field(default=0, description="Existing products updated")
    products_with_cost: int = Field(default=0, description="Products with COGS data")
    products_missing_cost: int = Field(default=0, description="Products missing COGS")

    # Customer stats
    customers_created: int = Field(default=0, description="New customers added")
    customers_updated: int = Field(default=0, description="Existing customers updated")

    # Order stats
    orders_created: int = Field(default=0, description="New orders added")
    orders_updated: int = Field(default=0, description="Existing orders updated")
    orders_with_missing_costs: int = Field(default=0, description="Orders with products missing COGS")

    # Revenue/profit (from orders)
    total_revenue: float = Field(default=0.0, description="Sum of order totals synced")
    total_profit: float = Field(default=0.0, description="Sum of calculated profits")

    class Config:
        from_attributes = True


class ShopifySyncAPIResponse(BaseModel):
    """API response for Shopify sync endpoints."""

    success: bool = Field(description="Whether sync completed successfully")
    stats: ShopifySyncStatsResponse = Field(description="Sync statistics")
    errors: list[str] = Field(default_factory=list, description="Error messages if any")
    message: str = Field(default="", description="Summary message")


class ShopifyOrderSyncRequest(BaseModel):
    """Request body for order sync endpoint.

    WHAT: Optional parameters to control order sync behavior
    WHY: Allows manual date range and force full refresh
    """

    start_date: Optional[date] = Field(
        default=None,
        description="Start date for order sync (default: 90 days ago or last sync - 1 day)"
    )
    force_full_sync: bool = Field(
        default=False,
        description="If true, sync ALL orders ignoring last sync timestamp"
    )


# =============================================================================
# Helper function to convert dataclass to Pydantic response
# =============================================================================

def _to_api_response(result: ShopifySyncResponse) -> ShopifySyncAPIResponse:
    """Convert internal dataclass to API response model.

    WHAT: Transform ShopifySyncResponse dataclass to ShopifySyncAPIResponse Pydantic model
    WHY: Separates internal business logic types from API contract types
    """
    return ShopifySyncAPIResponse(
        success=result.success,
        stats=ShopifySyncStatsResponse(
            products_created=result.stats.products_created,
            products_updated=result.stats.products_updated,
            products_with_cost=result.stats.products_with_cost,
            products_missing_cost=result.stats.products_missing_cost,
            customers_created=result.stats.customers_created,
            customers_updated=result.stats.customers_updated,
            orders_created=result.stats.orders_created,
            orders_updated=result.stats.orders_updated,
            orders_with_missing_costs=result.stats.orders_with_missing_costs,
            total_revenue=float(result.stats.total_revenue),
            total_profit=float(result.stats.total_profit),
        ),
        errors=result.errors,
        message=result.message,
    )


# =============================================================================
# Router setup
# =============================================================================

router = APIRouter(
    prefix="/workspaces/{workspace_id}/connections/{connection_id}/shopify",
    tags=["Shopify Sync"],
)


# =============================================================================
# Validation helper
# =============================================================================

def _validate_shopify_connection(
    db: Session,
    workspace_id: UUID,
    connection_id: UUID,
) -> Connection:
    """Validate connection exists, belongs to workspace, and is Shopify.

    WHAT: Fetch and validate Connection record
    WHY: All endpoints need this validation, DRY principle

    Raises:
        HTTPException: 404 if not found, 400 if wrong provider
    """
    connection = (
        db.query(Connection)
        .filter(
            Connection.id == connection_id,
            Connection.workspace_id == workspace_id,
        )
        .first()
    )

    if not connection:
        raise HTTPException(
            status_code=404,
            detail=f"Connection {connection_id} not found in workspace {workspace_id}"
        )

    if connection.provider != ProviderEnum.shopify:
        raise HTTPException(
            status_code=400,
            detail=f"Connection {connection_id} is not a Shopify connection (provider={connection.provider})"
        )

    return connection


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/sync-products", response_model=ShopifySyncAPIResponse)
async def sync_products(
    workspace_id: UUID,
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShopifySyncAPIResponse:
    """Sync products from Shopify.

    WHAT: Fetch all products and variants from Shopify GraphQL API
    WHY: Products contain COGS data needed for profit calculations

    Returns product catalog with cost_per_item when available from:
    1. Variant inventoryItem.unitCost (preferred)
    2. Product metafield (fallback)
    """
    logger.info(
        "[SHOPIFY_SYNC] HTTP product sync requested: workspace=%s connection=%s",
        workspace_id,
        connection_id,
    )

    _validate_shopify_connection(db, workspace_id, connection_id)

    result = await sync_shopify_products(
        db=db,
        workspace_id=workspace_id,
        connection_id=connection_id,
    )

    return _to_api_response(result)


@router.post("/sync-customers", response_model=ShopifySyncAPIResponse)
async def sync_customers(
    workspace_id: UUID,
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShopifySyncAPIResponse:
    """Sync customers from Shopify.

    WHAT: Fetch all customers from Shopify GraphQL API
    WHY: Customer data needed for LTV calculations and cohort analysis

    Customer metrics (total_spent, order_count, AOV) are calculated
    when orders are synced to ensure accuracy.
    """
    logger.info(
        "[SHOPIFY_SYNC] HTTP customer sync requested: workspace=%s connection=%s",
        workspace_id,
        connection_id,
    )

    _validate_shopify_connection(db, workspace_id, connection_id)

    result = await sync_shopify_customers(
        db=db,
        workspace_id=workspace_id,
        connection_id=connection_id,
    )

    return _to_api_response(result)


@router.post("/sync-orders", response_model=ShopifySyncAPIResponse)
async def sync_orders(
    workspace_id: UUID,
    connection_id: UUID,
    request: ShopifyOrderSyncRequest = ShopifyOrderSyncRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShopifySyncAPIResponse:
    """Sync orders from Shopify.

    WHAT: Fetch orders from Shopify GraphQL API with line items
    WHY: Orders are the source of truth for revenue, profit, and LTV calculations

    For each order:
    - Extracts revenue (total_price)
    - Calculates profit (revenue - COGS) per line item
    - Captures UTM attribution from landing_site
    - Updates customer LTV metrics

    By default, syncs incrementally from (last_order - 1 day) to capture
    any delayed order updates. Use force_full_sync=true for complete refresh.
    """
    logger.info(
        "[SHOPIFY_SYNC] HTTP order sync requested: workspace=%s connection=%s force_full=%s",
        workspace_id,
        connection_id,
        request.force_full_sync,
    )

    _validate_shopify_connection(db, workspace_id, connection_id)

    # Convert start_date to datetime if provided
    since_datetime = None
    if request.start_date:
        since_datetime = datetime.combine(request.start_date, datetime.min.time())

    result = await sync_shopify_orders(
        db=db,
        workspace_id=workspace_id,
        connection_id=connection_id,
        since=since_datetime,
        force_full_sync=request.force_full_sync,
    )

    return _to_api_response(result)


@router.post("/sync-entities", response_model=ShopifySyncAPIResponse)
async def sync_entities(
    workspace_id: UUID,
    connection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShopifySyncAPIResponse:
    """Sync entities (products + customers) from Shopify.

    WHAT: Convenience endpoint to sync products and customers together
    WHY: Products must be synced before orders (for COGS lookup)
         Customers must be synced before orders (for customer_id FK)

    This is the "entity sync" equivalent of Meta's campaigns/adsets/ads sync.
    Call this before sync-orders for a complete data refresh.
    """
    logger.info(
        "[SHOPIFY_SYNC] HTTP entity sync requested: workspace=%s connection=%s",
        workspace_id,
        connection_id,
    )

    _validate_shopify_connection(db, workspace_id, connection_id)

    # Sync products first (needed for COGS)
    products_result = await sync_shopify_products(
        db=db,
        workspace_id=workspace_id,
        connection_id=connection_id,
    )

    # Then sync customers
    customers_result = await sync_shopify_customers(
        db=db,
        workspace_id=workspace_id,
        connection_id=connection_id,
    )

    # Combine results
    combined_stats = ShopifySyncStatsResponse(
        products_created=products_result.stats.products_created,
        products_updated=products_result.stats.products_updated,
        products_with_cost=products_result.stats.products_with_cost,
        products_missing_cost=products_result.stats.products_missing_cost,
        customers_created=customers_result.stats.customers_created,
        customers_updated=customers_result.stats.customers_updated,
    )

    combined_errors = products_result.errors + customers_result.errors
    success = products_result.success and customers_result.success

    return ShopifySyncAPIResponse(
        success=success,
        stats=combined_stats,
        errors=combined_errors,
        message=f"Synced {combined_stats.products_created + combined_stats.products_updated} products, "
                f"{combined_stats.customers_created + combined_stats.customers_updated} customers",
    )


@router.post("/sync-all", response_model=ShopifySyncAPIResponse)
async def sync_all(
    workspace_id: UUID,
    connection_id: UUID,
    force_full_sync: bool = Query(
        default=False,
        description="If true, sync ALL orders ignoring last sync timestamp"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShopifySyncAPIResponse:
    """Run complete Shopify sync: products → customers → orders.

    WHAT: Orchestrate full data sync in correct dependency order
    WHY: Provides one-click complete refresh of all Shopify data

    Sync order matters:
    1. Products first (COGS needed for profit calculation)
    2. Customers second (customer_id FK needed for orders)
    3. Orders last (references products and customers)

    This is equivalent to running sync-entities then sync-orders.
    """
    logger.info(
        "[SHOPIFY_SYNC] HTTP full sync requested: workspace=%s connection=%s force_full=%s",
        workspace_id,
        connection_id,
        force_full_sync,
    )

    _validate_shopify_connection(db, workspace_id, connection_id)

    result = await sync_shopify_all(
        db=db,
        workspace_id=workspace_id,
        connection_id=connection_id,
        force_full_sync=force_full_sync,
    )

    return _to_api_response(result)
