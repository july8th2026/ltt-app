"""LTT WORKFLOW V2 · Dot 2.2 — bang thi hanh (mo hinh C).

Revision ID: b5c92e3f7a41
Revises: a4f81c2d6b95
Create Date: 2026-09-08

## MO HINH C: CHUOI ANH CHUP BAT BIEN

Chot `Q3` (`docs/architecture/workflow_v2_audit/12_19 muc 16.2`). Ba bang, va
moi bang mot LUAT GHI khac han:

  workflow_run        SUA DUOC   trang thai luot chay, `version_id` GHIM
  node_run            SUA DUOC   CON TRO: mot hang moi node moi run
  node_run_snapshot   CHI THEM   khong bao gio sua mot hang da ghi

## 🔴 VI SAO TACH CON TRO KHOI LICH SU — nguong `M1`

`agent/executor.tick()` doc ca khoi `checkpoint`, sua, ghi lai: `O(31+N)` moi
luot tien du chi MOT node doi. O day mot luot tien la:

    INSERT 1 hang node_run_snapshot   +   UPDATE 1 hang node_run

=> `O(node doi)`. Doc trang thai hien tai la mot JOIN qua con tro, khong phai
mot lan quet lich su. `test_951` do bang cach dem hang sinh ra tren mot run 31
node — dung thu ma cach cu lam no ra.

## ⭐ `is_valid` — GHI CA LAN CHUYEN BI TU CHOI (G19)

Worker cham chan quay lai tien mot node da xong, hai worker cung gianh: cach cu
vut lan chuyen bi tu choi di, nen khi dieu tra chi con "trang thai cuoi" — thu
khong noi ai da thu gi. Ghi no ton MOT HANG; khong ghi ton mot buoi dieu tra
khong ket luan duoc.

Ghi lai KHONG phai chap nhan: con tro dung yen khi `is_valid=False`.

## ⛔ CHI MUC BO PHAN CHO `idempotency_key`

    ux_workflow_run_idem  UNIQUE(owner_id, idempotency_key)
                          WHERE idempotency_key <> ''

Phan lon luot chay khong dung khoa. Mot UNIQUE day du se chan MOI luot chay
thu hai cua mot nguoi — dung bai hoc cua `c9d4e1a77b02`.

## AN TOAN

Chi CREATE TABLE moi. Khong doi cot nao dang co, khong cham du lieu nao dang
co, chua noi vao duong chay nao (`27_29 §28`).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b5c92e3f7a41"
down_revision = "a4f81c2d6b95"
branch_labels = None
depends_on = None


_DIEU_KIEN_IDEM = "idempotency_key <> ''"


def upgrade() -> None:
    op.create_table(
        "workflow_run",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("workflow_id", sa.String(36), nullable=False),
        # GHIM: khong bao gio doi sau khi tao. Sua workflow luc 10:00 khong
        # duoc doi luot chay bat dau 09:58.
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(24), nullable=False,
                  server_default="queued"),
        sa.Column("trigger_kind", sa.String(24), nullable=False,
                  server_default="manual"),
        sa.Column("idempotency_key", sa.String(120), nullable=False,
                  server_default=""),
        sa.Column("estimated_max", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("actual_cost", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("hold_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_workflow_run_owner_id", "workflow_run", ["owner_id"])
    op.create_index("ix_workflow_run_workflow_id", "workflow_run",
                    ["workflow_id"])
    op.create_index("ix_workflow_run_status", "workflow_run", ["status"])
    op.create_index("ix_workflow_run_owner_created", "workflow_run",
                    ["owner_id", "created_at"])
    op.create_index(
        "ux_workflow_run_idem", "workflow_run", ["owner_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(_DIEU_KIEN_IDEM),
        sqlite_where=sa.text(_DIEU_KIEN_IDEM))

    op.create_table(
        "node_run",
        sa.Column("run_id", sa.String(36), primary_key=True),
        sa.Column("node_id", sa.String(64), primary_key=True),
        sa.Column("latest_snapshot_id", sa.String(36), nullable=False),
    )

    op.create_table(
        "node_run_snapshot",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("node_id", sa.String(64), nullable=False),
        # Rong = anh chup dau tien cua node nay.
        sa.Column("previous_snapshot_id", sa.String(36), nullable=False,
                  server_default=""),
        sa.Column("execution_status", sa.String(24), nullable=False),
        sa.Column("run_status", sa.String(24), nullable=False,
                  server_default=""),
        sa.Column("attempt_number", sa.Integer(), nullable=False,
                  server_default="1"),
        # TRUE = lan chuyen duoc chap nhan. FALSE = bi tu choi NHUNG van ghi.
        sa.Column("is_valid", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("job_id", sa.String(36), nullable=False, server_default=""),
        # CHI tham chieu artifact. Khong bytes — xem docstring cua model.
        sa.Column("output_ref", sa.JSON(), nullable=False),
        # Ghi LUC KET THUC, khong tinh lai (G21).
        sa.Column("cost_credit", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_nrs_run", "node_run_snapshot", ["run_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_nrs_run", table_name="node_run_snapshot")
    op.drop_table("node_run_snapshot")
    op.drop_table("node_run")
    op.drop_index("ux_workflow_run_idem", table_name="workflow_run")
    op.drop_index("ix_workflow_run_owner_created", table_name="workflow_run")
    op.drop_index("ix_workflow_run_status", table_name="workflow_run")
    op.drop_index("ix_workflow_run_workflow_id", table_name="workflow_run")
    op.drop_index("ix_workflow_run_owner_id", table_name="workflow_run")
    op.drop_table("workflow_run")
