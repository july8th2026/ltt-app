"""B13 B1 phu (dieu phoi 29/09) — BO DEM (⛔ khong phai bo loc) tin hieu ao
giac CHIEU NGUOC, muon nguyen van tu `D:\\Viral\\resources\\app-src\\localize.py`:

    _dur >= 6.0 and _nchar <= 10 and _nchar / max(_dur, 0.1) < 0.6   -> BO (Viral)

Ta chi DEM (`ban_ghi.dem_qua_it_ky_tu_dai`), ⛔ khong gan co, khong bo doan.
`n = 1` (luot that da do, 0/78) khong chung minh "khong bao gio xay ra", nen
day la mot BO DEM dua vao `outputs` de tich luy du lieu — quyet dinh loc chi
ban toi khi co du lieu that.
"""
from __future__ import annotations

from apps.auto_scan_video import ban_ghi


def _doan(bat, ket, chu, ma="x"):
    return {"ma": ma, "bat": bat, "ket": ket, "chu": chu, "tu": []}


def test_4927_doan_KHOP_cong_thuc_Viral_duoc_DEM():
    """Doan dai (>=6s), it ky tu (<=10), ty le duoi 0,6 kt/s — dung cong
    thuc Viral, phai duoc dem."""
    # 8s, "à ừ" -> bo khoang trang con "àừ" = 2 ky tu -> 2/8 = 0,25 < 0,6
    ban = {"doan": [_doan(0.0, 8.0, "à ừ")]}
    ra = ban_ghi.dem_qua_it_ky_tu_dai(ban)
    assert ra == {"so_khop": 1, "so_doan_da_xet": 1}


def test_4927_doan_NGAN_khong_khop_du_it_ky_tu():
    """Duoi 6s — ⛔ khong khop du chu it (Viral chi bat doan DAI ma im lang)."""
    ban = {"doan": [_doan(0.0, 5.9, "à")]}
    ra = ban_ghi.dem_qua_it_ky_tu_dai(ban)
    assert ra == {"so_khop": 0, "so_doan_da_xet": 1}


def test_4927_doan_DAI_nhung_NHIEU_ky_tu_khong_khop():
    """Dai >=6s nhung >10 ky tu — loi thoai binh thuong, ⛔ khong khop."""
    ban = {"doan": [_doan(0.0, 8.0, "một câu thoại bình thường có nhiều chữ")]}
    ra = ban_ghi.dem_qua_it_ky_tu_dai(ban)
    assert ra == {"so_khop": 0, "so_doan_da_xet": 1}


def test_4927_doan_DAI_it_ky_tu_nhung_TY_LE_khong_duoi_nguong():
    """<=10 ky tu, >=6s, nhung ty le kt/s KHONG duoi 0,6 — vd 6s/10 ky tu =
    1,67 kt/s — ⛔ khong khop."""
    ban = {"doan": [_doan(0.0, 6.0, "1234567890")]}   # 10/6 = 1.67 >= 0.6
    ra = ban_ghi.dem_qua_it_ky_tu_dai(ban)
    assert ra == {"so_khop": 0, "so_doan_da_xet": 1}


def test_4927_MAU_SO_dem_dung_TOAN_BO_doan_du_khop_hay_khong():
    """🔴 Mau so (`so_doan_da_xet`) phai la TOAN BO so doan, khong chi so doan
    khop — day la ly do `0` doc duoc thanh 'da xet N, sach' chu khong phai
    'chua do'."""
    ban = {"doan": [
        _doan(0.0, 8.0, "à ừ", "seg_0001"),          # khop
        _doan(0.0, 2.0, "câu bình thường", "seg_0002"),  # khong khop
        _doan(0.0, 1.0, "khác", "seg_0003"),          # khong khop
    ]}
    ra = ban_ghi.dem_qua_it_ky_tu_dai(ban)
    assert ra == {"so_khop": 1, "so_doan_da_xet": 3}


def test_4927_KHONG_MUTATE_ban_hay_doan():
    """🔴 Day la BO DEM, ⛔ khong phai bo loc: khong gan co, khong xoa doan,
    khong doi `ban`. So sanh truoc/sau."""
    doan_goc = _doan(0.0, 8.0, "à ừ")
    ban = {"doan": [dict(doan_goc)]}
    truoc = dict(ban["doan"][0])

    ban_ghi.dem_qua_it_ky_tu_dai(ban)

    assert ban["doan"][0] == truoc, "bo dem khong duoc doi doan"
    assert len(ban["doan"]) == 1, "bo dem khong duoc xoa doan"
    assert "viral_ao_giac" not in ban["doan"][0], "day la DEM, khong gan co"


def test_4927_LUOT_THAT_78_doan_0_khop_qua_tom_tat():
    """Doi chung: doi voi mot ban ghi 'sach' (khong doan nao khop cong thuc
    Viral), `tom_tat()` phai tra `so_khop: 0` kem `so_doan_da_xet` DUNG bang
    tong so doan — dung ca dinh dang duoc dua vao `outputs` that."""
    ban = ban_ghi.chuan_hoa(
        {"segments": [{"start": float(i), "end": float(i) + 1.0,
                       "text": f"câu số {i}", "words": []} for i in range(5)]},
        thoi_luong_nguon=10.0)
    tt = ban_ghi.tom_tat(ban)
    assert tt["qua_it_ky_tu_dai_muon_viral"] == {
        "so_khop": 0, "so_doan_da_xet": 5}


def test_4927_nguong_la_NGUYEN_VAN_tu_Viral_da_khai_ro():
    """Chot ba con so KHONG bi go nham — day la hang so MUON, dung dung so
    localize.py:620-622 khai: 6.0s / 10 ky tu / 0,6 kt/s."""
    assert ban_ghi.NGUONG_VIRAL_DAI_S == 6.0
    assert ban_ghi.NGUONG_VIRAL_KY_TU_TOI_DA == 10
    assert ban_ghi.NGUONG_VIRAL_TY_LE_KY_TU_MOI_GIAY == 0.6
