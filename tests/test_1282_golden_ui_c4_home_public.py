"""Golden UI C4 (17/09) — họ Workspace (trang chủ đã đăng nhập) và Public.

Chốt các khiếm khuyết người chấm độc lập V2 ghi (ảnh `sau/v6`), bằng mã nguồn +
HTML render thật — chỉ trình bày, không đổi quyền truy cập hay logic:

Workspace
* app "Đang phát triển" có nút PHỤ "Dùng thử", không cùng nút đỏ "Mở ứng dụng";
* mô tả thẻ cắt 2 dòng có "…", chân thẻ canh đáy, nhãn/nút ≥ 11px;
* ba mục chưa phát hành gom vào MỘT nhóm "Sắp có" (vẫn là nút vô hiệu);
* dải chip cuộn có mũi tên gợi cuộn gắn ngay khi tải; "Lỗi" trong hoạt động có màu;
* bìa nền sọc hiện icon lớn của app.
Public
* bảng tài liệu không ngắt giữa số / tên model; đường dẫn chỉ ngắt tại "/";
* h2 mục > h3 tiêu đề con theo thang chữ;
* trang chủ ẩn danh có CTA, thẻ dùng nút phụ, vạch đầu thẻ token ấm;
* LTTCODE: bước 1 theo trạng thái phát hành, chữ thân ≥ 14px;
* /gia-api có CTA, ghi chú làm tròn gom vào thẻ ví dụ; /api-dieu-khoan hết chữ in hoa hét.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
TPL = GOC / "server" / "templates"
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
LTTCODE = GOC / "apps" / "lttcode" / "templates" / "lttcode_download.html"


def _doc(p: pathlib.Path) -> str:
    return re.sub(r"\{#.*?#\}", "", p.read_text(encoding="utf-8"), flags=re.S)


def _khoi() -> str:
    mo, dong = "/* === C4: WORKSPACE-PUBLIC === */", "/* === HET C4: WORKSPACE-PUBLIC === */"
    assert CSS.count(mo) == 1 and CSS.count(dong) == 1, "khoi CSS C4 phai dung MOT lan"
    khoi = CSS.split(mo, 1)[1].split(dong, 1)[0]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b(?![-\w])", re.sub(r"#(market|catalog)-grid", "", khoi)), \
        "khoi C4 chi dung token, khong hex moi"
    return khoi


# ── Workspace ────────────────────────────────────────────────────────────────
def test_app_chua_phat_hanh_nut_phu_khong_doi_quyen():
    home = _doc(TPL / "home.html")
    # quyền truy cập giữ nguyên: thẻ enabled vẫn là <a href=route_prefix>
    assert '{% if m.enabled %}<a class="market-card" href="{{ m.route_prefix }}"' in home
    assert "{% if m.enabled and m.lifecycle == 'released' %}<strong>{{ _(\"Mở ứng dụng\") }}" in home
    assert '<strong class="c4-nut-phu">{{ _("Dùng thử") if m.lifecycle == \'development\'' in home
    khoi = _khoi()
    rule = re.search(r"strong\.c4-nut-phu\{([^}]*)\}", khoi)
    assert rule and "background:transparent" in rule.group(1)


def test_the_mo_ta_cat_co_ba_cham_chan_canh_day_chu_du_lon():
    khoi = _khoi()
    p = re.search(r"#market-grid \.market-card-body>p\{([^}]*)\}", khoi).group(1)
    assert "-webkit-line-clamp:2" in p and "text-overflow:ellipsis" in p and "height:auto" in p
    assert re.search(r"#market-grid \.market-card-foot\{[^}]*margin-top:auto", khoi)
    assert re.search(r"#market-grid \.market-card\{display:flex;flex-direction:column\}", khoi)
    for sel in (r"#market-grid \.market-card-foot i", r"#market-grid \.market-card-foot strong",
                r"#market-grid \.market-badge", r"\.c4-sap-co-ten"):
        m = re.search(sel + r"\{([^}]*)\}", khoi)
        co = float(re.search(r"font-size:([\d.]+)px", m.group(1)).group(1))
        assert co >= 11, (sel, co)


def test_sidebar_sap_co_gom_mot_nhom_van_vo_hieu():
    home = _doc(TPL / "home.html")
    nhom = re.search(r'<div class="c4-sap-co" role="group" aria-labelledby="c4-sap-co-ten">(.*?)</div>',
                     home, flags=re.S)
    assert nhom, "thieu nhom Sap co"
    assert nhom.group(1).count('class="market-deferred" disabled aria-disabled="true"') == 3
    assert '<small>{{ _("Chưa có") }}</small>' not in home


def test_chip_cuon_co_mui_ten_ngay_khi_tai_va_trang_thai_loi_co_mau():
    home = _doc(TPL / "home.html")
    assert "parentNode.classList.toggle('c4-con-tiep'" in home
    assert "document.fonts.ready" in home
    khoi = _khoi()
    assert '.market-filter-group.c4-con-tiep::after{content:"›"' in khoi
    assert 'class="c4-tt" data-trang-thai="{{ job.status }}"' in home
    assert ".activity-list small.c4-tt[data-trang-thai=error]{color:var(--err)}" in khoi


def test_bia_nen_soc_co_icon_app():
    home = _doc(TPL / "home.html")
    assert home.count('<span class="c4-bia-ic" aria-hidden="true">{{ ic.icon_app(m.icon) }}</span>') == 2
    khoi = _khoi()
    assert ".c4-bia-ic{display:none}" in khoi
    assert "#market-grid .market-cover:not(.cover-ai-image" in khoi


# ── Public ───────────────────────────────────────────────────────────────────
def test_catalog_an_danh_cta_nut_phu_vach_token():
    home = _doc(TPL / "home.html")
    assert "style=\"background:{{ m.accent }}\"" not in home
    assert '<span class="btn vien c4-nut-the">{{ _("Đăng nhập để dùng") }}</span>' in home
    assert '<a class="btn" href="{{ u(\'/register\') }}">' in home
    assert '<a class="btn ghost" href="{{ u(\'/login\') }}">' in home
    assert "#catalog-grid .appcard .accent.c4-vach{background:var(--brand-border)}" in _khoi()


@pytest.mark.parametrize("ten", ["huong_dan.html", "huong_dan_cong_cu.html", "gia_api.html", "api_dieu_khoan.html"])
def test_tai_lieu_co_pham_vi_thang_chu(ten):
    assert '<div class="c4-tai-lieu">' in (TPL / ten).read_text(encoding="utf-8")


def test_thang_chu_h2_lon_hon_h3_va_bang_khong_ngat_so():
    khoi = _khoi()
    assert ".c4-tai-lieu h2:not(.c3-muc-luc-ten){font-size:var(--fs-section)}" in khoi
    assert ".c4-tai-lieu h3{font-size:var(--fs-card)}" in khoi
    rule = re.search(r"\.c4-tai-lieu td\.c4-so,[^{]*\.c4-tai-lieu th code\{([^}]*)\}", khoi)
    assert rule and "white-space:nowrap" in rule.group(1)


def test_lttcode_buoc_mot_theo_trang_thai_va_chu_than_14px():
    src = _doc(LTTCODE)
    buoc = re.search(r'<li><b>\{\{ _\("Tải bộ cài"\) \}\}</b>(.*?)</li>', src, flags=re.S).group(1)
    assert buoc.startswith("{% if ban %}") and "{% else %}" in buoc
    style = re.search(r"<style>(.*?)</style>", src, flags=re.S).group(1)
    for sel in (".lc-feat p", ".lc-grid p", ".lc-faq p", ".lc-price p", ".lc-soon p", ".lc-note"):
        rule = re.search(re.escape(sel) + r"\{([^}]*)\}", style).group(1)
        assert "font-size:var(--fs-body)" in rule, sel


def test_gia_api_cta_va_ghi_chu_gom():
    gia = _doc(TPL / "gia_api.html")
    assert gia.count('<p class="c4-cta">') == 2
    assert 'href="/huong-dan">{{ _("Xem cách cắm") }}</a>' in gia
    # ghi chú làm tròn không còn là một thẻ riêng một câu
    assert not re.search(r'<div class="card">\s*\{% if bang\.toi_thieu_moi_luot_credit %\}', gia)
    assert gia.count('c4-ghi-chu') == 2


def test_api_dieu_khoan_khong_in_hoa_het():
    src = _doc(TPL / "api_dieu_khoan.html")
    assert "CHƯA đầy đủ" not in src and '_("Bản này chưa đầy đủ")' in src
    # 17/09 (L3 check_i18n): chữ đậm qua _() để bánh cóc i18n không tăng.
    assert '("<strong>%s</strong>"|format(_("giữ lại")))|safe' in src


# ── HTML render thật ─────────────────────────────────────────────────────────
@pytest.fixture()
def client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'c4.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(data))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "c4-test-secret")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from fastapi.testclient import TestClient

    from server.app import create_app
    try:
        yield TestClient(create_app(), base_url="https://testserver")
    finally:
        dbmod.reset_engine()


def test_render_huong_dan_duong_dan_ngat_tai_gach_va_so_nowrap(client):
    html = client.get("/huong-dan").text
    assert 'class="c4-duong">POST /<wbr>api/<wbr>v1/<wbr>' in html
    assert html.count('class="c4-so"') >= 5


def test_render_api_dieu_khoan_chu_dam_thay_in_hoa(client):
    html = client.get("/api-dieu-khoan").text
    assert "GIỮ LẠI" not in html and "CHƯA đầy đủ" not in html
    assert "<strong>giữ lại</strong>" in html


def test_render_lttcode_chua_phat_hanh_khong_bao_bam_nut_khong_co(client):
    html = client.get("/lttcode").text
    assert "Bấm Tải cho Windows ở đầu trang" not in html
    assert "sẽ hiện ở đầu trang khi bản ổn định đầu tiên phát hành" in html


def test_render_trang_chu_an_danh_co_cta_va_khong_mau_accent(client):
    html = client.get("/").text
    hero = re.search(r'<div class="hero c4-hero">.*?</ol></div>', html, flags=re.S)
    assert hero and 'href="/register"' in hero.group(0) and 'href="/login"' in hero.group(0)
    grid = html.split('id="catalog-grid"', 1)[1].split("<script>", 1)[0]
    assert 'style="background:' not in grid
    assert grid.count('class="btn vien c4-nut-the"') >= 1
