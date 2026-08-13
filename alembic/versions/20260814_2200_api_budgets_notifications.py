"""them ngan sach va thong bao cho khu API (EXT-11)

Ngan sach QUAN SAT chi tieu, khong ghi so credit: khong cot nao o day co the
lam doi mot dong `credit_entries`. Ngan sach "cung" thi tu choi loi goi ke tiep;
ngan sach "mem" chi bao. Hai loi hua khac nhau nen la hai truong khac nhau.

Thong bao khu trung theo (user, kind, subject) trong mot cua so cooldown — mot
kenh canh bao qua on thi khach tat het, ma tat het thi giong het nhu khong co.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_budgets",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False,
                  server_default="account"),
        sa.Column("project_id", sa.String(36), nullable=False,
                  server_default=""),
        sa.Column("period", sa.String(8), nullable=False,
                  server_default="month"),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("thresholds", sa.JSON(), nullable=False),
        sa.Column("hard_cap", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_budgets_user_id", "api_budgets", ["user_id"])
    op.create_index("ix_api_budgets_owner", "api_budgets", ["user_id", "scope"])

    op.create_table(
        "api_notifications",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("subject", sa.String(120), nullable=False, server_default=""),
        sa.Column("title", sa.String(200), nullable=False, server_default=""),
        sa.Column("body", sa.String(1000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_notifications_user_id", "api_notifications",
                    ["user_id"])
    op.create_index("ix_api_notifications_dedupe", "api_notifications",
                    ["user_id", "kind", "subject", "created_at"])
    op.create_index("ix_api_notifications_unread", "api_notifications",
                    ["user_id", "read_at"])


def downgrade() -> None:
    op.drop_index("ix_api_notifications_unread", table_name="api_notifications")
    op.drop_index("ix_api_notifications_dedupe", table_name="api_notifications")
    op.drop_index("ix_api_notifications_user_id", table_name="api_notifications")
    op.drop_table("api_notifications")
    op.drop_index("ix_api_budgets_owner", table_name="api_budgets")
    op.drop_index("ix_api_budgets_user_id", table_name="api_budgets")
    op.drop_table("api_budgets")
