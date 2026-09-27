"""`to_tien_da_giu_khoa` phai nhan ra `chay_nang.py` la mot to tien DA giu khoa.

🔴 VI SAO CO TEP NAY — MOT CA KHOA CHET DA XAY RA THAT (26/09/2026)

   `tests/conftest.py` tu xin `cpu_nhieu` khi luot co >= `_NGUONG_TEP_NANG` tep,
   va bo qua khi mot TO TIEN da xin ho. Danh sach to tien duoc viet tu goc nhin
   cua kho: `gate.py`, `test_nhanh.py`. Nhung `chay_nang.py` — cong cu ma brief
   agent bat moi lan chay lenh nang phai di qua — song NGOAI kho
   (`~/.claude/ltt/`), nen khong nam trong danh sach.

       chay_nang.py giu cpu_nhieu
         └─ pytest (26 tep)
              └─ conftest xin cpu_nhieu  ->  CHO MAI

   Khoa la tep `O_EXCL`, khong tai nhap.

⭐ PHEP KIEM NAY DO MOT TINH CHAT, KHONG DO CACH GO

   No hoi: "mot to tien la `chay_nang.py` thi ta co bo qua viec xin khoa khong?"
   Doi ten hang so, doi thu tu tuple, them cong cu thu tu — phep kiem nay van
   dung. ⛔ No KHONG khang dinh noi dung cua `kich_ban`.

⚠️ Vi sao khong the bat bang mot luot pytest binh thuong: ca khoa chet chi no khi
   >= 20 tep, va mot luot nhu vay giu khoa that. Nen ta tiem `to_tien` tuong minh
   — tham so do ton tai dung de kiem duoc ma khong phai dung tien trinh that.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from test_nhanh import to_tien_da_giu_khoa  # noqa: E402

#: Hinh dang to tien THAT, do tu `psutil`: (ten tien trinh, cmdline).
#: `chay_nang.py` luon chay dang `python <duong dan>/chay_nang.py --phien X -- ...`
CHAY_NANG = ("python.exe", [
    r"C:\Users\Thang Tuong\AppData\Local\Programs\Python\Python313\python.EXE",
    r"C:\Users\Thang Tuong\.claude\ltt\chay_nang.py",
    "--phien", "pha3-M3", "--", "python", "-m", "pytest",
])
GATE = ("python.exe", ["python", "tools/gate.py", "--doi"])
TEST_NHANH = ("python.exe", ["python", "tools/test_nhanh.py", "-n", "6"])
#: To tien KHONG giu khoa ho: mot shell, va mot pytest go tay.
SHELL = ("bash.exe", ["bash", "-c", "python -m pytest tests/"])
PYTEST_TAY = ("python.exe", ["python", "-m", "pytest", "tests/"])


@pytest.mark.parametrize("to_tien,mong_doi", [
    pytest.param([CHAY_NANG], True, id="chay_nang-phai-duoc-nhan-ra"),
    pytest.param([GATE], True, id="gate-van-duoc-nhan-ra"),
    pytest.param([TEST_NHANH], True, id="test_nhanh-van-duoc-nhan-ra"),
    pytest.param([SHELL], False, id="shell-KHONG-giu-khoa-ho"),
    pytest.param([PYTEST_TAY], False, id="pytest-go-tay-KHONG-giu-khoa-ho"),
    pytest.param([], False, id="khong-to-tien-nao"),
])
def test_nhan_dung_to_tien_nao_da_giu_khoa(to_tien, mong_doi):
    assert to_tien_da_giu_khoa(to_tien=to_tien) is mong_doi


def test_chay_nang_lan_trong_chuoi_to_tien_van_duoc_nhan_ra():
    """That te `chay_nang.py` khong phai to tien TRUC TIEP cua pytest.

    Chuoi that: bash -> chay_nang.py -> python <script> -> pytest. Neu phep hoi
    chi xet to tien gan nhat thi no bo sot dung ca da gay khoa chet.
    """
    chuoi = [PYTEST_TAY, ("python.exe", ["python", "nghiem_thu.py"]),
             CHAY_NANG, SHELL]
    assert to_tien_da_giu_khoa(to_tien=chuoi) is True


def test_doi_chung_chuoi_dai_ma_KHONG_co_cong_cu_nao_thi_False():
    """Tiem loi: bo `chay_nang` khoi chuoi tren thi phai tra False.

    Khong co phep doi chung nay thi phep tren co the xanh chi vi ham luon tra
    True cho moi chuoi dai — `khong-doi-chung-thi-so-khong-khong-phai-phat-hien`.
    """
    chuoi = [PYTEST_TAY, ("python.exe", ["python", "nghiem_thu.py"]), SHELL]
    assert to_tien_da_giu_khoa(to_tien=chuoi) is False


def test_conftest_dung_DUNG_ham_nay_chu_khong_chep_phep_hoi():
    """⛔ Hai ban sao cua cung mot phep hoi la hai cho de chung lech nhau.

    Docstring cua `to_tien_da_giu_khoa` tu noi dieu do. Phep kiem nay ep no
    thanh su that co may kiem, khong phai mot loi hua trong binh luan.
    """
    nguon = (Path(__file__).resolve().parent / "conftest.py").read_text(
        encoding="utf-8")
    assert "to_tien_da_giu_khoa" in nguon, (
        "conftest phai DUNG LAI ham nay, khong tu viet phep hoi rieng")
    # ⛔ Va no khong duoc tu chep danh sach cong cu: mot tuple `kich_ban` thu hai
    #    trong conftest la cho de hai ban lech nhau, dung cai docstring canh bao.
    assert "kich_ban" not in nguon, (
        "conftest dang tu khai `kich_ban` — phai dung mac dinh cua "
        "`to_tien_da_giu_khoa`, neu khong hai cho se lech")
