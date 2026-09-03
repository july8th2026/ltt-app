"""giam_sat_may.py — hop den cua may. Ghi lien tuc, doc lai sau mot lan treo.

    python tools/giam_sat_may.py --chay          # chay nen, ghi moi 15s
    python tools/giam_sat_may.py --kham          # KHAM NGHIEM sau mot lan reset
    python tools/giam_sat_may.py --kham 2        # kham hai lan dut gan nhat
    python tools/giam_sat_may.py --trang-thai    # dang chay khong

## Khac gi `nhat_ky_chay.py`

    nhat_ky_chay   ghi MOT luot chay, boc quanh mot lenh
    giam_sat_may   ghi LIEN TUC, khong phu thuoc ai chay gi

Ngay 03/09 may reset **hai lan**. Ca hai lan `nhat_ky_chay` deu chua ton tai
hoac chua duoc dung, va quan trong hon: **cai lam treo may co the khong phai
lenh ta boc**. Do duoc luc do: cay gate co 13 tien trinh, toan may co 58. Bon
muoi lam cai con lai — bot, phien Claude khac, dich vu production, deploy — khong
di qua bat cu thu gi ta boc duoc.

⇒ Hop den phai ghi **may**, khong phai **lenh cua ta**.

## 🔑 `--kham` la ly do tep nay ton tai

Ghi log thi de. Cai kho la sau mot lan reset, doc mot nghin dong JSON de tra loi
"cai gi lam treo". `--kham` lam viec do:

  1. tim cho log **DUT** (khoang trong > 3 nhip = may chet hoac ngu)
  2. lay 6 mau cuoi truoc khi dut
  3. xep hang tien trinh theo CPU va RAM o dung nhung mau do
  4. so voi nen binh thuong cua chinh may (trung vi 24h) de biet cai gi BAT THUONG

⛔ No khong doan nguyen nhan. No dua ra ai dang chiem cho luc do va cai gi lech
   khoi thuong le — phan ket luan la cua nguoi doc. Mot cong cu tu ket luan se
   dan nguoi doc vao gia thuyet dau tien, va do dung la kieu sai da xay ra chin
   lan trong mot ngay o du an nay.

## Ba rang buoc thiet ke

### 1. Chinh no khong duoc thanh nghi can

Bai hoc dat nhat 03/09: phep do cua toi la mot trong ba ung vien lam treo may —
`process_iter` qua 58 tien trinh, `cpu_percent` tung cai, moi 2 giay.

⇒ Nhip **15 giay**, va moi vong chi lay **top 5** tien trinh theo CPU. Do bang
  `oneshot()` de mot lan doc lay het truong, thay vi goi lai tung truong.

### 2. `flush` + `fsync` moi dong

Mot lan treo khong cho tien trinh dong tep. Thu nam trong buffer la thu khong
bao gio doc lai duoc, dung luc no dang gia nhat.

### 3. ASCII thuan o dau ra

`print` mot emoji vo voi `UnicodeEncodeError` tren stdout cp1252 — va no vo o
dung nhanh "bi cat", tuc dung luc can doc nhat. Da xay ra that voi
`nhat_ky_chay.py`.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

THU_MUC = Path(tempfile.gettempdir()) / "ltt_hop_den"

#: Nhip ghi. Thua co y — xem rang buoc 1 dau tep.
NHIP_S = 15.0

#: Bao nhieu tien trinh nang nhat duoc ghi moi vong.
TOP_N = 5

#: Khoang trong bao nhieu NHIP thi coi la log DUT (may chet / ngu / reset).
NHIP_COI_LA_DUT = 3

#: Giu bao nhieu ngay. Moi ngay mot tep.
GIU_NGAY = 7


#: Da dat moc `cpu_percent` cho tung tien trinh chua. Xem `mot_vong`.
_da_dat_moc = False


def _tep_hom_nay() -> Path:
    THU_MUC.mkdir(parents=True, exist_ok=True)
    return THU_MUC / f"{datetime.now():%Y%m%d}.jsonl"


def _don_tep_cu() -> None:
    """Xoa tep qua han. Mot hop den phinh mai se bi ai do xoa ca thu muc."""
    gioi_han = time.time() - GIU_NGAY * 86400
    for t in THU_MUC.glob("*.jsonl"):
        try:
            if t.stat().st_mtime < gioi_han:
                t.unlink()
        except OSError:
            pass


def mot_vong() -> dict:
    """Mot anh chup. Nhe: top-N tien trinh, doc bang `oneshot`."""
    try:
        import psutil
    except ImportError:
        return {"loi": "khong co psutil"}

    m = psutil.virtual_memory()
    ra = {"cpu": psutil.cpu_percent(interval=0.2),
          "ram_trong_gib": round(m.available / 2**30, 2),
          "so_tien_trinh": len(psutil.pids())}

    # 🔴 `p.cpu_percent(None)` lan goi DAU cua MOI tien trinh tra 0.0 — no do
    #    chenh lech voi lan truoc, va lan dau khong co lan truoc. Voi bo loc
    #    `if c <= 0: continue` ben duoi, ket qua la `top: []` — mot may dang
    #    chay 100% trong y het mot may khong co tien trinh nao.
    #
    # ⇒ Dat moc cho MOI tien trinh, doi mot nhip ngan, roi moi doc that. Trong
    #   `chay()` moc da co tu vong truoc nen buoc nay gan nhu mien phi; o lan
    #   goi don le (vd `--trang-thai`) thi no la thu cuu ket qua khoi rong.
    if not _da_dat_moc:
        for p in psutil.process_iter():
            try:
                p.cpu_percent(None)
            except (psutil.Error, OSError):
                pass
        time.sleep(0.3)
        globals()["_da_dat_moc"] = True

    nang = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            # ⛔ `System Idle Process` la tien trinh NHAN ROI cua Windows: CPU%
            #    cua no la tong so loi dang RANH, nen no luon dung dau bang va
            #    day moi thu that xuong. Mot bao cao kham nghiem mo dau bang
            #    "System Idle Process 1786%" la mot bao cao khong ai doc tiep.
            if p.pid in (0, 4):
                continue
            with p.oneshot():
                c = p.cpu_percent(None)
                if c <= 0:
                    continue
                nang.append({"pid": p.pid, "ten": (p.info["name"] or "")[:22],
                             "cpu": round(c, 1),
                             "ram_mb": round(p.memory_info().rss / 2**20)})
        except (psutil.Error, OSError):
            continue
    nang.sort(key=lambda x: -x["cpu"])
    ra["top"] = nang[:TOP_N]
    return ra


def chay() -> int:
    """Vong lap ghi. Chay nen, khong in gi tru khi hong."""
    try:
        import psutil
        psutil.cpu_percent(interval=None)          # dat moc cho lan do dau
        for p in psutil.process_iter():
            try:
                p.cpu_percent(None)
            except psutil.Error:
                pass
    except ImportError:
        print("[hop den] khong co psutil - khong ghi duoc")
        return 1

    print(f"[hop den] ghi vao {THU_MUC}, nhip {NHIP_S:.0f}s. Ctrl-C de dung.")
    _don_tep_cu()
    ngay = None
    f = None
    try:
        while True:
            t = _tep_hom_nay()
            if t != ngay:
                if f:
                    f.close()
                f = open(t, "a", encoding="utf-8", newline="\n")
                ngay = t
                _don_tep_cu()
            dong = {"t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    **mot_vong()}
            f.write(json.dumps(dong, ensure_ascii=False) + "\n")
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
            time.sleep(NHIP_S)
    except KeyboardInterrupt:
        print("\n[hop den] dung.")
        return 0
    finally:
        if f:
            f.close()


# ══════════════════════════════════════════════════════════════════════════════
#  KHAM NGHIEM — phan quan trong nhat
# ══════════════════════════════════════════════════════════════════════════════

def _doc_het() -> list[dict]:
    ra = []
    for t in sorted(THU_MUC.glob("*.jsonl")):
        for l in t.read_text(encoding="utf-8", errors="replace").splitlines():
            l = l.strip()
            if not l:
                continue
            try:
                ra.append(json.loads(l))
            except ValueError:
                continue          # dong ghi do dang luc may chet - bo qua
    return ra


def _giay(d: dict) -> float:
    return datetime.fromisoformat(d["t"]).timestamp()


def _tim_cho_dut(dong: list[dict]) -> list[int]:
    """Chi so cua nhung mau NGAY TRUOC mot khoang trong bat thuong."""
    nguong = NHIP_S * NHIP_COI_LA_DUT
    return [i for i in range(len(dong) - 1)
            if _giay(dong[i + 1]) - _giay(dong[i]) > nguong]


def kham(so_lan: int = 1) -> int:
    if not THU_MUC.is_dir():
        print(f"[kham] chua co hop den nao o {THU_MUC}")
        print("       bat bang: python tools/giam_sat_may.py --chay")
        return 1
    dong = _doc_het()
    if len(dong) < 4:
        print(f"[kham] moi co {len(dong)} mau - chua du de kham")
        return 1

    cpu_all = [d["cpu"] for d in dong if "cpu" in d]
    ram_all = [d["ram_trong_gib"] for d in dong if "ram_trong_gib" in d]
    nen_cpu = statistics.median(cpu_all) if cpu_all else 0
    nen_ram = statistics.median(ram_all) if ram_all else 0
    print(f"[kham] {len(dong)} mau tu {dong[0]['t']} den {dong[-1]['t']}")
    print(f"       NEN cua may nay: CPU trung vi {nen_cpu:.0f}%, "
          f"RAM trong trung vi {nen_ram:.1f} GiB")

    dut = _tim_cho_dut(dong)
    if not dut:
        print("\n[kham] KHONG co cho dut nao - may chua tat/treo trong ky nay.")
        return 0

    for chi_so in dut[-max(1, so_lan):]:
        truoc, sau = dong[chi_so], dong[chi_so + 1]
        khoang = (_giay(sau) - _giay(truoc)) / 60
        print(f"\n{'='*66}")
        print(f"DUT luc {truoc['t']} -> chay lai {sau['t']}  (im lang {khoang:.0f} phut)")
        print(f"{'='*66}")

        mau = dong[max(0, chi_so - 5):chi_so + 1]
        print(f"\n  6 mau cuoi truoc khi dut:")
        for d in mau:
            co = "  <-- BAT THUONG" if d.get("cpu", 0) > nen_cpu * 2 + 20 else ""
            print(f"    {d['t'][11:19]}  CPU {d.get('cpu', 0):5.1f}%  "
                  f"RAM trong {d.get('ram_trong_gib', 0):5.1f} GiB  "
                  f"{d.get('so_tien_trinh', 0):4d} tien trinh{co}")

        gom: dict[str, dict] = {}
        for d in mau:
            for p in d.get("top", []):
                k = p["ten"]
                g = gom.setdefault(k, {"cpu": 0.0, "ram_mb": 0, "lan": 0})
                g["cpu"] += p["cpu"]
                g["ram_mb"] = max(g["ram_mb"], p["ram_mb"])
                g["lan"] += 1
        if gom:
            print(f"\n  Ai chiem cho trong 6 mau do (tong CPU, RAM dinh):")
            for ten, g in sorted(gom.items(), key=lambda x: -x[1]["cpu"])[:8]:
                print(f"    {ten:24} CPU {g['cpu']:7.1f}  "
                      f"RAM {g['ram_mb']:6d} MB  ({g['lan']} mau)")

        cuoi = mau[-1]
        print(f"\n  So voi nen:")
        d_cpu = cuoi.get("cpu", 0) - nen_cpu
        d_ram = cuoi.get("ram_trong_gib", 0) - nen_ram
        print(f"    CPU      {cuoi.get('cpu', 0):.0f}%  "
              f"({'+' if d_cpu >= 0 else ''}{d_cpu:.0f} diem so voi nen)")
        print(f"    RAM trong {cuoi.get('ram_trong_gib', 0):.1f} GiB  "
              f"({'+' if d_ram >= 0 else ''}{d_ram:.1f} GiB)")
        if cuoi.get("ram_trong_gib", 99) < 3:
            print("    [!] RAM trong RAT THAP - het bo nho la nguyen nhan hang dau")
        if cuoi.get("cpu", 0) > 90:
            print("    [!] CPU bao hoa o mau cuoi")

    print("\n[kham] Day la SO LIEU, khong phai ket luan. Doi chieu voi:")
    print("       - nhat ky lenh:  python tools/nhat_ky_chay.py --xem 3")
    print("       - log bot:       D:/FULL AUTO VIDEO/*/logs/")
    print("       - phien khac:    ListAgents")
    return 0


def trang_thai() -> int:
    try:
        import psutil
    except ImportError:
        print("khong co psutil")
        return 1
    # ⛔ Loc theo `cmdline[1]`, KHONG quet chuoi trong ca dong lenh.
    #
    # 🔴 Lan thu MUOI MOT cua cung mot loi trong ngay 03/09: ban dau dong nay
    #    la `any("giam_sat_may" in str(c) for c in cmdline)`, va no bat ba
    #    **shell wrapper** cua chinh cau lenh vua go — cmdline cua chung chua
    #    chuoi do vi no la cau lenh. Bao "DANG CHAY pid [3 cai]" cho mot thu
    #    khong chay.
    #
    #    Cung lop loi da bat "7 tien trinh gate.py" (that ra 1) va "5 tien trinh
    #    test_nhanh" (that ra 1). **Quet chuoi bat nham thu NHAC DEN no.**
    dang = []
    for pr in psutil.process_iter(["pid", "cmdline"]):
        cl = pr.info["cmdline"] or []
        if len(cl) > 1 and str(cl[1]).endswith("giam_sat_may.py")                 and pr.pid != os.getpid():
            dang.append(pr.pid)
    print(f"hop den: {'DANG CHAY pid ' + str(dang) if dang else 'KHONG chay'}")
    if THU_MUC.is_dir():
        tep = sorted(THU_MUC.glob("*.jsonl"))
        print(f"tep: {len(tep)} ngay, moi nhat: {tep[-1].name if tep else '(khong)'}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Hop den cua may.")
    p.add_argument("--chay", action="store_true", help="vong lap ghi (chay nen)")
    p.add_argument("--kham", nargs="?", type=int, const=1, default=None,
                   help="kham nghiem N lan dut gan nhat")
    p.add_argument("--trang-thai", action="store_true")
    a = p.parse_args()
    if a.chay:
        return chay()
    if a.kham is not None:
        return kham(a.kham)
    if a.trang_thai:
        return trang_thai()
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
