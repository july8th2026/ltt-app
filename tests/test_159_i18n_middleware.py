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


# ── 6. Lời gọi dữ liệu trong trang KHÔNG phải điều hướng ─────────────────────
#
# Chuyển hướng 302 sinh ra để **thanh địa chỉ khớp nội dung** (xem docstring của
# middleware). `fetch()` trong trang không có thanh địa chỉ: chuyển hướng nó chỉ
# tốn thêm một chặng. Vòng poll của Canvas v3 gọi 1,5 giây một lần ⇒ 302 ở đây
# là nhân đôi tải của cả tính năng.
#
# Tiêu chí phân biệt KHÔNG được là tiền tố đường dẫn: có 136 route `/api/` nằm
# dưới `route_prefix` của các app (`/agent/api/…`, `/chatltt/api/…`, …) và app
# sau sẽ lại dính. Dùng Fetch Metadata (`Sec-Fetch-Mode`) — chính trình duyệt
# khai đây có phải điều hướng hay không — và lùi về `Accept` cho client cũ.

# Trình duyệt mở cả trang: Fetch Metadata khai `navigate`, Accept xin HTML.
DIEU_HUONG = {
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Dest": "document",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
# CÙNG trình duyệt đó, nhưng là `fetch()` trong trang.
GOI_DU_LIEU = {"Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty", "Accept": "*/*"}


@pytest.fixture()
def client_hep():
    """App tối giản chỉ gắn `I18nMiddleware`.

    Đo đúng hành vi của middleware và KHÔNG phụ thuộc route của app nào — nhờ vậy
    khẳng định được "200 thẳng, thân trả về đúng", thay vì chỉ "không phải 302"
    (một route bị xoá cũng cho `!= 302`, nên phép đo ấy một mình là rỗng).
    """
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.testclient import TestClient

    from server.i18n_middleware import I18nMiddleware

    app = FastAPI()

    @app.get("/thu/api/v3/runs/{ma}")
    def _api(ma: str):
        return JSONResponse({"ma": ma})

    @app.get("/thu/trang")
    def _trang():
        return HTMLResponse("<p>trang</p>")

    app.add_middleware(I18nMiddleware)
    return TestClient(app, base_url="https://testserver")


def test_fetch_trong_trang_tra_200_thang_khong_qua_302(client_hep):
    """Phép đo chính: MỘT chặng, có thân JSON đúng — không phải 302 rồi 200."""
    r = client_hep.get("/thu/api/v3/runs/abc", headers={**US, **GOI_DU_LIEU},
                       follow_redirects=False)
    assert r.status_code == 200, f"302 = nhan doi tai vong poll: {r.headers.get('location')!r}"
    assert "location" not in r.headers
    assert r.json() == {"ma": "abc"}


def test_client_chi_nhan_json_khong_bi_chuyen_huong(client_hep):
    """Client máy-gọi-máy (SDK, worker) không gửi Fetch Metadata nhưng nói rõ nó
    chỉ nhận JSON — cũng không có thanh địa chỉ để mà khớp."""
    r = client_hep.get("/thu/api/v3/runs/abc",
                       headers={**US, "Accept": "application/json"},
                       follow_redirects=False)
    assert r.status_code == 200, r.headers.get("location")


# ── 6b. VẾ ĐỐI CHỨNG: hành vi CŨ phải còn nguyên ─────────────────────────────
# Đây là middleware của CẢ trang web. Một bản vá quá tay tắt i18n cho mọi người
# mà bộ test vẫn xanh, nếu không có những phép kiểm dưới đây.

def test_doi_chung_dieu_huong_html_van_duoc_chuyen_huong(client_hep):
    r = client_hep.get("/thu/trang", headers={**US, **DIEU_HUONG},
                       follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/en/thu/trang"


def test_doi_chung_trinh_duyet_cu_khong_co_fetch_metadata_van_chuyen_huong(client_hep):
    """Safari < 16.4 không gửi `Sec-Fetch-*`. Chỉ còn `Accept` để mà xét."""
    r = client_hep.get("/thu/trang",
                       headers={**US, "Accept": "text/html,*/*;q=0.8"},
                       follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/en/thu/trang"


def test_doi_chung_client_khong_khai_gi_giu_nguyen_hanh_vi_cu(client_hep):
    """`Accept: */*` và không có Fetch Metadata = KHÔNG có bằng chứng. Không có
    bằng chứng thì giữ hành vi cũ — thu hẹp chuyển hướng chỉ ở nơi client đã nói
    rõ, để bản vá này không lặng lẽ tắt i18n cho một loại client chưa nghĩ tới."""
    r = client_hep.get("/thu/trang", headers={**US, "Accept": "*/*"},
                       follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/en/thu/trang"


def test_doi_chung_tien_to_en_tren_duong_api_van_chay(client_hep):
    """`/en/...` không được thành 404 — đó là cái giá của cách vá bằng `MIEN_TRU`."""
    r = client_hep.get("/en/thu/api/v3/runs/abc", headers=GOI_DU_LIEU,
                       follow_redirects=False)
    assert r.status_code == 200
    assert r.json() == {"ma": "abc"}


def test_doi_chung_tien_to_en_tren_trang_van_chay(client_hep):
    r = client_hep.get("/en/thu/trang", headers={**US, **DIEU_HUONG},
                       follow_redirects=False)
    assert r.status_code == 200


# ── 6c. Trên ỨNG DỤNG THẬT ───────────────────────────────────────────────────
def test_api_cua_app_tren_ung_dung_that_khong_bi_chuyen_huong(client):
    """`/agent/api/…` là đường thật vòng poll Canvas v3 gọi.

    Đo ĐÚNG chặng ngôn ngữ, không đo hộ lớp khác: request này chưa đăng nhập nên
    router vẫn trả 303 về `/login` — đó là lớp xác thực, chuyện khác. Cái phải
    biến mất là chặng 302 sang CHÍNH đường đó có thêm `/en`.
    """
    duong = "/agent/api/v3/runs/khong-ton-tai"
    r = client.get(duong, headers={**US, **GOI_DU_LIEU}, follow_redirects=False)
    assert r.headers.get("location", "") != "/en" + duong, "van con chang 302 ngon ngu"
    assert r.status_code != 302, r.headers.get("location")


def test_doi_chung_trang_that_van_duoc_chuyen_huong(client):
    r = client.get("/login", headers={**US, **DIEU_HUONG}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/en/login"


def test_doi_chung_api_v1_van_khong_bi_dung_toi(client):
    """`/api/v1/…` đã nằm trong `MIEN_TRU` từ trước — phải y như cũ."""
    r = client.get("/api/v1/me", headers={**US, **GOI_DU_LIEU},
                   follow_redirects=False)
    assert not (300 <= r.status_code < 400), r.headers.get("location")
