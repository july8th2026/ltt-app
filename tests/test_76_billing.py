"""
H9 — Thanh toán / nạp credit: toán tiền, cổng agnostic (PayOS), nghiệp vụ đơn.

Chạy trên SQLite tạm. Khoá các tính chất TIỀN:
- toán base/bonus/tổng đúng, làm tròn xuống, không tạo credit lẻ;
- đơn hàng idempotent: webhook lặp / mark-paid lại KHÔNG cộng credit hai lần;
- chữ ký webhook PayOS verify được, chữ ký sai bị từ chối.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'billing.db').as_posix()}"
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


# ── H9.1 toán tiền ─────────────────────────────────────────────────────────────
def test_credits_base_theo_ti_gia():
    from platform_core import billing_math as bm
    assert bm.VND_PER_CREDIT == 100
    assert bm.credits_base_tu_vnd(100_000) == 1000     # 100k = 1000 credit
    assert bm.credits_base_tu_vnd(150) == 1            # lam tron xuong
    assert bm.credits_base_tu_vnd(99) == 0


def test_bonus_va_tong():
    from platform_core import billing_math as bm
    assert bm.bonus_credits(1000, 10) == 100
    assert bm.bonus_credits(1000, 0) == 0
    assert bm.bonus_credits(555, 10) == 55             # 55.5 -> 55 (xuong)
    assert bm.tong_credits(1000, 20) == 1200
    assert bm.tong_credits(1000, 0) == 1000


def test_gia_tri_am_bi_tu_choi():
    from platform_core import billing_math as bm
    with pytest.raises(ValueError):
        bm.credits_base_tu_vnd(-1)
    with pytest.raises(ValueError):
        bm.bonus_credits(-1, 10)


def test_tao_goi_va_don(db):
    from platform_core.models import CreditPackage, PaymentOrder, ORDER_PENDING
    pkg = CreditPackage(name="Goi 100k", price_vnd=100_000, credits_base=1000,
                        bonus_percent=0, sort_order=1)
    db.add(pkg); db.commit()
    assert pkg.id and pkg.active is True
    order = PaymentOrder(order_code=123456, user_id="u1", package_id=pkg.id,
                         price_vnd=100_000, credits=1000, bonus_percent=0)
    db.add(order); db.commit()
    assert order.status == ORDER_PENDING and order.credited is False


# ── H9.2 cổng agnostic + PayOS ─────────────────────────────────────────────────
def _payos(monkeypatch, key="test-checksum-key"):
    monkeypatch.setenv("LTT_PAYOS_CLIENT_ID", "cid")
    monkeypatch.setenv("LTT_PAYOS_API_KEY", "akey")
    monkeypatch.setenv("LTT_PAYOS_CHECKSUM_KEY", key)
    from platform_core.payments.payos import PayOSGateway
    return PayOSGateway()


def test_payos_tat_mem_khi_thieu_env(monkeypatch):
    for k in ("LTT_PAYOS_CLIENT_ID", "LTT_PAYOS_API_KEY", "LTT_PAYOS_CHECKSUM_KEY"):
        monkeypatch.delenv(k, raising=False)
    from platform_core.payments.payos import PayOSGateway
    from platform_core.payments import GatewayChuaCauHinh
    g = PayOSGateway()
    assert g.da_cau_hinh() is False
    with pytest.raises(GatewayChuaCauHinh):
        g.tao_thanh_toan(order_code=1, amount_vnd=100000, description="x",
                         return_url="r", cancel_url="c")


def test_payos_webhook_chu_ky_hop_le(monkeypatch):
    import json
    from platform_core.payments.payos import _sap_xep_ky
    g = _payos(monkeypatch)
    data = {"orderCode": 777, "amount": 100000, "code": "00", "reference": "FT123"}
    sig = _sap_xep_ky("test-checksum-key", data)
    body = json.dumps({"code": "00", "data": data, "signature": sig}).encode()
    out = g.xac_thuc_webhook({}, body)
    assert out == {"order_code": 777, "paid": True, "ref": "FT123"}


def test_payos_webhook_chu_ky_sai_bi_tu_choi(monkeypatch):
    import json
    from platform_core.payments import ChuKyKhongHopLe
    g = _payos(monkeypatch)
    data = {"orderCode": 777, "amount": 100000, "code": "00"}
    body = json.dumps({"code": "00", "data": data, "signature": "sai-be-bet"}).encode()
    with pytest.raises(ChuKyKhongHopLe):
        g.xac_thuc_webhook({}, body)


def test_payos_webhook_da_bi_sua_doi(monkeypatch):
    # Ký theo amount cũ rồi đổi amount -> chữ ký không còn khớp.
    import json
    from platform_core.payments.payos import _sap_xep_ky
    from platform_core.payments import ChuKyKhongHopLe
    g = _payos(monkeypatch)
    data = {"orderCode": 5, "amount": 100000, "code": "00"}
    sig = _sap_xep_ky("test-checksum-key", data)
    data["amount"] = 1  # sửa sau khi ký
    body = json.dumps({"code": "00", "data": data, "signature": sig}).encode()
    with pytest.raises(ChuKyKhongHopLe):
        g.xac_thuc_webhook({}, body)


def test_payos_registry_co_payos():
    from platform_core import payments
    assert payments.get("payos") is not None
    assert payments.get("payos").id == "payos"


# ── H9.3 nghiệp vụ đơn (idempotent) ────────────────────────────────────────────
def _goi(db, *, price=100_000, base=1000, bonus=10):
    from platform_core.models import CreditPackage
    p = CreditPackage(name=f"Goi {price}", price_vnd=price, credits_base=base,
                      bonus_percent=bonus, sort_order=1)
    db.add(p); db.commit(); return p


def test_tao_don_chot_credits_gom_bonus(db):
    from platform_core import billing
    p = _goi(db, price=100_000, base=1000, bonus=10)
    order = billing.tao_don(db, user_id="u1", package=p, gateway_id="payos")
    db.commit()
    assert order.credits == 1100 and order.bonus_percent == 10
    assert order.status == "pending" and order.credited is False
    assert order.order_code >= 1_000_000_000


def test_ghi_nhan_tra_cong_credit_dung_mot_lan(db):
    from platform_core import billing, credit
    p = _goi(db, price=100_000, base=1000, bonus=10)
    order = billing.tao_don(db, user_id="u1", package=p, gateway_id="payos"); db.commit()
    billing.ghi_nhan_tra(db, order.order_code, gateway_ref="FT1"); db.commit()
    assert credit.so_du(db, "u1") == 1100
    db.refresh(order)
    assert order.credited is True and order.status == "paid"
    # Gọi lại (webhook lặp) -> KHÔNG cộng đôi.
    billing.ghi_nhan_tra(db, order.order_code); db.commit()
    assert credit.so_du(db, "u1") == 1100


def test_ghi_nhan_tra_don_khong_ton_tai(db):
    from platform_core import billing
    assert billing.ghi_nhan_tra(db, 999_999) is None


def test_het_han_don(db):
    from datetime import datetime, timedelta, timezone
    from platform_core import billing
    p = _goi(db)
    order = billing.tao_don(db, user_id="u1", package=p, gateway_id="payos")
    order.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    assert billing.het_han_don(db) == 1
    db.commit(); db.refresh(order)
    assert order.status == "expired"


def test_doanh_thu(db):
    from platform_core import billing
    p = _goi(db, price=100_000, base=1000, bonus=0)
    for u in ("u1", "u2"):
        o = billing.tao_don(db, user_id=u, package=p, gateway_id="payos"); db.commit()
        billing.ghi_nhan_tra(db, o.order_code); db.commit()
    dt = billing.doanh_thu(db)
    assert dt == {"vnd": 200_000, "credits": 2000, "orders": 2}


# ── H9.5 webhook (money boundary, qua TestClient) ──────────────────────────────
@pytest.fixture()
def wclient(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    url = f"sqlite:///{(tmp_path / 'wh.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-wh")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "test-material-cho-secretbox-123")
    monkeypatch.setenv("LTT_PAYOS_CLIENT_ID", "cid")
    monkeypatch.setenv("LTT_PAYOS_API_KEY", "akey")
    monkeypatch.setenv("LTT_PAYOS_CHECKSUM_KEY", "wh-key")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    # PayOS gateway đọc env lúc khởi tạo -> đăng ký lại để nhận checksum test.
    import platform_core.payments as payments
    from platform_core.payments.payos import PayOSGateway
    payments.GATEWAYS["payos"] = PayOSGateway()
    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver")
    try:
        yield c
    finally:
        dbmod.reset_engine()


def _tao_don_wh(user_id="u1"):
    import platform_core.db as dbmod
    from platform_core import billing
    from platform_core.models import CreditPackage
    gen = dbmod.get_session(); db = next(gen)
    try:
        p = CreditPackage(name="G", price_vnd=100_000, credits_base=1000,
                          bonus_percent=10, sort_order=1)
        db.add(p); db.flush()
        order = billing.tao_don(db, user_id=user_id, package=p, gateway_id="payos")
        db.commit()
        return order.order_code
    finally:
        try: next(gen)
        except StopIteration: pass


def _so_du(user_id="u1"):
    import platform_core.db as dbmod
    from platform_core.credit import so_du
    gen = dbmod.get_session(); db = next(gen)
    try:
        return so_du(db, user_id)
    finally:
        try: next(gen)
        except StopIteration: pass


def _body_webhook(order_code, key="wh-key"):
    import json
    from platform_core.payments.payos import _sap_xep_ky
    data = {"orderCode": order_code, "amount": 100_000, "code": "00", "reference": "FT9"}
    sig = _sap_xep_ky(key, data)
    return json.dumps({"code": "00", "data": data, "signature": sig})


def test_webhook_cong_credit_va_idempotent(wclient):
    code = _tao_don_wh("u1")
    assert _so_du("u1") == 0
    r = wclient.post("/webhooks/payment/payos", content=_body_webhook(code),
                     headers={"content-type": "application/json"})
    assert r.status_code == 200 and _so_du("u1") == 1100
    # Gửi lại -> KHÔNG cộng đôi.
    r2 = wclient.post("/webhooks/payment/payos", content=_body_webhook(code),
                      headers={"content-type": "application/json"})
    assert r2.status_code == 200 and _so_du("u1") == 1100


def test_webhook_chu_ky_sai_khong_cong(wclient):
    code = _tao_don_wh("u2")
    import json
    body = json.dumps({"code": "00",
                       "data": {"orderCode": code, "amount": 100_000, "code": "00"},
                       "signature": "sai"})
    r = wclient.post("/webhooks/payment/payos", content=body,
                     headers={"content-type": "application/json"})
    assert r.status_code == 400 and _so_du("u2") == 0


def test_nap_can_dang_nhap(wclient):
    r = wclient.get("/nap", follow_redirects=False)
    assert r.status_code in (302, 303, 307)   # chưa đăng nhập -> đá về /login
