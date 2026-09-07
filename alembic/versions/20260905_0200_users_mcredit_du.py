"""users_mcredit_du — phần lẻ chưa thu, để thôi làm tròn LÊN mỗi lượt gọi

CHỈ THÊM một cột `NOT NULL DEFAULT 0`. Hàng cũ hợp lệ ngay, không backfill.

## Vì sao cột này tồn tại

Credit là số nguyên; một lượt gọi LLM điển hình tốn **0,3 credit**. Làm tròn LÊN
mỗi lượt gọi (phương án C1, chốt 22/08) biến:

  - một lượt agentic 4 vòng: **0,92 credit thật → thu 4** (4,0×)
  - một hội thoại 20 lượt ngắn: **3,13 credit thật → thu 20** (6,4×)

và làm ta **đắt hơn giá bán lẻ** ở mọi lượt dưới ~1 credit (chat rất ngắn: ta thu
1, `qwen/qwen3.8-27b` trên OpenRouter là 0,21 — tức 4,84×).

Đo và lý lẽ đầy đủ: `docs/CHATLTT_V3/04_ADR_R2B_TINH_TIEN_LUOT.md`.

⛔ Cột này **không phải sổ tiền**. `credit_entries` vẫn là sự thật duy nhất.
   Đây là bộ đếm dẫn xuất; xoá nó thì khách được lợi tối đa 0,999 credit.

⭐ Hạ migration này an toàn: mất phần lẻ đang giữ, không mất một bút toán nào.

Revision ID: 9f3a71b4c2e8
Revises: 4b8e21c6d907
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "9f3a71b4c2e8"
down_revision = "4b8e21c6d907"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mcredit_du", sa.Integer(), nullable=False,
                                     server_default="0"))


def downgrade() -> None:
    op.drop_column("users", "mcredit_du")
