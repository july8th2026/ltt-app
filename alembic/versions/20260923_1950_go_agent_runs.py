"""Buoc 2 cua cat chuyen §17.5 — drop bang `agent_runs`.

⚠️ CHI CHAY SAU khi ban ma khong con doc bang nay (plan 01b Task 9) da deploy
   va chay xanh >= 1 ngay. Hai buoc — ma ngung dung, ROI moi drop — de duong
   lui chi can "deploy lai `app.previous\\`".

## `downgrade` dung lai bang RONG, va do la mot lua chon co gia

Du lieu run v1 khong quay lai duoc. Dieu do da duoc chap nhan o §17.3: cac run
con do bi huy + hoan tien truoc khi bang bi drop (one-off
`tools/_luutru/dong_agent_run_con_do.py`, chay 23/09/2026: `tim_thay=0`, khong
co credit nao dang bi giu). Ban cu chi can bang TON TAI de khoi dong.

## Vi sao `upgrade` khong `drop_index` truoc

Ca PostgreSQL lan SQLite deu xoa chi muc cung bang. Goi `drop_index` truoc chi
them bon lenh co the that bai neu mot moi truong nao do thieu mot chi muc —
tuc them duong hong vao chinh cai lenh dang don dep.

## Doi xung voi `20260802_1200_agent_runs.py`

`downgrade` duoi day chep DUNG khoi `create_table` + bon `create_index` cua
migration da tao bang (revision `b2c3d4e5f6a7`), khong chep lai tu `models.py`:
model da bi go o Task 9, con migration cu la thu THAT SU da chay tren CSDL
production. Doc no la doc lai lich su, khong phai doc mot ban dich.

Revision ID: 8f1c6a4d2b90
Revises: 56a971862a15
Create Date: 2026-09-23
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8f1c6a4d2b90"
down_revision: Union[str, None] = "56a971862a15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("agent_runs")


def downgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("app_slug", sa.String(64), nullable=False, server_default="agent"),
        sa.Column("goal", sa.Text(), nullable=False, server_default=""),
        sa.Column("plan", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("checkpoint", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(24), nullable=False, server_default="planning"),
        sa.Column("budget_max", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(36), nullable=False, server_default=""),
        sa.Column("decision_log", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])
    op.create_index("ix_agent_runs_created_at", "agent_runs", ["created_at"])
    op.create_index("ix_agent_runs_user_created", "agent_runs",
                    ["user_id", "created_at"])
