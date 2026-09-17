"""Golden UI C3 — khu quản trị tự dựng (`admin/_vo.html`) và nửa SQLAdmin.

Chốt những lỗi người chấm độc lập ghi trên giao diện thật (Playwright + axe,
17/09/2026, seed `tools/golden_ui_dev.py`):

* thanh bên dùng chữ viết tắt "Tổ/Kh/Tà" thay icon; mẩu bánh mì lúc có lúc không;
* bảng ở 390px chỉ còn cột đầu (các cột khác trôi ngoài khung cuộn);
* tên trường thô tiếng Anh ("Provider & Models", PROVIDER/AUTH, "← APIKEYS",
  rpm_read không nhãn Việt, `<title>` không dấu "API - Chinh sach"), emoji trên nút;
* form chính sách chỉ có placeholder, ô dính nhau, select đầu trống không nhãn;
* vai trò hiện thô `user/admin`;
* SQLAdmin: DISPLAY_NAME/IS_ACTIVE/CREATED_AT kèm micro giây, "Role" ô gõ tự do,
  "Huỷ" tách xa cụm "Lưu", đầu trang `<h2>` rỗng, thanh trên thành dải cuộn ở 390px.

Đọc tệp nguồn (và dựng view sqladmin ở mức lớp) — không dựng app, không chạm provider.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
TPL = GOC / "server" / "templates" / "admin"
SQA = GOC / "server" / "admin_templates" / "sqladmin"
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
ADMIN_PY = (GOC / "server" / "admin.py").read_text(encoding="utf-8")
ADMIN_API_PY = (GOC / "server" / "admin_api.py").read_text(encoding="utf-8")


def _doc(thu_muc: Path, ten: str) -> str:
    return (thu_muc / ten).read_text(encoding="utf-8")


def _khoi_c3() -> str:
    return CSS[CSS.index("/* === C3: ADMIN === */"):]


# ── Vỏ admin tự dựng ─────────────────────────────────────────────────────────

def test_thanh_ben_dung_icon_svg_khong_dung_chu_viet_tat():
    vo = _doc(TPL, "_vo.html")
    assert "m.nhan[:2]" not in vo
    assert '{% import "_icon.html" as ic %}' in vo
    assert re.search(r'<span class="ic" aria-hidden="true">\{\{ ic\.icon\(', vo)
    for k in ("tong_quan", "khach_hang", "tai_chinh", "api_overview", "van_hanh", "he_thong"):
        assert f'"{k}":' in vo, k


def test_banh_mi_co_o_moi_trang_tru_tong_quan():
    vo = _doc(TPL, "_vo.html")
    assert "_co_banh_mi" in vo
    assert '<a href="/admin/">Quản trị</a>' in vo


def test_bang_hep_thanh_the_nhan_gia_tri():
    vo = _doc(TPL, "_vo.html")
    assert 'setAttribute("data-nhan"' in vo and 'classList.add("adm-the")' in vo
    c3 = _khoi_c3()
    assert "@media (max-width:640px)" in c3
    assert re.search(r"table\.adm-the>thead\{display:none\}", c3)
    assert re.search(r"td\[data-nhan\]::before\{content:attr\(data-nhan\)", c3)


def test_khoi_c3_khong_them_hex():
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", _khoi_c3())


def test_trang_model_va_tai_chinh_khong_con_tieng_anh_tho_hay_emoji():
    for cu in ("<h1>Provider &amp; Models</h1>", "&larr; APIKEYS</a>",
               "<th>Provider</th><th>Auth</th><th>Category</th>", "Thêm provider/model = sửa file này",
               "📈", "🧾", "💠", "🧩", "🧭", "💬", "🖼️", "🎬", "sổ credit H3"):
        assert cu not in ADMIN_PY, cu


def test_title_api_co_dau():
    for cu in ("Chinh sach", "Bao mat", "Truy vet", '"API - Gia"'):
        assert f'"API - {cu}", "api_' not in ADMIN_API_PY and f'{cu}, "api_' not in ADMIN_API_PY, cu
    for moi in ("API — Chính sách", "API — Bảo mật", "API — Truy vết"):
        assert f'"{moi}", "api_' in ADMIN_API_PY, moi


def test_form_chinh_sach_co_nhan_viet_va_ten_ky_thuat():
    t = _doc(TPL, "api_chinh_sach.html")
    assert '"rpm_read": "Nhịp đọc / phút"' in t
    assert '<code class="adm-ten-ky-thuat">{{ f }}</code>' in t
    assert t.count('class="adm-form-luoi') == 4
    # Không còn ô chỉ có placeholder / select không nhãn.
    assert 'placeholder="tên (vd: pro)"' not in t and 'aria-label="Chính sách"' not in t
    assert "Chưa có chính sách — tạo ở trên trước" in t
    # Giao thức form giữ nguyên.
    for ten in ('name="name"', 'name="description"', 'name="is_default"', 'name="reason"',
                'name="policy_id"', 'name="scope"', 'name="subject_id"',
                'value="user"', 'value="project"', 'value="key"'):
        assert ten in t, ten


def test_vai_tro_hien_tieng_viet():
    for ten in ("khach_hang.html", "ho_so_360.html"):
        t = _doc(TPL, ten)
        assert "role or 'user' }}" not in t, ten
        assert "'admin': 'Quản trị viên', 'user': 'Thành viên'" in t, ten


# ── SQLAdmin ─────────────────────────────────────────────────────────────────

def test_sqladmin_nhan_cot_viet_va_ngay_gio_gon():
    from sqladmin.formatters import BASE_FORMATTERS

    from server.admin import JobAdmin, UserAdmin

    for cot, nhan in (("display_name", "Tên hiển thị"), ("is_active", "Đang hoạt động"),
                      ("is_verified", "Đã xác thực email"), ("created_at", "Tạo lúc"),
                      ("role", "Vai trò")):
        assert any(getattr(k, "key", k) == cot and v == nhan
                   for k, v in UserAdmin.column_labels.items()), cot
    assert UserAdmin.column_labels.get("so_du_credit") == "Số dư"
    assert JobAdmin.column_labels.get("created_at") == "Tạo lúc"
    assert BASE_FORMATTERS[datetime](datetime(2026, 9, 17, 10, 44, 9, 618680)) == "17/09/2026 10:44"


def test_sqladmin_vai_tro_la_o_chon_giu_gia_tri_luu():
    from wtforms import SelectField

    from server.admin import UserAdmin

    assert UserAdmin.form_overrides["role"] is SelectField
    assert [v for v, _ in UserAdmin.form_args["role"]["choices"]] == ["user", "admin"]


def test_sqladmin_huy_cung_cum_luu_va_gia_tri_save_nguyen_ven():
    for ten in ("edit.html", "create.html"):
        t = _doc(SQA, ten)
        cum = t[t.index('<div class="ltt-form-nut">'):t.index("</form>")]
        assert 'name="save" value="Save"' in cum and 'value="Save and continue editing"' in cum, ten
        assert '{{ _("Huỷ") }}</a>' in cum, ten
        assert 'class="col-md-2"' not in t, ten


def test_sqladmin_dau_trang_co_banh_mi_va_h1():
    t = _doc(SQA, "layout.html")
    assert '<h2 class="page-title">{{ title }}</h2>' not in t
    assert '<nav class="ltt-banhmi"' in t and '<h1 class="ltt-h1">' in t
    assert "{% block body_class %}co-aside{% endblock %}" in t


def test_sqladmin_thanh_tren_mobile_la_menu_khong_phai_dai_cuon():
    b = _doc(SQA, "base.html")
    assert "overflow-x:auto}" not in b[b.index(".ltt-adminhead"):b.index("</style>")]
    assert '<details class="ltt-adminmenu">' in b
    assert "{% block menu_phu %}{% endblock %}" in b
    assert re.search(r"@media\(max-width:767\.98px\)\{\s*\.navbar-vertical\{display:none!important\}", b)
    assert "aspect-ratio:1/1" in b, "checkbox khong bi keo thanh chu nhat cao"
