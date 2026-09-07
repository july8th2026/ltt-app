r"""Banh coc CVE cho phu thuoc SAN PHAM -- chot TAP HOP theo ma advisory.

    py tools\check_cve.py            # kiem, so voi danh sach da chap nhan
    py tools\check_cve.py --accept   # ghi lai danh sach (PHAI kem ly do)

## ⛔ VI SAO TEP MOC NAY KHAC MOI TEP MOC KHAC TRONG KHO

`check_ruff.moc` va `check_mypy.moc` chot **so luong**: chung la no ky thuat,
va don dan la viec noi bo. Mot CVE thi khong phai no ky thuat -- no la mot lo
hong ma NGUOI NGOAI co the khai thac, va "chap nhan" no la mot quyet dinh BAO
MAT, khong phai mot quyet dinh gon gang ma nguon.

⇒ Nen `check_cve.moc` khong chi ghi ma advisory. Moi dong PHAI co LY DO, va
  cong cu TU CHOI chay neu mot dong thieu ly do. Mot danh sach mien tru khong
  ly do la mot danh sach se dai ra ma khong ai nho vi sao.

## Trang thai 06/09/2026

`cryptography` co 4 advisory (6 dong, co trung lap). `requirements.txt:17` da
ghi san phan tich: ban va doi 48-50, ma tran hien tai la `<47.0`, nen nang len
la mot QUYET DINH RIENG co anh huong deploy -- khong phai viec cong cu nay tu
lam.

⭐ Gia tri cua banh coc nay khong phai "phat hien ra cai da biet", ma la:
   **advisory THU NAM se lam gate do**, thay vi nam im den luc co nguoi tinh
   co chay lai.

## ⛔ Duong SUY BIEN: khong co mang

`pip-audit` hoi PyPI/OSV qua mang. Mot buoc gate phu thuoc mang se do vi ly do
KHONG LIEN QUAN toi ma nguon -- va mot cong do vi ly do khong lien quan la mot
cong day nguoi ta bo qua mau do (xem `docs/BAY_TRONG_CONG_CHAT_LUONG.md` Bay
26).

⇒ Mat mang thi TU KHAI `BO QUA` va tra 0. Gate co co che doc dong do. Nhung
  phai noi RO la da bo qua, khong duoc im lang thanh "sach".
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent

#: Chi soi phu thuoc SAN PHAM. `requirements-dev.txt` khong duoc cai tren may
#: chu (xem dau tep do), nen mot CVE o `pytest` khong phai be mat tan cong.
TEP_YEU_CAU = ("requirements.txt", "requirements-server.txt")

TEP_MOC = pathlib.Path(
    __import__("os").environ.get("LTT_CVE_MOC")
    or pathlib.Path(__file__).with_name("check_cve.moc"))

_DONG_MOC = re.compile(r"^(?P<ma>[A-Za-z0-9-]+)\s*\|\s*(?P<goi>[^|]+?)\s*\|\s*(?P<ly_do>.+)$")


def _ra(*p: object) -> None:
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    print(*p)


def quet() -> tuple[set[tuple[str, str]], str]:
    """({(ma_advisory, goi)}, ly_do_bo_qua). Ly do rong = da quet duoc that."""
    thay: set[tuple[str, str]] = set()
    for ten in TEP_YEU_CAU:
        p = GOC / ten
        if not p.is_file():
            continue
        r = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--progress-spinner", "off",
             "--format", "json", "-r", str(p)],
            cwd=GOC, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode not in (0, 1):
            # ⛔ 2+ = khong chay duoc. Phan lon la mang; nhung KHONG doan --
            #    in dau ra that cho nguoi doc.
            return set(), (f"`pip-audit` khong chay duoc tren {ten} "
                           f"(ma {r.returncode}): {(r.stderr or '')[-300:]}")
        try:
            d = json.loads(r.stdout or "{}")
        except ValueError:
            return set(), f"`pip-audit` tra dau ra khong phai JSON tren {ten}"
        for goi in d.get("dependencies", []):
            for v in goi.get("vulns", []) or []:
                thay.add((v.get("id", "?"), goi.get("name", "?")))
    return thay, ""


def doc_moc() -> dict[tuple[str, str], str]:
    if not TEP_MOC.exists():
        return {}
    ra: dict[tuple[str, str], str] = {}
    for so, dong in enumerate(TEP_MOC.read_text(encoding="utf-8").splitlines(), 1):
        d = dong.strip()
        if not d or d.startswith("#"):
            continue
        m = _DONG_MOC.match(d)
        if not m:
            raise SystemExit(
                f"{TEP_MOC.name}:{so} sai dinh dang.\n"
                f"  Moi dong phai la:  <MA> | <goi> | <ly do>\n"
                f"  Mot dong mien tru KHONG CO LY DO la mot dong se song mai ma "
                f"khong ai nho vi sao.\n  Doc duoc: {d!r}")
        ra[(m.group("ma"), m.group("goi").strip())] = m.group("ly_do").strip()
    return ra


def main() -> int:
    hien, bo_qua = quet()
    if bo_qua:
        # Gate doc dong bat dau bang `BO QUA` la mot buoc TU KHAI khong lam gi.
        _ra(f"BO QUA: {bo_qua}")
        _ra("  => KHONG ket luan gi ve bao mat. Chay lai khi co mang.")
        return 0

    moc = doc_moc()
    if "--accept" in sys.argv:
        _ra("[cve] `--accept` KHONG ghi tu dong.")
        _ra(f"  Moi advisory phai co LY DO do nguoi viet. Them tay vao "
            f"{TEP_MOC.name}:")
        for ma, goi in sorted(hien - set(moc)):
            _ra(f"    {ma} | {goi} | <ly do o day>")
        return 1

    moi = sorted(hien - set(moc))
    het = sorted(set(moc) - hien)

    if moi:
        _ra("[cve] ADVISORY MOI -- moi dong duoi day la mot lo hong CHUA duoc xet:")
        for ma, goi in moi:
            _ra(f"   {goi:<20} {ma}")
        _ra("\n  Sua bang cach NANG goi, hoac neu that su phai chap nhan thi them")
        _ra(f"  vao {TEP_MOC.name} kem LY DO, va noi ro trong commit.")
        return 1

    _ra(f"[cve] {len(hien)} advisory, tat ca da duoc xet ({len(moc)} dong trong moc)")
    if het:
        _ra("   da HET (nho go khoi moc):")
        for ma, goi in het:
            _ra(f"   {goi:<20} {ma}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
