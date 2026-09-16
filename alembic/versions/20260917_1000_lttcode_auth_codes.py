"""`lttcode_auth_codes`: mã cấp quyền một lần cho "Đăng nhập LTT Studios" của LTTCODE.

Revision ID: 7c2e5a91d4b3
Revises: f4a7c2d9e610

Bảng mới, không đụng bảng cũ: migration chạy được trước khi mã mới lên, và mã
cũ không biết bảng này vẫn chạy bình thường. `downgrade()` bỏ bảng — nội dung là
mã sống 120 giây, không có gì cần giữ.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "7c2e5a91d4b3"
down_revision = "f4a7c2d9e610"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lttcode_auth_codes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("code_challenge", sa.String(64), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("device", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_lttcode_auth_codes_expires_at", "lttcode_auth_codes", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_lttcode_auth_codes_expires_at", table_name="lttcode_auth_codes")
    op.drop_table("lttcode_auth_codes")
