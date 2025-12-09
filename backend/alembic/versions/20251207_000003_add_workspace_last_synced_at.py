"""Add last_synced_at to workspaces table

Revision ID: 20251207_000003
Revises: 20251207_000002
Create Date: 2025-12-07

WHAT:
    Adds last_synced_at column to workspaces table for tracking sync status.

WHY:
    - Dashboard UI needs to show "Last updated X min ago"
    - Provides workspace-level sync visibility
    - Updated by snapshot_sync_service after successful syncs
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251207_000003'
down_revision = '20251207_000002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add last_synced_at column to workspaces."""
    op.add_column(
        'workspaces',
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Remove last_synced_at column from workspaces."""
    op.drop_column('workspaces', 'last_synced_at')
