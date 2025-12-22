"""Add workspace business profile fields for onboarding

Revision ID: 20251214_000001
Revises: a7b48d313327
Create Date: 2025-12-14

WHAT:
    Adds business profile fields to workspaces table for onboarding flow.
    Includes domain, niche, target_markets, brand_voice, and onboarding tracking.

WHY:
    New users go through onboarding to provide business context.
    This context is used by the Copilot for personalized responses.
    Existing users are marked as onboarding_completed=true to skip onboarding.

REFERENCES:
    - backend/app/models.py:Workspace (business profile fields)
    - backend/app/routers/onboarding.py (endpoints)
    - backend/app/agent/nodes.py (copilot context injection)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251214_000001'
down_revision = 'a7b48d313327'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Business profile fields
    op.add_column('workspaces', sa.Column('domain', sa.String(), nullable=True))
    op.add_column('workspaces', sa.Column('domain_description', sa.Text(), nullable=True))
    op.add_column('workspaces', sa.Column('niche', sa.String(), nullable=True))
    op.add_column('workspaces', sa.Column('target_markets', postgresql.JSON(), nullable=True))
    op.add_column('workspaces', sa.Column('brand_voice', sa.String(), nullable=True))
    op.add_column('workspaces', sa.Column('business_size', sa.String(), nullable=True))

    # Onboarding tracking
    op.add_column('workspaces', sa.Column('onboarding_completed', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('workspaces', sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('workspaces', sa.Column('intended_ad_providers', postgresql.JSON(), nullable=True))

    # Mark ALL existing workspaces as onboarding_completed=true
    # WHY: Existing users should NOT be forced through onboarding
    op.execute("UPDATE workspaces SET onboarding_completed = true")


def downgrade() -> None:
    op.drop_column('workspaces', 'intended_ad_providers')
    op.drop_column('workspaces', 'onboarding_completed_at')
    op.drop_column('workspaces', 'onboarding_completed')
    op.drop_column('workspaces', 'business_size')
    op.drop_column('workspaces', 'brand_voice')
    op.drop_column('workspaces', 'target_markets')
    op.drop_column('workspaces', 'niche')
    op.drop_column('workspaces', 'domain_description')
    op.drop_column('workspaces', 'domain')
