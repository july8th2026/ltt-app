"""vps_instance: bon cot do bang thong (H39/G7)

Trang ban da hua "bang thong co han muc theo goi, vuot thi giam toc" tu truoc,
nhung khong co ma nao do va khong co ma nao ham. Bon cot nay la phan luu tru cua
phep do; phan do nam tren router (`nft` set co counter tung phan tu).

`moc_len`/`moc_xuong` giu lan doc bo dem gan nhat. Bo dem cua `nft` VE 0 khi
router khoi dong lai, nen lay hieu ma khong xu ly viec do se cho ra so AM -- va
mot so am cong vao tong la hoan lai bang thong cho khach.

Revision ID: 8c1f4a67b209
Revises: 5b9e2c47a103
"""
from alembic import op
import sqlalchemy as sa

revision = "8c1f4a67b209"
down_revision = "5b9e2c47a103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vps_instance", sa.Column(
        "bang_thong_byte", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("vps_instance", sa.Column(
        "bang_thong_moc_len", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("vps_instance", sa.Column(
        "bang_thong_moc_xuong", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("vps_instance", sa.Column(
        "bi_giam_toc", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    for c in ("bi_giam_toc", "bang_thong_moc_xuong", "bang_thong_moc_len",
              "bang_thong_byte"):
        op.drop_column("vps_instance", c)
