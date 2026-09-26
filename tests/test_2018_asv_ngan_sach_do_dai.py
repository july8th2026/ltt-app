"""R-04 — NGAN SACH DO DAI cua mot cau long tieng, va DONG HO cua giai doan GIONG.

Luot nghiem thu nen v3 (23/09) do duoc `voice_synthesis` = 943 giay cho mot phim
107 giay. `tools/do_toc_do_giong.py` tach con so ay lam hai va chi ra nguyen nhan
o dau chuoi — chi tiet + so lieu: `docs/auto_scan_video_final/L_FIX_TOC_DO.md`.

Bon cua, moi cua mot cau hoi:

  §1 `ngon_ngu.NHIP`              — nhip doc la MOT con so DO DUOC, moi noi tinh ra tu no
  §2 `ngan_sach_do_dai`           — tran DEM DUOC, khong phai mot phep nhan giao cho model
  §3 loi nhac mang tran do        — ca pha VIET DAU lan pha NAN, cung mot nguon
  §4 `giai_doan_giong` co dong ho — "cham vi cai gi" tra loi duoc tu bang chung cua luot

⛔ Khong phep kiem nao o day goi model hay may sinh tieng that.
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (ai, giai_doan_giong, long_tieng,  # noqa: E402
                                  nan_cho_vua, ngon_ngu as nn)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Nhip doc: MOT con so, moi cum tinh ra tu no
# ══════════════════════════════════════════════════════════════════════════════

def test_nhip_phu_kin_moi_dich_hop_le():
    """Mot dich khong co nhip = mot dich khong tinh duoc ngan sach do dai."""
    for m in nn.DICH_HOP_LE:
        assert m in nn.NHIP and nn.NHIP[m] > 0
        assert m in nn.DON_VI_DO_DAI


def test_cum_loi_nhac_TINH_RA_tu_NHIP_chu_khong_go_tay():
    """🔴 Tai hien nguyen nhan goc cua R-04.

    Truoc 23/09 `CUM[vi]["nhip"]` la chuoi `"khoang 4,5 am tiet/giay"` go tay,
    va khong con so nao ben canh no. Nen khi phep do that cho ra 3,35 thi khong
    co cho nao de sua **mot lan**: chuoi nam o `CUM`, phep nhan nam trong dau
    model, va khong ai doi chieu hai thu do.
    """
    for m in nn.DICH_HOP_LE:
        n = f"{nn.NHIP[m]:.2f}".rstrip("0").rstrip(".").replace(".", ",")
        assert nn.CUM[m]["nhip"] == f"khoang {n} {nn.DON_VI_DO_DAI[m]}/giay"
        assert nn.CUM[m]["nhip_moi_giay"] == \
            f"khoang {n} {nn.DON_VI_DO_DAI[m]} moi giay"


def test_nhip_vi_la_so_DA_DO_khong_phai_4_5():
    """⛔ Banh coc: khong duoc quay ve con so chua do.

    3,35 am tiet/giay — `tools/do_toc_do_giong.py --che-do tts`, hai vong tren
    sau doan tieng Viet that cua luot nen v3, giong `Minh Duc`:
    trung binh 3,349 va 3,324; bien 3,04-3,51.
    """
    assert nn.NHIP["vi"] == pytest.approx(3.35)


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Tran DEM DUOC
# ══════════════════════════════════════════════════════════════════════════════

def test_ngan_sach_do_dai_la_so_nguyen_duong_va_TANG_theo_khe():
    assert nn.ngan_sach_do_dai(19.879, "vi") == 61
    assert nn.ngan_sach_do_dai(4.553, "vi") == 14
    assert nn.ngan_sach_do_dai(0.0, "vi") >= 1
    truoc = 0
    for giay in (1, 5, 10, 30, 60):
        n = nn.ngan_sach_do_dai(giay, "vi")
        assert isinstance(n, int) and n > truoc
        truoc = n


def test_ngan_sach_NHAM_THAP_hon_khe_va_he_so_o_MOT_cho():
    """`HE_SO_MUC_TIEU` la nguon duy nhat — `nan_cho_vua` khong go lai 0,92."""
    assert 0.8 <= nn.HE_SO_MUC_TIEU < 1.0
    assert nn.ngan_sach_do_dai(10.0, "vi") < round(10.0 * nn.NHIP["vi"])
    ma = inspect.getsource(nan_cho_vua.loi_nhac_nan)
    assert "ngon_ngu.HE_SO_MUC_TIEU" in ma
    assert "* 0.92" not in ma and "*0.92" not in ma


def test_ngan_sach_tu_choi_dich_ngoai_hop_dong():
    with pytest.raises(nn.NgonNguError):
        nn.ngan_sach_do_dai(5.0, "ja")


def test_bien_do_DO_DUOC_cua_may_sinh_tieng_NAM_TRONG_dung_sai():
    """🔑 Vi sao he so la 0,92 chu khong phai 1,0 — va no kiem duoc.

    Nhip do duoc bien thien 3,04-3,51 am tiet/giay. Mot cau viet dung ngan sach
    (`NHIP x HE_SO_MUC_TIEU`) doc o hai dau bien do deu phai con nam trong dung
    sai cua `nan_cho_vua` — neu khong, bac thang nan lai chay o **moi** doan y
    het truoc 23/09.
    """
    khe = 20.0
    n = nn.ngan_sach_do_dai(khe, "vi")
    for nhip_that in (3.04, 3.51):
        giay = n / nhip_that
        assert not nan_cho_vua.can_nan(giay, khe), (
            f"nhip that {nhip_that} -> {giay:.2f}s cho khe {khe}s: van phai nan")


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Loi nhac mang tran — CA HAI pha
# ══════════════════════════════════════════════════════════════════════════════

def _than(msg) -> tuple[str, dict]:
    return msg[0]["content"], json.loads(msg[1]["content"])


def test_loi_nhac_VIET_DAU_mang_tran_dem_duoc_cho_TUNG_doan():
    d = [{"ma": "a", "chu": "x", "bat": 0.0, "ket": 19.879},
         {"ma": "b", "chu": "y", "bat": 19.879, "ket": 24.432}]
    he_thong, nguoi_dung = _than(
        long_tieng.loi_nhac(d, tat_ca=d, ngon_ngu_goc="zh", dac_diem_giong={}))
    assert "do_dai_toi_da" in he_thong and "am tiet" in he_thong
    theo_ma = {m["ma"]: m for m in nguoi_dung["doan"]}
    assert theo_ma["a"]["do_dai_toi_da"] == nn.ngan_sach_do_dai(19.879, "vi")
    assert theo_ma["b"]["do_dai_toi_da"] == nn.ngan_sach_do_dai(4.553, "vi")


def test_loi_nhac_NAN_mang_CUNG_tran_voi_pha_viet_dau():
    """Hai pha nham hai dich khac nhau tren cung mot khe thi vong hai khong hoi tu."""
    khe = 13.818
    he_thong, nguoi_dung = _than(nan_cho_vua.loi_nhac_nan(
        {"ma": "a", "goc": "x"}, chu_hien_tai="y", giay_do_duoc=18.0, khe=khe))
    assert "do_dai_toi_da" in he_thong
    assert nguoi_dung["do_dai_toi_da"] == nn.ngan_sach_do_dai(khe, "vi")
    assert nguoi_dung["muc_tieu_giay"] == round(khe * nn.HE_SO_MUC_TIEU, 2)


def test_loi_nhac_en_KHONG_mang_don_vi_tieng_Viet():
    d = [{"ma": "a", "chu": "x", "bat": 0.0, "ket": 10.0}]
    he_thong, nguoi_dung = _than(long_tieng.loi_nhac(
        d, tat_ca=d, ngon_ngu_goc="zh", dac_diem_giong={}, ngon_ngu_dich="en"))
    assert "am tiet" not in he_thong and " tu" in he_thong
    assert nguoi_dung["doan"][0]["do_dai_toi_da"] == \
        nn.ngan_sach_do_dai(10.0, "en")


def test_doi_tran_do_dai_lam_DOI_VAN_TAY_ban_long_tieng():
    """⛔ Doi loi nhac ma giu van tay = lan chay sau dung lai ban cua loi nhac cu."""
    assert long_tieng.PHIEN_BAN_LONG_TIENG >= 2
    assert nan_cho_vua.PHIEN_BAN_NAN >= 2


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Dong ho cua giai doan GIONG + muc suy nghi cua thao tac NAN
# ══════════════════════════════════════════════════════════════════════════════

def test_giai_doan_giong_GHI_giay_TTS_va_giay_LLM_rieng():
    """Luot nen v3 chi biet TONG (943 giay) — phai do lai ngoai san pham moi
    biet 751 giay la LLM. Hai con so nay lam cau do khong phai hoi lan hai."""
    ma = inspect.getsource(giai_doan_giong.chay)
    assert '"giay_tts"' in ma and '"giay_llm_nan"' in ma
    assert "time.monotonic()" in ma


def test_thao_tac_NAN_khai_muc_suy_nghi_THAP():
    """🔑 `rut_ngan_cho_vua` la thao tac de nhat trong nam; do duoc 68,3 giay/luot
    o `medium` va 47,7 o `low` (cung 6/6 `stop`, cung 6/6 cau ngan hon)."""
    assert ai.RUT_NGAN_CHO_VUA.muc_nghi == "low"
    # ⛔ `none` bi `ltt_llm` tu choi tu 14/09 — khong thao tac nao duoc khai no.
    assert all(t.muc_nghi != "none" for t in ai.THAO_TAC)


def test_ai_goi_TRUYEN_muc_nghi_cua_thao_tac_xuong_dieu_phoi():
    ma = inspect.getsource(ai.goi)
    assert "reasoning_effort" in ma and "thao_tac.muc_nghi" in ma


# ══════════════════════════════════════════════════════════════════════════════
#  §5  `thoi_gian.ngan_sach_nan_s` — MOT nguon cho ngan sach BAC THANG NAN
# ══════════════════════════════════════════════════════════════════════════════

def test_ngan_sach_nan_khong_co_khoang_lang_thi_BANG_khe():
    from apps.auto_scan_video.thoi_gian import ngan_sach_nan_s
    assert ngan_sach_nan_s(3.0, 3.0) == 3.0


def test_ngan_sach_nan_muon_DUNG_ty_le_da_khai():
    from apps.auto_scan_video import thoi_gian as tg
    # khe 3,0 s · toi moc sau 4,0 s => khoang lang 1,0 s
    ra = tg.ngan_sach_nan_s(3.0, 4.0)
    assert abs(ra - (3.0 + 1.0 * tg.TY_LE_MUON_KHOANG_LANG)) < 1e-9


def test_ngan_sach_nan_KHONG_BAO_GIO_nho_hon_khe():
    """Du lieu hong (`moc_sau` < `ket`) khong duoc lam ngan sach teo lai."""
    from apps.auto_scan_video.thoi_gian import ngan_sach_nan_s
    assert ngan_sach_nan_s(3.0, 1.0) == 3.0
