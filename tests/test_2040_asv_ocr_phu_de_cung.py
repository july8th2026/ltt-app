"""ASV final — lan ocr: hardsub -> dong thoi gian (logic, khong model).

Khung gia lap DUNG hinh dang ra cua `apps/asv_gpu/do_luong/ocr_khung.py`, mo
phong nhung thu bon clip Douyin nghiem thu co that (L_OCR.md §2): phu de doi
chu o day giua, logo goc tren, watermark giua hinh tinh, HUD la ban can giua
nhung chu nho, ma tran dau o day khung.
"""
from __future__ import annotations

from apps.auto_scan_video import phu_de_cung as pd

W, H = 864, 576


def _dong(chu, x0, y0, x1, y1, diem=0.99):
    return {"hop": [x0, y0, x1, y1], "chu": chu, "diem": diem}


def _khung_douyin(n=40, *, co_phu_de=True):
    ra = []
    for i in range(n):
        dong = [
            _dong("中国", 12, 0, 83, 38),                       # logo goc
            _dong("千奇百战", 380, 215, 500, 258),               # watermark giua, tinh
            _dong(f"{195 + i} 210 西南", 300, 10, 560, 28),     # la ban: giua, doi, NHO
            _dong("15683.0-2X6CGYX", 107, 564, 249, 575),       # ma tran, lech tam
        ]
        if co_phu_de and i % 5 != 4:                            # phu de vang 1/5 khung
            dong.append(_dong(f"第{i // 2}句字幕内容", 250, 515, 610, 564))
        ra.append({"t": float(i), "dong": dong})
    return ra


# ══ 1. Tim dai ══════════════════════════════════════════════════════════════

def test_dai_la_phu_de_KHONG_phai_la_ban_logo_hay_watermark():
    dai = pd.phat_hien_dai(_khung_douyin(), rong=W, cao=H)
    assert dai is not None
    assert dai["y0"] <= 515 and dai["y1"] >= 564
    assert dai["y0"] > 300, "dai phai o phia duoi, khong phai la ban/watermark"
    assert dai["tam_y"] > 0.85


def test_khong_co_phu_de_thi_KHONG_co_dai():
    """Doi chung: cung HUD/logo/watermark, bo phu de ⇒ None (v1 gia dinh cua brief)."""
    assert pd.phat_hien_dai(_khung_douyin(co_phu_de=False), rong=W, cao=H) is None


def test_chu_TINH_can_giua_o_day_khong_phai_phu_de():
    khung = [{"t": float(i), "dong": [_dong("抖音号123", 300, 520, 560, 560)]}
             for i in range(30)]
    assert pd.phat_hien_dai(khung, rong=W, cao=H) is None


def test_diem_thap_bi_loai():
    khung = [{"t": float(i), "dong": [_dong(f"字幕{i}", 300, 520, 560, 560, diem=0.4)]}
             for i in range(30)]
    assert pd.phat_hien_dai(khung, rong=W, cao=H) is None


def test_dau_vao_rong():
    assert pd.phat_hien_dai([], rong=W, cao=H) is None


# ══ 2. Dong thoi gian ═══════════════════════════════════════════════════════

def _khung_dai(chuoi, fps=5.0, y=(515, 564)):
    """`chuoi` = danh sach chu moi khung ('' = khong co chu)."""
    return [{"t": i / fps, "dong": ([_dong(c, 250, y[0], 610, y[1])] if c else [])}
            for i, c in enumerate(chuoi)]


def test_gop_khung_giong_nhau_va_dat_moc_bat_ket():
    k = _khung_dai(["甲乙丙丁"] * 5 + [""] * 3 + ["戊己庚辛"] * 4)
    seg = pd.dung_dong_thoi_gian(k, cao_chu=49, fps=5, thoi_luong=10)
    assert [s["text"] for s in seg] == ["甲乙丙丁", "戊己庚辛"]
    assert seg[0]["start"] == 0.0 and abs(seg[0]["end"] - 1.0) < 1e-6
    assert abs(seg[1]["start"] - 1.6) < 1e-6
    assert all(0 < s["confidence"] <= 1 for s in seg)


def test_OCR_doc_sai_mot_chu_van_la_CUNG_dong_va_lay_bien_the_pho_bien():
    k = _khung_dai(["圆拱形状内部的空间更是相当宽敞"] * 4 + ["圆拱形状内部的空间更是相当宽散"]
                   + ["圆拱形状内部的空间更是相当宽敞"] * 3)
    seg = pd.dung_dong_thoi_gian(k, cao_chu=49, fps=5, thoi_luong=10)
    assert len(seg) == 1 and seg[0]["text"] == "圆拱形状内部的空间更是相当宽敞"


