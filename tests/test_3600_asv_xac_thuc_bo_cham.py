"""Task 10 — hop dong cua CONG CU XAC THUC bo cham ngu nghia.

🔴 **Phep kiem o day canh chinh CAI THUOC DO, khong canh bo cham.** Cau hoi cua
   Task 10 la *"44/95 la ban dich te that, hay bo cham qua tay"*, va cau tra loi
   do se duoc doc tu con so ma cong cu nay in ra. Mot cong cu dem sai thi ca hai
   cau tra loi deu sai, va khong ai bat duoc — vi khong con thuoc do nao khac.

⛔ Khong goi may B trong tep nay. Moi phep kiem o day la TINH.
"""
from __future__ import annotations

import random

import pytest

from tools import bench_b2_xac_thuc_bo_cham as bc


# ══════════════════════════════════════════════════════════════════════════════
#  1. Nguong — viet TRUOC khi do, va banh coc de khong ai noi sau khi thay so
# ══════════════════════════════════════════════════════════════════════════════

def test_nguong_da_viet_truoc_va_khong_duoc_noi():
    """⛔ Ba hang so nay la PHAN QUYET cua Task 10. Doi chung = doi ket luan."""
    assert bc.NGUONG_BAO_DONG_GIA == 0.15
    assert bc.N_TOI_THIEU == 100
    # Cong ap `--temp 1.0` va `seed` khong co hieu luc => mot luot don le khong
    # phai mot phan quyet.
    assert bc.LUOT_MOI_CAP >= 3


def test_do_voi_n_duoi_nguong_bi_TU_CHOI():
    """Co mau nho hon `N_TOI_THIEU` khong duoc phep cho ra mot phan quyet."""
    with pytest.raises(SystemExit):
        bc.main(["do", "--n", "40", "--ra", "khong_dung.json"])


# ══════════════════════════════════════════════════════════════════════════════
#  2. Phep LAM HONG — doi chung am chi co nghia neu no that su lam hong
# ══════════════════════════════════════════════════════════════════════════════

def test_lat_nghia_that_su_lat_nghia():
    assert bc.lam_hong_lat_nghia("Sản lượng tăng trong năm nay.") == \
        "Sản lượng giảm trong năm nay."
    # Them phu dinh vao mot cau khang dinh.
    ra = bc.lam_hong_lat_nghia("Ông ấy có mặt tại hiện trường.")
    assert ra is not None and "không có" in ra


def test_lat_nghia_tra_None_khi_khong_ap_duoc_phep_nao():
    """⭐ `None`, ⛔ khong tra lai cau nguyen ven.

    Mot cau "da lam hong" ma thuc ra khong doi gi se di vao cot *bo cham khong
    bat duoc* va keo ti le bat xuong — tuc ta ket toi bo cham mot loi cua chinh
    bo do.
    """
    assert bc.lam_hong_lat_nghia("Mưa rơi.") is None


def test_sai_thuc_the_doi_SO_khi_cau_co_so():
    rng = random.Random(1)
    ra = bc.lam_hong_sai_thuc_the("Có 12 người tham dự.", rng)
    assert ra == "Có 19 người tham dự."


def test_sai_thuc_the_doi_TEN_RIENG_khi_cau_khong_co_so():
    rng = random.Random(1)
    goc = "Hội nghị diễn ra tại Stanford vào mùa thu."
    ra = bc.lam_hong_sai_thuc_the(goc, rng)
    assert ra is not None and ra != goc and "Stanford" not in ra
    assert any(t in ra for t in bc.TEN_THAY_THE)


def test_sai_thuc_the_tra_None_khi_khong_co_gi_de_doi():
    assert bc.lam_hong_sai_thuc_the("mưa rơi rất to.", random.Random(1)) is None


