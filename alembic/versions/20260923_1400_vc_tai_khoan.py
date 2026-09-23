"""Kho tai khoan he thong cua video_crawler: vc_tai_khoan.

Revision ID: 5e1a9c46b2d7
Revises: 3b7d2f9e1c48
Create Date: 2026-09-23

## VI SAO CO BANG NAY

Khach gan nhu khong bao gio tu xuat duoc cookies.txt, nen sau nen can phien cua
video_crawler gan nhu khong dung duoc (THIET_KE_PHIEN_VA_KENH.md §1). Chu du an
duyet 23/09: LTT giu mot KHO tai khoan PHU; job nao khong co phien rieng cua
khach thi muon mot tai khoan trong kho, va LTT dung ten luot do.

Dot dau chi douyin, xiaohongshu, tiktok. KHONG bilibili (hai kho API Bilibili lon
nhat bi luat su cua Bilibili buoc dong nam 2026 - rui ro phap ly co tien le that).

## KHONG PHAI DU LIEU CUA KHACH

Bang khong co `owner_id` va khong co noi dung cua khach: no la tai san cua LTT.
Vi the no khai o `governance.NOT_CUSTOMER_DATA`, khong phai `governance.STORES`.
Quan he "luot cua khach nao di qua tai khoan nao" nam o su kien job INTERNAL.

## RANG BUOC UNIQUE

`uq_vc_tai_khoan_nen_nhan`: mot nen khong co hai tai khoan cung nhan. Mat rang
buoc nay thi "tam nghi tai khoan do" tro thanh cau hoi khong co dap an.
⚠️ `tools/restore_drill_schema.py` (KHONG thuoc lan nay) can them ten rang buoc
   nay vao danh sach doi chieu sau khoi phuc.

## ROLLBACK

Them thuan tuy. `downgrade` xoa dung bang nay va chi so cua no.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "5e1a9c46b2d7"
down_revision = "3b7d2f9e1c48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vc_tai_khoan",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("nen_tang", sa.String(length=32), nullable=False),
        sa.Column("nhan", sa.String(length=64), nullable=False),
        sa.Column("cookie_ma_hoa", sa.Text(), nullable=False),
        sa.Column("trang_thai", sa.String(length=16), nullable=False),
        sa.Column("diem", sa.Integer(), nullable=False),
        sa.Column("han", sa.DateTime(timezone=True), nullable=True),
        sa.Column("loi_gan_nhat", sa.String(length=32), nullable=True),
        sa.Column("dung_gan_nhat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cua_so_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("so_luot_trong_gio", sa.Integer(), nullable=False),
        sa.Column("tao_luc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cap_nhat_luc", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("nen_tang", "nhan", name="uq_vc_tai_khoan_nen_nhan"),
    )
    op.create_index("ix_vc_tai_khoan_nen_tang", "vc_tai_khoan", ["nen_tang"])


def downgrade() -> None:
    op.drop_index("ix_vc_tai_khoan_nen_tang", table_name="vc_tai_khoan")
    op.drop_table("vc_tai_khoan")
