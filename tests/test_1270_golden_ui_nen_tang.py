"""Golden UI — chốt nền tảng thị giác (chiến dịch 16/09/2026, `plan_trien_khai.md`).

Ba nhóm chốt:

1. **Token đạt AA bằng PHÉP TÍNH**, không bằng mắt: chữ trắng trên nền đỏ có
   chữ (`--brand-fill`) và `--text-muted` trên mọi nền bề mặt/soft. Baseline
   312 lỗi tương phản — ~144 trong số đó là đúng một cặp `#fff` / `#ef3731`.
2. **Decision Locks**: DL-002 (một bảng màu ấm — không override nền trung tính,
   không cyan/teal riêng) và DL-003 (một biến `--font` cho mọi shell).
3. **Trang lỗi theo mã** (P0-02): mỗi mã có tiêu đề + đường phục hồi riêng.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")


def _root_tokens() -> dict[str, str]:
    """Token khai bằng hex trong khối `:root` ĐẦU TIÊN (khối nguồn)."""
    khoi = re.search(r":root\{(.*?)\n\}", CSS, flags=re.S).group(1)
    return dict(re.findall(r"--([a-z0-9-]+):(#[0-9a-fA-F]{6})\b", khoi))


def _do_sang(hex_: str) -> float:
    kenh = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    kenh = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in kenh]
    return 0.2126 * kenh[0] + 0.7152 * kenh[1] + 0.0722 * kenh[2]


def _ti_le(a: str, b: str) -> float:
    la, lb = sorted((_do_sang(a), _do_sang(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


T = _root_tokens()


# ── 1. Tương phản ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nen", ["brand-fill", "brand-fill-hover"])
def test_chu_trang_tren_nen_do_co_chu_dat_AA(nen):
    assert _ti_le("#ffffff", T[nen]) >= 4.5, (
        f"--{nen} {T[nen]} chỉ {_ti_le('#ffffff', T[nen]):.2f}:1 với chữ trắng")


@pytest.mark.parametrize("nen", [
    "surface-canvas", "surface-base", "surface-raised", "surface-overlay",
    "surface-interactive", "brand-soft", "status-success-soft",
    "status-warning-soft", "status-danger-soft", "status-info-soft",
])
def test_chu_mo_dat_AA_tren_moi_nen(nen):
    assert _ti_le(T["text-muted"], T[nen]) >= 4.5, (
        f"--text-muted {T['text-muted']} trên --{nen} {T[nen]} = "
        f"{_ti_le(T['text-muted'], T[nen]):.2f}:1")


def test_nut_chinh_dung_nen_fill_va_hover_khong_lam_sang():
    khoi_btn = re.search(r"\n\.btn\{[^}]*\}", CSS).group(0)
    assert "background:var(--brand-fill)" in khoi_btn
    assert ".btn:hover{background:var(--brand-fill-hover)}" in CSS
    # `brightness(1.1)` làm nền đỏ SÁNG hơn ⇒ chữ trắng tụt dưới AA lúc rê chuột.
    assert ".btn:hover{filter:brightness" not in CSS
    kieu_chung = (GOC / "server" / "templates" / "_kieu_chung.html").read_text(encoding="utf-8")
    assert "background:var(--brand-fill); color:#fff" in kieu_chung


# ── 2. Decision Locks ────────────────────────────────────────────────────────

def test_DL002_khu_api_khong_con_override_nen_trung_tinh():
    # Bỏ chú thích: lịch sử màu cũ được phép KỂ trong chú thích, không được DÙNG.
    luat = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S).lower()
    assert not re.search(r"\.khu-dev\{\s*--surface-", luat)
    for mau_cu in ("#2bb8c9", "#0b7285", "#0d0d0f", "#141416"):
        assert mau_cu not in luat, f"màu khu riêng còn sót: {mau_cu}"


def test_DL002_moi_token_teal_duoc_tham_chieu_deu_co_dinh_nghia():
    dung = set(re.findall(r"var\(--(vps-teal[a-z-]*)\)", CSS))
    khai = set(re.findall(r"--(vps-teal[a-z-]*):", CSS))
    assert dung <= khai, f"tham chiếu mà không định nghĩa: {sorted(dung - khai)}"


def test_DL003_mot_ho_chu_cho_moi_shell():
    assert re.search(r'--font:"Segoe UI",-apple-system', CSS)
    for ten in ("base.html", "base_public.html", "base_plain.html"):
        html = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        assert "font-family: system-ui" not in html, ten
        assert "var(--font)" in html, ten


# ── 3. Trang lỗi theo mã ─────────────────────────────────────────────────────

def _render_loi(code: int, message: str = "thông điệp backend") -> str:
    from starlette.requests import Request

    from server.templating import templates

    scope = {"type": "http", "method": "GET", "path": "/jobs/abc",
             "raw_path": b"/jobs/abc", "query_string": b"", "headers": [],
             "scheme": "https", "server": ("testserver", 443),
             "client": ("127.0.0.1", 1), "root_path": "", "session": {}}
    req = Request(scope)
    return templates.get_template("error.html").render(
        request=req, code=code, message=message, correlation_id="cid-123")


@pytest.mark.parametrize("code,tieu_de,phai_co", [
    (401, "Cần đăng nhập", "/login?next=/jobs/abc"),
    (403, "Chưa có quyền truy cập", "Liên hệ hỗ trợ"),
    (404, "Không tìm thấy trang", "Về trang chính"),
    (429, "Thao tác quá nhanh", 'href="/jobs/abc">Thử lại'),
    (500, "Máy chủ gặp sự cố", 'href="/jobs/abc">Thử lại'),
    (503, "Dịch vụ đang bảo trì hoặc quá tải", "Liên hệ hỗ trợ"),
])
def test_trang_loi_co_tieu_de_va_duong_phuc_hoi_theo_ma(code, tieu_de, phai_co):
    html = _render_loi(code)
    assert f'<h1 id="loi-tieu-de" class="ui-state-title">{tieu_de}</h1>' in html
    assert phai_co in html
    # Thông điệp của backend vẫn hiện nguyên — template chỉ THÊM, không thay.
    assert "thông điệp backend" in html
    assert "cid-123" in html and "Mã tra cứu" in html
    assert 'style="' not in html.split("<main", 1)[-1].split("</main>", 1)[0]


def test_ma_la_van_co_trang_loi_mac_dinh():
    html = _render_loi(418)
    assert "Đã có lỗi xảy ra" in html and "Về trang chính" in html


# ── 4. Macro trạng thái dùng chung (`_ui.html`) ─────────────────────────────

def _macro(ten: str, *args):
    from server.templating import templates
    ui = templates.env.get_template("_ui.html").module
    return str(getattr(ui, ten)(*args))


@pytest.mark.parametrize("status,mau,chu", [
    ("queued", "b-warn", "Đang chờ"), ("running", "b-warn", "Đang chạy"),
    ("done", "b-ok", "Hoàn tất"), ("error", "b-err", "Lỗi"),
    ("cancelled", "b-grey", "Đã hủy"),
])
def test_nhan_trang_thai_job_khong_lo_enum(status, mau, chu):
    html = _macro("nhan_trang_thai", status)
    assert f'class="badge {mau}"' in html and chu in html
    assert f">{status}<" not in html


@pytest.mark.parametrize("status,mau,chu", [
    ("pending", "b-warn", "Đang chờ thanh toán"), ("paid", "b-ok", "Đã thanh toán"),
    ("expired", "b-grey", "Hết hạn"), ("cancelled", "b-grey", "Đã hủy"),
    ("failed", "b-err", "Thanh toán lỗi"),
])
def test_nhan_trang_thai_don_nap(status, mau, chu):
    html = _macro("nhan_trang_thai", status, "don")
    assert f'class="badge {mau}"' in html and chu in html


def test_trang_thai_la_hien_ra_chu_khong_bi_giau():
    assert "trang_thai_moi" in _macro("nhan_trang_thai", "trang_thai_moi")


def test_thanh_tien_do_co_ten_va_kep_bien():
    html = _macro("thanh_tien_do", 140, "Tiến độ việc")
    assert 'role="progressbar"' in html and 'aria-label="Tiến độ việc"' in html
    assert 'aria-valuenow="100"' in html
    assert 'aria-valuenow="0"' in _macro("thanh_tien_do", None, "x")


def test_man_viec_khong_in_slug_va_job_type_cho_khach():
    for ten in ("jobs.html", "job_detail.html"):
        html = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        assert "j.job_type" not in html and "job.job_type" not in html, ten
        assert "ten_app(" in html, ten
    for ten in ("jobs.html", "_job_progress.html"):
        html = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        assert "ui.nhan_trang_thai(" in html, ten
