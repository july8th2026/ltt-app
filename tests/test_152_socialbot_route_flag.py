"""
test_152 - 43 route bảng điều khiển FB/TikTok cũ nằm sau một cờ (H22.10).

Bối cảnh đo được (docs/APP_AUDIT/control-plane/2026-08-06/04_BAN_DO_CORE.md):
**43/69 = 62% route công khai** của nền tảng phục vụ app socialbot đã **đóng
băng**, gắn vô điều kiện. Mỗi route là một chỗ phải xét lại mỗi lần rà bảo mật,
cho một nghiệp vụ không còn bán.

Hai điều file này chốt, và điều thứ hai quan trọng hơn:

1. Đặt `LTT_SOCIALBOT_ROUTES=0` thì 43 route đó **thực sự biến mất**.
2. **Mặc định vẫn BẬT.** Tắt sẵn nghĩa là bảng điều khiển cũ biến mất *lặng lẽ*
   với người còn đang dùng, ngay lần deploy tới. Đó là quyết định sản phẩm của
   chủ sản phẩm, không phải hệ quả phụ của một lần refactor.
"""
from __future__ import annotations

import pytest

from server.app import _socialbot_routes_enabled

# Các tiền tố thuộc bảng điều khiển cũ. Lấy từ chính router để không phải
# gõ tay 43 đường dẫn (gõ tay là sai ngay khi ai đó thêm route).
LEGACY_MODULES = ("accounts", "workers", "settings", "sheet", "manual",
                  "monitor", "oauth")


def _legacy_paths() -> set[str]:
    import importlib
    paths: set[str] = set()
    for name in LEGACY_MODULES:
        mod = importlib.import_module(f"server.routes.{name}")
        paths |= {r.path for r in mod.router.routes}
    return paths


def test_mac_dinh_van_bat(monkeypatch):
    """Nếu ai đó đổi mặc định thành TẮT, người đang dùng mất bảng điều khiển
    ngay lần deploy tới mà không được báo."""
    monkeypatch.delenv("LTT_SOCIALBOT_ROUTES", raising=False)
    assert _socialbot_routes_enabled() is True
    assert _socialbot_routes_enabled({}) is True


@pytest.mark.parametrize("gia_tri", ["0", "false", "FALSE", "no", "off", ""])
def test_cac_cach_viet_tat_deu_hieu(gia_tri):
    assert _socialbot_routes_enabled({"LTT_SOCIALBOT_ROUTES": gia_tri}) is False


@pytest.mark.parametrize("gia_tri", ["1", "true", "yes", "on", "bat-ky-gi-khac"])
def test_gia_tri_khac_thi_van_bat(gia_tri):
    """Giá trị lạ phải nghiêng về GIỮ route, không phải làm mất chúng."""
    assert _socialbot_routes_enabled({"LTT_SOCIALBOT_ROUTES": gia_tri}) is True


def _paths(app) -> set[str]:
    """Mọi đường dẫn của app, kể cả router lồng.

    `app.routes` ở bản FastAPI này KHÔNG chứa route phẳng: mỗi
    `include_router()` để lại một object `_IncludedRouter` không có `.path`,
    còn route thật nằm trong `.original_router.routes`. Đọc thẳng `r.path` vừa
    ném vừa bỏ sót gần hết.
    """
    ra: set[str] = set()

    def _di(items):
        for r in items:
            goc = getattr(r, "original_router", None)
            if goc is not None:
                _di(getattr(goc, "routes", []))
            con = getattr(r, "routes", None)
            if con and goc is None:
                _di(con)
            duong = getattr(r, "path", None)
            if duong:
                ra.add(duong)

    _di(app.routes)
    return ra


def _app(env_extra: dict) -> object:
    from server.app import create_app
    env = {"LTT_ENV": "development", "LTT_SESSION_SECRET": "x" * 32,
           "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""}
    env.update(env_extra)
    return create_app(env=env)


def test_tat_co_thi_route_legacy_bien_mat_that():
    """Không kiểm bằng lời — so tập đường dẫn thật của app hai lần."""
    legacy = _legacy_paths()
    assert len(legacy) >= 30, f"chỉ thấy {len(legacy)} route legacy — dò sai?"

    bat = _paths(_app({"LTT_SOCIALBOT_ROUTES": "1"}))
    tat = _paths(_app({"LTT_SOCIALBOT_ROUTES": "0"}))

    con_sot = legacy & tat
    assert not con_sot, f"tắt cờ rồi mà route legacy vẫn còn: {sorted(con_sot)[:8]}"
    assert legacy <= bat, "bật cờ mà thiếu route legacy"


def test_tat_co_KHONG_lam_mat_route_cua_nen_tang():
    """Cách hỏng đắt nhất: tắt nhầm cả đăng nhập/nạp tiền/health."""
    tat = _paths(_app({"LTT_SOCIALBOT_ROUTES": "0"}))
    phai_con = ["/login", "/logout", "/health/ready", "/health/live", "/nap", "/register"]
    thieu = [p for p in phai_con if p not in tat]
    assert not thieu, f"tắt cờ làm mất route của nền tảng: {thieu}"


def test_tat_co_thi_app_van_khoi_dong_va_trang_chu_song():
    """Tắt 43 route mà app không dựng được thì cờ này vô dụng."""
    from fastapi.testclient import TestClient
    app = _app({"LTT_SOCIALBOT_ROUTES": "0"})
    with TestClient(app, base_url="https://testserver") as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/login").status_code == 200
