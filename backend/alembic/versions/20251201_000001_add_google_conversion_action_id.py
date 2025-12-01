"""Add google_conversion_action_id to connections.

Revision ID: 20251201_000001
Revises: 20251130_000002
Create Date: 2025-12-01

WHAT: Adds google_conversion_action_id column to connections table
WHY: Required for Google Offline Conversions to upload purchase events
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251201_000001'
down_revision = '20251130_000002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add google_conversion_action_id column to connections."""
    op.add_column(
        'connections',
        sa.Column('google_conversion_action_id', sa.String(), nullable=True)
    )


def downgrade() -> None:
    """Remove google_conversion_action_id column from connections."""
    op.drop_column('connections', 'google_conversion_action_id')
