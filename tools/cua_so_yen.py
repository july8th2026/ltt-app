"""cua_so_yen.py — mot khoa cap may cho cac luot do dat tien.

    python tools/cua_so_yen.py trang-thai     # ai dang giu, tu bao gio
    python tools/cua_so_yen.py nha --ep       # go khoa treo (hiem khi can)

## Vi sao no ton tai

Kho nay thuong xuyen co **ba phien Claude cung ghi mot cay**. Mot luot
`gate.py` day du mat 5-6 phut va pha `bo test` lay `-n auto` = **moi loi**.
Hai luot cung luc tren 20 loi thi moi luot duoc ~7 loi: tong thoi gian gan y
het chay lan luot, nhung tra them gap doi bo nho, gap doi thu muc tam, va gap
doi kha nang do sai.

⇒ Song song hoa mot thu **da bao hoa loi** khong phai toi uu, chi la chia nho
  cung mot chiec banh. Nen cho xep hang, dung cho tranh.

⭐ Va cai xep hang mua duoc thu quan trong hon toc do: mot **cua so yen**. Phien
   dang cho biet chinh xac ai dang do va tu bao gio, nen no biet nen doi hay nen
   di lam viec khac — thay vi nhan tin hoi nhau roi doan.

## Vi sao KHONG dat khoa trong cay kho

`gate._anh_chup_cay()` quet `tools/` de phat hien cay doi giua chung. Mot tep
khoa nam trong do se **tu lam ban phep do cua chinh no**: gate ghi khoa luc bat
dau, thay `tools/...` doi luc ket thuc, roi bao "cay da doi". Cung lop loi voi
"gate tu nhieu vao phep do" da ghi trong CLAUDE.md.

⛔ KHONG dung `os.kill(pid, 0)` de do tien trinh con song tren Windows. Python
   tren Windows dich moi tin hieu khac `CTRL_C_EVENT`/`CTRL_BREAK_EVENT` thanh
   `TerminateProcess` — tuc phep "do xem con song khong" se **giet** dung cai
   tien trinh no dang hoi. Dung `OpenProcess` qua ctypes.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

#: Ngoai cay kho — xem ghi chu dau tep.
TEP_KHOA = Path(tempfile.gettempdir()) / "ltt_cua_so_yen.json"

#: Khoa gia hon nguong nay coi nhu treo, du tien trinh con song. Mot luot gate
#: day du mat ~6 phut; 2 gio la rong rai gap 20 lan, nen cham nguong nay nghia
#: la co gi do that su hong chu khong phai "dang chay lau".
TUOI_TOI_DA_S = 7200

#: Nhip in lai dong "dang doi" khi xep hang. Im lang qua thi nguoi dung tuong treo.
NHIP_IN_S = 15


def _con_song(pid: int) -> bool:
    """PID con song khong. Khong bao gio dung `os.kill` — xem dau tep."""
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    import ctypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return False
    try:
        # ⚠️ Mo duoc handle KHONG du de ket luan con song: mot tien trinh da
        #    thoat van mo duoc handle chung nao con ai giu tham chieu toi no.
        #    Phai hoi ma thoat — `STILL_ACTIVE` moi la dang chay.
        ma = ctypes.c_ulong()
        if k32.GetExitCodeProcess(h, ctypes.byref(ma)):
            return ma.value == STILL_ACTIVE
        return True
    finally:
        k32.CloseHandle(h)


def _doc() -> dict | None:
    try:
        return json.loads(TEP_KHOA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _treo(ban_ghi: dict) -> str:
    """Khoa co dang treo khong. Tra LY DO, hoac chuoi rong neu con hieu luc."""
    pid = int(ban_ghi.get("pid") or 0)
    tuoi = time.time() - float(ban_ghi.get("bat_dau_epoch") or 0)
    if not _con_song(pid):
        return f"tien trinh {pid} khong con chay"
    if tuoi > TUOI_TOI_DA_S:
        return f"giu qua lau ({tuoi / 3600:.1f} gio)"
    return ""


def _mo_ta(ban_ghi: dict) -> str:
    giay = time.time() - float(ban_ghi.get("bat_dau_epoch") or 0)
    ten = ban_ghi.get("phien") or "?"
    return (f"{ten} (pid {ban_ghi.get('pid')}) chay "
            f"`{ban_ghi.get('lenh') or '?'}` duoc {giay / 60:.1f} phut")


def thu_giu(phien: str, lenh: str) -> bool:
    """Thu chiem khoa MOT lan. True neu duoc."""
    ban_ghi = {
        "phien": phien,
        "pid": os.getpid(),
        "may": socket.gethostname(),
        "lenh": lenh,
        "bat_dau_epoch": time.time(),
        "bat_dau": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    try:
        # O_EXCL: hai tien trinh cung goi thi dung MOT thang thang. Doc-roi-ghi
        # khong lam duoc dieu do, va cua so dua chinh la luc dong nhat.
        fd = os.open(TEP_KHOA, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        cu = _doc()
        if cu is None:
            # Tep co that nhung khong doc duoc: rac tu mot lan ngat giua chung.
            TEP_KHOA.unlink(missing_ok=True)
            return thu_giu(phien, lenh)
        ly_do = _treo(cu)
        if not ly_do:
            return False
        print(f"  [cua so yen] doat khoa treo: {_mo_ta(cu)} - {ly_do}")
        TEP_KHOA.unlink(missing_ok=True)
        return thu_giu(phien, lenh)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(ban_ghi, ensure_ascii=False))
    return True


def nha(phien: str = "", *, ep: bool = False) -> bool:
    """Tra khoa. Chi tra khoa CUA MINH tru khi `ep`."""
    cu = _doc()
    if cu is None:
        TEP_KHOA.unlink(missing_ok=True)
        return True
    if not ep and int(cu.get("pid") or 0) != os.getpid():
        return False
    TEP_KHOA.unlink(missing_ok=True)
    return True


class CuaSoYen:
    """Context manager: giu khoa suot mot luot do.

    ⛔ `bat=False` van dung duoc nhu mot khoi `with` — de ben goi khong phai
       viet hai nhanh chi vi co mot co `--khong-khoa`.

    ⚠️ Cho qua han thi **van chay**, khong bo cuoc. Mot cong chat luong tu choi
       chay vi ban la mot cong khong ai dung; no chi phai NOI RO rang ket qua
       lan nay co the bi nhieu.
    """

    def __init__(self, phien: str, lenh: str, *, bat: bool = True,
                 cho_toi_da_s: float = 1800.0):
        self.phien = phien
        self.lenh = lenh
        self.bat = bat
        self.cho_toi_da_s = cho_toi_da_s
        self.da_giu = False
        self.da_cho_s = 0.0

    def __enter__(self) -> "CuaSoYen":
        if not self.bat:
            return self
        bat_dau = time.time()
        in_lan_cuoi = 0.0
        while True:
            if thu_giu(self.phien, self.lenh):
                self.da_giu = True
                self.da_cho_s = time.time() - bat_dau
                if self.da_cho_s > 2:
                    print(f"  [cua so yen] den luot - da doi "
                          f"{self.da_cho_s / 60:.1f} phut\n")
                return self
            doi = time.time() - bat_dau
            if doi > self.cho_toi_da_s:
                cu = _doc() or {}
                print(f"  [cua so yen] cho qua {self.cho_toi_da_s / 60:.0f} "
                      f"phut ma khoa van bi giu: {_mo_ta(cu)}")
                print("  [cua so yen] CHAY MA KHONG CO KHOA - ket qua co the "
                      "bi nhieu boi luot kia.\n")
                self.da_cho_s = doi
                return self
            if time.time() - in_lan_cuoi > NHIP_IN_S:
                print(f"  [cua so yen] xep hang {doi / 60:.1f} phut - "
                      f"{_mo_ta(_doc() or {})}")
                in_lan_cuoi = time.time()
            time.sleep(1.0)

    def __exit__(self, *_exc) -> None:
        if self.da_giu:
            nha(self.phien)


def main() -> int:
    p = argparse.ArgumentParser(description="Khoa cua so yen cho cac luot do.")
    p.add_argument("lenh", choices=["trang-thai", "nha"])
    p.add_argument("--ep", action="store_true",
                   help="voi `nha`: go ca khoa cua phien khac")
    a = p.parse_args()

    if a.lenh == "trang-thai":
        cu = _doc()
        if cu is None:
            print("RANH - khong ai giu cua so yen.")
            return 0
        print(f"DANG GIU: {_mo_ta(cu)}")
        print(f"  tep: {TEP_KHOA}")
        ly_do = _treo(cu)
        if ly_do:
            print(f"  CANH BAO: khoa nay TREO ({ly_do}) - luot sau se tu doat.")
        return 0

    if nha(ep=a.ep):
        print("Da nha khoa.")
        return 0
    print("Khoa dang do phien khac giu. Dung `nha --ep` neu chac no treo.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
