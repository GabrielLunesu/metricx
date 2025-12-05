"""add_performance_indexes

Revision ID: edfe2eb266dc
Revises: 91de05b5bf49
Create Date: 2025-12-03 13:39:56.191477

WHAT: Add database indexes for frequently queried columns
WHY: Every query filters by workspace_id but there were no indexes,
     causing full table scans. This was identified as a P0 issue causing
     app-wide slowness and crashes under load.

IMPACT:
- Entity queries: workspace_id filter (30+ occurrences in codebase)
- MetricFact queries: entity_id + event_date filters
- Attribution queries: workspace_id + attributed_at filters
- ShopifyOrder queries: workspace_id + order_created_at filters

REFERENCES:
- docs/PERFORMANCE_INVESTIGATION.md
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'edfe2eb266dc'
down_revision = '91de05b5bf49'
branch_labels = None
depends_on = None


def create_index_if_not_exists(index_name: str, table_name: str, columns: list[str]):
    """Create index only if it doesn't already exist.

    WHY: Some indexes may have been created manually or in a previous partial run.
    Using IF NOT EXISTS prevents migration failures on re-runs.
    """
    columns_str = ', '.join(columns)
    op.execute(text(
        f'CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns_str})'
    ))


def drop_index_if_exists(index_name: str, table_name: str):
    """Drop index only if it exists."""
    op.execute(text(
        f'DROP INDEX IF EXISTS {index_name}'
    ))


def upgrade() -> None:
    # ==========================================================================
    # ENTITIES TABLE INDEXES
    # ==========================================================================
    # Most queries filter by workspace_id (30+ occurrences in codebase)
    create_index_if_not_exists(
        'ix_entities_workspace_id',
        'entities',
        ['workspace_id']
    )

    # Common filter: workspace_id + level (e.g., get all campaigns for workspace)
    create_index_if_not_exists(
        'ix_entities_workspace_level',
        'entities',
        ['workspace_id', 'level']
    )

    # Connection lookups for sync operations
    create_index_if_not_exists(
        'ix_entities_connection_id',
        'entities',
        ['connection_id']
    )

    # Parent-child traversal for hierarchy queries
    create_index_if_not_exists(
        'ix_entities_parent_id',
        'entities',
        ['parent_id']
    )

    # ==========================================================================
    # METRIC_FACTS TABLE INDEXES
    # ==========================================================================
    # All metric queries join on entity_id
    create_index_if_not_exists(
        'ix_metric_facts_entity_id',
        'metric_facts',
        ['entity_id']
    )

    # Date range queries are common (last 7 days, last 30 days)
    create_index_if_not_exists(
        'ix_metric_facts_event_date',
        'metric_facts',
        ['event_date']
    )

    # Composite index for the most common query pattern: entity + date range
    create_index_if_not_exists(
        'ix_metric_facts_entity_date',
        'metric_facts',
        ['entity_id', 'event_date']
    )

    # ==========================================================================
    # SHOPIFY_ORDERS TABLE INDEXES
    # ==========================================================================
    # Dashboard KPIs query by workspace + date
    create_index_if_not_exists(
        'ix_shopify_orders_workspace_id',
        'shopify_orders',
        ['workspace_id']
    )

    create_index_if_not_exists(
        'ix_shopify_orders_workspace_date',
        'shopify_orders',
        ['workspace_id', 'order_created_at']
    )

    # ==========================================================================
    # ATTRIBUTIONS TABLE INDEXES
    # ==========================================================================
    # Attribution queries filter by workspace + date
    create_index_if_not_exists(
        'ix_attributions_workspace_id',
        'attributions',
        ['workspace_id']
    )

    create_index_if_not_exists(
        'ix_attributions_workspace_date',
        'attributions',
        ['workspace_id', 'attributed_at']
    )

    # ==========================================================================
    # CONNECTIONS TABLE INDEXES
    # ==========================================================================
    # Frequent lookups by workspace
    create_index_if_not_exists(
        'ix_connections_workspace_id',
        'connections',
        ['workspace_id']
    )

    # ==========================================================================
    # PNLS TABLE INDEXES
    # ==========================================================================
    # P&L queries by entity + date
    create_index_if_not_exists(
        'ix_pnls_entity_id',
        'pnls',
        ['entity_id']
    )

    create_index_if_not_exists(
        'ix_pnls_entity_date',
        'pnls',
        ['entity_id', 'event_date']
    )


def downgrade() -> None:
    # Drop all indexes in reverse order (using IF EXISTS for safety)
    drop_index_if_exists('ix_pnls_entity_date', 'pnls')
    drop_index_if_exists('ix_pnls_entity_id', 'pnls')
    drop_index_if_exists('ix_connections_workspace_id', 'connections')
    drop_index_if_exists('ix_attributions_workspace_date', 'attributions')
    drop_index_if_exists('ix_attributions_workspace_id', 'attributions')
    drop_index_if_exists('ix_shopify_orders_workspace_date', 'shopify_orders')
    drop_index_if_exists('ix_shopify_orders_workspace_id', 'shopify_orders')
    drop_index_if_exists('ix_metric_facts_entity_date', 'metric_facts')
    drop_index_if_exists('ix_metric_facts_event_date', 'metric_facts')
    drop_index_if_exists('ix_metric_facts_entity_id', 'metric_facts')
    drop_index_if_exists('ix_entities_parent_id', 'entities')
    drop_index_if_exists('ix_entities_connection_id', 'entities')
    drop_index_if_exists('ix_entities_workspace_level', 'entities')
    drop_index_if_exists('ix_entities_workspace_id', 'entities')



