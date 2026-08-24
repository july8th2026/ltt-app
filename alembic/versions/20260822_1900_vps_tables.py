"""vps: nam bang cho app ban may chu ao (Q103, Q104)

Chi THEM bang moi, khong dung toi bang nao dang co. An toan chay tren CSDL dang
phuc vu khach.

Ba rang buoc DUY NHAT o day khong phai de "cho sach": chung la trong tai khi
nhieu tien trinh worker cung cap phat mot luc.

  * uq_vps_instance_vmid   - hai job khong duoc nhan cung mot VMID
  * uq_vps_port_map_cong   - hai may khong duoc nhan cung mot cong NAT
  * uq_vps_ip_instance     - mot IP chi gan duoc vao mot may

Bo chung di thi mau "cu INSERT, IntegrityError nghia la nguoi khac gianh truoc"
o apps/vps/services/provisioning.py mat cho dua, va hai khach se dung chung mot
cong - khach dau tien mat ket noi IM LANG.

Revision ID: c1f4a2b70e51
Revises: 5a3a13144782
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c1f4a2b70e51"
down_revision = "5a3a13144782"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vps_gateway",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ten", sa.String(80), nullable=False),
        sa.Column("vung", sa.String(16), nullable=False),
        sa.Column("ip_cong_khai", sa.String(64), nullable=False),
        sa.Column("ten_mien", sa.String(190), nullable=False, server_default=""),
        sa.Column("wg_endpoint", sa.String(190), nullable=False, server_default=""),
        sa.Column("cong_dau", sa.Integer(), nullable=False),
        sa.Column("cong_cuoi", sa.Integer(), nullable=False),
        sa.Column("cho_phep_ip_rieng", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column("dang_nhan_may_moi", sa.Boolean(), nullable=False,
                  server_default=sa.true()),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ten", name="uq_vps_gateway_ten"),
    )
    op.create_index("ix_vps_gateway_vung", "vps_gateway", ["vung"])

    op.create_table(
        "vps_instance",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("ten", sa.String(80), nullable=False, server_default=""),
        sa.Column("plan_id", sa.String(32), nullable=False),
        sa.Column("dia_them_gb", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("os_id", sa.String(32), nullable=False),
        sa.Column("gateway_id", sa.String(36), nullable=False),
        sa.Column("vmid", sa.Integer(), nullable=True),
        sa.Column("trang_thai", sa.String(16), nullable=False,
                  server_default="dang_tao"),
        sa.Column("ly_do", sa.Text(), nullable=False, server_default=""),
        sa.Column("paid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("xoa_sau", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("vmid", name="uq_vps_instance_vmid"),
    )
    op.create_index("ix_vps_instance_user_id", "vps_instance", ["user_id"])
    op.create_index("ix_vps_instance_gateway_id", "vps_instance", ["gateway_id"])
    op.create_index("ix_vps_instance_trang_thai", "vps_instance", ["trang_thai"])
    op.create_index("ix_vps_instance_user_trangthai", "vps_instance",
                    ["user_id", "trang_thai"])
    op.create_index("ix_vps_instance_paid_until", "vps_instance", ["paid_until"])

    op.create_table(
        "vps_ip",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("gateway_id", sa.String(36), nullable=False),
        sa.Column("dia_chi", sa.String(64), nullable=False),
        sa.Column("instance_id", sa.String(36), nullable=True),
        sa.Column("gia_thang_vnd", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("gateway_id", "dia_chi", name="uq_vps_ip_dia_chi"),
        sa.UniqueConstraint("instance_id", name="uq_vps_ip_instance"),
    )
    op.create_index("ix_vps_ip_gateway_id", "vps_ip", ["gateway_id"])

    op.create_table(
        "vps_port_map",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("instance_id", sa.String(36), nullable=False),
        sa.Column("gateway_id", sa.String(36), nullable=False),
        sa.Column("cong_ngoai", sa.Integer(), nullable=False),
        sa.Column("cong_trong", sa.Integer(), nullable=False),
        sa.Column("giao_thuc", sa.String(8), nullable=False, server_default="tcp"),
        sa.Column("nhan", sa.String(32), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("gateway_id", "cong_ngoai", "giao_thuc",
                            name="uq_vps_port_map_cong"),
    )
    op.create_index("ix_vps_port_map_instance_id", "vps_port_map", ["instance_id"])
    op.create_index("ix_vps_port_map_gateway_id", "vps_port_map", ["gateway_id"])

    op.create_table(
        "vps_event",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                  primary_key=True, autoincrement=True),
        sa.Column("instance_id", sa.String(36), nullable=False),
        sa.Column("loai", sa.String(32), nullable=False),
        sa.Column("boi", sa.String(190), nullable=False, server_default=""),
        sa.Column("chi_tiet", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vps_event_instance_id", "vps_event", ["instance_id"])
    op.create_index("ix_vps_event_created_at", "vps_event", ["created_at"])


def downgrade() -> None:
    op.drop_table("vps_event")
    op.drop_table("vps_port_map")
    op.drop_table("vps_ip")
    op.drop_table("vps_instance")
    op.drop_table("vps_gateway")
