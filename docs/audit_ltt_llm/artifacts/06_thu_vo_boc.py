# -*- coding: utf-8 -*-
"""thu_vo_boc.py -- Prompt 06 §1/§2: vo boc NSSM chet thi chuyen gi xay ra?

Chay TREN MAY B. Ghi ket qua xuong tep SAU MOI BUOC.

## Hai cau hoi, khong phai mot

1. SCM co dung day dich vu khong? (vua bat FAILURE_ACTIONS luc 23:58)
2. Ban moi co GIANH LAI duoc cong 8299 khong, hay tien trinh con MO COI van
   giu cong va lam ban moi chet khi bind?

Cau 2 moi la cau kho. Vo boc chet -> con mo coi song sot -> `/health` VAN 200
trong khi `Get-Service` noi Stopped. Do la health XANH GIA, dung thu ma §2 bao
phai chung minh la khong xay ra.

## ⛔ KIEM DUNG CU TRUOC

Da hong dung cu BA lan trong mot toi:
  1. doc sai ten truong -> `.get()` -> None -> bao hoi quy GIA
  2. dong ho co the chet ma van cho ra day so 0 -> phai co doi chung
  3. `curl -w` tra chuoi RONG -> vong lap tuong dich vu chet tu giay 0

⇒ To nay BAT DAU bang mot phep tu kiem: neu `/health` khong tra 200 va
  `Get-Service` khong Running ngay tu dau thi DUNG, khong do gi ca.

## ⛔ GHI XUONG TEP TUNG BUOC

Nexus co tran CUNG 120s bat ke `timeout_ms`. Mot phep do 150s bi cat mat sach
ket qua luc 23:52. Ghi tung buoc thi dut van con so lieu.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RA = Path(r"H:\LTT_LLM\work\ket_vo_boc.txt")
TOK = ""
for _d in Path(r"C:\ProgramData\LTTLlm\gateway.env").read_text(
        encoding="utf-8-sig").splitlines():
    if _d.startswith("LTT_LLM_TOKEN="):
        TOK = _d.split("=", 1)[1].strip()


def ghi(s: str = "") -> None:
    print(s, flush=True)
    with RA.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def ma_health() -> int:
    """Ma HTTP cua /health. 0 = khong noi duoc (dich vu that su chet)."""
    try:
        yc = urllib.request.Request(
            "http://127.0.0.1:8299/health",
            headers={"User-Agent": "ltt-vb/1.0",
                     "Authorization": f"Bearer {TOK}"})
        with urllib.request.urlopen(yc, timeout=3) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0


def ps(lenh: str) -> str:
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                        "-Command", lenh], capture_output=True, text=True,
                       timeout=60)
    return (r.stdout or "").strip()


def trang_thai() -> str:
    return ps("(Get-Service LTTLlmGateway).Status")


def pid_cong() -> str:
    return ps("(Get-NetTCPConnection -LocalPort 8299 -State Listen "
              "-ErrorAction SilentlyContinue).OwningProcess") or "<khong ai>"


def pid_scm() -> str:
    return ps("(Get-WmiObject Win32_Service -Filter \"Name='LTTLlmGateway'\")"
              ".ProcessId")


def main() -> int:
    RA.write_text(f"THU VO BOC  {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
                  encoding="utf-8")

    # ---- TU KIEM DUNG CU (xem docstring: da hong 3 lan trong mot toi) ----
    ma, tt = ma_health(), trang_thai()
    ghi(f"tu kiem: /health={ma}  Get-Service={tt}  "
        f"pid_cong={pid_cong()}  pid_scm={pid_scm()}")
    if ma != 200 or tt != "Running":
        ghi("DUNG -- he chua o trang thai nen, khong do gi ca.")
        ghi("   (KHONG phai 'khong dat' -- la 'khong do duoc'.)")
        return 2
    ghi("   dung cu OK: doc duoc 200 va Running -> phep do co nghia.")
    ghi("")

    vo = pid_scm()
    con = pid_cong()
    ghi(f"vo boc (SCM biet) = {vo}")
    ghi(f"con dang phuc vu  = {con}")
    ghi(f"hai so nay {'BANG NHAU' if vo == con else 'KHAC NHAU'}")
    ghi("")
    ghi(f"-- DUNG VO BOC {vo} --")
    ps(f"Stop-Process -Id {vo} -Force")

    t0 = time.monotonic()
    mo_coi_thay = False
    for _ in range(200):
        t = round(time.monotonic() - t0, 1)
        if t > 100:
            break
        ma, tt, pc = ma_health(), trang_thai(), pid_cong()
        ghi(f"  +{t:>5.1f}s  /health={ma:<3} Get-Service={tt:<8} cong8299={pc}")
        if ma == 200 and tt != "Running":
            mo_coi_thay = True
        if tt == "Running" and ma == 200 and pc not in ("<khong ai>", con):
            ghi("")
            ghi(f"  => SCM DA DUNG DAY, va ban moi GIANH DUOC cong (pid moi {pc})")
            break
        time.sleep(2.5)

    ghi("")
    ghi("KET LUAN")
    ghi(f"  co thay HEALTH XANH GIA khong (200 nhung Stopped): "
        f"{'CO -- day la lo §2' if mo_coi_thay else 'khong'}")
    ghi(f"  trang thai cuoi: Get-Service={trang_thai()} /health={ma_health()} "
        f"cong8299={pid_cong()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
