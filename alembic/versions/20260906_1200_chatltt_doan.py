"""chatltt_doan — đoạn văn bản đã trích. Bảng NÀY giữ chữ. (H44 P06 bước 3)

## Vì sao bảng này giữ chữ trong khi `chatltt_tep` thì không

Trông mâu thuẫn, nhưng hai bảng trả lời hai câu khác nhau:

* `chatltt_tep` nói **tệp nào thuộc hội thoại nào**. Byte gốc nằm ở `storage`,
  và giữ chúng ở CSDL là dựng một kho lưu trữ thứ hai đi vòng qua cửa credit
  của `upload_sessions` — đúng cửa mà `upload_sessions.py` tự viết ra để chặn.
* `chatltt_doan` giữ **chữ đã trích**: một biểu diễn *dẫn xuất* và *có trần*.
  Chỉ số FTS (bước 4) phải chạy trên chính chữ ấy; đẩy nó ra ngoài CSDL rồi kéo
  về mỗi lần tìm là làm chậm đúng thao tác nóng nhất.

⇒ **Byte gốc ở ngoài, chữ dẫn xuất ở trong.**

## `trang` tồn tại vì bước 5, không vì gỡ lỗi

P06 bước 5 đòi mỗi câu trả lời trỏ về `(tep_id, doan_id, trang)`. Số trang chỉ
tồn tại trong lúc **đọc** tệp — không suy ngược ra được từ chuỗi chữ. Không ghi
lúc trích thì mất vĩnh viễn.

⭐ `trang = 0` nghĩa là **không biết** (định dạng không có khái niệm trang, ví
   dụ `.txt`), không phải "trang đầu" — nên trang thật bắt đầu từ 1.

## `ux_chatltt_doan_tep_thu_tu` — vì sao unique

Trích lại một tệp phải **thay** các đoạn cũ, không chồng thêm một bộ thứ hai.
Hai bộ đoạn cho cùng một tệp làm truy hồi trả kết quả trùng và làm trích dẫn
trỏ vào bản nào không ai biết. Ràng buộc ở CSDL vì một `if` trong worker thì
quên được — cùng luật `ux_chatltt_approval_step`.

Revision ID: e5b2d9c4a71f
Revises: a3f92c5d7e14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e5b2d9c4a71f"
down_revision = "a3f92c5d7e14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chatltt_doan",
        sa.Column("id", sa.String(40), primary_key=True),
        # ⛔ String(36), khong phai so — apps/ltt_voice/tables.py:66-75.
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("conversation_id", sa.String(40), nullable=False),
        sa.Column("tep_id", sa.String(40), nullable=False),
        sa.Column("thu_tu", sa.Integer(), nullable=False),
        sa.Column("trang", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("noi_dung", sa.Text(), nullable=False, server_default=""),
        sa.Column("so_ky_tu", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bam", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ux_chatltt_doan_tep_thu_tu", "chatltt_doan",
                    ["tep_id", "thu_tu"], unique=True)
    op.create_index("ix_chatltt_doan_conv", "chatltt_doan", ["conversation_id"])
    op.create_index("ix_chatltt_doan_user", "chatltt_doan", ["user_id"])
    op.create_index("ix_chatltt_doan_tep", "chatltt_doan", ["tep_id"])


def downgrade() -> None:
    op.drop_table("chatltt_doan")
