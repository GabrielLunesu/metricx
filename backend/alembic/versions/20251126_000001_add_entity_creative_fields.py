"""Add creative fields to entities (thumbnail_url, image_url, media_type)

Revision ID: 20251126_000001
Revises: b573f4f83461
Create Date: 2025-11-26 17:30:00.000000

Purpose:
    Adds creative image support to Entity model for displaying ad creatives
    in the QA system. Currently only Meta ads are supported for creative images.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251126_000001'
down_revision = 'b573f4f83461'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create MediaTypeEnum (use raw SQL with IF NOT EXISTS)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mediatypeenum AS ENUM ('image', 'video', 'carousel', 'unknown');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Add creative fields to entities table
    op.add_column('entities', sa.Column('thumbnail_url', sa.String(), nullable=True))
    op.add_column('entities', sa.Column('image_url', sa.String(), nullable=True))
    op.add_column('entities', sa.Column(
        'media_type',
        sa.Enum('image', 'video', 'carousel', 'unknown', name='mediatypeenum', create_type=False),
        nullable=True
    ))


def downgrade() -> None:
    op.drop_column('entities', 'media_type')
    op.drop_column('entities', 'image_url')
    op.drop_column('entities', 'thumbnail_url')

    # Drop enum type
    op.execute('DROP TYPE IF EXISTS mediatypeenum')
