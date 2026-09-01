"""voice_tu_dien — từ điển phát âm riêng của từng khách

⭐ Bảng này là ĐẦU KIA của một đường ống đã dựng sẵn từ lâu:
   `features.chuan_bi_van_ban(tu_dien_rieng=...)` →
   `text_pipeline.chuan_hoa(tu_dien_rieng=...)` → `tu_dien.ap_dung(them=...)`.
   Cả ba tầng nhận tham số ấy, và **không ai truyền** cho tới 01/09/2026.

⛔ RÀNG BUỘC DUY NHẤT `(owner_id, tu)` là bắt buộc, không phải cho gọn. Một
   khách có hai mục cho cùng một từ thì phép thay phụ thuộc **thứ tự đọc từ
   CSDL**, và thứ tự ấy không ai bảo đảm — cùng một kịch bản sẽ đọc khác nhau
   giữa hai lần chạy, không lỗi nào báo.

Revision ID: c7b91e4a2f80
Revises: a5f31c07d2b4
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c7b91e4a2f80"
down_revision = "a5f31c07d2b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voice_tu_dien",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                  primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.String(36), nullable=False, index=True),
        sa.Column("tu", sa.String(80), nullable=False),
        sa.Column("thay", sa.String(160), nullable=False),
        sa.Column("ghi_chu", sa.String(200), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("sua_luc", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("owner_id", "tu", name="uq_voice_tudien_owner_tu"),
    )


def downgrade() -> None:
    op.drop_table("voice_tu_dien")
