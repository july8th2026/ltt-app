"""Boc `pytest` trong mot lop giu `cpu_nhieu` = TU KHOA CHINH MINH.

🔴 **Su co do duoc (Task 24).** `tests/conftest.py` tu xin khoa may `cpu_nhieu`
   khi mot luot pytest cham **>= 20 tep**, va no bo qua viec xin neu to tien la
   `gate.py` / `test_nhanh.py`. Ba luot do cung mot may:

       18 tep qua `chay_nang.py`  ->  132 passed   (duoi nguong, khong xin)
       12 tep qua `chay_nang.py`  ->   51 passed   (duoi nguong)
       26 tep qua `chay_nang.py`  ->  TREO MAI, CPU ~ 0

   Khoa cua `cua_so_yen` la mot tep `O_EXCL` — **khong tai nhap**. Nen lop boc
   giu khoa, roi `conftest` xin **lai chinh khoa do**, va cho chinh to tien cua
   minh het `cho_toi_da_s = 900` giay.

⛔ **Vi sao mot dong them vao danh sach la KHONG DU.** `chay_nang.py` song
   **ngoai kho** (`~/.claude/ltt/`), nen ma trong kho khong thay no ton tai —
   danh sach `kich_ban` khong the tu day du duoc bang cach doc kho. Tep nay la
   **banh coc**: no di TIM moi lop boc vua giu `cpu_nhieu` vua phong pytest, va
   doi moi cai tim duoc phai **duoc phan loai** — hoac trong `KICH_BAN_GIU_KHOA`,
   hoac trong `NGOAI_LE` kem ly do. Mot lop boc moi khong o ca hai cho ⇒ DO.

⚠️ Trieu chung ("treo, CPU 0, tai hien duoc") **giong het** ba con bo khac trong
   phien 26/09, nen no rat de bi chan doan nham thanh loi nghiep vu. Mot phien
   da mat gan mot buoi vi no ⇒ them mot cua **chan doan duoc** (`test_CHAN_DOAN`).
"""
from __future__ import annotations

import ast
import pathlib
import socket
import sys
import warnings

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "tools"))

#: Lop boc GIU `cpu_nhieu` nhung phong pytest **ngoai** khoa ⇒ ⛔ KHONG duoc vao
#: `kich_ban`. Dat o day, khong o `test_nhanh.py`, vi day la mot ghi chu cua
#: phep kiem — dua vao danh sach san xuat thi no thanh mot lo hong that.
#:
#: 🔴 Chieu hong nguy hiem la chieu **bo lot**: mot ten trong `kich_ban` lam
#:    `conftest` **thoi xin khoa**. Neu lop boc ay khong thuc su giu khoa luc no
#:    phong pytest thi mot luot 26 tep chay **khong khoa nao** — dung tai nan
#:    dem 05-06/09 mo lai.
NGOAI_LE = {
    "cay_gate.py":
        "giu `cpu_nhieu` CHI quanh `npm ci` (dong 243); no phong `tools/gate.py` "
        "o dong 283 NGOAI moi khoa, va `gate.py` tu xin khoa cua no — nen "
        "`gate.py` (da co trong danh sach) moi la to tien giu khoa, khong phai "
        "tep nay.",
}

#: Thu muc chua lop boc **ngoai kho**. Chinh su ton tai cua no la ly do banh coc
#: nay can thiet: ma trong kho khong the `grep` ra thu nam ngoai kho.
THU_MUC_NGOAI_KHO = pathlib.Path.home() / ".claude" / "ltt"


def _doc_tep(p: pathlib.Path) -> tuple[bool, list[str], bool, bool] | None:
    """(giu_cpu_nhieu, cac token chuoi, co REMAINDER, co dinh nghia CuaSoYen)."""
    try:
        # ⚠️ `simplefilter` vi mot so script ngoai kho co escape la (`"\c"`) va
        #    `ast.parse` phat SyntaxWarning tu `<unknown>:4` — mot dong nhieu
        #    khong truy duoc chu, de bi doc thanh loi cua phep kiem nay.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cay = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return None
    giu = rem = dinh_nghia = False
    token: list[str] = []
    for n in ast.walk(cay):
        if isinstance(n, ast.ClassDef) and n.name == "CuaSoYen":
            dinh_nghia = True
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            s = n.value
            # ⭐ Chi lay **token lenh** (khong khoang trang). Van xuoi trong
            #    docstring nhac chu "pytest" thi khong phai mot lop boc — do la
            #    ca lam `tools/cua_so_yen.py` bi bat oan o ban dau cua phep kiem.
            if s and not any(c.isspace() for c in s):
                token.append(s)
        if isinstance(n, ast.Attribute) and n.attr == "REMAINDER":
            rem = True
        if isinstance(n, ast.Call):
            for kw in n.keywords:
                if kw.arg != "tai_nguyen":
                    continue
                if isinstance(kw.value, ast.Name):   # hang so cung tep
                    giu = True
                for e in getattr(kw.value, "elts", []) or []:
                    if isinstance(e, ast.Constant) and e.value == "cpu_nhieu":
                        giu = True
            f = n.func
            ten = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if ten == "CuaSoYen" and not any(k.arg == "tai_nguyen"
                                             for k in n.keywords):
                giu = True                            # mac dinh la `cpu_nhieu`
    return giu, token, rem, dinh_nghia


