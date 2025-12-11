"""Add rate_limited_until field to connections

Revision ID: 20251211_000001
Revises: 20251209_000002
Create Date: 2025-12-11

WHAT:
    Adds rate_limited_until timestamp field to the connections table.

WHY:
    Circuit breaker for API quota exhaustion. When Google/Meta returns a 429
    "Resource Exhausted" error with a retry hint (e.g., "Retry in 723 seconds"),
    we set this field to skip syncing until the cooldown expires.

    This prevents:
    - Hammering the API after quota is exhausted
    - Worker crashes from repeated 429 errors
    - Wasted compute resources on doomed requests

REFERENCES:
    - docs/living-docs/plans/fancy-launching-lake.md (quota fix plan)
    - app/models.py:Connection.rate_limited_until
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251211_000001'
down_revision = '20251209_000002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add rate_limited_until column for circuit breaker
    # WHAT: Timestamp until which this connection should not sync
    # WHY: Respects API quota cooldown hints
    op.add_column(
        'connections',
        sa.Column('rate_limited_until', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('connections', 'rate_limited_until')
