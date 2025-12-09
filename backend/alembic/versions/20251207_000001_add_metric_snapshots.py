"""Add metric_snapshots table for 15-min granularity sync

Revision ID: 20251207_000001
Revises: 20251205_000001
Create Date: 2025-12-07

WHAT:
    Creates metric_snapshots table to replace metric_facts with finer granularity:
    - 15-min snapshots for today and yesterday
    - Hourly snapshots for older data (compacted daily)
    - Same base measures as metric_facts

WHY:
    Current system stores 1 row per entity per day, which:
    - Doesn't support intraday analytics
    - Doesn't allow real-time rules engine (stop-losses)
    - Never re-syncs for attribution corrections

    New system:
    - 15-min sync for fresh data (matches Meta's refresh rate)
    - Compaction to hourly after 2 days (storage efficiency)
    - Daily re-fetch of last 7 days (attribution corrections)

REFERENCES:
    - Original: app/models.py:MetricFact
    - Design doc: docs/architecture/unified-metrics.md
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251207_000001'
down_revision = '20251205_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # STEP 1: Create metric_snapshots table
    # =========================================================================
    # WHAT: New table for 15-min granularity ad metrics
    # WHY: Replaces metric_facts with finer time resolution

    op.create_table(
        'metric_snapshots',

        # Primary key
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),

        # Foreign keys
        sa.Column('entity_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('entities.id', ondelete='CASCADE'),
                  nullable=False, index=True),

        # Provider (meta, google, tiktok)
        sa.Column('provider', sa.String(20), nullable=False),

        # Timestamp of this snapshot
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),

        # Base measures (same as metric_facts)
        sa.Column('spend', sa.Numeric(18, 4), nullable=True),
        sa.Column('impressions', sa.BigInteger, nullable=True),
        sa.Column('clicks', sa.BigInteger, nullable=True),
        sa.Column('conversions', sa.Numeric(18, 4), nullable=True),
        sa.Column('revenue', sa.Numeric(18, 4), nullable=True),
        sa.Column('leads', sa.Numeric(18, 4), nullable=True),
        sa.Column('purchases', sa.Integer, nullable=True),
        sa.Column('installs', sa.Integer, nullable=True),
        sa.Column('visitors', sa.Integer, nullable=True),
        sa.Column('profit', sa.Numeric(18, 4), nullable=True),

        # Currency
        sa.Column('currency', sa.String(10), server_default='USD'),

        # Audit timestamp
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
    )

    # =========================================================================
    # STEP 2: Create unique constraint for deduplication
    # =========================================================================
    # WHAT: Ensure one snapshot per entity per provider per timestamp
    # WHY: UPSERT pattern needs this for conflict resolution

    op.create_unique_constraint(
        'uq_metric_snapshots_entity_provider_time',
        'metric_snapshots',
        ['entity_id', 'provider', 'captured_at']
    )

    # =========================================================================
    # STEP 3: Create indexes for common query patterns
    # =========================================================================

    # Index for "get latest snapshot for entity" queries
    # WHY: Rules engine needs fast lookup of current values
    op.create_index(
        'idx_snapshots_entity_captured_desc',
        'metric_snapshots',
        ['entity_id', sa.text('captured_at DESC')]
    )

    # Index for date-based queries (timeseries, compaction)
    # WHY: Compaction job needs to find all snapshots for a specific date
    # NOTE: Using raw SQL with timezone cast to make it IMMUTABLE
    op.execute("""
        CREATE INDEX idx_snapshots_captured_date
        ON metric_snapshots (((captured_at AT TIME ZONE 'UTC')::date))
    """)

    # Index for provider filtering
    # WHY: Dashboard often filters by provider (meta vs google)
    op.create_index(
        'idx_snapshots_provider',
        'metric_snapshots',
        ['provider']
    )

    # Composite index for common dashboard query pattern
    # WHY: "Get all snapshots for entity in date range" is the most common query
    op.create_index(
        'idx_snapshots_entity_date_range',
        'metric_snapshots',
        ['entity_id', 'captured_at']
    )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_snapshots_entity_date_range', 'metric_snapshots')
    op.drop_index('idx_snapshots_provider', 'metric_snapshots')
    op.drop_index('idx_snapshots_captured_date', 'metric_snapshots')
    op.drop_index('idx_snapshots_entity_captured_desc', 'metric_snapshots')

    # Drop constraint
    op.drop_constraint('uq_metric_snapshots_entity_provider_time', 'metric_snapshots')

    # Drop table
    op.drop_table('metric_snapshots')
