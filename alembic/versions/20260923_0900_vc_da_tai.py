"""Bang dedup ben cua video_crawler: vc_da_tai.

Revision ID: 3b7d2f9e1c48
Revises: 9c3e5a1d7f20
Create Date: 2026-09-23

## VI SAO CO BANG NAY

"Cao khong trung" truoc day suy tu `jobs.result` cua job tai da xong. `jobs.result`
bi xoa sau 30 ngay (governance hang `jobs`) va chi quet 500 job gan nhat, nen
video tai tu hon 30 ngay bi tai + thu tien lai. Hai job cung luc cung video cua
mot user cung deu tai va deu thu tien (SO_LOI L4, review W1). Chu du an duyet Q4
(22/09): moi hang = mot (owner, nen, video_id); UNIQUE o CSDL la cho quyet dinh
job nao duoc tai. Khai o `platform_core/public_api/governance.py` (hang `vc_da_tai`).

## KHONG DI TRU DU LIEU CU

Muc cua job da xong truoc khi co bang KHONG duoc chep vao day: app con sau co
`LTT_VIDEO_CRAWLER` (tat tren production), chua co khach — pham vi dev. Doc lai
`jobs.result` cu chi lam ton tai lai gioi han 30 ngay ma bang nay sinh ra de bo.

## ROLLBACK

Them thuan tuy. `downgrade` xoa dung bang nay va chi so cua no.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "3b7d2f9e1c48"
down_revision = "9c3e5a1d7f20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vc_da_tai",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("nen_tang", sa.String(length=32), nullable=False),
        sa.Column("video_id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("tep", sa.String(length=512), nullable=True),
        sa.Column("trang_thai", sa.String(length=16), nullable=False),
        sa.Column("tao_luc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cap_nhat_luc", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "nen_tang", "video_id", name="uq_vc_da_tai_owner_nen_video"),
    )
    op.create_index("ix_vc_da_tai_owner_id", "vc_da_tai", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_vc_da_tai_owner_id", table_name="vc_da_tai")
    op.drop_table("vc_da_tai")
