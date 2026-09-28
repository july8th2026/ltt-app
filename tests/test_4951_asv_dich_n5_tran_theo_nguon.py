"""B14/V3 N5 — tran DO DAI THEO MAT DO NGUON, muon `D:\\Viral\\...\\
dich_gemini_web.py:155-184 tran_tu_dich` (chi doc). Chot 28/09 cua chu du an:
ti le 0,75 dung NGUYEN.

⚠️ Khac PHA voi `nan_cho_vua` (chay SAU TTS, do giay THAT) — cua nay chay
TRUOC TTS, uoc tu mat do nguon. Hai cua BO SUNG nhau.

🔴 `wps_dich` KHONG lay bang cua Viral (ho = 5,00, do tren giong edge-tts CUA
HO) — dung `ngon_ngu.NHIP` (do tren chinh giong that cua san pham nay, xem
`dich_thuat.tran_do_dai_theo_nguon` docstring). Day la thay vi hieu chinh, vi
tien de cua bang Viral (TTS khac hang) khong dung voi ta — giong het tien le da
chot o `V3_DICH.md` hang 8.
"""
from __future__ import annotations

from apps.auto_scan_video import dich_thuat, ngon_ngu


def test_tran_dung_ngon_ngu_NHIP_khong_dung_bang_cua_Viral():
    """Tran = min(giay * NHIP[vi], n_nguon * 0,75) — NHIP la CUA TA (3,35), khong
    phai 5,00 cua Viral.
    """
    giay = 10.0
    nguon = "这" * 100  # 100 ky tu CJK -> n_nguon = 100 (dem CJK, khong split)
    tran = dich_thuat.tran_do_dai_theo_nguon(giay, nguon, dich=ngon_ngu.VI)

    tran_vat_ly = int(round(giay * ngon_ngu.NHIP[ngon_ngu.VI] * ngon_ngu.HE_SO_MUC_TIEU))
    tran_theo_nguon = int(100 * 0.75)
    assert tran == min(max(1, tran_vat_ly), tran_theo_nguon)
    # Nguong nay PHAI khac han tran neu dung wps=5,00 cua Viral (kiem cach ly):
    # vat_ly voi NHIP cua ta (3,35*0,92 ~ 3,08/giay) ~ 31; voi wps Viral (5,00)
    # se la 50 — hai gia tri khac nhau chung minh ham KHONG lay bang cua Viral.
    tran_neu_dung_wps_viral = int(min(giay * 5.00, 100 * 0.75))
    assert tran != tran_neu_dung_wps_viral


def test_dem_don_vi_nguon_CJK_dem_ky_tu_khong_dem_theo_dau_cach():
    """Nguon Trung dinh lien — dem so ky tu CJK, KHONG split() theo khoang trang."""
    nguon = "这是一段没有空格的中文文本内容"  # 15 ky tu CJK lien nhau, 0 khoang trang
    assert dich_thuat._dem_don_vi_nguon(nguon) == len(nguon)


def test_dem_don_vi_nguon_khong_CJK_dem_theo_tu():
    """Nguon en/vi (khong CJK) -> dem tu theo dau cach, cung don vi voi dich."""
    nguon = "this is an english source sentence"
    assert dich_thuat._dem_don_vi_nguon(nguon) == len(nguon.split())


def test_doan_noi_NHANH_THAT_khong_bi_gan_co_oan():
    """⭐ DOI CHUNG AM (bat buoc) — doan noi NHANH (nguon nhieu ky tu trong giay
    ngan) co tran RONG hon tuong ung; mot ban dich TUONG XUNG voi nhip noi that
    khong duoc gan co.
    """
    # Nguon dac: 60 ky tu CJK trong 4 giay (nhip nguon rat nhanh).
    nguon = "这" * 60
    giay = 4.0
    tran = dich_thuat.tran_do_dai_theo_nguon(giay, nguon, dich=ngon_ngu.VI)
    # Dich TU NHIEN, vua khop trong tran (khong ep) — KHONG duoc gan co.
    dich_vua = " ".join(["tu"] * tran)
    vuot, do_dai, tran_ra = dich_thuat.vuot_tran_theo_nguon(
        giay=giay, nguon=nguon, dich_ra=dich_vua, dich=ngon_ngu.VI)
    assert tran_ra == tran
    assert do_dai == tran
    assert vuot is False, "dich vua khop tran theo mat do van bi gan co oan"


def test_doan_dich_QUA_DAI_so_voi_tran_theo_nguon_bi_gan_co():
    nguon = "这" * 10           # nguon thua
    giay = 20.0                 # khe rong -> tran vat ly cao, tran theo nguon THAP
    dich_ra = " ".join(["mot"] * 50)   # co y dai hon han tran-theo-nguon (10*0,75=7)
    vuot, do_dai, tran = dich_thuat.vuot_tran_theo_nguon(
        giay=giay, nguon=nguon, dich_ra=dich_ra, dich=ngon_ngu.VI)
    assert tran == 7        # min(vat ly lon, 10*0,75=7,5 -> int=7)
    assert do_dai == 50
    assert vuot is True


def test_tran_KHONG_am_du_giay_am_hoac_nguon_rong():
    assert dich_thuat.tran_do_dai_theo_nguon(0.0, "", dich=ngon_ngu.VI) >= 1
    assert dich_thuat.tran_do_dai_theo_nguon(-5.0, "这", dich=ngon_ngu.VI) >= 1
