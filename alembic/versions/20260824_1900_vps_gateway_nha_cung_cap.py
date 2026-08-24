"""vps: id cua cong vao ben nha cung cap (H39/G2)

Muon gan mot Reserved IP vao cong vao thi phai biet id cua no ben Vultr. Tim
theo NHAN moi lan la mot vong goi API thua va mot cho de sai: doi ten cong vao
tren bang dieu khien la app khong tim thay nua, va no hong dung luc khach dang
cho may.

Revision ID: 9c3b18e5f27a
Revises: 6f2a91d47c30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "9c3b18e5f27a"
down_revision = "6f2a91d47c30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vps_gateway",
                  sa.Column("nha_cung_cap_id", sa.String(64), nullable=False,
                            server_default=""))


def downgrade() -> None:
    op.drop_column("vps_gateway", "nha_cung_cap_id")
