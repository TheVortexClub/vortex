"""tool runs: jobs (image/video), message tool info, file origin

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result_file_ids", sa.JSON(), nullable=False),
        sa.Column("conversation_id", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_index("ix_jobs_conversation_id", "jobs", ["conversation_id"])

    with op.batch_alter_table("messages") as batch:
        batch.add_column(sa.Column("tool", sa.JSON(), nullable=True))
    with op.batch_alter_table("files") as batch:
        batch.add_column(
            sa.Column("origin", sa.String(16), nullable=False, server_default="upload")
        )


def downgrade() -> None:
    with op.batch_alter_table("files") as batch:
        batch.drop_column("origin")
    with op.batch_alter_table("messages") as batch:
        batch.drop_column("tool")
    op.drop_index("ix_jobs_conversation_id", table_name="jobs")
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_table("jobs")
