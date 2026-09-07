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


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    hong: list[str] = []
    ds = can_soi()
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

    print(f"[ascii] {len(ds)} tep cau hinh deu thuan ASCII")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
