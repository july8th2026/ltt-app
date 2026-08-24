"""vps_instance.sao_luu_luc — lan chup anh gan nhat (H39/G9)

Trang ban da hua "sao luu hang tuan, giu 1 ban" tu truoc khi co ma nao lam viec
do. Cot nay la lich: vong bao tri chup cho may nao co `sao_luu_luc` cu hon 7 ngay.

Revision ID: a4d70e93f158
Revises: 8c1f4a67b209
"""
from alembic import op
import sqlalchemy as sa

revision = "a4d70e93f158"
down_revision = "8c1f4a67b209"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vps_instance", sa.Column(
        "sao_luu_luc", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("vps_instance", "sao_luu_luc")
