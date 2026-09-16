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


# ── 5. Billing: số kiểu Việt, hợp đồng thanh toán giữ nguyên ─────────────────

BILLING = ("nap.html", "nap_don.html", "_nap_trangthai.html", "nap_khong_thay.html")


@pytest.mark.parametrize("ten", BILLING)
def test_billing_khong_dinh_dang_so_kieu_anh(ten):
    html = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
    # `'{:,}'.format(x)` in `200,000đ` giữa giao diện tiếng Việt (P1-08).
    assert "'{:,}'" not in html and '"{:,}"' not in html
    assert 'style="' not in html, "inline style đã gom về lớp billing-*"


def test_billing_giu_nguyen_form_va_hx_cua_thanh_toan():
    nap = (GOC / "server" / "templates" / "nap.html").read_text(encoding="utf-8")
    assert '<form method="post" action="/nap/tao">' in nap
    assert 'name="csrf_token"' in nap and 'name="package_id" value="{{ g.id }}"' in nap
    don = (GOC / "server" / "templates" / "nap_don.html").read_text(encoding="utf-8")
    assert 'hx-get="/nap/don/{{ order.id }}/trangthai{% if vua_ve %}?ve=1{% endif %}"' in don
    assert 'hx-trigger="load" hx-swap="outerHTML"' in don and 'rel="noopener"' in don
    tt = (GOC / "server" / "templates" / "_nap_trangthai.html").read_text(encoding="utf-8")
    assert tt.count('<div id="tt"') == 3 and 'hx-trigger="every 4s"' in tt


def test_tablewrap_dinh_vi_de_sr_only_khong_keo_rong_trang():
    assert re.search(r"\n\.tablewrap\{position:relative;", CSS)


# ── 6. Auth: chuỗi qua _(), link giữ ngôn ngữ, nút đạt AA ────────────────────

AUTH = ("login.html", "register.html", "register_sent.html", "forgot_password.html",
        "reset_password.html", "verify_result.html")


@pytest.mark.parametrize("ten", AUTH)
def test_auth_tieu_de_va_link_theo_ngon_ngu(ten):
    html = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
    # `{% set auth_title = 'Chuỗi' %}` không qua _() ⇒ /en/login hiện tiếng Việt.
    assert not re.search(r"set auth_(title|subtitle) = '", html), ten
    assert not re.search(r"\{% block title %\}[^{]", html), ten
    # href="/login" viết thẳng ⇒ người dùng bản EN bị đưa về bản VI.
    assert not re.search(r'href="/(login|register|forgot-password)"', html), ten


def test_auth_nut_nen_phang_brand_fill():
    plain = (GOC / "server" / "templates" / "base_plain.html").read_text(encoding="utf-8")
    assert "background:var(--brand-fill);" in plain
    assert "linear-gradient(180deg,var(--accent)" not in plain
    assert "#4b1512" not in plain


def test_register_sent_van_escape_email():
    from starlette.requests import Request

    from server.templating import templates

    scope = {"type": "http", "method": "GET", "path": "/register", "raw_path": b"/register",
             "query_string": b"", "headers": [], "scheme": "https",
             "server": ("t", 443), "client": ("1", 1), "root_path": "", "session": {}}
    html = templates.get_template("register_sent.html").render(
        request=Request(scope), email="<script>x</script>@a.b")
    assert "<script>x" not in html
    assert "<strong>&lt;script&gt;x&lt;/script&gt;@a.b</strong>" in html


# ── 7. DL-001: workspace trang chủ dùng chung phần khung với top-nav ─────────

def test_DL001_trang_chu_mot_landmark_main_va_dau_thuong_hieu_chung():
    home = (GOC / "server" / "templates" / "home.html").read_text(encoding="utf-8")
    home = re.sub(r"\{#.*?#\}", "", home, flags=re.S)  # chú thích được phép KỂ về <main>
    base = (GOC / "server" / "templates" / "base.html").read_text(encoding="utf-8")
    assert "<main" in base
    # base.html đã mở <main>; một <main> nữa trong home là hai landmark (baseline axe).
    assert "<main" not in home
    # Cùng dấu `.mark` với `_header.html`, không còn "LTT STUDIOS" riêng.
    assert '<span class="mark" aria-hidden="true">LTT</span>' in home
    assert "STUDIOS" not in home
    assert "| so }}</b>" in home, "credit ở workspace định dạng như header (1.250)"
    assert 'id="market-sort" aria-label=' in home


def test_DL001_khoi_css_workspace_cu_khong_con_hex_6_chu_so():
    dong = next(d for d in CSS.split("\n") if d.startswith(".home-page{min-height:100vh"))
    assert not re.findall(r"#[0-9a-fA-F]{6}(?![0-9a-fA-F])", dong)


# ── 8. Khung cuộn tới được bằng bàn phím; nhãn form admin nối với ô nhập ─────

def _moi_template():
    for p in list((GOC / "server" / "templates").rglob("*.html")) + list(GOC.glob("apps/*/templates/*.html")):
        yield p, p.read_text(encoding="utf-8")
    yield GOC / "server" / "admin.py", (GOC / "server" / "admin.py").read_text(encoding="utf-8")


def test_moi_khung_cuon_ngang_deu_focus_duoc():
    thieu = []
    for p, s in _moi_template():
        for m in re.finditer(r'<(?:div|section|table)\s[^>]*\bclass="(?:[^"]*\s)?(?:tablewrap|dev-bang)(?:\s[^"]*)?"[^>]*>', s):
            if "tabindex" not in m.group(0):
                thieu.append(f"{p.name}: {m.group(0)[:60]}")
    assert not thieu, thieu
    js = (GOC / "server" / "static" / "sao_chep.js").read_text(encoding="utf-8")
    assert "pre.tabIndex = 0" in js


