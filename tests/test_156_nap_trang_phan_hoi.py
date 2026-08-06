"""
H9.6 — trang phản hồi sau thanh toán, và URL trả về của cổng.

Bug thật, phát hiện bởi giao dịch 50.000đ đầu tiên (2026-08-06): route gửi chuỗi
`PLACEHOLDER` làm `return_url`, nên trả tiền xong PayOS ném khách vào
`/nap/don/PLACEHOLDER` → tra không ra đơn → một dòng chữ trần "Không thấy đơn."
Khách vừa mất tiền nhìn thấy đúng câu đó.

Ba lớp khoá ở đây:
1. `tao_don` phải thay `{order_id}` bằng id THẬT trước khi gọi cổng;
2. mã nguồn không được tái xuất hiện chuỗi giữ chỗ;
3. khi vẫn hụt đơn, trang phải là trang tử tế có lối thoát — và phải nói rõ
   "tiền không mất", vì đó là điều người đọc đang lo.
"""
from __future__ import annotations

import re

import pytest


# ── 1. URL trả về mang id thật ────────────────────────────────────────────────
@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'b.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
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


class _CongGia:
    """Cổng giả — chỉ ghi lại tham số nhận được."""
    def __init__(self):
        self.nhan = {}

    def da_cau_hinh(self):
        return True

    def tao_thanh_toan(self, **kw):
        self.nhan = kw
        return {"checkout_url": "https://pay.example/x", "ref": "REF1"}


def _goi(db):
    from platform_core.models import CreditPackage
    p = CreditPackage(name="G", price_vnd=50_000, credits_base=500,
                      bonus_percent=0, sort_order=1)
    db.add(p); db.flush()
    return p


def test_return_url_mang_id_that_khong_phai_chuoi_giu_cho(db, monkeypatch):
    import platform_core.payments as payments
    from platform_core import billing
    cong = _CongGia()
    monkeypatch.setitem(payments.GATEWAYS, "payos", cong)

    order = billing.tao_don(
        db, user_id="u1", package=_goi(db), gateway_id="payos",
        return_url="https://x.test/nap/don/{order_id}",
        cancel_url="https://x.test/nap/don/{order_id}")
    db.commit()

    assert cong.nhan["return_url"] == f"https://x.test/nap/don/{order.id}"
    assert cong.nhan["cancel_url"] == f"https://x.test/nap/don/{order.id}"
    assert "{order_id}" not in cong.nhan["return_url"]


def test_url_khong_co_token_thi_giu_nguyen(db, monkeypatch):
    """Tương thích ngược: chuỗi không chứa `{order_id}` không bị đụng."""
    import platform_core.payments as payments
    from platform_core import billing
    cong = _CongGia()
    monkeypatch.setitem(payments.GATEWAYS, "payos", cong)
    billing.tao_don(db, user_id="u1", package=_goi(db), gateway_id="payos",
                    return_url="https://x.test/xong", cancel_url="")
    db.commit()
    assert cong.nhan["return_url"] == "https://x.test/xong"
    assert cong.nhan["cancel_url"] == ""


def test_ma_nguon_khong_con_chuoi_giu_cho():
    """Bánh cóc: đừng ai ghép lại chuỗi giữ chỗ vào URL gửi cho cổng.

    Soi bằng AST chứ không tìm chuỗi cả file — tìm cả file sẽ dính vào chính
    đoạn chú thích kể lại con bug này, tức báo động giả mãi mãi.
    """
    import ast
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "server" / "routes" / "billing.py"
    text = src.read_text(encoding="utf-8")
    cay = ast.parse(text)

    xem_xet = []
    for node in ast.walk(cay):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg in ("return_url", "cancel_url"):
                    xem_xet.append((kw.arg, ast.get_source_segment(text, kw.value) or ""))

    assert xem_xet, "khong tim thay cho nao truyen return_url/cancel_url"
    for ten, doan in xem_xet:
        assert "PLACEHOLDER" not in doan, (
            f"{ten} lại chứa chuỗi giữ chỗ ({doan!r}) — cổng sẽ đưa khách tới "
            f"URL đó thật, và khách vừa trả tiền sẽ rơi vào trang 404")
        assert "{order_id}" in doan, (
            f"{ten}={doan!r} không mang id đơn — khách quay về sẽ không thấy đơn")


# ── 2. Trang phản hồi ─────────────────────────────────────────────────────────
@pytest.fixture()
def web(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    url = f"sqlite:///{(tmp_path / 'w.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-nap-phan-hoi")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "test-material-cho-secretbox-123")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core import billing
    from platform_core.models import CreditPackage
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); s = next(gen)
    ua = tao_nguoi_dung(s, email="a@x.com", password="matkhau-tot", is_verified=True)
    ub = tao_nguoi_dung(s, email="b@x.com", password="matkhau-tot", is_verified=True)
    pkg = CreditPackage(name="Goi 50K", price_vnd=50_000, credits_base=500,
                        bonus_percent=0, sort_order=1)
    s.add(pkg); s.flush()
    don_a = billing.tao_don(s, user_id=ua.id, package=pkg, gateway_id="payos")
    don_a.checkout_url = "https://pay.example/abc"
    don_b = billing.tao_don(s, user_id=ub.id, package=pkg, gateway_id="payos")
    s.commit()
    thong_tin = {"a": don_a.id, "b": don_b.id, "code_a": don_a.order_code}
    s.close()

    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver")
    try:
        yield c, thong_tin
    finally:
        dbmod.reset_engine()


