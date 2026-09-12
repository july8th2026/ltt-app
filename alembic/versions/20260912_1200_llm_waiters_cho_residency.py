"""`llm_waiters.cho_residency_s`: trong thời gian chờ, bao nhiêu giây là vì cư trú GPU.

## Vì sao cột này ở đây (5.3) chứ không ở Task 6.3 như plan viết

Plan xếp migration của cột vào Task 6.3 (quan sát) trong khi Task 5.3 đã là bên
**ghi** vào nó (`platform_core/llm/phong_cho.py` cộng từng khoảng giữa hai nhịp).
Người ghi đi trước người đọc thì cột phải có mặt ở lần deploy của người ghi —
nếu không, 5.3 lên production và mỗi khoảng chờ vì cửa sổ ảnh biến mất không dấu
vết, đúng giai đoạn duy nhất mà số ấy cần để chốt tham số cửa sổ (D01: *"tham số
khởi đầu, chốt lại bằng lưu lượng đo"*). Task 6.3 giữ phần của nó:
`llm_waiters.model` + hai khối `/ops/jobs-metrics` **đọc** cột này.

## Add-only, nullable-an-toàn, và vô hại với mã cũ

Một cột, `NOT NULL` kèm `server_default 0`: dòng đang chờ lúc migration chạy vẫn
đọc/ghi được, và mã cũ (bản đang chạy ở máy A) không biết cột này tồn tại —
nó không SELECT theo tên cột nào ở bảng này, và mọi INSERT của nó đủ giá trị nhờ
`server_default`. Nên migration chạy được **trước** khi mã 5.3 lên, và mã 5.3
chạy được trên CSDL đã migrate — hai chiều đều an toàn, đúng yêu cầu của
`docs/16_CAP_NHAT_VA_DEPLOY.md` với một máy A đang sống.

`downgrade()` bỏ cột: bảng là sổ vận hành 30 ngày (`governance.py`: OPERATIONAL),
không phải dữ liệu khách, nên mất một cột phân tích khi lùi là giá đúng phải trả.

Revision ID: d91f6c37ab24
Revises: c7a3f1e5b904
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d91f6c37ab24"
down_revision = "c7a3f1e5b904"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("llm_waiters", sa.Column(
        "cho_residency_s", sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("llm_waiters", "cho_residency_s")
