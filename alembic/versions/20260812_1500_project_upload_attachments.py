"""gan upload session vao editor project

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b6c7d8e9f0a1"
down_revision = "a5b6c7d8e9f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("upload_sessions", sa.Column(
        "project_id", sa.String(36), nullable=False, server_default=""))
    op.create_index("ix_upload_sessions_project", "upload_sessions",
                    ["project_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_upload_sessions_project", table_name="upload_sessions")
    op.drop_column("upload_sessions", "project_id")
