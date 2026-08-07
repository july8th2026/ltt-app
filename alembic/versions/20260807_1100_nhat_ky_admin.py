"""F-06 — bảng nhật ký thao tác quản trị

Audit LTT-AQA 2026-08-07 (control-plane/quan-tri-user), finding F-06, D6 chốt làm.

`cap_tay(by=)` đã ghi `admin=` vào ghi chú bút toán nên **tiền** truy được. Nhưng
đổi vai trò và vô hiệu hoá tài khoản thì không để lại dấu vết nào. Bảng này lấp
chỗ đó, và chỉ ghi thêm — cùng nguyên tắc với sổ credit.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nhat_ky_admin",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("admin_email", sa.String(255), nullable=False, server_default=""),
        sa.Column("hanh_dong", sa.String(64), nullable=False),
        sa.Column("doi_tuong", sa.String(255), nullable=False, server_default=""),
        sa.Column("chi_tiet", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nhat_ky_admin_created_at", "nhat_ky_admin", ["created_at"])
    op.create_index("ix_nhat_ky_admin_admin_email", "nhat_ky_admin", ["admin_email"])
    op.create_index("ix_nhat_ky_admin_hanh_dong", "nhat_ky_admin", ["hanh_dong"])


def downgrade() -> None:
    op.drop_index("ix_nhat_ky_admin_hanh_dong", table_name="nhat_ky_admin")
    op.drop_index("ix_nhat_ky_admin_admin_email", table_name="nhat_ky_admin")
    op.drop_index("ix_nhat_ky_admin_created_at", table_name="nhat_ky_admin")
    op.drop_table("nhat_ky_admin")
