"""agent workflow snapshots and private shares

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-04 03:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("agent_workflow_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workflow_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_agent_workflow_snapshots_workflow_id", "agent_workflow_snapshots", ["workflow_id"])
    op.create_index("ix_agent_workflow_snapshots_user_id", "agent_workflow_snapshots", ["user_id"])
    op.create_index("ux_agent_snapshot_workflow_revision", "agent_workflow_snapshots",
                    ["workflow_id", "revision"], unique=True)
    op.create_table("agent_workflow_shares",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workflow_id", sa.String(36), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("permission", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_agent_workflow_shares_workflow_id", "agent_workflow_shares", ["workflow_id"])
    op.create_index("ix_agent_workflow_shares_owner_id", "agent_workflow_shares", ["owner_id"])
    op.create_index("ix_agent_workflow_shares_token_hash", "agent_workflow_shares", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("agent_workflow_shares")
    op.drop_table("agent_workflow_snapshots")
