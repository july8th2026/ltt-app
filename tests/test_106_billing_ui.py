"""Regression guards for H15.S2 BILL-001."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _template(name: str) -> str:
    return (ROOT / "server" / "templates" / name).read_text(encoding="utf-8")


def test_billing_route_loads_user_scoped_recent_orders():
    source = (ROOT / "server" / "routes" / "billing.py").read_text(encoding="utf-8")
    assert "billing.liet_ke_don(db, user_id=u.id, limit=10)" in source
    assert '"don_gan_day": don_gan_day' in source


def test_billing_page_has_quote_history_and_localized_statuses():
    source = _template("nap.html")
    assert "Báo giá trọn gói" in source
    assert 'aria-labelledby="billing-history-title"' in source
    # Golden UI 16/09: nhan trang thai don di qua macro dung chung (`_ui.html`)
    # va phan biet du 5 trang thai thay vi gop "Khong hoan tat"; chu tieng Viet
    # cua tung nhan chot o test_1270::test_nhan_trang_thai_don_nap.
    assert "ui.nhan_trang_thai(order.status, 'don')" in source
    assert "order.status }}" not in source


def test_order_status_is_announced_without_leaking_internal_enum():
    detail = _template("nap_don.html")
    fragment = _template("_nap_trangthai.html")
    assert 'aria-live="polite"' in detail
    assert 'aria-live="polite"' in fragment
    assert "Đơn {{ order.status }}" not in fragment
    assert 'rel="noopener"' in detail
