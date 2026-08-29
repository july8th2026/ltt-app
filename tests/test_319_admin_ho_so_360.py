"""Lo C2 — Ho so khach hang 360 (`05_PAGE_CONTRACT_MATRIX.md` P3) + GJ1.

Golden Journey 1: tim khach -> mo ho so -> hieu tinh hinh -> thao tac an toan ->
dau vet trong nhat ky. Tep nay di het duong do bang HTTP that.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def gj1(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'gj1.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-gj1")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="sep@example.com", password="matkhau-tot-12",
                       role="admin", is_verified=True)
        u = tao_nguoi_dung(db, email="khach@example.com",
                           password="matkhau-tot-12", role="user",
                           is_verified=True)
        credit.cap_tay(db, u.id, 300, by="test", note="mo so")
        db.commit()
        uid = u.id
    finally:
        try: next(gen)
        except StopIteration: pass

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")

    # Khach dang nhap that -> co mot phien that de thu hoi.
    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text)
    client.post("/login", data={"username": "khach@example.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": tok.group(1)},
                follow_redirects=False)
    client.cookies.clear()

    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text)
    r = client.post("/login", data={"username": "sep@example.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": tok.group(1)},
                    follow_redirects=False)
    assert r.status_code == 303
    client.uid = uid
    try:
        yield client
    finally:
        dbmod.reset_engine()


def test_khong_tim_thay_tra_404_va_noi_lam_gi_tiep(gj1):
    r = gj1.get("/admin/nguoi-dung?q=khong-ai@vidu.com")
    assert r.status_code == 404
    assert "Không tìm thấy" in r.text


def test_chua_go_gi_thi_khong_phai_la_loi(gj1):
    r = gj1.get("/admin/nguoi-dung")
    assert r.status_code == 200
    assert "Gõ email hoặc User ID" in r.text


def test_ho_so_gom_du_cac_khoi_co_nguon_that(gj1):
    body = gj1.get("/admin/nguoi-dung?q=khach@example.com").text
    for khoi in ("Biến động credit", "Đơn nạp", "Việc đã chạy", "Quyền app",
                 "Admin đã làm gì với tài khoản này", "Phiên đăng nhập"):
        assert khoi in body, khoi
    assert "300 credit" in body


def test_khong_bia_du_lieu_ho_so_khach(gj1):
    """Anh mockup co muoi mot truong ma bang `users` khong co.

    Day la kiem TREN TRANG DA RENDER, khac voi `test_317` (grep template) — mot
    chuoi cung co the lot vao qua chuoi f-string trong Python.
    """
    body = gj1.get("/admin/nguoi-dung?q=khach@example.com").text
    for cam in ("KYC", "Ngày sinh", "Số điện thoại", "Quốc gia",
                "Ghi chú hỗ trợ", "Gói dịch vụ", "Gia hạn"):
        assert cam not in body, cam


def test_thu_hoi_phien_can_csrf(gj1):
    r = gj1.post("/admin/nguoi-dung/thu-hoi-phien",
                 data={"user_id": gj1.uid, "csrf_token": "sai"},
                 follow_redirects=False)
    assert r.status_code == 400


def test_gj1_thu_hoi_phien_chay_that_va_de_lai_dau_vet(gj1):
    """Duong day du: ho so -> hanh dong -> hieu qua -> nhat ky admin.

    Truoc dot nay thao tac an ninh nay chi lam duoc bang cach vao bang tho
    `/admin/session/list`, loc bang UUID, roi bam "xoa dong" tung dong — va
    KHONG de lai dau vet admin nao.
    """
    import platform_core.db as dbmod
    from platform_core.models import NhatKyAdmin
    from platform_core.models import Session as DbSession

    trang = gj1.get(f"/admin/nguoi-dung?q={gj1.uid}").text
    tok = re.search(r'name="csrf_token" value="([^"]+)"', trang)
    assert tok

    gen = dbmod.get_session(); db = next(gen)
    try:
        truoc = db.query(DbSession).filter(DbSession.user_id == gj1.uid).count()
    finally:
        try: next(gen)
        except StopIteration: pass
    assert truoc >= 1, "khach phai co it nhat mot phien de phep kiem co y nghia"

    r = gj1.post("/admin/nguoi-dung/thu-hoi-phien",
                 data={"user_id": gj1.uid, "csrf_token": tok.group(1)},
                 follow_redirects=False)
    assert r.status_code == 303
    assert "/admin/nguoi-dung?q=" in r.headers["location"]

    gen = dbmod.get_session(); db = next(gen)
    try:
        sau = db.query(DbSession).filter(DbSession.user_id == gj1.uid).count()
        vet = db.query(NhatKyAdmin).filter(
            NhatKyAdmin.hanh_dong == "thu_hoi_phien").all()
    finally:
        try: next(gen)
        except StopIteration: pass

    assert sau == 0
    assert len(vet) == 1
    assert vet[0].doi_tuong == gj1.uid
    assert vet[0].admin_email == "sep@example.com"


def test_hanh_dong_nguy_hiem_khong_dung_chung_hang_voi_thao_tac_doc(gj1):
    """Hop dong P3: khong don moi nut do vao mot thanh.

    Anh mockup ve bon nut canh nhau o dau trang — "Cong credit", "Xem don hang",
    "Thu hoi phien", "Khoa tai khoan" — tuc mot thao tac doc dung ngay canh mot
    thao tac chan dang nhap, cung kich thuoc, cung hang.
    """
    body = gj1.get(f"/admin/nguoi-dung?q={gj1.uid}").text
    assert "Thao tác thường" in body
    assert "Thao tác nguy hiểm" in body
    thuong = body.index("Thao tác thường")
    nguy = body.index("Thao tác nguy hiểm")
    assert thuong < nguy, "thao tac doc phai dung TRUOC khoi nguy hiem"
    # Nut nguy hiem phai co xac nhan, khong phai mot cu bam.
    assert "onclick=\"return confirm(" in body[nguy:]
