"""waitpoint: han cho + che do het han; workflow_trigger: version/cursor/loi

Revision ID: c4a17f9b6d20
Revises: 3b1a2e203c41
Create Date: 2026-09-24

⚠️ Ban dau revision nay TU hop hai head `b06f7b03870a` + `b7d2e9c41a03` (ca
   hai cung ton tai tren `main` chieu 24/09, lam `alembic upgrade head` tu
   choi chay ⇒ MOI deploy bi chan). Trong luc do mot phien khac da tao nut hop
   rieng `3b1a2e203c41` va gop `main` truoc. Hai nut hop cho CUNG mot cap
   nhanh lai tao ra HAI head moi — dung thu ca hai dinh sua.

⇒ Revision nay nay NOI THANG vao head duy nhat sau khi hop (`3b1a2e203c41`),
  ⛔ khong de them mot nut hop thu hai. Phep kiem re nhat cho loi dat nhat:
  `python -m alembic heads` phai in DUNG MOT dong.

⛔ Khong `alembic stamp`, khong `create_all`: doi voi PostgreSQL that day la
   mot lenh `ALTER TABLE ... ADD COLUMN` co `server_default` — tren
   PostgreSQL >= 11 la thao tac CHI SUA CATALOG, khong viet lai bang. Ca hai
   bang deu dang chay that.

Chi so `ix_waitpoint_het_han` la `(het_han_luc, id)` chu khong phai
`(het_han_luc)`: bo quet het han di bang KEYSET CURSOR
(`cho_doi.quet_het_han`), va mot dieu kien `(a, id) > (:a, :id)` chi dung duoc
chi so khi chi so mang dung hai cot do theo dung thu tu.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4a17f9b6d20"
down_revision: Union[str, Sequence[str], None] = "3b1a2e203c41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("waitpoint", sa.Column(
        "het_han_luc", sa.DateTime(timezone=True), nullable=True))
    op.add_column("waitpoint", sa.Column(
        "che_do_het_han", sa.String(length=16), nullable=False,
        server_default="fail"))
    op.create_index(
        "ix_waitpoint_het_han", "waitpoint", ["het_han_luc", "id"],
        postgresql_where=sa.text(
            "status = 'PENDING' AND het_han_luc IS NOT NULL"),
        sqlite_where=sa.text("status = 'PENDING' AND het_han_luc IS NOT NULL"))

    op.add_column("workflow_trigger", sa.Column(
        "version_mode", sa.String(length=16), nullable=False,
        server_default="published"))
    op.add_column("workflow_trigger", sa.Column(
        "pinned_version_id", sa.String(length=36), nullable=False,
        server_default=""))
    op.add_column("workflow_trigger", sa.Column(
        "con_tro", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("workflow_trigger", sa.Column(
        "last_fired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("workflow_trigger", sa.Column(
        "loi_lien_tiep", sa.Integer(), nullable=False, server_default="0"))

    # `ix_foreach_muc_chua_xong`: `(vong_id)` -> `(vong_id, chi_so)`.
    #
    # Lan p3b do tren PostgreSQL that: bo lai vong lap doc N hang MOI TICK =>
    # tong cong `N^2/P` (127 000 hang, 31,67 giay cho N=1000, P=8). Ban sua di
    # bang KEYSET (`foreach.muc_chua_xong`), va mot dieu kien
    # `chi_so > :sau ORDER BY chi_so` chi dung duoc chi so khi chi so MANG cot
    # do. DROP roi CREATE vi doi CO cot, khong doi ten.
    op.drop_index("ix_foreach_muc_chua_xong", table_name="foreach_muc")
    op.create_index(
        "ix_foreach_muc_chua_xong", "foreach_muc", ["vong_id", "chi_so"],
        postgresql_where=sa.text("xong = false"),
        sqlite_where=sa.text("xong = 0"))


def downgrade() -> None:
    op.drop_index("ix_foreach_muc_chua_xong", table_name="foreach_muc")
    op.create_index(
        "ix_foreach_muc_chua_xong", "foreach_muc", ["vong_id"],
        postgresql_where=sa.text("xong = false"),
        sqlite_where=sa.text("xong = 0"))
    op.drop_column("workflow_trigger", "loi_lien_tiep")
    op.drop_column("workflow_trigger", "last_fired_at")
    op.drop_column("workflow_trigger", "con_tro")
    op.drop_column("workflow_trigger", "pinned_version_id")
    op.drop_column("workflow_trigger", "version_mode")
    op.drop_index("ix_waitpoint_het_han", table_name="waitpoint")
    op.drop_column("waitpoint", "che_do_het_han")
    op.drop_column("waitpoint", "het_han_luc")
