"""vps_console_ve.pve_ve: varchar(255) -> TEXT

Ve `vncproxy` cua Proxmox la mot chung chi CO CHU KY va dai hon 255 ky tu. Voi
tran do dai, Postgres tu choi ca cau INSERT va **console tra 500 cho moi may** --
tinh nang khong chay duoc lan nao.

Vi sao bo test khong bat: test dung SQLite, ma SQLite **khong cuong che do dai
VARCHAR**. Cung mot cau lenh chay sach o test va no o production. Chi mo trinh
duyet moi thay (quy tac 5 cua CLAUDE.md) -- va da thay dung nhu vay 24/08.

## Va vi sao ban dau tien cua chinh migration nay cung hong -- theo huong nguoc lai

Ban dau no goi thang `op.alter_column(... type_=sa.Text())`. Alembic dich cai do
thanh `ALTER TABLE ... ALTER COLUMN ... TYPE TEXT`, mot cau **Postgres hieu va
SQLite khong co**. Nen:

  - tren production (Postgres) migration chay sach;
  - tren SQLite no chet: `near "ALTER": syntax error`.

Tuc cung mot cot da lam VO bo test hai lan, mot lan vi SQLite qua DE (khong cuong
che do dai), mot lan vi SQLite qua CHAT (khong co ALTER COLUMN TYPE). Bai hoc
khong phai "SQLite dom" ma la: **moi cau DDL doi kieu cot phai di qua
`batch_alter_table`**, thu Alembic sinh ra dung de che khac biet nay -- no dung
ALTER that tren Postgres, va dung ky thuat tao-bang-moi-roi-doi-ten tren SQLite.

Revision ID: 5b9e2c47a103
Revises: 7a41f6d29e83
"""
from alembic import op
import sqlalchemy as sa

revision = "5b9e2c47a103"
down_revision = "7a41f6d29e83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("vps_console_ve") as batch:
        batch.alter_column("pve_ve",
                           existing_type=sa.String(length=255),
                           type_=sa.Text(),
                           existing_nullable=False,
                           existing_server_default="")


def downgrade() -> None:
    # Thu hep lai se CAT CUT ve dang luu. Ve song nhieu nhat 60 giay nen viec do
    # vo hai trong thuc te, nhung phai noi ra thay vi de nguoi doc doan.
    with op.batch_alter_table("vps_console_ve") as batch:
        batch.alter_column("pve_ve",
                           existing_type=sa.Text(),
                           type_=sa.String(length=255),
                           existing_nullable=False,
                           existing_server_default="")
