"""them cot xoay secret cho webhook (EXT-10)

Xoay secret ma co hieu luc tuc thi se lam hong MOI lan giao dang bay tren duong
o mot receiver da doi sang secret moi — dung luc khach dang nhin. Nen giu secret
cu them mot cua so an han va KY BANG CA HAI trong khoang do.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("public_api_webhooks",
                  sa.Column("previous_secret_enc", sa.Text(), nullable=False,
                            server_default=""))
    op.add_column("public_api_webhooks",
                  sa.Column("previous_secret_until",
                            sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("public_api_webhooks", "previous_secret_until")
    op.drop_column("public_api_webhooks", "previous_secret_enc")
