"""Bang phien dang nhap nen tang cua video_crawler: vc_phien.

Revision ID: 9c3e5a1d7f20
Revises: e4a19c07b5d2
Create Date: 2026-09-22

## VI SAO CO BANG NAY

Nen can dang nhap (TikTok tim tu khoa, Facebook Page, Instagram, Twitter, Douyin...)
can cookie cua CHINH khach. Donor ViralCrawl dung MOT profile Chromium chung may cho
moi nguoi — cam o SaaS nhieu khach. Moi hang = cookie cua mot (owner, nen), MA HOA
bang `platform_core.secretbox`, chi giu cookie cua ten mien nen do.

Khai o `platform_core/public_api/governance.py` (hang `vc_phien`, CONTENT).

## ROLLBACK

Them thuan tuy. `downgrade` xoa dung bang nay va chi so cua no.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "9c3e5a1d7f20"
down_revision = "e4a19c07b5d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vc_phien",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("nen_tang", sa.String(length=32), nullable=False),
        sa.Column("cookie_ma_hoa", sa.Text(), nullable=False),
        sa.Column("so_cookie", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("het_han_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tao_luc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cap_nhat_luc", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "nen_tang", name="uq_vc_phien_owner_nen"),
    )
    op.create_index("ix_vc_phien_owner_id", "vc_phien", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_vc_phien_owner_id", table_name="vc_phien")
    op.drop_table("vc_phien")
