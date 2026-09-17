"""Golden UI C3 — họ Apps (17/09/2026). Chốt TĨNH các sửa trình bày đã soi trên khung nhìn thật.

1. Upscale: công tắc bị luật chung `input[type=checkbox]{18px}` ép thành hai hình tròn chồng ⇒
   luật riêng cao hơn đặt kích thước công tắc; chữ nút lọc ≥ 12px.
2. Ô chạm ≥ 24px: radio/checkbox ẩn trong chip phủ kín chip; radio/checkbox hiện 24px.
3. Chèn khoảng lặng: khách không phải tự đoán cú pháp JSON — giải thích ba khoá + nút chèn
   mẫu; hợp đồng form (name/required) giữ nguyên.
4. Tiếng Việt: Seedance không còn nhãn "Model"/"Prompt" trần, Thumbnail không "Brand Kit",
   Prompt AI classic không "Jobs ↗".
5. h1 riêng: Thumbnail không trùng "Tạo ảnh AI"; Seedance không trùng "Video của tôi" của
   LTT Video; hai dải menu video không vẽ lại logo LTT (topbar đã có).
6. Voice @≤820: bỏ đệm 64px (khoảng trống thật trước "Kết quả"); h1 Voice theo token.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")


def _doc(tep: str) -> str:
    return (GOC / tep).read_text(encoding="utf-8")


def _khoi_c3() -> str:
    i = CSS.find("/* === C3: APPS ===")
    assert i >= 0, "thiếu khối CSS C3: APPS"
    return CSS[i:]


def test_khoi_c3_la_khoi_cuoi_va_khong_hex_moi():
    khoi = _khoi_c3()
    assert CSS.count("/* === C3: APPS ===") == 1
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", khoi), "khối C3 phải dùng token, không hex"


def test_upscale_cong_tac_thang_luat_chung_checkbox():
    khoi = _khoi_c3()
    # (0,2,1) > (0,1,1) của `input[type=checkbox],input[type=radio]{width:18px}`
    assert re.search(r"\.up-switch input\[type=checkbox\]\{[^}]*width:44px;height:24px", khoi)
    assert ".up-switch input[type=checkbox]:checked::after{transform:translateX(20px)}" in khoi
    assert re.search(r"\.up-job-filters button,[^{]*\{font-size:12px\}", khoi)


def test_o_chon_an_phu_kin_chip_va_o_chon_hien_24px():
    khoi = _khoi_c3()
    assert re.search(r">input:is\(\[type=radio\],\[type=checkbox\]\)\{inset:0;width:100%;height:100%", khoi)
    m = re.search(r":is\(([^)]*\.lv-chon-muc[^)]*)\)>input:is\(\[type=radio\],\[type=checkbox\]\)\{width:24px;height:24px\}", khoi)
    assert m, "radio/checkbox hiện trong app phải 24px"
    for lop in (".lv-chon-muc", ".asv-chon", ".up-mode", ".th-save-brand", ".tv-audio"):
        assert lop in m.group(1)


def test_audio_pause_tro_giup_json_giu_hop_dong_form():
    src = _doc("apps/audio_pause/templates/audio_pause.html")
    assert re.search(r'<textarea id="ap-plan" name="pause_plan" rows="8" required', src)
    assert 'id="ap-chen-mau"' in src and 'type="button"' in src
    for khoa in ("<code>id</code>", "<code>anchor_text</code>", "<code>pause_ms</code>"):
        assert khoa in src
    assert "Danh sách mốc (JSON)" not in src
    # JS chỉ trình bày: không chặn submit, không đổi dữ liệu gửi đi.
    assert "preventDefault" not in src and "'submit'" not in src.split("<script>")[-1]


@pytest.mark.parametrize("tep,cu", [
    ("apps/taovideo/templates/taovideo.html", "<strong>01</strong> Model<"),
    ("apps/taovideo/templates/taovideo.html", "<strong>02</strong> Prompt<"),
    ("apps/thumbnail/templates/thumbnail.html", "Brand Kit"),
    ("apps/thumbnail/templates/thumbnail_fragment.html", "Brand Kit"),
    ("apps/taoanh/templates/image_thumbnail_shell.html", "Brand Kit"),
    ("apps/prompt_ai_ommi/templates/prompt_ai_ommi.html", ">Jobs ↗<"),
    ("apps/taovideo/templates/taovideo.html", "◉ LTT"),
    ("apps/lttvideo/templates/lttvideo.html", "◉ LTT"),
])
def test_khong_con_nhan_tieng_anh_hoac_logo_lap(tep, cu):
    assert cu not in _doc(tep)


def test_h1_moi_trang_rieng():
    h1 = {}
    for tep in ("apps/taoanh/templates/image.html", "apps/taoanh/templates/image_thumbnail_shell.html",
                "apps/thumbnail/templates/thumbnail.html", "apps/taovideo/templates/taovideo.html",
                "apps/lttvideo/templates/lttvideo.html"):
        m = re.search(r"<h1[^>]*>(.*?)</h1>", _doc(tep), re.S)
        assert m, tep
        h1[tep] = m.group(1).strip()
    assert h1["apps/taoanh/templates/image_thumbnail_shell.html"] != h1["apps/taoanh/templates/image.html"]
    assert h1["apps/thumbnail/templates/thumbnail.html"] != h1["apps/taoanh/templates/image.html"]
    assert h1["apps/taovideo/templates/taovideo.html"] != h1["apps/lttvideo/templates/lttvideo.html"]


def test_voice_khong_de_khoang_trong_man_hep_va_h1_theo_token():
    khoi = _khoi_c3()
    assert "@media(max-width:820px){.lv-studio .lv-st-trai{padding-bottom:0}}" in khoi
    assert re.search(r"\.lv-vo \.lv-vo-chu h1\{font-size:var\(--fs-section\)", khoi)


def test_chuoi_moi_co_ban_dich_tieng_anh():
    po = _doc("locale/en/LC_MESSAGES/messages.po")
    for msgid in ("Model AI", "Video Seedance của tôi", "Tạo thumbnail YouTube", "Chèn ví dụ mẫu",
                  "Danh sách mốc ngắt", "Lưu làm bộ nhận diện thương hiệu mặc định của tôi"):
        m = re.search(r'msgid "' + re.escape(msgid) + r'"\nmsgstr "([^"]+)"', po)
        assert m and m.group(1), msgid
