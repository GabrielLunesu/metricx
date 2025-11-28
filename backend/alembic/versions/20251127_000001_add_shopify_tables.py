"""Add Shopify e-commerce tables (shops, products, customers, orders, line_items)

Revision ID: 20251127_000001
Revises: 20251126_000001
Create Date: 2025-11-27 23:00:00.000000

WHAT:
    Creates dedicated Shopify tables for e-commerce data:
    - shopify_shops: Store metadata (one per Connection)
    - shopify_products: Product catalog with COGS
    - shopify_customers: Customer master for LTV calculations
    - shopify_orders: Order facts with attribution
    - shopify_order_line_items: Line items with cost tracking

WHY:
    Shopify data structure differs from ad platforms - needs separate schema
    for LTV calculations, profit tracking (COGS), and revenue analytics.
    Enables calculating actual profit (revenue - COGS), not just revenue.

REFERENCES:
    - Implementation plan: docs/living-docs/SHOPIFY_INTEGRATION_PLAN.md
    - Shopify GraphQL Admin API: https://shopify.dev/docs/api/admin-graphql
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251127_000001'
down_revision = '20251126_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # STEP 1: Add 'shopify' to ProviderEnum
    # =========================================================================
    # WHAT: Extend the provider enum to include Shopify
    # WHY: Connections need to identify as Shopify provider
    op.execute("ALTER TYPE providerenum ADD VALUE IF NOT EXISTS 'shopify'")

    # =========================================================================
    # STEP 2: Create Shopify-specific enums
    # =========================================================================
    # WHAT: Create enums for order financial and fulfillment status
    # WHY: Track order lifecycle for accurate revenue reporting

    # Financial status enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE shopifyfinancialstatusenum AS ENUM (
                'pending', 'authorized', 'partially_paid', 'paid',
                'partially_refunded', 'refunded', 'voided'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Fulfillment status enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE shopifyfulfillmentstatusenum AS ENUM (
                'unfulfilled', 'partial', 'fulfilled', 'restocked',
                'pending_fulfillment', 'open', 'in_progress', 'on_hold', 'scheduled'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # =========================================================================
    # STEP 3: Create shopify_shops table
    # =========================================================================
    # WHAT: Store metadata - one per Connection
    # WHY: Need shop-level settings like timezone and currency
    op.create_table(
        'shopify_shops',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('connections.id'), nullable=False, unique=True),
        sa.Column('external_shop_id', sa.String(), nullable=False),
        sa.Column('shop_domain', sa.String(), nullable=False),
        sa.Column('shop_name', sa.String(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False, server_default='USD'),
        sa.Column('timezone', sa.String(), nullable=True),
        sa.Column('country_code', sa.String(), nullable=True),
        sa.Column('plan_name', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_shopify_shops_workspace_id', 'shopify_shops', ['workspace_id'])
    op.create_index('ix_shopify_shops_connection_id', 'shopify_shops', ['connection_id'])

    # =========================================================================
    # STEP 4: Create shopify_products table
    # =========================================================================
    # WHAT: Product catalog with COGS from metafields
    # WHY: Need product-level cost to calculate true profit per order
    op.create_table(
        'shopify_products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shopify_shops.id'), nullable=False),
        sa.Column('external_product_id', sa.String(), nullable=False),
        sa.Column('handle', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('product_type', sa.String(), nullable=True),
        sa.Column('vendor', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('price', sa.Numeric(18, 4), nullable=True),
        sa.Column('compare_at_price', sa.Numeric(18, 4), nullable=True),
        sa.Column('cost_per_item', sa.Numeric(18, 4), nullable=True),
        sa.Column('cost_source', sa.String(), nullable=True),
        sa.Column('total_inventory', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('shopify_created_at', sa.DateTime(), nullable=True),
        sa.Column('shopify_updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('shop_id', 'external_product_id', name='uq_shopify_product'),
    )
    op.create_index('ix_shopify_products_workspace_id', 'shopify_products', ['workspace_id'])
    op.create_index('ix_shopify_products_shop_id', 'shopify_products', ['shop_id'])
    op.create_index('ix_shopify_products_external_id', 'shopify_products', ['external_product_id'])

    # =========================================================================
    # STEP 5: Create shopify_customers table
    # =========================================================================
    # WHAT: Customer master for LTV calculations
    # WHY: Customer-level metrics enable LTV calculations
    op.create_table(
        'shopify_customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shopify_shops.id'), nullable=False),
        sa.Column('external_customer_id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('verified_email', sa.Boolean(), server_default='false'),
        sa.Column('accepts_marketing', sa.Boolean(), server_default='false'),
        sa.Column('total_spent', sa.Numeric(18, 4), server_default='0'),
        sa.Column('order_count', sa.Integer(), server_default='0'),
        sa.Column('average_order_value', sa.Numeric(18, 4), nullable=True),
        sa.Column('first_order_at', sa.DateTime(), nullable=True),
        sa.Column('last_order_at', sa.DateTime(), nullable=True),
        sa.Column('tags', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('shopify_created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('shop_id', 'external_customer_id', name='uq_shopify_customer'),
    )
    op.create_index('ix_shopify_customers_workspace_id', 'shopify_customers', ['workspace_id'])
    op.create_index('ix_shopify_customers_shop_id', 'shopify_customers', ['shop_id'])
    op.create_index('ix_shopify_customers_external_id', 'shopify_customers', ['external_customer_id'])
    op.create_index('ix_shopify_customers_email', 'shopify_customers', ['email'])

    # =========================================================================
    # STEP 6: Create shopify_orders table
    # =========================================================================
    # WHAT: Order facts with attribution and totals
    # WHY: Orders are the source of truth for revenue and profit metrics
    op.create_table(
        'shopify_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shopify_shops.id'), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shopify_customers.id'), nullable=True),
        sa.Column('external_order_id', sa.String(), nullable=False),
        sa.Column('order_number', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        # Totals
        sa.Column('total_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('subtotal_price', sa.Numeric(18, 4), nullable=True),
        sa.Column('total_tax', sa.Numeric(18, 4), nullable=True),
        sa.Column('total_shipping', sa.Numeric(18, 4), nullable=True),
        sa.Column('total_discounts', sa.Numeric(18, 4), nullable=True),
        sa.Column('currency', sa.String(), nullable=False, server_default='USD'),
        # Profit calculation
        sa.Column('total_cost', sa.Numeric(18, 4), nullable=True),
        sa.Column('total_profit', sa.Numeric(18, 4), nullable=True),
        sa.Column('has_missing_costs', sa.Boolean(), server_default='false'),
        # Status
        # NOTE: Using postgresql.ENUM with create_type=False since enums are created via raw SQL above
        sa.Column('financial_status', postgresql.ENUM(
            'pending', 'authorized', 'partially_paid', 'paid',
            'partially_refunded', 'refunded', 'voided',
            name='shopifyfinancialstatusenum', create_type=False
        ), nullable=True),
        sa.Column('fulfillment_status', postgresql.ENUM(
            'unfulfilled', 'partial', 'fulfilled', 'restocked',
            'pending_fulfillment', 'open', 'in_progress', 'on_hold', 'scheduled',
            name='shopifyfulfillmentstatusenum', create_type=False
        ), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('cancel_reason', sa.String(), nullable=True),
        # Attribution
        sa.Column('source_name', sa.String(), nullable=True),
        sa.Column('landing_site', sa.String(), nullable=True),
        sa.Column('referring_site', sa.String(), nullable=True),
        sa.Column('utm_source', sa.String(), nullable=True),
        sa.Column('utm_medium', sa.String(), nullable=True),
        sa.Column('utm_campaign', sa.String(), nullable=True),
        sa.Column('utm_content', sa.String(), nullable=True),
        sa.Column('utm_term', sa.String(), nullable=True),
        # Metadata
        sa.Column('app_name', sa.String(), nullable=True),
        sa.Column('tags', postgresql.JSON(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('order_created_at', sa.DateTime(), nullable=False),
        sa.Column('order_processed_at', sa.DateTime(), nullable=True),
        sa.Column('order_closed_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('shop_id', 'external_order_id', name='uq_shopify_order'),
    )
    op.create_index('ix_shopify_orders_workspace_id', 'shopify_orders', ['workspace_id'])
    op.create_index('ix_shopify_orders_shop_id', 'shopify_orders', ['shop_id'])
    op.create_index('ix_shopify_orders_customer_id', 'shopify_orders', ['customer_id'])
    op.create_index('ix_shopify_orders_external_id', 'shopify_orders', ['external_order_id'])
    op.create_index('ix_shopify_orders_created_at', 'shopify_orders', ['order_created_at'])
    op.create_index('ix_shopify_orders_financial_status', 'shopify_orders', ['financial_status'])
    op.create_index('ix_shopify_orders_utm_source', 'shopify_orders', ['utm_source'])

    # =========================================================================
    # STEP 7: Create shopify_order_line_items table
    # =========================================================================
    # WHAT: Line items linking orders to products with cost tracking
    # WHY: Line-item level cost tracking enables accurate profit calculation
    op.create_table(
        'shopify_order_line_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shopify_orders.id'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shopify_products.id'), nullable=True),
        sa.Column('external_line_item_id', sa.String(), nullable=False),
        sa.Column('external_product_id', sa.String(), nullable=True),
        sa.Column('external_variant_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('variant_title', sa.String(), nullable=True),
        sa.Column('sku', sa.String(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('price', sa.Numeric(18, 4), nullable=False),
        sa.Column('total_discount', sa.Numeric(18, 4), server_default='0'),
        sa.Column('cost_per_item', sa.Numeric(18, 4), nullable=True),
        sa.Column('cost_source', sa.String(), nullable=True),
        sa.Column('line_profit', sa.Numeric(18, 4), nullable=True),
        sa.Column('fulfillable_quantity', sa.Integer(), nullable=True),
        sa.Column('fulfillment_status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_shopify_line_items_order_id', 'shopify_order_line_items', ['order_id'])
    op.create_index('ix_shopify_line_items_product_id', 'shopify_order_line_items', ['product_id'])


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign keys)
    op.drop_table('shopify_order_line_items')
    op.drop_table('shopify_orders')
    op.drop_table('shopify_customers')
    op.drop_table('shopify_products')
    op.drop_table('shopify_shops')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS shopifyfulfillmentstatusenum')
    op.execute('DROP TYPE IF EXISTS shopifyfinancialstatusenum')

    # Note: We don't remove 'shopify' from providerenum as it could break existing data
    # PostgreSQL doesn't support removing enum values easily
