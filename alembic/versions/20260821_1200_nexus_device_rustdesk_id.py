"""nexus: cot rustdesk_id cho cuong che billing o tang relay (Q101, P-relay)

Them mot cot NOT NULL (server_default "") vao `nexus_devices`: ID RustDesk cua
engine tren may, do client bao len. Relay LTT (hbbs da fork) anh xa ID -> tai
khoan -> trang thai tra phi de tu choi moi gioi ket noi khi chua tra.

Chi them, khong xoa du lieu. server_default "" de dong cu (neu co) hop le.

Revision ID: 5a3a13144782
Revises: 455d0097906f
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "5a3a13144782"
down_revision = "455d0097906f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("nexus_devices", sa.Column(
        "rustdesk_id", sa.String(length=32), nullable=False,
        server_default=""))


def downgrade() -> None:
    op.drop_column("nexus_devices", "rustdesk_id")
