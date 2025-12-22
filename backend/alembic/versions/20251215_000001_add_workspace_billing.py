"""Add workspace billing fields and Polar integration tables

Revision ID: 20251215_000001
Revises: 20251214_000001
Create Date: 2025-12-15

WHAT:
    Adds per-workspace billing fields and Polar integration tables:
    - billing_status enum and column on workspaces
    - billing_plan, polar_subscription_id, polar_customer_id on workspaces
    - trial_end, current_period_start, current_period_end timestamps
    - pending_since for pending workspace cap enforcement
    - polar_checkout_mappings table (checkout_id → workspace lookup)
    - polar_webhook_events table (idempotency)

WHY:
    Implements per-workspace billing with Polar. Each workspace requires its own
    subscription (Monthly $79 / Annual $569). Access to /onboarding and /dashboard
    is gated by billing_status: allowed if trialing/active, blocked otherwise.

REFERENCES:
    - openspec/changes/add-polar-workspace-billing/proposal.md
    - openspec/changes/add-polar-workspace-billing/design.md
    - backend/app/models.py (BillingStatusEnum, Workspace, PolarCheckoutMapping, PolarWebhookEvent)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251215_000001'
down_revision = '20251214_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create billing_status enum type
    billing_status_enum = postgresql.ENUM(
        'locked', 'trialing', 'active', 'canceled', 'past_due', 'incomplete', 'revoked',
        name='billingstatusenum'
    )
    billing_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add billing columns to workspaces table
    op.add_column('workspaces', sa.Column(
        'billing_status',
        sa.Enum('locked', 'trialing', 'active', 'canceled', 'past_due', 'incomplete', 'revoked', name='billingstatusenum'),
        server_default='locked',
        nullable=False
    ))
    op.add_column('workspaces', sa.Column('billing_plan', sa.String(), nullable=True))
    op.add_column('workspaces', sa.Column('polar_subscription_id', sa.String(), nullable=True))
    op.add_column('workspaces', sa.Column('polar_customer_id', sa.String(), nullable=True))
    op.add_column('workspaces', sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column('workspaces', sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('workspaces', sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column('workspaces', sa.Column('pending_since', sa.DateTime(timezone=True), nullable=True))

    # 3. Add unique constraint on polar_subscription_id
    op.create_unique_constraint('uq_workspaces_polar_subscription_id', 'workspaces', ['polar_subscription_id'])

    # 4. Create polar_checkout_mappings table
    op.create_table(
        'polar_checkout_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('polar_checkout_id', sa.String(), nullable=False, unique=True),
        sa.Column('requested_plan', sa.String(), nullable=False),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(), server_default='pending'),
        sa.Column('polar_subscription_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_polar_checkout_mappings_polar_checkout_id', 'polar_checkout_mappings', ['polar_checkout_id'])

    # 5. Create polar_webhook_events table
    op.create_table(
        'polar_webhook_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_key', sa.String(), nullable=False, unique=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('polar_data_id', sa.String(), nullable=True),
        sa.Column('payload_json', postgresql.JSON(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('processing_result', sa.String(), server_default='success'),
    )
    op.create_index('ix_polar_webhook_events_event_key', 'polar_webhook_events', ['event_key'])

    # 6. Mark ALL existing workspaces as 'active' to grandfather them in
    # WHY: Existing workspaces should continue to have access during migration
    op.execute("UPDATE workspaces SET billing_status = 'active'")


def downgrade() -> None:
    # Drop tables
    op.drop_index('ix_polar_webhook_events_event_key', table_name='polar_webhook_events')
    op.drop_table('polar_webhook_events')

    op.drop_index('ix_polar_checkout_mappings_polar_checkout_id', table_name='polar_checkout_mappings')
    op.drop_table('polar_checkout_mappings')

    # Drop columns from workspaces
    op.drop_constraint('uq_workspaces_polar_subscription_id', 'workspaces', type_='unique')
    op.drop_column('workspaces', 'pending_since')
    op.drop_column('workspaces', 'current_period_end')
    op.drop_column('workspaces', 'current_period_start')
    op.drop_column('workspaces', 'trial_end')
    op.drop_column('workspaces', 'polar_customer_id')
    op.drop_column('workspaces', 'polar_subscription_id')
    op.drop_column('workspaces', 'billing_plan')
    op.drop_column('workspaces', 'billing_status')

    # Drop enum type
    billing_status_enum = postgresql.ENUM(
        'locked', 'trialing', 'active', 'canceled', 'past_due', 'incomplete', 'revoked',
        name='billingstatusenum'
    )
    billing_status_enum.drop(op.get_bind(), checkfirst=True)
