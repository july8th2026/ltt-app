"""Chay lo dung chung bang voi Du an: them `loai`, `nhan`, `loi`.

Revision ID: d4e0a63b8f29
Revises: c3d9f52a7e18
Create Date: 2026-08-31

VI SAO KHONG THEM HAI BANG MOI CHO CHAY LO:

    Dat hai luoc do canh nhau thi chung TRUNG gan nhu hoan toan -- chu so huu,
    ten, giong mac dinh, mot danh sach don vi van ban CO THU TU, moi don vi mang
    giong rieng, trang thai, job_id, khoa tep, so giay, so credit.

    Hai bang nua nghia la hai migration, hai phep tra quyen, hai `gan_ket_qua`,
    hai cua poll trang thai. Ngay mot trong sau thu do duoc sua o mot ben ma quen
    ben kia la ngay chung lech nhau -- va cho lech dau tien gan nhu chac chan la
    phep tra quyen.

    ⇒ Mot cot `loai` (`du_an` | `lo`). Khac biet that nam o HANH VI, khong o du
      lieu: Du an sua dan roi doc tung khoi; Lo nhap mot lan, kiem het roi chay
      het.

VI SAO `nhan` CHI LO DUNG:
    CSV cua khach thuong co cot ten rieng, va mot tep zip chua `1.wav`, `2.wav`,
    `3.wav` la mot tep zip vo dung -- nguoi nhan khong biet dong nao ra dong nao.

VI SAO `loi` LA MOT COT CHU KHONG DOC TU JOB:
    Man Chay lo hien hang tram dong. Tra `job_events` cho tung dong la hang tram
    truy van moi lan dung trang. Cot nay la BAN SAO cua cau loi DA DUYET
    (`public_message`), chep vao luc poll -- khong bao gio chep `job.error` tho,
    vi chuoi tho co the mang duong dan noi bo.

DUONG LUI: `downgrade()` bo ba cot. Du lieu Lo se mat `loai` va tro thanh Du an
    trong mat man hinh -- chap nhan duoc cho mot lan lui, va khong tep tieng nao
    bi anh huong (chung thuoc vong doi cua JOB).

⚠️ SQLite khong `ALTER COLUMN`, nhung `ADD COLUMN` co `server_default` thi chay
    binh thuong -- da thu ca upgrade lan downgrade tren sqlite dung mot lan.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d4e0a63b8f29"
down_revision = "c3d9f52a7e18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `server_default` bat buoc: bang co the da co dong, va cot NOT NULL khong
    # mac dinh se lam `ALTER TABLE` that bai tren moi CSDL.
    op.add_column("voice_project",
                  sa.Column("loai", sa.String(length=16), nullable=False,
                            server_default="du_an"))
    op.create_index("ix_voice_project_loai", "voice_project", ["loai"])

    # Chi muc cu chi co (owner_id, trang_thai); moi truy van danh sach nay loc
    # them `loai`, nen no phai vao chi muc — khong thi man Du an quet ca cac lo.
    op.drop_index("ix_voice_project_owner", table_name="voice_project")
    op.create_index("ix_voice_project_owner", "voice_project",
                    ["owner_id", "loai", "trang_thai"])

    op.add_column("voice_block",
                  sa.Column("nhan", sa.String(length=120), nullable=False,
                            server_default=""))
    op.add_column("voice_block",
                  sa.Column("loi", sa.String(length=500), nullable=False,
                            server_default=""))


def downgrade() -> None:
    op.drop_column("voice_block", "loi")
    op.drop_column("voice_block", "nhan")

    op.drop_index("ix_voice_project_owner", table_name="voice_project")
    op.create_index("ix_voice_project_owner", "voice_project",
                    ["owner_id", "trang_thai"])
    op.drop_index("ix_voice_project_loai", table_name="voice_project")
    op.drop_column("voice_project", "loai")
