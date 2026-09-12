"""`llm_waiters.model`: id model nội bộ của mỗi lượt chờ (dual-model 6.3).

## Cột này thêm gì mà `resource` chưa nói

Hôm nay ánh xạ là 1–1 (`ltt_38_3090` ↔ `qwen38-api`), nên "suy model từ
resource" **chạy được**. Nó vẫn sai chỗ: người đọc sổ là
`platform_core/job_metrics.py`, và `platform_core` không được biết tên app
(`test_147`), nên phép suy ấy buộc nền tảng nhập một bảng ánh xạ từ `apps/`.
App khai một lần lúc vào hàng thì không ai phải dịch.

## ⛔ CHỈ MỘT CỘT — `cho_residency_s` ĐÃ CÓ Ở `d91f6c37ab24`

Plan Task 6.3 liệt kê hai cột (`model`, `cho_residency_s`). Task 5.3 đã thêm
`cho_residency_s` vì nó là bên **ghi** và bên ghi phải deploy trước bên đọc.
Thêm lại ở đây là `DuplicateColumn` trên PostgreSQL, và trên SQLite là một lần
`upgrade` vỡ giữa hai câu lệnh.

## Add-only, an toàn hai chiều

`NOT NULL` + `server_default ''`: dòng đang chờ lúc migration chạy vẫn ghi
được, và bản mã cũ (không biết cột này) vẫn INSERT được nhờ default. Nên
migration chạy được **trước** khi mã 6.3 lên, và mã 6.3 chạy được trên CSDL đã
migrate — yêu cầu của `docs/16_CAP_NHAT_VA_DEPLOY.md` với một máy A đang sống.

`downgrade()` bỏ cột: bảng là sổ vận hành 30 ngày (`governance.py`:
OPERATIONAL), không phải dữ liệu khách.

Revision ID: a3f7c214e8b9
Revises: d91f6c37ab24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a3f7c214e8b9"
down_revision = "d91f6c37ab24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("llm_waiters", sa.Column(
        "model", sa.String(length=64), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("llm_waiters", "model")
