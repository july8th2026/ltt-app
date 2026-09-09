"""voice_profile.gioi — giới tính của giọng, để lùi giọng KHÔNG đổi người nói

🔴 MẶC ĐỊNH `""` (KHÔNG RÕ), VÀ MIGRATION NÀY KHÔNG ĐOÁN GIỚI CHO DÒNG NÀO.

   Cám dỗ rõ ràng là suy giới từ tên hiển thị ("Lily" -> nữ) hoặc từ F0 của
   clip nguồn. Cả hai đều **sai theo hướng nguy hiểm**: chúng sinh ra một cột
   trông như dữ liệu, được `lui_giong.py` tin, và khi sai thì hậu quả đúng bằng
   thứ cột này sinh ra để ngăn — đọc bài của khách bằng giọng khác giới.

   `toc_do.py` đã ghi lại một ca thật của phép đo F0: bộ dò nhầm quãng tám trên
   một clip giọng nữ và báo 105,6 Hz. Một lần nhầm như thế, nhân với cả bảng,
   là một cột không ai dám dùng nữa.

⇒ `""` là một câu trả lời ĐẦY ĐỦ: *"chưa ai nói"*. `lui_giong` từ chối lùi khi
  gặp nó, và bộ lọc ở giao diện luôn hiện giọng ấy. Chủ giọng điền sau, từng
  cái một, ở màn Giọng.

Revision ID: e7b2c94a1d38
Revises: c9d4e1a77b02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e7b2c94a1d38"
down_revision = "c9d4e1a77b02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "voice_profile",
        sa.Column("gioi", sa.String(length=8), nullable=False,
                  server_default=""))


def downgrade() -> None:
    op.drop_column("voice_profile", "gioi")
