"""Add is_superuser field to users table.

Revision ID: 20250107_superuser
Revises: edfe2eb266dc
Create Date: 2025-01-07

WHAT: Add is_superuser Boolean field to users table
WHY: Enable platform-level admin access for user/workspace management
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20250107_superuser"
down_revision = "20251217_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_superuser column with default False
    op.add_column(
        "users",
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("users", "is_superuser")
