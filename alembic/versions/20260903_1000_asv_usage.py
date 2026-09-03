"""So cai su dung DA GIAO cua Auto Scan Video: asv_usage.

Revision ID: c81d3f5a90e7
Revises: a4c17f9b62d0
Create Date: 2026-09-03

## VI SAO MOT COT TIEN KHONG DU

`AsvWorkItem.credit_actual` tra loi "het bao nhieu". Mot lan doi soat tien can ba
cau tra loi ma no khong co:

    nang luc nao da chay        -> khach hoi "toi tra cho cai gi"
    do bang don vi gi           -> 1.200 token va 12 giay la hai the gioi khac
    lan goi do co CHAC da chay  -> ADR-001 D9, dispatch mo ho

Va quan he la MOT-NHIEU: mot don vi viec o pha 11+ doc canh bang VLM roi sinh
tieng bang TTS — hai nang luc, hai don vi do, hai lan tinh tien, mot item.

## ⛔ BANG NAY KHONG PHAI DUONG TIEN THU HAI

Tien di qua dung MOT cot: `asv_work_item.credit_actual`. Bang nay giai thich con
so do. `features.tong_da_dung` **khong** cong bang nay, va `su_dung.doi_soat`
chot bat bien:

    item.credit_actual == tong `credit` cua cac dong `da_giao` cua item do

Neu ta cong ca hai thi co BA noi mang tien cho cung mot viec — stage, item, so
cai — trong khi `features._kiem_khong_tinh_hai_lan` da ton tai chinh vi hai noi
da la mot noi qua nhieu.

## RANG BUOC CHIU LUC, VA PHAM VI CUA NO

`UNIQUE(run_id, ma_dispatch)`: mot ma dispatch **on dinh cua provider** phat lai
lan hai se bi CSDL tu choi thay vi tinh tien lan hai. Do la lop bao ve cho tinh
huong "may chet giua ket qua da giao va checkpoint".

⚠️ Noi chinh xac pham vi: no bao ve khi ma dispatch on dinh. Tang goi sinh ma moi
   moi lan thi do la mot lan gui KHAC va tinh tien no la dung. Bang nay khong
   biet — va khong the biet — hai lan gui khac ma co phai cung mot viec khong.

⚠️ Khai NGAY TRONG `create_table`: SQLite khong ALTER duoc rang buoc, va ca bo
   test cua kho chay tren SQLite. Cung ghi chu voi ba migration ASV truoc.

## ROLLBACK

Them thuan tuy. Khong cot nao cua bang cu doi kieu hay doi y nghia. Mot lan chay
tao truoc migration nay khong co dong su dung nao, va do la trang thai hop le:
`doi_soat` chi rang buoc nhung item CO dong su dung, nen du lieu cu di qua ma
khong bi ket toi.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c81d3f5a90e7"
down_revision = "a4c17f9b62d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asv_usage",
        sa.Column("id", sa.String(length=48), primary_key=True),
        sa.Column("run_id", sa.String(length=48), nullable=False),
        # Chu so huu o COT: mot phep tra "cua ai" phai la mot dieu kien WHERE.
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("item_key", sa.String(length=64), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nang_luc", sa.String(length=64), nullable=False),
        # App CHU, khong phai ten vendor: ta khong ban ten nha cung cap cho khach.
        sa.Column("app_chu", sa.String(length=32), nullable=False),
        sa.Column("trang_thai", sa.String(length=16), nullable=False),
        # Rong voi `tu_choi`/`mo_ho` — mot su that, khong phai cho trong can dien.
        sa.Column("don_vi", sa.String(length=16), nullable=False,
                  server_default=""),
        sa.Column("so_luong", sa.Float(), nullable=False, server_default="0"),
        # DO DUOC. Bang 0 tru khi `trang_thai == da_giao`.
        sa.Column("credit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ma_dispatch", sa.String(length=64), nullable=False),
        sa.Column("ghi_chu", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "ma_dispatch",
                            name="ux_asv_usage_run_dispatch"),
    )
    op.create_index("ix_asv_usage_run_id", "asv_usage", ["run_id"])
    op.create_index("ix_asv_usage_owner_id", "asv_usage", ["owner_id"])
    op.create_index("ix_asv_usage_trang_thai", "asv_usage", ["trang_thai"])
    op.create_index("ix_asv_usage_run_stage_item", "asv_usage",
                    ["run_id", "stage", "item_key"])
    op.create_index("ix_asv_usage_run_trang_thai", "asv_usage",
                    ["run_id", "trang_thai"])


def downgrade() -> None:
    op.drop_index("ix_asv_usage_run_trang_thai", table_name="asv_usage")
    op.drop_index("ix_asv_usage_run_stage_item", table_name="asv_usage")
    op.drop_index("ix_asv_usage_trang_thai", table_name="asv_usage")
    op.drop_index("ix_asv_usage_owner_id", table_name="asv_usage")
    op.drop_index("ix_asv_usage_run_id", table_name="asv_usage")
    op.drop_table("asv_usage")
