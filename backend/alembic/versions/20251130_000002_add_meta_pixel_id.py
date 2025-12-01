"""Add meta_pixel_id to connections.

Revision ID: 20251130_000002
Revises: 20251130_000001
Create Date: 2025-11-30

WHAT: Adds meta_pixel_id column to connections table
WHY: Required for Meta CAPI integration to send purchase events
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251130_000002'
down_revision = '20251130_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add meta_pixel_id column to connections."""
    op.add_column(
        'connections',
        sa.Column('meta_pixel_id', sa.String(), nullable=True)
    )


def downgrade() -> None:
    """Remove meta_pixel_id column from connections."""
    op.drop_column('connections', 'meta_pixel_id')
