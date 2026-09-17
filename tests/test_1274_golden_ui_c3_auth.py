"""Golden UI C3 — họ Auth / Error / Status (17/09/2026).

Chốt các khiếm khuyết người chấm độc lập ghi ở vòng v5:

* Auth: form đặt mật khẩu mới có gợi ý quy tắc + đường về đăng nhập; hành động
  phục hồi (liên kết hết hạn, xác thực hỏng/thành công) là NÚT; footer trong hộp
  auth căn giữa và đủ vùng chạm 44px ở màn hẹp; phụ đề cân dòng.
* Error: 404/403 cho người CHƯA đăng nhập có nút đăng nhập kèm `next`; 404 có
  hai lối (trang chính + hỗ trợ); câu dẫn 404 không lặp tiêu đề; 4xx dùng
  `ui-state--warn` như 404 đơn nạp (không còn biến thể `neutral` không tồn tại).
* Status: API không có năng lực ⇒ trạng thái rỗng, không "Hoạt động bình
  thường"; giờ dd/mm/yyyy HH:MM, không ISO/UTC; khung `.page` chung; mục môi
  trường thành danh sách có nhãn; Nexus có nhãn trạng thái bằng chữ.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
TPL = GOC / "server" / "templates"
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
MOC = "/* === C3: AUTH-ERROR-STATUS === */"


def _doc(ten: str) -> str:
    return (TPL / ten).read_text(encoding="utf-8")


def _khoi_css() -> str:
    assert CSS.count(MOC) == 1
    khoi = CSS.split(MOC, 1)[1]
    return khoi.split("/* === ", 1)[0]


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

    return templates.get_template(ten).render(
        request=request or _request(), **ctx)


def _main(html: str) -> str:
    return html.split("<main", 1)[-1].split("</main>", 1)[0]


# ── Auth ─────────────────────────────────────────────────────────────────────

def test_reset_hop_le_co_goi_y_quy_tac_va_duong_ve_dang_nhap():
    html = _render("reset_password.html", hop_le=True, token="t", csrf_token="c",
                   error="")
    assert 'aria-describedby="reset-password-goi-y"' in html
    assert 'id="reset-password-goi-y"' in html and "ít nhất 8 ký tự" in html
    assert 'href="/login"' in html
    # Hợp đồng form giữ nguyên.
    for chuoi in ('action="/reset-password"', 'name="password"', 'name="token"',
                  'name="csrf_token"'):
        assert chuoi in html


def test_reset_het_han_hanh_dong_phuc_hoi_la_nut():
    html = _render("reset_password.html", hop_le=False, error="")
    assert re.search(r'<a class="btn auth-action" href="/forgot-password">', html)
    assert 'href="/login"' in html


@pytest.mark.parametrize("ok,dich", [(True, "/login"), (False, "/register")])
def test_verify_hanh_dong_chinh_la_nut(ok, dich):
    html = _render("verify_result.html", ok=ok)
    assert f'<a class="btn auth-action" href="{dich}">' in html
    if not ok:
        assert 'href="/login"' in html  # đường phụ cho người đã xác thực trước


def test_css_auth_footer_can_giua_va_du_vung_cham():
    khoi = _khoi_css()
    assert ".box .auth-brand h1,.box .auth-brand p{text-wrap:balance}" in khoi
    assert re.search(r"\.box>\.platform-footer\{align-items:center", khoi)
    assert ".box>.platform-footer a{min-height:44px" in khoi
    assert ".box .card .auth-action{display:flex;width:100%;min-height:44px" in khoi


# ── Error ────────────────────────────────────────────────────────────────────

def test_404_an_danh_co_nut_dang_nhap_kem_next_va_ho_tro():
    html = _main(_render("error.html", code=404,
                         message="Không tìm thấy trang bạn yêu cầu.",
                         correlation_id="cid"))
    assert 'href="/login?next=/jobs/abc">Đăng nhập' in html
    assert "Về trang chính" in html and "Liên hệ hỗ trợ" in html
    # Câu dẫn chung lặp tiêu đề đã được thay bằng câu có ích.
    assert "Không tìm thấy trang bạn yêu cầu." not in html
    assert "Đường dẫn có thể đã gõ sai" in html
    assert "ui-state--warn" in html


def test_404_da_dang_nhap_khong_moi_dang_nhap_nhung_co_hai_loi():
    req = _request(session={"sid": "x"})
    html = _main(_render("error.html", request=req, code=404,
                         message="Không tìm thấy trang bạn yêu cầu.",
                         correlation_id="cid"))
    assert "/login?next=" not in html
    assert html.count('class="btn') >= 2
    assert "Về trang chính" in html and "Liên hệ hỗ trợ" in html


def test_404_thong_diep_cu_the_van_hien_nguyen():
    html = _render("error.html", code=404, message="Không tìm thấy job này.",
                   correlation_id="")
    assert "Không tìm thấy job này." in html


def test_khong_con_bien_the_ui_state_neutral():
    assert "'neutral'" not in _doc("error.html")
    for code in (400, 404, 405, 413):
        html = _render("error.html", code=code, message="m", correlation_id="")
        assert "ui-state--warn" in html, code
    assert "ui-state--err" in _render("error.html", code=500, message="m",
                                      correlation_id="")


# ── Status API ───────────────────────────────────────────────────────────────

@dataclass
class _Dong:
    capability: str = "Tạo ảnh"
    tools: tuple = ("anh.tao",)
    state: str = "degraded"
    wording: str = "Đang trục trặc."
    note: str = "Bảo trì"
    since: datetime | None = field(
        default_factory=lambda: datetime(2026, 9, 17, 3, 5, tzinfo=timezone.utc))


def _bao_cao(dong: list) -> dict:
    return {"checked_at": datetime(2026, 9, 17, 10, 45, tzinfo=timezone.utc),
            "overall": "degraded" if dong else "operational",
            "overall_wording": "Đang trục trặc." if dong else "Hoạt động bình thường.",
            "capabilities": dong}


def test_status_api_rong_khong_bao_hoat_dong_binh_thuong():
    html = _main(_render("status_api.html", request=_request("/status/api"),
                         report=_bao_cao([])))
    assert "Hoạt động bình thường." not in html
    assert "ui-state ui-state--inline" in html
    assert "Chưa mở năng lực nào ra API công khai." in html
    assert "<table" not in html


def test_status_api_co_nang_luc_bang_co_nhan_va_gio_dia_phuong():
    html = _main(_render("status_api.html", request=_request("/status/api"),
                         report=_bao_cao([_Dong()])))
    assert "Đang trục trặc." in html
    assert html.count('data-nhan="') == 3
    assert "UTC" not in html
    assert not re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", html)
    assert len(re.findall(r'data-gio-dia-phuong>\d{2}/\d{2}/\d{4} \d{2}:\d{2}</time>',
                          html)) == 2


def test_css_status_api_dung_khung_page_va_bang_xep_doc():
    khoi = _khoi_css()
    assert ".tt-api{max-width:none;margin:0;padding:0}" in khoi
    assert ".tt-api-bang tbody td::before{content:attr(data-nhan)" in khoi


# ── Status admin ─────────────────────────────────────────────────────────────

def test_status_admin_moi_truong_la_danh_sach_co_nhan_va_nhan_chu():
    muc = {"check": "Môi trường", "status": "ok",
           "detail": "profile=production\ndata=C:\\d\nlogs=C:\\l", "fix": ""}
    nexus = {"gia_thang": 0, "loi": None, "may": 0, "online": 0, "phien": 0,
             "thu_hoi": 0, "chua_tra": 0}
    html = _main(_render("status.html", request=_request("/status"),
                         sections=[muc], blockers=[], checked_sheet=False,
                         nexus=nexus))
    assert '<dl class="status-kv">' in html and "<pre" not in html
    for nhan in ("Hồ sơ môi trường", "Thư mục dữ liệu", "Thư mục nhật ký"):
        assert f"<dt>{nhan}</dt>" in html
    assert "profile=" not in html and "✓" not in html
    assert "Đạt</span>" in html
    assert "Chưa có máy nào ghép" in html
    # Ô "Google Sheet" chết (route bỏ `check_sheet` từ 25/08) không còn.
    assert 'name="check_sheet"' not in html


def test_status_admin_chi_tiet_khong_dang_khoa_gia_tri_giu_pre():
    muc = {"check": "X", "status": "blocker", "detail": "lỗi tự do", "fix": "sửa"}
    html = _main(_render("status.html", request=_request("/status"),
                         sections=[muc], blockers=[muc], checked_sheet=False,
                         nexus=None))
    assert "<pre" in html and "lỗi tự do" in html and "Lỗi chặn" in html


def test_khoi_css_c3_chi_dung_token():
    khoi = _khoi_css()
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", khoi)
