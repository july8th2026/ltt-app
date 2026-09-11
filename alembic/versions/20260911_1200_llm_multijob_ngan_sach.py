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
Revises: f2c48b71e903
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "7c1e4b9a2d58"
down_revision = "f2c48b71e903"
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
