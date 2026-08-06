"""H19.5: luu gop y cua nguoi dung vao tung phien ban canh

Revision ID: d4e5f6a3b4c5
Revises: c3d4e5f6a2b3
Create Date: 2026-08-06 16:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a3b4c5"
down_revision: Union[str, None] = "c3d4e5f6a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ommi_scene_version",
                  sa.Column("feedback", sa.Text(), nullable=False,
                            server_default=""))


def downgrade() -> None:
    op.drop_column("ommi_scene_version", "feedback")
