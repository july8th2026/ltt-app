"""VPS V2: `vps_instance.cach_ly_luc` + `cach_ly_ly_do` — cach ly vi lam dung (Pha 07).

Revision ID: d15b8c30f7a4
Revises: c93a5d17be42
Create Date: 2026-09-09

## Vi sao mot khai niem RIENG chu khong tai dung `bi_treo`

`bi_treo` la khai niem TIEN, va no dat luon moc `xoa_sau` bay ngay
(`billing.AN_HAN_TRUOC_KHI_XOA_NGAY`). Dung no cho lam dung thi:

* so sach ghi rang khach no tien — sai su that;
* va may cua mot khach **dang tra tien day du** bi xoa sau mot tuan vi mot canh
  bao mang.

Cach ly thi cat duong NAT, giu nguyen dia va VM, va go lai duoc bang mot lenh.
Xem `apps/vps/services/cach_ly.py`.

`cach_ly_ly_do` la `Text` chu khong `String(n)`: no la thu nguoi ta doc lai sau
ba thang de tra loi khach, nen cat cut no la mat dung phan can nhat.
"""
from alembic import op
import sqlalchemy as sa

revision = "d15b8c30f7a4"
down_revision = "c93a5d17be42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vps_instance", sa.Column(
        "cach_ly_luc", sa.DateTime(timezone=True), nullable=True))
    op.add_column("vps_instance", sa.Column(
        "cach_ly_ly_do", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("vps_instance", "cach_ly_ly_do")
    op.drop_column("vps_instance", "cach_ly_luc")
