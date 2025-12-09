"""add_product_level_enum

Revision ID: 20251205_000001
Revises: edfe2eb266dc
Create Date: 2025-12-05

WHAT: Add 'product' value to LevelEnum for Shopping/PMax product-level data
WHY: Shopping campaigns use product groups instead of ads, and PMax retail
     campaigns have product-level performance data. We need to store this
     at the product level for accurate metrics and top performer analysis.

REFERENCES:
- Google Ads API: shopping_performance_view
- Google Ads API: asset_group_product_group_view
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '20251205_000001'
down_revision = 'edfe2eb266dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add 'product' to levelenum before 'unknown'.

    PostgreSQL allows adding new values to enum types with ALTER TYPE.
    The 'BEFORE' clause ensures proper ordering.
    """
    op.execute("ALTER TYPE levelenum ADD VALUE IF NOT EXISTS 'product' BEFORE 'unknown'")


def downgrade() -> None:
    """Downgrade not supported for enum value removal.

    PostgreSQL doesn't easily support removing enum values without
    recreating the entire type. Since 'product' is additive and
    backwards-compatible, we leave it in place on downgrade.
    """
    # Note: Removing enum values in PostgreSQL requires:
    # 1. Creating a new enum type without the value
    # 2. Updating all columns to use the new type
    # 3. Dropping the old type
    # This is destructive and not recommended for production.
    pass
