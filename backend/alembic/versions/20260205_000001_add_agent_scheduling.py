"""Add scheduling and multi-channel notification support to agents

Revision ID: 20260205_000001
Revises: 20260122_000001
Create Date: 2026-02-05

WHAT:
    Adds scheduling capabilities and multi-channel notification support to agents:
    - schedule_type: 'realtime', 'daily', 'weekly', 'monthly'
    - schedule_config: JSON with hour, minute, timezone, day_of_week, day_of_month
    - last_scheduled_run_at: Track when scheduled agent last ran
    - condition_required: Allow "always send" reports without condition evaluation
    - date_range_type: Specify metrics date range ('yesterday', 'last_7_days', etc.)
    - 'notify' action type for multi-channel notifications

WHY:
    Users need scheduled reports (daily at 1am, weekly summaries) and multi-channel
    notifications (Email, Slack, Webhook) for their monitoring agents. This extends
    the existing real-time evaluation system to support time-based triggers.

REFERENCES:
    - Scheduled Reports & Multi-Channel Notifications Plan
    - AgentNotificationService extension for Slack/webhook
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260205_000001'
down_revision = '20260122_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # STEP 1: Add 'notify' to actiontypeenum
    # =========================================================================
    # WHAT: Add new action type for multi-channel notifications
    # WHY: Support Email, Slack, and Webhook in a single unified action
    op.execute("ALTER TYPE actiontypeenum ADD VALUE IF NOT EXISTS 'notify'")

    # =========================================================================
    # STEP 2: Add scheduling columns to agents table
    # =========================================================================
    # WHAT: Columns for schedule configuration
    # WHY: Allow agents to run on a schedule (daily, weekly, monthly) instead of real-time

    # schedule_type: When should this agent evaluate?
    # 'realtime' = every 15 min (existing behavior)
    # 'daily', 'weekly', 'monthly' = at specific time
    op.add_column(
        'agents',
        sa.Column('schedule_type', sa.String(20), nullable=False, server_default='realtime')
    )

    # schedule_config: JSON with scheduling details
    # {"hour": 1, "minute": 0, "timezone": "America/New_York", "day_of_week": 0}
    op.add_column(
        'agents',
        sa.Column('schedule_config', sa.JSON(), nullable=True)
    )

    # last_scheduled_run_at: Track when scheduled agent last ran
    # Used to determine if schedule time has passed
    op.add_column(
        'agents',
        sa.Column('last_scheduled_run_at', sa.DateTime(timezone=True), nullable=True)
    )

    # condition_required: Must condition be met to trigger?
    # False = "always send" mode - trigger at schedule time regardless of condition
    op.add_column(
        'agents',
        sa.Column('condition_required', sa.Boolean(), nullable=False, server_default='true')
    )

    # date_range_type: What date range to use for metrics
    # 'rolling_24h', 'today', 'yesterday', 'last_7_days', 'last_30_days'
    op.add_column(
        'agents',
        sa.Column('date_range_type', sa.String(20), nullable=True)
    )

    # =========================================================================
    # STEP 3: Add index for scheduled agent queries
    # =========================================================================
    # WHAT: Index for finding agents by schedule_type
    # WHY: Cron job needs to efficiently find all scheduled agents
    op.create_index(
        'ix_agents_schedule_type',
        'agents',
        ['workspace_id', 'schedule_type', 'status']
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_agents_schedule_type', table_name='agents')

    # Drop columns (reverse order of creation)
    op.drop_column('agents', 'date_range_type')
    op.drop_column('agents', 'condition_required')
    op.drop_column('agents', 'last_scheduled_run_at')
    op.drop_column('agents', 'schedule_config')
    op.drop_column('agents', 'schedule_type')

    # Note: Cannot remove 'notify' from enum easily in PostgreSQL
    # Would need to recreate the enum which is complex
