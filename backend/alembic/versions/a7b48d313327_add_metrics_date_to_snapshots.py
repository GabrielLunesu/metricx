"""add_metrics_date_to_snapshots

Revision ID: a7b48d313327
Revises: 20251211_000001
Create Date: 2025-12-14 11:50:37.143061

WHY:
    Ad platforms (Google, Meta) report metrics by calendar day in the account's
    configured timezone. Previously we tried to derive this from captured_at
    using timezone math, which caused day-boundary bugs.

    This migration adds an explicit metrics_date column that stores the date
    the data represents (directly from the API response), eliminating timezone
    confusion when querying "today" or "yesterday".
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b48d313327'
down_revision = '20251211_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add metrics_date column (nullable initially for existing data)
    op.add_column(
        'metric_snapshots',
        sa.Column('metrics_date', sa.Date(), nullable=True)
    )

    # Add index for efficient date-based queries
    op.create_index(
        'ix_metric_snapshots_metrics_date',
        'metric_snapshots',
        ['metrics_date']
    )

    # Backfill existing data: extract date from captured_at
    # NOTE: This uses UTC date, which may be off by 1 day for some timezones.
    # A full re-sync is recommended after deployment to get correct dates.
    op.execute("""
        UPDATE metric_snapshots
        SET metrics_date = DATE(captured_at)
        WHERE metrics_date IS NULL
    """)


def downgrade() -> None:
    op.drop_index('ix_metric_snapshots_metrics_date', table_name='metric_snapshots')
    op.drop_column('metric_snapshots', 'metrics_date')



