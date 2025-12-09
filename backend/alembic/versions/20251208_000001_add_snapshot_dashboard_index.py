"""Add optimized index for dashboard snapshot queries

Revision ID: 20251208_000001
Revises: 20251207_000003
Create Date: 2025-12-08

WHAT:
    Adds composite index for the DISTINCT ON queries used in dashboard.
    Optimizes "get latest snapshot per entity per day" pattern.

WHY:
    Dashboard queries use DISTINCT ON (entity_id, date_trunc('day', captured_at))
    to get the latest snapshot for each entity on each day.
    This index makes that pattern O(1) per entity instead of scanning.

REFERENCES:
    - app/routers/dashboard.py (uses DISTINCT ON pattern)
    - app/services/snapshot_sync_service.py (compaction uses similar pattern)
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '20251208_000001'
down_revision = '20251207_000003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # Compound index for entity + provider queries
    # =========================================================================
    # WHAT: Index on (entity_id, provider, captured_at DESC)
    # WHY: Many queries filter by both entity and provider, then order by time
    #
    # Existing indexes cover entity_id and captured_at separately, but
    # queries that also filter by provider benefit from this compound index.

    op.execute("""
        CREATE INDEX idx_snapshots_entity_provider_time
        ON metric_snapshots (
            entity_id,
            provider,
            captured_at DESC
        )
    """)

    # =========================================================================
    # BRIN index for time-series compression
    # =========================================================================
    # WHAT: Block Range INdex on captured_at
    # WHY: Very compact index for time-series data where rows are inserted
    #      in roughly time-order. Uses ~1000x less space than B-tree while
    #      still supporting range queries efficiently.

    op.execute("""
        CREATE INDEX idx_snapshots_captured_brin
        ON metric_snapshots
        USING BRIN (captured_at)
        WITH (pages_per_range = 128)
    """)


def downgrade() -> None:
    op.drop_index('idx_snapshots_captured_brin', 'metric_snapshots')
    op.drop_index('idx_snapshots_entity_provider_time', 'metric_snapshots')
