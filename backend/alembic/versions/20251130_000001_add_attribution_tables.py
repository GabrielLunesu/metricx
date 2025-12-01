"""Add attribution engine tables (journeys, touchpoints, pixel_events, attributions).

Revision ID: 20251130_000001
Revises: 20251127_000001
Create Date: 2025-11-30 12:00:00.000000

WHAT:
    Creates attribution engine tables:
    - pixel_events: Immutable raw event log from web pixel (event sourcing)
    - customer_journeys: Tracks visitors across sessions
    - journey_touchpoints: Each marketing interaction (UTMs, click IDs)
    - attributions: Final attribution records linking orders to entities

    Also adds:
    - checkout_token to shopify_orders (for journey linking)
    - web_pixel_id to connections (for pixel activation)

WHY:
    The Attribution Engine bridges the gap between ad spend and revenue by
    tracking customer journeys from first ad click through purchase.
    This enables accurate ROAS calculation per campaign/ad.

REFERENCES:
    - docs/living-docs/ATTRIBUTION_ENGINE.md
    - Shopify Web Pixels API: https://shopify.dev/docs/api/web-pixels-api
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251130_000001'
down_revision = '20251127_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # STEP 1: Add checkout_token to shopify_orders
    # =========================================================================
    # WHAT: Add checkout_token column for linking orders to pixel journeys
    # WHY: Pixel sends checkout_token on checkout_completed; webhook has same token
    op.add_column(
        'shopify_orders',
        sa.Column('checkout_token', sa.String(), nullable=True)
    )
    # Partial index for efficient lookup (only non-null tokens)
    op.create_index(
        'ix_shopify_orders_checkout_token',
        'shopify_orders',
        ['workspace_id', 'checkout_token'],
        postgresql_where=sa.text('checkout_token IS NOT NULL')
    )

    # =========================================================================
    # STEP 2: Add web_pixel_id to connections
    # =========================================================================
    # WHAT: Store Shopify web pixel ID for each connection
    # WHY: Need to track which pixel is activated for this store
    op.add_column(
        'connections',
        sa.Column('web_pixel_id', sa.String(), nullable=True)
    )

    # =========================================================================
    # STEP 3: Create pixel_events table (immutable event log)
    # =========================================================================
    # WHAT: Raw pixel events for event sourcing
    # WHY: Never lose data; can recompute journeys if attribution logic changes
    op.create_table(
        'pixel_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('visitor_id', sa.String(), nullable=False),
        # Client-generated UUID for deduplication
        sa.Column('event_id', sa.String(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('event_data', postgresql.JSONB(), server_default='{}'),

        # Attribution fields (denormalized for fast queries)
        sa.Column('utm_source', sa.String(), nullable=True),
        sa.Column('utm_medium', sa.String(), nullable=True),
        sa.Column('utm_campaign', sa.String(), nullable=True),
        sa.Column('utm_content', sa.String(), nullable=True),
        sa.Column('utm_term', sa.String(), nullable=True),
        sa.Column('fbclid', sa.String(), nullable=True),
        sa.Column('gclid', sa.String(), nullable=True),
        sa.Column('ttclid', sa.String(), nullable=True),
        sa.Column('landing_page', sa.String(), nullable=True),

        # Context
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('referrer', sa.String(), nullable=True),
        sa.Column('ip_hash', sa.String(), nullable=True),  # Hashed for privacy

        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'))
    )

    # Indexes for pixel_events
    op.create_index('ix_pixel_events_workspace', 'pixel_events',
                    ['workspace_id', 'created_at'])
    op.create_index('ix_pixel_events_visitor', 'pixel_events',
                    ['workspace_id', 'visitor_id', 'created_at'])
    # Partial index for deduplication (only non-null event_ids)
    op.create_index(
        'ix_pixel_events_dedup',
        'pixel_events',
        ['workspace_id', 'event_id'],
        unique=True,
        postgresql_where=sa.text('event_id IS NOT NULL')
    )

    # =========================================================================
    # STEP 4: Create customer_journeys table
    # =========================================================================
    # WHAT: Tracks visitors across sessions
    # WHY: One visitor can make multiple purchases over time (journey 1:N orders)
    op.create_table(
        'customer_journeys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('workspaces.id'), nullable=False),

        # Identity
        sa.Column('visitor_id', sa.String(), nullable=False),
        sa.Column('customer_email', sa.String(), nullable=True),
        sa.Column('shopify_customer_id', sa.BigInteger(), nullable=True),

        # For linking to orders (most recent checkout)
        sa.Column('checkout_token', sa.String(), nullable=True),

        # First touch attribution (captured on first visit)
        sa.Column('first_touch_source', sa.String(), nullable=True),
        sa.Column('first_touch_medium', sa.String(), nullable=True),
        sa.Column('first_touch_campaign', sa.String(), nullable=True),
        sa.Column('first_touch_entity_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('entities.id'), nullable=True),

        # Last touch (updated on each touchpoint)
        sa.Column('last_touch_source', sa.String(), nullable=True),
        sa.Column('last_touch_medium', sa.String(), nullable=True),
        sa.Column('last_touch_campaign', sa.String(), nullable=True),
        sa.Column('last_touch_entity_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('entities.id'), nullable=True),

        # Journey state
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('touchpoint_count', sa.Integer(), server_default='0'),

        # Conversion tracking
        sa.Column('total_orders', sa.Integer(), server_default='0'),
        sa.Column('total_revenue', sa.Numeric(12, 2), server_default='0'),
        sa.Column('first_order_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_order_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),

        # Unique constraint: one journey per visitor per workspace
        sa.UniqueConstraint('workspace_id', 'visitor_id', name='uq_journey_visitor'),
    )

    # Indexes for customer_journeys
    op.create_index('ix_journeys_workspace', 'customer_journeys', ['workspace_id'])
    op.create_index('ix_journeys_visitor', 'customer_journeys',
                    ['workspace_id', 'visitor_id'])
    # Partial index for checkout_token lookup
    op.create_index(
        'ix_journeys_checkout',
        'customer_journeys',
        ['workspace_id', 'checkout_token'],
        postgresql_where=sa.text('checkout_token IS NOT NULL')
    )
    # Partial index for email lookup
    op.create_index(
        'ix_journeys_email',
        'customer_journeys',
        ['workspace_id', 'customer_email'],
        postgresql_where=sa.text('customer_email IS NOT NULL')
    )

    # =========================================================================
    # STEP 5: Create journey_touchpoints table
    # =========================================================================
    # WHAT: Each marketing interaction (UTMs, click IDs)
    # WHY: Attribution models need all touchpoints to determine credit
    op.create_table(
        'journey_touchpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('journey_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('customer_journeys.id', ondelete='CASCADE'),
                  nullable=False),

        # Event info
        sa.Column('event_type', sa.String(), nullable=False),

        # Attribution params
        sa.Column('utm_source', sa.String(), nullable=True),
        sa.Column('utm_medium', sa.String(), nullable=True),
        sa.Column('utm_campaign', sa.String(), nullable=True),
        sa.Column('utm_content', sa.String(), nullable=True),
        sa.Column('utm_term', sa.String(), nullable=True),
        sa.Column('fbclid', sa.String(), nullable=True),
        sa.Column('gclid', sa.String(), nullable=True),
        sa.Column('ttclid', sa.String(), nullable=True),

        # Resolved entity (if matched)
        sa.Column('entity_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('entities.id'), nullable=True),
        sa.Column('provider', sa.String(), nullable=True),

        # Context
        sa.Column('landing_page', sa.String(), nullable=True),
        sa.Column('referrer', sa.String(), nullable=True),

        sa.Column('touched_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Indexes for journey_touchpoints
    op.create_index('ix_touchpoints_journey', 'journey_touchpoints',
                    ['journey_id', 'touched_at'])
    # Partial indexes for click ID lookups
    op.create_index(
        'ix_touchpoints_gclid',
        'journey_touchpoints',
        ['gclid'],
        postgresql_where=sa.text('gclid IS NOT NULL')
    )
    op.create_index(
        'ix_touchpoints_fbclid',
        'journey_touchpoints',
        ['fbclid'],
        postgresql_where=sa.text('fbclid IS NOT NULL')
    )

    # =========================================================================
    # STEP 6: Create attributions table
    # =========================================================================
    # WHAT: Final attribution records linking orders to entities
    # WHY: Stores the result of attribution processing for fast dashboard queries
    op.create_table(
        'attributions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('workspaces.id'), nullable=False),

        # Links
        sa.Column('journey_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('customer_journeys.id'), nullable=True),
        sa.Column('shopify_order_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('shopify_orders.id'), nullable=True),

        # Attribution result
        sa.Column('entity_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('entities.id'), nullable=True),
        # Provider: meta, google, tiktok, direct, organic, unknown
        sa.Column('provider', sa.String(), nullable=False),
        # Entity level: campaign, adset, ad (NULL if no entity match)
        sa.Column('entity_level', sa.String(), nullable=True),

        # Match info
        # match_type: gclid, utm_campaign, utm_content, fbclid, utm_source, referrer, none
        sa.Column('match_type', sa.String(), nullable=False),
        # confidence: high, medium, low, none
        sa.Column('confidence', sa.String(), nullable=False),
        sa.Column('attribution_model', sa.String(), nullable=False,
                  server_default='last_click'),
        sa.Column('attribution_window_days', sa.Integer(), server_default='30'),

        # Revenue (stored in order's original currency)
        sa.Column('attributed_revenue', sa.Numeric(12, 2), nullable=True),
        # For multi-touch (0.0-1.0)
        sa.Column('attribution_credit', sa.Numeric(5, 4), server_default='1.0'),
        sa.Column('currency', sa.String(), nullable=False, server_default='USD'),

        # Timestamps
        sa.Column('order_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attributed_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),

        # Idempotency: One attribution per order per model
        sa.UniqueConstraint('shopify_order_id', 'attribution_model',
                            name='uq_attribution_order_model'),
    )

    # Indexes for attributions
    op.create_index('ix_attributions_workspace', 'attributions',
                    ['workspace_id', 'order_created_at'])
    op.create_index('ix_attributions_entity', 'attributions',
                    ['entity_id', 'order_created_at'])
    op.create_index('ix_attributions_provider', 'attributions',
                    ['workspace_id', 'provider', 'order_created_at'])


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign keys)
    op.drop_table('attributions')
    op.drop_table('journey_touchpoints')
    op.drop_table('customer_journeys')
    op.drop_table('pixel_events')

    # Drop added columns
    op.drop_index('ix_shopify_orders_checkout_token', table_name='shopify_orders')
    op.drop_column('shopify_orders', 'checkout_token')

    op.drop_column('connections', 'web_pixel_id')
