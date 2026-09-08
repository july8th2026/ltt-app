"""voice: cot license_status + bang voice_quality_profile (U-05, U-04).

Revision ID: a4c71e93f8b2
Revises: e8f35c1a7d64
Create Date: 2026-09-08

## Vi sao mot migration cho CA HAI

Hai hang muc, nhung mot cau hoi: *"giong nay co duoc mang ra kho chung khong"*.
`license_status` tra loi ve XUAT XU, `voice_quality_profile` tra loi ve CHAT
LUONG, va cong o `tham_chieu.py` doc ca hai. Tach lam hai luot thi co mot khoang
giua ma cong da bat nhung mot nua du lieu chua ton tai.

## [!] MOI DONG CU NHAN "cho_soat", KE CA DONG DANG `dung_chung=True`

Do KHONG phai mot so suat, va no la quyet dinh dat gia nhat cua migration nay:
mot dong `dung_chung=True` dat thanh "cho_soat" se **bien mat khoi kho chung**
ngay sau khi trien khai.

Van chon nhu vay, vi ba ly do theo thu tu quan trong:

  1. Chua ai soat that thi ghi "ok" la **bia mot phan quyet**. Cot nay sinh ra
     de duoc trich dan trong mot tranh chap; mot gia tri bia trong no con te
     hon khong co cot nao.
  2. Huong sai la huong an toan. "cho_soat" nham thi mot giong tam thoi khong
     hien; "ok" nham thi mot giong chua ro xuat xu duoc phat tan cho **moi**
     tai khoan, va do la loai loi khong lay lai duoc bang mot ban va.
  3. [!] CHUA DO co bao nhieu dong dang `dung_chung=True` tren production.
     Ban dau toi viet "do duoc: khong dong nao" o day - do la mot con so toi
     KHONG do, va no lam luan diem manh len mot cach khong that. Neu co dong
     nhu vay, chung se tam an sau khi trien khai, va cach mo lai la mot lenh
     UPDATE co y - khong phai mot migration doan ho.

     => Nguoi trien khai NEN dem truoc:
            SELECT count(*) FROM voice_profile WHERE dung_chung = true;
        So do doi kich thuoc cua hau qua, KHONG doi huong quyet dinh: ly do 1
        va 2 dung voi moi so.

⇒ Bat mot giong ra kho chung nay la HAI buoc co y: dat `dung_chung=True` va dat
  `license_status="ok"`. Hai buoc, vi do la hai cau hoi khac nhau.

## downgrade

Go het. Cot va bang deu MOI, khong co duong doc nao cu phu thuoc chung.
"""
from alembic import op
import sqlalchemy as sa

revision = "a4c71e93f8b2"
down_revision = "e8f35c1a7d64"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "voice_profile",
        sa.Column("license_status", sa.String(length=24), nullable=False,
                  server_default="cho_soat"),
    )
    op.create_index("ix_voice_profile_license", "voice_profile",
                    ["license_status"])

    op.create_table(
        "voice_quality_profile",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("trang_thai_curate", sa.String(length=24), nullable=False,
                  server_default="cho_soat"),
        sa.Column("ly_do_loai", sa.Text(), nullable=True),
        # [!] `nullable=True` KHONG PHAI luoi. `None` = CHUA DO, va no khac
        #     0.0 = "do duoc, va rat te". Mot cot `NOT NULL DEFAULT 0` se noi
        #     rang moi giong deu da duoc cham va deu duoc 0 diem.
        sa.Column("diem", sa.Float(), nullable=True),
        sa.Column("benchmark_version", sa.String(length=64), nullable=True),
        sa.Column("sample_key", sa.String(length=255), nullable=True),
        sa.Column("nguoi_soat", sa.String(length=36), nullable=True),
        sa.Column("soat_luc", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", name="uq_voice_quality_profile"),
    )
    op.create_index("ix_voice_quality_profile_profile_id",
                    "voice_quality_profile", ["profile_id"])
    op.create_index("ix_voice_quality_profile_trang_thai",
                    "voice_quality_profile", ["trang_thai_curate"])


def downgrade() -> None:
    op.drop_index("ix_voice_quality_profile_trang_thai",
                  table_name="voice_quality_profile")
    op.drop_index("ix_voice_quality_profile_profile_id",
                  table_name="voice_quality_profile")
    op.drop_table("voice_quality_profile")
    op.drop_index("ix_voice_profile_license", table_name="voice_profile")
    op.drop_column("voice_profile", "license_status")
