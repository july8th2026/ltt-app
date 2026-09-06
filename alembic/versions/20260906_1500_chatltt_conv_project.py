"""chatltt_conversation.project_id — hội thoại thuộc một dự án. (H44 B5 bước 1)

## Add-only, và ở đây "add-only" không phải một khẩu hiệu

Bảng này có **220 hàng THẬT** trên production. Mọi cột thêm vào phải `nullable`
và không có `server_default` bắt buộc — 220 hội thoại đang sống **không** thuộc
dự án nào, và chúng sẽ tiếp tục không thuộc dự án nào.

⇒ Dự án là **tuỳ chọn**. Một cột `NOT NULL DEFAULT ''` sẽ biến nó thành một tầng
  mọc thêm trên đầu mọi người, và không ai xin điều đó.

## ⛔ KHÔNG khoá ngoại, KHÔNG `ON DELETE CASCADE`

Xoá một dự án phải trả `project_id` về `NULL` và **giữ nguyên hội thoại**. Một
cái thư mục bị xoá không được mang theo thứ nó đựng: người dùng nghĩ mình đang
dọn một cái nhãn, không phải đốt nội dung.

⭐ Và `app_projects` là bảng của **nền tảng**, dùng chung cho mọi app. Một khoá
   ngoại từ bảng của một app trỏ vào đó là buộc lõi phải biết app nào đang bám
   vào nó — đúng thứ hợp đồng app sinh ra để tránh.

Revision ID: f2c48b71e903
Revises: d1a7f4c9b620
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f2c48b71e903"
down_revision = "d1a7f4c9b620"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chatltt_conversation",
                  sa.Column("project_id", sa.String(36), nullable=True))
    # Liet ke hoi thoai cua MOT du an. `user_id` dung dau vi moi truy van cua
    # ChatLTT deu bat dau bang no — khong ham nao doc theo `id` tran.
    op.create_index("ix_chatltt_conv_project", "chatltt_conversation",
                    ["user_id", "project_id"])


def downgrade() -> None:
    op.drop_index("ix_chatltt_conv_project", table_name="chatltt_conversation")
    op.drop_column("chatltt_conversation", "project_id")
