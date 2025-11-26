"""Add QA feedback table for self-learning

Revision ID: b573f4f83461
Revises: 20251124_000001
Create Date: 2025-11-26 13:46:34.685785
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b573f4f83461'
down_revision = '20251124_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create FeedbackTypeEnum (use raw SQL with IF NOT EXISTS)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE feedbacktypeenum AS ENUM ('accuracy', 'relevance', 'visualization', 'completeness', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Add answer_text column to qa_query_logs (for feedback tracking)
    # Check if column exists first
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='qa_query_logs' AND column_name='answer_text'
    """))
    if not result.fetchone():
        op.add_column('qa_query_logs', sa.Column('answer_text', sa.Text(), nullable=True))

    # Create qa_feedback table if not exists
    result = conn.execute(sa.text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_name='qa_feedback'
    """))
    if not result.fetchone():
        op.create_table('qa_feedback',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('query_log_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('rating', sa.Integer(), nullable=False),
            sa.Column('feedback_type', postgresql.ENUM('accuracy', 'relevance', 'visualization', 'completeness', 'other', name='feedbacktypeenum', create_type=False), nullable=True),
            sa.Column('comment', sa.Text(), nullable=True),
            sa.Column('corrected_answer', sa.Text(), nullable=True),
            sa.Column('is_few_shot_example', sa.Boolean(), nullable=True, default=False),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['query_log_id'], ['qa_query_logs.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    op.drop_table('qa_feedback')
    op.drop_column('qa_query_logs', 'answer_text')

    # Drop enum type
    op.execute('DROP TYPE IF EXISTS feedbacktypeenum')



