# -*- coding: utf-8 -*-
"""Bo nho ben cua piece connector: connector_store.

Revision ID: 7f2b91d4c8ae
Revises: 9c1e4b77a205
Create Date: 2026-09-24

## VI SAO CO BANG NAY (spec §11.4, plan wf-v2 P6)

Mot trigger POLLING cua Activepieces goi `ctx.store.put(...)` voi khoa DO PIECE
TU DAT, nhieu khoa, hinh dang tuy piece. Nhet chung vao
`workflow_trigger.con_tro` la tron hai quyen so huu vao mot cot JSON: nen tang
ghi lich, piece ghi con tro cua no. Lan dau hai ben ghi de nhau se la mot
trigger ban lai toan bo lich su — tuc tao lai MOI run cu, tuc tieu credit that.

## KHOA DUY NHAT GOM `owner_id`

⛔ Khong phai de loc cho nhanh. Hai khach dung CUNG MOT piece phai khong bao
gio doc duoc store cua nhau, va cach chac chan nhat la khong ton tai mot hang
nao ho cung tro toi. `pham_vi` la mot DUONG (`trigger:<id>` / `run:<id>`), cung
bai hoc ba lan lap o phase 4 (`wakeup`, `node_run`, `dedupe_key` deu khoa theo
`node_id` tran thay vi duong thi hanh).

## DAY LA DU LIEU CUA KHACH

Noi dung do piece ghi va co the chua ID cua ban ghi ben thu ba (vd id dong
Sheets da thay). ⛔ Khong cot nao trong bang nay duoc tra thang ra API soan
thao: mot con tro poll tra ve cho trinh soan thao la mot duong ro danh sach
ban ghi cua khach.

## ROLLBACK

`downgrade()` DROP bang. Mat con tro poll = lan poll ke tiep coi MOI ban ghi la
moi = tao lai run cho ca lich su. Ai chay no phai biet minh dang xoa gi.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "7f2b91d4c8ae"
down_revision = "9c1e4b77a205"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_store",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("pham_vi", sa.String(64), nullable=False),
        sa.Column("khoa", sa.String(200), nullable=False),
        sa.Column("gia_tri", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("owner_id", "pham_vi", "khoa",
                            name="ux_connector_store_khoa"),
    )
    op.create_index("ix_connector_store_owner_id", "connector_store",
                    ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_connector_store_owner_id", table_name="connector_store")
    op.drop_table("connector_store")
