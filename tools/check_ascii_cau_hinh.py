r"""Tep cau hinh doc bang BANG MA HE THONG phai THUAN ASCII.

    py tools\check_ascii_cau_hinh.py

## Vi sao luat nay ton tai

Ba tep duoi day KHONG duoc doc bang UTF-8:

    mypy.ini        `configparser.read()` mo tep theo encoding HE THONG
    .importlinter   cung vay
    *.ps1           PowerShell 5.1 doc `.ps1` khong BOM theo bang ma ANSI

Tren may nay bang ma he thong la **cp1252**. Mot ky tu ngoai ASCII trong nhung
tep ay khong bao "sai ky tu" — no lam VO CA TEP, va bao loi o cho khac.

## Ba lan da tra gia

    CLAUDE.md quy tac 2   mot dau tieng Viet trong `.ps1` lam hong ca cau lenh
                          va bao loi o DONG KHAC
    06/09  mypy.ini       emoji -> `UnicodeDecodeError ... byte 0x90`, mypy
                          chet han (rc 2) TRUOC khi kiem mot dong ma nao
    06/09  .importlinter  ban dau cua chinh toi co mot dau `=>` unicode — go
                          ngay trong tep dang VIET RA luat ay

⭐ Lan thu ba la ly do cong cu nay ton tai thay vi mot dong chu thich. Toi da
   biet luat, viet luat, roi vi pham luat trong cung mot tep. Tri thuc khong
   chan duoc lop loi nay; mot phep do thi co.

⛔ `.editorconfig` KHONG thay duoc: no chi noi cho TRINH SOAN THAO, khong rang
   buoc script ghi tep, va phan lon tep o kho nay do script ghi ra.
"""
from __future__ import annotations

import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent

#: Tep don le + mau glob. Chi liet ke thu THAT SU duoc doc bang bang ma he
#: thong — dua them tep UTF-8 vao day la tao ra bao dong gia.
TEP = ("mypy.ini", ".importlinter")
MAU = ("setup/*.ps1", "*.ps1", "tools/*.ps1")

#: Thu muc khong soi: ban sinh ra, ban vendor, ban cua phien khac.
BO_QUA = ("tmp", "dist", "build", "node_modules", ".playwright-cli",
          ".claude", "cutclipshort", "core")


def _bo_qua(p: pathlib.Path) -> bool:
    return any(phan in BO_QUA for phan in p.relative_to(GOC).parts)


def can_soi() -> list[pathlib.Path]:
    ra: list[pathlib.Path] = []
    for ten in TEP:
        p = GOC / ten
        if p.is_file():
            ra.append(p)
    for mau in MAU:
        for p in GOC.glob(mau):
            if p.is_file() and not _bo_qua(p):
                ra.append(p)
    return sorted(set(ra))


def _da_theo_doi_git():
    """Tap duong dan (posix) ma git DANG THEO DOI, hoac `None` neu khong hoi duoc.

    `git ls-files` gom ca tep **dang staged**, nen mot tep moi sap commit VAN bi
    chan — dung: do la luc phai bat.
    """
    import subprocess

    try:
        ra = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                            cwd=str(GOC), timeout=90)
    except (OSError, subprocess.SubprocessError):
        return None
    if ra.returncode != 0:
        return None
    return {d.strip().replace(chr(92), "/") for d in ra.stdout.splitlines()
            if d.strip()}


def can_soi_chan() -> list[pathlib.Path]:
    """Tap duoc quyen lam DO. Chi tep git dang theo doi.

    🔴 Do 26/09/2026: `deploy.ps1` — mot tep CHUA THEO DOI, scratch cua mot lan khac,
       co mot dau gach dai trong chu thich — **chan commit cua MOI phien**. Do la lan
       thu ba trong mot ngay mot thu khong thuoc kho chan ca kho (truoc do: mot
       worktree trong kho lam banh coc ruff dem gap doi; mot chuoi chua boc `_()` cua
       lan khac). Ca ba cung mot hinh: **phep do noi ve "kho nay" nhung dem thu nam
       tren DIA**.

    ⚠️ Tep chua theo doi VAN duoc neu ra o `main()` — chi la khong lam do. Mot `.ps1`
       co ky tu ngoai ASCII se vo khi **ai do chay no**, du chua vao kho; bo han phan
       canh bao la doi mot bao dong gia thanh mot diem mu.

    ⛔ `git` khong tra loi ⇒ **chan TAT CA** (tra ve nguyen tap soi), khong phai cho
       qua. Cho qua la fail-open: mot loi cong cu se TAT banh coc, im lang.
    """
    theo_doi = _da_theo_doi_git()
    ds = can_soi()
    if theo_doi is None:
        return ds
    return [p for p in ds
            if p.relative_to(GOC).as_posix() in theo_doi]


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    hong: list[str] = []
    ds = can_soi_chan()
    for p in ds:
        b = p.read_bytes()
        xau = [(i, by) for i, by in enumerate(b) if by > 127]
        if xau:
            vt, byte = xau[0]
            # Dong nao, de nguoi sua khong phai dem byte.
            dong = b[:vt].count(b"\n") + 1
            hong.append(f"   {p.relative_to(GOC).as_posix()}: {len(xau)} byte "
                        f"ngoai ASCII, dau tien o dong {dong} (0x{byte:02x})")

    if hong:
        print("[ascii] TEP CAU HINH CO KY TU NGOAI ASCII:")
        print("\n".join(hong))
        print("\n  Nhung tep nay duoc doc bang BANG MA HE THONG (cp1252), khong")
        print("  phai UTF-8. Mot ky tu ngoai ASCII lam VO CA TEP, va trieu chung")
        print("  se hien o cho khac. Xem docstring cua tools/check_ascii_cau_hinh.py")
        return 1

    # Tep CHUA THEO DOI van duoc neu ra — chi la khong lam do. Mot `.ps1` co ky tu
    # ngoai ASCII se vo khi AI DO CHAY NO, du no chua vao kho. Bo han phan nay la
    # doi mot bao dong gia thanh mot diem mu.
    canh: list[str] = []
    for p in can_soi():
        if p in ds:
            continue
        b = p.read_bytes()
        xau = [(i, by) for i, by in enumerate(b) if by > 127]
        if xau:
            dong = b[:xau[0][0]].count(bytes([10])) + 1
            canh.append(f"   {p.relative_to(GOC).as_posix()}: {len(xau)} byte "
                        f"ngoai ASCII, dau tien o dong {dong} — CHUA THEO DOI")
    if canh:
        print("[ascii] CANH BAO (khong lam do, vi git chua theo doi nhung tep nay):")
        print(chr(10).join(canh))
        print("  Chay chung thi PowerShell doc theo cp1252 va tep VO — sua truoc "
              "khi chay, hoac truoc khi commit.")

    print(f"[ascii] {len(ds)} tep cau hinh (da theo doi) deu thuan ASCII")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
