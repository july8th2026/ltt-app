r"""nang_quyen.py — chay MOT script Python voi quyen Administrator, lay ket qua ve.

    python tools\nang_quyen.py <duong_dan_script.py> [tham so...]
    python tools\nang_quyen.py --lenh "python -c 'print(1)'"

## Vi sao co tep nay

Mot so viec tren may nay CHI lam duoc khi nang quyen, va deu la viec that:

  * doc `C:\LTTPlatform\secrets\app.env` (ACL chi SYSTEM/Administrators)
    -> ba buoc gate (`bat bien da tien trinh`, `migration tren postgres`,
       `M-1 tren postgres`) TU BO QUA neu khong doc duoc, va gate tu khai o dong
       `RESULT` rang chung "KHONG PHAI BANG CHUNG";
  * doc trang thai tien trinh cua dich vu (`LTTStudioWeb`) — tu phien thuong,
    `cpu_percent()` tra 0% chu khong bao loi, tuc mot phep do SAI IM LANG;
  * ghi so khoa, chay `setup\2-cai-dat.ps1`.

Truoc khi co tep nay, moi lan can quyen la mot lan dung tay mot cap
`.ps1` + `Start-Process -Verb RunAs` moi. Ba lan trong mot buoi la ba lan lap
lai cung mot khuon, va **hai lan trong so do sai** theo dung hai kieu duoi day.

## ⛔ TEP NAY KHONG NOI UAC, KHONG DOI ACL

No dung dung co che Windows da co. `CLAUDE.md` ghi ro ACL o `secrets\` va
`D:\LTTBackups` la **co y**, va *"thay Access denied ma chay `icacls` de mo ra la
go mot ban va bao mat da hoan thanh"*. Cong cu nay cho phep **lam viec can
quyen**, no khong cho phep **ha muc an toan**.

## Hai cai bay da dinh, va cach tep nay chan chung

🔴 **Duong dan co DAU CACH.** `-ArgumentList '-File','C:\Users\Thang Tuong\...'`
   bi cat thanh hai tham so; PowerShell di mo `C:\Users\Thang` roi **chet im
   lang** — khong log, khong loi. Tep nay luon dung dang 8.3 (`GetShortPathName`)
   cho moi duong dan truyen sang tien trinh nang quyen.

🔴 **`| Add-Content` giu HANDLE DOC QUYEN** tren tep log suot ca luot chay, nen
   khong doc duoc tien do trong luc can nhat. Tep nay dung `cmd /c ... > log`:
   `>` cua cmd mo tep voi `FILE_SHARE_READ`.

⚠️ Va mot cai bay thu ba, khong chan duoc bang ma: tien trinh nang quyen KHONG
   thua ke `PATH` cua Git Bash, nen `sh` khong tim thay va bat ky buoc nao goi
   `sh` se do bang `FileNotFoundError [WinError 2]`. Tep nay tu them Git vao
   `PATH`, va dat `PYTHONIOENCODING=utf-8` (cp1252 lam cong cu chet o mot emoji).
"""
from __future__ import annotations

import argparse
import ctypes
import os
import pathlib
import subprocess
import sys
import tempfile
import time

GIT_BIN = (r"C:\Program Files\Git\bin", r"C:\Program Files\Git\usr\bin")


def dang_nang_quyen() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        # không phải Windows (`ctypes.windll` vắng) ⇒ coi như không nâng quyền.
        return False


def duong_ngan(p: str) -> str:
    """Dang 8.3 — duong dan KHONG dau cach.

    ⛔ Day khong phai mot toi uu: `-ArgumentList` cat tham so theo dau cach, nen
       mot duong dan co dau cach truyen sang tien trinh nang quyen se thanh HAI
       tham so va PowerShell chet im lang. Xem docstring dau tep.
    """
    buf = ctypes.create_unicode_buffer(1024)
    n = ctypes.windll.kernel32.GetShortPathNameW(str(p), buf, 1024)
    return buf.value if n else str(p)