def tim_lop_boc() -> dict[str, str]:
    """{ten tep: ly do} moi script vua co the giu `cpu_nhieu` vua phong pytest.

    ⚠️ Phep do nay o muc **TEP**, khong o muc **thoi diem**: no tra loi *"tep nay
       co ca hai kha nang khong"*, chu khong tra loi *"no co giu khoa DUNG LUC no
       phong pytest khong"*. Cau thu hai can luong chay, va `gate.py` khai khoa
       **khai bao** (`Step(tai_nguyen=...)`) nen khong long nhau theo cu phap.
       Vi vay ket qua phai di qua `NGOAI_LE` — con nguoi phan loai, may thi chot
       rang **khong ai bi bo quen**.
    """
    ung: dict[str, tuple[list[str], bool]] = {}
    for d in (GOC / "tools", THU_MUC_NGOAI_KHO):
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.py")):
            r = _doc_tep(p)
            if r and r[0] and not r[3]:
                ung[p.name] = (r[1], r[2])
    ket: dict[str, str] = {}
    for ten, (token, rem) in ung.items():
        vi = [t for t in token if "pytest" in t]
        if rem:
            vi.append("nhan lenh bat ky qua argparse.REMAINDER")
        if vi:
            ket[ten] = vi[0]
    doi = True
    while doi:                                  # bac cau: gate.py -> test_nhanh.py
        doi = False
        for ten, (token, _rem) in ung.items():
            if ten in ket:
                continue
            for s in token:
                if s.replace(chr(92), "/").split("/")[-1] in ket:
                    ket[ten] = f"phong {s}"
                    doi = True
                    break
    return ket


# -- Bug A, phep kiem DO: to tien la `chay_nang.py` / `do_phu_diff.py` --------

def _to_tien(duong: str, *them: str) -> list[tuple]:
    """Mot to tien gia lap: (ten tien trinh, argv). ⭐ Cua tiem cua
    `to_tien_da_giu_khoa` — de phep kiem chot **tinh chat cua ma**, khong chot
    mot su that moi truong ("luot nay tinh co khong chay duoi gate")."""
    return [("python.exe", ["python", duong, *them])]


def test_DO_chay_nang_phai_duoc_coi_la_to_tien_giu_khoa():
    """26 tep qua `chay_nang.py` treo mai vi ham nay tra False."""
    from test_nhanh import to_tien_da_giu_khoa

    to_tien = _to_tien("C:/Users/x/.claude/ltt/chay_nang.py",
                       "--phien", "lan-1", "--", "python", "-m", "pytest")
    assert to_tien_da_giu_khoa(to_tien=to_tien) is True, (
        "`chay_nang.py` giu `cpu_nhieu` roi phong pytest; `conftest` phai THOI "
        "xin khoa, khong thi no cho chinh to tien cua no 900 giay")


def test_DO_do_phu_diff_phai_duoc_coi_la_to_tien_giu_khoa():
    """Lo THU HAI, nam **trong** kho: `tools/do_phu_diff.py` giu
    `cpu_nhieu` + `postgres_test` (dong 149) roi chay
    `python -m pytest ... <pham_vi>` voi `--pham-vi` **mac dinh la `tests`** —
    tuc ca bo test, chac chan > 20 tep. Tim ra bang banh coc duoi day, khong
    bang doc tay."""
    from test_nhanh import to_tien_da_giu_khoa

    assert to_tien_da_giu_khoa(to_tien=_to_tien("tools/do_phu_diff.py")) is True


def test_BANH_COC_moi_lop_boc_tim_duoc_deu_da_duoc_phan_loai():
    """⭐ Day la thu ma "mot dong them vao danh sach" khong cho duoc.

    Mot lop boc moi (trong kho hay ngoai kho) vua giu `cpu_nhieu` vua phong
    pytest se hien ra o day va **do**, thay vi mo lai cai lo mot cach im lang.
    """
    from test_nhanh import KICH_BAN_GIU_KHOA

    tim = tim_lop_boc()
    assert tim, "khong tim thay lop boc nao — phep do da hong, khong phai may sach"
    chua_phan_loai = {k: v for k, v in tim.items()
                      if k not in KICH_BAN_GIU_KHOA and k not in NGOAI_LE}
    assert not chua_phan_loai, (
        "lop boc giu `cpu_nhieu` + phong pytest ma CHUA duoc phan loai: "
        + repr(chua_phan_loai)
        + " -> them vao `test_nhanh.KICH_BAN_GIU_KHOA` (neu no giu khoa luc "
          "phong pytest) hoac vao `NGOAI_LE` cua tep nay kem ly do")


