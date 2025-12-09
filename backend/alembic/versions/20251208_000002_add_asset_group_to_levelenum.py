"""Add asset_group to levelenum for PMax campaigns

Revision ID: 20251208_000002
Revises: 20251208_000001
Create Date: 2025-12-08

WHAT:
    Adds 'asset_group' value to the PostgreSQL levelenum type.

WHY:
    Performance Max (PMax) campaigns in Google Ads don't use traditional
    ad_groups/ads hierarchy. Instead they use asset_groups which contain
    the creative assets. We need this level to capture PMax metrics properly.

REFERENCES:
    - app/models.py:LevelEnum (Python enum already has asset_group)
    - app/services/google_sync_service.py (creates asset_group entities)
    - app/services/snapshot_sync_service.py (fetches asset_group metrics)
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '20251208_000002'
down_revision = '20251208_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'asset_group' to the levelenum PostgreSQL enum type
    # PostgreSQL requires ALTER TYPE to add new enum values
    op.execute("ALTER TYPE levelenum ADD VALUE IF NOT EXISTS 'asset_group'")


def downgrade() -> None:
    # NOTE: PostgreSQL doesn't support removing enum values directly.
    # To truly downgrade, you'd need to:
    # 1. Create a new enum without 'asset_group'
    # 2. Update all columns using the enum
    # 3. Drop the old enum
    # 4. Rename the new enum
    #
    # For safety, we leave the enum value in place during downgrade.
    # The Python code will simply not use it.
    pass
