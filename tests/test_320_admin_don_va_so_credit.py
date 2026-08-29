"""Lo C3 — Don hang & so credit (`05_PAGE_CONTRACT_MATRIX.md` P5) + GJ2/GJ5.

Bat bien tien phai song sot qua dot doi giao dien:
  · so credit append-only,
  · mark-paid idempotent,
  · lich su don khong bi viet lai.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def tien(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'tien.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-tien")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core import billing
    from platform_core.models import CreditPackage
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="sep@example.com", password="matkhau-tot-12",
                       role="admin", is_verified=True)
        u = tao_nguoi_dung(db, email="khach@example.com",
                           password="matkhau-tot-12", role="user",
                           is_verified=True)
        goi = CreditPackage(name="Goi thu", price_vnd=100_000, credits_base=1000,
                            bonus_percent=0, active=True)
        db.add(goi); db.flush()
        don = billing.tao_don(db, user_id=u.id, package=goi, gateway_id="payos")
        db.commit()
        ids = {"uid": u.id, "code": don.order_code}
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
    client.ids = ids
    try:
        yield client
    finally:
        dbmod.reset_engine()


def _tok(client):
    """Token CSRF lay tu mot trang LUON co form.

    ⚠️ Khong lay tu `/admin/don`: sau khi mot don duoc xac nhan, form mark-paid
    cua no bien mat (chi don `pending` moi co), nen trang co the khong con form
    nao — va phep kiem se hong vi mot ly do khong lien quan gi toi thu no do.
    """
    m = re.search(r'name="csrf_token" value="([^"]+)"',
                  client.get("/admin/grant-credit").text)
    assert m
    return m.group(1)


def test_don_hien_email_chu_khong_phai_tam_ky_tu_uuid(tien):
    """GJ2/GJ5: het luong copy UUID bang tay.

    Truoc dot nay cot "User" hien `user_id[:8]` — tam ky tu dau cua mot UUID,
    khong bam duoc, khong noi len ai. Muon biet do la ai phai chep no sang mot
    trang khac.
    """
    body = tien.get("/admin/don").text
    assert "khach@example.com" in body
    assert f'/admin/nguoi-dung?q={tien.ids["uid"]}' in body


def test_loc_theo_ma_don(tien):
    body = tien.get(f"/admin/don?q={tien.ids['code']}").text
    assert str(tien.ids["code"]) in body


def test_mark_paid_can_csrf(tien):
    r = tien.post("/admin/don/action",
                  data={"order_code": tien.ids["code"], "csrf_token": "sai"},
                  follow_redirects=False)
    assert r.status_code == 400


def test_gj5_mark_paid_cong_credit_dung_mot_lan_va_noi_ro_ket_qua(tien):
    """Bam hai lan KHONG cong doi, va lan thu hai NOI ra la no khong lam gi.

    Im lang chuyen huong thi nguoi bam khong biet minh vua khong lam gi — va lan
    sau ho se bam tiep.
    """
    import platform_core.db as dbmod
    from platform_core import credit

    code = tien.ids["code"]
    r1 = tien.post("/admin/don/action",
                   data={"order_code": code, "csrf_token": _tok(tien)},
                   follow_redirects=False)
    assert r1.status_code == 303
    assert "ok=" in r1.headers["location"]

    gen = dbmod.get_session(); db = next(gen)
    try:
        sau_lan_1 = credit.so_du(db, tien.ids["uid"])
    finally:
        try: next(gen)
        except StopIteration: pass
    assert sau_lan_1 == 1000

    r2 = tien.post("/admin/don/action",
                   data={"order_code": code, "csrf_token": _tok(tien)},
                   follow_redirects=False)
    assert r2.status_code == 303
    assert "tu+truoc" in r2.headers["location"] or "tu%20truoc" in r2.headers["location"]

    gen = dbmod.get_session(); db = next(gen)
    try:
        sau_lan_2 = credit.so_du(db, tien.ids["uid"])
    finally:
        try: next(gen)
        except StopIteration: pass
    assert sau_lan_2 == 1000, "mark-paid phai idempotent"


def test_mark_paid_de_lai_dau_vet_trong_nhat_ky_admin(tien):
    """⭐ Truoc dot nay thao tac TIEN nay khong co dong nao trong nhat ky admin.

    Dau vet chi nam o `order.note` va o but toan credit — tuc cau "ai xac nhan
    don nay, luc nao" khong tra duoc o noi nguoi ta se di tim.
    Xem `01_LIVE_EVIDENCE.md` E-03.
    """
    import platform_core.db as dbmod
    from platform_core.models import NhatKyAdmin

    tien.post("/admin/don/action",
              data={"order_code": tien.ids["code"], "csrf_token": _tok(tien)},
              follow_redirects=False)
    gen = dbmod.get_session(); db = next(gen)
    try:
        vet = db.query(NhatKyAdmin).filter(
            NhatKyAdmin.hanh_dong == "xac_nhan_don_da_tra").all()
    finally:
        try: next(gen)
        except StopIteration: pass
    assert len(vet) == 1
    assert vet[0].doi_tuong == str(tien.ids["code"])
    assert vet[0].admin_email == "sep@example.com"


def test_don_khong_tim_thay_khong_lam_hong_trang(tien):
    r = tien.post("/admin/don/action",
                  data={"order_code": 999_999_999, "csrf_token": _tok(tien)},
                  follow_redirects=False)
    assert r.status_code == 303
    assert "loi=" in r.headers["location"]


def test_so_credit_van_la_chi_doc(tien):
    """Hop dong P5: so credit khong duoc co nut tao/sua/xoa duoi bat ky hinh thuc nao."""
    body = tien.get("/admin/credit-entry/list").text
    assert "/admin/credit-entry/create" not in body
    assert "/admin/credit-entry/edit" not in body


def test_don_khong_co_cot_goi_dich_vu(tien):
    """Anh mockup co cot "Goi dich vu: Starter/Pro/Business - 30 ngay".

    Nen tang ban CREDIT, khong ban thue bao. `PaymentOrder.package_id` la goi
    NAP. Day la cai bay de lot nhat trong bo anh vi no khong trong giong mot
    metric gia — no trong nhu mot cot du lieu binh thuong.
    """
    body = tien.get("/admin/don").text
    assert "Gói dịch vụ" not in body
    assert "30 ngày" not in body


def test_tong_quan_tai_chinh_tra_loi_cau_hoi_don_nao_can_xu(tien):
    """Hop dong P4.

    Truoc dot nay trang nay co ba o so va mot bang don DA tra — tuc thu duy nhat
    con can lam gi do (don dang cho) thi khong co mat.
    """
    body = tien.get("/admin/doanh-thu").text
    assert body.count("Đơn cần xử lý") == 1
    assert "Đơn đã trả gần đây" in body
    assert "Hành động tiền của admin gần đây" in body
    # Don pending cua fixture phai co mat, kem lien ket sang khach.
    assert str(tien.ids["code"]) in body
    assert f'/admin/nguoi-dung?q={tien.ids["uid"]}' in body


def test_tong_quan_tai_chinh_khong_bia_kenh_thanh_toan(tien):
    """Anh mockup co donut VNPay / MoMo / the quoc te / chuyen khoan.

    Cong duy nhat cua nen tang la PayOS. Bon nhan do khong co nguon nao.
    """
    body = tien.get("/admin/doanh-thu").text
    for cam in ("VNPay", "MoMo", "Thẻ quốc tế", "Đối soát", "Sức khỏe tài chính"):
        assert cam not in body, cam
