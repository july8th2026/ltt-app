# -*- coding: utf-8 -*-
"""workflow_run.chay_lai_tu_run_id — "chay lai tu node" (P9b).

Revision ID: 3d5c07e2ba91
Revises: 7f2b91d4c8ae
Create Date: 2026-09-24

## VI SAO MOT COT RIENG, KHONG MUON `parent_run_id`

Hai quan he trong giong nhau (`run nay sinh ra tu run kia`) nhung mang NGHIA VU
TRAI NGUOC ve TIEN:

    parent_run_id       run CON cua `core.call_workflow` — KHONG co `hold_id`
                        rieng, cha da giu cho. Giu hai lan = khach tra hai lan.
    chay_lai_tu_run_id  mot run DOC LAP: nguoi dung bam "chay lai tu node nay",
                        no co khoan giu RIENG va tieu tien MOI.

Gop hai quan he vao mot cot nghia la moi cau hoi "run nay co hold rieng khong"
tra loi sai cho mot nua so hang — im lang. Cung hang loi voi ba lan khoa theo
`node_id` tran o phase 4 (`wakeup`, `node_run`, `dedupe_key`).

## AI YEU CAU

Lan `p9b` can cot nay cho duong "chay lai tu node" va DA DUNG DUNG RANH GIOI
thay vi tu them (dac ta: `docs/superpowers/reports/p9b-quan-sat-2/
task-4-report.md`). Dieu phoi chuyen yeu cau sang lan P6 vi P6 la lan DUY NHAT
duoc ghi so alembic hom nay — mot so, mot nguoi ghi. Hai head chan MOI deploy
cua MOI phien.

## CHI SO BO PHAN

Dai da so run KHONG phai mot luot chay lai, nen chi so chi phuc vu cau hoi
"nhung luot chay lai cua run nay la ai". Cung khuon `ix_workflow_run_parent`.

## ROLLBACK

`downgrade()` drop index roi drop cot. Mat cot = mat lien ket giua mot luot
chay lai va run goc cua no; ban than cac run VAN CON (chung doc lap).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "3d5c07e2ba91"
down_revision = "7f2b91d4c8ae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_run",
        sa.Column("chay_lai_tu_run_id", sa.String(36), nullable=False,
                  server_default=""))
    op.create_index(
        "ix_wfrun_chay_lai_tu", "workflow_run", ["chay_lai_tu_run_id"],
        postgresql_where=sa.text("chay_lai_tu_run_id <> ''"),
        sqlite_where=sa.text("chay_lai_tu_run_id <> ''"))


def downgrade() -> None:
    op.drop_index("ix_wfrun_chay_lai_tu", table_name="workflow_run")
    op.drop_column("workflow_run", "chay_lai_tu_run_id")
