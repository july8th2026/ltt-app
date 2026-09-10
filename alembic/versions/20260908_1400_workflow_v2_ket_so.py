"""LTT WORKFLOW V2 · Dot 3B — dau KET SO tren `workflow_run`.

Revision ID: d7e24b9f1c53
Revises: c6d13a8e4b72
Create Date: 2026-09-08

## VI SAO CAN MOT COT, KHONG PHAI MOT SUY LUAN

He con `finally` phai LUY DANG: bo don nen, mot luot thu lai, va nguoi van hanh
deu co the goi no. Khong co dau ben vung thi "da ket so chua" phai SUY ra tu
mot thu khac — vd `hold_id == ''`. Suy nhu vay SAI o dung ca dang lo:

    hold_id rong  ->  co the la "da ket so"
                  ->  cung co the la "run nay chua bao gio co giu cho"

Hai chuyen khac han nhau, mot gia tri. `ket_so_luc IS NULL` thi khong nhap
nhang: no noi ve HANH DONG, khong ve HAU QUA cua hanh dong.

## NGUONG `M10` — 145 -> 0

    145 dong "GIU CHO TREO: <n> khoan, <n> credit cua khach dang bi giu"
        trong 28 ngay log worker            (`01 §A`, `G16` -> `G32`)

Khoan giu cho treo la TIEN CUA KHACH BI GIAM: so du hien thi thap hon thuc te,
va khong lenh nao cua khach go duoc. No khong gay loi, khong gay canh bao — no
im lang cho toi khi ai do doc log.

Nguyen nhan la HINH DANG chu khong phai su cau tha: hom nay `_terminal_status`
ghi trang thai o mot cho, `budget.settle` ket so o cho khac, va giua hai cho la
mot cua so. Worker restart 13,6 lan/ngay nen cua so ay duoc THU 13,6 lan moi
ngay.

⇒ Ban va: `may_trang_thai.chuyen_run()` goi thang `ket_so.ket_so()` trong CUNG
  transaction. `test_955` kiem bang ROLLBACK — neu hai thao tac o hai
  transaction thi mot trong hai song sot, va bai do se do.

## AN TOAN

Hai cot MOI, nullable / co server_default, tren mot bang chua ai dung
(`workflow_run` sinh ra o `b5c92e3f7a41` cung ngay). Khong doi cot nao dang co,
khong cham du lieu nao dang co.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d7e24b9f1c53"
down_revision = "c6d13a8e4b72"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_run",
                  sa.Column("ket_so_luc", sa.DateTime(timezone=True),
                            nullable=True))
    op.add_column("workflow_run",
                  sa.Column("ly_do_ket_so", sa.String(200), nullable=False,
                            server_default=""))


def downgrade() -> None:
    op.drop_column("workflow_run", "ly_do_ket_so")
    op.drop_column("workflow_run", "ket_so_luc")
