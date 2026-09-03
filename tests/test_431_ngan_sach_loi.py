"""Ngan sach loi cua `gate.py` la GIOI HAN TREN, khong phai mot phep gan.

## Loi that ma tep nay chot lai — do 2026-09-03

        os.cpu_count()            = 20   loi LOGIC
        psutil.cpu_count(False)   = 10   loi VAT LY   <- xdist `auto` dung so nay
        gate truyen  -n           = 11

`ngan_sach_loi()` tinh tren loi **logic**, xdist `auto` tinh tren loi **vat ly**,
va ca hai bi tru cung hang so `LOI_DE_DANH_CHO_MAY = 6`. Nen mot co che sinh ra
de **giam** tai lai dang **tang** no.

⭐ Tren may khong sieu phan luong, hai so trung nhau va loi nay khong ton tai.
   No chi lo ra o may co SMT. Nen phep kiem duoi day **gia lap nhieu hinh may**
   thay vi chi kiem may dang chay — mot phep kiem chi chay tren may nay se xanh
   o nua so may va khong ai biet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import gate  # noqa: E402


def _n_truyen_cho_pytest() -> int:
    """Dung LAI dung phep tinh o `gate.py`, khong chep so.

    ⚠️ Neu mai nay `gate.py` doi phep tinh nay ma tep test giu mot ban chep, thi
       phep kiem se chot mot thu khong con ai chay. Doc lai tu chinh module.
    """
    return max(1, min(gate.LOI_TOI_DA_MOI_CONG_CU,
                      gate.ngan_sach_loi() - len(gate.FRONTENDS),
                      gate.loi_cong_cu_tu_do()))


def test_n_khong_bao_gio_vuot_so_xdist_tu_chon():
    """🔑 Bat bien chinh: ngan sach la TRAN, khong duoc thanh SAN."""
    assert _n_truyen_cho_pytest() <= gate.loi_cong_cu_tu_do()


@pytest.mark.parametrize("logic,vat_ly", [
    (20, 10),   # may nay — SMT, va la hinh may loi da song
    (16, 8),
    (8, 4),
    (4, 4),     # khong SMT: hai so trung nhau, loi khong the lo ra
    (2, 1),
    (64, 32),
])
def test_moi_hinh_may_deu_ton_trong_tran(monkeypatch, logic, vat_ly):
    """Gia lap nhieu may, vi loi nay chi lo ra o may co SMT.

    ⛔ Mot phep kiem chi chay tren may hien tai se xanh o nua so cau hinh va
       khong noi gi ve nua kia. `LOI_DE_DANH_CHO_MAY` cung bi keo theo — tren may
       4 loi, `20-6` va `4-6` cho hai the gioi khac han.
    """
    monkeypatch.setattr(gate.os, "cpu_count", lambda: logic)
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: vat_ly)

    n = _n_truyen_cho_pytest()
    assert n <= vat_ly, f"may {logic}/{vat_ly}: truyen -n {n} > auto {vat_ly}"
    assert n >= 1, "khong duoc tra ve 0 worker"


def test_chot_nay_THAT_SU_bat_duoc_ban_gan_thang(monkeypatch):
    """Chung minh phep kiem tren khong phai mot den xanh noi vao khong.

    Tai hien **ban truoc khi sua**: bo ve `loi_cong_cu_tu_do()` ra khoi `min`.
    Neu no van xanh thi phep kiem o tren dang do mot thu khac.
    """
    monkeypatch.setattr(gate.os, "cpu_count", lambda: 20)
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)

    ban_cu = max(1, min(gate.LOI_TOI_DA_MOI_CONG_CU,
                        gate.ngan_sach_loi() - len(gate.FRONTENDS)))
    assert ban_cu == 11, "ban cu phai tai hien dung con so 11 da do duoc"
    assert ban_cu > gate.loi_cong_cu_tu_do(), (
        "ban cu phai VUOT tran — neu khong thi khong co gi de sua")

    # Va ban moi thi khong.
    assert _n_truyen_cho_pytest() == 10


def test_loi_cong_cu_tu_do_doc_cung_nguon_voi_xdist():
    """Neu hai ben doc hai nguon khac nhau thi chung se lech lai, im lang.

    ⭐ `xdist/plugin.py:32` goi `psutil.cpu_count(logical=use_logical)`, va chi
       roi ve `os.cpu_count()` khi khong co psutil (`plugin.py:46`). Ham cua ta
       phai co dung hai nhanh do.
    """
    import inspect

    nguon = inspect.getsource(gate.loi_cong_cu_tu_do)
    assert "psutil" in nguon
    assert "logical=False" in nguon
    assert "os.cpu_count" in nguon, "thieu nhanh du phong khi khong co psutil"


def test_khong_tra_ve_0_khi_may_rat_nho(monkeypatch):
    """`max(1, ...)`: mot may 2 loi van phai chay duoc, chi la cham hon.

    Tu choi chay van la kieu hong te hon cham — cung luan cu voi
    `ngan_sach_loi()` giu `max(2, ...)`.
    """
    monkeypatch.setattr(gate.os, "cpu_count", lambda: 2)
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 1)
    assert _n_truyen_cho_pytest() == 1
