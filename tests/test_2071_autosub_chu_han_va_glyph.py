"""asv-final lan phu-de — MO RONG `apps/autosubvideo` cho chu Han: ngat dong,
karaoke tung chu, va hoi glyph THAT cua font.

🔑 Ba nang luc nay nam o APP CHU (khai o `BE_MAT_CONG_KHAI` + `lint_app_contract`)
   chu khong chep sang Auto Scan — AutoSub huong cung luc.

⛔ Duong chu co dau cach (tieng Viet/Anh) phai giu NGUYEN tung byte: mot doi
   ngam o day doi phu de cua moi khach AutoSub dang dung.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))

from apps.autosubvideo import BE_MAT_CONG_KHAI, ass_builder, font_checker, segmenter  # noqa: E402
from apps.autosubvideo.segmenter import SubtitleEvent  # noqa: E402

#: Dong hardsub that cua clip v1 (`Desktop\TEST VIDEO`), 30 chu Han.
HAN = "从屠宰场运送过来的牛肠还带着温热，清洗牛肠才是最关键的一步想要牛肠好吃"


# ══ Ngat dong ═══════════════════════════════════════════════════════════════

def test_chu_Han_KHONG_con_la_mot_dong_dai_vo_han():
    """Doi chung: ban cu (`_wrap_text`) tra MOT dong cho cau khong dau cach."""
    assert len(segmenter._wrap_text(HAN, 42, 2)) == 1           # loi cu, do duoc
    dong = segmenter.wrap_lines(HAN, 42, 2)
    assert len(dong) == 2
    assert "".join(dong) == HAN                                  # khong mat, khong them
    assert all(segmenter.display_width(d) <= 42 for d in dong[:-1])


def test_can_bang_hai_dong_va_khong_mo_dong_bang_dau_phay():
    dong = segmenter.wrap_lines("从屠宰场运送过来的牛肠还带着温热，清洗牛肠才是最关键的一步", 42, 2)
    assert len(dong) == 2
    assert not dong[1].startswith("，")
    assert abs(segmenter.display_width(dong[0]) - segmenter.display_width(dong[1])) <= 4


def test_tron_Han_va_Latin_giu_dau_cach_that():
    s = "我们用 GPU 渲染 video 字幕"
    units = segmenter.split_units(s)
    assert segmenter._join_units(units) == s


@pytest.mark.parametrize("s", [
    "Lòng bò chở từ lò mổ về vẫn còn ấm, và rửa sạch mới là bước quan trọng nhất",
    "The tripe arrives from the slaughterhouse still warm and cleaning it matters",
    "ngắn",
])
def test_duong_co_dau_cach_giu_NGUYEN_tung_byte(s):
    assert segmenter.wrap_lines(s, 42, 2) == segmenter._wrap_text(s, 42, 2)


def test_segment_cua_autosub_huong_luon():
    ev = segmenter.segment([{"start": 0.0, "end": 4.0, "text": HAN}],
                           segmenter.SegmentConfig(mode="sentence"))
    assert all(e.line_count <= 2 for e in ev)
    assert any("\\N" in e.display_text for e in ev)


# ══ Karaoke tung chu Han ═══════════════════════════════════════════════════

def test_karaoke_word_co_the_kf_cho_TUNG_chu_Han():
    """🔴 Ban cu tach theo dau cach -> mot 'tu' -> tra ve KHONG the nao: che do
    `word` im lang khong lam gi tren phu de tieng Trung."""
    ev = SubtitleEvent(start=0, end=3, text="想要牛肠好吃", display_text="想要牛肠好吃")
    ra = ass_builder._apply_highlight(ev, "word", "#FFD700")
    assert ra.count("\\kf") == 6
    assert ra.replace("{\\kf50}", "") == "想要牛肠好吃"


def test_karaoke_Latin_KHONG_doi():
    ev = SubtitleEvent(start=0, end=2, text="xin chao ban", display_text="xin chao ban")
    assert ass_builder._apply_highlight(ev, "word", "#FFD700") == \
        "{\\kf66}xin {\\kf66}chao {\\kf66}ban"


# ══ Glyph that cua font ═════════════════════════════════════════════════════

# ⛔ KHONG skipif: render chay tren chinh may A (Windows). Thieu Arial/YaHei o day
#    la thieu glyph o ban ra that — phai DO, khong duoc bo qua.

def test_Arial_ve_du_tieng_Viet_nhung_THIEU_chu_Han():
    assert font_checker.missing_glyphs("Arial", "Lòng bò ấm, rửa sạch — Đ ữ ỹ") == ""
    thieu = font_checker.missing_glyphs("Arial", "想要牛肠")
    assert thieu == "想要牛肠"


def test_YaHei_ve_du_chu_Han():
    assert font_checker.missing_glyphs("Microsoft YaHei", HAN) == ""


def test_font_khong_ton_tai_la_KHONG_BIET_chu_khong_phai_du():
    assert font_checker.missing_glyphs("Font-Khong-Bao-Gio-Co-2070", "abc") is None


def test_asv_glyph_thieu_lui_qua_danh_sach_du_phong():
    from apps.auto_scan_video import phu_de

    ho = phu_de.chuan_hoa({"che_do": "nguon"})
    assert phu_de.glyph_thieu(ho, [{"text": HAN + " Lòng bò"}]) == ""
    # Ky tu ngoai moi font du phong (Linear B) -> bao ra, khong nuot
    assert phu_de.glyph_thieu(ho, [{"text": "\U00010000"}]) == "\U00010000"


# ══ Be mat lien-app: khai CA HAI phia ═══════════════════════════════════════

@pytest.mark.parametrize("ten", [("apps.autosubvideo.segmenter", "wrap_lines"),
                                 ("apps.autosubvideo.font_checker", "missing_glyphs")])
def test_nang_luc_moi_khai_o_ca_hai_phia(ten):
    assert ten in BE_MAT_CONG_KHAI
    sys.path.insert(0, str(GOC / "tools"))
    import lint_app_contract as lac
    assert ten in lac.APP_DUOC_DUNG_APP[("auto_scan_video", "autosubvideo")]
