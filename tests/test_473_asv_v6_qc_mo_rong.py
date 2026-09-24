"""ASV V6 pha 27 — QC mo rong: T14 chinh sach render · T15 bien phu de · T16 lech tieng-hinh.

🔴 **Moi bai o day canh mot phep kiem CHAN DUOC mot lan chay.**
   `giai_doan_qc` doc `muc_hong` roi nem `QcChan`, nen mot muc `HONG` sai la mot
   video da render xong bi tu choi giao. Vi the tep nay chot **hai chieu** cho
   moi nguong:

     · ca tren nguong  -> phai DO   (phep kiem co tac dung)
     · ca duoi nguong  -> phai XANH (phep kiem khong bao oan)

   Chi chot mot chieu la de ngo dung cai hong dat gia hon:
   `phep-do-lech-chieu-phai-bo-khong-phai-sua` — sai so day ve phia HANH DONG
   thi khong co ban sua.

⭐ Nguong `LECH_TIENG_HINH_S` khong phai so muon: do 11/09 bang chinh
   `ket_xuat.dung_lenh` tren ca hai duong render, gom nhip le 29,97 — lech te
   nhat 0,0206 s. Bang chung o `PHA27_QC_MO_RONG.md`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import che_do_render as cdr, qc

D, H, N = qc.DAT, qc.HONG, qc.KHONG_AP_DUNG

NGUON = {"co_video": True, "co_tieng": True, "thoi_luong": 10.0,
         "codec_video": "h264", "rong": 1920, "cao": 1080, "xoay": 0}
RA = dict(NGUON, thoi_luong_video=10.0, thoi_luong_tieng=10.0)

CHUNG = dict(
    tt_nguon=NGUON, am_luong={"lufs": -14.0, "dinh_that": -2.0},
    ke_hoach={"doan": [{"ma": "s1", "dai_ms": 2000, "dat_tai_ms": 0,
                        "he_so_toc": 1.0}], "tong_ms": 10000},
    ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "v/s1.wav"}]},
    thoi_luong_mong_doi=10.0,
    hinh_ra={"den_s": 0.0, "dong_s": 0.0, "so_loi_giai_ma": 0, "ma_thoat": 0},
    hinh_nguon={"den_s": 0.0, "dong_s": 0.0, "so_loi_giai_ma": 0, "ma_thoat": 0})


def _bc(**kw):
    return qc.kiem(**{**CHUNG, "tt_ra": RA,
                      "che_do_render": cdr.CAT_MA_HOA_LAI, **kw})


def _tt(bao_cao, ma):
    return next(m for m in bao_cao["muc"] if m["ma"] == ma)["trang_thai"]


def _so(bao_cao, ma, khoa):
    return next(m for m in bao_cao["muc"] if m["ma"] == ma).get(khoa)


def _pd(*cap):
    return {"phu_de": {"che_do": "tu_dong",
                       "su_kien": [{"start": a, "end": b} for a, b in cap]}}


# ══ T14 — chinh sach render ═════════════════════════════════════════════════

def test_T14_preset_giu_hinh_khop_thi_DAT():
    assert _tt(_bc(che_do_render=cdr.SAO_CHEP), "T14") == D


@pytest.mark.parametrize("doi", [
    {"codec_video": "hevc"},
    {"rong": 1280, "cao": 720},
    {"xoay": 90},
])
def test_T14_preset_giu_hinh_ma_luong_hinh_DOI_thi_HONG(doi):
    """🔴 `-c:v copy` cho byte hinh di thang tu nguon sang tep ra — no **khong
       the** doi bo ma hoa, kich thuoc hay goc xoay. Mot trong ba doi nghia la
       loi hua cua preset da bi pha, va truoc pha 27 khong ai kiem dieu do khi
       T3 khong bam duoc luong hinh.
    """
    bc = _bc(tt_ra=dict(RA, **doi), che_do_render=cdr.SAO_CHEP)
    assert _tt(bc, "T14") == H
    assert _so(bc, "T14", "lech"), "bao HONG ma khong noi truong nao lech"


def test_T14_duong_CAT_khong_ap_dung():
    """⭐ Duong cat CO QUYEN ma hoa lai — do la muc dich cua no. So o day la
       chot mot dieu ta co y khong lam, y het ly do T3 tu bo qua o duong nay.
    """
    assert _tt(_bc(che_do_render=cdr.CAT_MA_HOA_LAI), "T14") == N


def test_T14_thieu_du_lieu_thi_KHONG_AP_DUNG_chu_khong_HONG():
    """⛔ Mot truong vang mat la mot truong ffprobe khong doc duoc — **khong
       phai** mot truong da doi. Bao HONG o day la tu choi giao mot video hoan
       toan binh thuong.
    """
    trong = dict(RA, codec_video="", rong=0, cao=0, xoay=0)
    assert _tt(_bc(tt_ra=trong, che_do_render=cdr.SAO_CHEP), "T14") == N


def test_T14_chi_so_nhung_truong_CA_HAI_ben_deu_khai():
    """Nguon thieu `xoay` thi truong do bi bo qua, ba truong con lai van so."""
    nguon = {k: v for k, v in NGUON.items() if k != "xoay"}
    bc = qc.kiem(**{**CHUNG, "tt_nguon": nguon, "tt_ra": RA,
                    "che_do_render": cdr.SAO_CHEP})
    assert _tt(bc, "T14") == D
    assert _so(bc, "T14", "so_truong_da_so_sanh") == 3


# ══ T15 — bien phu de ═══════════════════════════════════════════════════════

def test_T15_moi_dong_nam_trong_ban_ra_thi_DAT():
    assert _tt(_bc(ban_hinh=_pd((0.0, 3.0), (4.0, 9.5))), "T15") == D


def test_T15_dong_vuot_qua_cuoi_ban_ra_thi_HONG():
    """🔴 Mot dong phu de dat qua cuoi ban ra la mot dong **khong ai thay**.

    Khach tra tien cho phu de, tep `.ass` hop le, ffmpeg khong bao gi, va dong
    chu do khong bao gio hien ra — dung hinh dang *tinh nang khong ton tai*.
    """
    bc = _bc(ban_hinh=_pd((0.0, 3.0), (12.0, 14.0)))
    assert _tt(bc, "T15") == H
    ngoai = _so(bc, "T15", "ngoai_bien")
    assert ngoai and ngoai[0]["i"] == 1, ngoai


def test_T15_dong_xuoi_nguoc_thi_HONG():
    assert _tt(_bc(ban_hinh=_pd((5.0, 2.0))), "T15") == H


def test_T15_dong_ket_dung_o_CUOI_ban_ra_van_DAT():
    """⚠️ Chieu con lai cua nguong. Mot dong ket dung o giay cuoi la binh
       thuong — bao hong o do la tu choi giao mot video dung.
    """
    assert _tt(_bc(ban_hinh=_pd((8.0, 10.0))), "T15") == D
    # va trong dung sai da do sai lech thoi luong cua `kiem_tep_ra`
    assert _tt(_bc(ban_hinh=_pd((8.0, 10.4))), "T15") == D


def test_T15_chong_lan_duoc_DEM_chu_khong_bi_danh_truot():
    """⭐ `ass_builder` xep chong duoc, va mot ban karaoke co the co hai dong
       cung luc. Dem de nguoi doc bao cao thay — khong de chan lan chay.
    """
    bc = _bc(ban_hinh=_pd((0.0, 5.0), (3.0, 8.0)))
    assert _tt(bc, "T15") == D
    assert _so(bc, "T15", "so_chong_lan") == 1


def test_T15_khong_phu_de_thi_KHONG_AP_DUNG():
    assert _tt(_bc(ban_hinh={}), "T15") == N
    assert _tt(_bc(ban_hinh=None), "T15") == N
    assert _tt(_bc(ban_hinh={"phu_de": {"che_do": "tat"}}), "T15") == N


# ══ T16 — lech tieng-hinh ═══════════════════════════════════════════════════

def test_T16_bang_nhau_thi_DAT():
    assert _tt(_bc(), "T16") == D


def test_T16_lech_DA_DO_tren_chuoi_lenh_that_van_DAT():
    """⭐ 0,0206 s la muc te nhat do duoc tren `ket_xuat.dung_lenh` (nhip 29,97).
       Neu nguong bi siet xuong duoi con so nay thi MOI lan chay 29,97 fps se bi
       tu choi giao — mot phep kiem lech chieu ve phia HANH DONG.
    """
    assert _tt(_bc(tt_ra=dict(RA, thoi_luong_tieng=10.0 - 0.0206)), "T16") == D


def test_T16_lech_ngay_DUOI_nguong_van_DAT():
    duoi = qc.LECH_TIENG_HINH_S - 0.01
    assert _tt(_bc(tt_ra=dict(RA, thoi_luong_tieng=10.0 - duoi)), "T16") == D


def test_T16_lech_TREN_nguong_thi_HONG():
    tren = qc.LECH_TIENG_HINH_S + 0.01
    bc = _bc(tt_ra=dict(RA, thoi_luong_tieng=10.0 - tren))
    assert _tt(bc, "T16") == H
    assert _so(bc, "T16", "lech") == pytest.approx(tren, abs=1e-3)


def test_T16_nguong_du_dia_it_nhat_MUOI_LAN_muc_da_do():
    """🔑 Chot chinh CON SO, khong chi chot hanh vi.

    Muc te nhat do duoc la 0,0206 s. Mot ban sua sau nay siet nguong xuong
    0,05 s se van lam moi bai tren xanh — nhung no dua nguong toi sat vung
    nhieu that, va lan chay 29,97 fps dau tien gap them mot nguon nhieu se bi
    tu choi giao.
    """
    assert qc.LECH_TIENG_HINH_S >= 0.0206 * 10


def test_T16_luong_khong_khai_duration_thi_KHONG_AP_DUNG():
    """⚠️ MP4 duoc phep khong khai `duration` o tung luong. `None` KHONG phai
       `0` — doan bang `0` se bien mot tep binh thuong thanh bao cao hong.
    """
    trong = dict(RA, thoi_luong_video=None, thoi_luong_tieng=None)
    assert _tt(_bc(tt_ra=trong), "T16") == N
    assert _tt(_bc(tt_ra=dict(RA, thoi_luong_tieng=None)), "T16") == N


# ══ Rang buoc chung ═════════════════════════════════════════════════════════

def test_ba_muc_moi_KHONG_lam_do_mot_lan_chay_binh_thuong():
    """🔴 Bai quan trong nhat cua tep nay.

    Ba phep kiem moi deu chan duoc mot lan chay. Mot lan chay hoan toan binh
    thuong phai di qua ca ba ma khong mot muc HONG nao — neu khong, pha 27 vua
    them ba cach moi de tu choi giao mot video dung.
    """
    for cach in (cdr.SAO_CHEP, cdr.CAT_MA_HOA_LAI):
        bc = _bc(che_do_render=cach, ban_hinh=_pd((0.0, 3.0), (4.0, 9.5)))
        for ma in ("T14", "T15", "T16"):
            assert _tt(bc, ma) != H, (cach, ma, bc["muc_hong"])


def test_phien_ban_QC_da_len_3():
    """🔑 Thieu buoc nay thi mot lan chay lai dung lai bao cao QC cu tu cache —
       bao cao do mot bo luat **chua biet ba muc nay ton tai** lam ra.
    """
    assert qc.PHIEN_BAN_QC >= 3


def test_giai_doan_qc_CO_truyen_ban_hinh():
    """⛔ `nang-luc-co-nhung-khong-ai-di-tren-duong`: khong truyen thi T14/T15
       luon tra `KHONG_AP_DUNG` — mot phep kiem ton tai ma khong ai di qua, va
       moi bai tren van xanh.
    """
    import ast

    goc = Path(__file__).resolve().parents[1]
    cay = ast.parse((goc / "apps/auto_scan_video/giai_doan_qc.py")
                    .read_text(encoding="utf-8"))
    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute) and n.func.attr == "kiem"]
    assert goi, "khong tim thay loi goi `qc.kiem`"
    ten = {k.arg for g in goi for k in g.keywords}
    assert "ban_hinh" in ten, sorted(ten)


def test_soi_bao_do_dai_TUNG_LUONG():
    """T16 doc hai truong nay; thieu chung thi no luon `KHONG_AP_DUNG`."""
    import ast

    goc = Path(__file__).resolve().parents[1]
    van = (goc / "apps/auto_scan_video/nhap_media.py").read_text(encoding="utf-8")
    assert '"thoi_luong_video"' in van and '"thoi_luong_tieng"' in van
    ast.parse(van)