def _login(client, email):
    client.post("/logout", follow_redirects=False)
    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text).group(1)
    r = client.post("/login", data={"username": email, "password": "matkhau-tot",
                                    "csrf_token": tok}, follow_redirects=False)
    assert r.status_code == 303


def test_don_khong_ton_tai_ra_trang_tu_te_khong_phai_mot_dong_chu(web):
    client, _ = web
    _login(client, "a@x.com")
    r = client.get("/nap/don/PLACEHOLDER")
    assert r.status_code == 404
    html = r.text
    # Trang thật, không phải chuỗi trần: có khung trang và lối đi tiếp.
    assert 'href="/nap"' in html
    assert len(html) > 500, "van con la mot dong chu tran"
    # Điều người vừa mất tiền cần đọc đầu tiên.
    assert "tiền không mất" in html.lower() or "không mất" in html


def test_hut_id_van_tim_duoc_don_qua_order_code(web):
    """Cổng đính `?orderCode=` — dùng nó cứu URL hỏng, khỏi bỏ rơi khách đã trả."""
    client, tt = web
    _login(client, "a@x.com")
    r = client.get(f"/nap/don/PLACEHOLDER?orderCode={tt['code_a']}")
    assert r.status_code == 200
    assert str(tt["code_a"]) in r.text


def test_khong_xem_duoc_don_cua_nguoi_khac(web):
    client, tt = web
    _login(client, "a@x.com")
    r = client.get(f"/nap/don/{tt['b']}")
    assert r.status_code == 404


def test_order_code_cua_nguoi_khac_cung_khong_lot(web):
    """Đường vòng orderCode không được thành lỗ hổng xem đơn người khác."""
    client, tt = web
    import platform_core.db as dbmod
    from platform_core import billing
    gen = dbmod.get_session(); s = next(gen)
    code_b = billing.lay_don(s, tt["b"]).order_code
    s.close()
    _login(client, "a@x.com")
    r = client.get(f"/nap/don/PLACEHOLDER?orderCode={code_b}")
    assert r.status_code == 404


def test_vua_ve_tu_cong_thi_noi_dang_xac_nhan(web):
    """Webhook đo thật mất ~40 giây. Trong lúc đó phải trấn an, không được để
    khách tưởng hỏng rồi chuyển tiền lần hai."""
    client, tt = web
    _login(client, "a@x.com")
    r = client.get(f"/nap/don/{tt['a']}/trangthai?ve=1")
    assert r.status_code == 200
    assert "xác nhận" in r.text
    assert "không cần chuyển lại" in r.text


def test_chua_ve_thi_van_la_dang_cho_thanh_toan(web):
    client, tt = web
    _login(client, "a@x.com")
    r = client.get(f"/nap/don/{tt['a']}/trangthai")
    assert "Đang chờ thanh toán" in r.text


def test_don_da_tra_khong_con_nut_mo_cong(web):
    """Bấm lại link cổng sau khi đã trả = nguy cơ chuyển tiền lần hai."""
    client, tt = web
    import platform_core.db as dbmod
    from platform_core import billing
    gen = dbmod.get_session(); s = next(gen)
    code = billing.lay_don(s, tt["a"]).order_code
    billing.ghi_nhan_tra(s, code, gateway_ref="FT999"); s.commit(); s.close()

    _login(client, "a@x.com")
    html = client.get(f"/nap/don/{tt['a']}").text
    assert "Mở PayOS" not in html
    assert "https://pay.example/abc" not in html


def test_don_da_tra_khong_con_noi_chuyen_khoan_hay_han(web):
    """Đơn đã trả mà vẫn hiện 'Hết hạn' + 'chuyển khoản đúng số tiền' thì khách
    tưởng chưa xong, hoặc tưởng credit cũng hết hạn theo."""
    client, tt = web
    import platform_core.db as dbmod
    from platform_core import billing
    gen = dbmod.get_session(); s = next(gen)
    code = billing.lay_don(s, tt["a"]).order_code
    billing.ghi_nhan_tra(s, code, gateway_ref="FT999"); s.commit(); s.close()

    _login(client, "a@x.com")
    html = client.get(f"/nap/don/{tt['a']}").text
    assert "Hết hạn" not in html
    assert "Chuyển khoản đúng số tiền" not in html
    assert "Đơn đã hoàn tất" in html


def test_don_chua_tra_van_hien_han_thanh_toan(web):
    client, tt = web
    _login(client, "a@x.com")
    html = client.get(f"/nap/don/{tt['a']}").text
    assert "Hết hạn" in html


def test_don_da_tra_hien_bien_lai_day_du(web):
    client, tt = web
    import platform_core.db as dbmod
    from platform_core import billing
    gen = dbmod.get_session(); s = next(gen)
    code = billing.lay_don(s, tt["a"]).order_code
    billing.ghi_nhan_tra(s, code, gateway_ref="FT999"); s.commit(); s.close()

    _login(client, "a@x.com")
    html = client.get(f"/nap/don/{tt['a']}/trangthai").text
    assert "Thanh toán thành công" in html
    assert "FT999" in html                      # ma giao dich de doi soat
    assert "500" in html                        # so credit da cong