def test_truot_MOT_khung_trong_khong_cat_dong():
    k = _khung_dai(["即使遇到暴风雨"] * 3 + [""] + ["即使遇到暴风雨"] * 3)
    seg = pd.dung_dong_thoi_gian(k, cao_chu=49, fps=5, thoi_luong=10)
    assert len(seg) == 1 and abs(seg[0]["end"] - 1.4) < 1e-6


def test_dong_chi_MOT_khung_bi_bo():
    k = _khung_dai(["甲乙丙丁"] * 4 + ["乱码"] + ["戊己庚辛"] * 4)
    seg = pd.dung_dong_thoi_gian(k, cao_chu=49, fps=5, thoi_luong=10)
    assert "乱码" not in [s["text"] for s in seg]


def test_chu_NHO_trong_dai_bi_bo():
    """Dong bao ha guc cua game (cao 21 px) chen vao dai phu de (34 px) o v3."""
    k = [{"t": i / 5, "dong": [_dong("趁现在赶紧把人补了", 309, 431, 533, 465),
                               _dong("你使用击倒了", 277, 462, 559, 483),
                               _dong("自动", 626, 412, 657, 431)]}
         for i in range(5)]
    seg = pd.dung_dong_thoi_gian(k, cao_chu=31, fps=5, thoi_luong=10, rong=W)
    assert [s["text"] for s in seg] == ["趁现在赶紧把人补了"]


def test_lop_phu_chen_ngang_KHONG_cat_dong_va_chu_lay_ban_NGAN():
    """v3: dong phu de doc `X` roi `X + dong bao`, roi `X` — VAN la mot dong."""
    k = ([{"t": i / 5, "dong": [_dong("把楼给守住", 309, 431, 533, 465)]} for i in range(3)]
         + [{"t": (3 + i) / 5, "dong": [_dong("把楼给守住你使用击倒了小李", 280, 431, 559, 465)]}
            for i in range(2)]
         + [{"t": (5 + i) / 5, "dong": [_dong("把楼给守住", 309, 431, 533, 465)]}
            for i in range(3)])
    seg = pd.dung_dong_thoi_gian(k, cao_chu=34, fps=5, thoi_luong=10, rong=W)
    assert [s["text"] for s in seg] == ["把楼给守住"]
    assert seg[0]["so_khung"] == 8


def test_phu_de_dai_bi_thu_NHO_van_duoc_doc():
    """v2: dong dai bi CapCut thu font (33 px) trong khi trung vi dai la 53 px."""
    k = [{"t": i / 5, "dong": [_dong("圆拱形状内部的空间更是相当宽敞", 129, 523, 737, 556)]}
         for i in range(4)]
    seg = pd.dung_dong_thoi_gian(k, cao_chu=53, fps=5, thoi_luong=10, rong=W)
    assert [s["text"] for s in seg] == ["圆拱形状内部的空间更是相当宽敞"]


def test_phu_de_HAI_hang_ghep_theo_thu_tu_doc():
    k = [{"t": i / 5, "dong": [_dong("第二行", 300, 540, 560, 570),
                               _dong("第一行", 300, 500, 560, 530)]} for i in range(4)]
    seg = pd.dung_dong_thoi_gian(k, cao_chu=30, fps=5, thoi_luong=10)
    assert seg[0]["text"] == "第一行第二行"


def test_watermark_trong_dai_bi_bo():
    k = _khung_dai(["水印"] * 60 + ["真的字幕"] * 5)
    seg = pd.dung_dong_thoi_gian(k, cao_chu=49, fps=5, thoi_luong=13)
    assert [s["text"] for s in seg] == ["真的字幕"]


def test_KHONG_chong_thoi_gian_va_khong_vuot_thoi_luong():
    k = _khung_dai(["甲乙丙丁"] * 3 + ["戊己庚辛"] * 3 + ["壬癸子丑"] * 10)
    seg = pd.dung_dong_thoi_gian(k, cao_chu=49, fps=5, thoi_luong=3.1)
    assert len(seg) == 3
    for a, b in zip(seg, seg[1:], strict=False):  # cap lien ke: do dai lech 1
        assert a["end"] <= b["start"]
    assert seg[-1]["end"] <= 3.1


def test_ti_le_chu_han():
    assert pd.ti_le_chu_han("即使遇到暴风雨") == 1.0
    assert pd.ti_le_chu_han("hello 世界") < 0.5
    assert pd.ti_le_chu_han("123 !!") == 0.0
