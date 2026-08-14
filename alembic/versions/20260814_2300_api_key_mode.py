"""danh dau khoa API la live hay test (EXT-12)

Mot cot chu khong phai mot bang: che do test dung y nguyen bang khoa, y nguyen
so credit, y nguyen hang doi job. Bang thu hai se la thu hai phai giu dung, va
khi hai ban sao lech nhau thi sandbox day nguoi tich hop vao mot loi that o
production.

Khoa cu deu la "live". Server default de dong cu khong bi NULL, va model cung
dat default nen khong phu thuoc vao rieng mot phia.

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b4c5d6e7f8a9"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "developer_api_keys",
        sa.Column("mode", sa.String(8), nullable=False, server_default="live"),
    )


def downgrade() -> None:
    op.drop_column("developer_api_keys", "mode")
