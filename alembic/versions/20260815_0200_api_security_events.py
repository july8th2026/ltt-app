"""them bang su kien bao mat cho khu API (EXT-16)

Vi sao mot bang RIENG chu khong noi `public_api_requests`: cot `user_id` cua
bang do la NOT NULL va la truc phan tach tenant cua trang nhat ky khach. Su kien
o day thuong KHONG thuoc ve ai — goi khong co credential, khoa khong ton tai,
khoa da thu hoi. Mot dong `user_id=""` trong bang kia se hoac lot vao trang cua
ai do, hoac vo hinh; ca hai deu sai.

Truoc EXT-16 nhung su kien nay khong co dong nao trong CSDL: `guard.py` bo qua
nhat ky request khi chua co principal, nen moi that bai xac thuc chi vao file
log cua tien trinh. Cau hoi "co ai dang do khoa khong" khong tra loi duoc bang
du lieu.

KHONG luu: nua bi mat cua token, header Authorization, body. `key_id` la nua
CONG KHAI, dung thu ma mot cuoc ho tro van nhac toi.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e7f8a9b0c1d2"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_security_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("key_id", sa.String(48), nullable=False, server_default=""),
        # Co y KHONG phai khoa ngoai: phan lon su kien khong thuoc tai khoan
        # nao, va mot rang buoc doi hoi chu se la ly do de KHONG ghi dung nhung
        # su kien quan trong nhat.
        sa.Column("user_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("route", sa.String(200), nullable=False, server_default=""),
        sa.Column("request_id", sa.String(64), nullable=False,
                  server_default=""),
        sa.Column("detail", sa.String(200), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_security_events_kind", "api_security_events",
                    ["kind"])
    op.create_index("ix_api_security_events_request_id", "api_security_events",
                    ["request_id"])
    op.create_index("ix_api_security_events_created_at", "api_security_events",
                    ["created_at"])
    op.create_index("ix_api_security_window", "api_security_events",
                    ["created_at", "kind"])
    op.create_index("ix_api_security_source", "api_security_events",
                    ["ip", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_api_security_source", table_name="api_security_events")
    op.drop_index("ix_api_security_window", table_name="api_security_events")
    op.drop_index("ix_api_security_events_created_at",
                  table_name="api_security_events")
    op.drop_index("ix_api_security_events_request_id",
                  table_name="api_security_events")
    op.drop_index("ix_api_security_events_kind",
                  table_name="api_security_events")
    op.drop_table("api_security_events")
