"""
W2.4 — smoke GUI tự động bằng Playwright. Chính sách CLAUDE.md yêu cầu kiểm giao
diện thật; đây là bản TỰ ĐỘNG hoá tối thiểu để không phải kiểm tay mỗi lần.

OPT-IN (không chạy trong suite thường): tự bỏ qua nếu chưa cài `playwright`
(pip install playwright && playwright install chromium) HOẶC chưa đặt
`LTT_SMOKE_URL`. Đặt thêm `LTT_SMOKE_USER` / `LTT_SMOKE_PASS` để kiểm luôn luồng
đăng nhập.

    LTT_SMOKE_URL=https://app.lttstudios.com \
    LTT_SMOKE_USER=admin@lttstudios.com LTT_SMOKE_PASS=... \
    python -m pytest tests/test_74_smoke_playwright.py -v
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("playwright", reason="chua cai playwright (opt-in)")

SMOKE_URL = os.environ.get("LTT_SMOKE_URL", "").strip().rstrip("/")

pytestmark = pytest.mark.skipif(
    not SMOKE_URL, reason="dat LTT_SMOKE_URL de chay smoke GUI")


def test_smoke_catalog_va_dang_nhap():
    from playwright.sync_api import sync_playwright

    user = os.environ.get("LTT_SMOKE_USER", "")
    pw = os.environ.get("LTT_SMOKE_PASS", "")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            # 1) Catalog công khai hiển thị (khách chưa đăng nhập).
            page.goto(f"{SMOKE_URL}/", wait_until="domcontentloaded", timeout=20000)
            html = page.content()
            assert "Đăng nhập" in html and "Đăng ký" in html

            # 2) Trang đăng nhập mở được.
            page.goto(f"{SMOKE_URL}/login", wait_until="domcontentloaded", timeout=20000)
            assert page.query_selector('input[name="username"]') is not None

            # 3) Nếu có tài khoản smoke: đăng nhập → vào vỏ nội bộ.
            if user and pw:
                page.fill('input[name="username"]', user)
                page.fill('input[name="password"]', pw)
                page.click('button[type="submit"]')
                page.wait_for_load_state("domcontentloaded", timeout=20000)
                assert "Việc của tôi" in page.content()   # sidebar authed
        finally:
            browser.close()
