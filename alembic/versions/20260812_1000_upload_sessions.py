"""them upload staging lifecycle

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a5b6c7d8e9f0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "upload_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("app_slug", sa.String(64), nullable=False),
        sa.Column("staging_key", sa.String(512), nullable=False),
        sa.Column("final_key", sa.String(512), nullable=False, server_default=""),
        sa.Column("filename", sa.String(255), nullable=False, server_default=""),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("expected_size", sa.Integer(), nullable=False),
        sa.Column("actual_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("job_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staging_key"),
    )
    op.create_index("ix_upload_sessions_owner_status", "upload_sessions",
                    ["user_id", "status", "expires_at"])
    op.create_index("ix_upload_sessions_app_created", "upload_sessions",
                    ["app_slug", "created_at"])
    op.create_index("ix_upload_sessions_job", "upload_sessions", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_upload_sessions_job", table_name="upload_sessions")
    op.drop_index("ix_upload_sessions_app_created", table_name="upload_sessions")
    op.drop_index("ix_upload_sessions_owner_status", table_name="upload_sessions")
    op.drop_table("upload_sessions")
