"""add_user_profile_fields

Revision ID: 95e2fb15bec2
Revises: fe534aa60c90
Create Date: 2025-11-24 11:41:57.417623
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '95e2fb15bec2'
down_revision = 'fe534aa60c90'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('avatar_url', sa.String(), nullable=True))
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('users', sa.Column('verification_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_token_expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'reset_token_expires_at')
    op.drop_column('users', 'reset_token')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'avatar_url')



