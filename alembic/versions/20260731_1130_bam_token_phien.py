"""bam token phien (P0-5): sessions.id luu SHA-256 hex thay vi token tho

Revision ID: b1c2d3e4f5a6
Revises: d5f7989d5101
Create Date: 2026-07-31 11:30:00.000000

Vi sao: id cua bang sessions vua la token phien vua la KHOA CHINH. sqladmin
phoi khoa chinh ra checkbox/URL tung dong, nen luu token tho = admin xem trang
Phien la lay duoc token song -> mao danh (audit 2026-07-31, P0-5). Tu nay cookie
mang token tho, DB chi luu SHA-256 (64 ky tu hex) cua no.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'd5f7989d5101'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Phien cu co id = token THO (43 ky tu). Tu nay tra cuu bang SHA-256 (64 ky
    # tu) cua token trong cookie, nen phien cu khong con khop -> xoa cho sach,
    # nguoi dung dang nhap lai. An toan: mat phien = phai dang nhap lai, khong
    # mat du lieu.
    op.execute("DELETE FROM sessions")
    # Chi Postgres can (va lam duoc) noi rong cot. SQLite bo qua do dai VARCHAR
    # va chi dung de test bo may migration, nen khong doi gi.
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column('sessions', 'id',
                        existing_type=sa.String(length=43),
                        type_=sa.String(length=64),
                        existing_nullable=False)


def downgrade() -> None:
    op.execute("DELETE FROM sessions")
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column('sessions', 'id',
                        existing_type=sa.String(length=64),
                        type_=sa.String(length=43),
                        existing_nullable=False)
