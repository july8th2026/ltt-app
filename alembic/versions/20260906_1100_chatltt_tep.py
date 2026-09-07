"""chatltt_tep — bảng LIÊN KẾT tệp ↔ hội thoại. Không chứa byte nào. (H44 P06 b2)

## Vì sao một bảng mới chứ không phải `Job.params`

`Job.params` là JSON nên **về mặt kỹ thuật** nó chứa được `conversation_id`.
P06 §7 vẫn bác, và lý do không kỹ thuật chút nào: `governance.py` xếp `jobs` là
**OPERATIONAL** — tự già đi theo hạn riêng — còn `chatltt_*` là **CONTENT**.
Treo tri thức của khách vào một bảng tự dọn là hẹn ngày người dùng mở lại một
hội thoại còn nguyên vẹn và thấy tệp đã biến mất khỏi nó.

🔴 Lần **thứ ba** cùng một ca: P03 đã ghi `chatltt_run` **không thể** là
   OPERATIONAL vì đúng lý do ấy.

## Migration CHỈ THÊM

Không `alter`, không `drop`, không chạm bảng nào đang có dữ liệu thật. Hạ nó lại
là `drop_table` một bảng vừa tạo — không mất một hàng nào của ai.
`test_822.test_migration_chi_THEM_bang_moi` đọc chính tệp này bằng AST để chốt.

## `unique` là CẶP `(conversation_id, upload_id)`, không phải riêng `upload_id`

Hỏi cùng một tài liệu ở hai hội thoại là việc bình thường; ràng buộc riêng
`upload_id` biến việc bình thường ấy thành lỗi 500. Chặt hơn không phải an toàn
hơn. Còn ràng buộc **cặp** thì cần thật: bấm hai lần / F5 giữa chừng là ca
thường, và một `if` trong route quên được trong khi CSDL thì không — cùng luật
`ux_chatltt_approval_step`.

Revision ID: a3f92c5d7e14
Revises: c7d41e8a2b93
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a3f92c5d7e14"
down_revision = "c7d41e8a2b93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chatltt_tep",
        sa.Column("id", sa.String(40), primary_key=True),
        # ⛔ String(36), khong phai so — bai hoc apps/ltt_voice/tables.py:66-75:
        #    khai so ⇒ moi khach thanh chu so 0.
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("conversation_id", sa.String(40), nullable=False),
        sa.Column("upload_id", sa.String(36), nullable=False),
        sa.Column("ten_tep", sa.String(255), nullable=False, server_default=""),
        sa.Column("content_type", sa.String(128), nullable=False, server_default=""),
        sa.Column("kich_thuoc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trang_thai_trich", sa.String(16), nullable=False,
                  server_default="moi"),
        sa.Column("job_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("so_doan", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ly_do_loi", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ux_chatltt_tep_conv_upload", "chatltt_tep",
                    ["conversation_id", "upload_id"], unique=True)
    op.create_index("ix_chatltt_tep_user", "chatltt_tep",
                    ["user_id", "created_at"])
    op.create_index("ix_chatltt_tep_trich", "chatltt_tep", ["trang_thai_trich"])
    op.create_index("ix_chatltt_tep_conv", "chatltt_tep", ["conversation_id"])
    op.create_index("ix_chatltt_tep_upload", "chatltt_tep", ["upload_id"])
    op.create_index("ix_chatltt_tep_user_id", "chatltt_tep", ["user_id"])


def downgrade() -> None:
    op.drop_table("chatltt_tep")
