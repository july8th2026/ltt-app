"""B13 B2 (28/09) — hai CUA doc lap tren `phu_song`, con so DA CO SAN trong
`ban_ghi.tom_tat()` ma truoc gio chua ai doc.

Can cu (luot that asvr_47327a869a8f4597960048f09064740, 78 doan):

    phu_song 211,56 / thoi_luong 275,04 = 76,9 %   (DAY LA loi ASR)
    8 lo hong > 2s, lon nhat 32,5s; cac lo con lai 2,1-7,4s la BINH THUONG

CUA A (ty le) va CUA B (mot lo hong don le) la HAI cau hoi khac nhau: mot
tong thap co the la phim it loi (hop le) hoac mot ho lon bi giau trong tong
cao (loi). Test o day chot CA HAI chieu, voi doi chung am cho tung cua.
"""
from __future__ import annotations

from apps.auto_scan_video import ban_ghi


def _doan(bat, ket, ma="x"):
    return {"ma": ma, "bat": bat, "ket": ket, "chu": "a", "tu": []}


def test_4926_CUA_B_mot_LO_HONG_LON_bi_CANH_BAO():
    """Tai hien can canh: mot lo hong 32,5s giua hai doan (nguon: 65,17 ->
    97,66) trong mot ban ghi co ty le tong VAN cao — CUA B phai bat duoc du
    CUA A khong keu."""
    ban = {"doan": [
        _doan(0.0, 65.17, "a"),
        _doan(97.66, 260.0, "b"),   # lo hong = 32,5s
    ]}
    # thoi_luong du gan tong doan de ty le PHU SONG cao (khong kich CUA A)
    phu = ban_ghi.do_phu_song(ban, thoi_luong=227.66)

    assert phu["lo_hong_lon_nhat_s"] == 32.49    # 97,66 - 65,17
    assert phu["canh_bao_lo_hong"] is True
    assert phu["so_lo_hong_qua_nguong"] == 1
    assert phu["canh_bao_ty_le"] is False, (
        "ty le tong o day cao — CUA A KHONG duoc keu thay CUA B")


def test_4926_DOI_CHUNG_AM_8_lo_hong_BINH_THUONG_KHONG_bi_keu():
    """🔴 Doi chung am bat buoc cho CUA B: 8 lo hong do THAT (2,1-7,4s, deu duoi
    `NGUONG_LO_HONG_S`) la BINH THUONG cua mot phim co doi thoai — bao dong gia
    o day tung lam nguoi ta TAT ca cong (kho da ghi ca do)."""
    muc = [2.1, 3.0, 3.4, 4.2, 5.0, 5.8, 6.6, 7.4]   # 8 lo hong do THAT
    doan = []
    t = 0.0
    for i, g in enumerate(muc):
        t += g
        doan.append(_doan(t, t + 5.0, f"seg_{i:02d}"))
        t += 5.0
    ban = {"doan": doan}

    phu = ban_ghi.do_phu_song(ban, thoi_luong=t)

    assert phu["so_lo_hong_qua_nguong"] == 0
    assert phu["canh_bao_lo_hong"] is False, (
        "8 lo hong binh thuong (2,1-7,4s) khong duoc kich CUA B")
    assert phu["lo_hong_lon_nhat_s"] == max(muc)


def test_4926_CUA_A_ty_le_TONG_thap_ma_KHONG_co_lo_hong_don_le():
    """Doi chung: mot 'phim that su it loi' — nhieu doan NGAN, cach deu, moi
    khoang cach nam DUOI nguong CUA B — van co the co ty le tong thap. CUA A
    duoc phep keu rieng no; CUA B ⛔ khong duoc keu theo."""
    doan = []
    t = 0.0
    for i in range(10):
        t += 10.0                  # 10s im lang giua moi cau — duoi 15s
        doan.append(_doan(t, t + 1.0, f"seg_{i:02d}"))   # 1s thoai
        t += 1.0
    ban = {"doan": doan}
    # phu_song = 10*1.0 = 10s; thoi_luong = t (~110s) -> ty le ~9%
    phu = ban_ghi.do_phu_song(ban, thoi_luong=t)

    assert phu["canh_bao_ty_le"] is True
    assert phu["canh_bao_lo_hong"] is False, (
        "khong lo hong don le nao vuot nguong — CUA B khong duoc bao ke theo")