def chay(lenh: str, cho_giay: float = 1800.0, log: str = "") -> tuple[int, str]:
    """Chay `lenh` (mot dong cmd) voi quyen Admin. Tra `(ma_thoat, van_ban_log)`.

    Cho toi khi xong hoac het `cho_giay`. Log doc duoc TRONG LUC chay.
    """
    tam = pathlib.Path(log) if log else pathlib.Path(
        tempfile.gettempdir()) / f"nang_quyen_{int(time.time())}.log"
    tam.parent.mkdir(parents=True, exist_ok=True)
    tam.write_text("", encoding="utf-8")

    ps1 = tam.with_suffix(".ps1")
    duong_path = ";".join(GIT_BIN)
    # THUAN ASCII (CLAUDE.md luat 16: PowerShell 5.1 doc .ps1 khong BOM theo ANSI).
    ps1.write_text(
        "$ErrorActionPreference = 'Continue'\n"
        "$env:PYTHONIOENCODING = 'utf-8'\n"
        # 🔴 Thieu dong nay thi loi hua o docstring — "Log doc duoc TRONG LUC
        #    chay" — SAI voi moi tien trinh con Python: stdout bi chuyen huong
        #    la stdout ghi theo KHOI, nen tep log trong hang chuc phut du viec
        #    van dang chay. 23/09: mot luot do 22 phut bi chan doan nham la
        #    TREO dung vi the, va ca may bi chan theo.
        "$env:PYTHONUNBUFFERED = '1'\n"
        f"$env:PATH = '{duong_path};' + $env:PATH\n"
        f"Set-Location '{pathlib.Path.cwd()}'\n"
        f'cmd /c "{lenh} > ""{tam}"" 2>&1"\n'
        f'Add-Content "{tam}" ("__MA_THOAT__=" + $LASTEXITCODE)\n',
        encoding="ascii", errors="replace")

    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList "
         f"'-NoProfile','-ExecutionPolicy','Bypass','-File','{duong_ngan(str(ps1))}' "
         "-PassThru -WindowStyle Hidden | Select-Object -ExpandProperty Id"],
        capture_output=True, text=True)
    if r.returncode != 0:
        return 1, f"khong khoi dong duoc tien trinh nang quyen: {r.stderr[:300]}"

    han = time.monotonic() + cho_giay
    while time.monotonic() < han:
        van = tam.read_text(encoding="utf-8", errors="replace")
        if "__MA_THOAT__=" in van:
            ma = van.rsplit("__MA_THOAT__=", 1)[1].strip() or "0"
            return (int(ma) if ma.lstrip("-").isdigit() else 1,
                    van.rsplit("__MA_THOAT__=", 1)[0])
        time.sleep(2)
    return 124, tam.read_text(encoding="utf-8", errors="replace")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Chay mot viec voi quyen Admin.")
    ap.add_argument("script", nargs="?", default="",
                    help="tep .py chay voi quyen Admin")
    ap.add_argument("tham_so", nargs="*", help="tham so cho script")
    ap.add_argument("--lenh", default="", help="chay thang mot dong cmd")
    ap.add_argument("--cho", type=float, default=1800.0, help="tran cho (giay)")
    ap.add_argument("--log", default="", help="duong dan log")
    a = ap.parse_args(argv)

    if dang_nang_quyen():
        print("(da nang quyen san — chay thang)")
        if a.lenh:
            return subprocess.run(a.lenh, shell=True).returncode
        return subprocess.run([sys.executable, a.script, *a.tham_so]).returncode

    if a.lenh:
        lenh = a.lenh
    elif a.script:
        # Duong dan 8.3 cho CA trinh thong dich lan script: ca hai deu co the
        # nam duoi mot thu muc co dau cach.
        lenh = " ".join([duong_ngan(sys.executable), duong_ngan(a.script),
                         *[f'"{x}"' for x in a.tham_so]])
    else:
        ap.error("can `script` hoac `--lenh`")

    ma, van = chay(lenh, a.cho, a.log)
    sys.stdout.write(van)
    if ma == 124:
        print(f"\n[nang_quyen] HET GIO sau {a.cho:.0f}s — viec co the van dang chay")
    return ma


if __name__ == "__main__":
    raise SystemExit(main())
