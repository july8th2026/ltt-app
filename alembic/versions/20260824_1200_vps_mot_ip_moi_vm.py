"""vps: doi tu chia cong sang MOT IP CONG KHAI cho MOT VM (H39/G2)

Mo hinh cu buoc cong NAT va dia chi rieng vao nhau bang mot phep cong
(`cong_ngoai = cong_goc + octet`) de chi phai cap phat MOT thu. Tu 2026-08-24
moi may co mot IP cong khai rieng va khong con chia cong, nen:

  * thu khan hiem can cap phat la DIA CHI TRONG MANG RIENG, khong phai cong;
  * trong tai cap phat chuyen sang rang buoc duy nhat tren
    `vps_instance(gateway_id, ip_noi_bo)`;
  * `vps_port_map` khong con ly do ton tai.

`vps_ip.vultr_id` la cot quan trong nhat trong migration nay: thieu no thi khi
may bi xoa ta KHONG BIET phai tra IP nao ve cho nha cung cap, va moi may chet
de lai $3/thang chay mai.

Revision ID: 6f2a91d47c30
Revises: 8b2c5d1e40a7
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "6f2a91d47c30"
down_revision = "8b2c5d1e40a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("vps_gateway") as b:
        b.add_column(sa.Column("octet_dau", sa.Integer(), nullable=False,
                               server_default="10"))
        b.add_column(sa.Column("octet_cuoi", sa.Integer(), nullable=False,
                               server_default="250"))
        for ten in ("cong_dau", "cong_cuoi", "cong_goc"):
            b.drop_column(ten)

    with op.batch_alter_table("vps_ip") as b:
        b.add_column(sa.Column("vultr_id", sa.String(64), nullable=False,
                               server_default=""))
        b.add_column(sa.Column("nhan", sa.String(64), nullable=False,
                               server_default=""))

    with op.batch_alter_table("vps_instance") as b:
        b.add_column(sa.Column("ip_noi_bo", sa.String(64), nullable=True))
        b.create_unique_constraint("uq_vps_instance_ip",
                                   ["gateway_id", "ip_noi_bo"])

    op.drop_table("vps_port_map")


def downgrade() -> None:
    op.create_table(
        "vps_port_map",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("instance_id", sa.String(36), nullable=False, index=True),
        sa.Column("gateway_id", sa.String(36), nullable=False, index=True),
        sa.Column("cong_ngoai", sa.Integer(), nullable=False),
        sa.Column("cong_trong", sa.Integer(), nullable=False),
        sa.Column("giao_thuc", sa.String(8), nullable=False, server_default="tcp"),
        sa.Column("nhan", sa.String(32), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("gateway_id", "cong_ngoai", "giao_thuc",
                            name="uq_vps_port_map_cong"),
    )
    with op.batch_alter_table("vps_instance") as b:
        b.drop_constraint("uq_vps_instance_ip", type_="unique")
        b.drop_column("ip_noi_bo")
    with op.batch_alter_table("vps_ip") as b:
        b.drop_column("nhan")
        b.drop_column("vultr_id")
    with op.batch_alter_table("vps_gateway") as b:
        b.add_column(sa.Column("cong_goc", sa.Integer(), nullable=False,
                               server_default="0"))
        b.add_column(sa.Column("cong_cuoi", sa.Integer(), nullable=False,
                               server_default="0"))
        b.add_column(sa.Column("cong_dau", sa.Integer(), nullable=False,
                               server_default="0"))
        b.drop_column("octet_cuoi")
        b.drop_column("octet_dau")
