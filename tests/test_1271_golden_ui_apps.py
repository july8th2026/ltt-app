"""Golden UI — họ Apps (chiến dịch 17/09/2026, `plan_trien_khai.md`).

Chốt TĨNH trên template/CSS những gì đã sửa để các màn app server-render trông như
MỘT sản phẩm:

1. Bốn form app nhỏ (transcript, audio-pause, video-assembly, prompt-canh) dùng khung
   `.af-*`: đầu trang kicker + h1 + "Việc của tôi", thẻ có số bước 01/02, MỘT nút chính
   trong thanh hành động, lịch sử có trạng thái rỗng viền đứt. Trước đó KHÔNG có luật
   CSS nào cho `.ts-/.ap-/.va-/.pc-*`.
2. Hợp đồng form không đổi: action, name, accept/required/multiple.
3. Quality Lab: không input file trần, không nhãn tiếng Anh, không teal (DL-002).
4. Upscale: `h1` là tên trang, không phải chữ ô thả tệp; số bước 01..05.
5. Không còn ký tự điều khiển / `style=""` tĩnh / jargon tiếng Anh đã gỡ.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")


def _doc(tep: str) -> str:
    return (GOC / tep).read_text(encoding="utf-8")


FORM_NHO = {
    "apps/transcript/templates/transcript.html": ("ts", "/transcript/tao",
                                                  ("audio", "language", "min_s", "max_s", "include_silence")),
    "apps/audio_pause/templates/audio_pause.html": ("ap", "/audio-pause/tao",
                                                    ("audio", "pause_plan", "language", "nguong_khop",
                                                     "min_gap_s", "min_pause_ms", "max_pause_ms")),
    "apps/video_assembly/templates/video_assembly.html": ("va", "/video-assembly/tao",
                                                          ("clips", "music", "che_do_khop", "bat_demucs",
                                                           "bat_phu_de", "cau_hinh")),
    "apps/prompt_canh/templates/prompt_canh.html": ("pc", "/prompt-canh/tao",
                                                    ("kich_ban", "so_canh", "visual_style", "duration",
                                                     "batch_step2", "batch_step3")),
}


# ── 1. Khung form app nhỏ ────────────────────────────────────────────────────

@pytest.mark.parametrize("tep", FORM_NHO)
def test_form_app_nho_dung_khung_chung(tep):
    src = _doc(tep)
    tien_to, _action, _ten = FORM_NHO[tep]
    assert 'class="%s-head af-head"' % tien_to in src
    assert '<span class="af-kicker">' in src
    assert 'href="/jobs"' in src
    assert 'class="%s-form af-card"' % tien_to in src
    so = re.findall(r'<div class="af-step"><span>0(\d)</span>', src)
    assert so == ["1", "2"], so
    # Một nút chính, nằm trong thanh hành động.
    assert src.count('type="submit"') == 1
    assert re.search(r'<div class="af-actions"><button class="btn" type="submit">', src)
    assert 'class="btn primary"' not in src
    assert 'class="af-card af-history"' in src and 'class="af-empty"' in src


@pytest.mark.parametrize("tep", FORM_NHO)
def test_form_app_nho_khong_lap_tieu_de_va_alert_co_luat(tep):
    src = _doc(tep)
    assert "topbar_title" not in src, "dải tiêu đề lặp y nguyên h1"
    assert 'class="alert error"' not in src, "`.alert.error` không có luật CSS"


@pytest.mark.parametrize("tep", FORM_NHO)
def test_form_app_nho_giu_hop_dong_form(tep):
    src = _doc(tep)
    _tien_to, action, ten = FORM_NHO[tep]
    assert f'action="{action}"' in src
    assert 'name="csrf_token"' in src
    for t in ten:
        assert f'name="{t}"' in src or f"'{t}'" in src, t


def test_cot_cach_khop_khong_lo_enum():
    src = _doc("apps/video_assembly/templates/video_assembly.html")
    assert '.get("timeline_mode", "—") }}</td>' not in src
    assert '"sequential": _("Theo tên tệp")' in src


def test_css_khung_form_app_dung_token():
    khoi = CSS[CSS.index("/* === Golden UI song song: APPS === */"):]
    luat = re.sub(r"/\*.*?\*/", "", khoi, flags=re.S)
    for lop in (".af-head{", ".af-card{", ".af-step>span{", ".af-actions{", ".af-empty{",
                ".ts-row,.ap-row,.va-row,.pc-row{"):
        assert lop in luat, lop
    assert not re.findall(r"#[0-9a-fA-F]{3,6}\b", luat), "hex thô trong khối APPS"


# ── 2. Quality Lab ───────────────────────────────────────────────────────────

def test_quality_lab_upload_chung_tieng_viet_khong_teal():
    src = _doc("apps/qualitylab/templates/qualitylab.html")
    assert 'type="file"' not in src
    for id_, ten in (("ql-file", "source_file"), ("ql-reference", "reference_file"),
                     ("ql-low", "low_input_file")):
        assert f'o_chon_tep("{id_}", "{ten}"' in src
    for cu in ("Evaluation mới", "Evaluator registry", "Evaluation gần đây",
               "Tạo evaluation job", "<td>{{ job.status }}</td>", "<style>"):
        assert cu not in src, cu
    assert "ui.nhan_trang_thai(job.status)" in src
    assert "#0e7c86" not in re.sub(r"/\*.*?\*/", "", CSS, flags=re.S).lower()
    report = _doc("apps/qualitylab/templates/qualitylab_report.html")
    assert report.count("<h1") == 1


# ── 3. Upscale / Voice ───────────────────────────────────────────────────────

def test_upscale_h1_la_ten_trang_va_so_buoc_hai_chu_so():
    src = _doc("apps/upscalevideo/templates/upscalevideo.html")
    assert src.count("<h1") == 1
    assert '<h1 class="app-bar-title">Upscale Video</h1>' in src
    so = re.findall(r"<h2><b>(\d+)</b>", src)
    assert so == ["01", "02", "03", "04", "05"], so
    assert ".up-start{text-transform:none" in CSS


def test_voice_so_buoc_hai_chu_so_va_khong_ky_tu_dieu_khien():
    assert "content:counter(lvb,decimal-leading-zero)" in CSS
    assert not re.search(r"[\x80-\x9f]", CSS), "ký tự điều khiển C1 trong ltt.css"
    assert "details.lv-tao-giong[open]>summary::before{content:'\\2212'}" in CSS


# ── 4. Thống nhất chữ và style ───────────────────────────────────────────────

def test_hai_tab_image_studio_cung_dai_tieu_de():
    for tep in ("apps/taoanh/templates/image.html", "apps/taoanh/templates/image_thumbnail_shell.html",
                "apps/thumbnail/templates/thumbnail.html"):
        assert "{% block topbar_title %}<strong>Image Studio</strong>{% endblock %}" in _doc(tep), tep


@pytest.mark.parametrize("tep", [
    "apps/agent/templates/agent.html", "apps/agent/templates/agent_run.html",
    "apps/autosubvideo/templates/autosubvideo.html", "apps/chatltt/templates/chatltt.html",
    "apps/prompt_ai_ommi/templates/prompt_ai_ommi_workspace.html",
])
def test_khong_style_tinh_trong_template_app(tep):
    # Chỉ cho phép style="" mang giá trị Jinja (độ rộng thanh tiến độ).
    tinh = [s for s in re.findall(r'style="([^"]*)"', _doc(tep)) if "{{" not in s]
    assert not tinh, tinh


@pytest.mark.parametrize("tep,cu", [
    ("apps/taoanh/templates/image.html", "output thật"),
    ("apps/taoanh/templates/image.html", "Output thật"),
    ("apps/taoclipngan/templates/taoclipngan.html", "Upload mới hoặc dùng lại asset"),
    ("apps/taoclipngan/templates/taoclipngan.html", "upload thẳng Storage"),
    ("apps/thumbnail/templates/thumbnail.html", "remix từ output"),
    ("apps/thumbnail/templates/thumbnail_fragment.html", "hai output thật"),
])
def test_khong_jargon_tieng_anh_trong_cau_tieng_viet(tep, cu):
    assert cu not in _doc(tep)


def test_ommi_classic_nen_toi_dung_token_am():
    src = _doc("apps/prompt_ai_ommi/templates/prompt_ai_ommi.html")
    assert ".ommi.dark{--o-bg:var(--surface-canvas)" in src
    assert "#090a0c" not in src


def test_studio_video_so_buoc_lien_mach_va_mot_kieu_huy_hieu():
    """B1 17/09: LTT Video ẩn mục Đính kèm theo tác vụ ⇒ số viết cứng để lại 01·02·04.
    Đếm bằng biến Jinja; Seedance bỏ mục "03B"; hai studio dùng huy hiệu tròn chung."""
    ltt = (GOC / "apps/lttvideo/templates/lttvideo.html").read_text(encoding="utf-8")
    assert not re.search(r"<strong>0\d</strong>", ltt)
    assert ltt.count('{{ "%02d" % buoc.n }}') == 4
    seed = (GOC / "apps/taovideo/templates/taovideo.html").read_text(encoding="utf-8")
    assert "03B" not in seed
    css = (GOC / "server/static/ltt.css").read_text(encoding="utf-8")
    assert re.search(r"\.tv-fieldset legend strong,\.tv-section h2 strong\{display:inline-grid;[^}]*border-radius:50%", css)


@pytest.mark.parametrize("tep", ["frontend/agent-canvas/src/canvas.css", "frontend/autosub-studio/src/studio.css"])
def test_B4_spa_khong_con_xam_lanh_tran(tep):
    """DL-002: xám trung tính lạnh viết trần trong theme TỐI phải đi qua token ấm.
    Giữ: màu bão hoà (trạng thái/phân loại), hex alpha, fallback `var(--x,#…)`, định
    nghĩa biến `--x:`, và luật `.theme-light` (token Golden chỉ có bản tối)."""
    s = re.sub(r"var\(--[a-z0-9-]+,\s*#[0-9a-fA-F]{3,8}\)", "", (GOC / tep).read_text(encoding="utf-8"))
    lanh = []
    for sel, than in re.findall(r"([^{}]+)\{([^{}]*)\}", s):
        if "light" in sel.lower():
            continue
        for prop, val in re.findall(r"(-{0,2}[a-z][a-z0-9-]*)\s*:\s*([^;{}]*)", than):
            if prop.startswith("--"):
                continue
            chu = prop in ("color", "fill", "stroke", "caret-color")
            for h in re.findall(r"#[0-9a-fA-F]{6}", val):
                r, g, b = (int(h[k:k + 2], 16) for k in (1, 3, 5))
                sang = (r + g + b) / 3
                if (max(r, g, b) - min(r, g, b) <= 24 and b >= r + 4
                        and not (not chu and sang > 150) and not (chu and sang < 70)):
                    lanh.append(h)
    assert not lanh, lanh[:10]


def test_B4_canvas_theme_sang_chu_muted_dat_AA():
    """Đo 17/09 (axe, theme sáng): `--text-muted:#737d89` chỉ 4,14–4,18:1 trên nền #f5f6f8."""
    css = (GOC / "frontend/agent-canvas/src/canvas.css").read_text(encoding="utf-8")
    assert "#737d89" not in css and "--text-muted:#5f6874" in css
