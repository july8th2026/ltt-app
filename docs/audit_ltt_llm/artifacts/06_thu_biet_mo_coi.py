# -*- coding: utf-8 -*-
"""thu_biet_mo_coi.py -- mot tien trinh con CO tu biet no da mo coi khong?

Chay TREN MAY B. Khong dung toi dich vu nao -- tu dung cay cha/con rieng.

## Cau hoi

Bao cao 06 §6 cua toi viet: "khong sua duoc bang cach lam /health thong minh
hon, vi /health do CHINH con mo coi phuc vu". Cau do co the QUA MANH.

Con mo coi biet mot su that ve THE GIOI BEN NGOAI no: cha no da chet. Neu no
kiem duoc dieu do thi MOT nguon van du, va lap luan "phai hai nguon" cua toi
sai -- hoac it nhat la khong bat buoc.

## Cai bay phai tranh khi kiem

Windows KHONG danh so lai PID ngay, nhung no CO tai su dung PID sau mot thoi
gian. Nen "PPID con ton tai" CHUA DU -- phai kiem ca TEN va GIO KHOI DONG. Neu
khong, mot PID duoc cap lai cho tien trinh khac se lam con mo coi tuong cha
minh con song, va phep kiem im lang dung luc no can noi.

## 🔴 KHONG IN RA STDOUT

To nay GIET CHA MINH, va cha la chu cua ong stdout. Ban dau no dung `print()`,
va toan bo phan sau luc giet bi mat sach -- exit=-1, khong mot dong nao.
Ghi ra tep, doc bang mot luot goi khac.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

RA = Path(r"H:\LTT_LLM\work\ket_mo_coi.txt")


def out(s: str = "") -> None:
    with RA.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def ps(lenh: str) -> str:
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                        "-Command", lenh], capture_output=True, text=True,
                       timeout=30)
    return (r.stdout or "").strip()


def _mo_ta(pid: int) -> str:
    """'ten|gio sinh' cua mot PID, hoac '' neu khong co tien trinh do."""
    return ps(f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
              f"if ($p) {{ $p.ProcessName + '|' + "
              f"$p.StartTime.ToString('yyyy-MM-dd HH:mm:ss') }}")


def cha_con_song(ppid: int, mo_ta_luc_dau: str) -> bool:
    """Cha con song KHONG? So ca TEN va GIO SINH -- xem docstring."""
    return _mo_ta(ppid) == mo_ta_luc_dau


def main() -> int:
    RA.write_text("", encoding="utf-8")
    ppid = os.getppid()
    ban_dau = _mo_ta(ppid)
    if not ban_dau:
        out("khong doc duoc cha ngay tu dau -- thi nghiem VO")
        return 2
    out(f"toi pid={os.getpid()}  cha pid={ppid}  {ban_dau}")
    out(f"cha con song? {cha_con_song(ppid, ban_dau)}   <- phai la True")

    out(f"-- dung cha {ppid} --")
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    f"Stop-Process -Id {ppid} -Force"], capture_output=True)

    for i in (1, 2, 4, 8):
        time.sleep(i)
        song = cha_con_song(ppid, ban_dau)
        out(f"  +{i}s  toi VAN CHAY (pid {os.getpid()}), cha con song? {song}"
            f"   [cha bay gio: {_mo_ta(ppid) or '<khong co>'}]")
        if not song:
            out("")
            out("KET: CO -- mot tien trinh con TU BIET duoc no da mo coi.")
            out("   => lap luan 'phai hai nguon' cua bao cao 06 QUA MANH.")
            out("   => co mot ban sua MOT NGUON, re hon va khong can Nexus.")
            return 0
    out("")
    out("KET: KHONG -- con khong phan biet duoc. Lap luan hai nguon dung.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
