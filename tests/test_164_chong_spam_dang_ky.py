"""
Chống spam đăng ký — hai lớp bổ sung nhau (2026-08-07).

**Sự cố thật:** nhân viên vào tạo tài khoản để test, được 3 người thì bị chặn.
Nguyên nhân: trần 3 tài khoản/IP/24 giờ, mà cả đội ngồi cùng mạng văn phòng nên
ra Internet bằng **một IP công cộng** — và IP đó còn là **IP động**.

Cơ chế chạy đúng nhưng giả định sai: nó xây để chặn một người tạo hàng loạt tài
khoản ăn credit dùng thử, giả định "nhiều người lạ, mỗi người một IP".

**Vì sao không dùng IP làm danh tính:** IP động, dùng chung sau NAT, đổi được
bằng VPN trong năm giây. Nó vừa chặn nhầm người thật vừa không chặn được kẻ có
chủ ý — sai ở cả hai đầu.

Hai lớp phải đi cùng nhau:
- **L2 mở cửa cho người của mình** — miền email tin cậy không bị đếm theo IP.
- **L1 đóng cửa với người farm** — Gmail giao `a@`, `a+1@`, `a.b@` về CÙNG một
  hộp thư; trước đây đó là ba tài khoản, mỗi cái 20 credit.

Làm L2 một mình là nới lỏng. Làm L1 một mình thì nhân viên vẫn kẹt.
"""
from __future__ import annotations

import pytest


# ── L1: chuẩn hoá email theo hộp thư thật ────────────────────────────────────
@pytest.mark.parametrize("nhap,mong", [
    ("a@gmail.com", "a@gmail.com"),
    ("a+1@gmail.com", "a@gmail.com"),
    ("a+bat-ky-thu-gi@gmail.com", "a@gmail.com"),
    ("a.b.c@gmail.com", "abc@gmail.com"),
    ("A.B+x@GMail.COM", "ab@gmail.com"),
    ("a@googlemail.com", "a@gmail.com"),      # cung nha cung cap
    ("  a@gmail.com  ", "a@gmail.com"),
])
def test_gmail_alias_ve_cung_mot_hop_thu(nhap, mong):
    from platform_core.users import chuan_hoa_email_chong_trung
    assert chuan_hoa_email_chong_trung(nhap) == mong


@pytest.mark.parametrize("e", [
    "a.b@lttstudios.com", "a+x@congty.vn", "a.b@outlook.com",
])
def test_mien_khac_KHONG_bi_dung_luat_cua_gmail(e):
    """Mỗi nhà cung cấp một luật. Đoán bừa cho miền khác sẽ **gộp nhầm hai người
    thành một** — `a.b@congty.vn` và `ab@congty.vn` có thể là hai nhân viên."""
    from platform_core.users import chuan_hoa_email_chong_trung
    assert chuan_hoa_email_chong_trung(e) == e.lower()


def test_email_goc_KHONG_bi_sua():
    """Người dùng nhập `a.b@gmail.com` thì phải thấy đúng chuỗi đó — không phải
    chuỗi ta tự sửa. Chuẩn hoá chỉ dùng để chống trùng."""
    from platform_core.users import chuan_hoa_email
    assert chuan_hoa_email("A.B+x@Gmail.com") == "a.b+x@gmail.com"


# ── L1 qua CSDL: alias không tạo được tài khoản thứ hai ──────────────────────
@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 's.db').as_posix()}")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "test-material-cho-secretbox-123")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


def test_mot_hop_gmail_chi_tao_duoc_MOT_tai_khoan(db):
    """Đây là lỗ khai thác được: mỗi tài khoản 20 credit dùng thử."""
    from platform_core.users import UserError, tao_nguoi_dung
    tao_nguoi_dung(db, email="nguoi@gmail.com", password="matkhau-tot-12")
    db.commit()
    for alias in ("nguoi+1@gmail.com", "ng.uoi@gmail.com", "NGUOI@googlemail.com"):
        with pytest.raises(UserError):
            tao_nguoi_dung(db, email=alias, password="matkhau-tot-12")
        db.rollback()


