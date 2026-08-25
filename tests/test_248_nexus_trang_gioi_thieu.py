"""`/nexus` là trang GIỚI THIỆU, không còn là bảng điều khiển web-broker.

Vì sao có file này: Q101 chọn Model B (app native + relay LTT), nên luồng "mã
ghép + điều khiển trong trình duyệt" ở `apps/nexus/routes.py` đã đóng băng.
Nhưng route của nó vẫn đăng ký và vẫn là thứ hiện ra khi khách bấm **LTT Nexus**
trong menu — nghĩa là cửa hàng đang trưng bày một sản phẩm đã ngừng bán.

Ba điều được chốt ở đây:

1. `/nexus` mở được **khi chưa đăng nhập** (nó là cửa giới thiệu, không phải
   bảng điều khiển) và nội dung là giới thiệu + bảng tải, không phải mã ghép.
2. Các route web-broker cũ trả **404** khi cờ tắt — không chỉ ẩn khỏi menu, mà
   gõ thẳng URL cũng không mở.
3. Bật `LTT_NEXUS_WEB_BROKER=1` thì lấy lại được bảng cũ (không xoá lặng lẽ thứ
   có thể còn người dùng — tiền lệ `LTT_SOCIALBOT_ROUTES` của H22.10, cờ đó nay
   đã đi hết vòng: đo xong là không ai dùng, và bị xoá hẳn 2026-08-25 theo Q108).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _dung_app(tmp_path, monkeypatch, *, web_broker: str | None = None,
              nexus_bat: str = "1"):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'gt.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "gt-secret-value")
    monkeypatch.setenv("LTT_NEXUS", nexus_bat)
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    if web_broker is None:
        monkeypatch.delenv("LTT_NEXUS_WEB_BROKER", raising=False)
    else:
        monkeypatch.setenv("LTT_NEXUS_WEB_BROKER", web_broker)

    from platform_core.public_api import limits
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from server.app import create_app

    return TestClient(create_app(), base_url="https://testserver")


@pytest.fixture()
def app_mac_dinh(tmp_path, monkeypatch):
    """Cấu hình mặc định: web-broker TẮT."""
    import platform_core.db as dbmod
    from platform_core.public_api import limits

    client = _dung_app(tmp_path, monkeypatch)
    try:
        yield client
    finally:
        limits.reset()
        dbmod.reset_engine()


@pytest.fixture()
def app_broker(tmp_path, monkeypatch):
    """Cấu hình bật lại bảng điều khiển web cũ."""
    import platform_core.db as dbmod
    from platform_core.public_api import limits

    client = _dung_app(tmp_path, monkeypatch, web_broker="1")
    try:
        yield client
    finally:
        limits.reset()
        dbmod.reset_engine()


# ── /nexus mặc định là trang giới thiệu công khai ────────────────────────────

def test_nexus_mo_duoc_khi_chua_dang_nhap(app_mac_dinh):
    """Cửa giới thiệu mà đòi đăng nhập thì người chưa có tài khoản không đọc được."""
    r = app_mac_dinh.get("/nexus", follow_redirects=False)
    assert r.status_code == 200, r.text[:400]


def test_nexus_la_trang_gioi_thieu_chu_khong_phai_ma_ghep(app_mac_dinh):
    html = app_mac_dinh.get("/nexus").text
    assert "Tải ứng dụng" in html
    assert "credit" in html.lower()
    # Ngôn ngữ của luồng web-broker đã đóng băng — không được còn ở đây.
    assert "mã ghép" not in html.lower()


def test_nexus_tro_toi_trang_tai_va_may_cua_toi(app_mac_dinh):
    html = app_mac_dinh.get("/nexus").text
    assert 'href="/tai-xuong"' in html
    assert 'href="/may-cua-toi"' in html


# ── Route web-broker đóng thật, không chỉ ẩn khỏi menu ───────────────────────

@pytest.mark.parametrize("duong", [
    "/nexus/tai",
    "/nexus/nhat-ky",
    "/nexus/phien/khong-co-that",
])
def test_route_web_broker_tra_404_khi_co_tat(app_mac_dinh, duong):
    r = app_mac_dinh.get(duong, follow_redirects=False)
    assert r.status_code == 404, f"{duong} -> {r.status_code}"


def test_ma_ghep_tra_404_khi_co_tat(app_mac_dinh):
    r = app_mac_dinh.post("/nexus/ma-ghep", data={"csrf_token": "x"},
                          follow_redirects=False)
    assert r.status_code == 404


# ── Bật cờ thì lấy lại được bảng cũ ──────────────────────────────────────────

def test_bat_co_thi_nexus_doi_bat_dang_nhap_lai(app_broker):
    """Bảng điều khiển là dữ liệu riêng → phải đòi đăng nhập (303 về /login)."""
    r = app_broker.get("/nexus", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers.get("location", "")


def test_bat_co_thi_route_cu_khong_con_404(app_broker):
    r = app_broker.get("/nexus/nhat-ky", follow_redirects=False)
    assert r.status_code != 404


# ── Cờ LTT_NEXUS tắt vẫn phải giấu tất cả ────────────────────────────────────

def test_tat_nexus_thi_ca_trang_gioi_thieu_cung_404(tmp_path, monkeypatch):
    import platform_core.db as dbmod
    from platform_core.public_api import limits

    client = _dung_app(tmp_path, monkeypatch, nexus_bat="0")
    try:
        assert client.get("/nexus", follow_redirects=False).status_code == 404
    finally:
        limits.reset()
        dbmod.reset_engine()


# ── Bản tiếng Anh phải thật sự là tiếng Anh ─────────────────────────────────
#
# Trang này là cửa hàng, và nó có hai bản ngôn ngữ. Một chuỗi quên bọc `_()` hay
# quên thêm vào `.po` KHÔNG làm trang vỡ — nó chỉ hiện tiếng Việt giữa một trang
# tiếng Anh, và không ai báo lỗi. Đã dính đúng vậy hai lần: nhãn nhóm ở header
# (`{{ group }}` thay vì `{{ _(group) }}`), và nhãn iOS nằm trong DỮ LIỆU bản kê
# nên không đi qua gettext được.

def test_ban_tieng_anh_khong_ro_tieng_viet(app_mac_dinh):
    html = app_mac_dinh.get("/en/nexus", follow_redirects=True).text
    for viet in ("Tải ứng dụng", "Máy của bạn", "Câu hỏi thường gặp",
                 "Ai thấy được gì", "Chọn máy của bạn"):
        assert viet not in html, f"con tieng Viet tren ban /en: {viet!r}"


def test_ban_tieng_anh_dich_dung_cac_moc_chinh(app_mac_dinh):
    html = app_mac_dinh.get("/en/nexus", follow_redirects=True).text
    for eng in ("Your machines", "Pick your platform", "Who can see what",
                "Things people ask", "Download the app"):
        assert eng in html, f"thieu ban dich: {eng!r}"


def test_link_noi_bo_mang_tien_to_ngon_ngu(app_mac_dinh):
    """Link viết thẳng vẫn tới đúng nơi, nhưng tốn thêm một cú 302 cho mỗi cú bấm."""
    html = app_mac_dinh.get("/en/nexus", follow_redirects=True).text
    assert 'href="/en/tai-xuong"' in html
    assert 'href="/tai-xuong"' not in html


def test_co_khoi_an_toan_va_loi_moi_cuoi_trang(app_mac_dinh):
    """Hai khối này trả lời hai câu người đọc mang theo tới cuối trang.

    Khối an toàn trả lời "ai nhìn thấy màn hình tôi" — nỗi lo số một với phần mềm
    điều khiển từ xa, và bản trang đầu tiên không hề nhắc tới. Khối cuối trả lời
    "giờ tôi làm gì" — bản đầu kết thúc ở FAQ rồi hết.
    """
    html = app_mac_dinh.get("/nexus").text
    assert "Khoá riêng không rời máy" in html
    assert "Màn hình không đi qua trình duyệt" in html
    assert "Cài mất chưa tới hai phút" in html
