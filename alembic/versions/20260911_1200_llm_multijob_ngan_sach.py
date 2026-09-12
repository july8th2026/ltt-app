"""LTT_LLM đa job: sổ ngân sách KV trên `execution_leases` + phòng chờ/sổ lượt `llm_waiters`.

## Add-only

- Bốn cột mới trên `execution_leases` đều có `server_default` rỗng/0/false: bảng
  này chỉ giữ lease SỐNG (TTL 20 phút), và lease cũ không có lớp/ngân sách thì luật
  nhận coi như "đếm slot" — đúng hành vi trước migration.
- `llm_waiters` là bảng mới, không khoá ngoại: nó là phòng chờ + sổ lượt vận hành
  (OPERATIONAL 30 ngày, `platform_core/public_api/governance.py`), không phải dữ liệu
  của khách, và không được kéo theo xoá của bảng nào khác.

Spec: `docs/superpowers/specs/2026-09-11-ltt-llm-multijob-design.md` §4.

Revision ID: 7c1e4b9a2d58
Revises: e26c9a41d8b5
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "7c1e4b9a2d58"
down_revision = "d9a1f6c2b3e5"   # forward-port 12/09: xep tren head CMC
#                ^^^^^^^^^^^^
# 🔴 TRUOC 12/09 dong nay tro `e26c9a41d8b5` — to tien CHUNG cua hai dong,
#    nen chuoi dual-model la mot NHANH ANH EM cua chuoi Voice RC1 chu khong
#    nam tren no. Hau qua do duoc: CSDL production dung o `d9a1f6c2b3e5`
#    (head do Voice RC1 tao), con `alembic/versions` cua nhanh dual KHONG co
#    revision ay ⇒ `alembic upgrade head` KHONG ve duoc duong di:
#
#        CommandError: Can't locate revision identified by 'd9a1f6c2b3e5'
#
#    Deploy may A 12/09 chet o dung cho nay va production tat ~4 phut.
#
# ⭐ Doi day la FORWARD-PORT, khong phai viet lai ancestry da apply: nam
#    migration dual CHUA TUNG duoc apply o production (prod dung o
#    `d9a1f6c2b3e5`, truoc ca cai dau tien cua ta). Thu KHONG duoc dong la
#    ancestry cua Voice — va no khong bi dong.
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("execution_leases", sa.Column(
        "lop", sa.String(16), nullable=False, server_default=""))
    op.add_column("execution_leases", sa.Column(
        "token_dat_truoc", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("execution_leases", sa.Column(
        "token_prefill_moi", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("execution_leases", sa.Column(
        "la_whale", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "llm_waiters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource", sa.String(96), nullable=False),
        sa.Column("cua", sa.String(16), nullable=False, server_default=""),
        sa.Column("lop", sa.String(16), nullable=False, server_default=""),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("token_dat_truoc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_prefill_moi", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("la_whale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("admitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trang_thai", sa.String(16), nullable=False, server_default="cho"),
        sa.Column("ly_do_cho", sa.String(32), nullable=False, server_default=""),
        sa.Column("so_nhip", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ket_qua", sa.String(32), nullable=False, server_default=""),
        sa.Column("lease_id", sa.String(36), nullable=False, server_default=""),
        sa.UniqueConstraint("request_id", name="uq_llm_waiters_request"),
    )
    op.create_index("ix_llm_waiters_resource_state", "llm_waiters",
                    ["resource", "trang_thai", "created_at"])
    op.create_index("ix_llm_waiters_user_id", "llm_waiters", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_waiters_user_id", table_name="llm_waiters")
    op.drop_index("ix_llm_waiters_resource_state", table_name="llm_waiters")
    op.drop_table("llm_waiters")
    op.drop_column("execution_leases", "la_whale")
    op.drop_column("execution_leases", "token_prefill_moi")
    op.drop_column("execution_leases", "token_dat_truoc")
    op.drop_column("execution_leases", "lop")
