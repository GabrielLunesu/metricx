"""Add clerk_id to users table for Clerk authentication.

WHAT: Adds clerk_id column to users table for Clerk identity linking
WHY: Migrating from custom JWT auth to Clerk authentication
REFERENCES: docs/ARCHITECTURE.md (Security section)

Revision ID: 20251209_000001_add_clerk_id
Revises: 20251208_000002
Create Date: 2025-12-09
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251209_000001_add_clerk_id'
down_revision = '20251208_000002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add clerk_id column with unique index."""
    # Add clerk_id column (nullable initially for existing users)
    op.add_column(
        'users',
        sa.Column('clerk_id', sa.String(), nullable=True)
    )

    # Create unique index for fast lookups
    op.create_index(
        'ix_users_clerk_id',
        'users',
        ['clerk_id'],
        unique=True
    )


def downgrade() -> None:
    """Remove clerk_id column and index."""
    op.drop_index('ix_users_clerk_id', table_name='users')
    op.drop_column('users', 'clerk_id')
