"""test_1254 — bao cao la HAM THUAN tu ban ghi sang bang.

⭐ Thuan CO CHU DICH: mot bao cao goi mang la mot bao cao KHONG tai lap duoc tu
   ban ghi da luu — va luc do ban ghi mat gia tri lam bang chung. Chay lai bao
   cao tren cung mot tep JSON phai cho ra cung mot bang, hom nay va sau sau
   thang.

🔴 Hai dieu bang nay BAT BUOC phai in ra, vi thieu chung thi bang noi doi:

   1. **commit production** — khong co no thi con so khong tai lap duoc; ta co
      mot bang dep ma khong biet no noi ve ban nao.
   2. **luot NHIEM, dem rieng** — 13/09 mot luot do bi deploy cua phien khac
      lam hong, va no trong y het mot phat hien lon. Gop no vao ti le "dat" la
      giau mat mot luot chua he do duoc.
"""
import pytest

from tools.nghiem_thu_van_hanh import bao_cao

_BAN_GHI = {
    "commit_production": "1235f8767d64",
    "tong_ket": {"dat": 2, "truot": 1, "nhiem": 1,
                 "tong_ket_luan_duoc": 3, "tong": 4},
    "kich_ban": [
        {"ma": "J1", "dat": True, "nhiem": False,
         "do_duoc": {"dinh_lease": 1, "chay_ngay": 1}},
        {"ma": "J4", "dat": True, "nhiem": False,
         "do_duoc": {"dinh_lease": 6, "chay_ngay": 6}},
        {"ma": "J10", "dat": False, "nhiem": False,
         "do_duoc": {"dinh_lease": 2, "khong_429": False}},
        {"ma": "J5", "dat": None, "nhiem": True,
         "ly_do_nhiem": "production doi commit giua luot do", "do_duoc": {}},
    ],
}


def test_bang_IN_commit_production():
    """Khong co commit thi con so khong tai lap duoc."""
    b = bao_cao.bang_chat_luong(_BAN_GHI)
    assert "1235f8767d64" in b


def test_bang_DEM_RIENG_luot_nhiem_va_NEU_LY_DO():
    """⚠️ So khop KHONG PHAN BIET HOA/THUONG va giu nguyen dau.

    Ban dau ve nay viet `"NHIEU" in b.upper() or "nhiễm" in b` — ca hai deu
    truot: bang in "NHIỄM" (hoa, CO dau), con ve tim mot ban khong dau va mot
    ban thuong. Ve do vi loi cua CHINH NO, khong phai vi ma sai. Mot phep kiem
    do nham the nay ton them mot vong doi chung de loai tru.
    """
    b = bao_cao.bang_chat_luong(_BAN_GHI)

    # ⛔ Ghim DONG CUA CHINH J5, khong phai "co chu nhiem o dau do trong bang".
    #    Doi chung da bat duoc diem yeu ay: go dau nhiem khoi tung dong ma ve
    #    van xanh, vi chu ay con o dong tong ket. Nguoi doc quet theo DONG.
    dong_j5 = [d for d in b.splitlines() if d.startswith("| `J5`")]
    assert dong_j5, f"khong thay dong cua J5 trong bang:\n{b[:400]}"
    assert "nhiễm" in dong_j5[0].lower(), (
        f"dong cua J5 khong danh dau NHIEM: {dong_j5[0]!r}")

    assert "production doi commit" in b, (
        "bang khong neu VI SAO mot luot bi loai — nguoi doc khong the tu quyet")


def test_ti_le_dat_KHONG_tinh_luot_nhiem_vao_mau_so():
    t = bao_cao.tham_so_do_duoc(_BAN_GHI)
    assert t["so_dat"] == 2
    assert t["so_truot"] == 1
    assert t["so_nhiem"] == 1
    assert t["mau_so"] == 3, "luot nhiem dang bi tinh vao mau so"


def test_bang_LIET_KE_kich_ban_TRUOT_ro_rang():
    b = bao_cao.bang_chat_luong(_BAN_GHI)
    assert "J10" in b


def test_ham_THUAN_khong_doi_ban_ghi():
    """⛔ Bao cao khong duoc sua ban ghi — ban ghi la bang chung."""
    import copy

    goc = copy.deepcopy(_BAN_GHI)
    bao_cao.bang_chat_luong(_BAN_GHI)
    bao_cao.tham_so_do_duoc(_BAN_GHI)
    assert _BAN_GHI == goc, "bao cao da sua ban ghi dau vao"


def test_ban_ghi_THIEU_commit_thi_BAO_chu_khong_im():
    """Mot bang khong noi ve ban nao thi vo dung — phai noi ra, khong duoc im."""
    thieu = {k: v for k, v in _BAN_GHI.items() if k != "commit_production"}
    with pytest.raises(bao_cao.BanGhiThieu):
        bao_cao.bang_chat_luong(thieu)


def test_chay_HAI_LAN_cho_cung_mot_bang():
    """Thuan = tai lap duoc. Neu khong, ban ghi mat gia tri lam bang chung."""
    assert bao_cao.bang_chat_luong(_BAN_GHI) == bao_cao.bang_chat_luong(_BAN_GHI)
