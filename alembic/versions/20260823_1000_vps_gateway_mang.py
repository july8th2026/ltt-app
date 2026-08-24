"""vps: cot mo ta MANG RIENG ma mot cong vao phuc vu (H39 P1)

Sau cot them vao `vps_gateway`. Chi THEM, khong dung toi du lieu nao dang co.

Cot dang chu y nhat la `cong_goc`. No buoc cong NAT va dia chi rieng cua may vao
nhau bang MOT phep cong:

    cong_ngoai = cong_goc + octet

Nho vay chi phai cap phat MOT thu (cong, da nguyen tu san qua rang buoc duy nhat
trong `vps_port_map`) va suy ra duoc dia chi. Cap phat hai thu doc lap la mo cua
cho chung lech nhau: may A giu cong 33931 nhung dia chi 10.50.0.52, trong khi
DNAT tren gateway tro 33931 ve 10.50.0.51 — khach go dung dia chi va roi vao may
NGUOI KHAC, khong co loi nao duoc ghi ra.

Quy uoc lay tu ha tang dang chay: VM100 o 10.50.0.11 ung voi cong 33891.

Revision ID: 8b2c5d1e40a7
Revises: c1f4a2b70e51
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "8b2c5d1e40a7"
down_revision = "c1f4a2b70e51"
branch_labels = None
depends_on = None

COT = (
    ("bridge", sa.String(32), ""),
    ("subnet_cidr", sa.String(32), ""),
    ("subnet_gw", sa.String(64), ""),
    ("dns", sa.String(128), ""),
)


def upgrade() -> None:
    for ten, kieu, mac_dinh in COT:
        op.add_column("vps_gateway",
                      sa.Column(ten, kieu, nullable=False,
                                server_default=mac_dinh))
    op.add_column("vps_gateway",
                  sa.Column("mtu", sa.Integer(), nullable=False,
                            server_default="0"))
    op.add_column("vps_gateway",
                  sa.Column("cong_goc", sa.Integer(), nullable=False,
                            server_default="0"))


def downgrade() -> None:
    for ten in ("cong_goc", "mtu") + tuple(t[0] for t in COT):
        op.drop_column("vps_gateway", ten)
