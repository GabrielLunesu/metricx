"""add_sync_frequency_to_connections

WHAT:
    Adds sync automation tracking fields to the connections table.
    Enables near-realtime syncing with configurable frequencies.

WHY:
    - Users need control over sync frequency (manual, realtime, 30min, hourly, daily)
    - Track sync attempts, completions, and change detections
    - Monitor sync health and statistics

REFERENCES:
    - docs/living-docs/REALTIME_SYNC_STATUS.md
    - docs/ARCHITECTURE.md (Near-realtime sync section)

Revision ID: fe534aa60c90
Revises: 20251104_000002
Create Date: 2025-11-11 18:26:08.300124
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fe534aa60c90'
down_revision = '20251104_000002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add sync automation tracking fields to connections table.
    
    Fields added:
    - sync_frequency: User-selected sync interval (manual, realtime, 30min, hourly, daily)
    - last_sync_attempted_at: Timestamp of last sync attempt (success or failure)
    - last_sync_completed_at: Timestamp of last successful sync completion
    - last_metrics_changed_at: Timestamp when metrics actually changed (data freshness)
    - total_syncs_attempted: Counter for all sync attempts
    - total_syncs_with_changes: Counter for syncs that resulted in DB writes
    - sync_status: Current sync state (idle, syncing, error)
    - last_sync_error: Error message from last failed sync (null if success)
    """
    # Sync frequency configuration
    op.add_column('connections', sa.Column(
        'sync_frequency',
        sa.String(),
        server_default='manual',
        nullable=False,
        comment='Sync interval: manual, realtime, 30min, hourly, daily'
    ))
    
    # Timestamp tracking
    op.add_column('connections', sa.Column(
        'last_sync_attempted_at',
        sa.DateTime(),
        nullable=True,
        comment='Last time a sync job was started (success or failure)'
    ))
    
    op.add_column('connections', sa.Column(
        'last_sync_completed_at',
        sa.DateTime(),
        nullable=True,
        comment='Last time a sync job completed successfully'
    ))
    
    op.add_column('connections', sa.Column(
        'last_metrics_changed_at',
        sa.DateTime(),
        nullable=True,
        comment='Last time metrics actually changed (data freshness indicator)'
    ))
    
    # Statistics tracking
    op.add_column('connections', sa.Column(
        'total_syncs_attempted',
        sa.Integer(),
        server_default='0',
        nullable=False,
        comment='Total number of sync attempts'
    ))
    
    op.add_column('connections', sa.Column(
        'total_syncs_with_changes',
        sa.Integer(),
        server_default='0',
        nullable=False,
        comment='Number of syncs that resulted in metric changes'
    ))
    
    # Status tracking
    op.add_column('connections', sa.Column(
        'sync_status',
        sa.String(),
        server_default='idle',
        nullable=False,
        comment='Current sync state: idle, syncing, error'
    ))
    
    op.add_column('connections', sa.Column(
        'last_sync_error',
        sa.Text(),
        nullable=True,
        comment='Error message from last failed sync (null if success)'
    ))


def downgrade() -> None:
    """
    Remove sync automation tracking fields from connections table.
    """
    op.drop_column('connections', 'last_sync_error')
    op.drop_column('connections', 'sync_status')
    op.drop_column('connections', 'total_syncs_with_changes')
    op.drop_column('connections', 'total_syncs_attempted')
    op.drop_column('connections', 'last_metrics_changed_at')
    op.drop_column('connections', 'last_sync_completed_at')
    op.drop_column('connections', 'last_sync_attempted_at')
    op.drop_column('connections', 'sync_frequency')



