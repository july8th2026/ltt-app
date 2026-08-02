"""agent runs, checkpoint and child job linkage

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-02 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("parent_id", sa.String(36), nullable=False,
                                    server_default=""))
    op.add_column("jobs", sa.Column("plan_id", sa.String(36), nullable=False,
                                    server_default=""))
    op.add_column("jobs", sa.Column("step_id", sa.String(32), nullable=False,
                                    server_default=""))
    op.create_index("ix_jobs_parent_id", "jobs", ["parent_id"])
    op.create_index("ix_jobs_plan_id", "jobs", ["plan_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("app_slug", sa.String(64), nullable=False, server_default="agent"),
        sa.Column("goal", sa.Text(), nullable=False, server_default=""),
        sa.Column("plan", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("checkpoint", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(24), nullable=False, server_default="planning"),
        sa.Column("budget_max", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(36), nullable=False, server_default=""),
        sa.Column("decision_log", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])
    op.create_index("ix_agent_runs_created_at", "agent_runs", ["created_at"])
    op.create_index("ix_agent_runs_user_created", "agent_runs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_index("ix_jobs_plan_id", table_name="jobs")
    op.drop_index("ix_jobs_parent_id", table_name="jobs")
    op.drop_column("jobs", "step_id")
    op.drop_column("jobs", "plan_id")
    op.drop_column("jobs", "parent_id")
