"""Golden UI C4 — họ Apps (17/09/2026): một mẫu đầu trang, một kiểu chip, một quy tắc chữ ô mô tả.

Người chấm độc lập V2 cho họ Apps 79 điểm, đòn bẩy lớn nhất: mỗi app một kiểu đầu trang
(Voice tiêu đề nhỏ, Seedance eyebrow xám, Tạo ảnh eyebrow đỏ + dải "Image Studio", Lồng
tiếng Việt lặp tiêu đề, Upscale tiêu đề trần trong dải). Chốt ở đây:

1. Macro `server/templates/_app_head.html`: eyebrow nhóm -> h1 -> mô tả -> hành động phụ,
   và CHÚ THÍCH quy ước độ rộng (form 1120px / studio rộng).
2. Mọi app server-render trong danh sách gọi macro, không còn `topbar_title` lặp tên.
3. Studio immersive (Seedance, LTT Video) dùng cùng lớp eyebrow/h1.
4. Một kiểu chip lọc (viền; đang chọn = --brand-soft + --brand-border), không hex.
5. Ô mô tả tự nhiên chữ sans; monospace chỉ cho ô JSON.
6. Rail/nút studio dùng icon SVG (`ic.icon`), không ký tự ▶ ▣ ▦ ☷ ⚡ ◇ ✦.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")


def _doc(tep: str) -> str:
    return (GOC / tep).read_text(encoding="utf-8")


def _khoi_c4() -> str:
    i = CSS.index("/* === C4: APPS ===")
    khoi = CSS[i:]
    j = khoi.find("/* === ", 10)
    return khoi if j < 0 else khoi[:j]


# ── 1. Macro ─────────────────────────────────────────────────────────────────

def _macro(*args, **kw) -> str:
    from server.templating import templates
    ah = templates.env.get_template("_app_head.html").module
    return str(ah.dau_trang(*args, **kw))


def test_macro_dau_trang_mot_thu_tu_eyebrow_h1_mo_ta_hanh_dong():
    html = _macro("Workflow", "Phiên âm", "Một câu mô tả.", id_tieu_de="ts-title", lop="ts-head")
    assert 'class="app-head app-head--form ts-head"' in html
    vi_tri = [html.index(x) for x in ('class="app-eyebrow"', '<h1 class="app-head-h1" id="ts-title">',
                                      'class="app-head-mota"', 'href="/jobs"')]
    assert vi_tri == sorted(vi_tri), vi_tri
    assert html.count("<h1") == 1 and "Việc của tôi" in html


def test_macro_khong_mo_ta_khong_hanh_dong_thi_khong_ve_the_rong():
    html = _macro("Video", "Upscale Video", "", viec=False, kieu="studio")
    assert "app-head--studio" in html
    assert "app-head-mota" not in html and "app-head-hd" not in html


def test_macro_ghi_ro_quy_uoc_do_rong():
    src = _doc("server/templates/_app_head.html")
    assert "QUY ƯỚC ĐỘ RỘNG" in src and "1120px" in src
    assert 'kieu="form"' in src and 'kieu="studio"' in src


# ── 2. App dùng macro ────────────────────────────────────────────────────────

DUNG_MACRO = [
    "apps/ltt_voice/templates/_voice_vo.html",
    "apps/taoanh/templates/image.html",
    "apps/taoanh/templates/image_thumbnail_shell.html",
    "apps/thumbnail/templates/thumbnail.html",
    "apps/taoclipngan/templates/taoclipngan.html",
    "apps/upscalevideo/templates/upscalevideo.html",
    "apps/auto_scan_video/templates/asv_trang_chinh.html",
    "apps/auto_scan_video/templates/asv_chi_tiet.html",
    "apps/transcript/templates/transcript.html",
    "apps/audio_pause/templates/audio_pause.html",
    "apps/video_assembly/templates/video_assembly.html",
    "apps/prompt_canh/templates/prompt_canh.html",
    "apps/qualitylab/templates/qualitylab.html",
    "apps/qualitylab/templates/qualitylab_report.html",
    "apps/agent/templates/agent.html",
]


@pytest.mark.parametrize("tep", DUNG_MACRO)
def test_app_goi_macro_dau_trang_khong_lap_ten_trong_dai_tieu_de(tep):
    src = _doc(tep)
    assert '{% import "_app_head.html" as ah %}' in src
    assert "ah.dau_trang(" in src
    assert "topbar_title" not in src, "dải tiêu đề lặp tên trang"
    assert "<h1" not in src, "h1 phải do macro vẽ"
    # Eyebrow đầu trang chép tay cũ (mỗi app một câu, một lớp). Kicker của khối con
    # (vd "Lịch sử kết quả" trên h2) vẫn được phép.
    for cu in ('<span class="af-kicker">', '<span class="image-shell-kicker">', "Không gian clip ngắn AI",
               "Studio sáng tạo AI · Thumbnail", '<header class="im-heading">', '<header class="asv-dau">'):
        assert cu not in src, cu


def test_form_mot_cot_rong_1120_studio_giu_rong():
    # Form một cột: bỏ `wide` (video-assembly từng rộng 1600px). Studio nhiều cột giữ.
    assert "page_mode" not in _doc("apps/video_assembly/templates/video_assembly.html")
    for tep in ("apps/taoanh/templates/image.html", "apps/taoclipngan/templates/taoclipngan.html"):
        assert "{% block page_mode %}wide{% endblock %}" in _doc(tep)
    assert "{% block page_mode %}immersive{% endblock %}" in _doc("apps/upscalevideo/templates/upscalevideo.html")
    assert re.search(r"\.page--standard:has\([^)]*app-head--form[^{]*\{max-width:calc\(1120px \+ 48px\)\}", _khoi_c4())


def test_voice_dai_dau_man_van_giu_chip_co_loi_giai_thich():
    src = _doc("apps/ltt_voice/templates/_voice_vo.html")
    assert 'lop="lv-vo"' in src and "{% call ah.dau_trang(" in src
    assert src.count("title=") >= 3


@pytest.mark.parametrize("tep", ["apps/taovideo/templates/taovideo.html", "apps/lttvideo/templates/lttvideo.html"])
def test_studio_immersive_cung_eyebrow_va_h1(tep):
    src = _doc(tep)
    assert 'class="eyebrow app-eyebrow">{{ _("Video") }} · ' in src
    assert '<h1 class="app-head-h1">' in src


# ── 3. CSS ───────────────────────────────────────────────────────────────────

def test_css_c4_dung_token_khong_hex():
    khoi = re.sub(r"/\*.*?\*/", "", _khoi_c4(), flags=re.S)
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", khoi)
    for lop in (".app-head{", ".app-head-chu{", ".app-head .app-head-h1", ".app-head-hd{"):
        assert lop in khoi, lop


def test_mot_kieu_chip_loc_cho_moi_app():
    khoi = _khoi_c4()
    nhom = ".asv-loc>button[data-nguon-giong],.lv-loc-nut,.tv-tabs a,.up-job-filters button"
    assert re.search(r":is\(" + re.escape(nhom) + r"\)\{[^}]*border:1px solid var\(--border-subtle\);"
                     r"border-radius:var\(--radius-pill\)", khoi)
    dang_chon = re.search(r":is\(\.asv-loc>button\[data-nguon-giong\]\[aria-pressed=true\],\.lv-loc-nut\.on,"
                          r"\.tv-tabs a\.on,\.up-job-filters button\[aria-pressed=true\]\)\{([^}]*)\}", khoi)
    assert dang_chon, "thiếu luật chip đang chọn chung"
    assert "var(--brand-border)" in dang_chon.group(1) and "var(--brand-soft)" in dang_chon.group(1)


def test_o_mo_ta_tu_nhien_chu_sans_json_monospace():
    khoi = _khoi_c4()
    sans = re.search(r":is\(([^)]*)\)\{font-family:var\(--font\)", khoi)
    assert sans
    for o in ("#im-prompt", "#tv-prompt", ".th-field textarea", "#goal", ".pc-form textarea"):
        assert o in sans.group(1), o
    assert re.search(r":is\(\.va-adv textarea,#ap-plan\)\{font-family:var\(--mono\)\}", khoi)


# ── 4. Icon và chữ ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("tep", ["apps/taovideo/templates/taovideo.html", "apps/lttvideo/templates/lttvideo.html"])
def test_rail_studio_video_dung_icon_svg(tep):
    src = _doc(tep)
    assert '{% import "_icon.html" as ic %}' in src
    for cu in (">▶<small>", ">▣<small>", ">▦<small>", ">▦</button>", ">☷</button>", '"submit">✦ '):
        assert cu not in src, cu
    for ten in ("clapperboard", "clock", "folder", "layout-grid", "sparkles"):
        assert f'ic.icon("{ten}")' in src, ten


def test_upscale_icon_va_chu_viet():
    src = _doc("apps/upscalevideo/templates/upscalevideo.html")
    for cu in ("⚡", "◇", "✦", ">☷<", ">▦<", "submit nguyên tử"):
        assert cu not in src, cu
    assert 'aria-label="{{ _(\'Danh sách\') }}"' in src and 'aria-label="{{ _(\'Lưới\') }}"' in src


def test_seedance_nhan_may_quay_tieng_viet():
    src = _doc("apps/taovideo/templates/taovideo.html")
    for cu in (">Tracking<", ">Orbit<", ">Handheld<", ">Aerial<", ">Dolly in<", ">Theo prompt<", "<label>Camera<"):
        assert cu not in src, cu
    assert '<option value="tracking">{{ _("Bám theo (tracking)") }}</option>' in src
