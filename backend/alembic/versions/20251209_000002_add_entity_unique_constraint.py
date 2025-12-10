"""Add unique constraint on entities (connection_id, external_id)

Revision ID: 20251209_000001
Revises: 20251207_000001
Create Date: 2025-12-09

WHAT:
    Adds a unique constraint on entities table to prevent duplicate entities
    within the same connection.

WHY:
    Without this constraint, concurrent sync operations or race conditions can
    create duplicate entities with the same external_id for the same connection.
    This causes the entity map in sync services to have fewer entries than
    expected (due to dict key collision), which results in metrics being skipped.

    Example issue: 47 asset_group entities exist, but only 26 are synced because
    there are 21 duplicate external_ids that overwrite each other in the map.

REFERENCES:
    - app/models.py:Entity
    - app/services/google_sync_service.py:_upsert_entity
    - app/services/snapshot_sync_service.py:_sync_google_snapshots
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '20251209_000002'
down_revision = '20251209_000001_add_clerk_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add unique constraint to prevent duplicate entities
    # WHAT: Ensures (connection_id, external_id) is unique
    # WHY: Prevents race conditions from creating duplicates
    op.create_unique_constraint(
        'uq_entities_connection_external',
        'entities',
        ['connection_id', 'external_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_entities_connection_external', 'entities')