def test_4926_ca_hai_CUA_deu_SACH_tren_mot_ban_ghi_PHU_KIN():
    """Doi chung duong hoan toan: khong lo hong, ty le gan 100% — ca hai cua
    im lang."""
    ban = {"doan": [_doan(0.0, 10.0, "a"), _doan(10.0, 20.0, "b")]}
    phu = ban_ghi.do_phu_song(ban, thoi_luong=20.0)

    assert phu["ty_le_phu_song"] == 1.0
    assert phu["canh_bao_ty_le"] is False
    assert phu["lo_hong_lon_nhat_s"] == 0.0
    assert phu["canh_bao_lo_hong"] is False


def test_4926_nguong_CUA_A_nam_TREN_muc_that_hong_76_9_phan_tram():
    """🔴 Chot can cu bang mot con so tren luot that: 76,9 % PHAI kich CUA A."""
    assert ban_ghi.NGUONG_TY_LE_PHU_SONG > 0.769

    ban = {"doan": [_doan(0.0, 211.56, "a")]}
    phu = ban_ghi.do_phu_song(ban, thoi_luong=275.04)

    assert round(phu["ty_le_phu_song"], 3) == 0.769
    assert phu["canh_bao_ty_le"] is True


def test_4926_nguong_CUA_B_nam_GIUA_muc_binh_thuong_va_muc_loi():
    """🔴 Chot can cu: nguong CUA B nam tren muc binh thuong cao nhat da do
    (7,4s) va duoi muc loi that (32,5s) — khong sat nut ca hai phia."""
    assert 7.4 < ban_ghi.NGUONG_LO_HONG_S < 32.5


def test_4926_KHONG_chan_luot_chi_la_canh_bao():
    """B2 chi la log.warning + con so vao outputs — ham nay KHONG nem loi du
    canh bao ca hai cua."""
    ban = {"doan": [_doan(0.0, 1.0, "a"), _doan(50.0, 51.0, "b")]}
    phu = ban_ghi.do_phu_song(ban, thoi_luong=100.0)   # ty le thap + lo hong lon
    assert phu["canh_bao_ty_le"] and phu["canh_bao_lo_hong"]
    # khong ngoai le nao duoc nem — chi doc duoc con so


# ── Diem sua tiep theo dieu phoi (28/09): TONG vs HOP, mot nguon chan ly ────


def test_4926_CHONG_LAN_ca_dung_ra_TONG_khac_HOP():
    """🔴 Ca dung ra theo yeu cau dieu phoi: [0,3) va [1,4) chong lan 2 giay.

    TONG (`tong_giay_doan`) dem hai lan phan chong lan = 3 + 3 = 6.
    HOP (`hop_giay_co_tieng`, dung cho CUA A) chi tinh khoang thoi gian THAT
    co tieng = 4. Hai dai luong PHAI khac nhau o day — neu ban va lam chung
    mot so thi mot trong hai da bi go nham cong thuc cua ben kia.
    """
    ban = {"doan": [_doan(0.0, 3.0, "a"), _doan(1.0, 4.0, "b")]}

    assert ban_ghi.tong_giay_doan(ban["doan"]) == 6.0

    phu = ban_ghi.do_phu_song(ban, thoi_luong=4.0)
    assert phu["tong_giay_doan"] == 6.0
    assert phu["hop_giay_co_tieng"] == 4.0
    assert phu["giay_chong_lan"] == 2.0

    # CUA A phai dung HOP (4/4 = 100%), ⛔ khong dung TONG (6/4 = 150%,
    # vo ly — mot ty le khong the vuot 100%).
    assert phu["ty_le_phu_song"] == 1.0
    assert phu["canh_bao_ty_le"] is False


def test_4926_MOT_NGUON_CHAN_LY_tom_tat_va_do_phu_song_khop_nhau():
    """🔴 Doi chung bat buoc cho phat hien 'hai ban sao cua mot cong thuc':
    tren CUNG mot `ban`, `tom_tat()["phu_song"]` va
    `do_phu_song()["tong_giay_doan"]` phai la CUNG mot con so — vi ca hai
    goi CHUNG `tong_giay_doan()`, khong tu viet lai `sum(ket - bat)`."""
    ban = {"doan": [_doan(0.0, 3.0, "a"), _doan(1.0, 4.0, "b"),
                    _doan(10.0, 12.5, "c")]}

    tu_tom_tat = ban_ghi.tom_tat(ban)["phu_song"]
    tu_do_phu_song = ban_ghi.do_phu_song(ban, thoi_luong=12.5)["tong_giay_doan"]

    assert tu_tom_tat == tu_do_phu_song == 8.5   # (3-0)+(4-1)+(12.5-10) = 8.5
