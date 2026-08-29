"""Lo C10 — Tong quan quan tri (`05_PAGE_CONTRACT_MATRIX.md` P1) + GJ6.

Truoc dot nay GJ6 (suc khoe nen tang) KHONG CO DIEM BAT DAU: `/admin/` la trang
index cua goi SQLAdmin, va muc dau `_ADM_NAV` tro ve trang chu nen tang.

Luat cung cua P1: moi muc trong hang doi phai mo DUNG trang xu ly duoc no, kem
bo loc dat san. Tep nay di theo tung lien ket do de chung minh dieu ay.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def tq(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'tq.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-tong-quan")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="sep@example.com", password="matkhau-tot-12",
                       role="admin", is_verified=True)
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text)
    r = client.post("/login", data={"username": "sep@example.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": tok.group(1)},
                    follow_redirects=False)
    assert r.status_code == 303
    try:
        yield client
    finally:
        dbmod.reset_engine()


def _them_viec_hong(email="hong@example.com"):
    import platform_core.db as dbmod
    from platform_core.models import Job
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        u = tao_nguoi_dung(db, email=email, password="matkhau-tot-12",
                           role="user", is_verified=True)
        db.add(Job(user_id=u.id, app_slug="thumbnail", job_type="render",
                   status="error"))
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass


def test_admin_root_la_trang_cua_nen_tang_khong_phai_cua_goi_sqladmin(tq):
    """`/admin/` von thuoc ve `sqladmin` (`Route("/", endpoint=self.index)`).

    Ghi de `index` la diem mo rong chinh thuc — docstring cua chinh goi noi vay.
    Phep kiem nay chot rang viec ghi de THAT SU an, khong phai chi suy luan duoc.
    """
    r = tq.get("/admin/")
    assert r.status_code == 200
    assert 'class="adm-side"' in r.text          # vo cua ta
    assert "sqladmin/index.html" not in r.text
    assert "Tổng quan" in r.text


def test_hang_doi_rong_thi_noi_ro_la_rong_chu_khong_de_trong(tq):
    body = tq.get("/admin/").text
    assert "Không có việc nào đang chờ" in body


def test_moi_muc_hang_doi_mo_duoc_va_da_dat_san_bo_loc(tq):
    """Luat cung cua P1, kiem bang cach ĐI THEO tung lien ket."""
    _them_viec_hong()
    body = tq.get("/admin/").text
    assert "Việc chạy hỏng" in body

    dich = set(re.findall(r'<a href="(/admin/[^"]+)">', body))
    hang_doi = {d for d in dich if "job" in d or "don" in d or "khach-hang" in d}
    assert hang_doi, "hang doi khong tro di dau ca"
    for d in hang_doi:
        assert tq.get(d).status_code == 200, d


def test_tai_khoan_vo_hieu_hoa_dan_toi_danh_sach_DA_LOC(tq):
    import platform_core.db as dbmod
    from platform_core.models import User
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="tat@example.com", password="matkhau-tot-12",
                           role="user", is_verified=True)
        u.is_active = False
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    body = tq.get("/admin/").text
    assert "/admin/khach-hang?trang_thai=vo_hieu" in body, (
        "phai dat san bo loc, khong bo nguoi ta o mot danh sach day du")
    loc = tq.get("/admin/khach-hang?trang_thai=vo_hieu").text
    assert "tat@example.com" in loc


def test_tong_quan_khong_bia_chi_so(tq):
    """P1 cam sau thu, va ca sau deu co trong anh mockup cua cac trang khac."""
    body = tq.get("/admin/").text
    for cam in ("uptime", "SLA", "Độ tin cậy", "so với hôm qua", "Queue depth",
                "Worker"):
        assert cam.lower() not in body.lower(), cam


def test_nhat_ky_admin_hien_o_rail_va_la_du_lieu_that(tq):
    import platform_core.db as dbmod
    from platform_core.models import NhatKyAdmin
    gen = dbmod.get_session(); db = next(gen)
    try:
        db.add(NhatKyAdmin(admin_email="sep@example.com",
                           hanh_dong="thu_hoi_phien", doi_tuong="abc",
                           chi_tiet="thu"))
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    body = tq.get("/admin/").text
    assert "thu_hoi_phien" in body
    assert "sep@example.com" in body
