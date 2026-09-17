"""Golden UI C3 — khu API, VPS, Nexus (17/09/2026).

Chốt các khiếm khuyết người chấm độc lập ghi, theo HÀNH VI render khi dựng được
(macro), theo cấu trúc nguồn khi trang cần cả một phiên:

Khu API
  1. Viên trạng thái hiện NGHĨA TIẾNG VIỆT rõ ("Đang chạy · `running`"), enum
     API vẫn nguyên văn; cột Công cụ/Khóa toàn "—" thì bỏ cột.
  2. Màn hẹp: điều hướng là MỘT dải cuộn ngang có mép mờ.
  3. MỘT đường tạo khóa; "Project" → "Dự án".
  4. Nhãn ô lọc không còn là tên trường thô `request_id`.
  5. Checkbox/radio scope có vùng chạm ≥ 24px.
VPS
  1. Mã máy một dòng (cắt "…"), nút Chép vẫn chép mã đủ.
  2. Gói hết chỗ không tô kiểu lỗi, "nên chọn" giảm nhấn.
  3. Tiêu đề nhóm menu cách mục trên; không `style=""` trong thanh băng thông.
  4. Dải hành động: MỘT nút chính đứng đầu; lời khối Nguy hiểm không nhắc GitHub.
Nexus
  1/3. MỘT component thẻ tải cho /nexus và /tai-xuong; iOS nói tiếng Việt.
  2. Nhật ký thành thẻ nhãn/giá trị ở màn hẹp.
  4. Đổi tên mở bằng nút; nhãn viết hoa đầu; không badge credit lặp header.
  5. Một kiểu trạng thái rỗng.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest

from tests.test_197_developer_api_tab import _register, portal  # noqa: F401

GOC = Path(__file__).resolve().parents[1]
TPL = GOC / "server" / "templates"
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")


def _doc(ten: str) -> str:
    return (TPL / ten).read_text(encoding="utf-8")


def _khoi_c3() -> str:
    i = CSS.index("/* === C3: DEV-VPS-NEXUS === */")
    return CSS[i:CSS.index("/* === HET C3: DEV-VPS-NEXUS === */")]


@pytest.fixture(scope="module")
def env():
    from server.templating import templates
    return templates.env


# ── Khu API ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("gia_tri,nghia", [("running", "Đang chạy"), ("queued", "Đang chờ"),
                                           ("done", "Hoàn tất"), ("error", "Lỗi"),
                                           ("cancelled", "Đã hủy")])
def test_vien_trang_thai_hien_nghia_viet_TRUOC_ma_api(env, gia_tri, nghia):
    html = str(env.get_template("_dev_tt.html").make_module({}).tt(gia_tri))
    m = re.search(r'class="dev-tt-nghia">([^<]+)<.*?<code class="dev-tt-ma"[^>]*>([^<]+)<', html)
    assert m, html
    assert m.group(1) == nghia and m.group(2) == gia_tri, html
    # Nghĩa không nằm trong phần tử ẩn — người nhìn phải thấy.
    assert "sr-only" not in html


def test_o_loc_trang_thai_usage_hien_nghia(env):
    mod = env.get_template("_dev_tt.html").make_module({})
    assert str(mod.nghia("running")).strip() == "Đang chạy"
    t = _doc("dev_usage.html")
    assert "dtt.nghia(value" in t


def test_usage_bo_cot_toan_gach():
    t = _doc("dev_usage.html")
    assert "{% set co_tool =" in t and "{% set co_khoa =" in t
    assert '{% if co_tool %}<th scope="col">' in t
    assert '{% if co_khoa %}<th scope="col">' in t


def test_dieu_huong_man_hep_la_mot_dai_cuon_co_mep_mo():
    k = _khoi_c3()
    m = re.search(r"@media \(max-width:820px\)\{(.*?)\n\}", k, re.S)
    assert m, "thieu khoi man hep cua khu API"
    than = m.group(1)
    assert re.search(r"\.khu-dev \.app-side\{[^}]*flex-wrap:nowrap[^}]*overflow-x:auto", than)
    assert "mask-image:linear-gradient" in than
    # Mục đang mở được cuộn vào giữa dải (không cuộn trang).
    assert "scrollLeft" in _doc("developers_base.html")


def test_mot_duong_tao_khoa_va_du_an(portal):  # noqa: F811
    _register(portal, f"c3k-{uuid.uuid4().hex[:6]}@example.com")
    html = portal.get("/developers/keys").text
    # Chưa có khóa: biểu mẫu mở sẵn là đường DUY NHẤT — không nút đầu trang,
    # không nút trong trạng thái rỗng.
    assert html.count('href="#tao-khoa"') == 0, "con nut tao khoa trung lap"
    assert "Tạo khóa đầu tiên" not in html
    assert re.search(r'<details class="dev-tao" id="tao-khoa"\s+open', html)
    assert "Thuộc dự án" in html
    assert re.search(r'aria-current="page" class="active">\s*Khóa\s*<', html)
    assert re.search(r"<a href=\"/developers/projects\"[^>]*>\s*Dự án\s*</a>", html), (
        "tab con van ghi 'Project'")


def test_nhan_o_loc_request_id_co_nghia():
    t = _doc("dev_logs.html")
    assert '<label for="lg-request">request_id</label>' not in t
    assert re.search(r'<label for="lg-request">\{\{ _\("Mã yêu cầu"\) \}\}', t)


def test_checkbox_scope_vung_cham_24px():
    assert re.search(r"\.khu-dev \.dev-chon input\[type=checkbox\][^{]*\{[^}]*width:24px;height:24px",
                     _khoi_c3())


# ── VPS ────────────────────────────────────────────────────────────────────

def test_thanh_bang_thong_khong_style_noi_tuyen(env):
    mac = env.get_template("_vps_mac.html").make_module({})
    html = str(mac.do_bang_thong({"da_dung": "180.0 GB", "han_muc_gb": 600,
                                  "bi_giam_toc": False, "phan_tram": 37}))
    assert "style=" not in html, html
    assert 'width="37%"' in html
    tran = str(mac.do_bang_thong({"da_dung": "9 GB", "han_muc_gb": 1,
                                  "bi_giam_toc": False, "phan_tram": 900}))
    assert 'width="100%"' in tran and "qua-han" in tran
    assert 'style="display:none' not in _doc("vps.html")


def test_ma_may_mot_dong_chep_ma_du():
    t = _doc("_vps_mac.html")
    assert re.search(r'<code class="gt vps-ma-may" data-chep title="\{\{ may\.id \}\}"', t)
    assert re.search(r"\.vps-dinh-o \.vps-ma-may\{[^}]*white-space:nowrap[^}]*text-overflow:ellipsis",
                     _khoi_c3())


def test_goi_het_cho_khong_to_kieu_loi():
    k = _khoi_c3()
    assert re.search(r"\.goi-the\.goi-chon\.goi-het\{[^}]*background:transparent", k)
    assert re.search(r"\.goi-the\.goi-het \.goi-ten \.pill\{[^}]*color:var\(--text-muted\)", k)


def test_tieu_de_nhom_menu_vps_co_khoang_cach():
    assert re.search(r"\.app-side li:not\(:first-child\)>\.nhom\{[^}]*margin-top:18px", _khoi_c3())


def test_dai_hanh_dong_may_mot_nut_chinh_dung_dau():
    t = _doc("vps_chi_tiet.html")
    i = t.rindex('class="vps-hd"', 0, t.index("Cài Windows"))
    dai = t[i:t.index("</div>\n  {% endif %}", t.index("Cài Windows", i))]
    # Mỗi nhánh đúng MỘT nút chính, và nó là nút ĐẦU tiên của nhánh.
    nhanh_tat, nhanh_chay = dai.split("{% else %}", 1)
    for nhanh in (nhanh_tat, nhanh_chay):
        nut = re.findall(r'class="btn ([a-z -]+)"', nhanh)
        assert nut and nut[0] == "btn-may", nut
        assert nut.count("btn-may") == 1, nut
    assert 'class="vps-hd-nguon" role="group"' in nhanh_chay


def test_khoi_nguy_hiem_noi_voi_khach_khong_nhac_github():
    t = _doc("vps_chi_tiet.html")
    for s in re.findall(r'_\("([^"]*)"\)', t):
        assert "GitHub" not in s, s


# ── Nexus ──────────────────────────────────────────────────────────────────

def test_hai_man_tai_dung_chung_mot_component():
    for ten in ("nexus_download.html", "nexus_gioi_thieu.html"):
        t = _doc(ten)
        assert '{% import "_nexus_tai.html" as nxt with context %}' in t, ten
        assert "nxt.the(" in t, ten
    assert not re.search(r"^<style>", _doc("nexus_download.html"), re.M)
    assert "nx-os" not in _doc("nexus_gioi_thieu.html")


def test_the_tai_ios_noi_tieng_viet_khong_in_note_tho(env):
    mod = env.get_template("_nexus_tai.html").make_module({"u": lambda p: p})
    p = {"key": "ios", "label": "iOS", "available": True, "signed": False,
         "url": "/nexus/dl/x.ipa", "note": "Can SideStore hoac Sideloadly de cai"}
    html = str(mod.the(p, href="/tai-xuong"))
    assert "Can SideStore hoac" not in html
    assert "SideStore hoặc Sideloadly" in html
    assert ">Tải xuống<" in html
    chua = str(mod.the({"key": "android", "label": "Android", "available": False}, href="/tai-xuong"))
    assert "Đang chuẩn bị" in chua and "<a " not in chua


def test_may_cua_toi_doi_ten_mo_bang_nut_va_nhan_viet_hoa():
    t = _doc("nexus_may.html")
    assert "cbadge" not in t, "badge credit lap header"
    m = re.search(r'<details class="nx-may-doi">\s*<summary[^>]*>\{\{ _\("Đổi tên"\) \}\}</summary>'
                  r'\s*<form method="post" action="/may-cua-toi/\{\{ m\.id \}\}/doi-ten"', t)
    assert m, "o doi ten phai nam sau nut Doi ten"
    assert 'name="csrf_token"' in t[m.end():m.end() + 200]
    for thuong in ('_("tắt")', '_("đang bật")', '_("chưa từng kết nối")'):
        assert thuong not in t, thuong
    assert "'windows': 'Windows'" in t


def test_nhat_ky_dang_the_o_man_hep():
    t = _doc("nexus_may.html")
    assert t.count('data-nhan="') == 4
    assert re.search(r"\.nx-nhat-ky td::before\{content:attr\(data-nhan\)", _khoi_c3())


def test_mot_kieu_trang_thai_rong():
    t = _doc("nexus_may.html")
    assert "nx-may-rong" not in t
    assert t.count('class="appcard nx-may-trong"') == 2
