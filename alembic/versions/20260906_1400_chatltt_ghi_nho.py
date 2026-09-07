"""chatltt_ghi_nho — mẩu ghi nhớ, ba tầng phạm vi. (H44 B4 bước 1)

## Bảng này khác mọi bảng ChatLTT trước nó ở một điểm: nó vào MỌI lượt

`chatltt_doan` chỉ được đọc khi model gọi `noi_bo.tim_tai_lieu`. Ghi nhớ thì
được tiêm vào ngữ cảnh của **mọi** lượt trong phạm vi — nên mỗi hàng ở đây là
một khoản thuế token **lặp lại mãi**, không phải một hàng nằm im.

⇒ Hai hệ quả đi thẳng vào lược đồ:
  1. `noi_dung` là `String(500)` chứ không `Text` — trần ép ở CSDL.
  2. `ix_chatltt_ghi_nho_tiem` là chỉ số **nóng nhất** của cả tính năng.

## 🔴 `muc_tieu_id` `NOT NULL DEFAULT ''` — cố ý, đừng "sửa" thành NULL

Ràng buộc chống trùng là bộ bốn `(user_id, pham_vi, muc_tieu_id, bam)`. Với
`pham_vi='nguoi_dung'` thì không có mục tiêu. Để `NULL` trông đúng ngữ nghĩa
hơn, nhưng **`NULL` không bằng `NULL`** trong SQL ⇒ `UNIQUE` mất tác dụng đúng
ở phạm vi phổ biến nhất, và triệu chứng là kho tự nhân đôi chứ không phải một
lỗi ràng buộc.

⛔ `NULLS NOT DISTINCT` (PostgreSQL 15+) sửa được ở production nhưng **không có
   ở SQLite**, tức đường chạy test. Một bất biến chỉ đúng ở nơi ta không kiểm là
   một bất biến sẽ vỡ ở nơi ta không nhìn.

## Vì sao unique trên `bam` chứ không trên `noi_dung`

Chỉ số btree PostgreSQL có trần ~2.704 byte/hàng; 500 ký tự tiếng Việt ≈ 1.500
byte, cộng ba cột kia thì đã sát. Một ràng buộc chỉ vỡ với **hàng dài** vỡ đúng
lúc người dùng ghi mẩu quan trọng nhất.

Revision ID: d1a7f4c9b620
Revises: b8c31f6e9d24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d1a7f4c9b620"
down_revision = "b8c31f6e9d24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chatltt_ghi_nho",
        sa.Column("id", sa.String(40), primary_key=True),
        # ⛔ String(36), khong phai so — apps/ltt_voice/tables.py:66-75.
        sa.Column("user_id", sa.String(36), nullable=False),
        # nguoi_dung | du_an | hoi_thoai — PHAM VI AP DUNG, khong phai loai noi dung.
        sa.Column("pham_vi", sa.String(16), nullable=False),
        # Chuoi rong khi pham_vi='nguoi_dung'. Xem docstring: dung doi thanh NULL.
        sa.Column("muc_tieu_id", sa.String(40), nullable=False,
                  server_default=""),
        # nguoi | model — quyet dinh QUYEN SUA, doc lap voi pham_vi.
        sa.Column("nguon", sa.String(8), nullable=False),
        sa.Column("noi_dung", sa.String(500), nullable=False),
        sa.Column("bam", sa.String(64), nullable=False, server_default=""),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ux_chatltt_ghi_nho_khoa", "chatltt_ghi_nho",
                    ["user_id", "pham_vi", "muc_tieu_id", "bam"], unique=True)
    op.create_index("ix_chatltt_ghi_nho_tiem", "chatltt_ghi_nho",
                    ["user_id", "pham_vi", "muc_tieu_id"])


def downgrade() -> None:
    op.drop_table("chatltt_ghi_nho")
