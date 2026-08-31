"""voice_*: owner_id BigInteger -> String(36)

⛔ SỬA MỘT LỖI SAI KIỂU ĐÃ LÊN PRODUCTION.

`platform_core.models.User.id` là **UUID chuỗi** — cố ý, để id không đoán được
và không lộ quy mô. App `ltt_voice` khai `owner_id` là `BigInteger`, và mọi chỗ
đọc id đều ép `int(...)` rồi **nuốt lỗi** thành `0`.

Hệ quả đo được trên máy chủ thật 31/08/2026:

  · Trang hiện đúng `56 credit` ở header (chỗ đó đọc phiên trực tiếp) trong khi
    bấm Tạo trả `Khong du credit: can 2, con 0` — vì handler tra sổ của người
    dùng `"0"`. Nhìn như lỗi sổ tiền, thật ra là lỗi danh tính.
  · Và nguy hơn tiền: **mọi `owner_id` đều là 0**, nên `Giọng của tôi` sẽ hiện
    giọng của mọi khách cho mọi khách. Lỗi này còn tiềm ẩn chỉ vì chưa ai kịp
    tạo giọng nào.

⭐ Vì sao đổi kiểu được mà không cần chuyển dữ liệu: đo trước khi đổi, cả bốn
   bảng `voice_*` đều **0 dòng**. App chưa từng phục vụ ai. Nếu về sau đọc lại
   tệp này khi bảng đã có dữ liệu thì đây KHÔNG còn là khuôn để chép.

Revision ID: b2c8e41d5a90
Revises: a1f7c3d90b12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b2c8e41d5a90"
down_revision = "a1f7c3d90b12"
branch_labels = None
depends_on = None

#: (bảng, cột). `voice_ref` và `voice_repr` không mang `owner_id` — chúng treo
#: vào `profile_id`, nên chủ sở hữu suy ra từ profile, không nhân bản.
COT = [("voice_profile", "owner_id"), ("voice_consent", "owner_id")]


#: ⚠️ `batch_alter_table`, KHÔNG phải `op.alter_column` trần.
#:
#:    Production là PostgreSQL, nhưng vòng kiểm `test_63::test_vong_di_tru_tien_
#:    lui_tien` chạy toàn bộ chuỗi migration trên **SQLite**, và SQLite không có
#:    `ALTER TABLE ... ALTER COLUMN ... TYPE` — nó trả `near "ALTER": syntax
#:    error`. `batch_alter_table` dựng lại bảng trên SQLite và vẫn phát ra
#:    `ALTER COLUMN` thật trên PostgreSQL. Cùng khuôn với migration
#:    `5b9e2c47a103` (`vps_console_ve.pve_ve`).


def upgrade() -> None:
    for bang, cot in COT:
        with op.batch_alter_table(bang) as batch:
            batch.alter_column(
                cot,
                existing_type=sa.BigInteger(),
                type_=sa.String(length=36),
                existing_nullable=False,
                # PostgreSQL không tự ép bigint -> varchar; nói rõ phép ép.
                postgresql_using=f"{cot}::varchar(36)")


def downgrade() -> None:
    for bang, cot in COT:
        with op.batch_alter_table(bang) as batch:
            batch.alter_column(
                cot,
                existing_type=sa.String(length=36),
                type_=sa.BigInteger(),
                existing_nullable=False,
                postgresql_using=f"{cot}::bigint")
