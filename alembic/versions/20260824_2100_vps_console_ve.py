"""vps: bang ve mot-lan cho console (H39/G3b)

Ve phai nam trong CSDL chu khong phai bo nho: tang web chay NHIEU TIEN TRINH, va
ve cap o tien trinh A ma WebSocket roi vao tien trinh B thi console khong bao gio
mo duoc — trieu chung la "luc duoc luc khong".

Luu BAM SHA-256 chu khong luu ve tho, cung ly do `sessions.id` lam vay (P0-5):
ai doc duoc CSDL thi doc duoc ve, ma ve la quyen xem man hinh may cua khach.

Revision ID: 3e8d5a91c7b2
Revises: 9c3b18e5f27a
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "3e8d5a91c7b2"
down_revision = "9c3b18e5f27a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vps_console_ve",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("instance_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("da_dung_luc", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_vps_console_ve_instance_id", "vps_console_ve",
                    ["instance_id"])
    op.create_index("ix_vps_console_ve_created_at", "vps_console_ve",
                    ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_vps_console_ve_created_at", table_name="vps_console_ve")
    op.drop_index("ix_vps_console_ve_instance_id", table_name="vps_console_ve")
    op.drop_table("vps_console_ve")
