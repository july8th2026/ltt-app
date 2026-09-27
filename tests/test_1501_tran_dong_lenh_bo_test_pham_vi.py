"""L2 `--pham-vi` KHONG duoc chet vi tran do dai dong lenh cua Windows.

🔴 **SU CO 28/09/2026.** `gate.py --pham-vi` voi 23 thanh phan (mot diff cham
   `governance.py` + `manifest.py`, hai tep ca nen tang tieu thu) sinh **1067**
   duong test = **41 335 ky tu**, vuot tran **32 767** cua `CreateProcess`:

       [FAIL] bo test (pham vi)   0.0s
       khong chay duoc: [WinError 206] The filename or extension is too long

⭐ **Vi sao phep kiem nay ton tai thay vi mot dong `assert`.** `FAIL 0.0s` doc
   **y het** mot phep kiem do, nen no day nguoi ta di tim con bo trong MA. Hai
   cua cua gate cung dan toi mot ket cuc **khong co do phu**: L1 im lang qua
   `[HA CAP ... BO TEST KHONG CHAY]`, L2 on ao qua mot dong FAIL **sai nguyen
   nhan**. Mot cong chat luong khong do duoc gi ma van in mot phan quyet la
   dieu dat nhat trong ca ho so nay.

⛔ Va day la cho de "sua" sai nhat: thu hep pham vi cho vua tran. Pham vi la
   thu `thanh_phan.py` **do duoc**, khong phai thu ta chon cho vua cong cu —
   thu hep no lam loi tuyen bo rong hon phep do.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "tools"))

import test_nhanh as tn  # noqa: E402

#: Tran that cua `CreateProcess`. ⛔ Khong go lai so nay o cho khac.
TRAN_WINDOWS = 32767

#: Do do duoc 28/09: 1067 duong = 41 335 ky tu, tran cham o ~844 tep.
SO_TEP_DO_THAT = 1067


def _gia_lap_duong(n: int) -> list[str]:
    """`n` duong test CO THAT, lap lai tu nhung tep dang co trong `tests/`.

    ⛔ KHONG dung ten bia: `gom_duong_qua_dai` co y tu choi duong khong ton tai,
       nen mot danh sach bia se do vi ly do khac han cai ta dang do.
    """
    that = sorted(p.name for p in (GOC / "tests").glob("test_*.py"))
    assert len(that) >= 100, "kho nay phai co it nhat 100 tep test"
    return [f"tests/{that[i % len(that)]}" for i in range(n)]


def test_ke_hoach_pha_voi_1067_duong_cho_argv_DUOI_tran():
    """Phep do chinh: dung so tep da lam gate chet, argv phai vua tran."""
    duong = _gia_lap_duong(SO_TEP_DO_THAT)
    pha1, _ = tn.ke_hoach_pha(duong, "7")
    assert pha1 is not None
    do_dai = sum(len(a) + 1 for a in pha1)
    assert do_dai < TRAN_WINDOWS, (
        f"argv pha 1 dai {do_dai} ky tu >= tran {TRAN_WINDOWS} — "
        f"`gate.py --pham-vi` se chet bang [WinError 206]")
    assert sum(1 for a in pha1 if a.startswith("@")) == 1, \
        "phai gom thanh dung MOT doi so @tep"


def test_TIEM_LOI_khong_gom_thi_argv_VUOT_tran(monkeypatch):
    """Doi chung: bo co che gom => phep do tren PHAI do.

    ⭐ Khong co buoc nay thi `test_..._DUOI_tran` co the dang xanh vi mot ly do
       khong lien quan (vi du `ke_hoach_pha` doi hinh va khong con nhan duong
       nao ca). Do vang mat cua mot co che ⛔ khong phai bang chung no hoat dong.
    """
    monkeypatch.setattr(tn, "gom_duong_qua_dai", lambda d, **_: d)
    pha1, _ = tn.ke_hoach_pha(_gia_lap_duong(SO_TEP_DO_THAT), "7")
    assert pha1 is not None
    do_dai = sum(len(a) + 1 for a in pha1)
    assert do_dai > TRAN_WINDOWS, (
        f"tiem loi ma argv chi dai {do_dai} — phep kiem tren khong con do duoc "
        f"dieu gi, vi ca hai nhanh deu vua tran")


def test_danh_sach_NGAN_thi_giu_nguyen_duong():
    """Duoi nguong thi ⛔ khong gom: mot `@tep` lam thong bao loi kho doc hon."""
    duong = _gia_lap_duong(5)
    assert tn.gom_duong_qua_dai(duong) == duong


def test_duong_KHONG_TON_TAI_thi_NEM_chu_khong_teo_pham_vi_im_lang():
    """⛔ Pytest doc `@tep` co duong sai thi in `no tests collected` va IM.

    Do 28/09: `@tep` mot duong that = 4 test, hai duong = 9 test, mot duong bia
    = **0 test va khong mot dong loi**. Nen bat buoc kiem o BIEN, truoc khi ghi.
    """
    duong = _gia_lap_duong(SO_TEP_DO_THAT)
    duong[500] = "tests/test_khong_he_ton_tai_9999.py"
    with pytest.raises(SystemExit, match="KHONG ton tai"):
        tn.gom_duong_qua_dai(duong)


def test_atep_thu_thap_DUNG_TAP_nhu_truyen_duong_truc_tiep(tmp_path):
    """Phep do that: `@tep` va danh sach truc tiep cho CUNG so test thu thap.

    Day la cho duy nhat chung minh `@tep` **tuong duong**, chu khong chi "chay
    duoc". Chay pytest thiet, hai luot, chi 2 tep nen re.
    """
    hai = ["tests/test_1501_tran_dong_lenh_bo_test_pham_vi.py",
           "tests/test_394_nen_da_phien.py"]
    ds = tmp_path / "duong.txt"
    ds.write_text("\n".join(hai) + "\n", encoding="utf-8")

    def dem(doi_so: list[str]) -> int:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q",
                            "--collect-only", *doi_so],
                           cwd=GOC, capture_output=True, text=True)
        for dong in reversed(r.stdout.splitlines()):
            if "tests collected" in dong or "test collected" in dong:
                return int(dong.split()[0])
        raise AssertionError(f"khong doc duoc so test thu thap:\n{r.stdout[-800:]}")

    truc_tiep = dem(hai)
    qua_tep = dem([f"@{ds}"])
    assert truc_tiep == qua_tep > 0, \
        f"@tep thu thap {qua_tep} test, truyen truc tiep {truc_tiep}"


def test_steps_pham_vi_khong_bao_gio_dung_argv_dai(monkeypatch):
    """Chan gate.py -> test_nhanh.py cung phai duoi tran, ⛔ khong chi chan sau.

    Tran cham o CA HAI cho spawn. Va 26/09 toi da tin mot chan vi do chan kia.
    """
    sys.path.insert(0, str(GOC / "tools"))
    import gate

    monkeypatch.setattr(gate, "loi_cho_bo_test", lambda **_: 7)
    [buoc] = gate._steps_pham_vi(_gia_lap_duong(SO_TEP_DO_THAT))
    do_dai = sum(len(a) + 1 for a in buoc.argv)
    assert do_dai < TRAN_WINDOWS, f"argv gate dai {do_dai} ky tu"
    assert "-n" in buoc.argv, "ngan sach worker phai con (su co 17/09)"