def test_dung_cap_tiem_tach_HAI_LOAI_va_du_so_moi_loai():
    """⛔ Hai loai tach rieng tu day cho toi bao cao.

    Gop lai thanh mot ti le tong se giau mat truong hop nguy hiem nhat: bat gan
    het `sai_thuc_the` va bo gan het `lat_nghia` van cho ra mot con so dep.
    """
    cap = [(i, f"源{i}", f"Sản lượng tăng {i} phần trăm trong năm.")
           for i in range(40)]
    ra = bc.dung_cap_tiem(cap, moi_loai=5, rng=random.Random(bc.HAT_GIONG))
    assert len(ra) == 10
    assert sum(1 for m in ra if m["loai"] == "lat_nghia") == 5
    assert sum(1 for m in ra if m["loai"] == "sai_thuc_the") == 5
    assert len({m["ma"] for m in ra}) == 10
    # Moi cap tiem PHAI khac ban goc cua chinh dong do.
    goc = {i: v for i, _, v in cap}
    assert all(m["chu"] != goc[m["dong_flores"]] for m in ra)


def test_dung_cap_tiem_KHONG_im_lang_khi_thieu_cap():
    """Thieu cap thi dung, ⛔ khong tra ve mot bo nho hon roi de nguoi doc tuong
    la da du — mot mau so nho hon lam ti le bat NHAY len vo co."""
    with pytest.raises(SystemExit):
        bc.dung_cap_tiem([(0, "源", "Mưa rơi.")], moi_loai=3,
                         rng=random.Random(1))


# ══════════════════════════════════════════════════════════════════════════════
#  3. Gop nhieu luot — TRUNG VI
# ══════════════════════════════════════════════════════════════════════════════

def _luot(**dat) -> dict:
    return {"phan_quyet": {m: {"dat": v, "do_tin": 1.0, "ly_do": ""}
                           for m, v in dat.items()}, "loi_lo": []}


def test_gop_trung_vi_lay_DA_SO_chu_khong_lay_mot_luot():
    luot = [_luot(a=False, b=True), _luot(a=True, b=True),
            _luot(a=False, b=False)]
    gop = bc.gop_trung_vi(luot, ["a", "b"])
    assert gop["a"] == {"dat": False, "so_luot": 3, "so_bao_sai": 2}
    assert gop["b"] == {"dat": True, "so_luot": 3, "so_bao_sai": 1}


def test_gop_trung_vi_BO_HAN_ma_khong_luot_nao_tra_loi():
    """⛔ Khong phai `dat`, cung khong phai `khong dat` — la mot cau hoi CHUA
    duoc tra loi, va mau so cua moi ti le phai la so cau DA tra loi."""
    gop = bc.gop_trung_vi([_luot(a=True)], ["a", "vang_mat"])
    assert "vang_mat" not in gop
    tl = bc._ti_le([_luot(a=True)], ["a", "vang_mat"], gop)
    assert tl["n_hoi"] == 2 and tl["n_co_phan_quyet"] == 1
    assert tl["ti_le_trung_vi"] == 0.0


def test_ti_le_bao_cao_DAI_cua_tung_luot():
    luot = [_luot(a=False, b=False), _luot(a=True, b=True),
            _luot(a=False, b=True)]
    tl = bc._ti_le(luot, ["a", "b"], bc.gop_trung_vi(luot, ["a", "b"]))
    assert tl["ti_le_tung_luot"] == [1.0, 0.0, 0.5]
    assert tl["dai"] == [0.0, 1.0]


# ══════════════════════════════════════════════════════════════════════════════
#  4. Ti le BAT loi tiem — ⛔ khong duoc dao chieu
# ══════════════════════════════════════════════════════════════════════════════

def test_ti_le_bat_loi_tiem_dem_theo_CHIEU_DUNG(monkeypatch):
    """🔴 `khong dat` tren mot cap DA LAM HONG nghia la **BAT DUOC**.

    Mot dau tru lac cho o day dao nguoi mu thanh nguoi tinh: bo cham bat 0/15
    se duoc in ra la 100 %, va ta se ket luan no dang tin dung luc no chet.
    """
    muc = [{"ma": "tiem_lat_nghia_0500", "dong_flores": 500,
            "loai": "lat_nghia", "goc": "源", "chu": "x"},
           {"ma": "tiem_sai_thuc_the_0501", "dong_flores": 501,
            "loai": "sai_thuc_the", "goc": "源", "chu": "y"}]
    monkeypatch.setattr(bc, "dung_cap_tiem", lambda *a, **k: muc)
    monkeypatch.setattr(bc, "doc_flores", lambda *a, **k: [])
    # `lat_nghia` bi BAT o ca 2 luot; `sai_thuc_the` khong bi bat lan nao.
    monkeypatch.setattr(bc, "cham_mot_luot", lambda db, m: _luot(
        tiem_lat_nghia_0500=False, tiem_sai_thuc_the_0501=True))

    ra = bc.ti_le_bat_loi_tiem(db=None, moi_loai=1, bo_qua=0, luot=2)
    ln = ra["theo_loai"]["lat_nghia"]
    st = ra["theo_loai"]["sai_thuc_the"]
    assert ln["ti_le_trung_vi"] == 1.0 and ln["ti_le_tung_luot"] == [1.0, 1.0]
    assert ln["dat_nguong_mach"] is True
    assert st["ti_le_trung_vi"] == 0.0 and st["ti_le_tung_luot"] == [0.0, 0.0]
    assert st["dat_nguong_mach"] is False


