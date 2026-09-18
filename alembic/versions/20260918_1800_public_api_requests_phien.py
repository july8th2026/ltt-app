"""`public_api_requests`: mã lượt + phiên client (T4 P1, R-06/R-07).

Revision ID: b7d41e2c9a05
Revises: 7c2e5a91d4b3

## Thêm gì

Năm cột chuỗi + hai chỉ mục (thiết kế
`docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` §2.2):

* `ma_luot` `VARCHAR(36)` — mã lượt A sinh; = `credit_entries.job_id` =
  `llm_waiters.request_id` = `"ma"` ở sổ lượt máy B. Trước bản này dòng sổ
  request KHÔNG nối được sang ba sổ kia.
* `phien_khach`, `nhanh_khach`, `luot_khach` `VARCHAR(64)`, `ung_dung_khach`
  `VARCHAR(48)` — id phiên / sub-agent-thread / turn / tên-phiên-bản client đọc
  từ header (`server/api/phien_khach.py`). ⛔ Không cột nào cho id máy/cài đặt.
* `ix_public_api_requests_phien (user_id, phien_khach, created_at)`,
  `ix_public_api_requests_ma_luot (ma_luot)`.

## Add-only, an toàn hai chiều

`NOT NULL` + `server_default ''` (khuôn `20260912_1400_llm_waiters_model.py`):
dòng có sẵn nhận chuỗi rỗng, mã cũ không biết cột vẫn INSERT được ⇒ migration
chạy được TRƯỚC khi mã lên. Lưu giữ không đổi: 30 ngày qua
`request_log.purge_expired` (`governance.py`, OPERATIONAL).

`downgrade()` bỏ chỉ mục rồi cột (sổ vận hành 30 ngày, không phải dữ liệu khách).
SQLite cần `batch_alter_table` để bỏ cột.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b7d41e2c9a05"
down_revision = "7c2e5a91d4b3"
branch_labels = None
depends_on = None

_BANG = "public_api_requests"
_COT = (
    ("ma_luot", 36),
    ("phien_khach", 64),
    ("nhanh_khach", 64),
    ("luot_khach", 64),
    ("ung_dung_khach", 48),
)


def upgrade() -> None:
    for ten, dai in _COT:
        op.add_column(_BANG, sa.Column(
            ten, sa.String(length=dai), nullable=False, server_default=""))
    op.create_index("ix_public_api_requests_phien", _BANG,
                    ["user_id", "phien_khach", "created_at"])
    op.create_index("ix_public_api_requests_ma_luot", _BANG, ["ma_luot"])


def downgrade() -> None:
    op.drop_index("ix_public_api_requests_ma_luot", table_name=_BANG)
    op.drop_index("ix_public_api_requests_phien", table_name=_BANG)
    with op.batch_alter_table(_BANG) as batch:
        for ten, _dai in reversed(_COT):
            batch.drop_column(ten)