def test_moi_ten_trong_danh_sach_phai_co_ly_do_doc_duoc():
    """Danh sach khong duoc phinh ra bang cac ten khong ai giai thich: mot ten
    thua lam `conftest` **thoi xin khoa** o mot ca that."""
    from test_nhanh import KICH_BAN_GIU_KHOA, LY_DO_KICH_BAN

    assert set(KICH_BAN_GIU_KHOA) == set(LY_DO_KICH_BAN)
    for ten, ly_do in LY_DO_KICH_BAN.items():
        assert len(ly_do) > 20, f"{ten}: ly do qua so sai"


# -- `gate.py` KHONG bi doi hanh vi ------------------------------------------

def test_gate_khong_doi_hanh_vi():
    """`gate.py` di qua `_to_tien_la_gate`, ⛔ khong qua `to_tien_da_giu_khoa`.

    Chot bang ma: cua hoi cua gate chi biet **mot** kich ban, nen viec noi dai
    danh sach kia khong voi tay sang duoc.
    """
    from test_nhanh import _to_tien_la_gate

    assert _to_tien_la_gate(to_tien=_to_tien("tools/gate.py")) is True
    assert _to_tien_la_gate(
        to_tien=_to_tien("C:/Users/x/.claude/ltt/chay_nang.py")) is False
    assert _to_tien_la_gate(to_tien=_to_tien("tools/do_phu_diff.py")) is False


def test_khong_khop_bua_bai():
    """Van con phai hoi TEN TEP DUOC THI HANH, dung hoi van ban cau lenh."""
    from test_nhanh import to_tien_da_giu_khoa

    # mot vo `bash -c "... chay_nang.py ..."` KHONG duoc tinh
    assert to_tien_da_giu_khoa(
        to_tien=[("bash.exe", ["bash", "-c", "echo chay_nang.py va pytest"])]
    ) is False
    # tien trinh khong phai python
    assert to_tien_da_giu_khoa(
        to_tien=[("cmd.exe", ["cmd", "/c", "chay_nang.py"])]) is False


# -- Cua CHAN DOAN: to tien dang giu khoa, theo PID --------------------------

def test_CHAN_DOAN_nhan_ra_to_tien_dang_giu_khoa_theo_pid():
    """⭐ Luoi cuoi, bat ca lop boc **chua ai phan loai**.

    Danh sach ten khong bao gio day du duoc (lop boc o ngoai kho). Nhung ban
    ghi khoa cua `cua_so_yen` co `pid` + `may`, va cay to tien co pid — nen
    cau hoi *"nguoi dang giu khoa co phai to tien cua toi khong"* tra loi duoc
    **khong can biet ten** no.
    """
    from test_nhanh import ai_giu_khoa_la_to_tien

    ban_ghi = {"pid": 4242, "may": socket.gethostname(),
               "lenh": "python -m pytest -n 7 tests", "phien": "lan-1"}
    mo_ta = ai_giu_khoa_la_to_tien(ban_ghi=ban_ghi, pid_to_tien=[999, 4242, 1])
    assert mo_ta, "to tien dang giu khoa ma khong noi ra"
    assert "4242" in mo_ta


def test_CHAN_DOAN_khong_bao_dong_gia():
    from test_nhanh import ai_giu_khoa_la_to_tien

    may = socket.gethostname()
    # nguoi giu khong phai to tien -> im lang (day la ca BINH THUONG: phien khac)
    assert ai_giu_khoa_la_to_tien(
        ban_ghi={"pid": 4242, "may": may}, pid_to_tien=[1, 2]) == ""
    # khong co ban ghi -> khoa dang ranh
    assert ai_giu_khoa_la_to_tien(ban_ghi=None, pid_to_tien=[1]) == ""
    # ban ghi cua MAY KHAC: pid trung so la tinh co, khong phai to tien
    assert ai_giu_khoa_la_to_tien(
        ban_ghi={"pid": 1, "may": may + "-khac"}, pid_to_tien=[1]) == ""


def test_conftest_in_chan_doan_thay_vi_cho_im_lang():
    """`conftest` phai GOI cua chan doan do — khong chi co ham roi khong ai dung."""
    src = (GOC / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "ai_giu_khoa_la_to_tien" in src, (
        "conftest chua dung cua chan doan: mot luot bi treo se lai im lang")


if __name__ == "__main__":       # pragma: no cover
    for ten, ly in sorted(tim_lop_boc().items()):
        print(f"{ten:20s} <- {ly}")
    raise SystemExit(pytest.main([__file__, "-q"]))
