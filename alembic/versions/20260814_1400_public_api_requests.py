"""them bang nhat ky request cho Public API (EXT-09)

Vi sao can bang nay du da co dong log `ltt.public_api.access`: dong log chi
operator doc duoc. Khach hang khong grep duoc dia cua chung ta, va nhung loi goi
ho can hieu nhat (401, 403, 429) khong bao gio tao job — tuc khong co gi khac
luu lai.

KHONG co cot body/detail: bang go roi ma tich luy payload se thanh mot ban sao
noi dung khach hang voi cai ten de nghe hon. Chi luu bo xuong cua loi goi.

Retention 30 ngay nam trong `platform_core/public_api/request_log.py` va duoc
worker goi dinh ky — dat ngay tu dau, khong de lap lai bai hoc
`webhook_deliveries` (phinh vo han vi tao du lieu ma quen chinh sach don).

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_api_requests",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("key_id", sa.String(48), nullable=False, server_default=""),
        sa.Column("project_id", sa.String(36), nullable=False,
                  server_default=""),
        sa.Column("method", sa.String(8), nullable=False, server_default=""),
        sa.Column("route", sa.String(200), nullable=False, server_default=""),
        sa.Column("status", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("code", sa.String(48), nullable=False, server_default=""),
        sa.Column("latency_ms", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("tool", sa.String(64), nullable=False, server_default=""),
        sa.Column("job_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("credit_delta", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_public_api_requests_request_id", "public_api_requests",
                    ["request_id"])
    op.create_index("ix_public_api_requests_user_id", "public_api_requests",
                    ["user_id"])
    op.create_index("ix_public_api_requests_job_id", "public_api_requests",
                    ["job_id"])
    # Hai cau hoi trang nay hoi: "loi goi gan day cua toi" va "loi goi hong".
    op.create_index("ix_public_api_requests_owner_time", "public_api_requests",
                    ["user_id", "created_at"])
    op.create_index("ix_public_api_requests_owner_status", "public_api_requests",
                    ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_public_api_requests_owner_status",
                  table_name="public_api_requests")
    op.drop_index("ix_public_api_requests_owner_time",
                  table_name="public_api_requests")
    op.drop_index("ix_public_api_requests_job_id",
                  table_name="public_api_requests")
    op.drop_index("ix_public_api_requests_user_id",
                  table_name="public_api_requests")
    op.drop_index("ix_public_api_requests_request_id",
                  table_name="public_api_requests")
    op.drop_table("public_api_requests")
