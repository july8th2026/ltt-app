"""Golden UI C4 — họ Auth / Error / Status (17/09/2026).

Chốt các khiếm khuyết người chấm độc lập V2 ghi:

* Auth: liên kết đặt lại hỏng có tiêu đề/phụ đề theo trạng thái (không "Đặt mật
  khẩu mới … sẽ hết hạn"); placeholder đăng nhập khớp nhãn "email hoặc tên đăng
  nhập"; phụ đề không bị ép 34ch; gợi ý dưới ô ≥ 12px; khối thương hiệu một tên.
* Error: tối đa hai nút (một chính), hỗ trợ là liên kết; mã tra cứu một hàng
  không ngắt giữa chuỗi, có nút chép; 403/404 có biểu tượng riêng; nhãn "Mã tra
  cứu" dùng chữ phụ đạt AA; header "Đăng ký" lùi về nút phụ khi thẻ đã mời đăng
  nhập (một điểm nhấn đỏ).
* Status: API rỗng vẫn có khối tổng thể trung tính, lời văn "dịch vụ"; đoạn giải
  thích thành thẻ có tiêu đề; admin: nút "Kiểm tra lại" trong tiêu đề trang, nhãn
  Nexus trung tính, hồ sơ môi trường có nhãn Việt.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
TPL = GOC / "server" / "templates"
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
MOC = "/* === C4: AUTH-ERROR-STATUS === */"


def _doc(ten: str) -> str:
    return (TPL / ten).read_text(encoding="utf-8")


def _khoi_css() -> str:
    assert CSS.count(MOC) == 1
    return CSS.split(MOC, 1)[1].split("/* === ", 1)[0]


def _request(path: str = "/jobs/abc", session: dict | None = None):
    from starlette.requests import Request

    scope = {"type": "http", "method": "GET", "path": path,
             "raw_path": path.encode(), "query_string": b"", "headers": [],
             "scheme": "https", "server": ("testserver", 443),
             "client": ("127.0.0.1", 1), "root_path": "",
             "session": {} if session is None else session}
    return Request(scope)


def _render(ten: str, request=None, **ctx) -> str:
    from server.templating import templates

    return templates.get_template(ten).render(request=request or _request(), **ctx)


def _main(html: str) -> str:
    return html.split("<main", 1)[-1].split("</main>", 1)[0]


def _h1(html: str) -> str:
    m = re.search(r"<h1>(.*?)</h1>", html, re.S)
    assert m
    return m.group(1).strip()


# ── Auth ─────────────────────────────────────────────────────────────────────

def test_reset_het_han_tieu_de_theo_trang_thai():
    html = _render("reset_password.html", hop_le=False, error="")
    assert _h1(html) == "Liên kết không còn hiệu lực"
    assert "Đặt mật khẩu mới" not in html
    assert "sẽ hết hạn" not in html
    assert "<title>Liên kết không còn hiệu lực" in html


def test_reset_hop_le_giu_tieu_de_dat_mat_khau():
    html = _render("reset_password.html", hop_le=True, token="t", csrf_token="c", error="")
    assert _h1(html) == "Đặt mật khẩu mới"
    assert "sẽ hết hạn" in html


def test_login_placeholder_khop_nhan():
    html = _render("login.html", csrf_token="c", error="", next="")
    assert "Email hoặc tên đăng nhập</label>" in html
    assert 'placeholder="Nhập email hoặc tên đăng nhập"' in html
    assert "Nhập email của bạn" not in html


def test_khoi_thuong_hieu_auth_mot_ten():
    for ten, ctx in (("login.html", {"csrf_token": "c", "error": "", "next": ""}),
                     ("verify_result.html", {"ok": True}),
                     ("reset_password.html", {"hop_le": False, "error": ""})):
        html = _render(ten, **ctx)
        brand = html.split('<div class="auth-brand">', 1)[1].split("</div>", 1)[0]
        assert "LTT Studios" not in brand, ten
        assert brand.count("LTT AI Studio") == 1, ten  # chỉ eyebrow


def test_auth_goi_y_du_co_va_phu_de_khong_ep_hep():
    plain = _doc("base_plain.html")
    assert "font-size:11px" not in plain.split(".auth-field small{", 1)[1].split("}", 1)[0]
    assert ".auth-field small{color:var(--text-muted);font-size:var(--fs-helper)" in plain
    assert ".box .auth-brand p{max-width:none;text-wrap:pretty}" in _khoi_css()


# ── Error ────────────────────────────────────────────────────────────────────

def _loi(code: int, an_danh: bool = True, cid: str = "7f1de8ba-034c-4923-97cf-8e9688decd82") -> str:
    req = _request() if an_danh else _request(session={"sid": "x"})
    return _main(_render("error.html", request=req, code=code,
                         message="Không tìm thấy trang bạn yêu cầu.", correlation_id=cid))


@pytest.mark.parametrize("code,an_danh", [(404, True), (403, True), (404, False), (403, False), (500, False)])
def test_loi_toi_da_hai_nut_mot_nut_chinh(code, an_danh):
    html = _loi(code, an_danh)
    hanh_dong = html.split('<div class="ui-state-actions">', 1)[1].split("</div>", 1)[0]
    nut = re.findall(r'class="btn( [^"]*)?"', hanh_dong)
    assert 1 <= len(nut) <= 2
    assert sum(1 for n in nut if "ghost" not in (n or "")) == 1
    assert "Liên hệ hỗ trợ" not in hanh_dong
    assert re.search(r'<p class="loi-ho-tro">[^<]*<a href="[^"]+" rel="noopener">Liên hệ hỗ trợ</a>', html)


def test_loi_ma_tra_cuu_khoi_rieng_co_nut_chep():
    html = _loi(404)
    assert '<p class="loi-ma-nhan">Mã tra cứu</p>' in html
    assert 'title="7f1de8ba-034c-4923-97cf-8e9688decd82"' in html
    assert re.search(r'<button type="button" class="btn ghost loi-ma-chep" data-chep="7f1de8ba[^"]+"[^>]* hidden>', html)
    khoi = _khoi_css()
    ma = khoi.split(".loi-ma .ui-state-id{", 1)[1].split("}", 1)[0]
    assert "white-space:nowrap" in ma and "overflow-wrap:normal" in ma
    assert ".loi-ma-nhan{margin:0;color:var(--text-secondary)" in khoi


def test_loi_403_404_co_bieu_tuong_rieng():
    from server.templating import templates

    ic = templates.get_template("_icon.html").module
    h404, h403 = _loi(404), _loi(403)
    assert str(ic.icon("search")) in h404 and str(ic.icon("shield")) not in h404
    assert str(ic.icon("shield")) in h403 and str(ic.icon("search")) not in h403
    assert "loi-ma-404" in h404 and "loi-ma-403" in h403


def test_loi_an_danh_header_dang_ky_lui_ve_nut_phu():
    assert "loi-moi-dang-nhap" in _loi(404, an_danh=True)
    assert "loi-moi-dang-nhap" not in _loi(404, an_danh=False)
    assert 'body:has(.loi-moi-dang-nhap) .hdr-right a.btn[href="/register"]{background:var(--panel2)' in _khoi_css()


# ── Status API ───────────────────────────────────────────────────────────────

def _bao_cao_rong() -> dict:
    return {"checked_at": datetime(2026, 9, 17, 10, 45, tzinfo=timezone.utc),
            "overall": "operational", "overall_wording": "Hoạt động bình thường.",
            "capabilities": []}


def test_status_api_rong_co_khoi_tong_the_trung_tinh_loi_van_khach():
    html = _main(_render("status_api.html", request=_request("/status/api"), report=_bao_cao_rong()))
    assert "tt-api-tong tt-api-grey tt-api-rong" in html
    assert "Tổng thể" in html and "Chưa mở</span>" in html
    assert "năng lực" not in html.lower()
    assert "NĂNG LỰC" not in html
    assert "Hoạt động bình thường." not in html


def test_status_api_giai_thich_trong_the_co_tieu_de():
    html = _main(_render("status_api.html", request=_request("/status/api"), report=_bao_cao_rong()))
    assert '<section class="ui-card tt-api-ve" aria-labelledby="tt-api-ve">' in html
    assert '<h2 id="tt-api-ve">Về trang này</h2>' in html
    ds = html.split('<ul class="tt-api-ve-ds">', 1)[1].split("</ul>", 1)[0]
    assert ds.count("<li>") == 3
    assert '<a href="/developers/logs">Nhật ký request</a>' in ds  # liên kết thật, không bị escape
    assert "(correlation id)" in ds
    assert 'class="muted u-mt18"' not in html


# ── Status admin ─────────────────────────────────────────────────────────────

def _status_admin(profile: str = "development") -> str:
    muc = {"check": "Môi trường", "status": "ok",
           "detail": f"profile={profile}\ndata=C:\\d\nlogs=C:\\l", "fix": ""}
    nexus = {"gia_thang": 0, "loi": None, "may": 0, "online": 0, "phien": 0,
             "thu_hoi": 0, "chua_tra": 0}
    return _main(_render("status.html", request=_request("/status"), sections=[muc],
                         blockers=[], checked_sheet=False, nexus=nexus))


def test_status_admin_nut_kiem_tra_lai_trong_tieu_de_trang():
    html = _status_admin()
    dau = html.split('<div class="pagehead">', 1)[1].split('<div class="alert', 1)[0]
    assert '<form method="get" action="/status" class="status-recheck">' in dau
    assert '<button class="btn ghost" type="submit">Kiểm tra lại</button>' in dau
    assert html.count('action="/status"') == 1
    assert ".pagehead .status-recheck{margin-top:0}" in _khoi_css()


def test_status_admin_nexus_nhan_trung_tinh():
    html = _status_admin()
    assert re.search(r'<span class="badge b-grey status-trung-tinh">.*?Chưa có máy nào ghép</span>', html)
    assert ".badge.status-trung-tinh{" in _khoi_css()


@pytest.mark.parametrize("goc,nhan", [("development", "Phát triển"), ("production", "Chính thức")])
def test_status_admin_ho_so_co_nhan_viet_kem_gia_tri(goc, nhan):
    html = _status_admin(goc)
    assert f'<span class="status-kv-nhan">{nhan}</span> <code>{goc}</code>' in html


def test_status_admin_ho_so_la_giu_nguyen():
    assert '<dd><code>lab-x</code></dd>' in _status_admin("lab-x")


def test_khoi_css_c4_chi_dung_token():
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", _khoi_css())
