"""nexus: cau noi engine vao phien (W1)

Them ba cot vao `nexus_sessions` de agent may dich BAO chi tiet ket noi RustDesk
khi doi ve, va controller lay ve:

* `engine_id` — dinh danh ket noi RustDesk (so, KHONG bi mat, nhu so dien thoai)
* `engine_secret_enc` — mat khau MOT-LAN cua phien, **ma hoa at-rest** bang
  `platform_core.secretbox` (khong bao gio luu tho)
* `engine_reported_at` — luc agent bao (NULL = chua bao)

Tat ca them dang NULLABLE / co server_default: bang co the da co du lieu (phien
cu) va migration khong duoc lam vo dong nao. Xoa mat khau khi phien ket thuc la
viec cua tang nghiep vu (sessions.py), khong phai cua schema.

Chi them, khong xoa du lieu. Downgrade go dung ba cot.

Revision ID: 7445f5031805
Revises: d649cfad754f
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# Sinh ngau nhien + doi chieu voi id dang co (bai hoc R10: mot id TRONG hop ly
# ma trung tao vong lap va giet moi lenh alembic).
revision = "7445f5031805"
down_revision = "d649cfad754f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("nexus_sessions", sa.Column(
        "engine_id", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("nexus_sessions", sa.Column(
        "engine_secret_enc", sa.Text(), nullable=False, server_default=""))
    op.add_column("nexus_sessions", sa.Column(
        "engine_reported_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("nexus_sessions", "engine_reported_at")
    op.drop_column("nexus_sessions", "engine_secret_enc")
    op.drop_column("nexus_sessions", "engine_id")
