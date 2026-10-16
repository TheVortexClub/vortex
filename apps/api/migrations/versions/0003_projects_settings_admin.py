"""projects, user settings, server settings, admin flag, usage per user

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("color", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])

    op.create_table(
        "user_settings",
        sa.Column(
            "user_id",
            sa.String(32),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("default_model", sa.String(128), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("custom_instructions", sa.Text(), nullable=False),
        sa.Column("tools", sa.JSON(), nullable=False),
        sa.Column("memory_enabled", sa.Boolean(), nullable=False),
        sa.Column("language", sa.String(8), nullable=False),
    )

    op.create_table(
        "server_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
    )

    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    # The single local-mode user owns the install.
    op.execute("UPDATE users SET is_admin = true WHERE email = 'local@vortex.local'")

    with op.batch_alter_table("conversations") as batch:
        batch.add_column(sa.Column("project_id", sa.String(32), nullable=True))
        batch.create_foreign_key(
            "fk_conversations_project_id", "projects", ["project_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_index("ix_conversations_project_id", ["project_id"])

    with op.batch_alter_table("usage_events") as batch:
        batch.add_column(sa.Column("user_id", sa.String(32), nullable=True))
        batch.create_index("ix_usage_events_user_id", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table("usage_events") as batch:
        batch.drop_index("ix_usage_events_user_id")
        batch.drop_column("user_id")
    with op.batch_alter_table("conversations") as batch:
        batch.drop_index("ix_conversations_project_id")
        batch.drop_constraint("fk_conversations_project_id", type_="foreignkey")
        batch.drop_column("project_id")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("is_admin")
    op.drop_table("server_settings")
    op.drop_table("user_settings")
    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_table("projects")
