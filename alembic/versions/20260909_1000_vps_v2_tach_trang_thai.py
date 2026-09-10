"""VPS V2: tach `trang_thai` thanh vong doi / dien / tac vu / suc khoe (Pha 01).

Revision ID: b7f21c48ae90
Revises: a4c71e93f8b2
Create Date: 2026-09-09

## Vi sao

Mot cot `String(16)` dang ganh NAM cau hoi: may con la khach hang khong, khach
MUON no bat hay tat, no THUC SU dang bat hay tat, co viec gi dang chay do,
va ta con noi chuyen duoc voi no khong. Hai cau cuoi khong co cho nao de ghi,
nen chung bi nhet vao hai cau truoc — va do la goc cua ba loi P0 (V-02/V-03/V-04).

Xem `apps/vps/trang_thai_may.py` va `docs/vps_v2/ADR_INDEX.md` ADR-01.

## Cot `trang_thai` KHONG bi xoa

No doi vai: tu nguon su that thanh HINH CHIEU. Nho vay 18 tep test, 7 template
va bon bang tra trong `nhan.py` khong phai sua mot dong nao trong pha nay.

## Backfill: `quan_sat_luc` de NULL, va do la mot quyet dinh

Cam do la dat `quan_sat_luc = now()` cho moi dong dang chay — no lam bang du lieu
"day du" va lam moi canh bao tat het. Nhung ta CHUA HE do may nao ca; ta chi doc
lai mot con so CSDL da ghi tu truoc, co the tu tuan truoc.

Dong dau NULL noi dung su that: **chua do lan nao**. `trang_thai_may.qua_cu()`
coi NULL la qua cu, nen vong doi chieu dau tien sau khi trien khai se di do that
va dien vao. Dat mot dau thoi gian gia o day la bia mot phep do — cung hang loi
voi thu ma ca chuong trinh nay sinh ra de sua.
"""
from alembic import op
import sqlalchemy as sa

revision = "b7f21c48ae90"
down_revision = "a4c71e93f8b2"
branch_labels = None
depends_on = None


#: (trang_thai cu) -> (vong_doi, dien_mong_muon, dien_quan_sat, tac_vu)
#:
#: `dien_quan_sat` la `khong_ro` cho MOI hang, ke ca hang ghi `dang_chay`: gia
#: tri cu la mot y dinh da duoc ghi nham thanh mot quan sat, nen chep no sang cot
#: quan sat la chep lai dung loi do. Y dinh thi giu — no van dung.
_BACKFILL = {
    "dang_tao":  ("dang_tao",  "chay", "khong_ro", "dang_cap_phat"),
    "dang_chay": ("hoat_dong", "chay", "khong_ro", ""),
    "da_tat":    ("hoat_dong", "tat",  "khong_ro", ""),
    "bi_treo":   ("bi_treo",   "tat",  "khong_ro", ""),
    "loi":       ("loi",       "chay", "khong_ro", ""),
    "da_xoa":    ("da_xoa",    "tat",  "tat",      ""),
}


def upgrade() -> None:
    op.add_column("vps_instance", sa.Column(
        "vong_doi", sa.String(16), nullable=False, server_default="dang_tao"))
    op.add_column("vps_instance", sa.Column(
        "dien_mong_muon", sa.String(16), nullable=False, server_default="chay"))
    op.add_column("vps_instance", sa.Column(
        "dien_quan_sat", sa.String(16), nullable=False,
        server_default="khong_ro"))
    op.add_column("vps_instance", sa.Column(
        "tac_vu", sa.String(16), nullable=False, server_default=""))
    op.add_column("vps_instance", sa.Column(
        "suc_khoe", sa.String(16), nullable=False, server_default="khong_ro"))
    op.add_column("vps_instance", sa.Column(
        "quan_sat_luc", sa.DateTime(timezone=True), nullable=True))

    for cu, (vd, mm, qs, tv) in _BACKFILL.items():
        op.execute(sa.text(
            "UPDATE vps_instance SET vong_doi=:vd, dien_mong_muon=:mm, "
            "dien_quan_sat=:qs, tac_vu=:tv WHERE trang_thai=:cu"
        ).bindparams(vd=vd, mm=mm, qs=qs, tv=tv, cu=cu))

    # Mot ma trang thai LA la mot dong ta khong hieu. Dua no vao `loi` chu khong
    # vao `hoat_dong`: `loi` van dieu khien duoc va van hien ly do cho khach, con
    # `hoat_dong` la mot khang dinh rang moi thu binh thuong.
    op.execute(sa.text(
        "UPDATE vps_instance SET vong_doi='loi', dien_mong_muon='chay', "
        "dien_quan_sat='khong_ro' WHERE trang_thai NOT IN "
        "('dang_tao','dang_chay','da_tat','bi_treo','loi','da_xoa')"))

    op.create_index("ix_vps_instance_vong_doi", "vps_instance", ["vong_doi"])


def downgrade() -> None:
    # `trang_thai` chua bao gio ngung duoc ghi (no la hinh chieu, khong phai ban
    # sao du phong), nen go cac cot moi di la du — khong can dung lai gia tri nao.
    op.drop_index("ix_vps_instance_vong_doi", table_name="vps_instance")
    for cot in ("quan_sat_luc", "suc_khoe", "tac_vu", "dien_quan_sat",
                "dien_mong_muon", "vong_doi"):
        op.drop_column("vps_instance", cot)