def test_hai_nguoi_that_o_cung_mien_cong_ty_van_tao_duoc(db):
    from platform_core.users import tao_nguoi_dung
    tao_nguoi_dung(db, email="an.nguyen@lttstudios.com", password="matkhau-tot-12")
    tao_nguoi_dung(db, email="annguyen@lttstudios.com", password="matkhau-tot-12")
    db.commit()   # khong duoc gop nham hai nhan vien thanh mot


def test_email_chuan_duoc_ghi_xuong(db):
    from platform_core.models import User
    from platform_core.users import tao_nguoi_dung
    u = tao_nguoi_dung(db, email="A.B+x@Gmail.com", password="matkhau-tot-12")
    db.commit()
    assert u.email == "a.b+x@gmail.com"          # goc, de hien thi va gui thu
    assert u.email_chuan == "ab@gmail.com"       # chuan, de chong trung
    assert db.get(User, u.id).email_chuan == "ab@gmail.com"


# ── L2: miền tin cậy không bị đếm theo IP ────────────────────────────────────
@pytest.fixture()
def mien_tin_cay(monkeypatch):
    monkeypatch.setenv("LTT_DANGKY_MIEN_TIN_CAY", "lttstudios.com")
    import importlib

    from platform_core import antifraud
    importlib.reload(antifraud)
    yield antifraud
    monkeypatch.delenv("LTT_DANGKY_MIEN_TIN_CAY", raising=False)
    importlib.reload(antifraud)


def test_nhan_dien_mien_tin_cay(mien_tin_cay):
    assert mien_tin_cay.la_mien_tin_cay("ai-do@lttstudios.com")
    assert mien_tin_cay.la_mien_tin_cay("AI-DO@LTTSTUDIOS.COM")
    assert not mien_tin_cay.la_mien_tin_cay("nguoi-la@gmail.com")
    assert not mien_tin_cay.la_mien_tin_cay("khong-co-a-cong")


def test_nhan_vien_KHONG_bi_tran_IP_du_bao_nhieu_nguoi(db, mien_tin_cay):
    """Đây là sự cố thật đã xảy ra: cả đội một IP, người thứ 4 bị chặn."""
    from platform_core.users import tao_nguoi_dung
    IP = "14.177.12.60"
    for i in range(12):
        assert not mien_tin_cay.vuot_gioi_han_ip(db, IP, f"nv{i}@lttstudios.com")
        tao_nguoi_dung(db, email=f"nv{i}@lttstudios.com",
                       password="matkhau-tot-12", registration_ip=IP)
        db.commit()


def test_nguoi_LA_van_bi_tran_IP(db, mien_tin_cay):
    """L2 không được biến thành nới lỏng cho Internet."""
    from platform_core.users import tao_nguoi_dung
    IP = "1.2.3.4"
    n = mien_tin_cay.GIOI_HAN_IP_MOI_NGAY
    for i in range(n):
        assert not mien_tin_cay.vuot_gioi_han_ip(db, IP, f"la{i}@gmail.com")
        tao_nguoi_dung(db, email=f"la{i}@gmail.com",
                       password="matkhau-tot-12", registration_ip=IP)
        db.commit()
    assert mien_tin_cay.vuot_gioi_han_ip(db, IP, "them@gmail.com"), (
        "nguoi la khong con bi tran — L2 da thanh noi long cho ca Internet")


def test_khong_khai_mien_tin_cay_thi_moi_nguoi_deu_bi_tran(db, monkeypatch):
    """Mặc định phải là chặt. Quên khai biến môi trường không được thành mở toang."""
    import importlib

    monkeypatch.delenv("LTT_DANGKY_MIEN_TIN_CAY", raising=False)
    from platform_core import antifraud
    importlib.reload(antifraud)
    from platform_core.users import tao_nguoi_dung
    IP = "5.6.7.8"
    for i in range(antifraud.GIOI_HAN_IP_MOI_NGAY):
        tao_nguoi_dung(db, email=f"x{i}@lttstudios.com",
                       password="matkhau-tot-12", registration_ip=IP)
        db.commit()
    assert antifraud.vuot_gioi_han_ip(db, IP, "them@lttstudios.com")
