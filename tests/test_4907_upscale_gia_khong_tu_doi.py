"""Ghim DAU RA tinh tien cua `upscalevideo` — gia khong duoc tu doi trong im lang.

⭐ VI SAO TEP NAY TON TAI

27/09, mot commit sua *docstring* cua `cost.py` sap ra production. Toi da doi soat
bang cach nap `cost.py` tu CA HAI sha roi so 960 to hop tham so — ket qua: 0 lech.

Nhung phep doi soat do chay bang mot script trong thu muc TAM, roi bien mat. Khi
mot agent khac di kiem lai loi khai "960 to hop", no KHONG TIM THAY gi trong kho
va da noi thang ra dieu do.

⇒ Bai hoc: **mot phep xac minh khong de lai hien vat thi khong kiem toan duoc.**
  Mot cau "toi da kiem roi" trong bao cao co hinh dang giong het mot cau "toi
  nghi la on" — nguoi doc sau khong phan biet duoc.

Nen phep doi soat do bien thanh tep nay: no ghim DAU RA that cho mot ma tran tham
so, nen bat ky thay doi gia nao — co y hay vo tinh — deu lam no DO.

⛔ Tep nay KHONG phan xet gia dung hay sai. No chi bat viec doi gia phai la mot
   hanh dong CO Y: ai doi thi phai sua ca bang duoi day, tuc phai nhin thay minh
   dang doi cai gi.

⚠️ Doi gia la danh doi SAN PHAM (`CLAUDE.md` luat 2). Chu du an chot 27/09: giu
   nguyen gia hien tai, dieu chinh theo thuc te sau. So do lam can cu cho lan
   dieu chinh do nam o `docs/UPSCALE_V2_CORRECTION/08_BENCHMARK_RESULTS.md` §G/§H
   va trong docstring `cost.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# (thoi_luong_s, chieu_cao_dich, preset, preview, stabilize, smooth) -> credit
# Chup ngay 2026-09-27 tu ban DANG CHAY tren production.
MOC = [
    # --- duong thuong ---
    ((106.83, 1080, "fast", False, False, False), 54),
    ((106.83, 1440, "fast", False, False, False), 97),
    ((106.83, 2160, "fast", False, False, False), 214),
    ((106.83, 1080, "quality", False, False, False), 134),
    ((106.83, 2160, "quality", False, False, False), 535),
    ((60.0, 1080, "fast", False, False, False), 30),
    ((600.0, 1080, "fast", False, False, False), 300),
    # --- tinh nang cong them ---
    ((106.83, 1080, "fast", False, True, False), 65),
    ((106.83, 1080, "fast", False, False, True), 118),
    # 1,78050 phut x 30 x (1,2 x 2,2) = 141,0156 -> ceil = 142.
    # ⭐ Moc nay ban dau toi go tay la 141 va phep kiem bat duoc ngay luot
    #    dau — dung viec cua no. Ma DUNG, moc SAI.
    ((106.83, 1080, "fast", False, True, True), 142),
    # --- preview: kep o 8 giay ---
    ((106.83, 1080, "fast", True, False, False), 4),
    ((3600.0, 2160, "quality", True, False, False), 40),
    # --- ca bien ---
    ((0.0, 1080, "fast", False, False, False), 1),          # san MIN_CREDIT
    ((59.9, 1080, "fast", False, False, False), 30),        # lam tron len
    ((106.83, 720, "fast", False, False, False), 54),       # dich ngoai bang -> he so 1.0
    ((106.83, 4320, "fast", False, False, False), 54),      # dich ngoai bang -> he so 1.0
]


@pytest.mark.parametrize("tham_so,credit_cho", MOC)
def test_gia_dung_bang_moc_da_chup(tham_so, credit_cho):
    """Doi so nay = doi so tien khach tra. Phai la hanh dong CO Y.

    Do lam DO: sua `CREDIT_PER_MINUTE`, `_RES_MULT`, `_PRESET_MULT`,
    `_ENHANCEMENT_MULT`, `MIN_CREDIT`, `_PREVIEW_SECONDS`, hoac logic lam tron.
    """
    from apps.upscalevideo import cost

    dur, h, preset, prev, stab, smooth = tham_so
    that = cost.uoc_luong_credit(dur, h, preset, prev, stab, smooth)
    assert that == credit_cho, (
        f"gia DOI cho {tham_so}: moc {credit_cho} -> nay {that}. Neu co y thi cap "
        f"nhat bang MOC trong tep nay VA ghi ly do; neu khong co y thi day la mot "
        f"thay doi gia lot vao ma khong ai dinh lam.")


def test_preset_la_khong_con_thi_tinh_nhu_fast():
    """Duong `.get(..., 1.0)` mac dinh cung la mot phan cua hop dong gia.

    Neu mot preset moi duoc them ma quen them he so, khach se bi tinh nhu `fast`
    — im lang. Phep kiem nay ghi lai hanh vi do la CO Y o thoi diem nay.
    """
    from apps.upscalevideo import cost

    assert cost.he_so_preset("khong_ton_tai") == 1.0
    assert cost.he_so_res(9999) == 1.0


def test_uoc_luong_va_uoc_luong_credit_khop_nhau():
    """Hai cua vao cua cung mot phep tinh khong duoc lech nhau.

    `uoc_luong()` (tra dict cho UI/API) va `uoc_luong_credit()` (tra so) phai cho
    cung con so — neu lech thi UI bao mot gia va so sach ghi mot gia khac.
    """
    from apps.upscalevideo import cost

    for tham_so, _ in MOC:
        dur, h, preset, prev, stab, smooth = tham_so
        d = cost.uoc_luong(dur, h, preset, prev, stab, smooth)
        n = cost.uoc_luong_credit(dur, h, preset, prev, stab, smooth)
        assert d["credit"] == n, f"lech giua uoc_luong() va uoc_luong_credit() o {tham_so}"
        assert d["vnd"] == n * 100
