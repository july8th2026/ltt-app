"""chatltt_v3_dieu_phoi_tool — ba bảng của điều phối tool (H44 P03)

CHỈ THÊM. Không sửa `chatltt_conversation`/`chatltt_message`, không đổi nghĩa
cột nào của `chatltt_execution` — chỉ nối thêm hai cột `nullable` để một hàng V1
vẫn hợp lệ với cả hai NULL.

Đó là điều kiện của đường lùi (`02_ADR_ORCHESTRATION.md` §7): hạ migration này
làm mất `run`/`step`/`approval`, và hội thoại cũ **không đổi một byte**.

Xem `apps/chatltt/tables.py` và `docs/CHATLTT_V3/02_HOP_DONG.md` §2.

Revision ID: 4b8e21c6d907
Revises: 7d2c1e9f4a03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "4b8e21c6d907"
down_revision = "7d2c1e9f4a03"
branch_labels = None
depends_on = None


def _tg(ten: str, nullable: bool = False):
    return sa.Column(ten, sa.DateTime(timezone=True), nullable=nullable,
                     server_default=None if nullable else sa.func.now())


def upgrade() -> None:
    op.create_table(
        "chatltt_run",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("conversation_id", sa.String(40), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("message_id", sa.String(40), nullable=False, index=True),
        sa.Column("trang_thai", sa.String(24), nullable=False, server_default="CREATED"),
        sa.Column("so_vong_model", sa.Integer, nullable=False, server_default="0"),
        sa.Column("so_loi_goi_tool", sa.Integer, nullable=False, server_default="0"),
        # Ba cột DẪN XUẤT — cộng từ `chatltt_execution` con. Không phải bút toán.
        sa.Column("credit_giu_tong", sa.Integer, nullable=False, server_default="0"),
        sa.Column("credit_thu_tong", sa.Integer, nullable=False, server_default="0"),
        sa.Column("credit_hoan_tong", sa.Integer, nullable=False, server_default="0"),
        # Chi phí CHÍNH XÁC tích luỹ (milli-credit) — `credit_entries` chỉ lưu
        # credit nguyên đã làm tròn, nên phần lẻ phải sống ở đây (R2b).
        sa.Column("mcredit_tich_luy", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ly_do_ket", sa.String(24), nullable=False, server_default=""),
        sa.Column("lease_id", sa.String(40), nullable=False, server_default=""),
        _tg("created_at"), _tg("updated_at"), _tg("finished_at", nullable=True),
    )
    op.create_index("ix_chatltt_run_conv", "chatltt_run",
                    ["conversation_id", "created_at"])
    op.create_index("ix_chatltt_run_user_tt", "chatltt_run", ["user_id", "trang_thai"])

    op.create_table(
        "chatltt_step",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("run_id", sa.String(40), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("thu_tu", sa.Integer, nullable=False),
        sa.Column("loai", sa.String(16), nullable=False),
        sa.Column("execution_id", sa.String(40), nullable=True),
        sa.Column("tool_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("tool_call_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("doi_so", sa.JSON, nullable=False),
        # Chuỗi đối số TRƯỚC khi gộp — không dựng lại được từ kết quả.
        sa.Column("doi_so_tho", sa.Text, nullable=False, server_default=""),
        sa.Column("ket_qua", sa.JSON, nullable=False),
        sa.Column("job_id", sa.String(36), nullable=True, index=True),
        sa.Column("trang_thai", sa.String(16), nullable=False, server_default=""),
        sa.Column("bam_trung", sa.String(64), nullable=False, server_default=""),
        _tg("created_at"),
    )
    op.create_index("ux_chatltt_step_thu_tu", "chatltt_step", ["run_id", "thu_tu"],
                    unique=True)
    op.create_index("ix_chatltt_step_bam", "chatltt_step", ["run_id", "bam_trung"])

    op.create_table(
        "chatltt_approval",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("step_id", sa.String(40), nullable=False),
        sa.Column("run_id", sa.String(40), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("doi_so", sa.JSON, nullable=False),
        sa.Column("policy_class", sa.String(16), nullable=False),
        sa.Column("bao_gia_credit", sa.Integer, nullable=False, server_default="0"),
        sa.Column("phien_ban_gia", sa.String(32), nullable=False, server_default=""),
        sa.Column("quyet_dinh", sa.String(16), nullable=False, server_default="cho"),
        sa.Column("doi_so_da_sua", sa.JSON, nullable=True),
        sa.Column("quyet_boi", sa.String(36), nullable=False, server_default=""),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        _tg("created_at"), _tg("quyet_luc", nullable=True),
    )
    # 🔴 HAI RÀNG BUỘC DUY NHẤT NÀY LÀ CỔNG CHỐNG DUYỆT HAI LẦN.
    #    Ở tầng CSDL, không phải ở một `if` trong route: route có thể quên,
    #    ràng buộc không quên. Gỡ chúng ra thì `test_806` phải ĐỎ — nếu không,
    #    phép kiểm đó không ghim gì cả.
    op.create_index("ux_chatltt_approval_step", "chatltt_approval", ["step_id"],
                    unique=True)
    op.create_index("ux_chatltt_approval_idem", "chatltt_approval",
                    ["idempotency_key"], unique=True)
    op.create_index("ix_chatltt_approval_user", "chatltt_approval",
                    ["user_id", "quyet_dinh"])

    # Hai cột nối lên run/step. NULLABLE ⇒ mọi hàng V1 vẫn hợp lệ, không backfill.
    op.add_column("chatltt_execution",
                  sa.Column("run_id", sa.String(40), nullable=True))
    op.add_column("chatltt_execution",
                  sa.Column("step_id", sa.String(40), nullable=True))
    op.create_index("ix_chatltt_exec_run", "chatltt_execution", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_chatltt_exec_run", table_name="chatltt_execution")
    op.drop_column("chatltt_execution", "step_id")
    op.drop_column("chatltt_execution", "run_id")
    op.drop_table("chatltt_approval")
    op.drop_table("chatltt_step")
    op.drop_table("chatltt_run")
