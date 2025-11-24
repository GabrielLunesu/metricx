"""Add workspace_members and workspace_invites tables for multi-workspace.

Revision ID: 20251124_000001
Revises: 20251104_000002_tokens_access_nullable
Create Date: 2025-11-24 15:06:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251124_000001"
down_revision = "95e2fb15bec2"
branch_labels = None
depends_on = None


def upgrade():
    # Reuse existing role enum type (already created elsewhere); do not recreate
    role_enum = postgresql.ENUM("Owner", "Admin", "Viewer", name="roleenum", create_type=False)

    # Reuse invite status enum; ensure it exists without re-creating if present
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'invitestatusenum') THEN
                CREATE TYPE invitestatusenum AS ENUM ('pending', 'accepted', 'declined', 'expired');
            END IF;
        END$$;
        """
    )
    invite_status_enum = postgresql.ENUM("pending", "accepted", "declined", "expired", name="invitestatusenum", create_type=False)

    op.create_table(
        "workspace_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )

    op.create_table(
        "workspace_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("status", invite_status_enum, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table("workspace_invites")
    op.drop_table("workspace_members")
    op.execute("DROP TYPE IF EXISTS invitestatusenum;")
