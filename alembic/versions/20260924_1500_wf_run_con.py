"""workflow_run: parent_run_id / parent_node_id / do_sau (core.call_workflow)

Revision ID: b7d2e9c41a03
Revises: 8f1c6a4d2b90
Create Date: 2026-09-24

Ba cot MOI, deu co gia tri mac dinh va NOT NULL => `ALTER TABLE ... ADD COLUMN`
tren PostgreSQL >= 11 la thao tac CHI SUA CATALOG, khong viet lai bang. Bang
`workflow_run` dang chay that, nen dieu do la mot phan cua quyet dinh, khong
phai mot ghi chu.

Chi so `ix_workflow_run_parent` la chi so BO PHAN: dai da so run la run GOC
(`parent_run_id = ''`), va chi so chi phuc vu mot cau hoi duy nhat - "con cua
run nay la ai" - luc mot run con ket thuc.

⛔ KHONG co khoa ngoai toi `workflow_run.id`: cung quy uoc voi `hold_id` va
   `Job.plan_id` trong mo hinh nay (cot `String(36)` khong khoa ngoai).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7d2e9c41a03"
down_revision: Union[str, None] = "8f1c6a4d2b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workflow_run", sa.Column(
        "parent_run_id", sa.String(length=36), nullable=False,
        server_default=""))
    op.add_column("workflow_run", sa.Column(
        "parent_node_id", sa.String(length=64), nullable=False,
        server_default=""))
    op.add_column("workflow_run", sa.Column(
        "do_sau", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_workflow_run_parent", "workflow_run",
                    ["parent_run_id"],
                    postgresql_where=sa.text("parent_run_id <> ''"),
                    sqlite_where=sa.text("parent_run_id <> ''"))


def downgrade() -> None:
    op.drop_index("ix_workflow_run_parent", table_name="workflow_run")
    op.drop_column("workflow_run", "do_sau")
    op.drop_column("workflow_run", "parent_node_id")
    op.drop_column("workflow_run", "parent_run_id")
