"""Golden UI C4 — khu API, VPS, Nexus (17/09/2026, vòng chấm độc lập V2).

Chốt các khiếm khuyết người chấm ghi, theo HÀNH VI render khi dựng được (macro,
đoạn template, trang /tai-xuong), theo cấu trúc nguồn khi trang cần cả một phiên:

Khu API
  1. Ô chọn "Công cụ" không bao giờ trống không chữ.
  2. "Bắt đầu": liên kết là danh sách, mỗi mục không ngắt dòng; panel biểu đồ giãn.
  3. Không chữ tiếng Anh ngoài enum: project "Default" hiện "Mặc định", "bộ sưu tập
     Postman", "yêu cầu đầu tiên".
  4. Tài liệu & SDK: nhóm là panel có tiêu đề, tài liệu là ô, href giữ nguyên.
  5. Dải tab màn hẹp: mép mờ theo vị trí cuộn, mục đang mở cuộn vào giữa.
VPS
  1. Nhật ký đổi mã HĐH/gói thành tên hiển thị.
  2. "Lần đo gần nhất" chỉ hiện khi đã có số đo.
  3. Hộp thông tin trang máy dùng token ấm.
  4/5. Thẻ số liệu cùng kiểu khu API, 2×2 ở màn hẹp; "Điều cần biết" cuối cột trái.
Nexus
  1. Lưới tải auto-fill, không căn giữa lệch trục.
  2. Một nhãn "Tải xuống"; SHA-256 một dòng + nút Chép (mã đủ ở title/innerText).
  3. "Thu hồi" kiểu nguy hiểm.
  4. Huy hiệu hero viết hoa đầu, cùng kiểu trang thật.
  5. Nhật ký phân bổ cột.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from tests.test_244_nexus_download import app_bat  # noqa: F401 — fixture dựng app

GOC = Path(__file__).resolve().parents[1]
TPL = GOC / "server" / "templates"
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")


def _doc(ten: str) -> str:
    return (TPL / ten).read_text(encoding="utf-8")


def _khoi_c4() -> str:
    i = CSS.index("/* === C4: DEV-VPS-NEXUS === */")
    return CSS[i:CSS.index("/* === HET C4: DEV-VPS-NEXUS === */")]


@pytest.fixture(scope="module")
def env():
    from server.templating import templates
    return templates.env


# ── Khu API ────────────────────────────────────────────────────────────────

def test_o_chon_cong_cu_co_dong_goi_y():
    t = _doc("dev_pricing.html")
    m = re.search(r'<select id="pr-tool" name="tool">(.*?)</select>', t, re.S)
    assert m
    dau = m.group(1).split("{% for name in tools %}")[0]
    assert '<option value="" disabled{% if not chosen %} selected{% endif %}>' in dau
    assert '_("Chọn công cụ…")' in dau and '_("Chưa có công cụ nào đang bật")' in dau


def test_bat_dau_lien_ket_la_danh_sach_khong_ngat_dong():
    t = _doc("dev_overview.html")
    assert re.search(r'<ul class="dev-lien-ket[^"]*">\s*<li><a href="/developers/quickstart">', t)
    assert '<p class="muted u-mt10">' not in t
    k = _khoi_c4()
    assert re.search(r"\.khu-dev \.dev-lien-ket li\{white-space:nowrap\}", k)
    assert "dev-luoi-gian" in t
    assert re.search(r"\.dev-luoi-gian>\.dev-panel>\.dev-panel-than\{flex:1", k)


def test_ten_du_an_default_hien_mac_dinh(env):
    mod = env.get_template("_dev_tt.html").make_module({})
    assert str(mod.du_an("Default")).strip() == "Mặc định"
    assert str(mod.du_an("Tích hợp shop")).strip() == "Tích hợp shop"
    for ten in ("dev_keys.html", "dev_usage.html", "dev_projects.html"):
        t = _doc(ten)
        assert "{{ project.name }}" not in t, ten
        assert "dtt.du_an(project.name)" in t, ten
    assert '_("Default")' not in _doc("dev_keys.html")
    assert "dtt.du_an(key.project)" in _doc("dev_keys.html")
    assert "dtt.du_an(project_name)" in _doc("dev_log_detail.html")


def test_khong_chu_tieng_anh_ngoai_enum():
    docs = _doc("dev_docs.html")
    assert ">Postman collection<" not in docs and ">environment<" not in docs
    assert '_("Bộ sưu tập Postman")' in docs
    logs = _doc("dev_logs.html")
    assert "Thực hiện request đầu tiên" not in logs
    assert '_("Thực hiện yêu cầu đầu tiên")' in logs


def test_tai_lieu_nhom_thanh_panel_co_tieu_de_href_giu_nguyen():
    t = _doc("dev_docs.html")
    assert t.count('<section class="dev-panel dev-tl-nhom">') == 2
    assert t.count('<li class="dev-tl-the') == 7
    assert t.count('class="dev-tl-the dev-tl-chinh"') == 1
    assert '<div class="card">' not in t
    for href in ("/huong-dan", "/huong-dan/cong-cu", "/gia-api", "/api/v1/openapi.json",
                 "/developers/openapi/download", "/tai/ltt_public_api.py", "/tai/ltt-public-api.ts",
                 "/tai/ltt-public-api.postman_collection.json",
                 "/tai/ltt-public-api.postman_environment.json"):
        assert f'href="{href}"' in t, href
    # Lệnh gọi thử vẫn là HAI dòng nối bằng "\".
    assert '$LTT_API_KEY" \\\n' in t


def test_dai_tab_man_hep_mep_mo_theo_vi_tri_cuon():
    b = _doc("developers_base.html")
    assert "toggleAttribute('data-mep-trai'" in b and "toggleAttribute('data-mep-phai'" in b
    assert "getBoundingClientRect" in b and "addEventListener('scroll'" in b
    k = _khoi_c4()
    for mep in ("data-mep-trai", "data-mep-phai"):
        assert re.search(r"\.khu-dev \.app-side\[" + mep + r"\][^{]*\{[^}]*mask-image:linear-gradient", k), mep
    # Mép tĩnh hai phía cũ đã bỏ — không còn mặt nạ vô điều kiện trên dải.
    assert not re.search(r"\.khu-dev \.app-side\{[^}]*mask-image", CSS)


# ── VPS ────────────────────────────────────────────────────────────────────

def _macro_doc_chi_tiet() -> str:
    t = _doc("vps_chi_tiet.html")
    i = t.index("{% macro doc_chi_tiet(ct) -%}")
    return t[i:t.index("{%- endmacro %}", i) + len("{%- endmacro %}")]


def test_nhat_ky_doi_ma_hdh_goi_thanh_ten(env):
    os_ds = [NS(id="winsrv2016-core", ten="Windows Server 2016 (Core)"),
             NS(id="winsrv2016-core-x", ten="Bản giả có mã là tiền tố")]
    plan = NS(id="vps-nho", ten="VPS Nhỏ")
    tpl = env.from_string(_macro_doc_chi_tiet() + "{{ doc_chi_tiet(ct) }}")
    ra = tpl.render(ct="hệ điều hành: winsrv2016-core · gói: vps-nho",
                    os_ban_duoc=os_ds, os=None, plan=plan)
    assert ra == "hệ điều hành: Windows Server 2016 (Core) · gói: VPS Nhỏ", ra
    # Mã dài không bị mã ngắn (tiền tố của nó) thay nhầm.
    ra2 = tpl.render(ct="hệ điều hành: winsrv2016-core-x", os_ban_duoc=os_ds, os=None, plan=None)
    assert ra2 == "hệ điều hành: Bản giả có mã là tiền tố", ra2
    # Mã lạ, và chữ trùng mã nhưng KHÔNG đứng sau đúng nhãn, giữ nguyên.
    ra3 = tpl.render(ct="tên cũ: vps-nho · hệ điều hành: ubuntu", os_ban_duoc=os_ds, os=None, plan=plan)
    assert ra3 == "tên cũ: vps-nho · hệ điều hành: ubuntu", ra3
    assert "{{ doc_chi_tiet(e.chi_tiet) }}" in _doc("vps_chi_tiet.html")


def test_lan_do_gan_nhat_chi_khi_co_so_do():
    t = _doc("vps_chi_tiet.html")
    i = t.index("{% elif quan_sat_cu %}")
    doan = t[i:t.index("Dải hành động", i)]
    assert "{% if may.quan_sat_luc %}" in doan
    assert doan.index("{% if may.quan_sat_luc %}") < doan.index("lần đo gần nhất và có thể đã cũ")


def test_hop_thong_tin_vps_token_am():
    assert re.search(r"\.vps-may \.alert\.alert-info\{[^}]*var\(--border-strong\)[^}]*"
                     r"background:var\(--surface-overlay\)", _khoi_c4())


def test_the_so_lieu_vps_cung_kieu_va_2x2_man_hep():
    k = _khoi_c4()
    assert re.search(r"\.vps-chi-so-ds \.chi-so\{[^}]*border-radius:var\(--radius-lg\)", k)
    assert re.search(r"\.vps-chi-so-ds \.chi-so-gt\{[^}]*font-weight:600", k)
    assert re.search(r"@media \(max-width:560px\)\{\s*\.vps-chi-so-ds\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)", k)


def test_dieu_can_biet_nam_cuoi_cot_trai():
    t = _doc("vps.html")
    i = t.index('<details class="vps-can-biet">')
    assert t.index('<div class="vps-may-ds">') < i < t.index("</div>{# cột phải của .vps-nha #}")
    # Nằm TRƯỚC cột phải (bảng giá), không dưới cả lưới.
    assert i < t.index("<div>", t.index("{% endif %}", i))
    assert t.count("Điều cần biết về dịch vụ") == 1


# ── Nexus ──────────────────────────────────────────────────────────────────

def test_luoi_tai_auto_fill_khong_can_giua():
    assert not re.search(r"\.nx-tai-luoi\{[^}]*justify-content:center", CSS)
    assert re.search(r"\.nx-tai-luoi\{display:grid;[^}]*repeat\(auto-fill", CSS)
    assert re.search(r"\.nx-tai-luoi--rong\{grid-template-columns:repeat\(auto-fill", CSS)


def test_mot_nhan_tai_va_sha_mot_dong_co_nut_chep():
    t = _doc("nexus_download.html")
    assert "Tải file cài" not in t
    sha = re.findall(r'<code class="nx-tai-sha-ma" data-chep title="\{\{ p\.(\w+) \}\}" '
                     r'translate="no">\{\{ p\.(\w+) \}\}</code>', t)
    assert len(sha) == 3 and all(a == b for a, b in sha), sha
    assert re.search(r"\.nx-tai-sha code\.nx-tai-sha-ma\{[^}]*text-overflow:ellipsis;white-space:nowrap", CSS)


def test_trang_tai_render_mot_nhan_sha_du(app_bat):  # noqa: F811
    client, tmp_path = app_bat
    (tmp_path / "data" / "nexus_versions.json").write_text(json.dumps({
        "version": "1.4.0",
        "platforms": {"windows": {
            "available": True, "kind": "zip", "url": "/nexus/dl/a.zip", "sha256": "a" * 64,
            "setup_url": "/nexus/dl/a-setup.exe", "setup_sha256": "b" * 64}},
    }), encoding="utf-8")
    html = client.get("/tai-xuong").text
    assert "Tải file cài" not in html
    assert html.count(">Tải xuống</a>") >= 1
    for ma in ("a" * 64, "b" * 64):
        assert f'data-chep title="{ma}" translate="no">{ma}</code>' in html


def test_thu_hoi_kieu_nguy_hiem():
    t = _doc("nexus_may.html")
    assert re.search(r'<button class="btn ghost sm nx-nut-nguy" type="submit">\{\{ _\("Thu hồi"\) \}\}</button>', t)
    assert re.search(r"\.nx-may-tac-vu \.btn\.nx-nut-nguy\{[^}]*color:var\(--err\)", _khoi_c4())


def test_huy_hieu_hero_viet_hoa_cung_kieu_trang_that():
    t = _doc("nexus_gioi_thieu.html")
    assert '_("đang bật")' not in t and '_("tắt")' not in t
    assert t.count('<span class="badge b-ok">{{ _("Đang bật") }}</span>') == 2
    assert '<span class="badge b-grey">{{ _("Đang tắt") }}</span>' in t
    may = _doc("nexus_may.html")
    assert '<span class="badge b-ok">{{ _("Đang bật") }}</span>' in may
    assert '<span class="badge b-grey">{{ _("Đang tắt") }}</span>' in may


def test_nhat_ky_nexus_phan_bo_cot():
    assert 'class="appcard nx-nhat-ky nx-nhat-ky--cot"' in _doc("nexus_may.html")
    k = _khoi_c4()
    assert re.search(r"\.nx-nhat-ky--cot table\{table-layout:fixed", k)
    assert re.search(r"\.nx-nhat-ky--cot th:nth-child\(2\)\{width:38%\}", k)
