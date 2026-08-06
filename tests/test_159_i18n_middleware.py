"""
H24 Pha 0 — middleware ngôn ngữ, thử qua ứng dụng THẬT.

`test_158` thử logic thuần. Ở đây thử cả đường đi thật: bóc tiền tố, viết lại
`Location`, và — quan trọng nhất — **đường webhook không bị đụng tới**.

Vì sao webhook đứng đầu danh sách: PayOS gọi vào một URL cố định đã đăng ký. Gắn
tiền tố hay chuyển hướng đường đó nghĩa là khách trả tiền mà không nhận credit,
và lỗi chỉ lộ khi có người khiếu nại. Đúng loại lỗi `return_url=PLACEHOLDER` ngày
2026-08-06 — bên ngoài luôn gọi đúng URL ta đưa.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'i.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-i18n-mw")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "test-material-cho-secretbox-123")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver")
    try:
        yield c
    finally:
        dbmod.reset_engine()


VN = {"CF-IPCountry": "VN"}
US = {"CF-IPCountry": "US"}


# ── 1. Webhook và đường hệ thống: TUYỆT ĐỐI không đụng ───────────────────────
def test_webhook_thanh_toan_khong_bi_chuyen_huong_du_o_nuoc_ngoai(client):
    """Nguy hiểm nhất. 302 ở đây = PayOS gọi hụt = khách mất tiền."""
    r = client.post("/webhooks/payment/payos", json={}, headers=US,
                    follow_redirects=False)
    assert r.status_code != 302, "webhook bi chuyen huong — khach se mat tien"
    assert r.status_code in (400, 503)     # toi duoc ung dung, bi chan vi chu ky


def test_webhook_co_tien_to_thi_KHONG_ton_tai(client):
    """`/en/webhooks/...` không được là một đường hợp lệ — nếu nó chạy thì sẽ có
    người vô tình đăng ký URL đó với cổng thanh toán."""
    r = client.post("/en/webhooks/payment/payos", json={}, follow_redirects=False)
    assert r.status_code == 404


@pytest.mark.parametrize("duong", ["/health/ready", "/health/live"])
def test_health_khong_bi_chuyen_huong(client, duong):
    """`setup/4-nghiem-thu.ps1` và bộ giám sát mong 200, không phải 302."""
    r = client.get(duong, headers=US, follow_redirects=False)
    assert r.status_code == 200


def test_static_khong_bi_chuyen_huong(client):
    r = client.get("/static/ltt.css", headers=US, follow_redirects=False)
    assert r.status_code == 200


# ── 2. Bóc tiền tố: route cũ chạy nguyên xi ──────────────────────────────────
def test_tien_to_en_van_toi_dung_route(client):
    assert client.get("/en/login", follow_redirects=False).status_code == 200


def test_duong_goc_van_la_tieng_viet(client):
    r = client.get("/login", headers=VN, follow_redirects=False)
    assert r.status_code == 200


def test_duong_khong_ton_tai_van_404_ca_hai_ban(client):
    for d in ("/khong-co-trang-nay", "/en/khong-co-trang-nay"):
        assert client.get(d, headers=VN, follow_redirects=False).status_code == 404


# ── 3. Chuyển hướng lần đầu ──────────────────────────────────────────────────
def test_khach_nuoc_ngoai_duoc_dua_sang_en(client):
    r = client.get("/login", headers=US, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/en/login"


def test_khach_viet_nam_o_lai_duong_goc(client):
    r = client.get("/login", headers=VN, follow_redirects=False)
    assert r.status_code == 200


def test_chuyen_huong_giu_query_string(client):
    """Mất `?next=` là mất chỗ quay lại sau khi đăng nhập."""
    r = client.get("/login?next=/nap", headers=US, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/en/login?next=/nap"


def test_khong_co_tin_hieu_nao_thi_khong_chuyen_huong(client):
    """Script, bộ giám sát, curl — không gửi tín hiệu ngôn ngữ nào. Đá chúng sang
    /en/ chỉ tốn một vòng và làm gãy các lệnh kiểm tra vốn mong 200."""
    r = client.get("/login", follow_redirects=False)
    assert r.status_code == 200


def test_trinh_duyet_tieng_nhat_van_duoc_dua_sang_en(client):
    """`Accept-Language: ja-JP` VẪN là tín hiệu — client nói rõ nó không đọc
    tiếng Việt, nên đưa sang tiếng Anh chứ không để mặc ở bản tiếng Việt."""
    r = client.get("/login", headers={"Accept-Language": "ja-JP,ja;q=0.9"},
                   follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/en/login"


def test_khong_chuyen_huong_vong_lap(client):
    """Đã ở /en/ rồi thì không được chuyển hướng nữa."""
    r = client.get("/en/login", headers=US, follow_redirects=False)
    assert r.status_code == 200


def test_htmx_khong_bi_chuyen_huong(client):
    """HTMX nạp mảnh trang; chuyển hướng làm mảnh đó thành cả trang."""
    r = client.get("/login", headers={**US, "HX-Request": "true"},
                   follow_redirects=False)
    assert r.status_code != 302


# ── 4. Viết lại Location: không rơi về bản tiếng Việt giữa chừng ─────────────
def test_chuyen_huong_noi_bo_giu_nguyen_ngon_ngu(client):
    """`/nap` bắt đăng nhập → 303 về `/login`. Người đang ở bản tiếng Anh phải
    tới `/en/login`, không phải `/login` — nếu không thì mọi lần chuyển hướng sẽ
    âm thầm đổi ngôn ngữ của họ."""
    r = client.get("/en/nap", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/en/"), r.headers["location"]


def test_chuyen_huong_noi_bo_ban_tieng_viet_khong_bi_gan_tien_to(client):
    r = client.get("/nap", headers=VN, follow_redirects=False)
    assert r.status_code == 303
    assert not r.headers["location"].startswith("/en/")


# ── 5. Bộ nhớ đệm ────────────────────────────────────────────────────────────
def test_co_vary_de_cdn_khong_phuc_vu_nham_ngon_ngu(client):
    """Thiếu `Vary`, Cloudflare có thể phục vụ bản tiếng Việt cho người tiếng Anh."""
    r = client.get("/en/login", follow_redirects=False)
    vary = r.headers.get("vary", "")
    for h in ("Accept-Language", "CF-IPCountry", "Cookie"):
        assert h in vary, f"thieu {h} trong Vary: {vary!r}"
