"""add_tracking_params_to_entity

WHAT: Adds tracking_params JSON column to entities table
WHY: Store URL tracking configuration from ad platforms for proactive UTM detection
REFERENCES: docs/living-docs/FRONTEND_REFACTOR_PLAN.md

Revision ID: 91de05b5bf49
Revises: 20251201_000001
Create Date: 2025-12-02 19:52:56.547470
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '91de05b5bf49'
down_revision = '20251201_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tracking_params JSON column to store URL tracking configuration
    # For Meta: url_tags field from ads
    # For Google: tracking_url_template and final_url_suffix
    op.add_column(
        'entities',
        sa.Column('tracking_params', postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('entities', 'tracking_params')



