"""Add billing_tier for free/starter tier distinction

Revision ID: 20251217_000001
Revises: 20251215_000001
Create Date: 2025-12-17

WHAT:
    Adds billing_tier enum and column to workspaces table.
    - billing_tier: "free" (limited features) or "starter" (full features)

WHY:
    Implements free tier with restricted features:
    - Free: 1 ad account, dashboard only, no team invites
    - Starter: Unlimited ad accounts, all pages, team invites up to 10

    This is separate from billing_status (payment state) and billing_plan (monthly/annual).

REFERENCES:
    - backend/app/models.py (BillingPlanEnum, Workspace.billing_tier)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251217_000001'
down_revision = '20251215_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create billing_tier enum type
    billing_tier_enum = postgresql.ENUM(
        'free', 'starter',
        name='billingplanenum'
    )
    billing_tier_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add billing_tier column to workspaces table
    op.add_column('workspaces', sa.Column(
        'billing_tier',
        sa.Enum('free', 'starter', name='billingplanenum'),
        server_default='free',
        nullable=False
    ))

    # 3. Migrate existing data:
    # - Workspaces with polar_subscription_id → "starter" (they've paid)
    # - Workspaces without → "free"
    # Note: Need to cast text to enum type explicitly for PostgreSQL
    op.execute("""
        UPDATE workspaces
        SET billing_tier = CASE
            WHEN polar_subscription_id IS NOT NULL THEN 'starter'::billingplanenum
            ELSE 'free'::billingplanenum
        END
    """)


def downgrade() -> None:
    # Drop column
    op.drop_column('workspaces', 'billing_tier')

    # Drop enum type
    billing_tier_enum = postgresql.ENUM(
        'free', 'starter',
        name='billingplanenum'
    )
    billing_tier_enum.drop(op.get_bind(), checkfirst=True)
