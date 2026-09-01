"""voice_profile.dung_chung — kho giọng dùng chung của nền tảng

🔴 MẶC ĐỊNH `False`, VÀ MIGRATION NÀY KHÔNG ĐẶT `True` CHO BẤT KỲ DÒNG NÀO.

   Một giọng nhân bản là dữ liệu sinh trắc của một con người. Một migration
   "tiện tay" bật cột này cho các dòng cũ sẽ **công khai giọng của khách** cho
   mọi tài khoản khác — và đó là loại lỗi không lấy lại được bằng một bản vá,
   vì thứ đã bị đọc thì đã bị đọc.

   Bật một giọng lên kho chung là một hành động **có chủ ý, từng cái một**, qua
   `tools/dat_giong_dung_chung.py`.

Revision ID: a5f31c07d2b4
Revises: d4e0a63b8f29
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a5f31c07d2b4"
down_revision = "d4e0a63b8f29"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "voice_profile",
        sa.Column("dung_chung", sa.Boolean(), nullable=False,
                  server_default=sa.false()))
    # Index vì MỌI truy vấn danh sách sẽ lọc theo nó cùng `owner_id`.
    op.create_index("ix_voice_profile_dung_chung", "voice_profile",
                    ["dung_chung"])


def downgrade() -> None:
    op.drop_index("ix_voice_profile_dung_chung", table_name="voice_profile")
    op.drop_column("voice_profile", "dung_chung")
