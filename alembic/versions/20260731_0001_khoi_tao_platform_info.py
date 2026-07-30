"""khoi tao luoc do - bang platform_info

Revision ID: 0001_platform_info
Revises:
Create Date: 2026-07-31

Migration dau tien cua nen tang. No tao mot bang nho ghi lai luoc do nay duoc
dung khi nao va boi ban nao.

Vi sao khong phai la mot migration rong: mot migration khong tao gi thi khong
kiem chung duoc. Co bang that thi vong upgrade -> downgrade -> upgrade moi
chung minh duoc bo may di tru hoat dong dung, va do la dieu can biet TRUOC khi
co du lieu that trong CSDL.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_platform_info"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_info",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("app_version", sa.String(length=32), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=False,
                  server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("platform_info")
