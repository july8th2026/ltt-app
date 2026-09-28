"""B13 E3 — ngan sach cua `ke_cat.chon` phai do bang HOP cac khoang da nhan,
⛔ khong bang TONG do dai tung ung vien.

Bay: cong thang `dai` cua hai ung vien CHONG NHAU dem MOT vung hai lan ⇒ ngan
sach dong SOM va `vuot_tran` oan cho mot ung vien von vua. Kho tham chieu
`C:\\Cut_only ver2\\nerf_engine\\stages\\select.py` tu to giac dung bay nay:
*"counting overlapping chunks twice, which makes the selector stop early"*.

Hom nay (28/09) loi CHUA no vi moi canh sinh MOT ung vien (khong chong nhau) —
nen bai nay phai TU DUNG mot ca chong nhau, khong doc duoc tu du lieu hien co.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import ke_cat as kc


def _uv(bat, ket, diem=0.9):
    return kc.UngVien(bat=bat, ket=ket, diem_kem=diem, ly_do_cat="chat_luong_kem")


# ══════════════════════════════════════════════════════════════════════════════
#  Ca CHONG NHAU dung ra bay TONG — dung o day de "chua no" khong lam bai xanh gia
# ══════════════════════════════════════════════════════════════════════════════

def test_hai_ung_vien_CHONG_NHAU__ngan_sach_do_bang_HOP_khong_dong_som():
    """Video 100 s, tran mac dinh 5% => ngan sach 5,0 s.

    uv1 [0;3)  dai 3   diem 0,9
    uv2 [1;4)  dai 3   diem 0,9   (CHONG len uv1 tren [1;3))

    TONG = 3 + 3 = 6 > 5  => (bay CU) uv2 bi loai `vuot_tran` OAN.
    HOP  = do dai [0;4) = 4 <= 5  => (dung) CA HAI duoc nhan.
    """
    tl = 100.0
    ke = kc.chon([_uv(0.0, 3.0), _uv(1.0, 4.0)], thoi_luong=tl)

    # ── Ca hai duoc nhan, gop lai thanh MOT khoang lien tuc ─────────────────
    assert ke.cat == ((0.0, 4.0),)
    assert ke.bo_qua == ()   # ⛔ khong vuot_tran oan

    # ── Ngan sach da dung: HOP = 4,0 s, ⛔ khong phai TONG = 6,0 s ───────────
    assert ke.giay_cat == pytest.approx(4.0)
    assert ke.ti_le_cat == pytest.approx(0.04)
    assert ke.ti_le_cat <= kc.TRAN_CAT_TI_LE


def test_ba_ung_vien_chong_nhau_xep_tang__ngan_sach_van_do_bang_HOP():
    """3 ung vien chong len nhau tung doi mot: [0;3) [2;5) [4;7) -> hop [0;7).

    TONG = 9 s > ngan sach 5 s (bay CU se loai it nhat mot ung vien oan).
    HOP  = 7 s > ngan sach 5 s -> DUNG van phai tu choi bot, nhung con so dung
    de so sanh la 7 (hop), khong phai 9 (tong).
    """
    tl = 100.0
    ke = kc.chon([_uv(0.0, 3.0, diem=0.95), _uv(2.0, 5.0, diem=0.90),
                 _uv(4.0, 7.0, diem=0.85)], thoi_luong=tl)

    # uv1 (diem cao nhat) luon vao truoc: hop rieng no = 3 <= 5 -> nhan.
    # uv2: hop({uv1,uv2}) = do dai [0;5) = 5 <= 5 -> nhan.
    # uv3: hop({uv1,uv2,uv3}) = do dai [0;7) = 7 > 5 -> TU CHOI, ⛔ khong phai vi
    #      TONG (3+3+3=9) ma vi HOP that su vuot (7 > 5).
    assert ke.cat == ((0.0, 5.0),)
    assert [x["bat"] for x in ke.bo_qua] == [4.0]
    assert [x["ly_do"] for x in ke.bo_qua] == [kc.LY_DO_VUOT_TRAN]
    assert ke.giay_cat == pytest.approx(5.0)
    assert ke.ti_le_cat == pytest.approx(0.05)


def test_khong_chong_nhau__HOP_bang_TONG__hanh_vi_cu_khong_doi():
    """Hom nay (moi canh mot ung vien, khong chong nhau) HOP == TONG, nen phep
    vua khong duoc lam doi ket qua cua bai `test_4800` (tran, khong chong nhau).
    """
    tl = 1000.0
    ung_vien = [_uv(i * 30.0, i * 30.0 + 10.0) for i in range(30)]
    ke = kc.chon(ung_vien, thoi_luong=tl)
    assert ke.giay_cat == pytest.approx(50.0)
    assert ke.ti_le_cat == pytest.approx(0.05)
    vuot = [x for x in ke.bo_qua if x["ly_do"] == kc.LY_DO_VUOT_TRAN]
    assert len(vuot) == 25


# ══════════════════════════════════════════════════════════════════════════════
#  `giay_cat`/`ti_le_cat` trong outputs phai noi CUNG mot dai luong voi phan
#  vua PHAN QUYET (E3 §3, "⚠️")
# ══════════════════════════════════════════════════════════════════════════════

def test_tom_tat_giay_cat_la_HOP_cua_cac_khoang_da_nhan__khong_phai_tong_uv():
    tl = 100.0
    ke = kc.chon([_uv(0.0, 3.0), _uv(1.0, 4.0)], thoi_luong=tl)
    tt = kc.tom_tat(ke)
    # ⭐ 4,0 (hop), ⛔ khong phai 6,0 (tong do dai hai ung vien).
    assert tt["giay_cat"] == pytest.approx(4.0)
    assert tt["ti_le_cat"] == pytest.approx(0.04)
    assert tt["dung_o_tran"] is False
    assert tt["so_bo_qua"][kc.LY_DO_VUOT_TRAN] == 0


def test_do_dai_hop_noi_bo_dung_lai_boi_ca_ngan_sach_lan_bao_cao():
    """`_do_dai_hop` la MOT ham, dung cho ca cong ngan sach (`chon`) lan bao cao
    (`KeCat.giay_cat` qua `_gop`) — kiem no khong lech nhau tren cung du lieu."""
    khoang = [(0.0, 3.0), (1.0, 4.0), (10.0, 12.0)]
    assert kc._do_dai_hop(khoang) == pytest.approx(6.0)   # [0;4) + [10;12)
    ke = kc.KeCat(cat=kc._gop(tuple(sorted(khoang))), thoi_luong=100.0)
    assert ke.giay_cat == pytest.approx(kc._do_dai_hop(khoang))
