"""don_tien_trinh_mo_coi.py - thu hoi tien trinh con cua bo test bi bo lai.

    python tools\\don_tien_trinh_mo_coi.py           # xem, KHONG giet
    python tools\\don_tien_trinh_mo_coi.py --giet    # giet that
    python tools\\don_tien_trinh_mo_coi.py --gio 6   # doi nguong tuoi

================================================================================
VI SAO CAN TEP NAY — DO DUOC 30/08, VA CON SO KHONG NHO

    324 tien trinh python dang chay
    210 trong so do la con `multiprocessing.spawn` MO COI
    194 da song hon 3 gio, cu nhat tu 29/08 05:57 (gan hai ngay)
    9,5 GB RAM bi giu
    85 GB temp bi KHOA (154/158 thu muc pytest khong xoa duoc)

O muc do do, o C: con 9,4 GB / 930 GB. Postgres cua production nam tren C:. Neu
no day, Postgres TU CHOI GHI — va trieu chung se khong noi "het dia", no hien ra
thanh job hong ngau nhien hoac `/health/ready` 503.

================================================================================
VI SAO KHONG SUA BANG CACH "DON CHO KY HON"

`test_214` DA don dung: `p.join(timeout=...)` roi `p.terminate()` roi `join` lai.
Doc ma khong thay loi nao. Ro ri chi xay ra khi **tien trinh CHA bi giet giua
chung** — gate qua gio, Ctrl-C, `| head` gay SIGPIPE. Luc do vong `join` khong
bao gio chay.

Va tren Windows co mot cua so hep hon nua: `spawn` khoi dong con TRUOC khi gui
payload qua pipe. Cha chet dung khoang do thi con **ngoi cho mai mai** mot thu se
khong bao gio toi. Do la ly do chung dung o **42 MB** — co trinh thong dich vua
khoi dong, chua kip nap gi. Chinh con co han tu dung (`time.monotonic() >= han`)
nhung no chua bao gio chay toi do.

⛔ Khong co cach nao ngan mot tien trinh bi SIGKILL don dep sau no. Nen dung muc
   tieu la **ngan**, ma la **tu lanh**: moi luot chay don xac cu truoc khi bat dau.

================================================================================
BA DIEU KIEN, PHAI DU CA BA

Thieu mot dieu la co rui ro giet nham thu dang chay:

  1. duong thuc thi chua `Python313`        - dung trinh thong dich cua bo test
  2. dong lenh chua `multiprocessing.spawn` - dung la con spawn, khong phai app
  3. da song lau hon `--gio` gio            - khong dung vao luot dang chay

! VA BA THU KHONG BAO GIO DUNG TOI, du co khop:
    - `C:\\LTTPlatform\\*`  - dich vu production dang phuc vu khach
    - tien trinh khong doc duoc dong lenh - khong du can cu thi khong dung
    - tien trinh con moi hon nguong - co the la luot dang chay cua phien khac
"""
from __future__ import annotations

import argparse
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

#: Duong thuc thi cua trinh thong dich chay bo test. Con cua `spawn` thua ke no.
DAU_HIEU_TRINH_THONG_DICH = "python313"

#: Duong TUYET DOI khong dung toi, du moi dieu kien khac deu khop.
CAM = ("c:\\lttplatform\\",)


def ung_vien(gio: float) -> list:
    """Cac tien trinh du CA BA dieu kien. Doc-only."""
    try:
        import psutil
    except ImportError:
        print("khong co psutil - bo qua (khong phai loi)")
        return []

    moc = time.time() - gio * 3600.0
    ra = []
    for p in psutil.process_iter(["name", "exe", "cmdline", "create_time"]):
        try:
            if (p.info["name"] or "").lower() != "python.exe":
                continue
            exe = (p.info["exe"] or "").lower()
            if not exe or DAU_HIEU_TRINH_THONG_DICH not in exe:
                continue
            if any(exe.startswith(c) for c in CAM):
                continue
            dong_lenh = " ".join(p.info["cmdline"] or ())
            if "multiprocessing.spawn" not in dong_lenh:
                continue
            if (p.info["create_time"] or 0) >= moc:
                continue
            ra.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--giet", action="store_true",
                    help="giet that; khong co co nay thi chi xem")
    ap.add_argument("--gio", type=float, default=3.0,
                    help="chi dung toi tien trinh cu hon bao nhieu gio (mac dinh 3)")
    a = ap.parse_args(argv)

    ds = ung_vien(a.gio)
    if not ds:
        print(f"Khong co tien trinh mo coi nao cu hon {a.gio:g} gio.")
        return 0

    ram = 0
    cu_nhat = time.time()
    for p in ds:
        try:
            ram += p.memory_info().rss
            cu_nhat = min(cu_nhat, p.create_time())
        except Exception:                                       # noqa: BLE001
            pass
    tuoi = (time.time() - cu_nhat) / 3600.0
    print(f"Tien trinh con mo coi (cu hon {a.gio:g} gio): {len(ds)}")
    print(f"  RAM dang giu : {ram / 1024 ** 3:.1f} GB")
    print(f"  Cu nhat      : {tuoi:.1f} gio")

    if not a.giet:
        print("\n(chi xem — them `--giet` de thu hoi)")
        return 0

    xong = 0
    for p in ds:
        try:
            p.kill()
            xong += 1
        except Exception:                                       # noqa: BLE001
            pass
    print(f"\nDa dung: {xong}/{len(ds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
