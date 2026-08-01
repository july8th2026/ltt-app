"""
H-di-tru — Đợt R: khoá PARITY của app thumbnail với bản gốc BOT GEMINI.

Test này là "cổng parity": nếu ai lỡ xoá tài nguyên prompt hoặc quay lại hardcode
prompt, test đỏ ngay. Cũng khoá "nhà máy" `prompt_fragments`.
"""
from __future__ import annotations

import pathlib


PROMPTS = pathlib.Path(__file__).resolve().parent.parent / "apps" / "thumbnail" / "prompts"

# Số lựa chọn gốc (từ _labels.json BOT GEMINI, xem DOI_CHIEU_THUMBNAIL.md).
EXPECT = {"text_style": 6, "phong_cach": 11, "kieu_trend": 9, "ngon_ngu": 5}


def test_catalog_du_so_luong_lua_chon():
    from platform_core import prompt_fragments as pf
    for group, n in EXPECT.items():
        opts = pf.options(PROMPTS, group)
        assert len(opts) == n, f"{group}: co {len(opts)} lua chon, can {n}"


def test_moi_lua_chon_co_file_fragment():
    from platform_core import prompt_fragments as pf
    for group in EXPECT:
        for opt_id, _label in pf.options(PROMPTS, group):
            frag = pf.read_fragment(PROMPTS, group, opt_id)
            assert frag.strip(), f"fragment rong: {group}/{opt_id}"


def test_base_prompt_ton_tai_va_co_placeholder():
    base = (PROMPTS / "base_prompt.txt").read_text(encoding="utf-8")
    for ph in ("{aspect_ratio}", "{user_input}", "{phong_cach_style}",
               "{kieu_trend_layout}", "{text_style_directive}", "{ngon_ngu_directive}"):
        assert ph in base, f"base_prompt thieu {ph}"


def test_build_prompt_ghep_tu_fragment_khong_hardcode():
    from apps.thumbnail.jobs import build_prompt
    from platform_core import prompt_fragments as pf
    p = build_prompt("chu de test", title="TIEU DE", subtitle="phu de",
                     phong_cach="cinematic", kieu_trend="khuon_mat_cam_xuc",
                     text_style="bold_impact", ngon_ngu="tieng_viet", aspect_ratio="16:9")
    # Ghép đúng: chứa chủ đề + tiêu đề + một mẩu của fragment phong_cach đã chọn.
    assert "chu de test" in p and "TIEU DE" in p
    frag = pf.read_fragment(PROMPTS, "phong_cach", "cinematic")
    assert frag.split("\n")[0][:20] in p
    # Không còn placeholder chưa thay.
    assert "{" not in p and "}" not in p


def test_lua_chon_la_thi_ve_mac_dinh():
    from apps.thumbnail.jobs import build_prompt
    # id bịa → build vẫn chạy (lấy mặc định), không ném.
    p = build_prompt("x", phong_cach="KHONG_TON_TAI")
    assert p and "{" not in p


def test_default_option_la_muc_dau():
    from platform_core import prompt_fragments as pf
    assert pf.default_option(PROMPTS, "phong_cach") == "chuyen_nghiep_toi_gian"
    assert pf.default_option(PROMPTS, "ngon_ngu") == "tieng_viet"


def test_registry_co_it_nhat_3_model_anh_active():
    from platform_core import providers
    from platform_core.models import APIKEY_CAT_IMAGE
    active = [m for m in providers.models_for("gemini", category=APIKEY_CAT_IMAGE) if m.is_active]
    assert len(active) >= 3
    assert any(m.id == "gemini-2.5-flash-image" for m in active)
    assert all(m.label() for m in active)   # có nhãn hiển thị
