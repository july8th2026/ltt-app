"""lease co ten + khoa chong trung canh bao (T1/T2 runtime hardening)

Vi sao can: nen tang chay NHIEU tien trinh worker (so tien trinh mac dinh bang
so GPU), nhung moi viec nen — don du lieu, gui webhook, quet canh bao — deu duoc
viet voi gia dinh ngam "chi mot tien trinh chay vong nay". Khong ai viet gia dinh
do ra nen khong ai kiem no, va no sai.

`singleton_leases` bien gia dinh do thanh mot co che co ten: giu bang INSERT,
UNIQUE quyet dinh nguoi thang, `heartbeat_at` khien chu chet thi lease tu het
han. Cung khuon voi `gpu_leases` da chay trong production.

`api_notifications.event_key` + UNIQUE: cooldown cua canh bao truoc day chi duoc
thi hanh bang doc-roi-ghi trong Python, nen hai tien trinh quet cung luc deu thay
"chua co gi gan day" va deu ghi — khach nhan email trung. Gio CSDL quyet dinh,
giong het cach `job_events.event_key` da lam.

Dong cu duoc lap khoa tu id: khong the tinh lai o thoi gian goc, va de trong thi
UNIQUE se coi moi dong cu la trung nhau.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "singleton_leases",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("holder", sa.String(length=160), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_singleton_lease_name"),
    )
    op.create_index("ix_singleton_leases_heartbeat_at", "singleton_leases",
                    ["heartbeat_at"])

    op.add_column("api_notifications",
                  sa.Column("event_key", sa.String(length=200),
                            nullable=False, server_default=""))
    # Dong cu: lap khoa tu id de moi dong van duy nhat. Khong tinh lai duoc khoa
    # that (can thoi diem goc theo o cooldown), va de trong thi UNIQUE se coi
    # tat ca dong cu la trung nhau va migration se hong.
    op.execute("UPDATE api_notifications SET event_key = 'legacy:' || id "
               "WHERE event_key = ''")
    op.create_unique_constraint("uq_api_notifications_event_key",
                                "api_notifications", ["user_id", "event_key"])


def downgrade() -> None:
    op.drop_constraint("uq_api_notifications_event_key", "api_notifications",
                       type_="unique")
    op.drop_column("api_notifications", "event_key")
    op.drop_index("ix_singleton_leases_heartbeat_at",
                  table_name="singleton_leases")
    op.drop_table("singleton_leases")