def test_nut_sao_chep_theo_ngon_ngu_trang():
    js = (GOC / "server" / "static" / "sao_chep.js").read_text(encoding="utf-8")
    assert "document.documentElement.lang" in js and '"Copy"' in js


def test_admin_form_nhan_deu_noi_voi_o_nhap():
    admin = (GOC / "server" / "admin.py").read_text(encoding="utf-8")
    tran = re.findall(r'<label>[^<]*</label>\s*<(?:input|select)\s[^>]*\bname=', admin)
    assert not tran, tran[:3]


def test_admin_cham_provider_chu_trang_dat_AA():
    admin = (GOC / "server" / "admin.py").read_text(encoding="utf-8")
    bang = admin.split("_PROVCOL = {", 1)[1].split("}", 1)[0]
    for h in re.findall(r"#[0-9a-fA-F]{6}", bang):
        assert _ti_le("#ffffff", h) >= 4.5, h


# ── 9. DL-004: sqladmin phủ Golden, hành vi form giữ nguyên ──────────────────

SQA = GOC / "server" / "admin_templates" / "sqladmin"


def test_DL004_luat_dropdown_cua_header_co_pham_vi():
    """`.dropdown button{width:100%}` không phạm vi kéo nút Actions của sqladmin rộng hết hàng."""
    luat = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    tran = re.findall(r"(?:^|[,{}\s])\.dropdown\b(?![-\w])", luat)
    co_pham_vi = len(re.findall(r"\.hdr \.dropdown\b", luat))
    assert len(tran) == co_pham_vi, "mọi `.dropdown` trong ltt.css phải nằm dưới `.hdr`"


def test_DL004_override_chi_dich_chuoi_hien_thi():
    lst = (SQA / "list.html").read_text(encoding="utf-8")
    for cu in (">Search<", "Delete selected items<", "Showing <span>", "/ Page", "\n            Actions\n"):
        assert cu not in lst, cu
    assert 'id="search-reset"' in lst and 'aria-label="{{ _("Xoá tìm kiếm") }}"' in lst
    lay = (SQA / "layout.html").read_text(encoding="utf-8")
    assert '<ul class="navbar-nav">' in lay and "display_menu(" not in lay
    # edit/create KHÔNG được override: `value` của <input name="save"> là giao thức.
    assert not (SQA / "edit.html").exists() and not (SQA / "create.html").exists()


def test_DL004_bien_tabler_tro_ve_token():
    base = (SQA / "base.html").read_text(encoding="utf-8")
    assert "--tblr-primary:var(--brand-fill)" in base
    assert "--tblr-body-font-family:var(--font)" in base
    assert "#ef3731" not in base and "#151111f2" not in base


# ── 10. i18n: nhãn hiển thị không để tiếng Anh cứng; khoá lọc giữ nguyên ─────

@pytest.mark.parametrize("khoa,chu", [
    ("audio", "Âm thanh"), ("video", "Video"), ("Utilities", "Tiện ích"),
    ("Automation", "Tự động hoá"), ("AI Video", "Video AI"), ("Chat & Prompt", "Chat & Prompt"),
])
def test_ten_the_loai_hien_thi(khoa, chu):
    assert _macro("ten_the_loai", khoa) == chu


def test_trang_chu_loc_theo_khoa_goc_nhung_hien_ten_dich():
    home = (GOC / "server" / "templates" / "home.html").read_text(encoding="utf-8")
    assert "{{ _(category) }}" not in home and "ui.ten_the_loai(category)" in home
    assert 'data-category="{{ category }}"' in home


@pytest.mark.parametrize("tep,cam", [
    ("apps/taoanh/templates/image.html", (">GENERATIVE IMAGE<", ">OUTPUT HISTORY<", "> Reference &amp; Edit<")),
    ("apps/thumbnail/templates/thumbnail.html", (">OUTPUT HISTORY<", "THUMBNAIL MODE<", "> Thumbnail trend<")),
    ("apps/taoclipngan/templates/taoclipngan.html", (">OUTPUT LIBRARY<", "SHORT-FORM WORKSPACE<")),
    ("apps/prompt_ai_ommi/templates/prompt_ai_ommi.html", (">WORKSPACE<", ">INSPECTOR<")),
])
def test_nhan_app_khong_con_tieng_anh_cung(tep, cam):
    s = (GOC / tep).read_text(encoding="utf-8")
    for c in cam:
        assert c not in s, f"{tep}: {c}"


# ── 11. DL-001: MỘT menu tài khoản cho hai khung ────────────────────────────

def test_DL001_hai_khung_dung_chung_menu_tai_khoan():
    hdr = (GOC / "server" / "templates" / "_header.html").read_text(encoding="utf-8")
    home = (GOC / "server" / "templates" / "home.html").read_text(encoding="utf-8")
    assert '{% include "_menu_tai_khoan.html" %}' in hdr
    assert '{% include "_menu_tai_khoan.html" %}' in home
    # Hai bản chép tay cũ không được sống lại ở từng khung.
    for s in (hdr, home):
        assert 'action="/logout"' not in s
    menu = (GOC / "server" / "templates" / "_menu_tai_khoan.html").read_text(encoding="utf-8")
    assert 'action="/logout"' in menu and "phien_csrf(request)" in menu
    assert "_acc.role" not in menu, "không in thẳng enum vai trò"


def test_thanh_tren_workspace_noi_tren_nhan_the():
    z_top = max(int(z) for z in re.findall(r"\.market-top\{z-index:(\d+)\}", CSS))
    z_badge = max(int(z) for z in re.findall(r"\.market-badge\{[^}]*z-index:(\d+)", CSS))
    assert z_top > z_badge
