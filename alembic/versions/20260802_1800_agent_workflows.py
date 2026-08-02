"""agent canvas workflows

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-02 18:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_workflows",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False, server_default="Workflow moi"),
        sa.Column("goal", sa.Text(), nullable=False, server_default=""),
        sa.Column("plan_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("nodes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("edges", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("viewport", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("budget_max", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_workflow_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_workflows_user_id", "agent_workflows", ["user_id"])
    op.create_index("ix_agent_workflows_status", "agent_workflows", ["status"])
    op.create_index("ix_agent_workflows_user_updated", "agent_workflows",
                    ["user_id", "updated_at"])


def downgrade() -> None:
    op.drop_table("agent_workflows")
