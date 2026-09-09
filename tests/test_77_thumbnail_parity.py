"""
H-di-tru — Đợt R: khoá tài nguyên prompt của app thumbnail.

Test này là "cổng tài nguyên": ai lỡ xoá một mẩu prompt hoặc quay lại hardcode
prompt trong mã thì đỏ ngay. Cũng khoá "nhà máy" `prompt_fragments`.

🔴 VIẾT LẠI 09/09/2026 — AI CLEAN REBUILD V2 pha 06.3.

   Bản cũ tên là "cổng PARITY với bản gốc BOT GEMINI" và chốt bốn con số lấy từ
   `_labels.json` của kho ấy. Hai nhóm trong bốn — `text_style` (6 kiểu chữ) và
   `ngon_ngu` (5 thứ tiếng) — **chỉ phục vụ chữ vẽ trong ảnh**, thứ mà động cơ
   mới không làm được, nên chúng đã bị gỡ khỏi sản phẩm.

   ⛔ Nên "parity với BOT GEMINI" thôi là một bất biến của app này: nó đo độ
      giống một kho đã hết là nguồn. Cái CÒN là bất biến — và bản này chốt — là:
      **mỗi lựa chọn giao diện chào bán đều phải có một mẩu prompt thật**, và
      **thứ đã gỡ thì gỡ hẳn**. Cả hai đúng với mọi tập lựa chọn, kể cả tập sau.
"""
from __future__ import annotations

import pathlib


PROMPTS = pathlib.Path(__file__).resolve().parent.parent / "apps" / "thumbnail" / "prompts"

#: 🔴 Số của **sản phẩm**, không chép từ `_labels.json`. `kieu_trend` còn 7 chứ
#:    không 9: `listicle_numbered` và `text_heavy_chu_lon` ĐÒI chữ vẽ ra.
EXPECT = {"phong_cach": 11, "kieu_trend": 7}


def test_nhom_lua_chon_cua_san_pham_dung_bang_nhom_co_tai_nguyen():
    """Danh sách app chào bán phải bằng đúng danh sách nhóm được kiểm ở đây.

    ⭐ Chốt chống trôi: thêm một nhóm vào `jobs.NHOM_LUA_CHON` mà quên thêm tài
       nguyên (hoặc ngược lại) thì đỏ, thay vì lặng lẽ chào bán một nhóm rỗng.
    """
    from apps.thumbnail.jobs import NHOM_LUA_CHON
    assert set(NHOM_LUA_CHON) == set(EXPECT)


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


def test_hai_nhom_CHU_da_bi_go_han_khoi_dia():
    """⛔ Gỡ tính năng thì gỡ cả tài nguyên của nó.

    Để lại một thư mục toàn câu *"All text MUST be written in Vietnamese"* cho
    một động cơ không viết được tiếng Việt là để sẵn thứ cho người sau nối lại.
    """
    for nhom in ("text_style", "ngon_ngu"):
        assert not (PROMPTS / nhom).exists(), f"{nhom} van con tren dia"


def test_base_prompt_ton_tai_va_co_placeholder():
    base = (PROMPTS / "base_prompt.txt").read_text(encoding="utf-8")
    for ph in ("{aspect_ratio}", "{user_input}", "{phong_cach_style}",
               "{kieu_trend_layout}"):
        assert ph in base, f"base_prompt thieu {ph}"
    # Bốn chỗ dành cho chữ phải biến mất. `pf.build` KHÔNG ném khi thiếu khoá —
    # nó để nguyên `{...}` trong prompt gửi đi. Sót một cái là gửi rác cho model.
    for ph in ("{text_style_directive}", "{ngon_ngu_directive}",
               "{title_text}", "{subtitle_text}"):
        assert ph not in base, f"base_prompt con {ph}"


def test_base_prompt_CAM_chu_mot_cach_tuong_minh():
    """Không cấm thì model vẽ chữ giả — và chữ giả trông tệ hơn không có chữ."""
    base = (PROMPTS / "base_prompt.txt").read_text(encoding="utf-8").lower()
    assert "no text" in base


def test_build_prompt_ghep_tu_fragment_khong_hardcode():
    from apps.thumbnail.jobs import build_prompt
    from platform_core import prompt_fragments as pf
    p = build_prompt("chu de test", phong_cach="cinematic",
                     kieu_trend="khuon_mat_cam_xuc", aspect_ratio="16:9")
    assert "chu de test" in p
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
    assert pf.default_option(PROMPTS, "kieu_trend") == "khuon_mat_cam_xuc"


def test_bang_chon_model_cua_app_co_hang_de_ban():
    """Bảng chọn model không được rỗng, và nhà cung cấp của nó phải CÒN phục vụ.

    🔴 Bản cũ chốt *"gemini có ít nhất 3 model ảnh active"*. Nhà cung cấp ấy đã
       ngừng ở pha 04, nên câu hỏi đúng nay là về **cửa hàng của app này** chứ
       không về một hãng cụ thể.
    """
    from apps.thumbnail.routes import _PROVIDER, _models
    from platform_core import providers

    assert not providers.da_ngung(_PROVIDER), f"{_PROVIDER} da ngung phuc vu"
    ds = _models()
    assert ds, "khong con model nao de ban"
    assert all(label for _id, label in ds)
