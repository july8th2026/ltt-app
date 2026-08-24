"""vps: dai cong DA NAP SAN DNAT tren gateway (H39, mo hinh CHIA CONG)

⚠️ REVISION NAY DA BI THAY THE, nhung KHONG DUOC XOA FILE.

Mo hinh chia cong bi bo ngay 2026-08-24 (moi may mot IP cong khai rieng), va hai
cot duoi day khong con y nghia. Revision ke tiep `6f2a91d47c30` xoa chung.

Ly do phai giu file nay: no DA CHAY tren CSDL that (`alembic_version` cua
production tung o dung day). Xoa file cua mot revision da ap dung thi
`alembic upgrade head` chet ngay voi "Can't locate revision identified by
'4d7e91c2a6b8'" — va no chan CA CUM deploy, khong rieng app VPS. Lich su
migration la thu chi duoc them vao, khong duoc viet lai.

Revision ID: 4d7e91c2a6b8
Revises: 8b2c5d1e40a7
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "4d7e91c2a6b8"
down_revision = "8b2c5d1e40a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for ten in ("dnat_dau", "dnat_cuoi"):
        op.add_column("vps_gateway",
                      sa.Column(ten, sa.Integer(), nullable=False,
                                server_default="0"))


def downgrade() -> None:
    for ten in ("dnat_cuoi", "dnat_dau"):
        op.drop_column("vps_gateway", ten)
