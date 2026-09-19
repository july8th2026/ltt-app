"""`llm_waiters`: số đo của lượt — token vào/ra/cache + TTFB phía A (T4 P2).

Revision ID: e4a19c07b5d2
Revises: b7d41e2c9a05

## Thêm gì

Bốn cột (thiết kế `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md`
§2.3): `token_vao`, `token_ra`, `token_cache` `INTEGER NULL`, `ttfb_s`
`FLOAT NULL`. A vốn đếm được chúng (`DemToken` ở cửa stream, `KetQua` ở cửa một
cục) nhưng trước bản này chỉ in ra một dòng log văn bản — sổ lượt 30 ngày trả
lời được "chờ bao lâu" mà không trả lời được "lượt ấy to cỡ nào".

## Nullable, KHÔNG server_default — có chủ ý

`NULL` là "không đo được" (luồng vỡ trước `usage`, đường ra bận/lỗi trước
lượt); `0` là một khẳng định. Một `server_default 0` sẽ biến mọi dòng cũ và mọi
dòng mã cũ ghi thành "đo được: 0 token" — đúng lời nói dối cột này tránh.

## Add-only, an toàn hai chiều

Nullable ⇒ dòng có sẵn nhận NULL, mã cũ không biết cột vẫn INSERT được ⇒
migration chạy được TRƯỚC khi mã lên. `downgrade()` bỏ cột (sổ vận hành 30
ngày, `governance.py` OPERATIONAL). SQLite cần `batch_alter_table` để bỏ cột.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e4a19c07b5d2"
down_revision = "b7d41e2c9a05"
branch_labels = None
depends_on = None

_BANG = "llm_waiters"
_COT = (
    ("token_vao", sa.Integer()),
    ("token_ra", sa.Integer()),
    ("token_cache", sa.Integer()),
    ("ttfb_s", sa.Float()),
)


def upgrade() -> None:
    for ten, kieu in _COT:
        op.add_column(_BANG, sa.Column(ten, kieu, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table(_BANG) as batch:
        for ten, _kieu in reversed(_COT):
            batch.drop_column(ten)
