"""Golden UI C4 — khu quản trị (`admin/_vo.html`) và nửa SQLAdmin, đợt người chấm độc lập V2.

Chốt các khiếm khuyết người chấm V2 ghi trên giao diện thật (Playwright, 17/09/2026):

Admin
* ô chọn provider "Google Gemini (da xoa) []" — không dấu, ngoặc rỗng;
* nhãn trường thô `base_url`/`supported_models`/`default_model`/`priority`;
  enum lộ "global", "trạng thái error", "payos"; byte thô 94371840;
* ngày giờ lệch "09-17 10:56" / "17/09 11:14" / "2026-09-17 10:56";
* khung admin viền đen 8px (lề mặc định của <body>); thẻ số liệu Tài chính khác kiểu;
* hai hàng pill điều hướng chồng nhau; mô tả "Đơn cần xử lý" dính sát bảng.

SQLAdmin
* "mcredit_du", "topup", tiêu đề details "id: <uuid>", số "1250";
* tiêu đề cột lúc đỏ lúc trắng, không chỉ báo sắp xếp;
* phân trang chật, "Hiện" tách xa ô cỡ trang; ô trống không "—"; ô tìm bị cắt ở 390px;
* icon Font Awesome đặc lệch icon line của vỏ tự dựng.

Đọc tệp nguồn + dựng view ở mức lớp — không dựng app, không chạm provider/CSDL thật.
⛔ `password_hash` ở details là OOS-12 (bảo mật) — test này không đụng tới.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

GOC = Path(__file__).resolve().parents[1]
TPL = GOC / "server" / "templates" / "admin"
SQA = GOC / "server" / "admin_templates" / "sqladmin"
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
ADMIN_PY = (GOC / "server" / "admin.py").read_text(encoding="utf-8")
ADMIN_API_PY = (GOC / "server" / "admin_api.py").read_text(encoding="utf-8")


def _doc(thu_muc: Path, ten: str) -> str:
    return (thu_muc / ten).read_text(encoding="utf-8")


def _khoi_c4() -> str:
    return CSS[CSS.index("/* === C4: ADMIN === */"):]


# ── Admin tự dựng ────────────────────────────────────────────────────────────

def test_o_chon_provider_co_dau_va_khong_ngoac_rong():
    assert "[{escape(p.auth_style)}]</option>' for p" not in ADMIN_PY
    assert '.replace("(da xoa)", "(đã xoá)")' in ADMIN_PY
    assert 'if p.auth_style else ""' in ADMIN_PY


def test_nhan_truong_api_key_viet_kem_ten_ky_thuat():
    for cu in (">base_url (để trống", ">supported_models (phẩy", ">default_model</label>",
               ">priority (cao", ">priority</label>", ">base_url</label>", "(phay phan cach)"):
        assert cu not in ADMIN_PY, cu
    for ten in ("base_url", "supported_models", "default_model", "priority"):
        # Hai form (thêm + sửa) đều mang tên kỹ thuật trong <code> nhỏ.
        assert ADMIN_PY.count(f'<code class="adm-ten-ky-thuat">{ten}</code>') == 2, ten
    # Giao thức form giữ nguyên.
    for name in ('name="base_url"', 'name="supported_models"', 'name="default_model"', 'name="priority"'):
        assert name in ADMIN_PY, name


def test_chinh_sach_nguon_viet_va_byte_thanh_mb():
    t = _doc(TPL, "api_chinh_sach.html")
    assert '"global": "Mặc định hệ thống"' in t
    assert 'nen.sources.get(f, "") }}</td>' not in t
    assert "1048576" in t and "' MB'" in t
    # Ô nhập vẫn nhận byte (nhãn form giữ "(byte)").
    assert '"max_upload_bytes": "Tải lên tối đa (byte)"' in t


def test_byte_hien_thanh_mb_khi_render():
    from jinja2 import Environment

    t = _doc(TPL, "api_chinh_sach.html")
    dong = re.search(r'<td class="tnum">\{% if f == "max_upload_bytes".*?</td>', t, re.S).group(0)
    env = Environment()
    ra = lambda v, f="max_upload_bytes": env.from_string(dong).render(v=v, f=f)  # noqa: E731
    assert ">90 MB<" in ra(94371840)
    assert "94.371.840 byte" in ra(94371840)
    assert ">2 GB<" in ra(2147483648)
    assert ">1.200<" in ra(1200, "rpm_read")


def test_enum_trang_thai_va_cong_thanh_toan_nhan_viet():
    assert "'Job ở trạng thái error.'" not in _doc(TPL, "tong_quan.html")
    assert 'escape(o.gateway or "-")' not in ADMIN_PY
    assert '{"payos": "PayOS"}' in ADMIN_PY
    assert '"cap_credit": "Cấp credit"' in ADMIN_PY


def test_ngay_gio_mot_dinh_dang_dd_mm_yyyy():
    for cu in (":%m-%d %H:%M}", ":%d/%m %H:%M}"):
        assert cu not in ADMIN_PY, cu
    assert '"%Y-%m-%d %H:%M"' not in ADMIN_API_PY
    for ten in ("ho_so_360.html", "tong_quan.html"):
        assert "strftime('%d/%m %H:%M')" not in _doc(TPL, ten), ten
    from server.admin_api import _when

    assert _when(datetime(2026, 9, 17, 10, 56)) == "17/09/2026 10:56"


def test_vo_admin_khong_con_le_8px():
    assert '<body class="adm-body">' in _doc(TPL, "_vo.html")
    assert "body.adm-body{margin:0}" in _khoi_c4()


def test_tab_cap_3_gach_chan_va_mo_ta_cach_bang():
    c4 = _khoi_c4()
    assert re.search(r"\.adm-chrome \.dev-sub\.adm-tab a\{[^}]*border-bottom:2px solid transparent", c4)
    assert re.search(r"\.adm-chrome \.dev-sub\.adm-tab a\.active\{[^}]*border-bottom-color:var\(--brand-fill\)", c4)
    assert ".u-tieu-muc+.adm-dan{margin:0 0 var(--space-3)}" in c4


def test_the_so_lieu_tai_chinh_cung_kieu():
    c4 = _khoi_c4()
    assert ".adm-luoi-tai-chinh .adm-so-lon{font-size:24px" in c4
    assert re.search(r"\.adm-o-so\{font-size:24px", CSS)


def test_khoi_c4_khong_them_hex():
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", _khoi_c4())


# ── SQLAdmin ─────────────────────────────────────────────────────────────────

def test_sqladmin_o_trong_gach_ngang_va_so_kieu_viet():
    from sqladmin.formatters import BASE_FORMATTERS

    import server.admin  # noqa: F401 — cài formatter lúc import

    assert BASE_FORMATTERS[type(None)](None) == "—"
    assert BASE_FORMATTERS[str]("") == "—" and BASE_FORMATTERS[str]("abc") == "abc"
    assert BASE_FORMATTERS[int](1250) == "1.250" and BASE_FORMATTERS[int](-94371840) == "-94.371.840"
    assert BASE_FORMATTERS[datetime](datetime(2026, 9, 17, 10, 44)) == "17/09/2026 10:44"
    # bool giữ icon của gói (không bị formatter int nuốt).
    assert "fa-check" in str(BASE_FORMATTERS[bool](True))


def test_sqladmin_nhan_mcredit_va_loai_but_toan():
    from server.admin import CreditEntryAdmin, UserAdmin

    assert UserAdmin.column_labels.get("mcredit_du") == "Số dư (mcredit)"
    f = CreditEntryAdmin.column_formatters["kind"]
    assert CreditEntryAdmin.column_formatters_detail["kind"] is f
    ra = str(f(SimpleNamespace(kind="topup"), "kind"))
    assert "Nạp tiền" in ra and '<span class="adm-ten-ky-thuat">topup</span>' in ra
    # Mã lạ (kind do nơi gọi truyền) chỉ hiện mã, đã escape.
    assert "&lt;x&gt;" in str(f(SimpleNamespace(kind="<x>"), "kind"))
    assert f(SimpleNamespace(kind=""), "kind") == "—"


def test_sqladmin_tieu_de_details_co_nghia():
    t = _doc(SQA, "details.html")
    assert '{{ _("Chi tiết %(ten)s", ten=model_view.name) }}' in t
    assert "{% endfor %}: {{ get_object_identifier(model) }}</h3>" not in t
    assert '<div class="table-responsive" tabindex="0">' in t


def test_sqladmin_tieu_de_cot_sap_xep_co_chi_bao():
    t = _doc(SQA, "list.html")
    assert t.count('class="ltt-sapxep') == 3
    assert "fa-solid fa-sort" in t and 'aria-sort="ascending"' in t and 'aria-sort="descending"' in t
    c4 = _khoi_c4()
    assert re.search(r"a\.ltt-sapxep\{[^}]*color:var\(--text-muted\)", c4)
    # URL sắp xếp giữ nguyên hành vi gói.
    assert "include_query_params(sortBy=name, sort='asc')" in t


def test_sqladmin_phan_trang_va_co_trang():
    t = _doc(SQA, "list.html")
    assert "ltt-phantrang" in t and "ltt-cotrang" in t
    c4 = _khoi_c4()
    assert ".pagination.ltt-phantrang{gap:4px}" in c4
    assert re.search(r"\.ltt-cotrang\{display:inline-flex;align-items:center;gap:8px", c4)
    assert re.search(r"\.col-md-4\{flex:1 1 100%", c4)


def test_sqladmin_icon_line():
    lst = _doc(SQA, "list.html")
    for cu in ("fa-solid fa-eye", "fa-solid fa-pen-to-square", "fa-solid fa-trash"):
        assert cu not in lst, cu
    lay = _doc(SQA, "layout.html")
    assert "ic.icon(_IC_SQA" in lay and 'ic.icon("log-out")' in lay
    assert "menu_item(item, request)" not in lay
    assert 'ic=__import__("server.templating").templating.templates.env.get_template("_icon.html").module' in ADMIN_PY
    assert "a.btn.ltt-huy" in _khoi_c4()


def test_sqladmin_icon_map_chi_dung_icon_co_that():
    icon = (GOC / "server" / "templates" / "_icon.html").read_text(encoding="utf-8")
    lay = _doc(SQA, "layout.html")
    ban_do = re.search(r"_IC_SQA = \{(.*?)\}", lay, re.S).group(1)
    for ten in re.findall(r':\s*"([a-z-]+)"', ban_do):
        assert f"'{ten}':" in icon, ten
