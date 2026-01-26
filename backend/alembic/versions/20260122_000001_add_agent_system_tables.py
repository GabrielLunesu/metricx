"""Add Agent System tables (agents, agent_entity_states, agent_evaluation_events, agent_action_executions)

Revision ID: 20260122_000001
Revises: 20260113_000001
Create Date: 2026-01-22

WHAT:
    Creates tables for autonomous monitoring agents:
    - agents: Agent definitions with conditions, actions, and configuration
    - agent_entity_states: Per-entity state tracking for accumulation and triggers
    - agent_evaluation_events: Immutable event log of all evaluations
    - agent_action_executions: Record of executed actions with rollback capability

WHY:
    Agents are first-class entities that watch ad performance metrics,
    evaluate conditions over time, and take actions (notifications, budget
    scaling, campaign pausing). Full observability is critical for trust.

REFERENCES:
    - Agent System Implementation Plan
    - Event sourcing pattern for evaluation events
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20260122_000001'
down_revision = '20260113_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # STEP 1: Create Agent System enums
    # =========================================================================
    # WHAT: Create enums for agent status, scope type, state, trigger mode, etc.
    # WHY: Type-safe constraints for agent configuration

    # Agent status enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE agentstatusenum AS ENUM (
                'active', 'paused', 'draft', 'error', 'disabled'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Agent scope type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE agentscopetypeenum AS ENUM (
                'specific', 'filter', 'all'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Agent state enum (per-entity state machine)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE agentstateenum AS ENUM (
                'watching', 'accumulating', 'triggered', 'cooldown', 'error'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Trigger mode enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE triggermodeenum AS ENUM (
                'once', 'cooldown', 'continuous'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Accumulation unit enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE accumulationunitenum AS ENUM (
                'evaluations', 'hours', 'days'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Accumulation mode enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE accumulationmodeenum AS ENUM (
                'consecutive', 'within_window'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Result type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE agentresulttypeenum AS ENUM (
                'triggered', 'condition_met', 'condition_not_met', 'cooldown', 'error'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Action type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE actiontypeenum AS ENUM (
                'email', 'scale_budget', 'pause_campaign', 'webhook'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # =========================================================================
    # STEP 2: Create agents table
    # =========================================================================
    # WHAT: Main agent definition table
    # WHY: Stores agent identity, scope, conditions, actions, and configuration
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),

        # Identity
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Scope - what entities to watch
        sa.Column('scope_type', postgresql.ENUM(
            'specific', 'filter', 'all',
            name='agentscopetypeenum', create_type=False
        ), nullable=False),
        sa.Column('scope_config', postgresql.JSON(), nullable=False),

        # Condition - when to trigger (serialized condition tree)
        sa.Column('condition', postgresql.JSON(), nullable=False),

        # Accumulation config
        sa.Column('accumulation_required', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('accumulation_unit', postgresql.ENUM(
            'evaluations', 'hours', 'days',
            name='accumulationunitenum', create_type=False
        ), nullable=False, server_default='evaluations'),
        sa.Column('accumulation_mode', postgresql.ENUM(
            'consecutive', 'within_window',
            name='accumulationmodeenum', create_type=False
        ), nullable=False, server_default='consecutive'),
        sa.Column('accumulation_window', sa.Integer(), nullable=True),

        # Trigger behavior
        sa.Column('trigger_mode', postgresql.ENUM(
            'once', 'cooldown', 'continuous',
            name='triggermodeenum', create_type=False
        ), nullable=False, server_default='once'),
        sa.Column('cooldown_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('continuous_interval_minutes', sa.Integer(), nullable=True),

        # Actions (serialized action list)
        sa.Column('actions', postgresql.JSON(), nullable=False),

        # Safety configuration
        sa.Column('safety_config', postgresql.JSON(), nullable=True),

        # Status
        sa.Column('status', postgresql.ENUM(
            'active', 'paused', 'draft', 'error', 'disabled',
            name='agentstatusenum', create_type=False
        ), nullable=False, server_default='active'),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Metadata
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Cached stats
        sa.Column('last_evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_evaluations', sa.BigInteger(), server_default='0'),
        sa.Column('total_triggers', sa.BigInteger(), server_default='0'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),

        # Unique constraint
        sa.UniqueConstraint('workspace_id', 'name', name='uq_agent_workspace_name'),
    )

    # Indexes for agents
    op.create_index('ix_agents_workspace_status', 'agents', ['workspace_id', 'status'])
    op.create_index('ix_agents_workspace_id', 'agents', ['workspace_id'])
    op.create_index('ix_agents_created_by', 'agents', ['created_by'])

    # =========================================================================
    # STEP 3: Create agent_entity_states table
    # =========================================================================
    # WHAT: Per-entity state for accumulation and trigger tracking
    # WHY: Each entity an agent monitors needs independent state
    op.create_table(
        'agent_entity_states',
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.id', ondelete='CASCADE'), primary_key=True),

        # State machine
        sa.Column('state', postgresql.ENUM(
            'watching', 'accumulating', 'triggered', 'cooldown', 'error',
            name='agentstateenum', create_type=False
        ), nullable=False, server_default='watching'),

        # Accumulation tracking
        sa.Column('accumulation_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accumulation_count', sa.Integer(), server_default='0'),
        sa.Column('accumulation_history', postgresql.JSON(), server_default='[]'),

        # Trigger tracking
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trigger_count', sa.Integer(), server_default='0'),
        sa.Column('next_eligible_trigger_at', sa.DateTime(timezone=True), nullable=True),

        # Health tracking
        sa.Column('consecutive_errors', sa.Integer(), server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_error_at', sa.DateTime(timezone=True), nullable=True),

        # Baseline tracking for external change detection
        sa.Column('last_known_budget', sa.Numeric(18, 4), nullable=True),
        sa.Column('last_known_status', sa.String(), nullable=True),
        sa.Column('baseline_updated_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Indexes for agent_entity_states
    op.create_index('ix_agent_entity_states_agent', 'agent_entity_states', ['agent_id'])
    op.create_index('ix_agent_entity_states_entity', 'agent_entity_states', ['entity_id'])
    op.create_index('ix_agent_entity_states_state', 'agent_entity_states', ['agent_id', 'state'])

    # =========================================================================
    # STEP 4: Create agent_evaluation_events table
    # =========================================================================
    # WHAT: Immutable event log of all evaluations
    # WHY: Event sourcing for full observability and "why didn't it fire?" queries
    op.create_table(
        'agent_evaluation_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),

        # Result classification
        sa.Column('result_type', postgresql.ENUM(
            'triggered', 'condition_met', 'condition_not_met', 'cooldown', 'error',
            name='agentresulttypeenum', create_type=False
        ), nullable=False),
        sa.Column('headline', sa.Text(), nullable=False),

        # Observations
        sa.Column('observations', postgresql.JSON(), nullable=False),
        sa.Column('entity_snapshot', postgresql.JSON(), nullable=False),

        # Condition evaluation
        sa.Column('condition_definition', postgresql.JSON(), nullable=False),
        sa.Column('condition_inputs', postgresql.JSON(), nullable=False),
        sa.Column('condition_result', sa.Boolean(), nullable=False),
        sa.Column('condition_explanation', sa.Text(), nullable=False),

        # Accumulation state
        sa.Column('accumulation_before', postgresql.JSON(), nullable=False),
        sa.Column('accumulation_after', postgresql.JSON(), nullable=False),
        sa.Column('accumulation_explanation', sa.Text(), nullable=False),

        # State transition
        sa.Column('state_before', sa.String(50), nullable=False),
        sa.Column('state_after', sa.String(50), nullable=False),
        sa.Column('state_transition_reason', sa.Text(), nullable=False),

        # Trigger decision
        sa.Column('should_trigger', sa.Boolean(), nullable=False),
        sa.Column('trigger_explanation', sa.Text(), nullable=False),

        # Summary for Copilot
        sa.Column('summary', sa.Text(), nullable=False),

        # Performance
        sa.Column('evaluation_duration_ms', sa.Integer(), nullable=False),

        # Denormalized for filtering
        sa.Column('entity_name', sa.String(255), nullable=False),
        sa.Column('entity_provider', sa.String(50), nullable=False),
    )

    # Indexes for agent_evaluation_events
    op.create_index('ix_eval_events_agent_time', 'agent_evaluation_events', ['agent_id', sa.text('evaluated_at DESC')])
    op.create_index('ix_eval_events_workspace_time', 'agent_evaluation_events', ['workspace_id', sa.text('evaluated_at DESC')])
    op.create_index('ix_eval_events_result', 'agent_evaluation_events', ['agent_id', 'result_type', sa.text('evaluated_at DESC')])
    op.create_index('ix_eval_events_entity', 'agent_evaluation_events', ['entity_id', sa.text('evaluated_at DESC')])

    # =========================================================================
    # STEP 5: Create agent_action_executions table
    # =========================================================================
    # WHAT: Record of executed actions with rollback capability
    # WHY: Audit trail and ability to undo state-changing actions
    op.create_table(
        'agent_action_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('evaluation_event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_evaluation_events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),

        # Action definition
        sa.Column('action_type', postgresql.ENUM(
            'email', 'scale_budget', 'pause_campaign', 'webhook',
            name='actiontypeenum', create_type=False
        ), nullable=False),
        sa.Column('action_config', postgresql.JSON(), nullable=False),

        # Execution result
        sa.Column('executed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSON(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=False),

        # State tracking for rollback
        sa.Column('state_before', postgresql.JSON(), nullable=True),
        sa.Column('state_after', postgresql.JSON(), nullable=True),
        sa.Column('state_verified', sa.Boolean(), server_default='false'),

        # Rollback capability
        sa.Column('rollback_possible', sa.Boolean(), server_default='false'),
        sa.Column('rollback_executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rollback_executed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('rollback_result', postgresql.JSON(), nullable=True),
    )

    # Indexes for agent_action_executions
    op.create_index('ix_action_exec_agent', 'agent_action_executions', ['agent_id', sa.text('executed_at DESC')])
    op.create_index('ix_action_exec_workspace', 'agent_action_executions', ['workspace_id', sa.text('executed_at DESC')])
    op.create_index('ix_action_exec_event', 'agent_action_executions', ['evaluation_event_id'])


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign keys)
    op.drop_table('agent_action_executions')
    op.drop_table('agent_evaluation_events')
    op.drop_table('agent_entity_states')
    op.drop_table('agents')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS actiontypeenum')
    op.execute('DROP TYPE IF EXISTS agentresulttypeenum')
    op.execute('DROP TYPE IF EXISTS accumulationmodeenum')
    op.execute('DROP TYPE IF EXISTS accumulationunitenum')
    op.execute('DROP TYPE IF EXISTS triggermodeenum')
    op.execute('DROP TYPE IF EXISTS agentstateenum')
    op.execute('DROP TYPE IF EXISTS agentscopetypeenum')
    op.execute('DROP TYPE IF EXISTS agentstatusenum')
