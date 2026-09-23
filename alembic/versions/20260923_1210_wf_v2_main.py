"""Gop nhanh: wf v2 (dong co) + main (vc_tai_khoan).

Revision ID: 56a971862a15
Revises: e02cebbbd57a, 5e1a9c46b2d7
Create Date: 2026-09-23

Hai dau (head) sinh ra do gop `main` vao `phien/wf-v2`: nhanh wf-v2 them
`e02cebbbd57a` (workflow_event, waitpoint.so_nguon, ...), nhanh main them
`5e1a9c46b2d7` (vc_tai_khoan) sau khi hai nhanh da re. Merge thuan tuy noi
chuoi, khong doi schema.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "56a971862a15"
down_revision = ("e02cebbbd57a", "5e1a9c46b2d7")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
