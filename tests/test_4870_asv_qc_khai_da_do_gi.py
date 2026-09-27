"""Lan E — mot cong chat luong phai khai NO DA DO GI, va do bang HE SO NAO.

Ba menh de, ba ho loi cua bang bay chung:

  A. `qc_do_luong` do doan tieng qua DUNG he so `atempo` ban phoi DA AP
     (`giai_doan_thoi_gian.he_so_ap`), khong qua he so THO cua ban ke.
     -> ho #1 (kenh do khac kenh giao) + #9 (pham vi hep hon loi tuyen bo)

  B. Bao cao `qc` phai GOI TEN phep do KHONG chay duoc. `dat = not hong` cho
     `KHONG_AP_DUNG` di qua lang le, nen mot luot ma T3/T13/T17/T18 deu khong
     do duoc van in `qc_ky_thuat_dat: True`, `so_muc_hong: 0`.
     -> ho #5 (loi bi nuot) + #2 (mot gia tri ganh hai trang thai)

  C. `qc_do_luong` phai phan biet doan DA CHUAN BI voi doan THAT SU DO DUOC.
     `so_doan_do` dem doan chuan bi, nen mot luot bo do `khong_kha_dung` van
     khai "95 doan da do".
     -> ho #2

⚠️ Moi bai o day da DO thay vi chot mot hinh dang: xem ghi chu tung bai.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import giai_doan_qc as gq
from apps.auto_scan_video import giai_doan_qc_do_luong as gdl
from apps.auto_scan_video import giai_doan_thoi_gian as gt
from apps.auto_scan_video import qc


# ══════════════════════════════════════════════════════════════════════════════
#  A. He so co gian: do bang he so DA AP, khong he so THO
# ══════════════════════════════════════════════════════════════════════════════

def _bat_lenh(monkeypatch) -> list:
    """Chan `nhap_media._chay` de lay DUNG lenh ffmpeg `_dung_tep` dung."""
    from apps.auto_scan_video import nhap_media

    da_goi: list = []

    class _R:
        returncode = 0
        stderr = b""

    def _gia(cmd, **kw):
        da_goi.append(list(cmd))
        return _R()

    monkeypatch.setattr(nhap_media, "_chay", _gia)
    return da_goi


def _he_so_trong_lenh(cmd: list) -> float | None:
    for i, x in enumerate(cmd):
        if x == "-af":
            for phan in cmd[i + 1].split(","):
                if phan.startswith("atempo="):
                    return float(phan.split("=", 1)[1])
    return None


def test_he_so_VUOT_tran_ky_thuat_thi_do_bang_he_so_DA_AP(monkeypatch):
    """🔴 Con bug: `_dung_tep` dung he so THO cua ban ke.

    `giai_doan_thoi_gian` KEP he so ve `TRAN_KY_THUAT_ATEMPO` truoc khi tron
    (`he_so_theo_ma` -> `am_master.bieu_thuc_lo`), va chinh no ghi
    `log.warning` khi kep. Nhung dong `ban_ke` giu nguyen he so tho:
    `nan_cho_vua.ket_luan` tra `he_so_co_gian = giay/khe` KHONG kep cho trang
    thai `CAN_SUA` ("vuot ca tran co gian").

    ⇒ Voi mot doan `CAN_SUA`, `qc_do_luong` tang toc tep NHANH HON ban khach
      nghe. ASR chep mot tep khac voi tep da giao, WER phong len,
      `sua_chua.giong_khong_dat` danh dau, va vong sua chay cho mot doan
      KHONG hong. Docstring dau tep con khai nguoc lai: *"qua DUNG he so co
      gian `atempo` ma ban phoi ap cho doan do"*.
    """
    cmd = _bat_lenh(monkeypatch)
    gdl._dung_tep("a.wav", "b.wav", 2.8)
    assert _he_so_trong_lenh(cmd[0]) == pytest.approx(
        gt.he_so_ap(2.8, tran_ky_thuat=gt.TRAN_KY_THUAT_ATEMPO)), \
        "do bang he so THO — tep do khac tep khach nghe"


def test_he_so_TRONG_tran_thi_giu_nguyen(monkeypatch):
    """Chieu nguoc lai: khong duoc kep mot he so ban phoi THAT SU da ap."""
    cmd = _bat_lenh(monkeypatch)
    gdl._dung_tep("a.wav", "b.wav", 1.37)
    assert _he_so_trong_lenh(cmd[0]) == pytest.approx(1.37)


def test_he_so_1_thi_KHONG_co_atempo(monkeypatch):
    cmd = _bat_lenh(monkeypatch)
    gdl._dung_tep("a.wav", "b.wav", 1.0)
    assert "-af" not in cmd[0]


def test_he_so_ngoai_khoang_MOT_lan_atempo_khong_lam_HONG_ca_giai_doan(
        monkeypatch):
    """⚠️ Cung mot goc, trieu chung thu hai — va nay la mot CU SAP.

    `am_master.bieu_thuc_lo` nem tuong minh khi he so ngoai `[0,5; 100]`, nhung
    no khong bao gio thay so do vi ban phoi da kep ve 2,0. `_dung_tep` khong
    kep va khong kiem: mot `khe` rat ngan (`he_so = giay/khe`) cho ra he so
    > 100, ffmpeg tu choi, `MediaError` KHONG duoc bat o `chay` ⇒ mot giai
    doan **DO LUONG** lam hong ca lan chay da render xong va da qua cong `qc`.
    """
    cmd = _bat_lenh(monkeypatch)
    gdl._dung_tep("a.wav", "b.wav", 240.0)
    h = _he_so_trong_lenh(cmd[0])
    assert h is not None and 0.5 <= h <= 100.0, \
        f"he so {h} ngoai khoang mot lan `atempo` — ffmpeg se tu choi"


# ══════════════════════════════════════════════════════════════════════════════
#  B. Bao cao QC phai GOI TEN phep do khong chay duoc
# ══════════════════════════════════════════════════════════════════════════════

def _bao_cao_moi_thu_khong_do_duoc() -> dict:
    """Bao cao QC cua mot luot ma MOI phep do sau deu khong chay duoc."""
    return qc.kiem(
        tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 100.0},
        tt_nguon={"co_video": True, "co_tieng": True, "thoi_luong": 100.0},
        am_luong={"lufs": qc.LUFS_DICH, "dinh_that": -2.0},
        ke_hoach={"doan": [], "so_doan_bi_cat": 0, "troi_toi_da_ms": 0},
        ban_ke_tieng={"doan": []}, ban_dung_lop=[],
        # ⛔ Dung hinh dang ma `giai_doan_qc.chay` truyen khi ba phep do hong:
        #    bam rong (T3), `hinh_*` None (T13/T17), `vmaf` co `loi` (T18).
        bam_ra="", bam_nguon="", hinh_ra=None, hinh_nguon=None,
        che_do_render="cat_ma_hoa_lai", vmaf={"loi": "thieu libvmaf"},
        thoi_luong_mong_doi=100.0)


def test_bao_cao_QC_KHONG_do_gi_van_bao_DAT_day_la_SU_THAT_can_khai():
    """⭐ Phep do chung minh lo hong TON TAI (khong phai bai chot hanh vi moi).

    ⛔ Khong sua `qc.kiem` (tep cua lan khac) — chi ghi lai su that o day de
       menh de duoi doc duoc.
    """
    bc = _bao_cao_moi_thu_khong_do_duoc()
    assert bc["dat"] is True and bc["so_muc_hong"] == 0
    assert qc.tom_tat(bc)["qc_ky_thuat_dat"] is True
    khong_do = [m["ma"] for m in bc["muc"]
                if m["trang_thai"] == qc.KHONG_AP_DUNG]
    assert {"T3", "T13", "T17", "T18"} <= set(khong_do)


def test_tom_tat_cua_giai_doan_phai_GOI_TEN_phep_do_khong_chay_duoc():
    """🔴 Con bug: ba khoi `except` cua `giai_doan_qc.chay` chi `log.warning`.

    `tom_tat` di thang vao `asv_stage.outputs`, va do la thu `quan_sat.
    bang_chung_chat_luong` doc de noi voi khach. Khong co truong nao o do phan
    biet *"18 phep do, 18 dat"* voi *"4 phep do khong chay, 14 dat"* — nen mot
    production thieu `libvmaf` khai ĐAT y het mot production do du.

    ⚠️ Doi chieu: `giai_doan_qc_do_luong` DA lam dung dieu nay (`do_luong`:
       `{ten: trang_thai}`), va `quan_sat.NHAN_TRANG_THAI_BO_DO` da co cau
       *"chua do duoc tren may chu"*. Con `qc` thi chua.
    """
    bc = _bao_cao_moi_thu_khong_do_duoc()
    tt = gq.tom_tat_kem_khong_do(bc, {
        "T3": "QcError: Khong bam duoc luong hinh.",
        "T13": "TimeoutExpired: 3600s",
        "T17": "TimeoutExpired: 3600s",
        "T18": "thieu libvmaf"})
    assert tt["qc_ky_thuat_dat"] is True          # giu nguyen be mat cu
    assert tt["qc_so_muc_khong_do"] == 4
    assert set(tt["qc_muc_khong_do"]) == {"T3", "T13", "T17", "T18"}
    # Ly do do chinh cho NEM ra ghi lai — khong suy nguoc tu `mo_ta`.
    assert tt["qc_ly_do_khong_do"]["T18"] == "thieu libvmaf"


def test_do_het_18_phep_thi_KHONG_bao_thieu():
    """⛔ Khong duoc bao dong gia: mot luot do day du phai ra 0 phep khong do.

    ⚠️ T8/T9/T10 la `KHONG_AP_DUNG` **theo thiet ke** (ba dung sai da bo), nen
       chung phai bi tru ra — nguoc lai thi moi luot chay deu "thieu 3 phep do"
       va con so tro thanh tieng on, roi nguoi ta tat no.
    """
    bc = qc.kiem(
        tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 100.0},
        tt_nguon={"co_video": True, "co_tieng": True, "thoi_luong": 100.0},
        am_luong={"lufs": qc.LUFS_DICH, "dinh_that": -2.0},
        ke_hoach={"doan": [], "so_doan_bi_cat": 0, "troi_toi_da_ms": 0},
        ban_ke_tieng={"doan": []}, ban_dung_lop=[],
        bam_ra="aaa", bam_nguon="aaa",
        hinh_ra={"den_s": 0.0, "dong_s": 0.0, "so_loi_giai_ma": 0,
                 "ma_thoat": 0},
        hinh_nguon={"den_s": 0.0, "dong_s": 0.0},
        che_do_render="sao_chep", thoi_luong_mong_doi=100.0)
    tt = gq.tom_tat_kem_khong_do(bc, {})
    assert tt["qc_so_muc_khong_do"] == 0, tt["qc_muc_khong_do"]


def test_KHONG_AP_DUNG_theo_THIET_KE_khong_bi_dem_la_thieu_phep_do():
    """⛔ Chan bao dong gia — thu lam nguoi ta TAT mot cai cong.

    T8/T9/T10 la `KHONG_AP_DUNG` theo thiet ke (ba dung sai da bo), T18 la
    `KHONG_AP_DUNG` o preset giu hinh. Ca bon deu KHONG nam trong `ly_do`, nen
    chung ⛔ khong duoc dem.
    """
    bc = _bao_cao_moi_thu_khong_do_duoc()
    tt = gq.tom_tat_kem_khong_do(bc, {"T18": "thieu libvmaf"})
    assert tt["qc_muc_khong_do"] == ["T18"]
    assert set(tt["qc_muc_khong_do"]).isdisjoint({"T8", "T9", "T10"})


def test_phep_do_TUNG_hong_ma_CUOI_CUNG_van_co_ket_qua_thi_KHONG_dem():
    """Chieu nguoc lai, va no la cai giu con so khoi phong len.

    O preset cat, bam luong hinh KHONG duoc chay (T3 `KHONG_AP_DUNG` theo che
    do) — nhung neu mot muc trong `ly_do` lai DAT/HONG trong bao cao thi no DA
    duoc do bang duong khac, va khai no la "khong do duoc" la mot bao cao
    noi doi ve chinh no.
    """
    bc = _bao_cao_moi_thu_khong_do_duoc()
    do_duoc = [m["ma"] for m in bc["muc"]
               if m["trang_thai"] in (qc.DAT, qc.HONG)]
    assert do_duoc, "bo dau vao phai co it nhat mot muc DA do"
    tt = gq.tom_tat_kem_khong_do(bc, {ma: "bia ra" for ma in do_duoc})
    assert tt["qc_so_muc_khong_do"] == 0, tt["qc_muc_khong_do"]


# ── Tiem loi vao CHINH cho nem: cong co biet DO khong? ───────────────────────

def test_bam_luong_hinh_HONG_thi_ly_do_thanh_GIA_TRI_TRA_VE(monkeypatch):
    """⚠️ Tiem loi: `qc.bam_luong_hinh` nem ⇒ `_bam_hai_ben` phai GOI TEN no.

    Truoc ban sua, chinh cho nay chi `log.warning` — mot dong log ⛔ khong vao
    artifact va ⛔ khong vao `stage.outputs`, nen "T3 khong do duoc" bien mat
    khoi moi thu nguoi doc bao cao nhin thay.
    """
    def _nem(_duong, **kw):
        raise qc.QcError("Khong bam duoc luong hinh.")

    monkeypatch.setattr(qc, "bam_luong_hinh", _nem)
    ra, nguon, ly_do = gq._bam_hai_ben("ra.mp4", "nguon.mp4")
    assert (ra, nguon) == ("", "")
    assert "QcError" in ly_do and "bam" in ly_do


def test_do_hinh_HONG_thi_CA_T13_va_T17_deu_duoc_khai(monkeypatch):
    """⚠️ Tiem loi: MOT luot giai ma tra loi HAI phep kiem.

    Khai mot cai roi bo cai kia thi bang do phu noi rang T17 da chay.
    """
    def _nem(_duong, **kw):
        raise qc.QcError("Khong chay duoc bo do hinh.")

    monkeypatch.setattr(qc, "do_hinh", _nem)
    hr, hn, ly_do = gq._do_hinh_hai_ben("ra.mp4", "nguon.mp4", tt_ra={},
                                        tt_nguon={}, bam_khop=False)
    assert hr is None and hn is None and "QcError" in ly_do

    bc = _bao_cao_moi_thu_khong_do_duoc()
    tt = gq.tom_tat_kem_khong_do(bc, {"T13": ly_do, "T17": ly_do})
    assert tt["qc_muc_khong_do"] == ["T13", "T17"]


def test_bam_KHOP_thi_KHONG_giai_ma_nguon_lan_hai(monkeypatch):
    """⭐ Giu lai phep toi uu cu: bam khop ⇒ so do nguon = so do ban ra."""
    da_goi: list = []

    def _gia(duong, **kw):
        da_goi.append(duong)
        return {"den_s": 1.0, "dong_s": 2.0, "so_loi_giai_ma": 0, "ma_thoat": 0}

    monkeypatch.setattr(qc, "do_hinh", _gia)
    hr, hn, ly_do = gq._do_hinh_hai_ben("ra.mp4", "nguon.mp4", tt_ra={},
                                        tt_nguon={}, bam_khop=True)
    assert da_goi == ["ra.mp4"] and ly_do == ""
    assert hn == {"den_s": 1.0, "dong_s": 2.0}
    assert hr["so_loi_giai_ma"] == 0


# ══════════════════════════════════════════════════════════════════════════════
#  C. `so_doan_do` dem doan CHUAN BI, khong doan DO DUOC
# ══════════════════════════════════════════════════════════════════════════════

def _ket_bo_do_khong_kha_dung() -> dict:
    return {
        "giong": {"trang_thai": "khong_kha_dung", "ket_qua": {},
                  "ly_do": "thieu qc-venv"},
        "chat_luong_tieng": {"trang_thai": "khong_kha_dung", "ket_qua": {},
                             "ly_do": "thieu qc-venv"},
        "dich": {"trang_thai": "khong_kha_dung", "ket_qua": {},
                 "ly_do": "chua co bo do dich"},
    }


def test_bo_do_khong_kha_dung_thi_so_doan_DA_DO_bang_0():
    """🔴 Con bug: `so_doan_do = len(doan)` = so doan CHUAN BI.

    `quan_sat.bang_chung_chat_luong` in thang con so nay cho khach
    (`so_doan_do`), canh `so_giong_khong_dat: 0`. Voi bo do
    `khong_kha_dung`, hai con so ay doc thanh *"da do 95 doan, khong doan nao
    sai"* — trong khi KHONG doan nao duoc do.
    """
    tt = gdl.tom_tat_do_luong(_ket_bo_do_khong_kha_dung(), so_doan_chuan_bi=95)
    assert tt["so_doan_do"] == 95            # be mat cu: doan da chuan bi
    assert tt["so_doan_da_do"] == 0, "khai da do 95 doan ma khong do doan nao"
    assert tt["so_giong_khong_dat"] == 0


def test_bo_do_XONG_thi_so_doan_DA_DO_dem_doan_co_chi_so_that():
    """Chieu nguoc lai, va no dem theo `wer` — DUNG chi so `sua_chua` doc."""
    ket = {"giong": {"trang_thai": "xong",
                     "ket_qua": {"s1": {"wer": 0.05, "cer": 0.02},
                                 "s2": {"wer": 0.07, "cer": 0.03},
                                 # doan bi bo qua: khong co `wer`
                                 "s3": {"bo_qua": "tham chieu rong"}}},
           "chat_luong_tieng": {"trang_thai": "xong", "ket_qua": {}},
           "dich": {"trang_thai": "khong_kha_dung", "ket_qua": {}}}
    tt = gdl.tom_tat_do_luong(ket, so_doan_chuan_bi=3)
    assert tt["so_doan_do"] == 3 and tt["so_doan_da_do"] == 2
