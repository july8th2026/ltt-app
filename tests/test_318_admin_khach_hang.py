"""Lo C1 — trang danh sach khach hang (`05_PAGE_CONTRACT_MATRIX.md` P2).

Chot ba thu ma hop dong trang noi, va mot thu ma no CAM.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'kh.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-khach-hang")
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
        tat = tao_nguoi_dung(db, email="datat@example.com",
                             password="matkhau-tot-12", role="user",
                             is_verified=False)
        tat.is_active = False
        credit.cap_tay(db, u.id, 500, by="test", note="mo so")
        db.commit()
        ids = {"khach": u.id, "tat": tat.id}
    finally:
        try: next(gen)
        except StopIteration: pass

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text)
    assert tok
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


def test_danh_sach_hien_khach_va_so_du_bang_credit(khach):
    trang = khach.get("/admin/khach-hang")
    assert trang.status_code == 200
    body = trang.text
    assert "khach@example.com" in body
    # ⭐ Don vi la CREDIT. `PaymentOrder` tach `price_vnd` khoi `credits`
    #    (1 credit = 100 d), va anh mockup ghi so du kem "d" — be nguyen nhan do
    #    vao la sai so hien thi 100 lan.
    assert "500 credit" in body


def test_moi_dong_mo_duoc_ho_so_360_khong_phai_copy_uuid(khach):
    body = khach.get("/admin/khach-hang").text
    assert f'/admin/nguoi-dung?q={khach.ids["khach"]}' in body


def test_bo_loc_dung_truong_co_that(khach):
    chi_tat = khach.get("/admin/khach-hang?trang_thai=vo_hieu").text
    assert "datat@example.com" in chi_tat
    assert "khach@example.com" not in chi_tat

    chua = khach.get("/admin/khach-hang?xac_thuc=chua").text
    assert "datat@example.com" in chua

    tim = khach.get("/admin/khach-hang?q=khach@example.com").text
    assert "khach@example.com" in tim
    assert "datat@example.com" not in tim


def test_khong_ket_qua_thi_noi_lam_gi_tiep(khach):
    body = khach.get("/admin/khach-hang?q=khong-ai-ten-nhu-vay").text
    assert "dev-trong" in body
    assert "Bỏ lọc" in body


def test_bang_danh_sach_khong_chua_mutation(khach):
    """Hop dong P2: khong dat thao tac nguy hiem trong bang danh sach.

    Doi vai tro, vo hieu hoa, cap credit deu la thao tac len MOT khach — chung
    song trong Ho so 360, noi nguoi thao tac nhin thay doi tuong minh dang tac
    dong. Mot nut do tren mot dong cua bang dai la cach bam nham hang.
    """
    body = khach.get("/admin/khach-hang").text
    than = body[body.index('class="adm-content"'):]
    assert "<form" in than          # co dai loc...
    assert 'method="post"' not in than.lower()   # ...nhung khong form ghi nao
    assert "btn-danger" not in than


def test_rail_chu_y_chi_dem_tin_hieu_don_dinh(khach):
    body = khach.get("/admin/khach-hang").text
    assert "Tài khoản bị vô hiệu hoá" in body
    assert "Chưa xác thực email" in body
    # ⛔ Ba o cua anh mockup KHONG duoc dung: nen tang tra TRUOC bang credit nen
    #    khong co cong no; khong ban thue bao nen khong co han goi; khong co he
    #    ticket nen khong co yeu cau ho tro.
    for cam in ("Nợ quá hạn", "hết hạn gói", "Yêu cầu hỗ trợ"):
        assert cam not in body, cam


def test_sap_xep_theo_cot_va_giu_nguyen_bo_loc(khach):
    """Doi thu tu ma mat bo loc la mot cach lam mat cho nguoi ta dang dung."""
    body = khach.get("/admin/khach-hang?trang_thai=vo_hieu").text
    assert "sap_xep=dang_nhap" in body
    assert "trang_thai=vo_hieu" in body
    # Va lien ket sap xep phai giu bo loc:
    assert "trang_thai=vo_hieu&amp;sap_xep=dang_nhap" in body \
        or "sap_xep=dang_nhap&amp;trang_thai=vo_hieu" in body


def test_sap_xep_theo_email_doi_that_thu_tu(khach):
    import re
    def emails(url):
        return re.findall(r'<strong>([^<]+@[^<]+)</strong>', khach.get(url).text)
    assert emails("/admin/khach-hang?sap_xep=email") == sorted(
        emails("/admin/khach-hang?sap_xep=email"))


def test_khoa_sap_xep_la_bao_khong_lam_hong_trang(khach):
    """Danh sach trang: ten cot tuy y tu URL khong duoc ghep vao cau truy van."""
    r = khach.get("/admin/khach-hang?sap_xep=; DROP TABLE users")
    assert r.status_code == 200
    assert "khach@example.com" in r.text


def test_so_du_khong_sap_xep_duoc_va_do_la_mot_chot(khach):
    """`SAP_XEP` co y khong co "so du".

    So du la TONG cua so append-only, nen sap theo no can mot phep gop tren toan
    bang `credit_entries` roi moi phan trang duoc — mot luot quet toan bang cho
    moi lan doi trang. Neu ai do them no vao, phep kiem nay bat.
    """
    from platform_core.admin_console import SAP_XEP
    assert "so_du" not in SAP_XEP
    assert "balance" not in SAP_XEP


def test_user_id_khong_day_nut_hanh_dong_chinh_ra_ngoai(khach):
    """Do tren production 29/08, khung 1440px.

    Hien du 36 ky tu UUID lam cot dau rong 218px -> bang can 867px trong khung
    791px, va thu bi day ra ngoai la **nut hanh dong chinh** cua trang. Khong
    phai tran body (bang cuon trong khung cua no), nen phep quet tu dong khong
    bat duoc; chi nhin moi thay.

    Chot o day: ID phai cat bot, va gia tri day du phai con o `title`.
    """
    body = khach.get("/admin/khach-hang").text
    assert "adm-id-cat" in body
    assert f'title="{khach.ids["khach"]}"' in body


def test_rail_gap_xuong_du_som_de_nut_hanh_dong_chinh_khong_bi_day_ra():
    """Do tren PRODUCTION 29/08, khung 1440px — va day la mot lo hong cua chinh
    bo phep kiem nay, nen no dang duoc ghi lai.

    Rail 320px de lai 791px cho noi dung, trong khi bang khach hang can 867px:
    bay cot cong lai, moi cot da o muc toi thieu. Thu bi day ra ngoai la **nut
    hanh dong chinh** cua trang ("Mo ho so 360").

    ⛔ Vi sao khong phep kiem nao bat duoc:
       · quet tu dong do `body.scrollWidth` — bang cuon TRONG khung cua no nen
         body van dung, khong co tran ngang;
       · CSDL nhap chi co hai dong email ngan thi bang vua thoai mai.
       Chi 24 khach that voi email dai moi day no qua nguong.

    ⚠️ Lan sua dau tien SAI: cat bot User ID. CSS ap dung (ID con 101px) nhung
       bang VAN can 867px — cot dau rong vi EMAIL, khong vi UUID.
       Sua dung: nang nguong gap rail 1280 -> 1500px.
    """
    css = (GOC / "server/static/ltt.css").read_text(encoding="utf-8")
    assert "@media(max-width:1500px){.adm-luoi-rail" in css, (
        "nguong gap rail bi ha xuong — nut hanh dong chinh se bi day ra ngoai "
        "khung o 1440px")
