"""chatltt_cay_hoi_thoai — ba bảng của ChatLTT (H43 Phase 07)

Cây hội thoại (`parent_id`), khối nội dung typed (`blocks` JSON) và một bảng
thi hành ghi `partial_text` theo nhịp để reload dựng lại sự thật từ CSDL.
Không chạm `chat_conversations`/`chat_messages` của Chat AI Studio.

Xem `apps/chatltt/tables.py` để biết vì sao ba bảng và hai bất biến tầng ghi.

Revision ID: 7d2c1e9f4a03
Revises: c7b91e4a2f80
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "7d2c1e9f4a03"
down_revision = "c7b91e4a2f80"
branch_labels = None
depends_on = None


def _thoi_gian(ten: str, nullable: bool = False):
    return sa.Column(ten, sa.DateTime(timezone=True), nullable=nullable,
                     server_default=None if nullable else sa.func.now())


def upgrade() -> None:
    op.create_table(
        "chatltt_conversation",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False, server_default=""),
        sa.Column("model_alias", sa.String(64), nullable=False, server_default=""),
        sa.Column("current_leaf_id", sa.String(40), nullable=True),
        _thoi_gian("archived_at", nullable=True),
        _thoi_gian("deleted_at", nullable=True),
        _thoi_gian("created_at"),
        _thoi_gian("updated_at"),
    )
    op.create_index("ix_chatltt_conv_user_updated", "chatltt_conversation",
                    ["user_id", "deleted_at", "updated_at"])

    op.create_table(
        "chatltt_message",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("conversation_id", sa.String(40), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("parent_id", sa.String(40), nullable=True),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("blocks", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="done"),
        sa.Column("model_alias", sa.String(64), nullable=False, server_default=""),
        sa.Column("execution_id", sa.String(40), nullable=True),
        _thoi_gian("created_at"),
        _thoi_gian("updated_at"),
    )
    op.create_index("ix_chatltt_msg_conv_parent", "chatltt_message",
                    ["conversation_id", "parent_id"])
    op.create_index("ix_chatltt_msg_conv_created", "chatltt_message",
                    ["conversation_id", "created_at"])

    op.create_table(
        "chatltt_execution",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("message_id", sa.String(40), nullable=False, index=True),
        sa.Column("conversation_id", sa.String(40), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("job_id", sa.String(36), nullable=True, index=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="streaming"),
        sa.Column("partial_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("reasoning_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("finish_reason", sa.String(32), nullable=False, server_default=""),
        sa.Column("usage", sa.JSON(), nullable=False),
        sa.Column("credit_giu", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credit_thu", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credit_hoan", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(40), nullable=False, server_default=""),
        sa.Column("error_text", sa.String(500), nullable=False, server_default=""),
        sa.Column("seq", sa.Integer(), nullable=False, server_default="0"),
        _thoi_gian("created_at"),
        _thoi_gian("updated_at"),
        _thoi_gian("finished_at", nullable=True),
    )
    op.create_index("ix_chatltt_exec_conv_status", "chatltt_execution",
                    ["conversation_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_chatltt_exec_conv_status", table_name="chatltt_execution")
    op.drop_table("chatltt_execution")
    op.drop_index("ix_chatltt_msg_conv_created", table_name="chatltt_message")
    op.drop_index("ix_chatltt_msg_conv_parent", table_name="chatltt_message")
    op.drop_table("chatltt_message")
    op.drop_index("ix_chatltt_conv_user_updated", table_name="chatltt_conversation")
    op.drop_table("chatltt_conversation")
