"""Bảng `gpu_residency`: model nào đang cư trú trên một nhóm GPU (D01 B, dual-model 5.1).

## Add-only, và vô hại với mã cũ

Bảng mới, không khoá ngoại, không ai đọc nó cho tới Task 5.3 (luật 0 của
admission) và 5.5 (trọng tài). Mã đang chạy trước lần deploy này không biết bảng
này tồn tại và vẫn chạy đúng như cũ — nên đây là một bước **đi lên đơn phương**:
migration chạy được trước khi mã trọng tài có mặt.

## Không gieo dòng nào

`upgrade()` **không** INSERT dòng `rtx3090`. Trọng tài tự tạo dòng ở lượt bước
đầu tiên (upsert trong advisory lock, Task 5.5), và đó là chỗ đúng: dòng phải
sinh ra kèm trạng thái đọc được **từ máy B thật** (`/running`, VRAM theo UUID),
không phải kèm một giả định viết trong migration. Một dòng gieo sẵn nói
"3090 đang là của LTT-3.8" trên một máy vừa khởi động lại ComfyUI sẽ là câu trả
lời SAI — và nó sai theo hướng nguy hiểm: admission mở cho LTT-3.8 trong khi
VRAM đã là của model ảnh.

## `downgrade()` xoá cả bảng

Được, vì bảng không giữ dữ liệu của khách và không giữ lịch sử: nó là **trạng
thái hiện tại** của một card. Quay lại mã cũ thì hai trọng tài cũ
(`render_gateway/nhuong_card.py`, `llm_gateway/don_dep.py`) lại là bên quyết,
và chúng không đọc bảng này.

Revision ID: c7a3f1e5b904
Revises: b4d7f2c19e30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c7a3f1e5b904"
down_revision = "b4d7f2c19e30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gpu_residency",
        sa.Column("nhom", sa.String(32), primary_key=True),
        sa.Column("trang_thai", sa.String(16), nullable=False, server_default="llm"),
        sa.Column("tu_luc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cua_so_bat_dau", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lan_nap_loi", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="0"),
        # Trùng với primary key có chủ ý — lý do ở docstring của
        # `platform_core.models.GpuResidency`: drill khôi phục đối chiếu ràng
        # buộc sống còn **theo tên**, và một PRIMARY KEY không có tên `uq_`.
        sa.UniqueConstraint("nhom", name="uq_gpu_residency_nhom"),
    )


def downgrade() -> None:
    op.drop_table("gpu_residency")
