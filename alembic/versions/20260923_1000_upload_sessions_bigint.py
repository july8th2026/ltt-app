"""upload_sessions: expected_size/actual_size Integer -> BigInteger

⛔ SỬA F-08: `expected_size` là `int4` (giới hạn 2 147 483 647 byte, tức
2 GiB−1) trong khi sản phẩm chấp nhận tệp lớn hơn qua `upload_sessions`
(video gốc ASV, v.v.). Một phiên tải lên khai `expected_size` > 2 GiB bị
kẹp/ tràn số ở tầng CSDL. `actual_size` đi cùng cột (đếm byte đã nhận) nên
đổi luôn để không lặp lại lỗi khi tệp thật vượt ngưỡng.

Revision ID: d7bc2f8fbf0f
Revises: e4a19c07b5d2
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d7bc2f8fbf0f"
down_revision = "e4a19c07b5d2"
branch_labels = None
depends_on = None

#: (bảng, cột). Cùng khuôn `batch_alter_table` với `b2c8e41d5a90`
#: (`voice_owner_uuid`) — production là PostgreSQL nhưng vòng kiểm di trú
#: chạy toàn chuỗi trên SQLite, và SQLite không có `ALTER COLUMN ... TYPE`.
COT = [("upload_sessions", "expected_size"), ("upload_sessions", "actual_size")]


def upgrade() -> None:
    for bang, cot in COT:
        with op.batch_alter_table(bang) as batch:
            batch.alter_column(
                cot,
                existing_type=sa.Integer(),
                type_=sa.BigInteger(),
                existing_nullable=False,
                postgresql_using=f"{cot}::bigint")


def downgrade() -> None:
    for bang, cot in COT:
        with op.batch_alter_table(bang) as batch:
            batch.alter_column(
                cot,
                existing_type=sa.BigInteger(),
                type_=sa.Integer(),
                existing_nullable=False,
                postgresql_using=f"{cot}::integer")