# ══════════════════════════════════════════════════════════════════════════════
#  5. Lo HONG khong duoc doc thanh "khong co loi nao"
# ══════════════════════════════════════════════════════════════════════════════

def test_lo_hong_KHONG_duoc_dem_la_dat(monkeypatch):
    """⚠️ "Khong hoi duoc" khac han "da hoi va khong thay gi".

    `qc_ai.doc_ngu_nghia` mac dinh ma thieu la `dat`; neu `cham_mot_luot` cung
    lam vay thi ti le bao dong gia se **dep len** moi lan cong loi — tuc cong
    cang hong, bo cham cang trong dang tin.
    """
    from apps.auto_scan_video import ai

    def no(*a, **k):
        raise ai.AiError("cong tu choi")

    monkeypatch.setattr(ai, "goi", no)
    ra = bc.cham_mot_luot(None, [{"ma": "m1", "goc": "源", "chu": "v"}])
    assert ra["phan_quyet"] == {}
    assert len(ra["loi_lo"]) == 1 and "AiError" in ra["loi_lo"][0]["loi"]
    assert bc.gop_trung_vi([ra], ["m1"]) == {}


# ══════════════════════════════════════════════════════════════════════════════
#  6. Phan quyet in ra phai lat dung o nguong
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("ti_le,mong", [
    (0.15, "DANG TIN"), (0.1501, "sua BO CHAM"), (0.46, "sua BO CHAM")])
def test_bao_cao_lat_phan_quyet_dung_o_nguong(ti_le, mong):
    van = bc.bao_cao({"bao_dong_gia": {
        "n_hoi": 100, "n_co_phan_quyet": 100, "ti_le_trung_vi": ti_le,
        "dai": [ti_le, ti_le], "luot": 3}})
    assert mong in van


def test_bao_cao_KEU_LEN_khi_mu_o_mot_loai():
    van = bc.bao_cao({
        "bao_dong_gia": {"n_hoi": 100, "n_co_phan_quyet": 100,
                         "ti_le_trung_vi": 0.02, "dai": [0.0, 0.04], "luot": 3},
        "bat_loi_tiem": {"luot": 3, "theo_loai": {"lat_nghia": {
            "n_hoi": 15, "n_co_phan_quyet": 15, "ti_le_trung_vi": 0.2,
            "dai": [0.2, 0.2], "dat_nguong_mach": False}}}})
    assert "MU o `lat_nghia`" in van


# ══════════════════════════════════════════════════════════════════════════════
#  7. FLORES — hai tep lech dong thi DUNG
# ══════════════════════════════════════════════════════════════════════════════

def test_doc_flores_DUNG_khi_hai_tep_lech_so_dong(tmp_path):
    """Hai tep lech mot dong lam MOI cap sai, va moi phan quyet "dich sai" sau
    do la THAT — tuc phep do tu bien thanh mot phep do ve chinh no."""
    d = tmp_path / "dev"
    d.mkdir()
    (d / "zho_Hans.dev").write_text("一\n二\n三\n", encoding="utf-8")
    (d / "vie_Latn.dev").write_text("mot\nhai\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        bc.doc_flores(tmp_path)


def test_doc_flores_ghep_theo_CHI_SO_DONG(tmp_path):
    d = tmp_path / "dev"
    d.mkdir()
    (d / "zho_Hans.dev").write_text("一\n二\n", encoding="utf-8")
    (d / "vie_Latn.dev").write_text("mot\nhai\n", encoding="utf-8")
    assert bc.doc_flores(tmp_path) == [(0, "一", "mot"), (1, "二", "hai")]
