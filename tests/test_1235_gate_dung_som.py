"""test_1235 — `gate.py --dung-som`: dung o loi RE dau tien, va NOI RA.

## Bat bien

1. Mot buoc **re** do ⇒ cac buoc **dat** (`bo test`, `bat bien da tien trinh`)
   **khong chay**.
2. Moi buoc re van chay het — `--dung-som` cat o **ranh gioi nhom**, khong cat
   giua chung. Chay het nhom re la thu lam no huu dung: mot luot cho ta TAT CA
   loi tinh, khong phai cai dau tien.
3. Khong co loi re ⇒ nhom dat chay binh thuong (che do nay khong duoc bot viec
   khi moi thu on).
4. ⛔ Buoc chua chay **khong** duoc dem la FAIL, va **khong** duoc dem la PASS.
   No la trang thai thu ba, va dong RESULT phai noi ra.

## Vi sao (4) la ca quan trong nhat

Gate co mot luat da viet ra tu truoc, o ba cho khac nhau: *"mot luot chay it hon
thi DONG KET QUA cua no phai trong khac"* — vi dong RESULT la thu duy nhat duoc
doc khi nguoi ta voi. Ngay 31/08 hai phien doc cung mot dong `PASS 25/25` theo
hai cach trai nguoc, vi mot buoc da tu bo qua ma dong RESULT khong he noi.

`--dung-som` sinh ra dung cai rui ro do, chi khac chieu: neu buoc chua chay bi
gop vao PASS thi `FAIL (1/33)` cua mot luot bi cat va cua mot luot day du trong
Y HET nhau — trong khi luot dau **khong chung minh** gi ve `bo test` ca.

Do 12/09/2026 lam co so cho che do nay: 3 buoc chiem 95,3% (bo test 735,5s ·
bat bien 302,4s · mypy 124,0s), 30 buoc con lai cong lai 58,1s. Gate biet minh
FAIL tu giay 159 roi van chay them 575 giay.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import gate  # noqa: E402


def _buoc(ten: str, nhom: str, ok: bool):
    """Mot `Step` gia: `_chay_theo_lich` chi goi `_run`, nen ta thay `_run`."""
    s = gate.Step(ten, [sys.executable, "-c", "pass"], gate.ROOT, nhom=nhom)
    s._ket_gia = ok                                          # type: ignore[attr-defined]
    return s


def _chay(steps, monkeypatch, **kw):
    da_chay: list[str] = []

    def _run_gia(step):
        da_chay.append(step.name)
        step.ok = bool(getattr(step, "_ket_gia", True))
        step.seconds = 0.0
        step.bo_qua = False
        step.tail = ""

    monkeypatch.setattr(gate, "_run", _run_gia)
    gate._chay_theo_lich(steps, j=4, tuan_tu=False, **kw)
    return da_chay


def test_loi_o_nhom_re_thi_nhom_dat_KHONG_chay(monkeypatch):
    steps = [_buoc("bien dich duoc", "cong", True),
             _buoc("mypy", "tinh", False),
             _buoc("ruff", "tinh", True),
             _buoc("bo test (song song)", "nang", True),
             _buoc("bat bien da tien trinh", "nang", True)]
    da_chay = _chay(steps, monkeypatch, dung_som=True)

    assert "bo test (song song)" not in da_chay, (
        "buoc DAT nhat van chay du mot buoc re da do — `--dung-som` khong an")
    assert "bat bien da tien trinh" not in da_chay

    # (2) moi buoc RE van chay het.
    assert "ruff" in da_chay, (
        "`--dung-som` cat giua nhom re — no phai cat o RANH GIOI NHOM, de mot "
        "luot van cho ta TAT CA loi tinh")


def test_buoc_chua_chay_KHONG_phai_FAIL_va_KHONG_phai_PASS(monkeypatch):
    """⛔ Trang thai thu ba. Gop nham vao PASS la bao mot bang chung khong co."""
    steps = [_buoc("mypy", "tinh", False),
             _buoc("bo test (song song)", "nang", True)]
    _chay(steps, monkeypatch, dung_som=True)

    bo_test = [s for s in steps if s.nhom == "nang"][0]
    assert bo_test.ok is None, (
        f"buoc chua chay phai giu `ok is None`, dang la {bo_test.ok!r}")
    assert [s for s in steps if s.ok is False] == [steps[0]], (
        "chi buoc THAT SU do moi duoc dem la FAIL")


def test_khong_loi_re_thi_nhom_dat_VAN_chay(monkeypatch):
    """Che do nay khong duoc bot viec khi moi thu on."""
    steps = [_buoc("mypy", "tinh", True),
             _buoc("bo test (song song)", "nang", True)]
    da_chay = _chay(steps, monkeypatch, dung_som=True)
    assert "bo test (song song)" in da_chay
    assert all(s.ok is True for s in steps)


def test_mac_dinh_VAN_chay_het_du_co_loi(monkeypatch):
    """🔴 ĐỐI CHỨNG NGƯỢC. Mac dinh phai giu nguyen tac 'chay het roi moi bao'.

    Khong co ca nay thi mot ban sua lam `--dung-som` thanh mac dinh se qua het
    ba ca tren — va lam moi luot PHAN QUYET mat kha nang bao **moi** loi trong
    mot lan chay.
    """
    steps = [_buoc("mypy", "tinh", False),
             _buoc("bo test (song song)", "nang", True)]
    da_chay = _chay(steps, monkeypatch)          # KHONG truyen dung_som
    assert "bo test (song song)" in da_chay, (
        "mac dinh da bi doi thanh dung som — xem `NHOM_RE`, day la mot CO")


def test_mot_buoc_DAT_do_thi_buoc_DAT_ke_tiep_KHONG_chay(monkeypatch):
    """🔴 CHU SAN PHAM CHI RA 13/09/2026, va do duoc ngay trong luot gate ay.

    Cac buoc `nang` **khong** chay song song that: `bo test` an gan het ngan
    sach loi, nen `bat bien da tien trinh` xep hang sau no:

        00:46:49  `bo test` DO (725,6s)  -> phan quyet da la FAIL
        00:46:49  `bat bien` MOI khoi dong, chay them 302s

    Nguoi bam thay dong cuoi cung tu 5 phut truoc va tuong gate da xong. No
    chua — no dang tra tien cho mot buoc khong con doi duoc ket qua.

    ⛔ Phep loc phai nam SAU khi giu duoc ngan sach, khong o vong nop: luc nop,
       `bo test` chua do.
    """
    do_truoc = _buoc("bo test (song song)", "nang", False)
    sau = _buoc("bat bien da tien trinh", "nang", True)
    da_chay = _chay([do_truoc, sau], monkeypatch, dung_som=True)

    assert "bo test (song song)" in da_chay
    assert "bat bien da tien trinh" not in da_chay, (
        "buoc DAT thu hai van chay du buoc DAT thu nhat da do")
    assert sau.ok is None, "buoc bi cat phai giu `ok is None`, khong phai FAIL"


def test_mot_nhom_RONG_khong_lam_vo_lich(monkeypatch):
    """🔴 HOI QUY THAT 13/09/2026, bat duoc khi chay `--quick --dung-som`.

    `--quick` bo ca hai buoc `nang`, nen nhom DAT rong. Ban dau ham van goi
    `_chay_theo_lich([])`, va `ThreadPoolExecutor(max_workers=min(0, j))` nem
    `ValueError: max_workers must be greater than 0` — gate chet **sau khi da
    chay xong 24/24 buoc**, tuc mat trang ca luot do vi mot phep chia cho khong.

    ⛔ Ca nay phai kiem CA HAI chieu rong: mot ho so chi co buoc nang (vd mot
       `--pham-vi` hep) lam nhom RE rong theo dung kieu ay.
    """
    chi_re = [_buoc("mypy", "tinh", True), _buoc("ruff", "tinh", True)]
    assert _chay(chi_re, monkeypatch, dung_som=True) != []

    chi_dat = [_buoc("bo test (song song)", "nang", True)]
    assert _chay(chi_dat, monkeypatch, dung_som=True) == ["bo test (song song)"]

    assert _chay([], monkeypatch, dung_som=True) == []

    # 🔴 Ca THAT da lam vo `--quick --dung-som`: nhom DAT khong rong, nhung no
    #    chi gom `sau_test` — nen BEN TRONG lich, `nang` va `nhe` deu rong.
    #    Mot phep phong thu o vong ngoai KHONG du; phai phong thu o dung cho
    #    `ThreadPoolExecutor` duoc dung.
    chi_sau = [_buoc("migration tren postgres", "sau_test", True)]
    assert _chay(chi_sau, monkeypatch, dung_som=True) == ["migration tren postgres"]
    assert _chay(chi_sau, monkeypatch) == ["migration tren postgres"]


def test_dong_RESULT_khai_so_buoc_chua_chay():
    """Dong RESULT phai TU KHAI, cung luat da ap cho `--quick` va cay-doi."""
    ma = (gate.ROOT / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "DUNG SOM:" in ma and "KHONG PHAI" in ma, (
        "dong RESULT khong khai so buoc chua chay — mot luot bi cat se trong "
        "y het mot luot day du")


def test_NHOM_RE_khong_chua_buoc_dat():
    """Ba buoc dat nhat (do 12/09) phai nam NGOAI nhom re, neu khong co nay vo nghia."""
    assert "nang" not in gate.NHOM_RE
    assert "sau_test" not in gate.NHOM_RE
    steps = gate._steps(False)
    ten_re = {s.name for s in steps if s.nhom in gate.NHOM_RE}
    for dat in ("bo test (song song)", "bat bien da tien trinh"):
        assert dat not in ten_re, f"`{dat}` bi xep vao nhom RE"
