"""add_trial_started_at

Revision ID: 20260113_000001
Revises: a7b48d313327
Create Date: 2026-01-13

WHAT:
    Adds trial_started_at column to workspaces table for tracking when
    a workspace's 7-day trial period began.

WHY:
    Converting from freemium to trial-based billing. New users get 7-day
    full access trial, then downgrade to free tier. Need to track trial
    start for expiry calculation and to prevent re-trials.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260113_000001'
down_revision = '20250107_superuser'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add trial_started_at column to workspaces."""
    op.add_column(
        'workspaces',
        sa.Column('trial_started_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Remove trial_started_at column from workspaces."""
    op.drop_column('workspaces', 'trial_started_at')
