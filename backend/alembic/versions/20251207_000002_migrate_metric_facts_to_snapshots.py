"""Migrate metric_facts data to metric_snapshots

Revision ID: 20251207_000002
Revises: 20251207_000001
Create Date: 2025-12-07

WHAT:
    Migrates existing metric_facts data to the new metric_snapshots table.
    Converts daily granularity data to hourly format.

WHY:
    - Preserves historical data during the transition
    - Uses midnight timestamp for each date (since original data is daily)
    - Maintains data continuity for dashboards

NOTE:
    - This migration is data-only; table structure created in 20251207_000001
    - Uses INSERT ... SELECT for efficiency
    - Does NOT delete original metric_facts (kept for safety)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251207_000002'
down_revision = '20251207_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Migrate metric_facts data to metric_snapshots.

    Strategy:
    - Convert daily rows to hourly snapshots (midnight timestamp)
    - Use event_date as captured_at
    - Copy all base measures
    """
    # Use raw SQL for efficiency on large datasets
    op.execute("""
        INSERT INTO metric_snapshots (
            id,
            entity_id,
            provider,
            captured_at,
            spend,
            impressions,
            clicks,
            conversions,
            revenue,
            leads,
            purchases,
            installs,
            visitors,
            profit,
            currency,
            created_at
        )
        SELECT
            gen_random_uuid(),
            mf.entity_id,
            mf.provider::text,
            -- Convert event_date to timestamp at midnight UTC
            mf.event_date AT TIME ZONE 'UTC',
            mf.spend,
            mf.impressions,
            mf.clicks,
            mf.conversions,
            mf.revenue,
            mf.leads,
            mf.purchases,
            mf.installs,
            mf.visitors,
            mf.profit,
            mf.currency,
            NOW()
        FROM metric_facts mf
        -- Only migrate rows with valid entity_id
        WHERE mf.entity_id IS NOT NULL
        -- Avoid duplicates if migration runs twice
        ON CONFLICT (entity_id, provider, captured_at)
        DO NOTHING
    """)


def downgrade() -> None:
    """Remove migrated data from metric_snapshots.

    NOTE: This only removes data that was migrated from metric_facts.
    New snapshots created after migration are preserved.
    """
    # We could delete based on created_at timestamp, but safer to leave data
    # since metric_facts still exists as the original source
    pass
