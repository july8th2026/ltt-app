"""them phien ban gia va quan sat chi phi cho khu API (EXT-15)

`api_pricing_versions` KHONG tinh gia. Gia van do `credit_cost()` cua app tinh;
bang nay ghi lai CHE DO GIA nao dang co hieu luc, kem cua so va gioi han, roi
nhan do duoc dong dau len quote va job. Nho vay "khong sua gia hoi to" la tinh
chat cua luoc do, khong phai mot luat ai do phai nho: phat hanh ban moi la THEM
dong, khong sua dong cu.

`api_cost_observations` tach hoan toan khoi so credit. So credit la doanh thu
that; bang nay la chi phi UOC LUONG, va cot `is_estimate` ton tai de khong truy
van nao lo trinh bay no nhu so da doi soat.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d6e7f8a9b0c1"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_pricing_versions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("tool", sa.String(64), nullable=False),
        sa.Column("model", sa.String(64), nullable=False, server_default=""),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False,
                  server_default="draft"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("min_credit", sa.Integer(), nullable=True),
        sa.Column("max_credit", sa.Integer(), nullable=True),
        sa.Column("rounding", sa.Integer(), nullable=True),
        sa.Column("rounding_mode", sa.String(8), nullable=False,
                  server_default="nearest"),
        sa.Column("formula_ref", sa.String(200), nullable=False,
                  server_default=""),
        sa.Column("notes", sa.String(1000), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(255), nullable=False,
                  server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.String(255), nullable=False,
                  server_default=""),
        sa.PrimaryKeyConstraint("id"),
        # Mat rang buoc nay = hai phien ban cung nhan cho mot cong cu, va mot
        # dau gia tren hoa don khong con tro ve duoc mot dong duy nhat.
        sa.UniqueConstraint("tool", "label", name="uq_api_pricing_label"),
    )
    op.create_index("ix_api_pricing_versions_tool", "api_pricing_versions",
                    ["tool"])
    op.create_index("ix_api_pricing_versions_status", "api_pricing_versions",
                    ["status"])
    op.create_index("ix_api_pricing_window", "api_pricing_versions",
                    ["tool", "status", "effective_from"])

    op.create_table(
        "api_cost_observations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("tool", sa.String(64), nullable=False, server_default=""),
        sa.Column("kind", sa.String(16), nullable=False),
        # Dai luong DO DUOC.
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        # Don gia CAU HINH ap len no.
        sa.Column("unit_cost_micros", sa.Integer(), nullable=False),
        sa.Column("cost_micros", sa.BigInteger(), nullable=False),
        sa.Column("is_estimate", sa.Boolean(), nullable=False,
                  server_default=sa.true()),
        sa.Column("source", sa.String(32), nullable=False,
                  server_default="configured_rate"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_cost_observations_job_id", "api_cost_observations",
                    ["job_id"])
    op.create_index("ix_api_cost_observations_created_at",
                    "api_cost_observations", ["created_at"])
    op.create_index("ix_api_cost_window", "api_cost_observations",
                    ["created_at", "tool"])


def downgrade() -> None:
    op.drop_index("ix_api_cost_window", table_name="api_cost_observations")
    op.drop_index("ix_api_cost_observations_created_at",
                  table_name="api_cost_observations")
    op.drop_index("ix_api_cost_observations_job_id",
                  table_name="api_cost_observations")
    op.drop_table("api_cost_observations")
    op.drop_index("ix_api_pricing_window", table_name="api_pricing_versions")
    op.drop_index("ix_api_pricing_versions_status",
                  table_name="api_pricing_versions")
    op.drop_index("ix_api_pricing_versions_tool",
                  table_name="api_pricing_versions")
    op.drop_table("api_pricing_versions")
