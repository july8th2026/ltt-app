"""vps: ve console giu them cong VNC va ve cua Proxmox (H39/G3b)

`vncproxy` KHAC `termproxy`: no khong nhan mot dong `user:ticket` mo dau. Ve cua
Proxmox la MAT KHAU VNC, di qua buoc bat tay RFB — nen trinh duyet phai co no,
va server cung phai co no cho query `vncticket` cua URL WebSocket.

Chen mot dong chu vao giua luong nhi phan VNC lam Proxmox dong ket noi ngay va
KHONG NOI GI: trieu chung chi la "console trang". Phat hien 24/08 khi mo trinh
duyet that (quy tac 5 cua CLAUDE.md) — test khong bao gio bat duoc.

Revision ID: 7a41f6d29e83
Revises: 3e8d5a91c7b2
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "7a41f6d29e83"
down_revision = "3e8d5a91c7b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vps_console_ve",
                  sa.Column("cong", sa.Integer(), nullable=False,
                            server_default="0"))
    op.add_column("vps_console_ve",
                  sa.Column("pve_ve", sa.String(255), nullable=False,
                            server_default=""))


def downgrade() -> None:
    op.drop_column("vps_console_ve", "pve_ve")
    op.drop_column("vps_console_ve", "cong")
