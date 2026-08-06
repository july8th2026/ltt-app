"""H19.6: ngung dung mau catalog (deprecate) - tach khoi archive

Revision ID: e5f6a4b5c6d7
Revises: d4e5f6a3b4c5
Create Date: 2026-08-06 17:00:00.000000

`archived_at` va `deprecated_at` la HAI viec khac nhau:
  archived_at   = chu so huu tu cat ban RIENG cua minh di;
  deprecated_at = admin rut mot mau CHUNG khoi danh sach chao moi.
Dung chung mot cot thi "ngung chao mau cu" se vo tinh cat luon ban rieng cua
nguoi da clone - ho mat cong cu dang dung ma khong hieu vi sao.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a4b5c6d7"
down_revision: Union[str, None] = "d4e5f6a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BANG = ("ommi_meta_prompt", "ommi_prompt_snippet", "ommi_style")


def upgrade() -> None:
    for t in BANG:
        op.add_column(t, sa.Column("deprecated_at", sa.DateTime(timezone=True),
                                   nullable=True))
        op.add_column(t, sa.Column("deprecated_note", sa.String(length=300),
                                   nullable=False, server_default=""))


def downgrade() -> None:
    for t in BANG:
        op.drop_column(t, "deprecated_note")
        op.drop_column(t, "deprecated_at")
