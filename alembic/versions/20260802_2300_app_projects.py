"""generic app projects for stateful editors

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-02 23:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("app_slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False, server_default="Project moi"),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_app_projects_user_id", "app_projects", ["user_id"])
    op.create_index("ix_app_projects_app_slug", "app_projects", ["app_slug"])
    op.create_index("ix_app_projects_status", "app_projects", ["status"])
    op.create_index("ix_app_projects_owner_app_updated", "app_projects",
                    ["user_id", "app_slug", "updated_at"])


def downgrade() -> None:
    op.drop_table("app_projects")
